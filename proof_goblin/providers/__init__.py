"""Model-provider interfaces and adapters."""

from proof_goblin.providers.base import (
    Provider,
    ProviderError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderRequestError,
    ProviderResponse,
    ProviderResponseError,
    ProviderUnavailableError,
)
from proof_goblin.providers.openai import DEFAULT_OPENAI_MODEL, OpenAIProvider

__all__ = [
    "DEFAULT_OPENAI_MODEL",
    "OpenAIProvider",
    "Provider",
    "ProviderError",
    "ProviderQuotaError",
    "ProviderRateLimitError",
    "ProviderRefusalError",
    "ProviderRequestError",
    "ProviderResponse",
    "ProviderResponseError",
    "ProviderUnavailableError",
]
