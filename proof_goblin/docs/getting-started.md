# Getting Started

Proof Goblin is not yet published as an installable release. Until it is,
install the project from its GitHub repository. This guide takes you from a
clean checkout to an inspected prompt and an optional live review.

## Prerequisites

You will need:

- Python 3.11 or later;
- Git;
- an isolated Python environment; and
- an OpenAI API key only if you intend to run a live review.

Proof Goblin does not yet publish a formal operating-system support matrix.
Most examples below use POSIX shell syntax. PowerShell alternatives are shown
where activation or environment-variable syntax differs; PowerShell uses a
backtick rather than a backslash when splitting a command across lines.

## Clone the repository

```bash
git clone https://github.com/holisticnetworking/proof_goblin.git
cd proof_goblin
```

Unless a section says otherwise, run the remaining commands from this
repository root. The examples use paths relative to it.

## Create an isolated environment

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Or activate it in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Your shell prompt will normally show `(.venv)` while the environment is
active. You can also confirm which interpreter is in use:

```bash
python -c "import sys; print(sys.executable)"
```

The printed path should point inside the repository's `.venv` directory.

## Install the project

For the complete workflow in this guide, install Proof Goblin in editable mode
with its OpenAI integration:

```bash
python -m pip install -e ".[openai]"
```

Optional dependency groups can be installed separately or combined according
to the work you intend to do:

| Task | Installation command |
| --- | --- |
| Core library and prompt inspection only | `python -m pip install -e .` |
| Live OpenAI reviews | `python -m pip install -e ".[openai]"` |
| Build the documentation | `python -m pip install -e ".[docs]"` |
| Run the test suite | `python -m pip install -e ".[test]"` |
| Contribute across the project | `python -m pip install -e ".[openai,docs,test]"` |

Verify that the command-line interface is available:

```bash
proof-goblin --help
```

The command should describe the `prompt` and `review` operations. If your shell
cannot find `proof-goblin`, confirm that the virtual environment is active and
repeat the installation command with that environment's Python interpreter.

## Inspect a prompt without contacting a provider

Proof Goblin can validate a configuration and assemble the exact prompt for a
review without using an API key or contacting an AI provider:

```bash
proof-goblin prompt proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass
```

A successful command exits without an error and prints two labeled sections:
`[SYSTEM]`, containing the resolved Proof Lens, Mission, Review Protocol, and
Output Schema; and `[USER]`, containing artifact metadata and the artifact to be
reviewed. Inspecting this output is a useful check before incurring an API
request.

The `.md` extension deterministically resolves to `text/markdown`.
Extensionless names fall back to `text/plain`; unrecognized extensions require
`--media-type` so unfamiliar files are reviewed only deliberately. An explicit
supported textual type also overrides a recognized filename. See
{doc}`artifact-media-types` for the complete policy.

An invalid path, malformed configuration, unknown review name, or empty
artifact produces a `proof-goblin: error:` message and a nonzero exit status.
See {doc}`command-line-interface` for the complete command reference.

## Run a live review

Live reviews require the `openai` dependency group, an OpenAI API key, and
available API credits. Set the key in the environment used by Proof Goblin. Do
not put it in a source file or commit it to version control.

For a temporary value on macOS or Linux:

```bash
export OPENAI_API_KEY="replace-with-your-api-key"
```

For the current PowerShell session on Windows:

```powershell
$env:OPENAI_API_KEY = "replace-with-your-api-key"
```

Your shell may save commands in its history. See {doc}`openai-provider` for a
hidden-input example and additional provider details.

Run a technical-writing review and render the single provider response as both
Markdown and HTML:

```bash
proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass \
  --output overview-review.md \
  --output overview-review.html
```

The command should create both files in the repository root. Each report begins
with the review title and description, followed by review metadata and numbered
observations. The two files contain the same observations, response identifier,
creation time, and token usage because Proof Goblin contacts the provider only
once and renders that result into both formats.

Proof Goblin caches the result by the exact prepared provider request. Running
the same request again reuses that result rather than making another billable
request. Use interactive `--refresh` when you deliberately want to confirm a
replacement, or `--force-refresh` in a script. See
{doc}`command-line-interface` for identity, compatibility, privacy, and
output-format details.

Provider credential, quota, rate-limit, refusal, and response failures are
reported as `proof-goblin: error:` messages. The {doc}`openai-provider` page
describes the provider-specific error categories.

## Run the tests

After installing the `test` dependency group, run the complete test suite:

```bash
python -m pytest
```

The tests do not require an API key and do not make live provider requests.

## Build the documentation

After installing the `docs` dependency group, run Sphinx from the repository
root with warnings treated as errors:

```bash
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```

The generated site will be available at
`proof_goblin/docs/_build/html/index.html`.

The documentation directory also includes a Makefile, so environments with the
external `make` utility installed can run `make html` from
`proof_goblin/docs`. `make` is a convenience, not a Python dependency or a
requirement for building the documentation.

## PyCharm

Use the project's `.venv` environment as the PyCharm interpreter. Install the
dependency groups needed by your work; after installing the `docs` group,
Sphinx, MyST, and Furo will be available to both the terminal and any Sphinx run
configuration you create in PyCharm. Set `OPENAI_API_KEY` in the run
configuration's environment when running a live review from the IDE.
