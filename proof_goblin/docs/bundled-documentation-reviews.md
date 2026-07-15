# Bundled Documentation Reviews

Proof Goblin ships an evolving starter bundle for documentation review at
`proof_goblin/configs/documentation.pgcfg`. Its reviews are usable out of the
box and serve as reference implementations for creating project-specific
configurations.

These are recommended starting points, not runtime defaults. Proof Goblin never
selects a configuration or review implicitly: the CLI and Python API require
the caller to identify both. The bundled reviews are early prototypes—practical
enough for real work, but expected to improve as they are exercised against
more documents, audiences, purposes, and security boundaries.

## Available reviews

| Review identifier | Perspective and purpose |
| --- | --- |
| `business_owner_first_pass` | A business-operations perspective focused on meaning, decisions, responsibilities, risks, and next steps |
| `django_developer_first_pass` | A Django and Python implementation perspective focused on contracts, prerequisites, examples, errors, testing, and operations |
| `technical_writer_first_pass` | Audience fit, organization, terminology, clarity, consistency, and information gaps across general documentation |
| `technical_writer_concept_reference` | Definition, differentiation, relationships, consistency, and retrieval in conceptual or terminology references |
| `django_developer_concept_reference` | Agreement between a conceptual reference and the system an experienced Python developer must understand |
| `front_end_readability` | Scan path, headings, density, labels, links, and reader-facing comprehension |

The two concept-reference reviews share a Mission that treats accurate shared
meaning—not setup, implementation, or a call to action—as the intended reader
outcome. This prevents an otherwise useful perspective from imposing the wrong
kind of success criteria on a glossary or concepts page.

The front-end readability review uses the technical-writer Proof Lens with a
narrower Mission. Readability is an assignment within that professional
perspective rather than a separate kind of reader.

All bundled reviews use the `documentation_questions_only` Review Protocol and
the `observation.v1` Output Schema. They produce evidence-based questions for
the author; they do not rewrite the reviewed document or invent solutions.

## Choose a review

Match the review to both the required analytical perspective and the document's
purpose:

- Use `technical_writer_first_pass` for a general reading and learning
  experience, especially onboarding, explanation, and task-oriented pages.
- Follow with `django_developer_first_pass` when commands, APIs, configuration,
  operational behavior, or implementation claims must be usable as written.
- Use the two `*_concept_reference` reviews for glossaries, concept catalogs,
  terminology pages, and other material intended primarily for lookup and
  shared understanding.
- Use `business_owner_first_pass` when a non-technical decision-maker must
  understand consequences, responsibilities, or a next step.
- Use `front_end_readability` when scan path, headings, labels, links, and calls
  to action matter more than implementation depth.

Running more than one review can expose the same weakness from different
perspectives. Agreement increases confidence that the issue matters;
differences reveal which reader, responsibility, or use case is affected.
Human judgment remains responsible for reconciling the observations and
deciding whether the source should change.

## Use the bundle from a source checkout

From the repository root, pass the bundle and a named review explicitly:

```bash
proof-goblin review proof_goblin/docs/concepts.md \
  --config proof_goblin/configs/documentation.pgcfg \
  --review technical_writer_concept_reference \
  --output concepts-review.md
```

Use the same path with `Config.load()` in code:

```python
from proof_goblin import Config, PromptBuilder


config = Config.load("proof_goblin/configs/documentation.pgcfg")
prompt = PromptBuilder(config).build(
    review="django_developer_concept_reference",
    artifact=documentation,
    artifact_name="concepts.md",
    artifact_media_type="text/markdown",
)
```

The example assumes that the host has already produced the `documentation`
string. See {doc}`Host Application Integration <host-integration>` for a
complete application boundary.

## Load the installed bundle

The bundle is packaged with Proof Goblin. An installed application can locate
it through `importlib.resources` without depending on the package's filesystem
location:

```python
from importlib.resources import as_file, files

from proof_goblin import Config


bundle = files("proof_goblin").joinpath("configs/documentation.pgcfg")
with as_file(bundle) as config_path:
    config = Config.load(config_path)
```

Load the configuration inside the `as_file()` context. The returned `Config`
retains the validated content and digest after the context closes.

## Use directly or customize

There are three useful ways to work with the starter bundle:

1. **Use it directly** for exploration and general documentation work. Its
   behavior follows the version installed with Proof Goblin.
2. **Copy it into the project** when the team needs controlled customization,
   review-specific versioning, or reproducible behavior independent of package
   upgrades.
3. **Treat it as an upstream prototype** by comparing project-specific reviews
   with later bundled versions and deliberately adopting useful refinements.

For reproducible reviews, commit a copied bundle alongside the artifacts it
reviews. Changes to wording, components, or presentation metadata change the
configuration digest and therefore the review cache identity. Version and
review those changes like source code.

See {doc}`Configuration Bundles <configuration>` for the complete format,
validation, composition, and provenance contracts.
