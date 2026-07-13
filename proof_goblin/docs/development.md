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

## Documentation conventions

Documentation source files use MyST Markdown and live in `proof_goblin/docs/`.
Keep conceptual documentation independent of a particular provider or
application interface unless the page is specifically about that integration.

Before committing documentation changes, run a warnings-as-errors build:

```bash
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```
