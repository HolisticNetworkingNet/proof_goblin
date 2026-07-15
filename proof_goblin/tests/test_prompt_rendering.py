# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from proof_goblin import (
    Config,
    Prompt,
    PromptBuilder,
    PromptFormat,
    PromptRenderError,
    render_prompt,
)

EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"
PROMPT_SCHEMA = Path(__file__).parents[1] / "schemas" / "prompt.v1.schema.json"


@pytest.fixture
def prompt() -> Prompt:
    return PromptBuilder(Config.load(EXAMPLE_CONFIG)).build(
        review="homepage_first_pass",
        artifact="<script>alert(1)</script>\n```\nartifact fence",
        artifact_name="café-homepage.html",
        artifact_media_type="text/html",
    )


def test_text_prompt_preserves_terminal_representation(prompt) -> None:
    assert render_prompt(prompt, PromptFormat.TEXT) == f"{prompt}\n"


def test_json_prompt_is_versioned_and_contains_complete_prompt(prompt) -> None:
    record = json.loads(render_prompt(prompt, PromptFormat.JSON))

    assert record["format"] == "proof-goblin-prompt"
    assert record["schema_version"] == "1.0"
    assert record["review"]["name"] == "homepage_first_pass"
    assert record["config"]["name"] == "restaurants"
    assert record["config"]["version"] == "0.2.0"
    assert record["artifact"]["name"] == "café-homepage.html"
    assert record["prompt"]["system"] == prompt.system
    assert record["prompt"]["user"] == prompt.user
    schema = json.loads(PROMPT_SCHEMA.read_text(encoding="utf-8"))
    validate(record, schema)


def test_markdown_prompt_contains_warning_and_safe_dynamic_fences(prompt) -> None:
    rendered = render_prompt(prompt, PromptFormat.MARKDOWN)

    assert rendered.startswith("# Proof Goblin Prompt\n")
    assert "**Sensitive content:**" in rendered
    assert "`café-homepage.html`" in rendered
    assert "## System" in rendered
    assert "## User" in rendered
    assert "````text\n" in rendered
    assert "<script>alert(1)</script>" in rendered


def test_html_prompt_is_standalone_and_escapes_complete_prompt(prompt) -> None:
    rendered = render_prompt(prompt, PromptFormat.HTML)

    assert rendered.startswith("<!doctype html>\n")
    assert "Sensitive content" in rendered
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "café-homepage.html" in rendered
    assert prompt.system not in rendered


def test_unknown_prompt_format_is_rejected(prompt) -> None:
    with pytest.raises(PromptRenderError, match="Unknown prompt format"):
        render_prompt(prompt, "pdf")
