# Input Limits and Provider Preflight

Proof Goblin applies deterministic input limits before reserving a CLI cache
entry or executing a provider request. These limits protect application
stability, request cost, reproducibility, and review focus. They are not a
general security sandbox and do not guarantee that an accepted review is
appropriately scoped.

## Default limits

`DEFAULT_INPUT_LIMITS` is an immutable `InputLimits` value with these UTF-8
byte ceilings:

| Boundary | Default |
| --- | ---: |
| Configuration file loaded by `Config.load()` | 1,048,576 bytes (1 MiB) |
| One artifact | 262,144 bytes (256 KiB) |
| All artifacts in one review | 262,144 bytes (256 KiB) |
| Assembled system prompt | 131,072 bytes (128 KiB) |
| Complete assembled prompt | 524,288 bytes (512 KiB) |

The per-artifact and aggregate limits are equal while a review accepts one
artifact. Keeping both fields in the policy allows a future multi-document
review to enforce the same per-document limit and a separate total without
replacing the public policy.

The system-prompt ceiling covers the selected Proof Lens, Mission, Review
Protocol, Output Schema, and fixed instructions. The total is the sum of the
exact system and user prompt UTF-8 bytes. Artifact metadata and prompt framing
therefore participate in the total without receiving separate public knobs.

An exact limit is accepted. One byte over is rejected with `InputLimitError`.
The error identifies the boundary, measurement, and limit but never includes
configuration-derived prompt text or artifact content. Proof Goblin does not
truncate, summarize, or rewrite input to make it fit.

## Configure limits in a host

Hosts can derive an application policy without changing process-global state:

```python
from dataclasses import replace

from proof_goblin import (
    DEFAULT_INPUT_LIMITS,
    Config,
    OpenAIProvider,
    PromptBuilder,
    Reviewer,
)

limits = replace(
    DEFAULT_INPUT_LIMITS,
    max_artifact_bytes=131_072,
    max_total_artifact_bytes=131_072,
)

config = Config.load("documentation.pgcfg", limits=limits)
prompt = PromptBuilder(config, limits=limits).build(
    review="reader_first_pass",
    artifact="Draft documentation",
)
reviewer = Reviewer(OpenAIProvider(), limits=limits)
```

Pass the same policy at each boundary the host uses. `Config.from_mapping()`
receives an already-decoded object and therefore has no original file size to
enforce; selected configuration content remains subject to the system and
total prompt limits during assembly.

The command-line interface uses `DEFAULT_INPUT_LIMITS`. It reads artifact files
and standard input through bounded readers, so an oversized CLI artifact is
rejected without first reading an unbounded value into memory.

## Inspect prompt measurements

Every accepted `Prompt` exposes a `PromptMeasurements` record:

```python
print(prompt.measurements.artifact_bytes)
print(prompt.measurements.system_prompt_bytes)
print(prompt.measurements.user_prompt_bytes)
print(prompt.measurements.total_prompt_bytes)
```

The record contains counts only. It does not retain another copy of the prompt
or artifact. Byte measurements are provider-neutral safety boundaries, not an
estimate of model tokens.

## Provider preflight

`Reviewer.preflight()` assembles and validates the same request used by
`Reviewer.review()` without generating output:

```python
result = reviewer.preflight(
    config=config,
    review="reader_first_pass",
    artifact="Draft documentation",
)

print(result.capacity_status)
print(result.max_output_tokens)
```

Provider preflight validates provider-specific request compatibility and
returns the credential-free `ProviderRequest` description used for cache
identity and execution. It reserves the same maximum output tokens sent during execution. When a provider
has reliable input-token and context-window information, capacity is reported
as `fits` or `exceeds`. Otherwise it is `unknown`. A known excessive request is
rejected before generation; unknown capacity proceeds after the deterministic
byte limits pass.

The OpenAI adapter validates strict structured-output compatibility locally,
uses an 8,192-token default maximum output allowance, and explicitly disables
provider truncation. It reports unknown capacity because Proof Goblin does not
guess from a hard-coded model catalog or require an additional remote token
count for every review. Hosts can call `preflight()` and reject `unknown` when
their operating policy requires confirmed capacity.

Preflight does not probe credentials, account quota, rate-limit headroom,
network access, provider health, likely refusals, exact cost, prompt-injection
safety, or review quality. Those properties are transient, application-owned,
or unknowable before execution. The real provider call must still handle
normal failures.

## Technical fit and review focus

A prompt that fits every byte and token boundary can still be too broad for a
useful review. Limits answer whether Proof Goblin will accept and attempt the
request. Review authors and host applications remain responsible for choosing
an artifact and review mission with a coherent cognitive scope.
