# Configuration

Proof Goblin separates reusable review content from runtime controls. A
`.pgcfg` bundle defines what a named review asks the model to do. Environment
variables, CLI options, and Python arguments determine which inputs and
execution policies apply to one process or operation.

These surfaces are deliberately not interchangeable:

| Surface | Scope | Typical contents |
| --- | --- | --- |
| Configuration bundle | Portable, versioned review definition | Proof Lenses, Missions, Review Protocols, Output Schemas, and named reviews |
| Environment | Process and provider initialization | OpenAI credentials, CLI model default, and cache location |
| Command line | One invocation | Bundle and review selection, artifact identity, model override, rendering, and cache refresh behavior |
| Python API | One object or call | Input limits, provider output allowance, injected clients, cache directory, and the same review inputs exposed by the CLI |

Proof Goblin has no mutable process-global configuration object. Explicit CLI
and Python values apply at the narrowest scope. Environment values provide only
the documented defaults below. Bundle content never supplies credentials,
filesystem destinations, model selection, or cache policy.

## Configuration bundles

Configuration bundles define reusable review components and the named reviews
assembled from them. Bundles use the `.pgcfg` extension and are UTF-8 JSON
documents, so they can be inspected, compared, and versioned with the artifacts
they review.

Configuration loading is local and deterministic. It validates the bundle but
does not assemble a prompt or contact an AI provider.

### A complete minimal bundle

The following bundle defines one review named `reader_first_pass`. It includes
the complete top-level envelope and one member of each component collection:

```json
{
  "format": "proof-goblin-config",
  "schema_version": "1.0",
  "name": "documentation",
  "version": "0.1.0",
  "lenses": {
    "reader": {
      "description": "A documentation-reader perspective focused on comprehension and use."
    }
  },
  "missions": {
    "clarity": {
      "questions": [
        "What could prevent the reader from understanding or acting?"
      ]
    }
  },
  "protocols": {
    "questions_only": {
      "ask_questions": true,
      "require_evidence": true,
      "rewrite_content": false
    }
  },
  "output_schemas": {
    "observation.v1": {
      "type": "object",
      "additionalProperties": false,
      "required": ["observations"],
      "properties": {
        "observations": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["question", "evidence"],
            "properties": {
              "question": {"type": "string"},
              "evidence": {"type": "string"}
            }
          }
        }
      }
    }
  },
  "reviews": {
    "reader_first_pass": {
      "title": "Reader Documentation Review",
      "description": "Identifies barriers to understanding and acting on the document.",
      "lens": "reader",
      "mission": "clarity",
      "protocol": "questions_only",
      "output_schema": "observation.v1"
    }
  }
}
```

Save a bundle anywhere appropriate to the project, using a `.pgcfg` filename.
The Python example below assumes the minimal bundle was saved as
`documentation.pgcfg` in the current working directory. Paths passed to the
command-line interface or `Config.load()` may be absolute or relative to that
directory.

### Bundle identity and compatibility

The top-level fields have distinct responsibilities:

| Field | Contract and purpose |
| --- | --- |
| `format` | Must be the exact string `proof-goblin-config`. It distinguishes a bundle from other JSON documents. |
| `schema_version` | Must currently be `1.0`. It identifies the structural contract understood by the loader. |
| `name` | A non-empty, author-defined string identifying the bundle. Proof Goblin does not impose a naming pattern. |
| `version` | A non-empty, author-managed bundle revision. It describes the review content, not the loader schema, and has no enforced version format. |

The current Proof Goblin release accepts only configuration schema version
`1.0`; any other value raises `ConfigValidationError`. A bundle author should
change `version` when review content changes according to the project's own
versioning policy. Changing `schema_version` is appropriate only when adopting
a different structural contract supported by Proof Goblin.

Additional top-level fields are allowed and retained in `Config.metadata`. For
example, the bundled documentation configuration includes a `description`.

### Component collections

Every bundle contains five named JSON objects:

- `lenses` define the perspective from which the artifact is examined;
- `missions` define the purpose and priorities of the review;
- `protocols` define the behavioral rules of the review;
- `output_schemas` define the structured response expected from the provider;
  and
- `reviews` select one member from each of the other collections.

Each collection key must be a non-empty string, and every component value must
be a JSON object. Empty collections and unreferenced components are
structurally permitted, although a usable named review needs all four referenced
components.

The loader deliberately does not impose one vocabulary on lenses, missions, or
protocols. Their contents are prompt material and are serialized into the
assembled system prompt. This permits domain-specific fields such as
`knowledge`, `goals`, `circumstances`, or `instructions`.

The loader likewise verifies only that an output-schema component is a JSON
object. To execute a review, that object must also be a JSON Schema suitable for
the selected provider and for local result validation. The OpenAI integration
has additional strict-schema requirements described in {doc}`OpenAI Provider
<openai-provider>`.

### Named reviews

A review combines one Proof Lens, Mission, Review Protocol, and Output Schema.
Every review entry requires six non-empty string fields:

- `title` and `description` provide human-readable presentation metadata;
- `lens`, `mission`, `protocol`, and `output_schema` must exactly match keys in
  their corresponding collections.

The key in the `reviews` object is the review's stable identifier. It is used by
the CLI and Python API for selection and is recorded in result provenance.
`title` is the polished label displayed in reports, while `description` states
what the review is intended to accomplish.

Changing only the title or description does not change the selected components
or the prepared provider request. It does change the configuration digest and
the presentation metadata used for a newly generated result. Cache version 3
keys the exact prepared provider request, so a matching earlier result can be
reused and continues to report its original title, description, and
configuration provenance. Additional fields on a review are retained in
`ReviewDefinition.metadata`.

### Load and use a bundle

`Config.load(path)` accepts a string or `pathlib.Path` and returns a validated
`Config`. The `.pgcfg` extension is required, and the original file is subject
to the configured byte ceiling before JSON parsing.

```python
from pathlib import Path

from proof_goblin import Config, PromptBuilder


config = Config.load(Path("documentation.pgcfg"))
review = config.review("reader_first_pass")

print(review.title)
print(review.lens)

prompt = PromptBuilder(config).build(
    review=review.name,
    artifact="# Draft\n\nSome documentation to review.",
    artifact_name="draft.md",
    artifact_media_type="text/markdown",
)

print(prompt)
```

`config.review()` returns a `ReviewDefinition` containing the stable name,
title, description, four component references, and any additional metadata.
The related accessors `config.lens()`, `config.mission()`, `config.protocol()`,
and `config.output_schema()` return individual component mappings.

`PromptBuilder.build()` resolves the review references and creates the prompt
without contacting a provider. Pass the same `Config` and review identifier to
`Reviewer.review()` to execute a provider-backed review, or use the equivalent
commands described in {doc}`Command-Line Interface <command-line-interface>`.

### Validation and errors

Configuration failures use three focused exception types derived from
`ConfigError`:

- `ConfigParseError` reports files that cannot be read, invalid UTF-8, and
  invalid JSON; JSON syntax errors include line and column information;
- `ConfigValidationError` reports an incorrect extension, format, or schema
  version; missing or invalid fields; invalid collection shapes; and unresolved
  review references; and
- `ComponentNotFoundError` reports a missing name requested through
  `config.review()` or a component accessor.

`InputLimitError` separately reports a configuration file that exceeds the
active `InputLimits` policy. It is not derived from `ConfigError`.

The CLI catches these errors, writes a `proof-goblin: error:` diagnostic to
standard error, and exits with a nonzero status. Python callers may catch the
specific configuration exception or their common `ConfigError` base class.
See {doc}`errors` for the complete CLI contract, exception hierarchy,
diagnostic-sensitivity guidance, and recommended recovery behavior.

The loader validates the structural rules implemented for schema version 1.0;
it does not currently load a separate, published JSON Schema document for the
configuration format.

`Config.from_mapping()` accepts an already-decoded Python object, so it cannot
measure original file bytes. Selected configuration content is still bounded
when it becomes an assembled system prompt. See {doc}`input-limits` for the
complete boundary model.

The supplied mapping is caller-owned. `Config.from_mapping()` validates it,
recursively copies its JSON-compatible content, and stores mappings and
sequences in immutable internal forms. Mutating the original mapping or any of
its nested dictionaries and lists after validation cannot change the returned
`Config`.

The public `lenses`, `missions`, `protocols`, `output_schemas`, `reviews`, and
`metadata` mappings are read-only, including their nested mappings and
sequences. Named component accessors such as `config.mission()` return a fresh
mutable dictionary and fresh nested lists on every call. A caller may adapt
that copy for its own work without changing later access, prompt assembly,
provider validation, or cache identity. Additional review metadata is retained
as a recursively immutable `ReviewDefinition.metadata` mapping.

Construct a new `Config` when configuration state must change. For file-backed
configuration, modifying and reloading the `.pgcfg` file also produces a new
digest. `Config.from_mapping()` has no original byte representation and
therefore continues to use the explicitly supplied `sha256` value or `None`.

### Provenance

`Config.load()` reads the original file bytes before parsing them. The returned
`Config.source_path` is the absolute path produced by `Path.resolve()`—including
resolution of symbolic links—and `Config.sha256` is the SHA-256 digest of those
exact bytes. Consequently, even a whitespace-only file change produces a
different digest. Size inspection, reading, and hashing use one opened regular
file; `source_path` remains an informational name rather than authenticated
file identity. See {doc}`filesystem-boundaries` for concurrent replacement and
symbolic-link behavior.

An assembled prompt carries the bundle name, bundle version, and digest. A
`ReviewResult` records those values along with the review identifier,
presentation metadata, component names, and artifact provenance. The local
configuration path is not serialized into the result because it is
machine-specific. Use `ReviewResult.to_dict()` or `ReviewResult.to_json()` to
produce the versioned result record.

For a substantial working bundle, see
`proof_goblin/configs/documentation.pgcfg` in a source checkout and
{doc}`Bundled Documentation Reviews <bundled-documentation-reviews>`.

## Environment variables

Proof Goblin defines three application-facing environment variables. Provider
SDKs and operating systems can honor additional variables, but those are not
part of Proof Goblin's configuration contract.

| Variable | Consumer and default | Request, cache, and provenance effects | Security and operational notes |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | The default OpenAI SDK client reads it. There is no Proof Goblin default. | It is not included in the prepared request, cache identity, prompt, or result provenance. | Treat it as a secret. Every child process inherits exported values unless the host restricts its environment. An explicitly injected SDK client can obtain credentials another way. |
| `OPENAI_MODEL` | The `review` CLI and bundled live smoke test use it when no model is passed; otherwise they use `gpt-5.6`. `OpenAIProvider()` itself uses `gpt-5.6` unless Python passes `model=` explicitly. | The selected model is part of the provider request and cache identity. The provider's resolved response model is recorded in the result. | The operator is responsible for model availability, compatibility, context, capability, privacy, and cost. |
| `PROOF_GOBLIN_CACHE_DIR` | `ReviewCache()` and the CLI use it when no directory is supplied. Otherwise Proof Goblin uses the platform's per-user cache directory. | It changes where a key is looked up, not how the request key is calculated, and is not recorded in result provenance. | Existing POSIX directories must have user-only permissions. Cached observations and evidence can contain sensitive artifact excerpts. |

On macOS the default cache is `~/Library/Caches/proof-goblin`. Linux uses
`$XDG_CACHE_HOME/proof-goblin` or `~/.cache/proof-goblin`. Windows uses
`%LOCALAPPDATA%\proof-goblin\Cache` when `LOCALAPPDATA` is available and the
corresponding per-user AppData path otherwise.

Credentials and SDK transport settings are intentionally absent from cache
identity. If a host must separate results by account, endpoint, organization,
or another transport boundary, it must use isolated cache directories or its
own cache policy. Inject a configured OpenAI SDK client through
`OpenAIProvider(client=...)` instead of relying on undocumented Proof Goblin
environment behavior.

## Command-line controls

Both commands require an artifact, `--config`, and `--review`. Options affect
either request construction, presentation, or cache reuse:

| Input or option | Default and validation | Processing effect |
| --- | --- | --- |
| `artifact` | Required UTF-8 path, or `-` for standard input | Its complete text enters the user prompt and provider request. Content affects cache identity; its SHA-256 digest is recorded in provenance. |
| `--config PATH` | Required `.pgcfg` path | Selects and validates the bundle. Selected prompt material can affect the request; bundle name, version, and digest are recorded in provenance. |
| `--review NAME` | Required existing review identifier | Selects the four referenced components. Their content can affect the request. The identifier and presentation metadata are recorded in the result. |
| `--artifact-name NAME` | File basename, or `stdin` | Enters the user prompt, cache identity, and artifact provenance. It also supplies extension inference unless a media type is explicit. |
| `--media-type TYPE` | Inferred from the artifact name; extensionless names use `text/plain` and unknown extensions are rejected | The canonical value enters the user prompt, cache identity, and artifact provenance. |
| `--model MODEL` | `OPENAI_MODEL`, then `gpt-5.6` | `review` only. Enters provider preflight, execution, cache identity, and result metadata. |
| `--format FORMAT` | `text` on standard output | Selects `text`, `json`, `markdown`, or `html` rendering. It does not change provider execution, cache identity, or result provenance. |
| `--output PATH` | No file output; repeatable when supplied | The extension selects the rendering format. Output destinations do not affect provider execution or cache identity. |
| `--include-prompt` | Disabled | `review` only. Includes complete prompt text in JSON output; it does not change the cached canonical result. |
| `--refresh` | Disabled | `review` only. Interactively confirms replacement of a matching cached result. It does not change request identity. |
| `--force-refresh` | Disabled | `review` only. Replaces a matching result without confirmation. It does not change request identity. |

The CLI always uses `DEFAULT_INPUT_LIMITS` and the OpenAI provider's 8,192
maximum output-token default. It does not currently expose environment
variables or flags for changing those policies. A host that needs different
values must use the Python API.

See {doc}`command-line-interface` for complete workflows and {doc}`errors` for
argument and operational failure behavior.

## Python controls

Python callers configure individual objects and calls. Constructor and method
arguments take the values passed by the caller; they do not consult a shared
Proof Goblin settings registry.

| API | Control | Default and contract |
| --- | --- | --- |
| `Config.load(path, limits=...)` | Bundle path and file-size policy | `DEFAULT_INPUT_LIMITS`; requires a `.pgcfg` UTF-8 JSON file. |
| `Config.from_mapping(data, limits=...)` | Already-decoded bundle | Measures compact canonical JSON before validation and freezing; the original encoded size is unknowable. |
| `PromptBuilder(config, limits=...)` | Prompt-assembly policy | `DEFAULT_INPUT_LIMITS`; enforces artifact, system-prompt, and total-prompt byte ceilings. |
| `PromptBuilder.build(...)` | Review, artifact, artifact name, and media type | `artifact_name="artifact"`; media type is inferred unless explicit. |
| `Reviewer(provider, limits=...)` | Execution-time prompt and decoded-response policy | `DEFAULT_INPUT_LIMITS`; the reviewer builds, preflights, bounds, and validates using this policy. |
| `Reviewer.preflight(...)` and `Reviewer.review(...)` | Same review inputs as the builder | Prepare the same credential-free provider request; `review()` additionally executes it. |
| `OpenAIProvider(model=..., max_output_tokens=..., timeout_seconds=..., max_retries=..., limits=..., client=...)` | Model, output allowance, transport policy, response policy, and SDK client | Model `gpt-5.6`; 8,192 output tokens; 60-second timeout; two SDK retries; `DEFAULT_INPUT_LIMITS`; lazily created client. An injected client owns its transport policy. |
| `ReviewCache(directory=...)` | Cache storage location | `PROOF_GOBLIN_CACHE_DIR`, then the platform default. This lower-level class is available from `proof_goblin.cache`. |
| `render_prompt(prompt, prompt_format=...)` | Prompt presentation | `text`; every successful format includes the complete prompt and artifact. |
| `render_report(result, report_format=..., include_prompt=..., limits=...)` | Report presentation, optional prompt retention, and output ceiling | `text`, no prompt, and `DEFAULT_INPUT_LIMITS`; prompt inclusion is JSON-only. |

`InputLimits` contains positive-integer byte and nesting ceilings:

| Field | Default |
| --- | ---: |
| `max_config_bytes` | 1,048,576 (1 MiB) |
| `max_artifact_bytes` | 262,144 (256 KiB) |
| `max_total_artifact_bytes` | 262,144 (256 KiB) |
| `max_system_prompt_bytes` | 131,072 (128 KiB) |
| `max_prompt_bytes` | 524,288 (512 KiB) |
| `max_provider_response_bytes` | 1,048,576 (1 MiB) |
| `max_rendered_output_bytes` | 8,388,608 (8 MiB) |
| `max_json_depth` | 64 levels |

Pass the same `InputLimits` value to every boundary used by the host. The CLI
does this for configuration loading and review assembly. Independent Python
objects do not compare policies or detect a mismatch: a host can load a bundle
with one policy, inspect a prompt with another, and execute through a reviewer
with a third. `Reviewer` independently rebuilds and enforces the prompt using
its own policy before provider preflight.

`OpenAIProvider.max_output_tokens` is a token allowance, not an `InputLimits`
byte ceiling. It enters the provider request, preflight assessment, and cache
identity. It is not currently stored as a standalone `ReviewResult` provenance
field. See {doc}`input-limits` for the complete boundary and preflight model.

## Precedence and propagation

The following matrix shows where the major controls matter. “Indirect” means a
value is not stored itself but can change generated content that reaches that
stage.

| Control | Load | Prompt assembly | Provider request | Cache identity or reuse | Result provenance | Rendering |
| --- | --- | --- | --- | --- | --- | --- |
| Selected Lens, Mission, Protocol, and Output Schema content | Validated | Included in the system prompt | Included | Included | Component names only | Review metadata displayed |
| Bundle `name`, `version`, digest, and extra metadata | Recorded | Carried as prompt provenance, not prompt text | No direct effect | No direct effect in cache v3 | Name, version, and digest; extra metadata omitted | Name and version displayed |
| Review identifier, title, and description | Validated | Identifier carried as provenance; referenced content is resolved | Indirect through selected content | Indirect; labels alone do not change the request key | Recorded | Displayed |
| Artifact text | Read and bounded by the CLI | Included as untrusted user content | Included | Included | SHA-256 only by default | Can be retained with an explicit prompt-inclusive format |
| Artifact name and media type | Resolved and validated | Included in user content | Included | Included | Recorded | Displayed |
| `InputLimits` | Configuration and CLI artifact bytes | Enforced before and after the provider call | Values are not keyed directly | Values are not keyed directly | Not recorded | Enforces complete rendered bytes |
| Model | No effect | No effect | Included | Included | Resolved response model recorded | Displayed |
| Maximum output tokens | No effect | No effect | Included | Included | Not recorded as a standalone field | No direct effect |
| Credentials and SDK transport | No effect | No effect | Applied by the SDK at execution | Excluded | Not recorded | No direct effect |
| Cache directory and refresh mode | No effect | No effect | No effect | Select storage or replacement behavior; request key unchanged | No effect | No effect |
| Output format, destination, and prompt inclusion | No effect | No effect | No effect | No effect | Canonical result unchanged | Select presentation and retention |

For the CLI, explicit `--model` takes precedence over `OPENAI_MODEL`, which
takes precedence over `gpt-5.6`. Explicit `--artifact-name` and `--media-type`
take precedence over filename-derived values. An output filename extension is
authoritative when `--output` is used; `--format` cannot be combined with file
outputs. `--refresh` and `--force-refresh` are mutually exclusive.

For Python, explicit arguments are authoritative. `OpenAIProvider()` does not
read `OPENAI_MODEL`; pass `model=` when a host wants environment-derived model
selection. A supplied `client=` replaces lazy construction of the default
OpenAI SDK client.

## Trust and data-handling boundaries

A `.pgcfg` bundle is application-controlled instruction material, not
untrusted artifact content. The selected Lens, Mission, Review Protocol, and
Output Schema are serialized into the privileged system prompt. The output
schema is also sent as the provider's structured-output contract and used for
local response validation. Hosts must authorize and protect bundle files with
the same care as other application behavior or policy configuration.

The configuration SHA-256 digest records exact loaded bytes for provenance and
change detection. It is not a signature, does not identify an author, and does
not prove that a bundle was approved. Proof Goblin does not authenticate or
authorize a bundle path.

Do not place credentials, personal data, or unnecessary secrets in bundle
components. Selected component content is transmitted to the provider. Bundle
name, version, review title, and review description are retained in result
metadata; additional bundle and review metadata are retained in memory but are
not part of the canonical result record.

Environment variables are inherited process state. Restrict which processes
receive provider credentials, avoid printing their environment, and do not
assume that upstream SDK diagnostics share Proof Goblin's stable error wording.
Prompt-inclusive files contain the complete artifact and configuration-derived
system prompt. Cached results omit those prompt fields but can still contain
sensitive model-produced evidence. See {doc}`data-handling` for the full path
from configuration and artifact inputs through provider transmission, caching,
reports, retention, and deletion.
