# Configuration bundles

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
- named `reviews` that reference one member of each component collection.

Component definitions are JSON objects whose internal vocabulary remains
flexible. This allows a bundle to preserve its domain-specific prompt material
without forcing every lens or protocol into the same shape.

## Provenance

A configuration loaded from disk records its resolved source path and SHA-256
digest. These values can later be included in observation output to identify the
exact configuration bytes used for a review.

See `proof_goblin/examples/restaurants.pgcfg` for a complete working bundle.
