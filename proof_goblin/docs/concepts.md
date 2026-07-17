# Review Grammar

Proof Goblin uses a small vocabulary to describe reviews independently of any
particular AI provider, prompt, or implementation.

This **Review Grammar** defines the concepts used to express reviews,
configure review behavior, and interpret review results. Together they form
the language of Proof Goblin.

These concepts are intended to remain stable even as the software evolves.

This page is a conceptual reference rather than a setup or procedural guide.

## How the Review Grammar Fits Together

A Configuration Bundle contains components and Named Reviews. Each Named Review
selects one Proof Lens, Mission, Review Protocol, and Output Schema. At review
time, Proof Goblin combines that definition with an Artifact, sends the
resulting Assembled Prompt through a Provider, and normalizes the validated
response into a ReviewResult containing Observations.

```text
Configuration Bundle
  └─ Named Review
       ├─ Proof Lens
       ├─ Mission
       ├─ Review Protocol
       └─ Output Schema

Named Review + Artifact
  → Assembled Prompt
  → Provider
  → validated provider response
  → ReviewResult
       └─ Observations
```

## Artifact

The **Artifact** is the material being reviewed. The current Python API accepts
the artifact as a non-empty string, together with a descriptive name and a
canonical supported textual media type. When the media type is omitted, the CLI
and Python API infer it through the same fixed filename-extension map and use
`text/plain` as a fallback. Proof Goblin does not accept a PDF, image, or other
binary object directly. See {doc}`artifact-media-types` for the complete
boundary.

The artifact becomes part of the Assembled Prompt sent to the Provider. Its
UTF-8 bytes are also hashed so a ReviewResult can identify the reviewed content
without including the complete artifact in its default serialized record.

## Proof Lens

A **Proof Lens** is a disciplined perspective through which an Artifact is
examined.

Like a camera lens, it determines which signals are brought into focus while
allowing other concerns to remain in the background. Proof Goblin applies that
perspective; it does not impersonate or role-play a person.

A Security Expert notices trust boundaries.

A Technical Writer notices ambiguity.

An Accessibility Specialist notices exclusion.

A Product Manager notices user friction.

The Artifact does not change.

Only the perspective changes.

Proof Lens definitions use a flexible internal vocabulary. Bundled lenses
commonly use these fields:

- `description` identifies the analytical perspective established by the lens;
- `circumstances` describe the setting in which the Artifact is evaluated,
  including its purpose, pressures, and available context;
- `knowledge` states which knowledge the perspective treats as available and
  which knowledge the Artifact may not safely assume;
- `goals` describe the outcomes or qualities the perspective prioritizes;
- `routinely_notices` identifies the kinds of signals, gaps, or risks that this
  perspective is especially likely to recognize; and
- `perspective_guardrails` prevent the lens from becoming a caricature or
  exceeding its useful scope. They identify assumptions the review must not
  make or concerns it should not raise without a material reason.

These names are conventions used by the bundled configurations, not a closed
schema imposed on every Proof Lens. A domain-specific lens may include other
material needed to express its perspective.

## Mission

The **Review Mission** defines what the review is trying to discover.

Every review begins with a question.

The same Proof Lens may participate in many different Missions. For example, a
Technical Writer might review a tutorial for onboarding barriers, perform an
FAQ discovery review, or evaluate a concept reference for clarity and
precision.

A Review Mission provides purpose.

A Proof Lens provides perspective.

Bundled Missions commonly use `description` and `questions`. A Mission may also
state `document_expectations` or `guardrails` when the Artifact's purpose must
constrain the review. These fields are prompt conventions rather than a closed
loader schema.

The Mission supplies the objective; it should not duplicate the analytical
perspective expressed by the Proof Lens or the behavioral rules expressed by
the Review Protocol.

## Review Protocol

The **Review Protocol** defines how the review should behave. It can require
evidence, prohibit rewriting, limit the response to questions, or constrain
speculation. It governs the manner of the review rather than its perspective or
objective.

Bundled Review Protocols use boolean fields such as `rewrite_content`,
`provide_solutions`, `ask_questions`, `require_evidence`, and
`avoid_speculation`, together with an `instructions` array for specific
behavior. As with Proof Lenses and Missions, these are conventions serialized
into the prompt rather than a closed component schema.

Configuration files use `protocols` for the named collection and `protocol` for
a Named Review's reference to one member of that collection. Assembled prompts
use the more descriptive heading **Review Protocol**.

## Output Schema

The **Output Schema** is the JSON Schema supplied to a Provider adapter and used
locally to validate its decoded structured response. It controls response
structure, not review perspective, purpose, or behavior.

The configuration loader requires only that an Output Schema component be a
JSON object. The current Reviewer has a narrower normalization contract: after
schema validation, the response must contain an `observations` array whose
members provide string `question` and `evidence` fields. Proof Goblin converts
each member into an Observation. A schema that validates a different response
shape cannot currently produce a ReviewResult, even if the Provider accepts
that schema.

The bundled `observation.v1` Output Schema expresses this supported contract.
The complete decoded response remains available in memory as
`ReviewResult.raw_output`, while the normalized Observations contain the fields
used by reports and canonical serialization.

An Output Schema is distinct from the review-result schema. The former validates
the Provider response; `schemas/review-result.v1.schema.json` describes the
larger serialized ReviewResult, including attribution and execution
provenance.

## Named Review

A **Named Review** assembles one Proof Lens, Mission, Review Protocol, and Output
Schema into a reusable review definition.

Its key in a bundle's `reviews` object is the review identifier. That identifier
must be a non-empty string and is unique only within that Configuration Bundle.
Bundle authors are responsible for keeping it stable across revisions when it
continues to represent the same review. The CLI and Python API use it to select
a review, and Proof Goblin records it in prompt, cache, and result provenance.
It is not globally unique across bundles.

A Named Review also has a human-readable `title` and `description` for terminal
output, reports, and host applications. Its `lens`, `mission`, `protocol`, and
`output_schema` fields must name existing members of the corresponding
collections in the same bundle.

## Assembled Prompt

The **Assembled Prompt** is the deterministic `Prompt` produced by
`PromptBuilder` from a validated Configuration Bundle, a Named Review, and an
Artifact.

Its system portion contains the general Proof Goblin instructions and the
resolved Proof Lens, Mission, Review Protocol, and Output Schema. Its user
portion contains Artifact identity, media type, and complete content. The
Prompt also carries the review identifier and configuration and Artifact
provenance used by caching and ReviewResult serialization.

Prompt assembly is local and does not contact a Provider. See
{doc}`Prompt Assembly <prompt-assembly>` for the exact construction boundary.

## Provider

A **Provider** is an adapter between Proof Goblin's provider-neutral Reviewer
and a model service. It receives an Assembled Prompt and the selected Output
Schema, then returns a decoded `ProviderResponse` containing structured data,
provider and model identity, an optional response identifier, and available
token usage.

The Reviewer owns orchestration and local output validation; the Provider owns
service-specific request and response handling. Proof Goblin currently includes
an OpenAI Provider, while the public `Provider` protocol allows other adapters
and deterministic test providers.

## Observation

An **Observation** is one thing a particular Proof Lens considered worthy of
attention while pursuing a particular Review Mission.

Observations are the fundamental output of Proof Goblin.

They are intentionally small, attributable, and supported by evidence.

An Observation is not a judgment about the author.

It is an invitation to think more carefully.

The Provider response already contains objects with those fields. After
validating the response against the Output Schema, the Reviewer reads each
object and creates an immutable `Observation`. This normalization separates the
provider's decoded response from the stable fields used by Proof Goblin reports
and result serialization.

## ReviewResult

A **ReviewResult** represents one successfully completed and validated review.
It contains the normalized Observations, Assembled Prompt, review attribution,
provider and model identity, optional response identifier, token usage, raw
decoded provider output, and a timezone-aware creation time.

`ReviewResult.to_dict()` and `ReviewResult.to_json()` produce the canonical
versioned result record. Prompt text—and therefore the complete Artifact—is
omitted from that record by default, although the in-memory ReviewResult retains
it. Normalized observations and evidence can still reproduce Artifact content.
See {doc}`data-handling` for the complete lifecycle and {doc}`Host Application
Integration <host-integration>` for application persistence and compatibility
responsibilities.

## Configuration Bundle

A **Configuration Bundle** is a `.pgcfg` file containing reusable Proof Lenses,
Missions, Review Protocols, Output Schemas, and Named Reviews for a domain.

Configuration Bundles allow organizations, projects, and individuals to define
their own review language without modifying Proof Goblin itself. A bundle
captures reusable perspectives, review objectives, behavioral protocols, and
review definitions for a particular domain.

For example, the bundled documentation configuration defines several reader
perspectives and combines them with general, concept-reference, and readability
Missions. A project may use that starter bundle directly or version a customized
copy alongside the Artifacts it reviews.

Proof Goblin currently supports configuration schema version `1.0`. The loader
validates the required envelope, component collection shapes, and every Named
Review reference while leaving the internal vocabulary of Proof Lenses,
Missions, and Review Protocols flexible. See {doc}`Configuration Bundles
<configuration>` for the complete contract.
