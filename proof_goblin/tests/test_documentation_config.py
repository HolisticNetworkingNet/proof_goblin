# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Tests for the bundled documentation review configuration."""

from pathlib import Path

import pytest

from proof_goblin.builder import PromptBuilder
from proof_goblin.config import Config


CONFIG_PATH = (
    Path(__file__).resolve().parents[1] / "configs" / "documentation.pgcfg"
)


@pytest.fixture
def documentation_config() -> Config:
    """Load the bundled documentation configuration."""

    return Config.load(CONFIG_PATH)


def test_documentation_config_contains_expected_lenses(
    documentation_config: Config,
) -> None:
    assert set(documentation_config.lenses) == {
        "business_owner",
        "django_python_developer",
        "technical_writer",
    }


@pytest.mark.parametrize(
    ("review_name", "title", "lens_name", "mission_name"),
    [
        (
            "business_owner_first_pass",
            "Business Owner Documentation Review",
            "business_owner",
            "business_comprehension",
        ),
        (
            "django_developer_first_pass",
            "Django Developer Documentation Review",
            "django_python_developer",
            "developer_implementation",
        ),
        (
            "technical_writer_first_pass",
            "Technical Writing Review",
            "technical_writer",
            "technical_writing_quality",
        ),
        (
            "front_end_readability",
            "Front-End Readability Review",
            "technical_writer",
            "front_end_readability",
        ),
    ],
)
def test_documentation_reviews_resolve_expected_components(
    documentation_config: Config,
    review_name: str,
    title: str,
    lens_name: str,
    mission_name: str,
) -> None:
    resolved = PromptBuilder(documentation_config).resolve(review_name)

    assert resolved.definition.title == title
    assert resolved.definition.description
    assert resolved.definition.lens == lens_name
    assert resolved.definition.mission == mission_name
    assert resolved.definition.protocol == "documentation_questions_only"
    assert resolved.definition.output_schema == "observation.v1"


@pytest.mark.parametrize(
    "review_name",
    [
        "business_owner_first_pass",
        "django_developer_first_pass",
        "technical_writer_first_pass",
        "front_end_readability",
    ],
)
def test_documentation_reviews_build_prompts(
    documentation_config: Config,
    review_name: str,
) -> None:
    artifact = "# Exporting a site\n\nRun the export command."
    prompt = PromptBuilder(documentation_config).build(
        review=review_name,
        artifact=artifact,
    )

    assert prompt.system
    assert artifact in prompt.user
