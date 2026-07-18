# Proof Goblin

**Better Documents. Happier Writers.**

[![Push checks](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/push-checks.yml/badge.svg?branch=main)](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/push-checks.yml)
[![Pull request checks](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/pull-request-checks.yml/badge.svg?event=pull_request)](https://github.com/HolisticNetworkingNet/proof_goblin/actions/workflows/pull-request-checks.yml)

> [!WARNING]
> Proof Goblin is experimental. Its core review workflow is operational, but
> the public API and configuration schema may change before a stable release.
> AI-generated observations can be incomplete or incorrect and require human
> judgment.

Proof Goblin is an AI-assisted review engine that helps writers find problems without taking over the writing.

Instead of rewriting your work, Proof Goblin examines documents through reusable review perspectives called **Proof Lenses**. Each review produces structured **Observations** that surface ambiguity, missing context, contradictions, accessibility concerns, security questions, and other issues worth a closer look.

The result is a more useful kind of AI collaboration: writers remain in control of the words, while Proof Goblin helps them see what they may have missed.

Reviews are assembled from portable `.pgcfg` configuration files that define lenses, missions, protocols, and output schemas. Because those configurations can be stored in source control, review definitions are inspectable, versionable, shareable, and ready for automation.

Proof Goblin can be used as a Python library or from the command line. It is framework agnostic and deliberately independent of any particular web application or user interface. Continuous-integration workflows are planned.

## What Proof Goblin Does

- Reviews documents from clearly defined perspectives
- Surfaces questions and concerns instead of silently rewriting content
- Turns review behavior into portable, version-controlled configuration
- Produces structured observations with traceable review metadata
- Supports local workflows and application integration

## Design Principles
**(For the geeks)**

- **Observations over Edits** — Proof Goblin identifies questions and potential issues instead of rewriting content.
- **Composable Reviews** — Prompts are assembled from reusable components rather than handwritten monolithic prompts.
- **Traceable Executions** — Review outputs record the configuration, artifact identity, provider, model, and execution metadata. Repeating an AI review does not guarantee identical observations.
- **Configuration as Code** — Review definitions are stored in portable `.pgcfg` files and managed in source control.
- **Framework Agnostic** — The core engine has no dependency on Django or other application frameworks.

## Documentation

Start with the guide that matches what you want to do:

- **New users and writers:** [Getting Started](proof_goblin/docs/getting-started.md) and [The Philosophy of Proof Goblin](proof_goblin/docs/philosophy.md)
- **Command-line users:** [Command-Line Interface](proof_goblin/docs/command-line-interface.md)
- **Application integrators:** [Host Application Integration](proof_goblin/docs/host-integration.md)
- **Review authors:** [Review Grammar](proof_goblin/docs/concepts.md), [Configuration Bundles](proof_goblin/docs/configuration.md), and [Bundled Documentation Reviews](proof_goblin/docs/bundled-documentation-reviews.md)
- **Live-review operators:** [OpenAI Provider](proof_goblin/docs/openai-provider.md) and [Data Handling and Retention](proof_goblin/docs/data-handling.md)
- **Contributors:** [Development](proof_goblin/docs/development.md), including instructions for building the documentation locally

And yes: of course, every document has been proofed by the Proof Goblin!

## OpenAI provider

Install the optional OpenAI integration and set `OPENAI_API_KEY` in your
environment:

> A live review sends the complete artifact and selected review instructions
> to OpenAI and may incur provider charges. Confirm that the content is approved
> for external processing, and review [Data Handling and Retention](proof_goblin/docs/data-handling.md)
> before submitting sensitive material.

```bash
python -m pip install -e ".[openai]"
read -s "OPENAI_API_KEY?OpenAI API key: "
export OPENAI_API_KEY
python proof_goblin/examples/live_openai_review.py
```

The live example uses `gpt-5.6` by default. Set `OPENAI_MODEL` to use a different
compatible model.

## Command line

After following [Getting Started](proof_goblin/docs/getting-started.md), use
`prompt` to assemble and print the complete prompt locally without contacting a
provider. Use `review` to send the assembled request to OpenAI and print a
plain-text report to standard output:

```bash
proof-goblin prompt proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass

proof-goblin review proof_goblin/docs/overview.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_first_pass
```

See the [Command-Line Interface](proof_goblin/docs/command-line-interface.md)
for file output, report formats, caching, and provider behavior.

## License

Proof Goblin is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the full license text.
