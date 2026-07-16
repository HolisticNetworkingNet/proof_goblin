from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from proof_goblin import Config, PromptBuilder, PromptBuildError

PACKAGE_ROOT = Path(__file__).parents[1]
EXAMPLE_CONFIG = PACKAGE_ROOT / "examples" / "restaurants.pgcfg"
EXAMPLE_ARTIFACT = PACKAGE_ROOT / "examples" / "homepage.html"

DOCUMENTATION_CONFIG = PACKAGE_ROOT / "configs" / "documentation.pgcfg"


@pytest.fixture
def builder() -> PromptBuilder:
    return PromptBuilder(Config.load(EXAMPLE_CONFIG))


@pytest.fixture
def documentation_builder() -> PromptBuilder:
    return PromptBuilder(Config.load(DOCUMENTATION_CONFIG))


def test_resolves_named_review(builder: PromptBuilder) -> None:
    resolved = builder.resolve("homepage_first_pass")

    assert resolved.definition.title == "Restaurant Homepage Review"
    assert resolved.definition.description.startswith("Evaluates")
    assert resolved.definition.lens == "first_time_diner"
    assert resolved.lens["description"].startswith("A first-visit customer perspective")
    assert resolved.mission["questions"]
    assert resolved.protocol["ask_questions"] is True
    assert resolved.output_schema["type"] == "object"


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
    assert "analytical vantage point" in prompt.system
    assert "never impersonate" in prompt.system
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
    assert prompt.config_version == "0.2.0"
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


@pytest.mark.parametrize(
    (
        "review_name",
        "expected_title",
        "expected_lens",
        "expected_mission",
    ),
    [
        (
            "business_owner_first_pass",
            "Business Owner Documentation Review",
            "business_owner",
            "reader_facing",
        ),
        (
            "django_developer_first_pass",
            "Django Developer Documentation Review",
            "django_python_developer",
            "procedural",
        ),
        (
            "technical_writer_first_pass",
            "Technical Writing Review",
            "technical_writer",
            "procedural",
        ),
        (
            "technical_writer_concept_reference",
            "Technical Writing Concept Reference Review",
            "technical_writer",
            "reference",
        ),
        (
            "django_developer_concept_reference",
            "Developer Concept Reference Review",
            "django_python_developer",
            "reference",
        ),
        (
            "front_end_readability",
            "Front-End Readability Review",
            "technical_writer",
            "reader_facing",
        ),
    ],
)
def test_documentation_reviews_build(
    documentation_builder: PromptBuilder,
    review_name: str,
    expected_title: str,
    expected_lens: str,
    expected_mission: str,
) -> None:
    resolved = documentation_builder.resolve(review_name)

    assert resolved.definition.title == expected_title
    assert resolved.definition.lens == expected_lens
    assert resolved.definition.mission == expected_mission

    prompt = documentation_builder.build(
        review=review_name,
        artifact="Hello",
    )

    assert prompt.system
    assert prompt.user
    assert prompt.review_name == review_name
    assert prompt.config_name == "documentation"
