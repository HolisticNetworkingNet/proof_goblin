# Proof Goblin

[![Push checks](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/push-checks.yml/badge.svg?branch=main)](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/push-checks.yml)
[![Pull request checks](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/pull-request-checks.yml/badge.svg?event=pull_request)](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/pull-request-checks.yml)

Proof Goblin is a configurable AI review engine for analyzing documents, websites, and other artifacts through reusable review lenses.

Rather than generating edits, Proof Goblin is designed to ask questions, identify ambiguities, and surface observations from the perspective of a specific audience or stakeholder. Review behavior is assembled from portable configuration files that define Proof Lenses, review missions, protocols, and output schemas, making reviews reproducible, versionable, and suitable for automation.

The project is intended to serve as a lightweight Python library that can be embedded in other applications, used from the command line, or integrated into continuous integration workflows. It is deliberately independent of any particular web framework or user interface.

## Design Principles

- **Configuration as Code** — Review definitions are stored in portable `.pgcfg` files and managed in source control.
- **Composable Reviews** — Prompts are assembled from reusable components rather than handwritten monolithic prompts.
- **Observations over Edits** — Proof Goblin identifies questions and potential issues instead of rewriting content.
- **Reproducible Results** — Review outputs include sufficient metadata to recreate the review configuration and execution.
- **Framework Agnostic** — The core engine has no dependency on Django or other application frameworks.

Proof Goblin is currently under active development and should be considered experimental.

## Documentation

The project documentation is written in Markdown and built with Sphinx, MyST,
and Furo. To build it locally:

```bash
python -m pip install -e ".[docs]"
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```

Open `proof_goblin/docs/_build/html/index.html` to view the generated site.

## OpenAI provider

Install the optional OpenAI integration and set `OPENAI_API_KEY` in your
environment:

```bash
python -m pip install -e ".[openai]"
read -s "OPENAI_API_KEY?OpenAI API key: "
export OPENAI_API_KEY
python proof_goblin/examples/live_openai_review.py
```

The live example uses `gpt-5.6` by default. Set `OPENAI_MODEL` to use a different
compatible model.

## Command line

The installed `proof-goblin` command can inspect prompts without contacting a
provider or execute a live OpenAI review:

```bash
proof-goblin prompt proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass

proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass
```
