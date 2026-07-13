# Getting Started

Proof Goblin is not yet published as an installable release. For development,
clone the repository and use an isolated Python environment.

## Install the project

From the repository root, install Proof Goblin in editable mode with its test
dependencies:

```bash
python -m pip install -e ".[test]"
```

Add the `openai` extra when the project needs to run live reviews, or the `docs`
extra when working on this documentation:

```bash
python -m pip install -e ".[openai,docs,test]"
```

## Verify the installation

The complete test suite does not require an API key:

```bash
python -m pytest
```

## Build a prompt without contacting a provider

Configuration loading and prompt assembly are deterministic. This is the
smallest useful local check:

```python
from pathlib import Path

from proof_goblin import Config, PromptBuilder


config = Config.load("proof_goblin/configs/documentation.pgcfg")
artifact = Path("proof_goblin/docs/overview.md").read_text()

prompt = PromptBuilder(config).build(
    review="technical_writer_first_pass",
    artifact=artifact,
    artifact_name="overview.md",
    artifact_media_type="text/markdown",
)

print(prompt)
```

The same operation is available as
`proof-goblin prompt`; see {doc}`command-line-interface`. To execute a live
review, continue to {doc}`openai-provider`.

## Build the documentation

Run Sphinx with warnings treated as errors:

```bash
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```

The generated site will be available at
`proof_goblin/docs/_build/html/index.html`.

You can also build from the `docs` directory with:

```bash
make html
```

## PyCharm

Use the project's virtual environment as the PyCharm interpreter. After
installing the `docs` extra, Sphinx, MyST, and Furo will be available to both the
terminal and any Sphinx run configuration you create in PyCharm.
