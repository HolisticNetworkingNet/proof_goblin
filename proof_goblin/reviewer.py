"""Provider-neutral review orchestration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
    ProviderRequest,
    ProviderRequestError,
)


class ReviewError(RuntimeError):
    """Base exception for review orchestration errors."""


class ReviewOutputValidationError(ReviewError):
    """Raised when structured output does not match its declared schema."""


@dataclass(frozen=True, slots=True)
class PreparedReview:
    """A validated review and the exact credential-free provider request."""

    resolved: ResolvedReview
    prompt: Prompt
    request: ProviderRequest
    preflight: ProviderPreflight


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
        artifact_media_type: str | None = None,
    ) -> ProviderPreflight:
        """Prepare and validate a review without generating provider output."""

        return self.prepare(
            config=config,
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        ).preflight

    def prepare(
        self,
        *,
        config: Config,
        review: str,
        artifact: str,
        artifact_name: str = "artifact",
        artifact_media_type: str | None = None,
    ) -> PreparedReview:
        """Build and validate one canonical provider request."""

        resolved, prompt = self._prepare(
            config=config,
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
        preflight = self.provider.preflight(prompt, resolved.output_schema)
        _reject_excessive_provider_request(preflight)
        if preflight.request is None:
            raise ProviderRequestError(
                "provider preflight did not describe the prepared request"
            )
        return PreparedReview(
            resolved=resolved,
            prompt=prompt,
            request=preflight.request,
            preflight=preflight,
        )

    def review(
        self,
        *,
        config: Config,
        review: str,
        artifact: str,
        artifact_name: str = "artifact",
        artifact_media_type: str | None = None,
    ) -> ReviewResult:
        """Run a named review against an artifact."""

        prepared = self.prepare(
            config=config,
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
        return self.review_prepared(prepared)

    def review_prepared(self, prepared: PreparedReview) -> ReviewResult:
        """Execute a request that was already prepared and validated."""

        generate_prepared = getattr(self.provider, "generate_prepared", None)
        if generate_prepared is None:
            response = self.provider.generate(
                prepared.prompt,
                prepared.resolved.output_schema,
            )
        else:
            response = generate_prepared(prepared.request)
        _validate_output(response.data, prepared.resolved.output_schema)
        observations = _read_observations(response.data)

        return ReviewResult(
            observations=observations,
            prompt=prepared.prompt,
            review=ReviewAttribution(
                name=prepared.resolved.definition.name,
                title=prepared.resolved.definition.title,
                description=prepared.resolved.definition.description,
                lens=prepared.resolved.definition.lens,
                mission=prepared.resolved.definition.mission,
                protocol=prepared.resolved.definition.protocol,
                output_schema=prepared.resolved.definition.output_schema,
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
        artifact_media_type: str | None,
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
