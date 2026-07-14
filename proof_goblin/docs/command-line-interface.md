# Command-Line Interface

Proof Goblin provides a `proof-goblin` command with separate operations for
inspecting an assembled prompt and executing a live review. The CLI is a thin
interface over the same `Config`, `PromptBuilder`, and `Reviewer` APIs used by
host applications.

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

## Report formats

Select plain text, JSON, Markdown, or standalone HTML with `--format`:

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

Use `--output` to write the complete report to a UTF-8 file instead of standard
output:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --format markdown \
  --output technical-writing-review.md
```

When `--format` is omitted, Proof Goblin recognizes `.txt`, `.text`, `.json`,
`.md`, `.markdown`, `.html`, and `.htm`. An unrecognized extension produces an
error and requires an explicit format. An explicit `--format` always wins,
regardless of the output filename.

File writes replace the destination atomically after the complete report has
been encoded and flushed. A failed write reports an error and does not replace
an existing report with partial output.

## JSON prompt retention

JSON output uses the same versioned record returned by
`ReviewResult.to_json()`. Prompt text is omitted by default because the user
prompt contains the complete artifact. Add `--include-prompt` together with
`--format json` only when an explicit archival policy requires it:

```bash
proof-goblin review artifact.md \
  --config review.pgcfg \
  --review first_pass \
  --format json \
  --include-prompt \
  --output review.json
```

Text, Markdown, and HTML reports never include prompt text or artifact content.

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
