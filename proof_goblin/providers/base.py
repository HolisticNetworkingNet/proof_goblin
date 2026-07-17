"""Provider-neutral review request and response types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from proof_goblin.builder import Prompt
from proof_goblin.observations import TokenUsage


class ProviderError(RuntimeError):
    """Base exception for model-provider errors."""


class ProviderUnavailableError(ProviderError):
    """Raised when an optional provider dependency is unavailable."""


class ProviderRequestError(ProviderError):
    """Raised when a review cannot be represented as a provider request."""


class ProviderResponseError(ProviderError):
    """Raised when a provider returns an unusable response."""


class ProviderQuotaError(ProviderResponseError):
    """Raised when a provider account has no usable API quota."""


class ProviderRateLimitError(ProviderResponseError):
    """Raised when a provider temporarily rate-limits requests."""


class ProviderRefusalError(ProviderResponseError):
    """Raised when a provider reports a model refusal."""


class ProviderCapacityStatus(StrEnum):
    """Result of comparing a prepared request with provider capacity."""

    FITS = "fits"
    EXCEEDS = "exceeds"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    """Credential-free parameters that completely describe a provider call."""

    provider: str
    model: str
    parameters: Mapping[str, Any]

    def __post_init__(self) -> None:
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.parameters, Mapping):
            raise ValueError("parameters must be a mapping")


@dataclass(frozen=True, slots=True)
class ProviderPreflight:
    """Safe readiness information for an exact provider request."""

    provider: str
    model: str
    max_output_tokens: int
    capacity_status: ProviderCapacityStatus
    input_tokens: int | None = None
    context_window_tokens: int | None = None
    request: ProviderRequest | None = None

    def __post_init__(self) -> None:
        for name in ("provider", "model"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        _require_positive_token_count(self.max_output_tokens, "max_output_tokens")
        for name in ("input_tokens", "context_window_tokens"):
            value = getattr(self, name)
            if value is not None:
                _require_positive_token_count(value, name, allow_zero=True)
        if not isinstance(self.capacity_status, ProviderCapacityStatus):
            raise ValueError("capacity_status must be a ProviderCapacityStatus")
        if self.request is not None:
            if self.request.provider != self.provider:
                raise ValueError("request provider must match preflight provider")
            if self.request.model != self.model:
                raise ValueError("request model must match preflight model")
        if self.capacity_status is not ProviderCapacityStatus.UNKNOWN:
            if self.input_tokens is None or self.context_window_tokens is None:
                raise ValueError(
                    "known capacity status requires input_tokens and "
                    "context_window_tokens"
                )
            expected = (
                ProviderCapacityStatus.FITS
                if self.input_tokens + self.max_output_tokens
                <= self.context_window_tokens
                else ProviderCapacityStatus.EXCEEDS
            )
            if self.capacity_status is not expected:
                raise ValueError("capacity_status does not match supplied token counts")

    @classmethod
    def assess(
        cls,
        *,
        provider: str,
        model: str,
        max_output_tokens: int,
        input_tokens: int | None = None,
        context_window_tokens: int | None = None,
        request: ProviderRequest | None = None,
    ) -> ProviderPreflight:
        """Classify capacity when both token measurements are reliable."""

        if input_tokens is None or context_window_tokens is None:
            status = ProviderCapacityStatus.UNKNOWN
        elif input_tokens + max_output_tokens <= context_window_tokens:
            status = ProviderCapacityStatus.FITS
        else:
            status = ProviderCapacityStatus.EXCEEDS
        return cls(
            provider=provider,
            model=model,
            max_output_tokens=max_output_tokens,
            capacity_status=status,
            input_tokens=input_tokens,
            context_window_tokens=context_window_tokens,
            request=request,
        )


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    """A provider's decoded structured response."""

    data: Mapping[str, Any]
    provider: str
    model: str
    response_id: str | None = None
    usage: TokenUsage = TokenUsage()


class Provider(Protocol):
    """Interface implemented by model providers."""

    def preflight(
        self, prompt: Prompt, output_schema: Mapping[str, Any]
    ) -> ProviderPreflight:
        """Validate and describe an exact credential-free request."""

    def generate(
        self, prompt: Prompt, output_schema: Mapping[str, Any]
    ) -> ProviderResponse:
        """Generate structured output for an assembled prompt."""


def _require_positive_token_count(
    value: object,
    name: str,
    *,
    allow_zero: bool = False,
) -> None:
    minimum = 0 if allow_zero else 1
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{name} must be a {qualifier} integer")
