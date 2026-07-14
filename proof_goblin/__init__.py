# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Proof Goblin public package interface."""

from proof_goblin.builder import (
    Prompt,
    PromptBuildError,
    PromptBuilder,
    ResolvedReview,
)
from proof_goblin.config import (
    CONFIG_FORMAT,
    SUPPORTED_SCHEMA_VERSIONS,
    ComponentNotFoundError,
    Config,
    ConfigError,
    ConfigParseError,
    ConfigValidationError,
    ReviewDefinition,
)
from proof_goblin.observations import (
    REVIEW_RESULT_FORMAT,
    REVIEW_RESULT_SCHEMA_VERSION,
    Observation,
    ReviewAttribution,
    ReviewResult,
    TokenUsage,
)
from proof_goblin.providers import (
    DEFAULT_OPENAI_MODEL,
    OpenAIProvider,
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
from proof_goblin.reports import (
    HtmlReportRenderer,
    JsonReportRenderer,
    MarkdownReportRenderer,
    ReportFormat,
    ReportRenderError,
    ReportRenderer,
    TextReportRenderer,
    render_report,
)
from proof_goblin.reviewer import ReviewError, Reviewer, ReviewOutputValidationError

__all__ = [
    "CONFIG_FORMAT",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ComponentNotFoundError",
    "Config",
    "ConfigError",
    "ConfigParseError",
    "ConfigValidationError",
    "DEFAULT_OPENAI_MODEL",
    "HtmlReportRenderer",
    "JsonReportRenderer",
    "MarkdownReportRenderer",
    "Observation",
    "OpenAIProvider",
    "Prompt",
    "PromptBuildError",
    "PromptBuilder",
    "Provider",
    "ProviderError",
    "ProviderQuotaError",
    "ProviderRateLimitError",
    "ProviderRefusalError",
    "ProviderRequestError",
    "ProviderResponse",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "REVIEW_RESULT_FORMAT",
    "REVIEW_RESULT_SCHEMA_VERSION",
    "ReportFormat",
    "ReportRenderError",
    "ReportRenderer",
    "ResolvedReview",
    "ReviewError",
    "ReviewAttribution",
    "ReviewDefinition",
    "ReviewOutputValidationError",
    "ReviewResult",
    "Reviewer",
    "TextReportRenderer",
    "TokenUsage",
    "render_report",
]
