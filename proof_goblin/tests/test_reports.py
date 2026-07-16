from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
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
        created_at=datetime(2026, 7, 14, 9, 30, tzinfo=UTC),
    )


def expected_display_created_at(result: ReviewResult) -> str:
    created_at = result.created_at.astimezone()
    hour = created_at.strftime("%I").lstrip("0") or "0"
    timezone_name = created_at.tzname() or created_at.strftime("UTC%z")
    return (
        f"{created_at.strftime('%B')} {created_at.day}, {created_at.year} "
        f"at {hour}:{created_at.strftime('%M %p')} {timezone_name}"
    )


def test_text_report_contains_content_and_provenance() -> None:
    result = make_result()

    rendered = render_report(result, ReportFormat.TEXT)

    assert rendered.startswith("Restaurant Homepage Review\n")
    assert expected_display_created_at(result) in rendered
    assert "Evaluates whether a first-time diner" in rendered
    assert "Review ID: homepage_first_pass" in rendered
    assert "Proof Lens: first_time_diner" in rendered
    assert "Configuration: restaurants" in rendered
    assert "Artifact: homepage.html" in rendered
    assert (
        f"Created: {result.created_at.astimezone().isoformat(timespec='seconds')}"
        in rendered
    )
    assert "Provider: openai" in rendered
    assert "Input tokens: 100" in rendered
    assert "Output tokens: 20" in rendered
    assert "Total tokens: 120" in rendered
    assert "Observations: 1" in rendered
    assert "1. Where are the hours?" in rendered
    assert result.prompt.config_sha256 not in rendered
    assert result.prompt.artifact_sha256 not in rendered
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
    result = replace(
        result,
        prompt=replace(result.prompt, artifact_name="home|page.html"),
    )

    rendered = render_report(result, ReportFormat.MARKDOWN)

    assert rendered.startswith("# Restaurant Homepage Review\n")
    assert f"*{expected_display_created_at(result)}*" in rendered
    assert "Evaluates whether a first-time diner can plan a visit." in rendered
    assert "## Review details" in rendered
    assert "| Key | Value | Key | Value |" in rendered
    assert "| **Review ID** | `homepage_first_pass` |" in rendered
    assert "**Artifact** | `home&#124;page.html`" in rendered
    assert "**Input tokens** | `100`" in rendered
    assert "**Total tokens** | `120`" in rendered
    assert "colspan" not in rendered
    assert "background:" not in rendered
    assert "## Observations" in rendered
    assert "### Observation 1" in rendered
    assert "> Where are the hours?" in rendered
    assert "> No hours appear on the homepage." in rendered
    assert result.prompt.user not in rendered
    assert "Secret reviewed content" not in rendered
    assert result.prompt.config_sha256 not in rendered
    assert result.prompt.artifact_sha256 not in rendered


def test_markdown_report_neutralizes_links_and_images_from_untrusted_values() -> None:
    result = make_result()
    result = replace(
        result,
        review=replace(
            result.review,
            title="[Linked review](https://example.com)",
            description="![Remote image](https://example.com/tracker.png)",
        ),
        observations=(
            Observation(
                question="Could [this link][reference] load?",
                evidence=(
                    "The `.pgcfg` mentions ![another image](https://example.com/x).\n"
                    "[reference]: https://example.com"
                ),
            ),
        ),
    )

    rendered = render_report(result, ReportFormat.MARKDOWN)

    assert "[Linked review](" not in rendered
    assert "![Remote image](" not in rendered
    assert "[this link][reference]" not in rendered
    assert "![another image](" not in rendered
    assert "&#91;Linked review&#93;" in rendered
    assert "&#91;reference&#93;" in rendered
    assert "The `.pgcfg` mentions" in rendered


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
    local_created_at = result.created_at.astimezone().isoformat(timespec="seconds")
    assert f'<time datetime="{local_created_at}">' in rendered
    assert expected_display_created_at(result) in rendered
    assert '<table class="report-details">' in rendered
    assert "<caption>Review details</caption>" in rendered
    assert "<th>Key</th><th>Value</th><th>Key</th><th>Value</th>" in rendered
    assert '<th scope="row" class="detail-key">' in rendered
    assert "colspan" not in rendered
    assert "background:#354222" not in rendered
    assert "Input tokens" in rendered
    assert "100" in rendered
    assert "<script>Review</script>" not in rendered
    assert "&lt;script&gt;Review&lt;/script&gt;" in rendered
    assert "&lt;img src=x onerror=&quot;" in rendered
    assert "&lt;unsafe&gt;" in rendered
    assert "Owner &amp; reader &lt;needs&gt;" in rendered
    assert result.prompt.user not in rendered
    assert "Secret reviewed content" not in rendered
    assert result.prompt.config_sha256 not in rendered
    assert result.prompt.artifact_sha256 not in rendered


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
