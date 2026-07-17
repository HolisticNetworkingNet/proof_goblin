"""Private filesystem cache for provider review results."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from os import replace as replace_file
from pathlib import Path
from typing import Any

from proof_goblin.builder import Prompt
from proof_goblin.observations import ReviewResult, ReviewResultProvenanceError
from proof_goblin.providers.base import ProviderRequest

CACHE_KEY_VERSION = "3"
CACHE_DIRECTORY_ENV = "PROOF_GOBLIN_CACHE_DIR"
STALE_LOCK_AGE = timedelta(minutes=15)


class ReviewCacheError(RuntimeError):
    """Raised when a cached review cannot be safely read or written."""


class ReviewCache:
    """Store canonical results as private, atomically replaced JSON files."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or default_cache_directory()

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
                serialized = path.read_text(encoding="utf-8")
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

        return self._result_path(key).is_file()

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
                lock_file.write(f"pid={os.getpid()}\n")
            yield
        finally:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    def _prepare_directory(self) -> None:
        existed = self.directory.exists()
        try:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if not existed:
                self.directory.chmod(0o700)
            elif (
                os.name != "nt" and stat.S_IMODE(self.directory.stat().st_mode) & 0o077
            ):
                raise ReviewCacheError(
                    f"review cache {self.directory} must have user-only permissions"
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
    def _create_lock(path: Path) -> int:
        try:
            return os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            raise
        except OSError as exc:
            raise ReviewCacheError(
                f"could not reserve review cache {path}: {exc}"
            ) from exc

    @staticmethod
    def _remove_stale_lock(path: Path) -> bool:
        try:
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, UTC)
            if datetime.now(UTC) - modified_at < STALE_LOCK_AGE:
                return False
            path.unlink()
            return True
        except FileNotFoundError:
            return True
        except OSError as exc:
            raise ReviewCacheError(
                f"could not inspect review cache reservation {path}: {exc}"
            ) from exc


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
