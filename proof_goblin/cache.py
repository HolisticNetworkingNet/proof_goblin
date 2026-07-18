"""Private filesystem cache for provider review results."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import sys
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from os import replace as replace_file
from pathlib import Path
from threading import Event, Thread
from typing import Any

from proof_goblin.builder import Prompt
from proof_goblin.observations import ReviewResult, ReviewResultProvenanceError
from proof_goblin.providers.base import ProviderRequest

CACHE_KEY_VERSION = "3"
CACHE_DIRECTORY_ENV = "PROOF_GOBLIN_CACHE_DIR"
STALE_LOCK_AGE = timedelta(minutes=15)
LOCK_HEARTBEAT_INTERVAL = timedelta(minutes=1)


class ReviewCacheError(RuntimeError):
    """Raised when a cached review cannot be safely read or written."""


class ReviewCache:
    """Store canonical results as private, atomically replaced JSON files."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        stale_lock_age: timedelta = STALE_LOCK_AGE,
        lock_heartbeat_interval: timedelta = LOCK_HEARTBEAT_INTERVAL,
    ) -> None:
        self.directory = directory or default_cache_directory()
        if stale_lock_age <= timedelta(0):
            raise ValueError("stale_lock_age must be positive")
        if not timedelta(0) < lock_heartbeat_interval < stale_lock_age:
            raise ValueError(
                "lock_heartbeat_interval must be positive and less than stale_lock_age"
            )
        self.stale_lock_age = stale_lock_age
        self.lock_heartbeat_interval = lock_heartbeat_interval

    def key_for(self, request: ProviderRequest) -> str:
        """Return the stable identity of a provider request."""

        try:
            return self._hash_identity(
                {
                    "version": CACHE_KEY_VERSION,
                    "provider": request.provider,
                    "model": request.model,
                    "parameters": request.parameters,
                }
            )
        except (TypeError, ValueError) as exc:
            raise ReviewCacheError(
                "prepared provider request must contain JSON-compatible values"
            ) from exc

    @staticmethod
    def _hash_identity(identity: object) -> str:
        encoded = json.dumps(
            identity,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _version_two_key_for(self, prompt: Prompt, *, provider: str, model: str) -> str:
        return self._hash_identity(
            {
                "version": "2",
                "provider": provider,
                "model": model,
                "system": prompt.system,
                "user": prompt.user,
                "review_name": prompt.review_name,
                "config_name": prompt.config_name,
                "config_version": prompt.config_version,
                "config_sha256": prompt.config_sha256,
                "artifact_name": prompt.artifact_name,
                "artifact_media_type": prompt.artifact_media_type,
                "artifact_sha256": prompt.artifact_sha256,
            }
        )

    def _legacy_key_for(self, prompt: Prompt, *, provider: str, model: str) -> str:
        return self._hash_identity(
            {
                "version": "1",
                "provider": provider,
                "model": model,
                "system": prompt.system,
                "user": prompt.user,
            }
        )

    def load(
        self,
        key: str,
        *,
        request: ProviderRequest,
        prompt: Prompt,
        invalid_as_miss: bool = False,
    ) -> ReviewResult | None:
        """Load and verify a cached result, or return ``None`` on a miss."""

        if key != self.key_for(request):
            raise ReviewCacheError("review cache key does not match request identity")
        self._prepare_directory()
        version_two_key = self._version_two_key_for(
            prompt,
            provider=request.provider,
            model=request.model,
        )
        legacy_key = self._legacy_key_for(
            prompt,
            provider=request.provider,
            model=request.model,
        )
        candidates = [(self._result_path(key), False)]
        for legacy_candidate in (version_two_key, legacy_key):
            if legacy_candidate != key:
                candidates.append((self._result_path(legacy_candidate), True))

        for path, is_legacy in candidates:
            try:
                serialized = self._read_entry(path)
            except FileNotFoundError:
                continue
            except (OSError, UnicodeError) as exc:
                raise ReviewCacheError(
                    f"could not read review cache {path}: {exc}"
                ) from exc

            try:
                record = json.loads(serialized)
                if not isinstance(record, dict):
                    raise ValueError("cached result must be an object")
                result_prompt = prompt if is_legacy else _cached_prompt(record, prompt)
                result = ReviewResult.from_dict(record, prompt=result_prompt)
                if result.provider != request.provider:
                    raise ValueError("cached provider does not match request")
                return result
            except ReviewResultProvenanceError as exc:
                if is_legacy:
                    # Version 1 omitted provenance from its key. A mismatch is
                    # therefore a safe cache miss rather than corruption.
                    continue
                if invalid_as_miss:
                    return None
                raise ReviewCacheError(
                    f"cached review {path} is invalid; rerun with --refresh: {exc}"
                ) from exc
            except (json.JSONDecodeError, ValueError) as exc:
                if invalid_as_miss:
                    return None
                raise ReviewCacheError(
                    f"cached review {path} is invalid; rerun with --refresh: {exc}"
                ) from exc
        return None

    def has_entry(self, key: str) -> bool:
        """Return whether the exact current-version cache path exists."""

        try:
            entry = self._result_path(key).lstat()
        except FileNotFoundError:
            return False
        return stat.S_ISREG(entry.st_mode)

    def store(
        self,
        key: str,
        result: ReviewResult,
        *,
        request: ProviderRequest,
    ) -> None:
        """Atomically store a canonical result without prompt text."""

        expected_key = self.key_for(request)
        if key != expected_key:
            raise ReviewCacheError("review cache key does not match request identity")
        if result.provider != request.provider:
            raise ReviewCacheError("response provider does not match request provider")
        self._prepare_directory()
        path = self._result_path(key)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.directory,
                prefix=f".{key}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(result.to_json())
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            temporary_path.chmod(0o600)
            replace_file(temporary_path, path)
        except (OSError, UnicodeError) as exc:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise ReviewCacheError(
                f"could not write review cache {path}: {exc}"
            ) from exc

    @contextmanager
    def reserve(self, key: str) -> Iterator[None]:
        """Prevent simultaneous provider calls for the same review identity."""

        self._prepare_directory()
        path = self.directory / f"{key}.lock"
        token = secrets.token_hex(16)
        try:
            descriptor = self._create_lock(path)
        except FileExistsError:
            if not self._remove_stale_lock(path):
                raise ReviewCacheError(
                    "an identical review request is already in progress"
                ) from None
            try:
                descriptor = self._create_lock(path)
            except FileExistsError as exc:
                raise ReviewCacheError(
                    "an identical review request is already in progress"
                ) from exc

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as lock_file:
                lock_file.write(f"pid={os.getpid()} token={token}\n")
                lock_file.flush()
                os.fsync(lock_file.fileno())
            stop_heartbeat = Event()
            heartbeat_errors: list[ReviewCacheError] = []
            heartbeat = Thread(
                target=self._heartbeat_lock,
                args=(path, token, stop_heartbeat, heartbeat_errors),
                name="proof-goblin-cache-heartbeat",
                daemon=True,
            )
            heartbeat.start()
            completed = False
            yield
            completed = True
        finally:
            if "stop_heartbeat" in locals():
                stop_heartbeat.set()
                heartbeat.join()
            self._release_lock(path, token)
        if completed and heartbeat_errors:
            raise heartbeat_errors[0]

    def _prepare_directory(self) -> None:
        try:
            try:
                directory = self.directory.lstat()
            except FileNotFoundError:
                self.directory.mkdir(mode=0o700, parents=True)
                self.directory.chmod(0o700)
                directory = self.directory.lstat()
            if stat.S_ISLNK(directory.st_mode):
                raise ReviewCacheError(
                    f"review cache directory {self.directory} must not be a symbolic link"
                )
            if not stat.S_ISDIR(directory.st_mode):
                raise ReviewCacheError(
                    f"review cache {self.directory} must be a directory"
                )
            _require_private_posix_entry(
                directory,
                self.directory,
                "review cache directory",
            )
        except ReviewCacheError:
            raise
        except OSError as exc:
            raise ReviewCacheError(
                f"could not prepare review cache {self.directory}: {exc}"
            ) from exc

    def _result_path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    @staticmethod
    def _read_entry(path: Path) -> str:
        entry = path.lstat()
        if stat.S_ISLNK(entry.st_mode):
            raise ReviewCacheError(
                f"review cache entry {path} must not be a symbolic link"
            )

        descriptor: int | None = None
        try:
            flags = (
                os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            descriptor = os.open(path, flags)
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise ReviewCacheError(
                    f"review cache entry {path} must be a regular file"
                )
            _require_private_posix_entry(
                opened,
                path,
                "review cache entry",
            )
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = None
                return stream.read().decode("utf-8")
        finally:
            if descriptor is not None:
                os.close(descriptor)

    @staticmethod
    def _create_lock(path: Path) -> int:
        try:
            return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise
        except OSError as exc:
            raise ReviewCacheError(
                f"could not reserve review cache {path}: {exc}"
            ) from exc

    def _remove_stale_lock(self, path: Path) -> bool:
        try:
            lock = path.lstat()
            if stat.S_ISLNK(lock.st_mode) or not stat.S_ISREG(lock.st_mode):
                raise ReviewCacheError(
                    f"review cache reservation {path} must be a regular file"
                )
            _require_private_posix_entry(
                lock,
                path,
                "review cache reservation",
            )
            modified_at = datetime.fromtimestamp(lock.st_mtime, UTC)
            if datetime.now(UTC) - modified_at < self.stale_lock_age:
                return False
            path.unlink()
            return True
        except FileNotFoundError:
            return True
        except OSError as exc:
            raise ReviewCacheError(
                f"could not inspect review cache reservation {path}: {exc}"
            ) from exc

    def _heartbeat_lock(
        self,
        path: Path,
        token: str,
        stop: Event,
        errors: list[ReviewCacheError],
    ) -> None:
        interval = self.lock_heartbeat_interval.total_seconds()
        while not stop.wait(interval):
            try:
                if not self._lock_matches(path, token):
                    raise ReviewCacheError(
                        f"review cache reservation {path} changed while active"
                    )
                os.utime(path, None)
            except (OSError, ReviewCacheError) as exc:
                if isinstance(exc, ReviewCacheError):
                    errors.append(exc)
                else:
                    errors.append(
                        ReviewCacheError(
                            f"could not refresh review cache reservation {path}: {exc}"
                        )
                    )
                return

    def _release_lock(self, path: Path, token: str) -> None:
        try:
            if self._lock_matches(path, token):
                path.unlink()
        except (OSError, ReviewCacheError):
            pass

    @staticmethod
    def _lock_matches(path: Path, token: str) -> bool:
        lock = path.lstat()
        if stat.S_ISLNK(lock.st_mode) or not stat.S_ISREG(lock.st_mode):
            raise ReviewCacheError(
                f"review cache reservation {path} must be a regular file"
            )
        _require_private_posix_entry(lock, path, "review cache reservation")
        return f"token={token}" in path.read_text(encoding="utf-8")


def _require_private_posix_entry(
    entry: os.stat_result,
    path: Path,
    noun: str,
) -> None:
    if os.name == "nt":
        return
    if hasattr(os, "geteuid") and entry.st_uid != os.geteuid():
        raise ReviewCacheError(f"{noun} {path} must be owned by the current user")
    if stat.S_IMODE(entry.st_mode) & 0o077:
        raise ReviewCacheError(f"{noun} {path} must have user-only permissions")


def _cached_prompt(record: Mapping[str, Any], current: Prompt) -> Prompt:
    """Attach cached provenance to request-equivalent in-memory prompt text."""

    review = _cached_mapping(record, "review")
    config = _cached_mapping(record, "config")
    artifact = _cached_mapping(record, "artifact")
    config_sha256 = config.get("sha256")
    if config_sha256 is not None and not isinstance(config_sha256, str):
        raise ValueError("config.sha256 must be a string or null")
    return replace(
        current,
        review_name=_cached_string(review, "name", "review.name"),
        config_name=_cached_string(config, "name", "config.name"),
        config_version=_cached_string(config, "version", "config.version"),
        config_sha256=config_sha256,
        artifact_name=_cached_string(artifact, "name", "artifact.name"),
        artifact_media_type=_cached_string(
            artifact,
            "media_type",
            "artifact.media_type",
        ),
        artifact_sha256=_cached_string(artifact, "sha256", "artifact.sha256"),
    )


def _cached_mapping(record: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = record.get(field)
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _cached_string(record: Mapping[str, Any], field: str, display_name: str) -> str:
    value = record.get(field)
    if not isinstance(value, str):
        raise ValueError(f"{display_name} must be a string")
    return value


def default_cache_directory() -> Path:
    """Return the platform-native per-user cache directory."""

    override = os.getenv(CACHE_DIRECTORY_ENV)
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "proof-goblin"
    if os.name == "nt":
        root = os.getenv("LOCALAPPDATA")
        if root:
            return Path(root) / "proof-goblin" / "Cache"
        return Path.home() / "AppData" / "Local" / "proof-goblin" / "Cache"
    root = os.getenv("XDG_CACHE_HOME")
    if root:
        return Path(root).expanduser() / "proof-goblin"
    return Path.home() / ".cache" / "proof-goblin"
