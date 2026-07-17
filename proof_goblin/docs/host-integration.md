# Host Application Integration

This guide is for Python developers embedding Proof Goblin in an application,
service, worker, or scheduled job. By the end, you should be able to load a
review configuration, execute a review through a provider, handle failures,
persist a versioned result, and render that result without another provider
request.

Proof Goblin requires Python 3.11 or later and has no Django dependency. Until
the package is published, install it from a source checkout. Add the OpenAI
dependency group when using the bundled provider:

```bash
python -m pip install -e ".[openai]"
```

See {doc}`Getting Started <getting-started>` for repository and environment
setup and {doc}`Configuration Bundles <configuration>` for the `.pgcfg`
contract. The public Python API remains experimental before version 1.0, so a
host should pin the Proof Goblin version it has tested.

## Ownership boundary

The host application and Proof Goblin have separate responsibilities:

| Host application | Proof Goblin |
| --- | --- |
| Create or retrieve the artifact | Validate review configuration |
| Authorize the user and review | Assemble the configured prompt |
| Schedule work and control concurrency | Invoke the selected provider |
| Configure retries and deduplicate jobs | Validate structured provider output |
| Persist results and enforce retention | Normalize observations and provenance |
| Decide how results are presented | Render supported report formats |

Proof Goblin does not require a database, task queue, web framework, or storage
model. Those choices remain with the host.

## A complete synchronous service

The following service accepts a configuration path at startup and returns a
`ReviewResult` for each artifact. `OpenAIProvider` reads `OPENAI_API_KEY` from
the process environment when no client is supplied.

```python
from pathlib import Path

from proof_goblin import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_INPUT_LIMITS,
    Config,
    OpenAIProvider,
    ReviewResult,
    Reviewer,
)


class ProofService:
    def __init__(
        self,
        config_path: str | Path,
        *,
        model: str = DEFAULT_OPENAI_MODEL,
    ) -> None:
        self.config = Config.load(config_path, limits=DEFAULT_INPUT_LIMITS)
        self.reviewer = Reviewer(
            OpenAIProvider(model=model),
            limits=DEFAULT_INPUT_LIMITS,
        )

    def review_artifact(
        self,
        *,
        artifact: str,
        artifact_name: str,
        artifact_media_type: str,
        review: str,
    ) -> ReviewResult:
        return self.reviewer.review(
            config=self.config,
            review=review,
            artifact=artifact,
            artifact_name=artifact_name,
            artifact_media_type=artifact_media_type,
        )
```

Create the service once for a known configuration, then call it with a review
identifier defined by that bundle:

```python
service = ProofService(
    "proof_goblin/configs/documentation.pgcfg",
    model="gpt-5.6",
)

rendered_document = Path("proof_goblin/docs/getting-started.md").read_text(
    encoding="utf-8"
)

result = service.review_artifact(
    artifact=rendered_document,
    artifact_name="getting-started.md",
    artifact_media_type="text/markdown",
    review="technical_writer_first_pass",
)
```

The example path assumes a source checkout and the repository root as the
working directory. In an application, keep the bundle at an application-owned
path and load it during startup or worker initialization so configuration
errors occur before accepting review work.

The default OpenAI model is also available as `DEFAULT_OPENAI_MODEL`. Pass a
different model explicitly when the host has selected and tested it. To control
SDK-level settings such as timeouts or retries, construct an OpenAI client with
the required policy and pass it as `OpenAIProvider(client=client, model=...)`.

## Review input contract

`Reviewer.review()` accepts keyword-only arguments and returns a
`ReviewResult`:

| Argument | Requirement |
| --- | --- |
| `config` | A validated `Config`. |
| `review` | A non-empty identifier present in `config.reviews`. |
| `artifact` | A non-empty Python string containing the complete text to review. |
| `artifact_name` | A non-empty descriptive string; defaults to `artifact`. |
| `artifact_media_type` | A non-empty descriptive string; defaults to `text/plain`. |

Proof Goblin does not infer or validate media types in the Python API. The host
must decode files or responses to text and select an accurate media type.
Proof Goblin does enforce its shared artifact and assembled-prompt byte limits;
hosts may pass a lower or deliberately higher `InputLimits` policy. See
{doc}`input-limits` for defaults, measurements, and provider preflight.

The artifact digest is SHA-256 over `artifact.encode("utf-8")`; Proof Goblin
does not normalize newlines or other characters first. The configuration digest
is computed over the original `.pgcfg` file bytes as described in
{doc}`Configuration Bundles <configuration>`.

## Execution, scheduling, and retries

`Reviewer.review()` is synchronous and blocking. It assembles the prompt, calls
`Provider.generate()`, validates the complete response, and then returns a
result. It does not return a partial result when any stage fails.

Applications with request-latency constraints should call the service from a
worker or job system. The library-level `Reviewer` does not cache, deduplicate,
or make executions idempotent. The CLI has its own filesystem cache, but that
cache is not applied automatically to library calls.

A retry after a timeout or uncertain provider failure may create another
provider request and additional cost. The host should assign its own job
identity, prevent concurrent duplicates, record attempt state, and apply a
retry policy appropriate to each provider error. A provider response ID is
available only after a successful response and is useful for correlation, not
as a pre-request idempotency key.

## Failure contract

Integrations should handle errors at the boundary where the host can translate
them into job, API, or user-visible states:

- `ConfigError` covers configuration parsing, validation, and missing
  components;
- `PromptBuildError` covers invalid prompt inputs;
- `InputLimitError` covers deterministic configuration, artifact, and prompt
  byte ceilings;
- `ProviderError` covers provider initialization, request, quota, rate-limit,
  refusal, and response failures;
- `ReviewOutputValidationError` covers an invalid configured schema or provider
  output that does not match it; and
- `ReportRenderError` covers unsupported rendering requests.

For example:

```python
from proof_goblin import (
    ConfigError,
    InputLimitError,
    PromptBuildError,
    ProviderError,
    ReviewOutputValidationError,
)


try:
    result = service.review_artifact(
        artifact=rendered_document,
        artifact_name="getting-started.md",
        artifact_media_type="text/markdown",
        review="technical_writer_first_pass",
    )
except ConfigError:
    # Treat as a deployment or configuration defect.
    raise
except InputLimitError:
    # Reject input that exceeds the host's configured deterministic boundary.
    raise
except PromptBuildError:
    # Reject or correct the host-supplied artifact metadata.
    raise
except ProviderError:
    # Map the specific provider subtype to retryable or terminal job state.
    raise
except ReviewOutputValidationError:
    # Preserve diagnostics; no valid ReviewResult was produced.
    raise
```

The provider-specific subclasses and their meanings are listed in
{doc}`OpenAI Provider <openai-provider>`.

## Persist the canonical result

`ReviewResult.to_dict()` returns the current canonical, JSON-compatible record.
`ReviewResult.to_json()` returns the same record as a Python string with
non-ASCII characters preserved, keys sorted, and two-space indentation by
default:

```python
payload = result.to_dict()
payload_json = result.to_json()
```

The record has the following top-level contract:

| Field | Contents |
| --- | --- |
| `format` | The constant `proof-goblin-review-result`. |
| `schema_version` | The result-record schema version, currently `1.0`. |
| `created_at` | A timezone-aware ISO 8601 string. |
| `review` | Non-null strings for the review name, title, description, and four component names. |
| `config` | Name, bundle version, and a SHA-256 string or `null`. |
| `artifact` | Name, media type, and SHA-256 string. |
| `execution` | Provider and model strings, nullable response ID, and nullable integer token counts. |
| `observations` | An array of objects containing string `question` and `evidence` fields. |
| `prompt` | Present only when explicitly requested; contains the complete system and user prompts. |

The bundled JSON Schema is
`proof_goblin/schemas/review-result.v1.schema.json`. An installed host can read
it without assuming a package location:

```python
import json
from importlib.resources import files


schema_text = (
    files("proof_goblin")
    .joinpath("schemas/review-result.v1.schema.json")
    .read_text(encoding="utf-8")
)
result_schema = json.loads(schema_text)
```

The record is versioned, but the project does not yet promise cross-version API
or schema compatibility before Proof Goblin 1.0. Persist both `format` and
`schema_version`, pin the producing Proof Goblin version in the host, and reject
or explicitly migrate records with an unsupported value.

## Sensitive data and retention

The in-memory `ReviewResult` always contains the assembled `Prompt`; its user
portion contains the complete artifact. `to_dict()` and `to_json()` omit that
prompt by default. Include it only under an explicit retention and access
policy:

```python
archival_payload = result.to_dict(include_prompt=True)
archival_json = result.to_json(include_prompt=True)
```

Even without the prompt, observations and evidence may quote sensitive source
material. Provider identifiers, model names, token usage, configuration
identity, and artifact digests may also be operationally sensitive. Apply the
host's authorization, encryption, logging, retention, and deletion policy to
both in-memory work and persisted results. Avoid serializing an entire
`ReviewResult` into a task system merely to pass its default record.

Provider execution sends the assembled prompt to the selected provider. The
OpenAI adapter requests `store=False`, but the host remains responsible for
evaluating the provider's current data-handling terms and suitability for the
artifact.

## Render an existing result

Rendering is local and does not contact a provider:

```python
from proof_goblin import ReportFormat, render_report


text_report = render_report(result, ReportFormat.TEXT)
json_report = render_report(result, ReportFormat.JSON)
markdown_report = render_report(result, ReportFormat.MARKDOWN)
html_report = render_report(result, ReportFormat.HTML)
```

Each call returns a Python string. JSON is the canonical interchange record.
Text, Markdown, and standalone HTML are presentation formats and reject
`include_prompt=True`. HTML escapes all dynamic values. Markdown escapes HTML
and neutralizes provider-produced links and images. These renderers omit the
complete prompt and artifact body, but observation evidence may still quote the
artifact and must be treated according to its sensitivity.

See {doc}`Report Formats <report-formats>` for the full presentation and
escaping contract.

## Test without a live provider

The public `Provider` protocol is the integration seam for deterministic tests.
A fake provider can capture the prompt and return schema-compatible data without
credentials, network access, or API cost:

```python
from proof_goblin import Config, ProviderResponse, Reviewer, TokenUsage


class FakeProvider:
    def generate(self, prompt, output_schema):
        self.prompt = prompt
        self.output_schema = output_schema
        return ProviderResponse(
            data={
                "observations": [
                    {
                        "question": "Where is the prerequisite explained?",
                        "evidence": "The document begins with step two.",
                    }
                ]
            },
            provider="fake",
            model="fake-model",
            response_id="test-response",
            usage=TokenUsage(
                input_tokens=10,
                output_tokens=8,
                total_tokens=18,
            ),
        )


fake = FakeProvider()
config = Config.load("proof_goblin/configs/documentation.pgcfg")
result = Reviewer(fake).review(
    config=config,
    review="technical_writer_first_pass",
    artifact="Begin by running the command.",
    artifact_name="draft.md",
    artifact_media_type="text/markdown",
)

assert result.provider == "fake"
assert result.observations[0].question.startswith("Where")
assert fake.prompt.artifact_name == "draft.md"
```

Use this boundary to test configuration resolution, scheduling logic,
persistence, rendering, and each host-defined failure state. Provider adapter
tests can remain separate and narrowly focused on the external service.
