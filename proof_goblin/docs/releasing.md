# Release Process

This page defines the version, artifact, tag, publishing, provenance, and
release-note contract for the Proof Goblin 0.1.0 public preview. The production
workflow uses PyPI Trusted Publishing: GitHub exchanges a short-lived OpenID
Connect identity for a project-scoped upload token. No PyPI username, password,
API token, or publishing secret belongs in GitHub.

## Public-preview scope

Proof Goblin 0.1.0 reviews one textual artifact per `Reviewer` or command-line
execution. A caller may run several independent reviews and reconcile their
observations, but the release does not provide a multi-document request model or
cross-document synthesis contract.

Multi-document review is not a prerequisite for 0.1.0. The input-limit model
retains fields that can support a future multi-document design, but those fields
do not promise that feature. The Public Preview milestone gate is the tested
single-artifact contract documented above; any future multi-document behavior
requires its own design, implementation, tests, and release scope.

## Version and tag contract

`pyproject.toml` is the authoritative source of the distribution version. The
0.1.0 release must satisfy all of these invariants:

- the project metadata reports distribution name `proof-goblin` and version
  `0.1.0`;
- the import package remains `proof_goblin` and the console command remains
  `proof-goblin`;
- both the wheel and source distribution report version `0.1.0`;
- an installed environment reports `0.1.0` through
  `importlib.metadata.version("proof-goblin")`; and
- the production tag is exactly `v0.1.0` and points to the reviewed commit from
  which the published artifacts were built.

Do not create or move the production tag merely to test the release workflow.
TestPyPI rehearsal must use the non-production path established by #13. Once a
version has been published to PyPI, its files and tag are immutable release
records; corrections require a new version.

## Artifact validation

Build the source distribution and wheel together through isolated PEP 517
builds, then validate those exact files:

```bash
python -m build --outdir release-dist
python -m twine check --strict release-dist/*
python scripts/validate_distribution.py release-dist
python scripts/validate_installation.py release-dist
```

`validate_distribution.py` enforces the public package boundary, required
runtime resources, console entry point, license, and metadata in both artifacts.
`validate_installation.py` creates separate clean environments for the wheel and
source distribution. It verifies dependency consistency, the installed command,
core imports, version metadata, bundled configuration and schemas, prompt
assembly, and initialization of the optional OpenAI integration without making
a provider request.

Pull-request CI runs the same artifact checks. A release candidate is not
eligible for publication unless all required pull-request checks, the dependency
audit, and the TestPyPI rehearsal succeed for the release commit.

## Publishing workflow and permissions

`.github/workflows/release.yml` is the only authorized publishing workflow. It
has two deliberately separate entry points:

- manual `workflow_dispatch` from `main` builds, validates, and publishes to
  TestPyPI through the `testpypi` environment; and
- publication of a non-prerelease GitHub Release builds, validates, and
  publishes its exact `v0.1.0` tag to production PyPI through the `pypi`
  environment.

Pull requests, branch pushes, tags without a published GitHub Release, draft
releases, and prereleases cannot reach either publishing job. The release-source
check also rejects a manual run outside `main`, a production tag that does not
match the project version, a tag that does not identify the checked-out commit,
or a commit that is not contained in protected `main`. Main can accept changes
only through the required pull-request checks documented in {doc}`development`.

The build job has read-only repository permission and never receives an OIDC
token. It builds the wheel and source distribution once, validates them, records
their SHA-256 hashes, and uploads one immutable GitHub Actions artifact. Each
publishing job only downloads that artifact, verifies the recorded hashes, and
runs the PyPA publishing action. Only those jobs have `id-token: write`; all
other unspecified GitHub token permissions are absent.

All external actions are pinned to reviewed full commit SHAs with release
comments. Dependabot monitors GitHub Actions weekly. An action update must be
reviewed against its canonical repository and release before merge; a floating
tag is not an acceptable production pin.

## GitHub environments

Configure two GitHub environments before the first rehearsal. They require no
secrets or variables:

| Environment | Deployment source | Required protection |
| --- | --- | --- |
| `testpypi` | branch `main` only | at least one trusted maintainer reviewer; prevent bypass where available |
| `pypi` | tags matching `v*` only | at least one trusted maintainer reviewer; prevent bypass where available |

If one person is the only available release maintainer, self-review must remain
possible or the deployment will be impossible; the approval is still a
separate, recorded release decision. Add a second trusted reviewer and prevent
self-review when the maintainer model supports it. Reassess the reviewer list
whenever repository access changes.

## Trusted Publisher registration

Register separate GitHub Actions Trusted Publishers on TestPyPI and PyPI. The
identity fields must match exactly:

| Field | TestPyPI | PyPI |
| --- | --- | --- |
| PyPI project | `proof-goblin` | `proof-goblin` |
| Owner | `HolisticNetworkingNet` | `HolisticNetworkingNet` |
| Repository | `proof_goblin` | `proof_goblin` |
| Workflow | `release.yml` | `release.yml` |
| Environment | `testpypi` | `pypi` |

Use a pending publisher if the project does not exist yet. A pending publisher
does not reserve the project name until its first successful upload, so confirm
the normalized distribution name immediately before rehearsal. Do not configure
a broader publisher without an environment claim.

## TestPyPI rehearsal

After the workflow and environment configuration are merged:

1. Confirm that `main` is current and every required check passed for its latest
   release candidate.
2. Register the TestPyPI publisher shown above.
3. Run **Publish distributions** manually from `main` and approve only the
   `testpypi` deployment.
4. Confirm that the workflow built once, clean-installed both artifacts,
   downloaded the same artifact in the publishing job, verified both SHA-256
   values, and uploaded without a stored credential.
5. Inspect both TestPyPI files, their metadata, project links, hashes, and
   published attestations. Install 0.1.0 from TestPyPI in a clean environment
   and repeat `scripts/smoke_test_install.py` without making a provider request.
6. Record the workflow run, artifact hashes, and verification result in the
   release issue before authorizing production.

TestPyPI and PyPI are separate services with separate accounts and publisher
configuration. A successful rehearsal proves the workflow shape and TestPyPI
identity; production still requires its own publisher, environment approval,
and explicit release decision.

## Tag and GitHub release notes

After the release changes have merged to `main`, the release operator must:

1. Record the explicit human decision to publish.
2. Select the reviewed `main` commit and confirm that its `pyproject.toml` and
   built artifact metadata all report `0.1.0`.
3. Create the annotated `v0.1.0` tag at that exact commit. The tag must never
   point to a documentation-only follow-up or a different build input.
4. Create a draft GitHub Release for `v0.1.0`, using generated comparison notes
   as source material rather than publishing them unreviewed.
5. Edit the release notes to include highlights, installation commands,
   supported Python versions, known limitations, the experimental pre-1.0 API
   warning, and upgrade or compatibility information where applicable.
6. Publish through the reviewed workflow from #13, then add or verify direct
   links to the PyPI release and its provenance information.
7. Install the public artifacts, repeat the installed smoke test, verify hashes
   and attestations, and confirm that PyPI shows the intended project links.

The release title is `Proof Goblin 0.1.0`. Publication and any announcement are
separate deliberate actions; neither is implied by merging a pull request or by
creating a draft GitHub Release.

## Public verification

For each wheel and source distribution after production publication:

1. Compare the SHA-256 value displayed by PyPI with the workflow's
   `SHA256SUMS` record.
2. Confirm that PyPI identifies the expected GitHub repository, workflow, and
   `pypi` environment as the Trusted Publisher identity.
3. Install `pypi-attestations` in an isolated verification environment and run
   the following command separately for each PyPI file URL:

   ```bash
   pypi-attestations verify pypi \
     --repository https://github.com/HolisticNetworkingNet/proof_goblin \
     PYPI_DISTRIBUTION_URL
   ```

4. Confirm that PyPI displays the Source, Documentation, Issues, and Release
   notes project links with the expected verification state.

A valid publish attestation binds a distribution digest to the authorized
Trusted Publisher identity and detects modification after attestation. It does
not prove that the source, dependencies, workflow, maintainer, or resulting
package is safe, vulnerability-free, correctly designed, or worthy of trust.
Dependency auditing, review, branch protection, and human judgment remain
separate controls.

## Accounts, roles, and long-lived tokens

Before production publication, inspect both PyPI and TestPyPI account state:

- every owner and maintainer account has two-factor authentication enabled and
  securely stored recovery codes plus at least one recoverable second factor;
- only people who currently require administrative access retain a project
  role, and the release record names who can change Trusted Publishers;
- Trusted Publishers on the project match the reviewed identities above; and
- all obsolete project or account API tokens are revoked after the TestPyPI
  path is proven. No replacement token is added to GitHub.

Review project roles and publishers when a maintainer joins, leaves, changes
responsibility, or loses control of an account.

## Compromise and recovery

If the GitHub repository, workflow, environment, or maintainer account may be
compromised:

1. Stop pending deployments and disable the publishing workflow.
2. Remove both Trusted Publishers on PyPI and TestPyPI so the workflow identity
   can no longer mint upload tokens.
3. Revoke unexpected sessions, credentials, deploy keys, personal tokens, and
   environment approvals; restore trusted repository and account access.
4. Audit workflow changes, environment rules, tags, releases, project roles,
   publishers, uploaded files, hashes, and provenance records.
5. Yank a suspect release while investigating. Do not silently replace an
   immutable version; publish a corrected version only after a documented
   review and fresh provenance verification.
6. Re-register the exact publishers, repeat TestPyPI rehearsal, and require a
   new explicit production decision before restoring publication.

If a PyPI account or project is compromised, remove unauthorized roles and
publishers, reset account credentials and recovery factors, revoke long-lived
tokens, contact PyPI support when ownership cannot be safely restored, and then
perform the same artifact and provenance audit. Treat attestations as evidence
during the investigation, not as proof that a suspect release is harmless.

## Authoritative references

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
- [Adding a Trusted Publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [Publishing with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [PyPI digital attestations](https://docs.pypi.org/attestations/)
- [Consuming attestations](https://docs.pypi.org/attestations/consuming-attestations/)
- [GitHub deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [GitHub Actions secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
