# Prompt Assembly

This procedure assembles a named review and a text artifact into an inspectable
`Prompt`. It is the boundary between choosing review behavior and asking an AI
provider to perform the review. Assembly is local and deterministic: it does
not require an API key, make a network request, or incur provider charges.

For definitions of Artifact, Proof Lens, Mission, Review Protocol, Output
Schema, Named Review, and Assembled Prompt, see {doc}`Core Concepts <concepts>`.

## Before you begin

You need:

- Python 3.11 or later with Proof Goblin installed;
- a valid {doc}`configuration bundle <configuration>` in a `.pgcfg` file;
- the identifier of a named review in that bundle; and
- a text artifact to review.

The example below uses files included in the source checkout and assumes that
the current directory is the repository root. See {doc}`Getting Started
<getting-started>` for installation instructions.

## 1. Load the configuration and artifact

Load the configuration once, then read the artifact explicitly as UTF-8 text:

```python
from pathlib import Path

from proof_goblin import Config, PromptBuilder

config = Config.load("proof_goblin/examples/restaurants.pgcfg")
artifact_path = Path("proof_goblin/examples/homepage.html")
artifact = artifact_path.read_text(encoding="utf-8")

builder = PromptBuilder(config)
review_name = "homepage_first_pass"
```

`Config.load()` accepts a string or `Path` and returns a validated `Config`.
Unreadable or malformed input raises `ConfigParseError`; content that does not
conform to the supported configuration schema raises `ConfigValidationError`.
Their diagnostic and recovery contracts are defined in the
{doc}`Error Reference <errors>`.

## 2. Resolve and inspect the named review

Resolution verifies that the named review and each component it references
exist before an artifact is assembled:

```python
resolved = builder.resolve(review_name)

print(resolved.definition.name)
print(resolved.definition.title)
print(resolved.definition.description)
print(resolved.definition.lens)
print(resolved.definition.mission)
print(resolved.definition.protocol)
print(resolved.definition.output_schema)
```

`resolve()` returns a `ResolvedReview`. Its `definition` preserves the review's
identifier, presentation text, and component identifiers. Its `lens`,
`mission`, `protocol`, and `output_schema` attributes contain the resolved
component mappings that will be placed in the system prompt. An unknown review
or component identifier raises `ComponentNotFoundError`.

This step is useful when a host application needs to show users what a review
will do before building or executing it.

## 3. Build the prompt

```python
prompt = builder.build(
    review=review_name,
    artifact=artifact,
    artifact_name=artifact_path.name,
)
```

The omitted media type is deterministically inferred as `text/html` from the
artifact name. An explicit supported value would take precedence.

`build()` returns a `Prompt` with:

- `system` — the resolved review instructions;
- `user` — the artifact, its name, and its media type;
- `review_name`, `config_name`, and `config_version`;
- `config_sha256`; and
- `artifact_name`, `artifact_media_type`, and `artifact_sha256`; and
- `measurements`, containing artifact, system-prompt, user-prompt, and total
  UTF-8 byte counts.

The `system` and `user` values remain separate so a provider can preserve their
message roles. Artifact content is confined to the user prompt and explicitly
marked as untrusted review material. Empty artifact text or names raise
`PromptBuildError`. Invalid or unsupported media types raise
`ArtifactMediaTypeError`; see {doc}`artifact-media-types` for inference,
normalization, and the supported textual boundary.
Input that exceeds the builder's `InputLimits` raises `InputLimitError` without
including input text in the diagnostic. See {doc}`input-limits` for the default
ceilings and host configuration interface, and the {doc}`Error Reference
<errors>` for the complete assembly-error hierarchy and recovery guidance.

## 4. Inspect or render the result

Printing a `Prompt` produces a readable representation with `[SYSTEM]` and
`[USER]` sections:

```python
print(prompt)
```

Use `render_prompt()` when the assembled prompt needs to be inspected, stored,
or shared in a specific format:

```python
from proof_goblin import PromptFormat, render_prompt

markdown = render_prompt(prompt, PromptFormat.MARKDOWN)
Path("homepage-prompt.md").write_text(markdown, encoding="utf-8")
```

Text, versioned JSON, Markdown, and standalone HTML are supported. Every format
contains the complete artifact and must be handled as sensitive content. See
{doc}`Command-Line Interface <command-line-interface>` for the equivalent
`proof-goblin prompt` command and {doc}`Report Formats <report-formats>` for
the rendering and escaping contract.

## Determinism and provenance

Given the same validated configuration content, review identifier, exact
artifact string, artifact name, and resolved media type, `PromptBuilder` produces the
same `system` and `user` strings and the same provenance values. No whitespace,
line-ending, or Unicode normalization is performed.

The configuration digest is calculated from the original `.pgcfg` bytes. The
artifact digest is calculated from the UTF-8 encoding of the artifact string.
These SHA-256 values identify the inputs; they do not conceal the artifact or
make a rendered prompt safe to publish.

## What happens next

Prompt assembly ends with an inspectable `Prompt`. Choose the next path based
on what the application needs to do:

- **Inspect or share the prompt:** use `render_prompt()` or the
  `proof-goblin prompt` command. No provider is contacted.
- **Perform a review:** construct a `Reviewer` with a provider and call
  `Reviewer.review()` with the same configuration, review identifier, artifact,
  artifact name, and media type. The reviewer rebuilds the prompt internally,
  calls the provider, validates the response, and returns a `ReviewResult`.
- **Add Proof Goblin to an application:** continue with {doc}`Host Application
  Integration <host-integration>` for the complete provider and serialization
  workflow.

`Reviewer.review()` does not accept a previously assembled `Prompt`. The
separate assembly step is an inspection and validation boundary; the normal
execution path deliberately owns prompt construction and result validation as
one operation. See {doc}`OpenAI Provider <openai-provider>` before making a live
OpenAI request.
