# Core Concepts

Proof Goblin uses a small vocabulary to keep review configuration explicit.

## Artifact

The **Artifact** is the material being reviewed. It might be Markdown, HTML, a
PDF, an image, or another representation that a provider can evaluate.

## Proof Lens

A **Proof Lens** defines who is looking at the artifact and under what
circumstances. It establishes a coherent point of view rather than merely
assigning the model a job title.

Proof Lens definitions use a flexible internal vocabulary. Bundled lenses
commonly use these fields:

- `description` identifies the person or perspective represented by the lens;
- `circumstances` describe the situation in which that person encounters the
  artifact, including their purpose, pressures, and available context;
- `knowledge` states what the person can reasonably be expected to know, and
  therefore what the artifact may or may not leave implicit;
- `goals` describe what the person needs to understand, decide, or accomplish;
- `routinely_notices` identifies the kinds of signals, gaps, or risks that this
  perspective is especially likely to recognize; and
- `perspective_guardrails` prevent the lens from becoming a caricature or
  exceeding its useful scope. They can identify assumptions the review must not
  make or concerns it should not raise without a material reason.

These names are conventions used by the bundled configurations, not a closed
schema imposed on every Proof Lens. A domain-specific lens may include other
material needed to express its perspective.

## Mission

The **Mission** describes what the review is trying to discover. The same Proof
Lens can be used for different missions, such as finding onboarding barriers or
identifying unclear calls to action.

## Review Protocol

The **Review Protocol** defines how the review should behave. It can require
evidence, prohibit rewriting, limit the response to questions, or constrain
speculation. It governs the manner of the review rather than what the review is
trying to discover.

Configuration files use `protocols` for the named collection and `protocol` for
a review's reference to one member of that collection. Resolved prompts use the
more descriptive heading **Review Protocol**.

## Output Schema

The **Output Schema** defines the structure a provider must return. Proof Goblin
passes the selected JSON Schema to the provider and validates the response
against it before creating observations. The bundled `observation.v1` schema,
for example, requires an `observations` array whose members contain a question
and its evidence.

An Output Schema controls response structure, not review perspective, purpose,
or behavior. It is also distinct from the review-result schema: the Output
Schema validates raw provider output, while
`schemas/review-result.v1.schema.json` describes the larger serialized
`ReviewResult`, including attribution and execution provenance.

## Named Review

A **Named Review** assembles one Proof Lens, Mission, Review Protocol, and Output
Schema into a reusable review definition. Its stable identifier is used in
configuration references and commands. Its title and description provide a
human-readable identity for terminal output, reports, and host applications.

## Observation

An **Observation** is one structured finding from a review. It records a
question and the concrete evidence that prompted it. The surrounding
`ReviewResult` records the provenance needed to understand how the observations
were produced.

## Configuration bundle

A `.pgcfg` file is a portable collection of reusable Proof Lenses, Missions,
Review Protocols, Output Schemas, and Named Reviews for a domain.

For example, a restaurant-focused bundle could define both a first-time diner
lens and a restaurant-owner lens, then reuse them across several homepage or
menu-review missions.

Proof Goblin currently supports configuration schema version `1.0`. The loader
validates the required envelope and all named review references while leaving
the internal vocabulary of Proof Lenses, Missions, and Review Protocols
flexible.
