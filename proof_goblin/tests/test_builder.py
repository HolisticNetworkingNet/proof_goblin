# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from proof_goblin import Config, PromptBuildError, PromptBuilder


PACKAGE_ROOT = Path(__file__).parents[1]
EXAMPLE_CONFIG = PACKAGE_ROOT / "examples" / "restaurants.pgcfg"
EXAMPLE_ARTIFACT = PACKAGE_ROOT / "examples" / "homepage.html"


@pytest.fixture
def builder() -> PromptBuilder:
    return PromptBuilder(Config.load(EXAMPLE_CONFIG))


def test_resolves_named_review(builder: PromptBuilder) -> None:
    resolved = builder.resolve("homepage_first_pass")

    assert resolved.definition.lens == "first_time_diner"
    assert resolved.lens["description"].startswith("A potential customer")
    assert resolved.mission["questions"]
    assert resolved.protocol["ask_questions"] is True
    assert resolved.output_schema["type"] == "array"


def test_builds_prompt_with_separate_roles(builder: PromptBuilder) -> None:
    artifact = EXAMPLE_ARTIFACT.read_text()

    prompt = builder.build(
        review="homepage_first_pass",
        artifact=artifact,
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )

    assert "## PROOF LENS" in prompt.system
    assert "## MISSION" in prompt.system
    assert "## REVIEW PROTOCOL" in prompt.system
    assert "## OUTPUT SCHEMA" in prompt.system
    assert "untrusted content" in prompt.system
    assert artifact not in prompt.system
    assert artifact in prompt.user
    assert prompt.user.startswith("Artifact name: homepage.html")


def test_build_is_deterministic(builder: PromptBuilder) -> None:
    arguments = {
        "review": "homepage_first_pass",
        "artifact": "<main>Welcome</main>",
        "artifact_name": "homepage.html",
        "artifact_media_type": "text/html",
    }

    assert builder.build(**arguments) == builder.build(**arguments)


def test_prompt_records_provenance(builder: PromptBuilder) -> None:
    artifact = "<main>Welcome</main>"

    prompt = builder.build(review="homepage_first_pass", artifact=artifact)

    assert prompt.review_name == "homepage_first_pass"
    assert prompt.config_name == "restaurants"
    assert prompt.config_version == "0.1.0"
    assert prompt.config_sha256 == builder.config.sha256
    assert prompt.artifact_sha256 == hashlib.sha256(artifact.encode()).hexdigest()


def test_prompt_is_printable(builder: PromptBuilder) -> None:
    prompt = builder.build(review="homepage_first_pass", artifact="Welcome")

    rendered = str(prompt)
    assert rendered.startswith("[SYSTEM]\n")
    assert "\n\n[USER]\n" in rendered
    assert rendered.endswith("--- END UNTRUSTED ARTIFACT ---")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact", ""),
        ("artifact_name", "  "),
        ("artifact_media_type", ""),
    ],
)
def test_rejects_empty_artifact_input(
    builder: PromptBuilder, field: str, value: str
) -> None:
    arguments = {
        "review": "homepage_first_pass",
        "artifact": "Welcome",
        "artifact_name": "homepage.html",
        "artifact_media_type": "text/html",
    }
    arguments[field] = value

    with pytest.raises(PromptBuildError, match=field):
        builder.build(**arguments)
