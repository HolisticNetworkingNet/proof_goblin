# OpenAI Provider

Proof Goblin's first model provider uses OpenAI's Responses API and Structured
Outputs. The adapter sends the assembled system and user portions separately and
passes the selected `.pgcfg` output schema through strict `text.format`.

The core `Reviewer` remains provider-neutral. It validates the returned data
against the same configured JSON Schema before constructing `Observation`
objects.

Before generation, `Reviewer` runs provider preflight. The OpenAI adapter
validates its strict structured-output request, sets an explicit maximum output
allowance, and disables automatic truncation. Its default preflight capacity
status is `unknown`: Proof Goblin does not maintain a model-context catalog or
make a separate remote token-count request for every review. See
{doc}`input-limits` for the complete contract.

The prepared request is credential-free and deterministic. The CLI hashes that
complete description for cache identity, and execution sends the same prepared
parameters rather than assembling a second variant.

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

## Data sent to OpenAI

A live review sends the complete assembled prompt: selected Lens, Mission,
Review Protocol, and Output Schema content as instructions, plus the artifact
name, media type, and complete artifact as user input. The Output Schema is also
sent as the strict structured-output contract. The request includes the model,
maximum output allowance, disabled truncation, and `store=False`.

The API key authenticates the SDK request but is not placed in the prompt,
credential-free prepared request, cache identity, or result provenance.
`store=False` does not define every provider-side logging, abuse-monitoring,
retention, training-use, residency, or deletion rule. Confirm that the current
provider and account policy is appropriate before sending sensitive material.

Proof Goblin validates the decoded response in memory. An in-memory
`ReviewResult` retains the prompt and raw decoded output. Default serialized
results and CLI cache entries omit prompt fields, but their observations and
evidence can quote the artifact. See {doc}`data-handling` for the complete
lifecycle and ownership boundaries.

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

`OpenAIProvider(max_output_tokens=...)` changes the positive output-token
allowance used in both preflight and the Responses API request. The default is
8,192. An application can inspect readiness without generating output by
calling `Reviewer.preflight()` with the same review arguments.

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

For diagnostic shapes, potentially sensitive details, remediation, and retry
guidance for each provider failure, see the {doc}`Error Reference <errors>`.

The example output schema follows OpenAI's strict-schema requirements: its root
is an object, every object rejects additional properties, and every property is
required.

Proof Goblin checks those three constraints recursively before sending an
OpenAI request: the root must have `type: object`; each object must define a
`properties` object and set `additionalProperties: false`; and each object's
`required` array must name every property. This is the provider adapter's
enforced strict subset, not a promise that every otherwise valid JSON Schema
keyword is accepted by OpenAI.

After a response, the provider-neutral `Reviewer` selects the local validator
from the configured schema's `$schema` declaration, checks that schema, and
validates the decoded output against it. Configuration authors should declare
the intended JSON Schema dialect explicitly rather than relying on the
installed `jsonschema` library's default when `$schema` is absent. Provider
strictness and local JSON Schema validation are separate checks; an output
schema used with OpenAI must satisfy both.
