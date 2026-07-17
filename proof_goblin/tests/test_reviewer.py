from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from proof_goblin import (
    DEFAULT_INPUT_LIMITS,
    Config,
    InputLimitError,
    ProviderCapacityStatus,
    ProviderPreflight,
    ProviderRequest,
    ProviderRequestError,
    ProviderResponse,
    Reviewer,
    ReviewOutputValidationError,
    TokenUsage,
)

EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"


class FakeProvider:
    def __init__(self, data: dict[str, object]) -> None:
        self.data = data
        self.prompt = None
        self.output_schema = None

    def preflight(self, prompt, output_schema) -> ProviderPreflight:
        request = ProviderRequest(
            provider="fake",
            model="fake-model",
            parameters={
                "model": "fake-model",
                "system": prompt.system,
                "user": prompt.user,
                "schema": output_schema,
                "max_output_tokens": 100,
            },
        )
        return ProviderPreflight.assess(
            provider="fake",
            model="fake-model",
            max_output_tokens=100,
            request=request,
        )

    def generate(self, prompt, output_schema) -> ProviderResponse:
        self.prompt = prompt
        self.output_schema = output_schema
        return ProviderResponse(
            data=self.data,
            provider="fake",
            model="fake-model",
            response_id="response-123",
            usage=TokenUsage(input_tokens=100, output_tokens=20, total_tokens=120),
        )


def test_reviewer_returns_validated_observations() -> None:
    provider = FakeProvider(
        {
            "observations": [
                {
                    "question": "Where are the restaurant hours?",
                    "evidence": "No hours appear in the supplied homepage.",
                }
            ]
        }
    )
    config = Config.load(EXAMPLE_CONFIG)

    result = Reviewer(provider).review(
        config=config,
        review="homepage_first_pass",
        artifact="<main>Welcome</main>",
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )

    assert result.observations[0].question == "Where are the restaurant hours?"
    assert result.observations[0].evidence.startswith("No hours")
    assert result.review.name == "homepage_first_pass"
    assert result.review.title == "Restaurant Homepage Review"
    assert result.review.description.startswith("Evaluates")
    assert result.review.lens == "first_time_diner"
    assert result.review.mission == "homepage_clarity"
    assert result.review.protocol == "questions_only"
    assert result.review.output_schema == "observation.v1"
    assert result.provider == "fake"
    assert result.model == "fake-model"
    assert result.response_id == "response-123"
    assert result.usage.total_tokens == 120
    assert result.prompt.artifact_name == "homepage.html"
    assert provider.output_schema == config.output_schema("observation.v1")


def test_reviewer_accepts_no_observations() -> None:
    result = Reviewer(FakeProvider({"observations": []})).review(
        config=Config.load(EXAMPLE_CONFIG),
        review="homepage_first_pass",
        artifact="A complete homepage",
    )

    assert result.observations == ()


def test_reviewer_rejects_oversized_artifact_without_calling_provider() -> None:
    provider = FakeProvider({"observations": []})
    limits = replace(
        DEFAULT_INPUT_LIMITS,
        max_artifact_bytes=3,
        max_total_artifact_bytes=3,
    )

    with pytest.raises(InputLimitError, match="artifact input"):
        Reviewer(provider, limits=limits).review(
            config=Config.load(EXAMPLE_CONFIG),
            review="homepage_first_pass",
            artifact="four",
        )

    assert provider.prompt is None


def test_reviewer_exposes_provider_preflight_without_generation() -> None:
    provider = FakeProvider({"observations": []})

    result = Reviewer(provider).preflight(
        config=Config.load(EXAMPLE_CONFIG),
        review="homepage_first_pass",
        artifact="Welcome",
    )

    assert result.capacity_status is ProviderCapacityStatus.UNKNOWN
    assert provider.prompt is None


def test_reviewer_rejects_known_capacity_excess_before_generation() -> None:
    provider = FakeProvider({"observations": []})
    provider.preflight = lambda prompt, schema: ProviderPreflight.assess(
        provider="fake",
        model="small-model",
        input_tokens=901,
        max_output_tokens=100,
        context_window_tokens=1000,
        request=ProviderRequest(
            provider="fake",
            model="small-model",
            parameters={"model": "small-model"},
        ),
    )

    with pytest.raises(ProviderRequestError, match="requires 1001 tokens"):
        Reviewer(provider).review(
            config=Config.load(EXAMPLE_CONFIG),
            review="homepage_first_pass",
            artifact="Welcome",
        )

    assert provider.prompt is None


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({}, "'observations' is a required property"),
        ({"observations": "none"}, "is not of type 'array'"),
        (
            {"observations": [{"question": "Missing evidence"}]},
            "'evidence' is a required property",
        ),
        (
            {
                "observations": [
                    {"question": "Question", "evidence": "Evidence", "edit": "No"}
                ]
            },
            "Additional properties are not allowed",
        ),
    ],
)
def test_reviewer_rejects_output_that_does_not_match_schema(
    data: dict[str, object], message: str
) -> None:
    with pytest.raises(ReviewOutputValidationError, match=message):
        Reviewer(FakeProvider(data)).review(
            config=Config.load(EXAMPLE_CONFIG),
            review="homepage_first_pass",
            artifact="Welcome",
        )
