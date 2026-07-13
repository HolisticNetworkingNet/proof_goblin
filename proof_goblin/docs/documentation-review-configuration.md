# Documentation Review Configuration

Proof Goblin ships a reusable `documentation.pgcfg` configuration bundle for
reviewing documentation from three distinct perspectives. These are lenses,
not reading levels: each represents a reader with different knowledge,
responsibilities, and reasons for consulting the document.

| Review | Lens | Primary concern |
| --- | --- | --- |
| `business_owner_first_pass` | Business owner | Business meaning, decisions, responsibilities, risks, and next steps |
| `django_developer_first_pass` | Experienced Django and Python developer | Implementability, contracts, prerequisites, examples, errors, testing, and operations |
| `technical_writer_first_pass` | Technical writer | Audience fit, organization, terminology, clarity, consistency, and information gaps |
| `front_end_readability` | Technical writer | Scan path, headings, density, labels, links, and reader-facing comprehension |

The readability review remains a mission rather than a separate lens. A
technical writer performs that assignment using the same professional
perspective, while the mission narrows the review to the readability of
front-end content.

All four reviews share the `documentation_questions_only` protocol. They emit
evidence-based questions for the author and do not rewrite the source or invent
solutions.

## Loading the Bundle

The bundle is installed with the Python package:

```python
from pathlib import Path

import proof_goblin

from proof_goblin import Config


config_path = (
    Path(proof_goblin.__file__).parent / "configs" / "documentation.pgcfg"
)
config = Config.load(config_path)
```

It can then be passed to the same builder or reviewer used with any other
Proof Goblin configuration:

```python
from proof_goblin import PromptBuilder


prompt = PromptBuilder(config).build(
    review="django_developer_first_pass",
    artifact=documentation,
)
```

The configuration file is ordinary, versionable JSON. A project can use the
bundled version directly, copy it into its own repository, or extend the same
structure with domain-specific lenses and missions.
