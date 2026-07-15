# Development Status

Proof Goblin is an experimental but operational pure-Python library. It has no
Django dependency and no database. Its implemented core includes configuration
validation, deterministic prompt assembly, provider execution, structured
observation validation, provenance, and JSON-compatible result serialization.

The initial development milestones are:

1. load and validate a `.pgcfg` configuration bundle (complete);
2. resolve a named review and assemble an inspectable prompt (complete);
3. send the review to a provider and parse structured observations (complete); and
4. expose the workflow through a small command-line interface (complete).

Configuration loading and prompt assembly do not require an AI provider and are
tested deterministically. Provider and reviewer tests use local test doubles;
only the live example requires an API key and network access.

## Development environment

Install Proof Goblin in editable mode with the local quality, test, and
documentation dependencies:

```bash
python -m pip install -e ".[dev,test,docs]"
```

The optional `dev` dependency set contains repository-development tools rather
than packages required by Proof Goblin at runtime.

## Linting and formatting

Ruff provides the repository's linting, import-ordering, and formatting policy.
Its configuration is committed in `pyproject.toml`, so local and automated
checks use the same Python version, rules, and formatting behavior.

Run both read-only checks before committing:

```bash
ruff check .
ruff format --check .
```

Apply available lint fixes and format the codebase with:

```bash
ruff check --fix .
ruff format .
```

Review the resulting diff and rerun Ruff, pytest, and the strict documentation
build after any automated fix. Static type checking is not part of the current
Ruff policy and remains a separate future design decision.

## Automated checks

GitHub Actions separates fast feedback from complete pull-request validation:

- **Push checks** run on every push to every branch and execute `ruff check .`
  plus `python -m pytest -q -W error` on Python 3.11. This catches routine
  Python, behavioral, and deprecation errors quickly without duplicating the
  full platform and Python-version matrix on every intermediate commit.
- **Pull request checks** run when a pull request is opened and whenever its
  branch is updated, reopened, or marked ready for review. They run Ruff lint
  (`ruff check .`), Ruff formatting (`ruff format --check .`), the complete
  warnings-as-errors pytest matrix, `proof-goblin --help` in every matrix lane,
  and the strict Sphinx documentation build.
- **Dependency security** runs on every pull request, every Monday on a
  schedule, and on manual dispatch. It audits the complete installed dependency
  surface for known vulnerabilities.

Ubuntu is the primary CI platform. The pull-request pytest matrix covers every
supported CPython minor version from 3.11 through 3.14 on Ubuntu and adds a
representative Python 3.14 run on macOS. A Windows Python 3.14 lane is included
as inexpensive compatibility coverage, but Windows is not currently a declared
support requirement.

All three workflows use read-only repository permissions, cancel superseded
runs, and receive no OpenAI credentials. Only the dependency audit installs the
optional OpenAI package, solely so that package and its transitive dependencies
are included in the vulnerability scan; it makes no provider call. Run the core
checks locally with:

```bash
ruff check .
ruff format --check .
python -m pytest -q -W error
proof-goblin --help
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```

## Dependency security

The canonical `HolisticNetworkingNet/proof_goblin` repository has its dependency
graph, Dependabot alerts, and Dependabot security updates enabled. The committed
`.github/dependabot.yml` configuration monitors both Python packages and GitHub
Actions every Monday at 09:00 America/New_York. Minor and patch version updates
are grouped within each ecosystem, major updates remain separate for focused
review, and security updates are grouped within each ecosystem when multiple
fixes are available.

Dependabot pull requests are never merged automatically. They must pass the
normal protected-branch checks, including the `Dependency audit` job. That job
runs on every pull request, every Monday on a schedule, and on manual dispatch.
It installs the runtime and every optional dependency group, then runs
`pip-audit` with strict dependency collection and no OpenAI credentials. Run the
equivalent audit in a clean virtual environment with:

```bash
python -m pip install --upgrade pip
python -m pip install ".[dev,docs,openai,security,test]"
python -m pip uninstall --yes proof-goblin
python -m pip_audit --local --strict --progress-spinner off
```

Removing only the local project distribution is intentional: its dependencies
remain installed, while strict `pip-audit` does not try to find the unpublished
Proof Goblin package in the Python vulnerability database. Upgrading `pip`
before the scan ensures the installer itself is included at a current version.

All third-party GitHub Actions must be pinned to a full immutable commit SHA. A
trailing version comment records the corresponding release for human review,
and Dependabot proposes future Action SHA updates. New Actions require the same
pinning and verification that the commit belongs to the canonical Action
repository.

Repository maintainers own alert triage. Critical and high-severity findings
are assessed within one business day; moderate findings within seven days; and
low findings within thirty days or the next scheduled update cycle, whichever
comes first. Breaking upgrades receive a separate pull request and explicit
compatibility review. An alert dismissal or `pip-audit` ignore requires a
tracking issue that records the vulnerability identifier, affected dependency,
rationale, owner, compensating controls, and an expiry no later than thirty
days. Exceptions must be removed or explicitly renewed after review at expiry.

## Repository merge policy

The `main` branch is governed by the active **Protect main** GitHub repository
ruleset. Its version-controlled representation is
`.github/rulesets/main.json`. Changes to the live ruleset and this file must be
reviewed and updated together.

Normal changes to `main` must arrive through a pull request whose branch is
current with `main`. The following complete pull-request checks are required:

- `Ruff lint and format`;
- `Strict documentation build`;
- `Dependency audit`;
- `Tests (ubuntu-latest, Python 3.11)`;
- `Tests (ubuntu-latest, Python 3.12)`;
- `Tests (ubuntu-latest, Python 3.13)`;
- `Tests (ubuntu-latest, Python 3.14)`;
- `Tests (macos-latest, Python 3.14)`; and
- `Tests (windows-latest, Python 3.14)`.

Each required `Tests` job runs pytest with warnings treated as errors and then
verifies the installed `proof-goblin` command-line entry point.

The fast `Ruff and pytest error checks` push job still runs on every branch but
is not an additional required pull-request gate because its Ruff lint and
Python 3.11 pytest coverage duplicate the complete checks. Unresolved review
conversations block merging. The current contributor model requires no
approving review, no signed commits, and no linear history; merge commits remain
the repository's normal merge method. The ruleset also blocks deletion and
force pushes of `main`.

Only active `HolisticNetworkingNet` organization owners have a pull-request-only
ruleset bypass. It cannot be used to push directly to `main`, delete it, or force
push it. The bypass is an emergency mechanism, not an alternate normal
workflow. It may be used only to repair broken required-check infrastructure or
apply an urgent security correction when the normal gates cannot operate. The
owner using it must open or update a tracking issue with the reason, affected
commit, checks performed, and follow-up work before merging the emergency pull
request.

## Documentation conventions

Documentation source files use MyST Markdown and live in `proof_goblin/docs/`.
Keep conceptual documentation independent of a particular provider or
application interface unless the page is specifically about that integration.

Before committing documentation changes, run a warnings-as-errors build:

```bash
python -m sphinx -W --keep-going -b html proof_goblin/docs proof_goblin/docs/_build/html
```
