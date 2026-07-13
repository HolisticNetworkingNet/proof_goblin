# Project Overview

Proof Goblin is designed as a small, framework-agnostic Python library. Its core
responsibility is to review an artifact through one or more defined perspectives
and return structured observations.

The implemented library API can be embedded in another Python application. The
architecture also leaves room for additional interfaces without depending on
them:

- integration with another Python application (implemented);
- direct execution through the included OpenAI example script (implemented);
- a command-line interface for prompt inspection and live reviews (implemented);
- continuous-integration workflows (planned); and
- a possible web interface in the future.

## Design principles

Configuration as code
: Review definitions live in portable `.pgcfg` files that can be committed,
  diffed, reviewed, and shared.

Composable reviews
: Prompts are assembled from focused, reusable components rather than maintained
  as monolithic blocks of prose.

Observations over edits
: A review surfaces questions and potential concerns without silently rewriting
  the artifact.

Reproducible results
: Each result retains provenance identifying the configuration, artifact,
  model, and execution that produced it.

Framework independence
: The review engine does not depend on Django or any other application framework.

## Review flow

At a high level, a review combines a configuration bundle, a named review, and
an artifact:

```text
.pgcfg bundle + named review + artifact
                    |
                    v
              resolved prompt
                    |
                    v
          observations + provenance
```
