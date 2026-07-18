"""Model-provider interfaces and adapters."""

from proof_goblin.providers.base import (
    Provider,
    ProviderCapacityStatus,
    ProviderError,
    ProviderPreflight,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderRequest,
    ProviderRequestError,
    ProviderResponse,
    ProviderResponseError,
    ProviderUnavailableError,
)
from proof_goblin.providers.openai import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_OPENAI_MAX_RETRIES,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    OpenAIProvider,
)

__all__ = [
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_OPENAI_MAX_RETRIES",
    "DEFAULT_OPENAI_MODEL",
    "DEFAULT_OPENAI_TIMEOUT_SECONDS",
    "OpenAIProvider",
    "Provider",
    "ProviderCapacityStatus",
    "ProviderError",
    "ProviderQuotaError",
    "ProviderRateLimitError",
    "ProviderRefusalError",
    "ProviderPreflight",
    "ProviderRequest",
    "ProviderRequestError",
    "ProviderResponse",
    "ProviderResponseError",
    "ProviderUnavailableError",
]
