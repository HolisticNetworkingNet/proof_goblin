# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Provider-neutral rendering for distributable review reports."""

from __future__ import annotations

import html
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, Protocol

from proof_goblin.observations import (
    REVIEW_RESULT_FORMAT,
    REVIEW_RESULT_SCHEMA_VERSION,
    ReviewResult,
)


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


@dataclass(frozen=True, slots=True)
class _ReportDetail:
    """One metadata field shared by every human-facing report."""

    key: str
    value: str


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
            _format_display_created_at(result),
            result.review.description,
            "",
            "Review details:",
        ]
        for detail_row in _report_detail_rows(result):
            for detail in detail_row:
                lines.append(f"  {detail.key}: {detail.value}")
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
            f"*{_markdown_inline(_format_display_created_at(result))}*",
            "",
            _markdown_inline(result.review.description),
            "",
            "## Review details",
            "",
            _render_markdown_detail_table(_report_detail_rows(result)),
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
        detail_table = _render_html_detail_table(_report_detail_rows(result))
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
    .created {{ margin-top: -.5rem; font-weight: 600; }}
    section {{ margin-top: 1.25rem; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 1.5rem; }}
    caption {{ text-align: left; font-size: 1.35rem; font-weight: 700; margin-bottom: .5rem; }}
    th, td {{ border-top: 1px solid #d8d2c2; padding: .55rem .7rem; text-align: left; vertical-align: top; }}
    .detail-key {{ width: 16%; }}
    .detail-value {{ width: 34%; }}
    td {{ overflow-wrap: anywhere; }}
    .observation p {{ white-space: pre-wrap; }}
    .evidence {{ border-left: .25rem solid #9e6f36; padding-left: 1rem; }}
    .empty {{ font-style: italic; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #1d1f1a; color: #ece9df; }}
      header, section {{ background: #292c25; border-color: #4c5144; box-shadow: none; }}
      th, td {{ border-color: #4c5144; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <p class="created"><time datetime="{_html(_format_created_at(result))}">{_html(_format_display_created_at(result))}</time></p>
      <p>{_html(result.review.description)}</p>
{detail_table}
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
    return result.created_at.astimezone().isoformat(timespec="seconds")


def _format_display_created_at(result: ReviewResult) -> str:
    created_at = result.created_at.astimezone()
    hour = created_at.strftime("%I").lstrip("0") or "0"
    timezone_name = created_at.tzname() or created_at.strftime("UTC%z")
    return (
        f"{created_at.strftime('%B')} {created_at.day}, {created_at.year} "
        f"at {hour}:{created_at.strftime('%M %p')} {timezone_name}"
    )


def _report_detail_rows(
    result: ReviewResult,
) -> tuple[tuple[_ReportDetail, ...], ...]:
    details = (
        _ReportDetail("Review ID", result.review.name),
        _ReportDetail("Proof Lens", result.review.lens),
        _ReportDetail("Mission", result.review.mission),
        _ReportDetail("Review Protocol", result.review.protocol),
        _ReportDetail("Output Schema", result.review.output_schema),
        _ReportDetail("Configuration", result.prompt.config_name),
        _ReportDetail("Configuration version", result.prompt.config_version),
        _ReportDetail("Artifact", result.prompt.artifact_name),
        _ReportDetail("Media type", result.prompt.artifact_media_type),
        _ReportDetail("Created", _format_created_at(result)),
        _ReportDetail("Provider", result.provider),
        _ReportDetail("Model", result.model),
        _ReportDetail("Response ID", _display_value(result.response_id)),
        _ReportDetail("Input tokens", _display_value(result.usage.input_tokens)),
        _ReportDetail("Output tokens", _display_value(result.usage.output_tokens)),
        _ReportDetail("Total tokens", _display_value(result.usage.total_tokens)),
        _ReportDetail("Observations", str(len(result.observations))),
        _ReportDetail("Result format", REVIEW_RESULT_FORMAT),
        _ReportDetail("Schema version", REVIEW_RESULT_SCHEMA_VERSION),
    )
    return tuple(tuple(details[index : index + 2]) for index in range(0, len(details), 2))


def _display_value(value: object | None) -> str:
    return "-" if value is None else str(value)


def _markdown_inline(value: str) -> str:
    return html.escape(" ".join(value.splitlines()), quote=False)


def _markdown_code(value: str) -> str:
    escaped = _markdown_inline(value).replace("|", "&#124;")
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


def _render_markdown_detail_table(
    detail_rows: tuple[tuple[_ReportDetail, ...], ...],
) -> str:
    rows = [
        "| Key | Value | Key | Value |",
        "| :-- | :-- | :-- | :-- |",
    ]
    for details in detail_rows:
        cells: list[str] = []
        for detail in details:
            cells.extend([f"**{_markdown_inline(detail.key)}**", _markdown_code(detail.value)])
        while len(cells) < 4:
            cells.append("")
        rows.append(f"| {' | '.join(cells)} |")
    return "\n".join(rows)


def _render_html_detail_table(
    detail_rows: tuple[tuple[_ReportDetail, ...], ...],
) -> str:
    rows = []
    for details in detail_rows:
        cells = []
        for detail in details:
            cells.extend(
                [
                    f'<th scope="row" class="detail-key">{_html(detail.key)}</th>',
                    '<td class="detail-value">'
                    f"<code>{_html(detail.value)}</code></td>",
                ]
            )
        if len(details) == 1:
            cells.extend(["<th></th>", "<td></td>"])
        rows.append(f"  <tr>{''.join(cells)}</tr>")
    rendered_rows = "\n".join(rows)
    return (
        '<table class="report-details">\n'
        "  <caption>Review details</caption>\n"
        "  <thead><tr><th>Key</th><th>Value</th>"
        "<th>Key</th><th>Value</th></tr></thead>\n"
        "  <tbody>\n"
        f"{rendered_rows}\n"
        "  </tbody>\n"
        "</table>"
    )
