# Report Formats

Proof Goblin can render a validated `ReviewResult` without contacting a
provider or rerunning the review. Rendering is independent of the command-line
interface, so a host application can produce the same reports directly.

```python
from proof_goblin import ReportFormat, render_report

markdown = render_report(result, ReportFormat.MARKDOWN)
html = render_report(result, ReportFormat.HTML)
```

The command-line interface uses this same boundary for repeated `--output`
arguments and for results recovered from its private filesystem cache. All
requested formats are consequently renderings of one `ReviewResult`, rather
than separate provider responses.

`render_report()` accepts `text`, `json`, `markdown`, and `html`. The public
`ReportRenderer` protocol and the concrete renderer classes provide the same
boundary when a host needs to select or inject a renderer itself. Unsupported
formats and prompt-inclusion combinations raise `ReportRenderError`; see the
{doc}`Error Reference <errors>` for diagnostics and recovery.

## Public Python contracts

```python
def render_report(
    result: ReviewResult,
    report_format: ReportFormat | str = ReportFormat.TEXT,
    *,
    include_prompt: bool = False,
) -> str: ...

def render_prompt(
    prompt: Prompt,
    prompt_format: PromptFormat | str = PromptFormat.TEXT,
) -> str: ...
```

Both functions return the complete document as a Python string, including its
final newline. A format can be the corresponding enum member or its exact,
lowercase string value: `text`, `json`, `markdown`, or `html`. An unsupported
report format raises `ReportRenderError`; an unsupported prompt format raises
`PromptRenderError`.

`ReportRenderer` is the public structural protocol for custom report
renderers. Its method contract is:

```python
def render(
    self,
    result: ReviewResult,
    *,
    include_prompt: bool = False,
) -> str: ...
```

Proof Goblin publishes `TextReportRenderer`, `JsonReportRenderer`,
`MarkdownReportRenderer`, and `HtmlReportRenderer` implementations. Their
`render()` methods have the same signature. `include_prompt=True` is accepted
only by the JSON implementation; the other implementations raise
`ReportRenderError` rather than silently ignoring it.

At the CLI, `--format` selects standard output and defaults to text. An
`--output` path instead selects its format by the case-insensitive final
extension: `.txt` and `.text`, `.json`, `.md` and `.markdown`, or `.html` and
`.htm`. Repeated output paths render the same result in multiple formats.
`--format` and `--output` cannot be combined, so neither silently overrides the
other. Output paths must be unique. `--include-prompt` requires at least one
JSON output and affects only those JSON outputs.

## Report content

Human-facing text, Markdown, and HTML reports include:

- the review title, description, and stable identifier;
- the resolved Proof Lens, Mission, Review Protocol, and Output Schema names;
- configuration name and version;
- artifact name and media type;
- result format, schema version, creation time, and observation count;
- provider, model, response identifier, and token usage; and
- numbered questions with their evidence.

These formats identify the reviewed artifact but do not contain its body as a
dedicated field. They also exclude the system and user prompt text. Questions
and evidence are model-produced content and can quote the artifact, so an
ordinary report is not necessarily safe to disclose. See {doc}`data-handling`
for retention and access-control responsibilities.

## Plain text

Plain text is optimized for terminal output and simple text files. It is the
default when neither a format nor an output path selects another format.

```python
report = render_report(result, "text")
```

## JSON

JSON is the canonical versioned `ReviewResult` record, not a presentation
template. Rendering JSON is equivalent to calling `ReviewResult.to_json()`.

```python
record = render_report(result, "json")
```

Prompt text remains excluded by default. JSON alone supports the explicit
archival option:

```python
archival_record = render_report(result, "json", include_prompt=True)
```

Because the user prompt contains the complete artifact, callers should only use
this option under a deliberate retention and access-control policy.

## Markdown

Markdown reports are intended for repositories, documentation systems, issue
trackers, and subsequent editing. Questions and evidence use quoted blocks so
multiline model output remains associated with the correct observation.

The review title is the page heading. A human-readable creation date in the
local system timezone appears directly below it, followed by the review
description. A precise local timestamp with its UTC offset remains in the
metadata table. Canonical JSON continues to normalize `created_at` to UTC for
portable storage and interchange. Report metadata appears in a native
four-column Markdown table using the sequence key, value, key, value. Key
labels are bold; the table does not depend on HTML, column spans, or custom
colors.

Artifact-derived and model-derived values are HTML-escaped before they enter the
report. This prevents embedded HTML from becoming active when the Markdown is
rendered by a system that permits raw HTML. Link delimiters are encoded so
untrusted values cannot introduce active links or remote images; safe inline
code remains available for identifiers such as configuration filenames.
Specifically, inline values collapse line breaks to spaces, HTML-sensitive
characters are escaped, square brackets become `&#91;` and `&#93;`, table pipes
become `&#124;`, and backticks inside code cells become `&#96;`. Question and
evidence line breaks are preserved inside block quotes.

## Standalone HTML

HTML reports contain their own responsive styles and require no external
assets. All configuration-derived, artifact-derived, and model-derived values
are escaped before interpolation into the document. The report can therefore
display markup-like evidence as text without treating it as executable HTML.
Metadata uses the same fixed four-column key/value structure without column
spans or custom cell colors.

Text, Markdown, and HTML timestamps use the host system's local timezone at
render time. The public rendering API does not provide a timezone override.
Canonical JSON always normalizes `created_at` to UTC.

PDF is not currently supported. The renderer boundary allows another format to
be added without coupling it to provider execution or CLI argument parsing.

## Assembled prompt formats

Assembled prompts have a parallel rendering boundary because they are not
ReviewResults and have different security properties:

```python
from proof_goblin import PromptFormat, render_prompt


markdown_prompt = render_prompt(prompt, PromptFormat.MARKDOWN)
html_prompt = render_prompt(prompt, PromptFormat.HTML)
```

`render_prompt()` accepts `text`, `json`, `markdown`, and `html`. Text preserves
the direct `[SYSTEM]` and `[USER]` representation. JSON produces a versioned
`proof-goblin-prompt` record containing review, configuration, Artifact, and
prompt fields. Markdown and standalone HTML provide shareable human-facing
documents with metadata and separate System and User sections. The JSON record
is described by `proof_goblin/schemas/prompt.v1.schema.json`.

Every assembled-prompt format contains the complete Artifact in its User
section. Prompt rendering therefore never offers an artifact-excluding mode.
HTML escapes dynamic values, while Markdown encloses prompt roles in dynamic
code fences that cannot be closed by backticks in untrusted Artifact content.
Hosts must apply sensitive-data access, retention, and deletion policies to all
prompt renderings.

## Versioned JSON schema contracts

The assembled-prompt record has format identifier `proof-goblin-prompt`, schema
version `1.0`, and published schema
`proof_goblin/schemas/prompt.v1.schema.json`. The review-result record has
format identifier `proof-goblin-review-result`, schema version `1.0`, and
published schema `proof_goblin/schemas/review-result.v1.schema.json`. Their
canonical schema identifiers are, respectively:

- `https://proof-goblin.local/schemas/prompt.v1.schema.json`; and
- `https://proof-goblin.local/schemas/review-result.v1.schema.json`.

Both published schemas explicitly declare JSON Schema Draft 2020-12. Format
identifiers distinguish the two document families; schema versions identify
the contract within a family. Filenames are packaging locations, not values to
substitute for either field.

The prompt record always contains `review`, `config`, `artifact`, and `prompt`
objects. The result record contains `created_at`, review attribution,
configuration and artifact provenance, execution metadata, and normalized
`observations`. Its optional `prompt` object appears only when prompt inclusion
is explicitly requested. It does not serialize `ReviewResult.raw_output` as a
second field: `observations` is the canonical normalized representation of the
validated response.
