"""Deterministic boundaries for decoded text artifacts."""

from __future__ import annotations

import re

DEFAULT_ARTIFACT_MEDIA_TYPE = "text/plain"

_ASCII_WHITESPACE = " \t\n\r\f\v"
_TOKEN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_MEDIA_TYPES_BY_EXTENSION = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".csv": "text/csv",
    ".rst": "text/x-rst",
    ".py": "text/x-python",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".cjs": "text/javascript",
    ".json": "application/json",
    ".xml": "application/xml",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".toml": "application/toml",
}
_ALIASES = {"application/x-yaml": "application/yaml"}


class ArtifactMediaTypeError(ValueError):
    """Raised when an artifact media type is malformed or unsupported."""


def resolve_artifact_media_type(
    artifact_name: str,
    explicit_media_type: str | None = None,
) -> str:
    """Return one canonical supported textual media type.

    Explicit values take precedence. Otherwise the final filename extension is
    resolved through Proof Goblin's fixed mapping. Extensionless names use
    ``text/plain``; unknown extensions require an explicit value.
    """

    if not isinstance(artifact_name, str) or not artifact_name.strip():
        raise ArtifactMediaTypeError("artifact_name must be a non-empty string")
    if explicit_media_type is None:
        return _infer_artifact_media_type(artifact_name)
    if not isinstance(explicit_media_type, str):
        raise ArtifactMediaTypeError("artifact media type must be a string")

    media_type = explicit_media_type.strip(_ASCII_WHITESPACE).lower()
    parts = media_type.split("/")
    if (
        len(parts) != 2
        or not all(_TOKEN.fullmatch(part) for part in parts)
        or "*" in media_type
    ):
        raise ArtifactMediaTypeError(
            "artifact media type must be a bare ASCII type/subtype without "
            "parameters or wildcards"
        )

    media_type = _ALIASES.get(media_type, media_type)
    if not _is_supported_textual_media_type(media_type):
        raise ArtifactMediaTypeError(
            f"unsupported artifact media type {media_type!r}; "
            "Proof Goblin accepts decoded textual artifacts only"
        )
    return media_type


def _infer_artifact_media_type(artifact_name: str) -> str:
    filename = artifact_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    dot_index = filename.rfind(".")
    if dot_index == -1:
        return DEFAULT_ARTIFACT_MEDIA_TYPE
    extension = filename[dot_index:].lower()
    try:
        return _MEDIA_TYPES_BY_EXTENSION[extension]
    except KeyError:
        raise ArtifactMediaTypeError(
            f"unrecognized artifact file extension {extension!r}; "
            "provide an explicit artifact media type"
        ) from None


def _is_supported_textual_media_type(media_type: str) -> bool:
    top_level, subtype = media_type.split("/", 1)
    if top_level == "text":
        return True
    if top_level != "application":
        return False
    if subtype in {"json", "xml", "yaml", "toml"}:
        return True
    return (subtype.endswith("+json") and len(subtype) > len("+json")) or (
        subtype.endswith("+xml") and len(subtype) > len("+xml")
    )
