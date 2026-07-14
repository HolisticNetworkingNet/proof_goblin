# Configuration Bundles

Proof Goblin configuration bundles use the `.pgcfg` extension. Version 1.0 files
are UTF-8 JSON documents with a small required envelope and named collections of
review components.

```python
from proof_goblin import Config

config = Config.load("proof_goblin/examples/restaurants.pgcfg")
review = config.review("homepage_first_pass")
```

Loading validates the file format, schema version, component collections, and
every component reference made by a named review. It does not contact an AI
provider or assemble a prompt.

## Required structure

A version 1.0 bundle contains:

- `format`, which must be `proof-goblin-config`;
- `schema_version`, currently `1.0`;
- a bundle `name` and `version`;
- named `lenses`, `missions`, `protocols`, and `output_schemas`; and
- named `reviews` with presentation metadata that reference one member of each
  component collection.

Each review has three forms of identity with distinct purposes:

- the key in the `reviews` object is its stable identifier, used for selection,
  configuration references, and provenance;
- `title` is its polished human-readable label for CLI output, reports, and user
  interfaces; and
- `description` briefly states what the review is intended to accomplish.

For example:

```json
"technical_writer_first_pass": {
  "title": "Technical Writing Review",
  "description": "Evaluates documentation for audience fit, organization, clarity, consistency, and information gaps.",
  "lens": "technical_writer",
  "mission": "technical_writing_quality",
  "protocol": "documentation_questions_only",
  "output_schema": "observation.v1"
}
```

Titles and descriptions must be non-empty strings. They are presentation
metadata only: changing them does not alter the resolved lens, mission,
protocol, or output schema that controls review behavior.

Component definitions are JSON objects whose internal vocabulary remains
flexible. This allows a bundle to preserve its domain-specific prompt material
without forcing every lens or protocol into the same shape.

## Provenance

A configuration loaded from disk records its resolved source path and SHA-256
digest. The digest is carried into the assembled prompt and serialized review
result, identifying the exact configuration bytes used for a review.

The serialized result also records the review identifier, title, description,
and all four resolved component names. A host can therefore present and explain
a result without reopening the configuration bundle.

See `proof_goblin/examples/restaurants.pgcfg` for a complete working bundle.
Proof Goblin also ships a reusable documentation-focused bundle described in
{doc}`documentation-review-configuration`.
