# Prompt assembly

`PromptBuilder` resolves a named review and combines its components with an
artifact. Prompt assembly is deterministic and does not contact an AI provider.

```python
from pathlib import Path

from proof_goblin import Config, PromptBuilder

config = Config.load("proof_goblin/examples/restaurants.pgcfg")
artifact = Path("proof_goblin/examples/homepage.html").read_text()

prompt = PromptBuilder(config).build(
    review="homepage_first_pass",
    artifact=artifact,
    artifact_name="homepage.html",
    artifact_media_type="text/html",
)

print(prompt)
```

## Resolved reviews

`PromptBuilder.resolve()` exposes the exact lens, mission, protocol, and output
schema selected by a named review. This makes the inputs inspectable before a
prompt is generated.

## Prompt roles

An assembled `Prompt` keeps two roles separate:

- `system` contains the resolved configuration and general review instructions;
- `user` contains the artifact and its identifying information.

The system instructions explicitly treat the artifact as untrusted review
material. Artifact content is never interpolated into the system instructions.

## Provenance

The assembled prompt records the review and configuration names, configuration
version and digest, artifact name and media type, and the artifact's SHA-256
digest. This information can later travel with generated observations.
