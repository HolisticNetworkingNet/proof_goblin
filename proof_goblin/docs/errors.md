# Error Reference

Proof Goblin reports failures at the boundary where a caller can act on them.
The command-line interface presents a consistent diagnostic, while the Python
API exposes focused exception types so hosts can choose their own recovery and
logging behavior.

This page is the authoritative inventory of Proof Goblin's public error
categories. Message examples describe the current diagnostic contract. Text
originating in the operating system, OpenAI SDK, or provider response can vary
between environments and dependency versions.

## Command-line contract

The CLI uses three exit statuses:

| Status | Meaning | Output |
| --- | --- | --- |
| `0` | The command completed successfully. | The requested prompt or report is written to standard output or the selected files. |
| `1` | Proof Goblin recognized an operational failure. | Standard error receives `proof-goblin: error: <detail>`. |
| `2` | Command syntax or argument parsing failed. | `argparse` writes usage information and an argument diagnostic to standard error. |

Status `1` covers the public exception families described below as well as a
small number of CLI-only validation, file-reading, and file-writing failures.
The CLI does not print a traceback for these expected failures.

Argument-parsing errors occur before command execution. Examples include a
missing required option, an unknown option, an invalid `--format` choice, or
using both `--refresh` and `--force-refresh`. Correct the invocation before
retrying.

```text
usage: proof-goblin review ...
proof-goblin review: error: the following arguments are required: -c/--config
```

Operational diagnostics have this shape:

```text
proof-goblin: error: <detail>
```

Automation should use the exit status and documented exception category rather
than parse complete prose. Paths, artifact names, provider refusal text, JSON
locations, and operating-system or SDK diagnostics can appear in `<detail>`.
Treat standard error as potentially sensitive and do not assume that every
upstream diagnostic is redacted by Proof Goblin.

## CLI-only failures

These failures are represented by the CLI's internal `CliError`. It is not
exported from the package and is not part of the Python integration API.

| Condition | Diagnostic shape | Recovery | Retry unchanged? |
| --- | --- | --- | --- |
| An artifact file or standard input cannot be read as UTF-8. | `could not read artifact ...` | Correct the path, permissions, or encoding. | No |
| An output extension is unsupported. | `unsupported output extension ...; use one of: ...` | Select a supported extension. | No |
| `--format` is combined with `--output`. | `--format cannot be combined with --output; use file extensions` | Remove `--format`; each output filename selects its format. | No |
| The same output path is supplied more than once. | `each --output path must be unique` | Remove or rename the duplicate destination. | No |
| `--include-prompt` is requested without JSON output. | `--include-prompt requires JSON output` | Add a `.json` output or remove the option. | No |
| Interactive refresh is impossible. | `--refresh needs an interactive terminal ...; use --force-refresh ...` | Use an interactive terminal or deliberately select `--force-refresh`. | No |
| An invalid cached result is retained after refresh is declined. | `the matching cached result is invalid and was not replaced` | Confirm replacement or deliberately use `--force-refresh`. | No |
| A prompt or report file cannot be written. | `could not write <prompt|report> to ...` | Correct the parent directory, permissions, or destination conflict. | No |

File-reading and file-writing diagnostics can contain local paths and
operating-system text. Output files are prepared before replacement, but when
several destinations are requested, an earlier destination may already have
been written before a later write fails.

## Artifact and input boundaries

### `ArtifactMediaTypeError`

Raised when an artifact name or declared media type cannot identify a supported
decoded textual artifact.

Representative diagnostics include:

- `artifact_name must be a non-empty string`;
- `artifact media type must be a bare ASCII type/subtype without parameters or wildcards`;
- `unsupported artifact media type ...; Proof Goblin accepts decoded textual artifacts only`; and
- `unrecognized artifact file extension ...; provide an explicit artifact media type`.

Correct the artifact name or pass an explicit supported media type. Retrying
unchanged will not help. See {doc}`artifact-media-types` for inference and
normalization rules.

### `InputLimitError`

Raised when configuration bytes, artifact bytes, the assembled system prompt,
or the complete assembled prompt exceed the active `InputLimits` policy.

The stable message shape is:

```text
<boundary> is <measured> UTF-8 bytes; configured limit is <limit> bytes
```

Python callers can use the exception's `boundary`, `measured`, and `limit`
attributes instead of parsing the message. Reduce the input or deliberately
adopt a suitable consistent limits policy before retrying. See
{doc}`input-limits`.

## Configuration

`ConfigError` is the common base class for configuration-specific failures.
`InputLimitError` can also be raised while loading configuration, but it is a
separate boundary exception and is not a subclass of `ConfigError`.

### `ConfigParseError`

Raised when a `.pgcfg` file cannot be read, decoded as UTF-8, or parsed as JSON.
Diagnostics identify the path and can include an operating-system error or a
JSON line and column. Correct the file, permissions, encoding, or JSON syntax;
retrying unchanged will not help.

### `ConfigValidationError`

Raised when decoded configuration does not satisfy Proof Goblin's supported
structure. This includes the `.pgcfg` extension, format identifier, schema
version, required fields, collection shapes, and component references.
Diagnostics identify the failing configuration path or value. Correct the
bundle before retrying.

### `ComponentNotFoundError`

Raised when `Config.review()`, `Config.lens()`, `Config.mission()`,
`Config.protocol()`, or `Config.output_schema()` requests an unknown name.
The diagnostic shape is `Unknown <component type> '<name>'`. Select an existing
component or correct the bundle before retrying.

## Prompt assembly and rendering

### `PromptBuildError`

Raised when prompt assembly receives an invalid direct Python input, such as an
empty artifact or artifact name. Configuration lookup, media-type, and input
limit failures retain their more specific exception types. Correct the caller's
input before retrying.

### `PromptRenderError`

Raised when `render_prompt()` receives an unsupported output format. The
diagnostic lists the supported formats. Select `text`, `json`, `markdown`, or
`html`; retrying unchanged will not help.

Prompt-rendering errors do not contain the prompt body, but every successfully
rendered prompt contains the complete system and user prompts, including the
artifact. Handle the successful output as sensitive content.

## Provider preparation and execution

`ProviderError` is the common base class for model-provider failures.

### `ProviderUnavailableError`

Raised when the provider integration cannot be initialized. For OpenAI this
currently means the optional dependency is unavailable or the SDK client cannot
initialize, commonly because credentials are unavailable. Install the provider
extra or correct the credential environment before retrying.

The initialization diagnostic deliberately gives remediation rather than
including the underlying SDK exception. It does not print an API key.

### `ProviderRequestError`

Raised before provider output is accepted when a request is invalid or known to
be incompatible. Examples include an invalid model name or output-token value,
an output schema that cannot satisfy OpenAI strict-output requirements, a
prepared request that does not match its provider, or a known context-capacity
overrun.

Correct the model, schema, limits, or request construction before retrying.
Ordinary unchanged retries are not appropriate. Preflight failures occur before
Proof Goblin reserves the cache entry or intentionally executes the request.

### `ProviderQuotaError`

Raised when OpenAI reports `insufficient_quota`. The diagnostic directs the
operator to add billing credits or increase the project spending limit. Resolve
the account condition before retrying.

### `ProviderRateLimitError`

Raised when OpenAI returns HTTP status `429` without an
`insufficient_quota` code. The diagnostic recommends waiting briefly before
retrying. A host should bound its own retry policy and account for SDK-level
retry behavior and possible repeated cost.

### `ProviderRefusalError`

Raised when the provider response contains a model refusal. The diagnostic can
include provider-supplied refusal text. Review the artifact and provider policy;
do not retry unchanged in a loop.

### `ProviderResponseError`

Raised for other unusable provider outcomes, including a failed SDK request,
missing output text, invalid JSON, or a structured response whose root is not a
JSON object.

The generic request-failure form includes upstream exception text:

```text
OpenAI request failed: <upstream detail>
```

That detail can vary and should be treated as potentially sensitive. Whether a
retry is safe depends on the underlying failure; an ambiguous transport failure
may have reached the provider and incurred cost even when no usable response
was returned.
The bounded SDK and host retry contract is documented in
{doc}`execution-contract`.

## Review validation

`ReviewError` is the common base class for review-orchestration failures.

### `ReviewOutputValidationError`

Raised after provider execution when the configured output schema is invalid or
the provider's decoded output does not match it. Diagnostics identify either the
schema problem or the failing output location. Correct a confirmed schema defect
before retrying. If the schema is valid, an unchanged retry may produce another
billable response and is not guaranteed to repair the output.

## Cache

### `ReviewCacheError`

Raised when a cached review cannot be safely identified, read, validated,
reserved, or written. Common conditions and recovery are:

| Condition | Diagnostic shape | Recovery |
| --- | --- | --- |
| Cached provenance or JSON is invalid. | `cached review ... is invalid; rerun with --refresh: ...` | Inspect the path if appropriate, then deliberately refresh the result. |
| Another identical request owns the reservation. | `an identical review request is already in progress` | Wait for the active operation to complete before retrying. |
| The cache directory is accessible to other local users on POSIX. | `review cache ... must have user-only permissions` | Restrict the existing directory to its owner. |
| A POSIX cache path is owned by another user. | `review cache ... must be owned by the current user` | Select a cache owned by the process user or correct its ownership outside Proof Goblin. |
| A cache directory or result is a symbolic link, or an entry is not a regular file. | `review cache ... must not be a symbolic link` or `must be a regular file` | Select or restore an ordinary private cache directory and entry. |
| A cache path cannot be prepared, read, reserved, inspected, or written. | `could not <operation> review cache ...` | Correct the path, permissions, storage, or stale reservation condition. |
| Request, response, or cache-key identities disagree. | `<identity> does not match <expected identity>` | Treat this as an integration or state error; do not retry unchanged. |

Cache diagnostics can contain cache paths and validation details. Cached result
files omit prompt text and artifact bodies by default, but observations and
evidence can reproduce sensitive artifact content. See
{doc}`filesystem-boundaries` for the complete cache path contract.

## Reports and stored results

### `ReportRenderError`

Raised when `render_report()` receives an unsupported format or when prompt
inclusion is requested for a non-JSON report. Select a supported format, or use
JSON when an explicit archival policy requires prompt retention. Retrying
unchanged will not help.

### `ReviewResultProvenanceError`

Raised by `ReviewResult.from_dict()` when a serialized result's review,
configuration, or artifact provenance does not match the separately supplied
prompt. Supply the prompt associated with the record or treat the record as
untrusted or stale. Do not suppress the mismatch and continue.

`ReviewResult.from_dict()` also uses ordinary `ValueError` for malformed record
shape, field types, unsupported record versions, and invalid timestamps. Cache
loading converts these deserialization failures into `ReviewCacheError`; direct
Python callers should handle them as invalid external data.

## Python exception hierarchy

All names below except `ReviewCacheError` are exported from `proof_goblin`.
`ReviewCacheError` remains available from `proof_goblin.cache` and is included
because the CLI presents its failures through the public command-line contract.
The CLI-internal `CliError` is omitted from the hierarchy.

```text
ValueError
├── ArtifactMediaTypeError
├── ConfigError
│   ├── ConfigParseError
│   ├── ConfigValidationError
│   └── ComponentNotFoundError (also KeyError)
├── InputLimitError
├── PromptBuildError
├── PromptRenderError
├── ReportRenderError
└── ReviewResultProvenanceError

RuntimeError
├── ProviderError
│   ├── ProviderUnavailableError
│   ├── ProviderRequestError
│   └── ProviderResponseError
│       ├── ProviderQuotaError
│       ├── ProviderRateLimitError
│       └── ProviderRefusalError
├── ReviewCacheError
└── ReviewError
    └── ReviewOutputValidationError
```

Catch the narrowest exception that supports a meaningful recovery. Hosts that
catch a base class should still distinguish retryable operational conditions
from deterministic input and configuration failures. Avoid logging artifacts,
assembled prompts, complete provider output, or exception chains without an
explicit data-handling policy.
