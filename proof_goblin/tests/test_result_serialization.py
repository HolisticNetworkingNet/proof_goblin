from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from proof_goblin import (
    Config,
    Observation,
    PromptBuilder,
    ReviewAttribution,
    ReviewResult,
    TokenUsage,
)

EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"


def make_result() -> ReviewResult:
    config = Config.load(EXAMPLE_CONFIG)
    prompt = PromptBuilder(config).build(
        review="homepage_first_pass",
        artifact="<main>Welcome</main>",
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )
    return ReviewResult(
        observations=(
            Observation(
                question="Where are the hours?",
                evidence="No hours appear in the homepage.",
            ),
        ),
        prompt=prompt,
        review=ReviewAttribution(
            name="homepage_first_pass",
            title="Restaurant Homepage Review",
            description=(
                "Evaluates whether a first-time diner can understand the restaurant "
                "and find the information needed to visit."
            ),
            lens="first_time_diner",
            mission="homepage_clarity",
            protocol="questions_only",
            output_schema="observation.v1",
        ),
        provider="openai",
        model="gpt-5.6-sol",
        response_id="resp_123",
        usage=TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
        raw_output={
            "observations": [
                {
                    "question": "Where are the hours?",
                    "evidence": "No hours appear in the homepage.",
                }
            ]
        },
        created_at=datetime(2026, 7, 13, 18, 30, tzinfo=UTC),
    )


def result_schema() -> dict[str, object]:
    resource = files("proof_goblin").joinpath("schemas/review-result.v1.schema.json")
    return json.loads(resource.read_text())


def test_to_dict_returns_versioned_host_record() -> None:
    record = make_result().to_dict()

    assert record["format"] == "proof-goblin-review-result"
    assert record["schema_version"] == "1.0"
    assert record["created_at"] == "2026-07-13T18:30:00Z"
    assert record["review"] == {
        "name": "homepage_first_pass",
        "title": "Restaurant Homepage Review",
        "description": (
            "Evaluates whether a first-time diner can understand the restaurant "
            "and find the information needed to visit."
        ),
        "lens": "first_time_diner",
        "mission": "homepage_clarity",
        "protocol": "questions_only",
        "output_schema": "observation.v1",
    }
    assert record["config"]["name"] == "restaurants"
    assert record["artifact"]["name"] == "homepage.html"
    assert record["execution"]["provider"] == "openai"
    assert record["execution"]["usage"]["total_tokens"] == 120
    assert record["observations"][0]["question"] == "Where are the hours?"
    assert "prompt" not in record


def test_serialized_record_matches_published_schema() -> None:
    validator = Draft202012Validator(
        result_schema(),
        format_checker=FormatChecker(),
    )

    validator.validate(make_result().to_dict())
    validator.validate(make_result().to_dict(include_prompt=True))


def test_prompt_text_is_included_only_when_requested() -> None:
    result = make_result()

    record = result.to_dict(include_prompt=True)

    assert record["prompt"]["system"] == result.prompt.system
    assert record["prompt"]["user"] == result.prompt.user
    assert "<main>Welcome</main>" in record["prompt"]["user"]


def test_to_json_round_trips_to_the_same_record() -> None:
    result = make_result()

    assert json.loads(result.to_json()) == result.to_dict()


def test_from_dict_reconstructs_result_with_verified_prompt() -> None:
    result = make_result()

    reconstructed = ReviewResult.from_dict(result.to_dict(), prompt=result.prompt)

    assert reconstructed.to_dict() == result.to_dict()
    assert reconstructed.prompt is result.prompt


def test_from_dict_rejects_mismatched_prompt_provenance() -> None:
    result = make_result()
    different_prompt = replace(result.prompt, artifact_sha256="0" * 64)

    with pytest.raises(ValueError, match="artifact.sha256"):
        ReviewResult.from_dict(result.to_dict(), prompt=different_prompt)


def test_result_requires_timezone_aware_creation_time() -> None:
    result = make_result()

    with pytest.raises(ValueError, match="timezone information"):
        ReviewResult(
            observations=result.observations,
            prompt=result.prompt,
            review=result.review,
            provider=result.provider,
            model=result.model,
            response_id=result.response_id,
            usage=result.usage,
            raw_output=result.raw_output,
            created_at=datetime(2026, 7, 13, 18, 30),
        )


def test_result_requires_attribution_to_match_prompt() -> None:
    result = make_result()

    with pytest.raises(ValueError, match="must match prompt review name"):
        ReviewResult(
            observations=result.observations,
            prompt=result.prompt,
            review=replace(result.review, name="different_review"),
            provider=result.provider,
            model=result.model,
            response_id=result.response_id,
            usage=result.usage,
            raw_output=result.raw_output,
            created_at=result.created_at,
        )
