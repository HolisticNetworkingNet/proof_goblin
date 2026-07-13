# Getting started

Proof Goblin is not yet published as an installable release. For development,
clone the repository and use an isolated Python environment.

## Install the project and documentation tools

From the repository root, install Proof Goblin in editable mode with its
documentation dependencies:

```bash
python -m pip install -e ".[docs]"
```

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
