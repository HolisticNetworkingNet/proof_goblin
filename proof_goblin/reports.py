# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Provider-neutral rendering for distributable review reports."""

from __future__ import annotations

import html
from enum import StrEnum
from typing import Mapping, Protocol

from proof_goblin.observations import ReviewResult


class ReportRenderError(ValueError):
    """Raised when a report cannot be rendered as requested."""


class ReportFormat(StrEnum):
    """Supported report presentation and interchange formats."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


class ReportRenderer(Protocol):
    """Render a validated review result without executing a review."""

    def render(
        self,
        result: ReviewResult,
        *,
        include_prompt: bool = False,
    ) -> str:
        """Return the complete rendered report."""


class TextReportRenderer:
    """Render a plain-text report suitable for a terminal."""

    def render(
        self,
        result: ReviewResult,
        *,
        include_prompt: bool = False,
    ) -> str:
        _reject_prompt_in_presentation(include_prompt, ReportFormat.TEXT)
        lines = [
            result.review.title,
            "=" * len(result.review.title),
            result.review.description,
            "",
            f"Review ID: {result.review.name}",
            f"Proof Lens: {result.review.lens}",
            f"Mission: {result.review.mission}",
            f"Review Protocol: {result.review.protocol}",
            f"Output Schema: {result.review.output_schema}",
            f"Artifact: {result.prompt.artifact_name}",
            f"Artifact media type: {result.prompt.artifact_media_type}",
            f"Artifact SHA-256: {result.prompt.artifact_sha256}",
            f"Created: {_format_created_at(result)}",
            f"Provider: {result.provider}",
            f"Model: {result.model}",
            f"Response: {result.response_id or '-'}",
            f"Observations: {len(result.observations)}",
        ]
        for index, observation in enumerate(result.observations, start=1):
            lines.extend(
                [
                    "",
                    f"{index}. {observation.question}",
                    f"   Evidence: {observation.evidence}",
                ]
            )
        return "\n".join(lines) + "\n"


class JsonReportRenderer:
    """Render the canonical versioned result record as JSON."""

    def render(
        self,
        result: ReviewResult,
        *,
        include_prompt: bool = False,
    ) -> str:
        return result.to_json(include_prompt=include_prompt) + "\n"


class MarkdownReportRenderer:
    """Render a repository-friendly Markdown report."""

    def render(
        self,
        result: ReviewResult,
        *,
        include_prompt: bool = False,
    ) -> str:
        _reject_prompt_in_presentation(include_prompt, ReportFormat.MARKDOWN)
        lines = [
            f"# {_markdown_inline(result.review.title)}",
            "",
            _markdown_inline(result.review.description),
            "",
            "## Review details",
            "",
            f"- **Review ID:** {_markdown_code(result.review.name)}",
            f"- **Proof Lens:** {_markdown_code(result.review.lens)}",
            f"- **Mission:** {_markdown_code(result.review.mission)}",
            f"- **Review Protocol:** {_markdown_code(result.review.protocol)}",
            f"- **Output Schema:** {_markdown_code(result.review.output_schema)}",
            f"- **Artifact:** {_markdown_code(result.prompt.artifact_name)}",
            f"- **Media type:** {_markdown_code(result.prompt.artifact_media_type)}",
            f"- **Artifact SHA-256:** {_markdown_code(result.prompt.artifact_sha256)}",
            f"- **Created:** {_markdown_inline(_format_created_at(result))}",
            f"- **Provider:** {_markdown_code(result.provider)}",
            f"- **Model:** {_markdown_code(result.model)}",
            f"- **Response:** {_markdown_code(result.response_id or '-')}",
            f"- **Observations:** {len(result.observations)}",
            "",
            "## Observations",
        ]
        if not result.observations:
            lines.extend(["", "No observations were reported."])
        for index, observation in enumerate(result.observations, start=1):
            lines.extend(
                [
                    "",
                    f"### Observation {index}",
                    "",
                    "**Question**",
                    "",
                    _markdown_quote(observation.question),
                    "",
                    "**Evidence**",
                    "",
                    _markdown_quote(observation.evidence),
                ]
            )
        return "\n".join(lines) + "\n"


class HtmlReportRenderer:
    """Render a self-contained, safely escaped HTML report."""

    def render(
        self,
        result: ReviewResult,
        *,
        include_prompt: bool = False,
    ) -> str:
        _reject_prompt_in_presentation(include_prompt, ReportFormat.HTML)
        title = _html(result.review.title)
        observations = "\n".join(
            _render_html_observation(index, observation.question, observation.evidence)
            for index, observation in enumerate(result.observations, start=1)
        )
        if not observations:
            observations = '      <p class="empty">No observations were reported.</p>'
        created_at = _format_created_at(result)
        details = (
            ("Review ID", result.review.name),
            ("Proof Lens", result.review.lens),
            ("Mission", result.review.mission),
            ("Review Protocol", result.review.protocol),
            ("Output Schema", result.review.output_schema),
            ("Artifact", result.prompt.artifact_name),
            ("Media type", result.prompt.artifact_media_type),
            ("Artifact SHA-256", result.prompt.artifact_sha256),
            ("Created", created_at),
            ("Provider", result.provider),
            ("Model", result.model),
            ("Response", result.response_id or "-"),
            ("Observations", str(len(result.observations))),
        )
        detail_rows = "\n".join(
            f"        <dt>{_html(label)}</dt><dd>{_html(value)}</dd>"
            for label, value in details
        )
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f1e8; color: #25251f; }}
    main {{ max-width: 54rem; margin: 0 auto; padding: 3rem 1.5rem 5rem; }}
    header, section {{ background: #fffdf7; border: 1px solid #d8d2c2; border-radius: .75rem; padding: 1.5rem; box-shadow: 0 .25rem 1rem #2f2a1f12; }}
    header {{ border-top: .4rem solid #607744; }}
    h1, h2, h3 {{ line-height: 1.2; }}
    h1 {{ margin-top: 0; }}
    section {{ margin-top: 1.25rem; }}
    dl {{ display: grid; grid-template-columns: minmax(9rem, auto) 1fr; gap: .5rem 1rem; }}
    dt {{ font-weight: 700; }}
    dd {{ margin: 0; overflow-wrap: anywhere; }}
    .observation p {{ white-space: pre-wrap; }}
    .evidence {{ border-left: .25rem solid #9e6f36; padding-left: 1rem; }}
    .empty {{ font-style: italic; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #1d1f1a; color: #ece9df; }}
      header, section {{ background: #292c25; border-color: #4c5144; box-shadow: none; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <p>{_html(result.review.description)}</p>
      <dl>
{detail_rows}
      </dl>
    </header>
    <section aria-labelledby="observations-heading">
      <h2 id="observations-heading">Observations</h2>
{observations}
    </section>
  </main>
</body>
</html>
"""


_REPORT_RENDERERS: Mapping[ReportFormat, ReportRenderer] = {
    ReportFormat.TEXT: TextReportRenderer(),
    ReportFormat.JSON: JsonReportRenderer(),
    ReportFormat.MARKDOWN: MarkdownReportRenderer(),
    ReportFormat.HTML: HtmlReportRenderer(),
}


def render_report(
    result: ReviewResult,
    report_format: ReportFormat | str = ReportFormat.TEXT,
    *,
    include_prompt: bool = False,
) -> str:
    """Render a review result in a supported format.

    Prompt inclusion is an explicit JSON-only archival option. Presentation
    formats never contain prompt text or the reviewed artifact body.
    """

    try:
        selected_format = ReportFormat(report_format)
    except ValueError as exc:
        choices = ", ".join(item.value for item in ReportFormat)
        raise ReportRenderError(
            f"Unknown report format {report_format!r}; choose from: {choices}"
        ) from exc
    if include_prompt and selected_format is not ReportFormat.JSON:
        _reject_prompt_in_presentation(include_prompt, selected_format)
    return _REPORT_RENDERERS[selected_format].render(
        result,
        include_prompt=include_prompt,
    )


def _reject_prompt_in_presentation(
    include_prompt: bool,
    report_format: ReportFormat,
) -> None:
    if include_prompt:
        raise ReportRenderError(
            f"Prompt text can only be included in JSON, not {report_format.value}"
        )


def _format_created_at(result: ReviewResult) -> str:
    return result.created_at.isoformat(timespec="seconds")


def _markdown_inline(value: str) -> str:
    return html.escape(" ".join(value.splitlines()), quote=False)


def _markdown_code(value: str) -> str:
    escaped = html.escape(" ".join(value.splitlines()), quote=False)
    return f"`{escaped.replace('`', '&#96;')}`"


def _markdown_quote(value: str) -> str:
    escaped = html.escape(value, quote=False)
    return "\n".join(f"> {line}" if line else ">" for line in escaped.splitlines())


def _html(value: str) -> str:
    return html.escape(value, quote=True)


def _render_html_observation(index: int, question: str, evidence: str) -> str:
    return f"""      <article class="observation">
        <h3>{index}. {_html(question)}</h3>
        <p class="evidence"><strong>Evidence:</strong> {_html(evidence)}</p>
      </article>"""
