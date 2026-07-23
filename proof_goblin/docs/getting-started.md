# Getting Started

Proof Goblin is distributed as the `proof-goblin` package on PyPI. This guide
takes a first-time user from installation to an inspected prompt and an optional
live review without requiring a source checkout.

## Prerequisites

You need Python 3.11 or later and an isolated Python environment. An OpenAI API
key and available API credits are required only for a live review.

Proof Goblin requires Python 3.11 or later and is tested on CPython 3.11 through
3.14. Its wheel is operating-system independent; continuous integration covers
Linux plus representative macOS and Windows lanes.

Create and activate a virtual environment on macOS or Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Or activate it in Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## Install Proof Goblin

Install the core library and command-line interface from PyPI:

```bash
python -m pip install proof-goblin
proof-goblin --help
```

The command should describe the `prompt` and `review` operations. If your shell
cannot find `proof-goblin`, confirm that the virtual environment is active and
repeat the installation with that environment's Python interpreter.

Install the optional OpenAI integration when you want to make live requests:

```bash
python -m pip install "proof-goblin[openai]"
```

## Run an installed-package smoke test

Proof Goblin ships a starter documentation-review configuration. The following
program loads that installed resource and assembles a prompt entirely on the
local machine:

```python
from importlib.metadata import version
from importlib.resources import as_file, files

from proof_goblin import Config, PromptBuilder


bundle = files("proof_goblin").joinpath("configs/documentation.pgcfg")
with as_file(bundle) as config_path:
    config = Config.load(config_path)

prompt = PromptBuilder(config).build(
    review="technical_writer_first_pass",
    artifact="# Draft\n\nThis is a document to review.",
    artifact_name="draft.md",
)

print(version("proof-goblin"))
print(prompt.review_name)
print(prompt.artifact_media_type)
```

The program prints the installed version, `technical_writer_first_pass`, and
`text/markdown`. It does not require an API key, contact a provider, or depend
on files from the repository.

## Inspect a prompt from the command line

The command-line interface works with explicit artifact and `.pgcfg` files. To
try the bundled configuration, copy it into your working directory:

```python
from importlib.resources import files
from pathlib import Path


source = files("proof_goblin").joinpath("configs/documentation.pgcfg")
Path("documentation.pgcfg").write_bytes(source.read_bytes())
```

Create a UTF-8 Markdown file named `draft.md`, then inspect the exact prompt
without contacting a provider:

```bash
proof-goblin prompt draft.md \
  --config documentation.pgcfg \
  --review technical_writer_first_pass
```

A successful command prints two labeled sections: `[SYSTEM]`, containing the
resolved Proof Lens, Mission, Review Protocol, and Output Schema; and `[USER]`,
containing artifact metadata and the artifact to be reviewed. Inspecting this
output is useful before incurring an API request.

The `.md` extension deterministically resolves to `text/markdown`.
Extensionless names fall back to `text/plain`; unrecognized extensions require
`--media-type` so unfamiliar files are reviewed only deliberately. See
{doc}`artifact-media-types` for the complete policy.

An invalid path, malformed configuration, unknown review name, or empty
artifact produces a `proof-goblin: error:` message and a nonzero exit status.
See {doc}`command-line-interface` for the complete command reference.

## Run a live review

Live reviews require the `openai` extra, an OpenAI API key, and available API
credits. Do not put the key in a source file or commit it to version control.

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

The live review sends the complete artifact and selected review instructions to
OpenAI. Reports and CLI cache entries omit prompt fields by default, but
observations and evidence can quote the artifact and should be handled according
to its sensitivity. See {doc}`data-handling` for the complete transmission and
retention lifecycle.

Run a technical-writing review and render the single provider response as both
Markdown and HTML:

```bash
proof-goblin review draft.md \
  --config documentation.pgcfg \
  --review technical_writer_first_pass \
  --output draft-review.md \
  --output draft-review.html
```

The command creates both reports from one provider response. Proof Goblin
caches the result by the exact prepared provider request. Running the same
request again reuses that result rather than making another billable request.
Use interactive `--refresh` when you deliberately want to confirm a replacement,
or `--force-refresh` in a script. See {doc}`command-line-interface` for identity,
compatibility, privacy, and output-format details.

Provider credential, quota, rate-limit, refusal, and response failures are
reported as `proof-goblin: error:` messages. The {doc}`openai-provider` page
describes the provider-specific error categories.

## Contributor source checkout

Repository contributors should clone the project and use an editable install;
normal package users do not need these steps:

```bash
git clone https://github.com/HolisticNetworkingNet/proof_goblin.git
cd proof_goblin
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,test,docs,openai]"
```

On Windows PowerShell, activate the environment with
`.venv\Scripts\Activate.ps1`. Run the local verification suite with:

```bash
ruff check .
ruff format --check .
python -m pytest -q -W error
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```

See {doc}`development` for the complete contributor, CI, dependency-security,
and release-validation workflow.
