# Artifact Media Types

Proof Goblin accepts decoded text artifacts. A media type describes that text
in prompt and result provenance; it does not cause Proof Goblin to decode,
transcode, or inspect the content.

The CLI, `PromptBuilder`, and `Reviewer` use the same deterministic resolver:

```python
from proof_goblin import resolve_artifact_media_type

media_type = resolve_artifact_media_type("README.md")
assert media_type == "text/markdown"
```

## Resolution order

An explicit value wins over filename inference. Without one, Proof Goblin uses
the case-insensitive final extension of `artifact_name`. Extensionless names,
including the default name `artifact` and CLI name `stdin`, fall back to
`text/plain`. A filename with an unrecognized extension is rejected until the
caller deliberately supplies a supported explicit value.

Inference uses this fixed mapping and never consults the operating system or
Python `mimetypes` database:

| Extensions | Canonical media type |
| --- | --- |
| `.txt` | `text/plain` |
| `.md`, `.markdown` | `text/markdown` |
| `.html`, `.htm` | `text/html` |
| `.css` | `text/css` |
| `.csv` | `text/csv` |
| `.rst` | `text/x-rst` |
| `.py` | `text/x-python` |
| `.js`, `.mjs`, `.cjs` | `text/javascript` |
| `.json` | `application/json` |
| `.xml` | `application/xml` |
| `.yaml`, `.yml` | `application/yaml` |
| `.toml` | `application/toml` |

The map is intentionally modest. A textual file with another extension remains
reviewable when the caller supplies a supported explicit value. This prevents a
mistyped or unexpectedly sensitive filename from silently becoming
`text/plain`.

## Explicit values

Proof Goblin strips surrounding ASCII whitespace, lowercases the value, and
requires a bare ASCII `type/subtype` made from MIME token characters. It rejects
parameters, wildcards, control characters, malformed separators, and empty
values. `application/x-yaml` is accepted as a legacy alias and normalized to
`application/yaml`.

Supported textual types are:

- any syntactically valid `text/*` subtype;
- `application/json` and application subtypes ending in `+json`;
- `application/xml` and application subtypes ending in `+xml`;
- `application/yaml`; and
- `application/toml`.

Other application types and the `image`, `audio`, `video`, `font`, and `model`
top levels are rejected. For example, `application/pdf`,
`application/octet-stream`, and `image/png` are not text-artifact declarations.

Charset parameters such as `text/plain; charset=utf-8` are rejected because the
artifact has already entered Proof Goblin as a decoded Python string. File and
standard-input bytes must be UTF-8 before media-type resolution.

Malformed or unsupported values raise `ArtifactMediaTypeError` before provider
construction, cache reservation, or execution. The canonical value is the only
value stored in the `Prompt`, sent in provider request content, and recorded in
`ReviewResult` provenance.

Media-type validation is a declared-content boundary, not content sniffing.
Proof Goblin does not verify that the artifact body matches its name or declared
type. See {doc}`input-limits` for the separate UTF-8 byte boundaries.
