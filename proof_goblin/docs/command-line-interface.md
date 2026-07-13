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

The command prints provider metadata followed by numbered observations and
their evidence. Use `--model` to override `OPENAI_MODEL` or the package default.

## JSON Output

Use JSON when another process or host application will consume the result:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --output json
```

The output uses the same versioned record returned by `ReviewResult.to_json()`.
Prompt text is omitted by default because it contains the complete artifact.
Add `--include-prompt` when an explicit archival policy requires it.

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
