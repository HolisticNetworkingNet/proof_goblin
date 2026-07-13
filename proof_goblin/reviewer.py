# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Provider-neutral review orchestration."""

from __future__ import annotations

from typing import Any, Mapping

from jsonschema import SchemaError, ValidationError, validators

from proof_goblin.builder import PromptBuilder
from proof_goblin.config import Config
from proof_goblin.observations import Observation, ReviewResult
from proof_goblin.providers.base import Provider


class ReviewError(RuntimeError):
    """Base exception for review orchestration errors."""


class ReviewOutputValidationError(ReviewError):
    """Raised when structured output does not match its declared schema."""


class Reviewer:
    """Build a prompt, call a provider, and return validated observations."""

    def __init__(self, provider: Provider) -> None:
        self.provider = provider

    def review(
        self,
        *,
        config: Config,
        review: str,
        artifact: str,
        artifact_name: str = "artifact",
        artifact_media_type: str = "text/plain",
    ) -> ReviewResult:
        """Run a named review against an artifact."""

        builder = PromptBuilder(config)
        resolved = builder.resolve(review)
        prompt = builder.build(
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
        response = self.provider.generate(prompt, resolved.output_schema)
        _validate_output(response.data, resolved.output_schema)
        observations = _read_observations(response.data)

        return ReviewResult(
            observations=observations,
            prompt=prompt,
            provider=response.provider,
            model=response.model,
            response_id=response.response_id,
            usage=response.usage,
            raw_output=response.data,
        )


def _validate_output(data: Mapping[str, Any], schema: Mapping[str, Any]) -> None:
    try:
        validator_class = validators.validator_for(schema)
        validator_class.check_schema(schema)
        validator_class(schema).validate(data)
    except SchemaError as exc:
        raise ReviewOutputValidationError(
            f"Configured output schema is invalid: {exc.message}"
        ) from exc
    except ValidationError as exc:
        location = ".".join(str(part) for part in exc.absolute_path) or "output"
        raise ReviewOutputValidationError(
            f"Provider output failed validation at {location}: {exc.message}"
        ) from exc


def _read_observations(data: Mapping[str, Any]) -> tuple[Observation, ...]:
    values = data.get("observations")
    if not isinstance(values, list):
        raise ReviewOutputValidationError(
            "Provider output must contain an observations array"
        )

    observations: list[Observation] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise ReviewOutputValidationError(
                f"observations.{index} must be an object"
            )
        question = value.get("question")
        evidence = value.get("evidence")
        if not isinstance(question, str) or not isinstance(evidence, str):
            raise ReviewOutputValidationError(
                f"observations.{index} must contain string question and evidence"
            )
        observations.append(Observation(question=question, evidence=evidence))
    return tuple(observations)
