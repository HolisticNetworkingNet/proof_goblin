# Proof Goblin

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