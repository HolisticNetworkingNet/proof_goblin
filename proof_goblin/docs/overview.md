# Project Overview

Proof Goblin is an experimental, framework-agnostic Python package for reviewing
textual artifacts through reusable perspectives called **Proof Lenses**. It
supports Python 3.11 and later. A review combines an artifact with a named
review from a portable `.pgcfg` configuration bundle, asks a model to apply that
review, validates the structured response, and returns evidence-backed
**Observations**.

The project is not yet published as an installable release. Developers can
install the `proof-goblin` package from this repository and verify it without an
API key by following {doc}`getting-started`. The core package uses `jsonschema`;
live OpenAI reviews, documentation builds, and tests are provided through
optional dependency groups.

## Implemented interfaces

The same configuration, prompt, and result types support three implemented
entry points:

- **Python library:** `Config`, `PromptBuilder`, `Reviewer`, and `ReviewResult`
  can be embedded in another application. See {doc}`host-integration`.
- **Command-line interface:** `proof-goblin prompt` inspects a prompt without
  contacting a provider, while `proof-goblin review` executes a review and can
  produce one or more report formats. See {doc}`command-line-interface`.
- **OpenAI example:** `proof_goblin/examples/live_openai_review.py` runs a fixed
  smoke test against the included restaurant example. See
  {doc}`openai-provider`.

Continuous-integration workflows are planned. The architecture also leaves room
for other providers and application interfaces, including a possible web
interface, without coupling them to the core review model.

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

Traceable reviews
: Each result records the configuration, artifact digest, named review,
  provider, resolved model, response identifier, token usage, and execution time
  that produced it. This makes the inputs and execution attributable; it does
  not guarantee that a model will return identical observations when asked
  again.

Execution separated from presentation
: One validated result can be rendered as plain text, canonical JSON, Markdown,
  or standalone HTML without asking the provider to repeat the review.

Framework independence
: The review engine does not depend on Django, a database, or any other
  application framework.

## Review flow

At a high level, Proof Goblin resolves configuration and artifact inputs before
performing any provider work. A successful provider response becomes one
validated result that can be cached and rendered in several forms:

```text
.pgcfg bundle + named review + text artifact
                    |
                    v
       validated configuration + resolved prompt
                    |
                    v
        provider execution (live reviews only)
                    |
                    v
          validated ReviewResult + provenance
                    |
          +---------+---------+
          |                   |
          v                   v
   filesystem cache     text / JSON / Markdown / HTML
```

Configuration loading and prompt assembly are deterministic and do not contact
an AI provider. Rendering an existing result also requires no provider call.
The command-line cache reuses an exact prepared provider request, including its
prompt, output schema, model, and generation controls. Provenance metadata that
does not change the request does not create a miss. `--refresh` confirms a
replacement interactively; `--force-refresh` is the explicit noninteractive
form.

## Inputs and boundaries

The library accepts an artifact as a Python string together with an artifact
name and canonical textual media type used for provenance. The CLI and Python
API use one fixed extension map, use `text/plain` for extensionless names, and
require an explicit supported media type for unrecognized extensions. See
{doc}`artifact-media-types` for the exact policy. Binary artifacts are not
supported. Shared UTF-8 byte limits apply to artifact, configuration, and
assembled prompt inputs as described in {doc}`input-limits`.

Only live provider execution requires network access and credentials. Loading a
configuration, assembling a prompt, reading a cached result, and rendering
reports are local operations. Proof Goblin does not provide persistence for a
host application; the CLI cache is a private filesystem optimization rather
than an application database.

## Results and failures

Each `Observation` contains a question and the artifact evidence that prompted
it. `ReviewResult` adds review identity, configuration and artifact provenance,
provider execution metadata, token usage, creation time, and the validated raw
output. Its canonical JSON form is versioned and can be rendered alongside the
human-facing report formats described in {doc}`report-formats`.

Prompt text and the complete artifact body are excluded from serialized results
and cache entries by default. They can be retained explicitly in JSON when an
application has an appropriate archival and access-control policy. See
{doc}`host-integration` for the stable result record and {doc}`report-formats`
for presentation and security behavior.

Configuration, prompt assembly, provider, and output-validation failures use
focused exception types. The CLI reports these failures as errors and returns a
nonzero exit status. Proof Goblin does not currently expose its own retry or
timeout policy; a host application remains responsible for broader scheduling
and recovery behavior. Provider-specific failures are described in
{doc}`openai-provider`.

## Where to go next

- Install the project and run a provider-free verification in
  {doc}`getting-started`.
- Learn the vocabulary used by reviews in {doc}`concepts`.
- Define and select reviews in {doc}`configuration` and
  {doc}`prompt-assembly`.
- Inspect prompts or run reviews from a terminal in
  {doc}`command-line-interface`.
- Configure credentials and execute a live review in {doc}`openai-provider`.
- Embed Proof Goblin in another Python application with
  {doc}`host-integration`.
