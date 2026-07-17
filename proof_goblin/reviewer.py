"""Provider-neutral review orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import SchemaError, ValidationError, validators

from proof_goblin.builder import Prompt, PromptBuilder, ResolvedReview
from proof_goblin.config import Config
from proof_goblin.limits import DEFAULT_INPUT_LIMITS, InputLimits
from proof_goblin.observations import Observation, ReviewAttribution, ReviewResult
from proof_goblin.providers.base import (
    Provider,
    ProviderCapacityStatus,
    ProviderPreflight,
    ProviderRequestError,
)


class ReviewError(RuntimeError):
    """Base exception for review orchestration errors."""


class ReviewOutputValidationError(ReviewError):
    """Raised when structured output does not match its declared schema."""


class Reviewer:
    """Build a prompt, call a provider, and return validated observations."""

    def __init__(
        self,
        provider: Provider,
        *,
        limits: InputLimits = DEFAULT_INPUT_LIMITS,
    ) -> None:
        """Create a reviewer using explicit or default deterministic limits."""

        self.provider = provider
        self.limits = limits

    def preflight(
        self,
        *,
        config: Config,
        review: str,
        artifact: str,
        artifact_name: str = "artifact",
        artifact_media_type: str = "text/plain",
    ) -> ProviderPreflight:
        """Prepare and validate a review without generating provider output."""

        resolved, prompt = self._prepare(
            config=config,
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
        result = self.provider.preflight(prompt, resolved.output_schema)
        _reject_excessive_provider_request(result)
        return result

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

        resolved, prompt = self._prepare(
            config=config,
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
        preflight = self.provider.preflight(prompt, resolved.output_schema)
        _reject_excessive_provider_request(preflight)
        response = self.provider.generate(prompt, resolved.output_schema)
        _validate_output(response.data, resolved.output_schema)
        observations = _read_observations(response.data)

        return ReviewResult(
            observations=observations,
            prompt=prompt,
            review=ReviewAttribution(
                name=resolved.definition.name,
                title=resolved.definition.title,
                description=resolved.definition.description,
                lens=resolved.definition.lens,
                mission=resolved.definition.mission,
                protocol=resolved.definition.protocol,
                output_schema=resolved.definition.output_schema,
            ),
            provider=response.provider,
            model=response.model,
            response_id=response.response_id,
            usage=response.usage,
            raw_output=response.data,
        )

    def _prepare(
        self,
        *,
        config: Config,
        review: str,
        artifact: str,
        artifact_name: str,
        artifact_media_type: str,
    ) -> tuple[ResolvedReview, Prompt]:
        builder = PromptBuilder(config, limits=self.limits)
        resolved = builder.resolve(review)
        prompt = builder.build(
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
        return resolved, prompt


def _reject_excessive_provider_request(preflight: ProviderPreflight) -> None:
    if preflight.capacity_status is ProviderCapacityStatus.EXCEEDS:
        assert preflight.input_tokens is not None
        assert preflight.context_window_tokens is not None
        required = preflight.input_tokens + preflight.max_output_tokens
        raise ProviderRequestError(
            f"{preflight.provider} request requires {required} tokens including "
            f"reserved output; {preflight.model} context capacity is "
            f"{preflight.context_window_tokens} tokens"
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
            raise ReviewOutputValidationError(f"observations.{index} must be an object")
        question = value.get("question")
        evidence = value.get("evidence")
        if not isinstance(question, str) or not isinstance(evidence, str):
            raise ReviewOutputValidationError(
                f"observations.{index} must contain string question and evidence"
            )
        observations.append(Observation(question=question, evidence=evidence))
    return tuple(observations)
