# Development status

Proof Goblin is currently an experimental pure-Python project. The package
structure names the first expected responsibilities, but the public API and
configuration schema have not yet been implemented.

The initial development milestones are:

1. load and validate a `.pgcfg` configuration bundle (complete);
2. resolve a named review into its lens, mission, protocol, and output schema;
3. assemble and inspect the generated prompt;
4. send the review to a provider and parse structured observations; and
5. expose the workflow through a small command-line interface.

The first milestones intentionally do not require an AI provider. Prompt
assembly and configuration validation should be testable deterministically.

## Documentation conventions

Documentation source files use MyST Markdown and live in `proof_goblin/docs/`.
Keep conceptual documentation independent of a particular provider or
application interface unless the page is specifically about that integration.

Before committing documentation changes, run a warnings-as-errors build:

```bash
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```
