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

Proof Goblin can be used as a Python library or from the command line. It is framework agnostic and deliberately independent of any particular web application or user interface. The project validates every pull request across its supported Python versions and representative operating systems.

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

- **New users and writers:** [Getting Started](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/getting-started.md) and [The Philosophy of Proof Goblin](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/philosophy.md)
- **Command-line users:** [Command-Line Interface](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/command-line-interface.md)
- **Application integrators:** [Host Application Integration](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/host-integration.md)
- **Review authors:** [Review Grammar](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/concepts.md), [Configuration Bundles](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/configuration.md), and [Bundled Documentation Reviews](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/bundled-documentation-reviews.md)
- **Live-review operators:** [OpenAI Provider](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/openai-provider.md) and [Data Handling and Retention](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/data-handling.md)
- **Contributors:** [Development](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/development.md), including source-checkout and documentation-build instructions

And yes: of course, every document has been proofed by the Proof Goblin!

## Installation

Install the core library and command-line interface from PyPI:

```bash
python -m pip install proof-goblin
proof-goblin --help
```

Install the optional OpenAI integration when you want to run live reviews:

```bash
python -m pip install "proof-goblin[openai]"
```

The following installed-package smoke test loads the bundled documentation
configuration and assembles a prompt locally. It does not require an API key,
contact a provider, or depend on a source checkout:

```python
from importlib.resources import as_file, files

from proof_goblin import Config, PromptBuilder


bundle = files("proof_goblin").joinpath("configs/documentation.pgcfg")
with as_file(bundle) as config_path:
    config = Config.load(config_path)

prompt = PromptBuilder(config).build(
    review="technical_writer_first_pass",
    artifact="# Draft\n\nThis is a document to review.",
    artifact_name="draft.md",
)
print(prompt.review_name, prompt.artifact_media_type)
```

## OpenAI provider

After installing the optional OpenAI integration, set `OPENAI_API_KEY` in your
environment before making a live request:

> A live review sends the complete artifact and selected review instructions
> to OpenAI and may incur provider charges. Confirm that the content is approved
> for external processing, and review [Data Handling and Retention](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/data-handling.md)
> before submitting sensitive material.

```bash
read -s "OPENAI_API_KEY?OpenAI API key: "
export OPENAI_API_KEY
```

See the [OpenAI Provider guide](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/openai-provider.md)
for library and command-line examples. The repository's live example is a
contributor example that requires a source checkout.

## Command line

After following [Getting Started](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/getting-started.md), use
`prompt` to assemble and print the complete prompt locally without contacting a
provider. Use `review` to send the assembled request to OpenAI and print a
plain-text report to standard output:

```bash
proof-goblin prompt draft.md \
  --config review.pgcfg \
  --review first_pass

proof-goblin review draft.md \
  --config review.pgcfg \
  --review first_pass
```

See the [Command-Line Interface](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/proof_goblin/docs/command-line-interface.md)
for file output, report formats, caching, and provider behavior.

## License

Proof Goblin is licensed under the MIT License.

See the [LICENSE](https://github.com/HolisticNetworkingNet/proof_goblin/blob/main/LICENSE)
file for the full license text.
