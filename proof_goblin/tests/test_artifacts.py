from __future__ import annotations

import pytest

from proof_goblin import ArtifactMediaTypeError, resolve_artifact_media_type


@pytest.mark.parametrize(
    ("artifact_name", "expected"),
    [
        ("draft.txt", "text/plain"),
        ("draft.md", "text/markdown"),
        ("draft.markdown", "text/markdown"),
        ("draft.html", "text/html"),
        ("draft.htm", "text/html"),
        ("draft.css", "text/css"),
        ("draft.csv", "text/csv"),
        ("draft.rst", "text/x-rst"),
        ("draft.py", "text/x-python"),
        ("draft.js", "text/javascript"),
        ("draft.mjs", "text/javascript"),
        ("draft.cjs", "text/javascript"),
        ("draft.json", "application/json"),
        ("draft.xml", "application/xml"),
        ("draft.yaml", "application/yaml"),
        ("draft.yml", "application/yaml"),
        ("draft.toml", "application/toml"),
    ],
)
def test_infers_media_type_from_fixed_extension_mapping(
    artifact_name: str,
    expected: str,
) -> None:
    assert resolve_artifact_media_type(artifact_name) == expected


@pytest.mark.parametrize(
    "artifact_name",
    ["README.MD", "path/to/DRAFT.MD", r"path\to\DRAFT.MD"],
)
def test_inference_is_case_insensitive_and_path_style_independent(
    artifact_name: str,
) -> None:
    assert resolve_artifact_media_type(artifact_name) == "text/markdown"


@pytest.mark.parametrize(
    "artifact_name",
    ["artifact", "stdin", "README"],
)
def test_missing_extension_falls_back_to_text_plain(
    artifact_name: str,
) -> None:
    assert resolve_artifact_media_type(artifact_name) == "text/plain"


@pytest.mark.parametrize(
    "artifact_name",
    ["draft.unknown", "localhost-key.pem", ".env", "draft."],
)
def test_unknown_extension_requires_explicit_media_type(
    artifact_name: str,
) -> None:
    with pytest.raises(ArtifactMediaTypeError, match="provide an explicit"):
        resolve_artifact_media_type(artifact_name)


def test_explicit_media_type_allows_unknown_extension() -> None:
    assert (
        resolve_artifact_media_type("localhost-key.pem", "text/plain") == "text/plain"
    )


@pytest.mark.parametrize(
    ("explicit", "expected"),
    [
        (" TEXT/MARKDOWN ", "text/markdown"),
        ("text/x-custom", "text/x-custom"),
        ("application/json", "application/json"),
        ("application/problem+json", "application/problem+json"),
        ("application/xml", "application/xml"),
        ("application/atom+xml", "application/atom+xml"),
        ("application/yaml", "application/yaml"),
        ("application/x-yaml", "application/yaml"),
        ("application/toml", "application/toml"),
    ],
)
def test_normalizes_supported_explicit_media_types(
    explicit: str,
    expected: str,
) -> None:
    assert resolve_artifact_media_type("artifact.png", explicit) == expected


@pytest.mark.parametrize(
    "explicit",
    [
        "",
        "   ",
        "text",
        "text/",
        "/plain",
        "text/plain/extra",
        "text/*",
        "*/plain",
        "text/plain; charset=utf-8",
        "text /plain",
        "tëxt/plain",
        "text/plain\nmalicious",
    ],
)
def test_rejects_malformed_explicit_media_types(explicit: str) -> None:
    with pytest.raises(ArtifactMediaTypeError, match="bare ASCII type/subtype"):
        resolve_artifact_media_type("artifact.txt", explicit)


@pytest.mark.parametrize(
    "explicit",
    [
        "application/octet-stream",
        "application/pdf",
        "application/zip",
        "image/png",
        "audio/mpeg",
        "video/mp4",
        "font/woff2",
        "model/gltf+json",
    ],
)
def test_rejects_unsupported_non_textual_media_types(explicit: str) -> None:
    with pytest.raises(ArtifactMediaTypeError, match="decoded textual artifacts"):
        resolve_artifact_media_type("artifact.txt", explicit)


def test_explicit_media_type_wins_over_filename_inference() -> None:
    assert (
        resolve_artifact_media_type("artifact.json", "text/markdown") == "text/markdown"
    )


@pytest.mark.parametrize("artifact_name", ["", "   ", None, 42])
def test_requires_non_empty_artifact_name(artifact_name: object) -> None:
    with pytest.raises(ArtifactMediaTypeError, match="artifact_name"):
        resolve_artifact_media_type(artifact_name)  # type: ignore[arg-type]
