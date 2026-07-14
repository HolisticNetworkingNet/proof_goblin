# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

from proof_goblin import (
    Config,
    Observation,
    PromptBuilder,
    ReportFormat,
    ReportRenderError,
    ReviewAttribution,
    ReviewResult,
    TokenUsage,
    render_report,
)


EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"


def make_result() -> ReviewResult:
    prompt = PromptBuilder(Config.load(EXAMPLE_CONFIG)).build(
        review="homepage_first_pass",
        artifact="<main>Secret reviewed content</main>",
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )
    return ReviewResult(
        observations=(
            Observation(
                question="Where are the hours?",
                evidence="No hours appear on the homepage.",
            ),
        ),
        prompt=prompt,
        review=ReviewAttribution(
            name="homepage_first_pass",
            title="Restaurant Homepage Review",
            description="Evaluates whether a first-time diner can plan a visit.",
            lens="first_time_diner",
            mission="homepage_clarity",
            protocol="questions_only",
            output_schema="observation.v1",
        ),
        provider="openai",
        model="gpt-test",
        response_id="resp_report_test",
        usage=TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
        raw_output={
            "observations": [
                {
                    "question": "Where are the hours?",
                    "evidence": "No hours appear on the homepage.",
                }
            ]
        },
        created_at=datetime(2026, 7, 14, 9, 30, tzinfo=timezone.utc),
    )


def test_text_report_contains_content_and_provenance() -> None:
    result = make_result()

    rendered = render_report(result, ReportFormat.TEXT)

    assert rendered.startswith("Restaurant Homepage Review\n")
    assert "Review ID: homepage_first_pass" in rendered
    assert "Proof Lens: first_time_diner" in rendered
    assert "Artifact: homepage.html" in rendered
    assert "Created: 2026-07-14T09:30:00+00:00" in rendered
    assert "Provider: openai" in rendered
    assert "Observations: 1" in rendered
    assert "1. Where are the hours?" in rendered
    assert result.prompt.user not in rendered
    assert "Secret reviewed content" not in rendered


def test_json_report_is_the_canonical_result_record() -> None:
    result = make_result()

    rendered = render_report(result, "json")

    assert json.loads(rendered) == result.to_dict()
    assert "prompt" not in json.loads(rendered)


def test_json_report_can_explicitly_include_prompt() -> None:
    result = make_result()

    rendered = render_report(result, ReportFormat.JSON, include_prompt=True)

    assert json.loads(rendered)["prompt"]["user"] == result.prompt.user


def test_markdown_report_is_structured_and_excludes_artifact_content() -> None:
    result = make_result()

    rendered = render_report(result, ReportFormat.MARKDOWN)

    assert rendered.startswith("# Restaurant Homepage Review\n")
    assert "## Review details" in rendered
    assert "## Observations" in rendered
    assert "### Observation 1" in rendered
    assert "> Where are the hours?" in rendered
    assert "> No hours appear on the homepage." in rendered
    assert result.prompt.user not in rendered
    assert "Secret reviewed content" not in rendered


def test_html_report_is_standalone_and_escapes_untrusted_values() -> None:
    result = make_result()
    result = replace(
        result,
        prompt=replace(
            result.prompt,
            artifact_name='<img src=x onerror="alert(1)">',
        ),
        review=replace(
            result.review,
            title="<script>Review</script>",
            description="Owner & reader <needs>",
        ),
        observations=(
            Observation(
                question="Could <script>alert(1)</script> run?",
                evidence='The text says "<unsafe>" & more.',
            ),
        ),
    )

    rendered = render_report(result, ReportFormat.HTML)

    assert rendered.startswith("<!doctype html>\n")
    assert '<meta charset="utf-8">' in rendered
    assert "<style>" in rendered
    assert "<script>Review</script>" not in rendered
    assert "&lt;script&gt;Review&lt;/script&gt;" in rendered
    assert "&lt;img src=x onerror=&quot;" in rendered
    assert "&lt;unsafe&gt;" in rendered
    assert "Owner &amp; reader &lt;needs&gt;" in rendered
    assert result.prompt.user not in rendered
    assert "Secret reviewed content" not in rendered


@pytest.mark.parametrize(
    "report_format",
    [ReportFormat.TEXT, ReportFormat.MARKDOWN, ReportFormat.HTML],
)
def test_presentation_reports_reject_prompt_inclusion(
    report_format: ReportFormat,
) -> None:
    with pytest.raises(ReportRenderError, match="only be included in JSON"):
        render_report(make_result(), report_format, include_prompt=True)


def test_unknown_report_format_is_rejected() -> None:
    with pytest.raises(ReportRenderError, match="Unknown report format"):
        render_report(make_result(), "pdf")


@pytest.mark.parametrize(
    ("report_format", "expected"),
    [
        (ReportFormat.TEXT, "Observations: 0"),
        (ReportFormat.MARKDOWN, "No observations were reported."),
        (ReportFormat.HTML, "No observations were reported."),
    ],
)
def test_presentation_reports_handle_no_observations(
    report_format: ReportFormat,
    expected: str,
) -> None:
    result = replace(make_result(), observations=())

    assert expected in render_report(result, report_format)
