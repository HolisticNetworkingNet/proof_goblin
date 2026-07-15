"""OpenAI Responses API adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from proof_goblin.builder import Prompt
from proof_goblin.observations import TokenUsage
from proof_goblin.providers.base import (
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderRefusalError,
    ProviderRequestError,
    ProviderResponse,
    ProviderResponseError,
    ProviderUnavailableError,
)

DEFAULT_OPENAI_MODEL = "gpt-5.6"


class OpenAIProvider:
    """Generate structured review output with OpenAI's Responses API."""

    def __init__(
        self,
        *,
        model: str = DEFAULT_OPENAI_MODEL,
        client: Any | None = None,
    ) -> None:
        if not isinstance(model, str) or not model.strip():
            raise ProviderRequestError("model must be a non-empty string")
        self.model = model
        self.client = client if client is not None else _create_client()

    def generate(
        self, prompt: Prompt, output_schema: Mapping[str, Any]
    ) -> ProviderResponse:
        """Send a structured review request and decode its JSON response."""

        _validate_strict_schema(output_schema)
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=prompt.system,
                input=prompt.user,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "proof_goblin_observations",
                        "strict": True,
                        "schema": dict(output_schema),
                    }
                },
                store=False,
            )
        except Exception as exc:
            raise _translate_request_error(exc) from exc

        refusal = _find_refusal(response)
        if refusal is not None:
            raise ProviderRefusalError(f"OpenAI refused the review: {refusal}")

        output_text = getattr(response, "output_text", None)
        if not isinstance(output_text, str) or not output_text.strip():
            raise ProviderResponseError("OpenAI response did not contain output text")

        try:
            data = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError(
                f"OpenAI response was not valid JSON at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc
        if not isinstance(data, dict):
            raise ProviderResponseError(
                "OpenAI structured output must be a JSON object"
            )

        return ProviderResponse(
            data=data,
            provider="openai",
            model=getattr(response, "model", None) or self.model,
            response_id=getattr(response, "id", None),
            usage=_read_usage(getattr(response, "usage", None)),
        )


def _create_client() -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ProviderUnavailableError(
            "The OpenAI provider requires the optional dependency. "
            "Install it with: python -m pip install -e '.[openai]'"
        ) from exc
    try:
        return OpenAI()
    except Exception as exc:
        raise ProviderUnavailableError(
            "Could not initialize the OpenAI client. Set OPENAI_API_KEY in the "
            "environment before creating OpenAIProvider."
        ) from exc


def _translate_request_error(exc: Exception) -> ProviderResponseError:
    if getattr(exc, "code", None) == "insufficient_quota":
        return ProviderQuotaError(
            "The OpenAI API project has no available quota. Add API billing "
            "credits or increase the project's spending limit, then try again."
        )
    if getattr(exc, "status_code", None) == 429:
        return ProviderRateLimitError(
            "OpenAI temporarily rate-limited the request. Wait briefly and try again."
        )
    return ProviderResponseError(f"OpenAI request failed: {exc}")


def _validate_strict_schema(
    schema: Mapping[str, Any], path: str = "output schema"
) -> None:
    if schema.get("type") != "object":
        raise ProviderRequestError(f"{path} root must have type 'object'")
    _validate_object_constraints(schema, path)


def _validate_object_constraints(schema: object, path: str) -> None:
    if isinstance(schema, dict):
        if schema.get("type") == "object":
            properties = schema.get("properties")
            if not isinstance(properties, dict):
                raise ProviderRequestError(f"{path}.properties must be an object")
            if schema.get("additionalProperties") is not False:
                raise ProviderRequestError(
                    f"{path}.additionalProperties must be false for strict output"
                )
            required = schema.get("required")
            if not isinstance(required, list) or set(required) != set(properties):
                raise ProviderRequestError(
                    f"{path}.required must contain every property for strict output"
                )
        for key, value in schema.items():
            _validate_object_constraints(value, f"{path}.{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            _validate_object_constraints(value, f"{path}[{index}]")


def _find_refusal(response: Any) -> str | None:
    for item in getattr(response, "output", ()) or ():
        for content in getattr(item, "content", ()) or ():
            if getattr(content, "type", None) == "refusal":
                return getattr(content, "refusal", None) or "No reason provided"
    return None


def _read_usage(usage: Any) -> TokenUsage:
    if usage is None:
        return TokenUsage()
    return TokenUsage(
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        total_tokens=getattr(usage, "total_tokens", None),
    )
