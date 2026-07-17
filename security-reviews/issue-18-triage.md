# Issue #18 Documentation Security Review Triage

This engineering record dispositions every observation produced by the bounded
documentation review in #18. It is not a formal security audit and is not part
of the reader-facing Proof Goblin documentation.

## Reviewed revision and run manifest

All eight artifact SHA-256 values match repository commit `22a7131` (the merge
of #9) exactly. Every run used configuration `documentation` version `0.5.0`,
configuration SHA-256
`7c1479deece8aa242dff7ccbf353e9d28590a95434bdabbce183ff617cdeb603`,
provider `openai`, and model `gpt-5.6-sol` on July 17, 2026.

| Prefix | Artifact | Artifact SHA-256 | Reviews and response IDs | Observations |
| --- | --- | --- | --- | ---: |
| `HI` | `host-integration.md` | `c70be41330bb8ee23f8ca083e140614ca35671c3207db3ac486661c663ac6f10` | `S`: `resp_032086a484b130f0016a5a230543fc81a2bd8560417300a347`; `P`: `resp_0415d03756122712016a5a2333dc9081a3822261dd18a153e0` | 14 |
| `OP` | `openai-provider.md` | `b863c7c24b9385db4534266614cea55411a1ca56dff38c9c3af8836becf859a7` | `S`: `resp_0a7a5c25bb8a92aa016a5a235fb2cc81a18b5241e57b201c82`; `P`: `resp_06b67076c3323c7f016a5a2396c2e481a0bf7e60ffbb661505` | 19 |
| `CLI` | `command-line-interface.md` | `194290aca5644e975c41017766796448231a974c56270b72e9aa36baf5d5a671` | `S`: `resp_0a98b18bdc74c627016a5a23c8893081a1abb30f1eed51e803`; `P`: `resp_04404e4fecf14029016a5a246043bc81a182fdaca16312e1ce` | 16 |
| `CFG` | `configuration.md` | `3f5f481137a0612cd4d54546bdaae6de4f7c2237733143ffabbba0c6606e8432` | `S`: `resp_08fef61fe7c0c371016a5a249ae690819e936a6223e9c3b146`; `R`: `resp_0abf72a84ffe29f1016a5a24d0b50c819e8211c15d94e4d4c3` | 13 |
| `RPT` | `report-formats.md` | `47919c268c338b7b86b0d706aac44a51b7e8d1da20ed58685cdc7847916dd175` | `S`: `resp_0d19b999a7882927016a5a256e8aa481a29318364a306a9974`; `R`: `resp_0dc90b18e95b82ea016a5a259f1518819e810530aa75427fa1` | 18 |
| `AMT` | `artifact-media-types.md` | `26c422e4228c5079abdc7ddcf05423f4282102a709f7a65c7e9596fe9a92492f` | `S`: `resp_023ddb9b879ab2a3016a5a25cc327c81918eea9440c7b991b4`; `R`: `resp_0254ffe56442ba33016a5a25fb8470819d83ec9812be5edcf8` | 12 |
| `LIM` | `input-limits.md` | `3a7b93638193ec92271d4b5029ac11fe357c9a53310b9571eb8c1cc1e3c5a08c` | `S`: `resp_04dbf50980a68cd1016a5a261cb46481a1997385bd4e91bf05`; `P`: `resp_0d0d1e1214528fcb016a5a26483bf481a192b7b01f58c977cc` | 16 |
| `PA` | `prompt-assembly.md` | `37051b1b1742e616597b38ce8aaaddd0f83717e65f2b1dc5a36b7b2e66ee87f7` | `S`: `resp_018eb381f9be16c0016a5a26707ae081a1b9bf26f580add4fa`; `P`: `resp_083fe45c37a33804016a5a26ac1e28819fa07c078ba1e8a4ff` | 13 |

`S` means `security_expert_security_review`, `P` means
`security_expert_first_pass`, and `R` means
`django_developer_concept_reference`. The two-digit suffix is the observation's
one-based position in its canonical JSON result.

## Disposition and evidence codes

- `RD` — documentation ambiguity resolved in the current documentation.
- `VN` — implementation verified; no defect found, or the question's premise
  is contradicted by the implementation.
- `AR` — accepted, documented boundary or right-sized residual risk.
- `FU` — confirmed or unresolved concern linked to a focused follow-up issue.

Evidence references:

- `ERR` — [Error Reference](../proof_goblin/docs/errors.md), delivered by #33.
- `CFG` — [Configuration](../proof_goblin/docs/configuration.md), delivered by #34.
- `DATA` — [Data Handling and Retention](../proof_goblin/docs/data-handling.md)
  and its contextual links, delivered on the #18 branch.
- `DOC` — the current specialized documentation page named in the row.
- `CODE` — verified against the implementation and existing automated tests.
- `#38` — public API and schema reference contracts.
- `#39` — prompt framing for untrusted artifact metadata.
- `#40` — immutable validated configuration state.
- `#41` — filesystem path-safety boundaries.
- `#42` — post-request response and rendering resource limits.
- `#43` — retry, timeout, concurrency, duplicate execution, and cost contract.

## Observation ledger

### Host Application Integration

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `HI-S01` | Trust boundary for artifact and provider-produced observations | RD | DATA |
| `HI-S02` | Bind jobs and results to the correct user or tenant | RD | DATA; host remains responsible |
| `HI-S03` | Authorization and integrity of `.pgcfg` input | RD | CFG, DATA |
| `HI-S04` | Sensitive content in exception diagnostics | RD | ERR, DATA |
| `HI-S05` | SDK retries composed with host retries | FU | #43 |
| `HI-S06` | Thread/task safety and shared provider instances | FU | #43 |
| `HI-S07` | SHA-256 provenance mistaken for authenticity | RD | CFG, DATA |
| `HI-S08` | API-key inheritance and diagnostic disclosure | RD | ERR, CFG, DATA |
| `HI-P01` | Reload a canonical record for later rendering | FU | #38 |
| `HI-P02` | Serialization versus durable host persistence | RD | DATA |
| `HI-P03` | Provider warning before the first live call | RD | DATA, `openai-provider.md` |
| `HI-P04` | Credential and model prerequisites | RD | CFG, `openai-provider.md` |
| `HI-P05` | Escape untrusted observations in custom presentation | RD | DATA |
| `HI-P06` | Preserve failure diagnostics safely | RD | ERR, DATA |

### OpenAI Provider

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `OP-S01` | Exact data transmitted and provider-side policies | RD | DATA, `openai-provider.md` |
| `OP-S02` | Prompt, raw output, identifier, and provenance lifecycle | RD | DATA |
| `OP-S03` | Cache contents, access, isolation, retention, and deletion | RD | DATA, `command-line-interface.md` |
| `OP-S04` | Artifact prompt-injection behavior | FU | #39 |
| `OP-S05` | Schema-valid but misleading or sensitive observations | RD | DATA; model output remains untrusted |
| `OP-S06` | Unknown provider capacity and oversized requests | RD | `input-limits.md`, ERR |
| `OP-S07` | Timeout, retry, duplicate request, and cost behavior | FU | #43 |
| `OP-S08` | Sensitive values in provider diagnostics | RD | ERR |
| `OP-S09` | Credential-free request versus SDK credentials/tracing | RD | CFG, DATA |
| `OP-S10` | Alternative-model compatibility responsibility | AR | CFG, `openai-provider.md`; no model catalog is intentionally maintained |
| `OP-P01` | Starting directory and installation prerequisites | RD | `getting-started.md`, `openai-provider.md` |
| `OP-P02` | Provider transmission warning before sensitive review | RD | DATA, `openai-provider.md` |
| `OP-P03` | Inspect and remove sensitive cache data | RD | DATA, `command-line-interface.md` |
| `OP-P04` | In-memory and persisted prompt/raw-output behavior | RD | DATA |
| `OP-P05` | Remove a temporary exported API key | FU | #38 |
| `OP-P06` | Verify successful live smoke-test completion | VN | CODE; example prints provider, response, count, and observations or exits on provider failure |
| `OP-P07` | Determine compatible model before cost | AR | CFG; compatibility is provider/account-specific and preflight can be `unknown` |
| `OP-P08` | Remediation and safe retry by provider failure | RD | ERR |
| `OP-P09` | Request-cost boundary and token-usage verification | FU | #43 |

### Command-Line Interface

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `CLI-S01` | Reports can quote artifact content through evidence | RD | DATA, `report-formats.md`, `command-line-interface.md` |
| `CLI-S02` | Provider-side data handling before a live review | RD | DATA |
| `CLI-S03` | Cache disable, inspection, expiration, and deletion | RD | DATA; absence of automatic expiry/deletion is explicit |
| `CLI-S04` | Credentials and transport excluded from cache identity | RD | CFG, DATA |
| `CLI-S05` | Cache path permissions, ownership, and symbolic links | FU | #41 |
| `CLI-S06` | Output path permissions and symbolic links | FU | #41 |
| `CLI-S07` | Sensitive prompts written to standard output | RD | DATA, `command-line-interface.md` |
| `CLI-S08` | “At most once” versus SDK retries | FU | #43 |
| `CLI-S09` | Stale reservation versus legitimate long review | FU | #43 |
| `CLI-P01` | Installation starting state | RD | `getting-started.md` |
| `CLI-P02` | Provider data-handling boundary | RD | DATA |
| `CLI-P03` | Reconcile report confidentiality claims | RD | DATA, `report-formats.md` |
| `CLI-P04` | Terminal, CI, and redirection capture of prompts | RD | DATA |
| `CLI-P05` | Verify provider-account context after cache reuse | RD | DATA; isolate cache storage when transport identity matters |
| `CLI-P06` | Cache retention and platform permissions | RD | DATA, `command-line-interface.md` |
| `CLI-P07` | Recovery after partial multi-output completion | RD | ERR, `command-line-interface.md` |

### Configuration

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `CFG-S01` | Bundle trust, authorization, digest, and authenticity | RD | CFG, DATA |
| `CFG-S02` | Bundle fields transmitted and secret-placement warning | RD | CFG, DATA |
| `CFG-S03` | Privileged configuration versus untrusted artifact content | FU | #39 |
| `CFG-S04` | Output-schema rejection stage, dialect, and cost | FU | #38, #42 |
| `CFG-S05` | Large, cyclic, non-JSON, or mutable `from_mapping()` input | FU | #40, #42 |
| `CFG-S06` | Control characters in names and prompt/report contexts | FU | #39 |
| `CFG-S07` | Configuration path symbolic-link race and provenance | FU | #41 |
| `CFG-S08` | Sensitive CLI diagnostics and provenance | RD | ERR, DATA |
| `CFG-R01` | Exception count and `InputLimitError` inheritance | RD | ERR, CFG |
| `CFG-R02` | Supply and default of active `InputLimits` | RD | CFG |
| `CFG-R03` | `from_mapping()` source path, digest, and provenance | FU | #38 |
| `CFG-R04` | JSON Schema dialect, supported subset, and exceptions | FU | #38 |
| `CFG-R05` | `.pgcfg` suffix case and multi-suffix behavior | FU | #38 |

### Report Formats

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `RPT-S01` | Prompt omission does not make a report non-sensitive | RD | DATA, `report-formats.md` |
| `RPT-S02` | Report access, retention, and deletion | RD | DATA |
| `RPT-S03` | Output/cache permissions, links, atomicity, and cleanup | FU | #41 |
| `RPT-S04` | Cached-result integrity and intended-input association | AR | CODE, DATA; schema/provenance are verified, but local cache files are not authenticated |
| `RPT-S05` | Injected renderer access to retained prompt fields | RD | DATA; renderers receive the in-memory result and remain host-trusted code |
| `RPT-S06` | Prompt-inclusive JSON contents and sensitivity | RD | DATA, `report-formats.md` |
| `RPT-S07` | Markdown security claims across parser configurations | FU | #38 |
| `RPT-S08` | Resource limits for rendering large results/prompts | FU | #42 |
| `RPT-S09` | Local timezone as identifying metadata | RD | DATA |
| `RPT-R01` | Complete `render_report()` and `render_prompt()` signatures | FU | #38 |
| `RPT-R02` | Public renderer classes and protocol contract | FU | #38 |
| `RPT-R03` | Output-path format selection and precedence | RD | CFG, `command-line-interface.md` |
| `RPT-R04` | Canonical result schema identifier and versions | FU | #38 |
| `RPT-R05` | `include_prompt` with non-JSON or injected renderers | RD | CFG, ERR, `report-formats.md` |
| `RPT-R06` | Escaping configuration-derived Markdown values | FU | #38 |
| `RPT-R07` | Exact Markdown escaping/encoding contract | FU | #38 |
| `RPT-R08` | Timezone source and deterministic control | FU | #38 |
| `RPT-R09` | Exact prompt JSON fields and nesting | FU | #38 |

### Artifact Media Types

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `AMT-S01` | Declared media type mistaken for content safety | RD | `artifact-media-types.md`, DATA |
| `AMT-S02` | Provider support for arbitrary valid textual subtype | VN | CODE; media type is prompt text, not a provider API content-type selector |
| `AMT-S03` | Media type participation in cache identity | VN | CODE, CFG; canonical type is included in the user prompt/request |
| `AMT-S04` | UTF-8 and input limits across entry paths | VN | CODE, `input-limits.md`; Python accepts decoded strings and measures their UTF-8 encoding |
| `AMT-S05` | Explicit versus inferred provenance | AR | `artifact-media-types.md`; canonical semantic value is deliberately retained, resolution path is not |
| `AMT-R01` | Complete resolver signature | FU | #38 |
| `AMT-R02` | Explicit media type through CLI, builder, and reviewer | RD | CFG, `artifact-media-types.md` |
| `AMT-R03` | Exception import and diagnostic categories | RD | ERR |
| `AMT-R04` | Dotfiles, trailing dots, and path-component edge cases | FU | #38 |
| `AMT-R05` | UTF-8 behavior for direct Python strings | FU | #38 |
| `AMT-R06` | Exact MIME token grammar | RD | `artifact-media-types.md` |
| `AMT-R07` | `input-limits` cross-reference resolution | VN | CODE; strict Sphinx build resolves the document link |

### Input Limits and Provider Preflight

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `LIM-S01` | Configuration limit enforced before unbounded read | VN | CODE; stat, bounded `limit + 1` read, and second enforcement |
| `LIM-S02` | Mismatched policies across loader, builder, and reviewer | AR | CFG; explicit-object policy with host responsibility is documented |
| `LIM-S03` | Resource-intensive decoded `from_mapping()` objects | FU | #40, #42 |
| `LIM-S04` | Cache contents, access, retention, and deletion | RD | DATA |
| `LIM-S05` | Data transmitted to provider and provider policy | RD | DATA |
| `LIM-S06` | Independent response/parsing/error-body limits | FU | #42 |
| `LIM-S07` | Retry, duplicate execution, cache consistency, and cost | FU | #43 |
| `LIM-S08` | Invalid UTF-8 and diagnostic disclosure | RD | ERR |
| `LIM-P01` | Verify one custom policy through assembly and execution | FU | #38 |
| `LIM-P02` | Detect mismatched `InputLimits` policies | RD | CFG; mismatch is not detected and host responsibility is explicit |
| `LIM-P03` | `InputLimits` value and relationship constraints | FU | #38 |
| `LIM-P04` | Exception for known excessive provider capacity | RD | ERR, `input-limits.md` |
| `LIM-P05` | Host boundary for `Config.from_mapping()` | RD | CFG, DATA; additional resource decision tracked by #42 |
| `LIM-P06` | Configuration limit applied before complete load | VN | CODE |
| `LIM-P07` | Distinguish UTF-8 decoding and limit failures | RD | ERR |
| `LIM-P08` | Configure OpenAI maximum output allowance consistently | RD | CFG, `openai-provider.md` |

### Prompt Assembly

| ID | Concern | Disposition | Evidence or follow-up |
| --- | --- | --- | --- |
| `PA-S01` | Trust and provenance requirements for `.pgcfg` | RD | CFG, DATA |
| `PA-S02` | Preserve separate system/user provider roles | VN | CODE, `prompt-assembly.md`, `openai-provider.md` |
| `PA-S03` | Untrusted artifact name and media-type framing | FU | #39 |
| `PA-S04` | Provider transmission, retention, credentials, and cost | RD | DATA |
| `PA-S05` | Prompt-file permissions, links, replacement, and partial writes | FU | #41 |
| `PA-S06` | HTML rendering safety versus downstream embedding | VN | CODE, DATA; built-in escaping is tested and downstream transformation remains host-owned |
| `PA-S07` | Inspected prompt exactly matching later execution | FU | #40; reviewer rebuild is deterministic only while inputs remain unchanged |
| `PA-S08` | Sensitive prompt/configuration diagnostics | RD | ERR, DATA |
| `PA-P01` | Trust requirements for configuration before loading | RD | CFG, DATA |
| `PA-P02` | Local memory exhaustion before builder limits | FU | #42 |
| `PA-P03` | Successful prompt-assembly verification | RD | `prompt-assembly.md`; returned `Prompt`, inspection, and rendering steps are explicit |
| `PA-P04` | Printing/writing sensitive prompt output | RD | DATA, `prompt-assembly.md` |
| `PA-P05` | Artifact-file failure recognition and recovery | RD | ERR |

## Summary

The ledger contains 121 unique observations. Documentation work in #33, #34,
and the #18 branch resolves the dominant error, configuration, and data-lifecycle
ambiguities. Verified rows record cases where current code or strict builds
already establish the behavior. Accepted-risk rows preserve deliberate,
right-sized boundaries rather than implying stronger guarantees.

All remaining concerns are linked to #38–#43. Closing #18 does not require
implementing those follow-ups; it requires preserving this disposition and
ensuring each unresolved concern has an owning issue.
