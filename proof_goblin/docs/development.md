# Development Status

Proof Goblin is an experimental but operational pure-Python library. It has no
Django dependency and no database. Its implemented core includes configuration
validation, deterministic prompt assembly, provider execution, structured
observation validation, provenance, and JSON-compatible result serialization.

The initial development milestones are:

1. load and validate a `.pgcfg` configuration bundle (complete);
2. resolve a named review and assemble an inspectable prompt (complete);
3. send the review to a provider and parse structured observations (complete); and
4. expose the workflow through a small command-line interface (complete).

Configuration loading and prompt assembly do not require an AI provider and are
tested deterministically. Provider and reviewer tests use local test doubles;
only the live example requires an API key and network access.

## Development environment

Install Proof Goblin in editable mode with the local quality, test, and
documentation dependencies:

```bash
python -m pip install -e ".[dev,test,docs]"
```

The optional `dev` dependency set contains repository-development tools rather
than packages required by Proof Goblin at runtime.

## Linting and formatting

Ruff provides the repository's linting, import-ordering, and formatting policy.
Its configuration is committed in `pyproject.toml`, so local and automated
checks use the same Python version, rules, and formatting behavior.

Run both read-only checks before committing:

```bash
ruff check .
ruff format --check .
```

Apply available lint fixes and format the codebase with:

```bash
ruff check --fix .
ruff format .
```

Review the resulting diff and run the test and documentation checks after any
automated fix. Static type checking is not part of the current Ruff policy and
remains a separate future design decision.

## Documentation conventions

Documentation source files use MyST Markdown and live in `proof_goblin/docs/`.
Keep conceptual documentation independent of a particular provider or
application interface unless the page is specifically about that integration.

Before committing documentation changes, run a warnings-as-errors build:

```bash
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```
