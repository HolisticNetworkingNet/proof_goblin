# Proof Goblin

Proof Goblin is a configurable AI review engine for analyzing artifacts through
reusable perspectives called **Proof Lenses**.

Instead of rewriting content, Proof Goblin asks questions, identifies
ambiguities, and records evidence-backed **Observations**. Review behavior is
defined in portable configuration files so that it can be inspected, shared,
versioned, and reproduced.

```{toctree}
:maxdepth: 2
:caption: Contents

overview
concepts
getting-started
bundled-documentation-reviews
command-line-interface
configuration
prompt-assembly
openai-provider
report-formats
host-integration
development
```

```{note}
Proof Goblin is experimental, but its core review workflow is operational:
configuration loading, prompt assembly, OpenAI execution, structured
observations, and host-friendly result serialization are implemented. The
public API and configuration schema may still evolve before a stable release.
```
