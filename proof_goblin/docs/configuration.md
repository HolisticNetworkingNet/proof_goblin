# Configuration Bundles

Proof Goblin configuration bundles define reusable review components and the
named reviews assembled from them. Bundles use the `.pgcfg` extension and are
UTF-8 JSON documents, so they can be inspected, compared, and versioned with
the artifacts they review.

Configuration loading is local and deterministic. It validates the bundle but
does not assemble a prompt or contact an AI provider.

## A complete minimal bundle

The following bundle defines one review named `reader_first_pass`. It includes
the complete top-level envelope and one member of each component collection:

```json
{
  "format": "proof-goblin-config",
  "schema_version": "1.0",
  "name": "documentation",
  "version": "0.1.0",
  "lenses": {
    "reader": {
      "description": "A documentation-reader perspective focused on comprehension and use."
    }
  },
  "missions": {
    "clarity": {
      "questions": [
        "What could prevent the reader from understanding or acting?"
      ]
    }
  },
  "protocols": {
    "questions_only": {
      "ask_questions": true,
      "require_evidence": true,
      "rewrite_content": false
    }
  },
  "output_schemas": {
    "observation.v1": {
      "type": "object",
      "additionalProperties": false,
      "required": ["observations"],
      "properties": {
        "observations": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["question", "evidence"],
            "properties": {
              "question": {"type": "string"},
              "evidence": {"type": "string"}
            }
          }
        }
      }
    }
  },
  "reviews": {
    "reader_first_pass": {
      "title": "Reader Documentation Review",
      "description": "Identifies barriers to understanding and acting on the document.",
      "lens": "reader",
      "mission": "clarity",
      "protocol": "questions_only",
      "output_schema": "observation.v1"
    }
  }
}
```

Save a bundle anywhere appropriate to the project, using a `.pgcfg` filename.
The Python example below assumes the minimal bundle was saved as
`documentation.pgcfg` in the current working directory. Paths passed to the
command-line interface or `Config.load()` may be absolute or relative to that
directory.

## Bundle identity and compatibility

The top-level fields have distinct responsibilities:

| Field | Contract and purpose |
| --- | --- |
| `format` | Must be the exact string `proof-goblin-config`. It distinguishes a bundle from other JSON documents. |
| `schema_version` | Must currently be `1.0`. It identifies the structural contract understood by the loader. |
| `name` | A non-empty, author-defined string identifying the bundle. Proof Goblin does not impose a naming pattern. |
| `version` | A non-empty, author-managed bundle revision. It describes the review content, not the loader schema, and has no enforced version format. |

The current Proof Goblin release accepts only configuration schema version
`1.0`; any other value raises `ConfigValidationError`. A bundle author should
change `version` when review content changes according to the project's own
versioning policy. Changing `schema_version` is appropriate only when adopting
a different structural contract supported by Proof Goblin.

Additional top-level fields are allowed and retained in `Config.metadata`. For
example, the bundled documentation configuration includes a `description`.

## Component collections

Every bundle contains five named JSON objects:

- `lenses` define the perspective from which the artifact is examined;
- `missions` define the purpose and priorities of the review;
- `protocols` define the behavioral rules of the review;
- `output_schemas` define the structured response expected from the provider;
  and
- `reviews` select one member from each of the other collections.

Each collection key must be a non-empty string, and every component value must
be a JSON object. Empty collections and unreferenced components are
structurally permitted, although a usable named review needs all four referenced
components.

The loader deliberately does not impose one vocabulary on lenses, missions, or
protocols. Their contents are prompt material and are serialized into the
assembled system prompt. This permits domain-specific fields such as
`knowledge`, `goals`, `circumstances`, or `instructions`.

The loader likewise verifies only that an output-schema component is a JSON
object. To execute a review, that object must also be a JSON Schema suitable for
the selected provider and for local result validation. The OpenAI integration
has additional strict-schema requirements described in {doc}`OpenAI Provider
<openai-provider>`.

## Named reviews

A review combines one Proof Lens, Mission, Review Protocol, and Output Schema.
Every review entry requires six non-empty string fields:

- `title` and `description` provide human-readable presentation metadata;
- `lens`, `mission`, `protocol`, and `output_schema` must exactly match keys in
  their corresponding collections.

The key in the `reviews` object is the review's stable identifier. It is used by
the CLI and Python API for selection and is recorded in result provenance.
`title` is the polished label displayed in reports, while `description` states
what the review is intended to accomplish.

Changing only the title or description does not change the selected components,
but it does change the configuration bytes and therefore its digest and cache
identity. Additional fields on a review are retained in
`ReviewDefinition.metadata`.

## Load and use a bundle

`Config.load(path)` accepts a string or `pathlib.Path` and returns a validated
`Config`. The `.pgcfg` extension is required.

```python
from pathlib import Path

from proof_goblin import Config, PromptBuilder


config = Config.load(Path("documentation.pgcfg"))
review = config.review("reader_first_pass")

print(review.title)
print(review.lens)

prompt = PromptBuilder(config).build(
    review=review.name,
    artifact="# Draft\n\nSome documentation to review.",
    artifact_name="draft.md",
    artifact_media_type="text/markdown",
)

print(prompt)
```

`config.review()` returns a `ReviewDefinition` containing the stable name,
title, description, four component references, and any additional metadata.
The related accessors `config.lens()`, `config.mission()`, `config.protocol()`,
and `config.output_schema()` return individual component mappings.

`PromptBuilder.build()` resolves the review references and creates the prompt
without contacting a provider. Pass the same `Config` and review identifier to
`Reviewer.review()` to execute a provider-backed review, or use the equivalent
commands described in {doc}`Command-Line Interface <command-line-interface>`.

## Validation and errors

Configuration failures use three focused exception types, all derived from
`ConfigError`:

- `ConfigParseError` reports files that cannot be read, invalid UTF-8, and
  invalid JSON; JSON syntax errors include line and column information;
- `ConfigValidationError` reports an incorrect extension, format, or schema
  version; missing or invalid fields; invalid collection shapes; and unresolved
  review references; and
- `ComponentNotFoundError` reports a missing name requested through
  `config.review()` or a component accessor.

The CLI catches these errors, writes a `proof-goblin: error:` diagnostic to
standard error, and exits with a nonzero status. Python callers may catch the
specific exception or their common `ConfigError` base class.

The loader validates the structural rules implemented for schema version 1.0;
it does not currently load a separate, published JSON Schema document for the
configuration format.

## Provenance

`Config.load()` reads the original file bytes before parsing them. The returned
`Config.source_path` is the absolute path produced by `Path.resolve()`—including
resolution of symbolic links—and `Config.sha256` is the SHA-256 digest of those
exact bytes. Consequently, even a whitespace-only file change produces a
different digest.

An assembled prompt carries the bundle name, bundle version, and digest. A
`ReviewResult` records those values along with the review identifier,
presentation metadata, component names, and artifact provenance. The local
configuration path is not serialized into the result because it is
machine-specific. Use `ReviewResult.to_dict()` or `ReviewResult.to_json()` to
produce the versioned result record.

For a substantial working bundle, see
`proof_goblin/configs/documentation.pgcfg` in a source checkout and
{doc}`Bundled Documentation Reviews <bundled-documentation-reviews>`.
