# Project overview

Proof Goblin is designed as a small, framework-agnostic Python library. Its core
responsibility is to review an artifact through one or more defined perspectives
and return structured observations.

The library is intended to support several interfaces without depending on any
of them:

- a command-line tool;
- continuous-integration workflows;
- integration with another Python application; and
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
: Each result should retain enough provenance to identify the configuration,
  artifact, model, and execution that produced it.

Framework independence
: The review engine does not depend on Django or any other application framework.

## Intended review flow

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
