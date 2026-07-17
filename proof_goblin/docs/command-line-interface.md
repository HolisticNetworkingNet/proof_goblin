# Command-Line Interface

Proof Goblin provides a `proof-goblin` command with separate operations for
inspecting an assembled prompt and executing a live review. The CLI is a thin
interface over the same `Config`, `PromptBuilder`, and `Reviewer` APIs used by
host applications.

Both commands apply the shared default input limits before output, cache
reservation, or provider execution. Configuration files, artifact files,
standard input, the assembled system prompt, and the complete prompt are
bounded deterministically in UTF-8 bytes. Oversized input is rejected without
echoing its content; no input is silently truncated. See {doc}`input-limits`
for the default ceilings and Python host configuration.

## Inspect a Prompt

The `prompt` command loads a configuration, resolves a named review, and prints
the complete system and user messages without contacting an AI provider:

```bash
proof-goblin prompt proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass
```

This command requires only the core package and is useful for validating a
configuration or inspecting exactly what will be sent to a provider.

### Prompt formats and files

The `prompt` command supports plain text, canonical JSON, Markdown, and
standalone HTML. Use `--format` to select the standard-output representation:

```bash
proof-goblin prompt proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --format markdown
```

Use repeatable `--output` arguments to create several representations of the
same assembled prompt. Each filename extension selects its format:

```bash
proof-goblin prompt proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --output overview-prompt.md \
  --output overview-prompt.html \
  --output overview-prompt.json
```

This operation never contacts a provider. Text preserves the terminal
`[SYSTEM]` and `[USER]` representation. JSON is a versioned
`proof-goblin-prompt` record with prompt and provenance fields. Markdown and
HTML add a shareable heading, metadata, sensitive-content warning, and separate
System and User sections. HTML escapes all prompt-derived values; Markdown uses
code fences longer than any backtick sequence in the prompt so Artifact content
cannot close its containing fence. The JSON contract is described by the
bundled `proof_goblin/schemas/prompt.v1.schema.json` schema.

Unlike human-facing review reports, **every prompt format contains the complete
Artifact**. Treat prompt files as sensitive, even when they are created only to
share a proposed review with a colleague. `--format` controls standard output
and cannot be combined with `--output`.

## Run a Review

Install the OpenAI extra and set `OPENAI_API_KEY` before running a live review:

```bash
python -m pip install -e ".[openai]"

proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass
```

The command prints a plain-text report to standard output by default. It
includes the review title and description, stable identifier, resolved
components, artifact identity, creation time, provider metadata, and numbered
observations with their evidence. Use `--model` to override `OPENAI_MODEL` or
the package default.

## Review report formats

Select plain text, JSON, Markdown, or standalone HTML on standard output with
`--format`:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --format markdown
```

The supported values are:

- `text` for terminal-oriented reports;
- `json` for the canonical versioned `ReviewResult` record;
- `markdown` for repositories, documentation systems, and editing; and
- `html` for a safely escaped, self-contained browser document.

See {doc}`report-formats` for their content and security properties.

## File output

Use `--output` to write the complete report to a UTF-8 file. The filename
extension selects the format:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --output technical-writing-review.md
```

Proof Goblin recognizes `.txt`, `.text`, `.json`, `.md`, `.markdown`, `.html`,
and `.htm`. An unrecognized extension produces an error. `--format` controls
standard output and cannot be combined with `--output`, so a file's extension
is always authoritative.

Repeat `--output` to render one provider response in several formats:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --output technical-writing-review.md \
  --output technical-writing-review.html \
  --output technical-writing-review.json
```

Proof Goblin contacts the provider at most once for this command. Every output
therefore has the same response identifier, observations, creation time, and
token usage.

File writes replace the destination atomically after the complete report has
been encoded and flushed. A failed write reports an error and does not replace
an existing report with partial output.

## JSON prompt retention

JSON output uses the same versioned record returned by
`ReviewResult.to_json()`. Prompt text is omitted by default because the user
prompt contains the complete artifact. Add `--include-prompt` together with
JSON output only when an explicit archival policy requires it:

```bash
proof-goblin review artifact.md \
  --config review.pgcfg \
  --review first_pass \
  --include-prompt \
  --output review.json
```

Text, Markdown, and HTML reports never include prompt text or artifact content.
When several files are requested, `--include-prompt` affects only JSON files.

## Review cache

Before contacting the provider, the `review` command looks for a cached result
with the same assembled prompt, provider, and model. A matching result is reused
until the caller explicitly supplies `--refresh`. This lets a later command add
another format without purchasing or generating a different review:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --output technical-writing-review.txt
```

Changing the artifact, configuration, named review, model, or other prompt
content creates a different cache identity and permits a new provider request.
Use `--refresh` only when a new response is deliberately required. Simultaneous
identical requests are prevented; an abandoned reservation is considered stale
after fifteen minutes.

Cached entries are canonical JSON records without the system prompt, user
prompt, or complete artifact body. They can contain model-produced evidence
quoted from the artifact and should still be treated as potentially sensitive.
Proof Goblin creates the cache directory and files with user-only permissions
where the operating system supports them.

The default location is the platform's per-user cache area, including
`~/Library/Caches/proof-goblin` on macOS and `$XDG_CACHE_HOME/proof-goblin` (or
`~/.cache/proof-goblin`) on Linux. Set `PROOF_GOBLIN_CACHE_DIR` to override it.

## Standard Input

Use `-` as the artifact path to read UTF-8 content from standard input. Specify
a media type when it cannot be inferred from a filename:

```bash
printf '%s\n' '# Draft documentation' | proof-goblin prompt - \
  --config proof_goblin/configs/documentation.pgcfg \
  --review business_owner_first_pass \
  --artifact-name draft.md \
  --media-type text/markdown
```

Run `proof-goblin --help`, `proof-goblin prompt --help`, or
`proof-goblin review --help` for the complete option reference. The equivalent
module invocation is `python -m proof_goblin`.
