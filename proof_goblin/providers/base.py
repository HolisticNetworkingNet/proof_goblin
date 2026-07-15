"""Provider-neutral review request and response types."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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

    def generate(
        self, prompt: Prompt, output_schema: Mapping[str, Any]
    ) -> ProviderResponse:
        """Generate structured output for an assembled prompt."""
