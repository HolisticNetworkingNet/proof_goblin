# OpenAI provider

Proof Goblin's first model provider uses OpenAI's Responses API and Structured
Outputs. The adapter sends the assembled system and user portions separately and
passes the selected `.pgcfg` output schema through strict `text.format`.

The core `Reviewer` remains provider-neutral. It validates the returned data
against the same configured JSON Schema before constructing `Observation`
objects.

## Install the optional integration

```bash
python -m pip install -e ".[openai]"
```

Set `OPENAI_API_KEY` in the environment used by PyCharm or your terminal. Do not
put the key in source control.

For a temporary value in the macOS Zsh terminal, enter the replacement key at
the hidden prompt:

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
export OPENAI_API_KEY
```

Defining a Python variable named `OPENAI_API_KEY` does not configure the OpenAI
SDK. The value must be in the process environment or passed explicitly to the
SDK client.

## Run a live review

The repository includes a fixed smoke-test script using the restaurant bundle
and example homepage:

```bash
python proof_goblin/examples/live_openai_review.py
```

The script uses `gpt-5.6` by default. To choose another compatible model, set
`OPENAI_MODEL` before running it.

## Library usage

```python
from pathlib import Path

from proof_goblin import Config, OpenAIProvider, Reviewer

config = Config.load("proof_goblin/examples/restaurants.pgcfg")
artifact = Path("proof_goblin/examples/homepage.html").read_text()

result = Reviewer(OpenAIProvider()).review(
    config=config,
    review="homepage_first_pass",
    artifact=artifact,
    artifact_name="homepage.html",
    artifact_media_type="text/html",
)

for observation in result.observations:
    print(observation.question)
    print(observation.evidence)
```

`ReviewResult` also records the provider, resolved model, response identifier,
token usage, assembled prompt, raw structured output, and configuration and
artifact provenance carried by the prompt.

## Errors

Provider failures use focused exception types:

- `ProviderUnavailableError` for missing SDK installation or credentials;
- `ProviderRequestError` for an incompatible strict output schema;
- `ProviderQuotaError` when the API project has no usable credits or spending
  allowance;
- `ProviderRateLimitError` for temporary request-rate limits;
- `ProviderRefusalError` for a model refusal;
- `ProviderResponseError` for an API failure or unusable response; and
- `ReviewOutputValidationError` when returned data fails local schema validation.

The example output schema follows OpenAI's strict-schema requirements: its root
is an object, every object rejects additional properties, and every property is
required.
