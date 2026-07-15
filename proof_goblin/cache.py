

"""Private filesystem cache for provider review results."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from os import replace as replace_file
from pathlib import Path

from proof_goblin.builder import Prompt
from proof_goblin.observations import ReviewResult, ReviewResultProvenanceError

CACHE_KEY_VERSION = "2"
CACHE_DIRECTORY_ENV = "PROOF_GOBLIN_CACHE_DIR"
STALE_LOCK_AGE = timedelta(minutes=15)


class ReviewCacheError(RuntimeError):
    """Raised when a cached review cannot be safely read or written."""


class ReviewCache:
    """Store canonical results as private, atomically replaced JSON files."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or default_cache_directory()

    def key_for(self, prompt: Prompt, *, provider: str, model: str) -> str:
        """Return the stable identity of a provider request."""

        identity = {
            "version": CACHE_KEY_VERSION,
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
        return self._hash_identity(identity)

    @staticmethod
    def _hash_identity(identity: dict[str, str | None]) -> str:
        encoded = json.dumps(
            identity,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

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
        prompt: Prompt,
        provider: str,
        model: str,
    ) -> ReviewResult | None:
        """Load and verify a cached result, or return ``None`` on a miss."""

        if key != self.key_for(prompt, provider=provider, model=model):
            raise ReviewCacheError("review cache key does not match request identity")
        legacy_key = self._legacy_key_for(prompt, provider=provider, model=model)
        candidates = ((self._result_path(key), False),)
        if legacy_key != key:
            candidates += ((self._result_path(legacy_key), True),)

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
                result = ReviewResult.from_dict(record, prompt=prompt)
                if result.provider != provider:
                    raise ValueError("cached provider does not match request")
                return result
            except ReviewResultProvenanceError as exc:
                if is_legacy:
                    # Version 1 omitted provenance from its key. A mismatch is
                    # therefore a safe cache miss rather than corruption.
                    continue
                raise ReviewCacheError(
                    f"cached review {path} is invalid; rerun with --refresh: {exc}"
                ) from exc
            except (json.JSONDecodeError, ValueError) as exc:
                raise ReviewCacheError(
                    f"cached review {path} is invalid; rerun with --refresh: {exc}"
                ) from exc
        return None

    def store(
        self,
        key: str,
        result: ReviewResult,
        *,
        request_provider: str,
        request_model: str,
    ) -> None:
        """Atomically store a canonical result without prompt text."""

        expected_key = self.key_for(
            result.prompt,
            provider=request_provider,
            model=request_model,
        )
        if key != expected_key:
            raise ReviewCacheError("review cache key does not match request identity")
        if result.provider != request_provider:
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
