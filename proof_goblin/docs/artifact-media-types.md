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

## Public Python contract

```python
def resolve_artifact_media_type(
    artifact_name: str,
    explicit_media_type: str | None = None,
) -> str: ...
```

`artifact_name` is the name used for inference and must be a non-empty string.
`explicit_media_type`, when supplied, is validated and takes precedence over
the name. The function returns the canonical media-type string or raises
`ArtifactMediaTypeError`; it performs no file access or content inspection.

The corresponding parameter names at the other public boundaries are:

| Boundary | Artifact name | Explicit media type |
| --- | --- | --- |
| CLI | `--artifact-name` | `--media-type` |
| `PromptBuilder.build()` | `artifact_name` | `artifact_media_type` |
| `Reviewer.preflight()`, `prepare()`, and `review()` | `artifact_name` | `artifact_media_type` |

The builder and reviewer pass their `artifact_media_type` value to the
resolver as its `explicit_media_type` argument. All three boundaries therefore
produce the same canonical value and errors.

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

Only the final path component and its final dot are significant. Both `/` and
`\` are recognized as path separators, so `archive.v2/DRAFT.MD` resolves from
`.MD`, and `draft.notes.md` resolves from `.md`. A dotfile such as `.env` is
treated as having the extension `.env`, while `draft.` has the extension `.`;
both are unrecognized and require an explicit media type. A name with no dot at
all is the extensionless case and resolves to `text/plain`.

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
standard-input bytes must be UTF-8 before media-type resolution. Direct Python
callers supply `str` content and are responsible for any earlier byte decoding;
the CLI reads files as bytes and decodes them strictly as UTF-8.

Malformed or unsupported values raise `ArtifactMediaTypeError` before provider
construction, cache reservation, or execution. The canonical value is the only
value stored in the `Prompt`, sent in provider request content, and recorded in
`ReviewResult` provenance. See the {doc}`Error Reference <errors>` for its
diagnostic categories, import path, and recovery guidance.

Media-type validation is a declared-content boundary, not content sniffing.
Proof Goblin does not verify that the artifact body matches its name or declared
type. See {doc}`input-limits` for the separate UTF-8 byte boundaries.
