# Core Concepts

Proof Goblin uses a small vocabulary to keep review configuration explicit.

## Artifact

The **Artifact** is the material being reviewed. It might be Markdown, HTML, a
PDF, an image, or another representation that a provider can evaluate.

## Proof Lens

A **Proof Lens** defines who is looking at the artifact and under what
circumstances. It may describe that person's knowledge, responsibilities,
goals, constraints, and likely concerns.

## Mission

The **Mission** describes what the review is trying to discover. The same Proof
Lens can be used for different missions, such as finding onboarding barriers or
identifying unclear calls to action.

## Protocol

The **Protocol** defines how the review should behave. It can require evidence,
prohibit rewriting, limit the response to questions, or constrain speculation.

## Observation

An **Observation** is one structured finding from a review. It records a
question and the concrete evidence that prompted it. The surrounding
`ReviewResult` records the provenance needed to understand how the observations
were produced.

## Configuration bundle

A `.pgcfg` file is a portable collection of reusable lenses, missions,
protocols, output rules, and named review assemblies for a domain.

For example, a restaurant-focused bundle could define both a first-time diner
lens and a restaurant-owner lens, then reuse them across several homepage or
menu-review missions.

Proof Goblin currently supports configuration schema version `1.0`. The loader
validates the required envelope and all named review references while leaving
the internal vocabulary of lenses, missions, and protocols flexible.
