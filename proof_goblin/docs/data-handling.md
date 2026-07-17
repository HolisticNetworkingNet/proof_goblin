# Data Handling and Retention

Proof Goblin processes text that may be private, proprietary, regulated, or
otherwise sensitive. The immediate warning remains in each workflow page; this
reference traces the same data across configuration loading, prompt assembly,
provider execution, results, caching, and rendering.

The short version is:

- a live review sends the complete artifact and selected review instructions
  to the configured provider;
- an in-memory `ReviewResult` retains the complete assembled prompt and decoded
  provider output;
- canonical results and CLI cache files omit prompt text and the complete
  artifact body by default, but observations and evidence can quote the
  artifact;
- prompt renderings and prompt-inclusive JSON contain the complete artifact;
  and
- Proof Goblin does not impose a retention period or delete host records,
  output files, or completed cache entries automatically.

## End-to-end lifecycle

| Stage | Data present | Network or persistence behavior |
| --- | --- | --- |
| Configuration loading | Original `.pgcfg` bytes, decoded bundle content, source path, and SHA-256 digest | Local only. `Config.load()` retains validated content, the resolved path, and the digest in memory. It does not contact a provider or write another file. |
| Artifact loading | Complete decoded artifact text, name, media type, and SHA-256 digest | The CLI reads UTF-8 locally. Python hosts supply an already-decoded string. Loading alone does not contact a provider or persist another copy. |
| Prompt assembly | Fixed instructions; selected Lens, Mission, Review Protocol, and Output Schema; artifact name, media type, and complete text; configuration and artifact provenance | Local and in memory. Every `Prompt` retains separate system and user strings. Every rendered prompt contains both strings and therefore the complete artifact. |
| Provider request | Model; system prompt as provider instructions; user prompt as input; selected Output Schema as the strict response schema; maximum output allowance; and generation controls | A live review sends these values to the provider. The OpenAI adapter sets `truncation="disabled"` and `store=False`. Provider-side transport, logging, abuse monitoring, retention, residency, training-use, and deletion remain governed by the account and provider's current terms. |
| Provider authentication | API credentials and any SDK transport settings | The SDK applies credentials to authenticate the network request. Proof Goblin does not place the API key in the prompt, credential-free `ProviderRequest`, cache identity, or result provenance. |
| Provider response | Provider response object, decoded structured output, provider and model identity, response identifier, and token usage | Received into memory. Proof Goblin validates and normalizes the structured output. It does not automatically persist the provider's SDK response object. |
| In-memory `ReviewResult` | Normalized observations, complete `Prompt`, attribution and provenance, execution metadata, and decoded `raw_output` | Remains in memory for as long as the host retains the object. The raw decoded output is not serialized as a separate canonical-record field. |
| Canonical result | Review and configuration metadata; artifact name, media type, and digest; execution metadata; and normalized questions and evidence | `to_dict()` and `to_json()` omit the prompt by default. `include_prompt=True` adds complete system and user prompt text. Observations and evidence can reproduce artifact content in either form. |
| CLI cache | Default canonical result without prompt fields | Stored as per-user JSON files. The cache omits the complete prompt and artifact body as fields, but can contain sensitive evidence. Completed entries have no automatic expiration; the operator controls deletion. |
| Reports and standard output | Result metadata, observations, and evidence; optionally prompt text in JSON | Text, Markdown, and HTML reports omit prompt fields and the artifact body as a dedicated field. Their observations may still quote it. JSON includes the prompt only when explicitly requested. Files and captured standard output remain until their owner removes them. |
| Diagnostics | Proof Goblin detail plus, for some failures, paths, identifiers, provider refusal text, or upstream SDK and operating-system text | Written to standard error by the CLI or exposed as Python exceptions. Treat diagnostics and logs as potentially sensitive. See the {doc}`Error Reference <errors>`. |

`store=False` is one provider request control. It does not by itself promise
that the provider performs no transient processing, security logging, abuse
monitoring, or other retention permitted by the applicable service terms. An
operator must evaluate the current provider and account policy before sending
sensitive material.

## What crosses the provider boundary

For the bundled OpenAI adapter, the prepared request contains:

- the model name;
- the complete system prompt under `instructions`;
- the complete user prompt under `input`;
- the selected Output Schema under the strict structured-output format;
- the maximum output-token allowance;
- disabled truncation; and
- `store=False`.

The system prompt contains the selected configuration components. The user
prompt contains the artifact name, canonical media type, and complete artifact
inside the untrusted-artifact delimiters. Bundle-level metadata that is not
selected into the prompt, the local configuration path, output destinations,
cache directory, and input-limit values are not provider request fields.

The credential-free prepared request is also the CLI cache identity. API
credentials and SDK transport settings are excluded. Consequently, two
executions using different credentials or transport settings can address the
same cache key when their prepared provider parameters are otherwise
identical. A host that requires isolation by account, endpoint, organization,
tenant, or another transport boundary must isolate cache storage or supply its
own caching policy.

## Results are still potentially sensitive

Omitting prompt text is a useful default, not a sanitization guarantee. A model
is explicitly asked to cite evidence, so a question or evidence field can
repeat names, sentences, identifiers, secrets, or other source material from
the artifact. Result metadata can also reveal:

- artifact names, media types, and digests;
- bundle and review identity;
- provider and model selection;
- provider response identifiers;
- token usage and execution time; and
- the local timezone in human-facing reports.

Treat cached results and ordinary reports according to the artifact's
sensitivity unless a separate review establishes that disclosure is safe.
Escaping in the built-in Markdown and HTML renderers prevents dynamic values
from becoming active markup in those formats; it does not make their text
non-sensitive or authorize downstream actions based on model output.

Model-produced observations remain untrusted dynamic content. Custom
renderers, host interfaces, issue creation, automation, and other downstream
consumers must apply context-appropriate escaping, authorization, and action
validation.

## Retention and deletion ownership

Proof Goblin has no project-wide retention clock. Each owner controls the data
it stores:

| Owner | Responsibility |
| --- | --- |
| CLI operator | Choose appropriate artifact, prompt, report, and cache locations; protect terminal and CI output; remove output files and completed cache entries according to local policy. |
| Python host | Bind artifacts, jobs, results, and rendered output to the correct user or tenant; authorize access; choose encryption and storage; define retention and deletion; and avoid logging sensitive values without a policy. |
| Provider account owner | Confirm that sending the selected data is authorized and compatible with current provider retention, privacy, training-use, residency, deletion, and account settings. |
| Proof Goblin | Apply documented local limits, separate prompt roles, validate provider output, omit prompt text from default canonical records, and use private cache permissions where the operating system supports them. |

The CLI cache is an optimization, not an application database. It provides no
tenant model, retention schedule, archival workflow, or deletion command.
`PROOF_GOBLIN_CACHE_DIR` selects its location. On POSIX systems, Proof Goblin
creates new cache directories and files with user-only permissions and rejects
an existing cache directory that is accessible to other users. That operating-
system user boundary is not a substitute for application authorization.
The cache's POSIX ownership, mode, regular-file, and symbolic-link checks—and
the corresponding Windows limitation—are defined in
{doc}`filesystem-boundaries`.

An abandoned cache reservation becomes stale after fifteen minutes; that rule
applies only to in-progress lock files. It is not an expiration policy for
completed review results.

## Controls that change retained data

| Control | Effect |
| --- | --- |
| `proof-goblin prompt` | Contacts no provider, but every successful output contains the complete artifact and selected configuration-derived prompt. |
| `proof-goblin review` | Sends the assembled prompt and response schema to OpenAI, then caches the canonical result by default. |
| `--include-prompt` | Adds complete system and user prompt text to JSON review output. It does not add prompt text to the CLI cache entry. |
| `--output PATH` | Writes a prompt or report to the selected local path. Multiple formats render one in-memory object. |
| `PROOF_GOBLIN_CACHE_DIR` | Changes cache storage location, not cache identity or result provenance. |
| `ReviewResult.to_dict(include_prompt=True)` or `to_json(include_prompt=True)` | Adds the complete prompt to a host-created canonical record. |
| Direct `Reviewer` use | Performs no Proof Goblin caching or persistence. The host decides whether and how to store the returned in-memory result. |

Neither `--refresh` nor `--force-refresh` deletes other cache entries. They
control whether the matching request result is reused or replaced.

## Practical handling checklist

Before a live review:

- confirm that the artifact and selected configuration content may be sent to
  the provider;
- select the intended provider account, model, cache boundary, and retention
  policy;
- avoid placing credentials or unrelated secrets in `.pgcfg` components; and
- decide whether ordinary result evidence is permitted to quote the artifact.

Before saving or sharing output:

- distinguish a prompt rendering from an ordinary report;
- remember that ordinary observations can still reproduce source text;
- protect output paths, terminal capture, CI logs, caches, and host storage;
- bind persisted results to the correct user or tenant; and
- define how the stored value will be found and deleted when its retention
  period ends.

For configuration precedence and cache effects, see {doc}`configuration`. For
format-specific content and escaping, see {doc}`report-formats`. For host-owned
persistence, see {doc}`host-integration`.
