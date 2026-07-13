# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from proof_goblin import (
    Config,
    OpenAIProvider,
    PromptBuilder,
    ProviderRefusalError,
    ProviderQuotaError,
    ProviderRateLimitError,
    ProviderRequestError,
    ProviderResponseError,
)


EXAMPLE_CONFIG = (
    Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"
)


class FakeResponses:
    def __init__(self, response: object) -> None:
        self.response = response
        self.arguments = None

    def create(self, **kwargs):
        self.arguments = kwargs
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def make_client(response: object) -> SimpleNamespace:
    return SimpleNamespace(responses=FakeResponses(response))


def make_prompt_and_schema():
    config = Config.load(EXAMPLE_CONFIG)
    builder = PromptBuilder(config)
    return (
        builder.build(review="homepage_first_pass", artifact="Welcome"),
        config.output_schema("observation.v1"),
    )


def test_openai_provider_creates_real_sdk_client_without_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    provider = OpenAIProvider()

    assert provider.client is not None
    assert provider.client.responses is not None


def test_openai_provider_uses_responses_api_with_strict_schema() -> None:
    response = SimpleNamespace(
        id="resp_123",
        model="gpt-5.6-2026-01-01",
        output_text=(
            '{"observations":[{"question":"Where are the hours?",'
            '"evidence":"Hours are not present."}]}'
        ),
        output=[],
        usage=SimpleNamespace(input_tokens=80, output_tokens=20, total_tokens=100),
    )
    client = make_client(response)
    prompt, schema = make_prompt_and_schema()

    result = OpenAIProvider(model="gpt-5.6", client=client).generate(prompt, schema)

    request = client.responses.arguments
    assert request["model"] == "gpt-5.6"
    assert request["instructions"] == prompt.system
    assert request["input"] == prompt.user
    assert request["store"] is False
    assert request["text"]["format"] == {
        "type": "json_schema",
        "name": "proof_goblin_observations",
        "strict": True,
        "schema": schema,
    }
    assert result.data["observations"][0]["question"] == "Where are the hours?"
    assert result.response_id == "resp_123"
    assert result.model == "gpt-5.6-2026-01-01"
    assert result.usage.total_tokens == 100


def test_openai_provider_reports_model_refusal() -> None:
    refusal = SimpleNamespace(type="refusal", refusal="I cannot review this.")
    message = SimpleNamespace(content=[refusal])
    client = make_client(SimpleNamespace(output=[message], output_text=""))
    prompt, schema = make_prompt_and_schema()

    with pytest.raises(ProviderRefusalError, match="I cannot review this"):
        OpenAIProvider(client=client).generate(prompt, schema)


def test_openai_provider_rejects_missing_output_text() -> None:
    client = make_client(SimpleNamespace(output=[], output_text=None))
    prompt, schema = make_prompt_and_schema()

    with pytest.raises(ProviderResponseError, match="did not contain output text"):
        OpenAIProvider(client=client).generate(prompt, schema)


def test_openai_provider_rejects_non_json_output() -> None:
    client = make_client(SimpleNamespace(output=[], output_text="not json"))
    prompt, schema = make_prompt_and_schema()

    with pytest.raises(ProviderResponseError, match="was not valid JSON"):
        OpenAIProvider(client=client).generate(prompt, schema)


def test_openai_provider_reports_insufficient_quota() -> None:
    error = RuntimeError("quota exceeded")
    error.code = "insufficient_quota"
    error.status_code = 429
    prompt, schema = make_prompt_and_schema()

    with pytest.raises(ProviderQuotaError, match="no available quota"):
        OpenAIProvider(client=make_client(error)).generate(prompt, schema)


def test_openai_provider_distinguishes_temporary_rate_limit() -> None:
    error = RuntimeError("too many requests")
    error.status_code = 429
    prompt, schema = make_prompt_and_schema()

    with pytest.raises(ProviderRateLimitError, match="temporarily rate-limited"):
        OpenAIProvider(client=make_client(error)).generate(prompt, schema)


@pytest.mark.parametrize(
    ("schema", "message"),
    [
        ({"type": "array"}, "root must have type 'object'"),
        (
            {"type": "object", "properties": {}, "required": []},
            "additionalProperties must be false",
        ),
        (
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {"observations": {"type": "array"}},
                "required": [],
            },
            "required must contain every property",
        ),
    ],
)
def test_openai_provider_rejects_non_strict_schema(
    schema: dict[str, object], message: str
) -> None:
    prompt, _ = make_prompt_and_schema()

    with pytest.raises(ProviderRequestError, match=message):
        OpenAIProvider(client=make_client(None)).generate(prompt, schema)
