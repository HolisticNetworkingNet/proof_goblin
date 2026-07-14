# Report Formats

Proof Goblin can render a validated `ReviewResult` without contacting a
provider or rerunning the review. Rendering is independent of the command-line
interface, so a host application can produce the same reports directly.

```python
from proof_goblin import ReportFormat, render_report

markdown = render_report(result, ReportFormat.MARKDOWN)
html = render_report(result, ReportFormat.HTML)
```

`render_report()` accepts `text`, `json`, `markdown`, and `html`. The public
`ReportRenderer` protocol and the concrete renderer classes provide the same
boundary when a host needs to select or inject a renderer itself.

## Report content

Human-facing text, Markdown, and HTML reports include:

- the review title, description, and stable identifier;
- the resolved Proof Lens, Mission, Review Protocol, and Output Schema names;
- artifact name, media type, and SHA-256 digest;
- creation time and observation count;
- provider, model, and response identifiers; and
- numbered questions with their evidence.

These formats identify the reviewed artifact but do not contain its body. They
also exclude the system and user prompt text.

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

Artifact-derived and model-derived values are HTML-escaped before they enter the
report. This prevents embedded HTML from becoming active when the Markdown is
rendered by a system that permits raw HTML.

## Standalone HTML

HTML reports contain their own responsive styles and require no external
assets. All configuration-derived, artifact-derived, and model-derived values
are escaped before interpolation into the document. The report can therefore
display markup-like evidence as text without treating it as executable HTML.

PDF is not currently supported. The renderer boundary allows another format to
be added without coupling it to provider execution or CLI argument parsing.
