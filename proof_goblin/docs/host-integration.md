# Host Application Integration

Proof Goblin is intended to be installed as a library. A host such as WBR owns
artifact creation, execution scheduling, persistence, permissions, and
presentation. Proof Goblin owns review configuration, prompt assembly, provider
execution, output validation, and normalized observations.

## Stable result record

`ReviewResult.to_dict()` returns a versioned, JSON-compatible record suitable
for a database JSON field, application serializer, job result, or API response:

```python
result = reviewer.review(
    config=config,
    review="homepage_first_pass",
    artifact=rendered_homepage,
    artifact_name="homepage.html",
    artifact_media_type="text/html",
)

payload = result.to_dict()
```

The record includes:

- format and schema versions;
- review name;
- configuration name, version, and SHA-256 digest;
- artifact name, media type, and SHA-256 digest;
- provider, resolved model, response ID, and token usage;
- creation time; and
- normalized observations.

The bundled schema is
`proof_goblin/schemas/review-result.v1.schema.json`.

## JSON serialization

For text storage or transport:

```python
payload_json = result.to_json()
```

## Prompt retention

Prompt text is excluded by default because the user portion contains the entire
reviewed artifact. A host that has an explicit archival policy can include it:

```python
archival_payload = result.to_dict(include_prompt=True)
```

Configuration and artifact digests remain present without prompt retention, so
the host can associate the record with the exact inputs it stores separately.

## WBR service boundary

A WBR-owned service can translate Django concepts into Proof Goblin inputs while
keeping Django out of this package:

```python
from proof_goblin import Config, OpenAIProvider, Reviewer


class ProofService:
    def __init__(self, config_path):
        self.config = Config.load(config_path)
        self.reviewer = Reviewer(OpenAIProvider())

    def review_homepage(self, *, html, site_name):
        result = self.reviewer.review(
            config=self.config,
            review="homepage_first_pass",
            artifact=html,
            artifact_name=f"{site_name}-homepage.html",
            artifact_media_type="text/html",
        )
        return result.to_dict()
```

WBR can then persist that returned dictionary without depending on Proof
Goblin's internal dataclass layout.
