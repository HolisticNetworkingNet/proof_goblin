# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Render assembled prompts for inspection, storage, and sharing."""

from __future__ import annotations

import html
import json
import re
from enum import StrEnum
from typing import Any

from proof_goblin.builder import Prompt

PROMPT_DOCUMENT_FORMAT = "proof-goblin-prompt"
PROMPT_DOCUMENT_SCHEMA_VERSION = "1.0"


class PromptRenderError(ValueError):
    """Raised when an assembled prompt cannot be rendered as requested."""


class PromptFormat(StrEnum):
    """Supported assembled-prompt formats."""

    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"


def render_prompt(
    prompt: Prompt,
    prompt_format: PromptFormat | str = PromptFormat.TEXT,
) -> str:
    """Render an assembled prompt without contacting a provider.

    Every format contains the complete system and user prompt. The user prompt
    contains the complete artifact and must be handled as sensitive content.
    """

    try:
        selected_format = PromptFormat(prompt_format)
    except ValueError as exc:
        choices = ", ".join(item.value for item in PromptFormat)
        raise PromptRenderError(
            f"Unknown prompt format {prompt_format!r}; choose from: {choices}"
        ) from exc

    if selected_format is PromptFormat.TEXT:
        return str(prompt) + "\n"
    if selected_format is PromptFormat.JSON:
        return _render_json(prompt)
    if selected_format is PromptFormat.MARKDOWN:
        return _render_markdown(prompt)
    return _render_html(prompt)


def _prompt_record(prompt: Prompt) -> dict[str, Any]:
    return {
        "format": PROMPT_DOCUMENT_FORMAT,
        "schema_version": PROMPT_DOCUMENT_SCHEMA_VERSION,
        "review": {"name": prompt.review_name},
        "config": {
            "name": prompt.config_name,
            "version": prompt.config_version,
            "sha256": prompt.config_sha256,
        },
        "artifact": {
            "name": prompt.artifact_name,
            "media_type": prompt.artifact_media_type,
            "sha256": prompt.artifact_sha256,
        },
        "prompt": {
            "system": prompt.system,
            "user": prompt.user,
        },
    }


def _render_json(prompt: Prompt) -> str:
    return (
        json.dumps(
            _prompt_record(prompt),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _render_markdown(prompt: Prompt) -> str:
    details = (
        ("Review ID", prompt.review_name),
        ("Configuration", prompt.config_name),
        ("Configuration version", prompt.config_version),
        ("Artifact", prompt.artifact_name),
        ("Media type", prompt.artifact_media_type),
        ("Document format", PROMPT_DOCUMENT_FORMAT),
        ("Schema version", PROMPT_DOCUMENT_SCHEMA_VERSION),
    )
    rows = ["| Key | Value |", "| :-- | :-- |"]
    rows.extend(
        f"| **{_markdown_inline(key)}** | {_markdown_code(value)} |"
        for key, value in details
    )
    return "\n".join(
        [
            "# Proof Goblin Prompt",
            "",
            "**Sensitive content:** This document contains the complete reviewed "
            "artifact.",
            "",
            "## Prompt details",
            "",
            *rows,
            "",
            "## System",
            "",
            _markdown_fence(prompt.system),
            "",
            "## User",
            "",
            _markdown_fence(prompt.user),
            "",
        ]
    )


def _render_html(prompt: Prompt) -> str:
    details = (
        ("Review ID", prompt.review_name),
        ("Configuration", prompt.config_name),
        ("Configuration version", prompt.config_version),
        ("Artifact", prompt.artifact_name),
        ("Media type", prompt.artifact_media_type),
        ("Document format", PROMPT_DOCUMENT_FORMAT),
        ("Schema version", PROMPT_DOCUMENT_SCHEMA_VERSION),
    )
    rows = "\n".join(
        "        <tr>"
        f'<th scope="row">{html.escape(key)}</th>'
        f"<td><code>{html.escape(value)}</code></td>"
        "</tr>"
        for key, value in details
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Proof Goblin Prompt</title>
  <style>
    :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #f4f1e8; color: #25251f; }}
    main {{ max-width: 70rem; margin: 0 auto; padding: 3rem 1.5rem 5rem; }}
    header, section {{
      background: #fffdf7;
      border: 1px solid #d8d2c2;
      border-radius: .75rem;
      padding: 1.5rem;
      margin-bottom: 1.25rem;
    }}
    header {{ border-top: .4rem solid #607744; }}
    h1, h2 {{ line-height: 1.2; }}
    h1 {{ margin-top: 0; }}
    .warning {{
      border-left: .3rem solid #9e6f36;
      padding-left: 1rem;
      font-weight: 650;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      border-top: 1px solid #d8d2c2;
      padding: .55rem .7rem;
      text-align: left;
      vertical-align: top;
    }}
    th {{ width: 14rem; }}
    td {{ overflow-wrap: anywhere; }}
    pre {{
      overflow: auto;
      padding: 1rem;
      background: #f3efe5;
      border-radius: .5rem;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #1d1f1a; color: #ece9df; }}
      header, section {{ background: #292c25; border-color: #4c5144; }}
      th, td {{ border-color: #4c5144; }}
      pre {{ background: #20231e; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Proof Goblin Prompt</h1>
      <p class="warning">
        Sensitive content: this document contains the complete reviewed artifact.
      </p>
      <table>
        <thead><tr><th>Key</th><th>Value</th></tr></thead>
        <tbody>
{rows}
        </tbody>
      </table>
    </header>
    <section aria-labelledby="system-heading">
      <h2 id="system-heading">System</h2>
      <pre><code>{html.escape(prompt.system)}</code></pre>
    </section>
    <section aria-labelledby="user-heading">
      <h2 id="user-heading">User</h2>
      <pre><code>{html.escape(prompt.user)}</code></pre>
    </section>
  </main>
</body>
</html>
"""


def _markdown_inline(value: str) -> str:
    return html.escape(value, quote=False).replace("[", "&#91;").replace("]", "&#93;")


def _markdown_code(value: str) -> str:
    escaped = _markdown_inline(value).replace("|", "&#124;")
    return f"`{escaped.replace('`', '&#96;')}`"


def _markdown_fence(value: str) -> str:
    longest_run = max(
        (len(match.group(0)) for match in re.finditer(r"`+", value)),
        default=0,
    )
    fence = "`" * max(3, longest_run + 1)
    return f"{fence}text\n{value}\n{fence}"
