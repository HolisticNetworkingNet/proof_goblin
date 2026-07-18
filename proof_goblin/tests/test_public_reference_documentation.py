"""Keep public API and versioned-schema references aligned with the code."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from proof_goblin import (
    PROMPT_DOCUMENT_FORMAT,
    PROMPT_DOCUMENT_SCHEMA_VERSION,
    REVIEW_RESULT_FORMAT,
    REVIEW_RESULT_SCHEMA_VERSION,
    HtmlReportRenderer,
    JsonReportRenderer,
    MarkdownReportRenderer,
    PromptFormat,
    ReportFormat,
    ReportRenderer,
    TextReportRenderer,
    render_prompt,
    render_report,
    resolve_artifact_media_type,
)
from proof_goblin.artifacts import _MEDIA_TYPES_BY_EXTENSION

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_MEDIA_TYPES_DOC = PACKAGE_ROOT / "docs" / "artifact-media-types.md"
REPORT_FORMATS_DOC = PACKAGE_ROOT / "docs" / "report-formats.md"
PROMPT_SCHEMA = PACKAGE_ROOT / "schemas" / "prompt.v1.schema.json"
RESULT_SCHEMA = PACKAGE_ROOT / "schemas" / "review-result.v1.schema.json"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_artifact_reference_tracks_resolver_contract_and_mapping() -> None:
    documentation = _read(ARTIFACT_MEDIA_TYPES_DOC)
    signature = inspect.signature(resolve_artifact_media_type)

    assert tuple(signature.parameters) == ("artifact_name", "explicit_media_type")
    assert "`artifact_name`" in documentation
    assert "`explicit_media_type`" in documentation
    for extension, media_type in _MEDIA_TYPES_BY_EXTENSION.items():
        assert f"`{extension}`" in documentation
        assert f"`{media_type}`" in documentation


def test_report_reference_tracks_public_rendering_contracts() -> None:
    documentation = _read(REPORT_FORMATS_DOC)

    assert tuple(inspect.signature(render_report).parameters) == (
        "result",
        "report_format",
        "include_prompt",
        "limits",
    )
    assert tuple(inspect.signature(render_prompt).parameters) == (
        "prompt",
        "prompt_format",
    )
    assert tuple(inspect.signature(ReportRenderer.render).parameters) == (
        "self",
        "result",
        "include_prompt",
        "limits",
    )
    for renderer in (
        TextReportRenderer,
        JsonReportRenderer,
        MarkdownReportRenderer,
        HtmlReportRenderer,
    ):
        assert renderer.__name__ in documentation
        assert inspect.signature(renderer.render) == inspect.signature(
            ReportRenderer.render
        )
    for value in {
        *(item.value for item in ReportFormat),
        *(item.value for item in PromptFormat),
    }:
        assert f"`{value}`" in documentation


def test_report_reference_tracks_published_schema_identities() -> None:
    documentation = _read(REPORT_FORMATS_DOC)
    prompt_schema = json.loads(_read(PROMPT_SCHEMA))
    result_schema = json.loads(_read(RESULT_SCHEMA))

    expected = (
        (
            prompt_schema,
            PROMPT_DOCUMENT_FORMAT,
            PROMPT_DOCUMENT_SCHEMA_VERSION,
            PROMPT_SCHEMA.name,
        ),
        (
            result_schema,
            REVIEW_RESULT_FORMAT,
            REVIEW_RESULT_SCHEMA_VERSION,
            RESULT_SCHEMA.name,
        ),
    )
    for schema, format_identifier, schema_version, filename in expected:
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["properties"]["format"]["const"] == format_identifier
        assert schema["properties"]["schema_version"]["const"] == schema_version
        assert filename in documentation
        assert f"`{format_identifier}`" in documentation
        assert f"`{schema_version}`" in documentation
        assert f"`{schema['$id']}`" in documentation
