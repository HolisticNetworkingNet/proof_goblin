# Release Process

This page defines the version, artifact, tag, and release-note contract for the
Proof Goblin 0.1.0 public preview. Secure publishing credentials, Trusted
Publishing, TestPyPI, production PyPI environments, attestations, and recovery
controls are owned by GitHub issue #13 and must be complete before publication.

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
audit, and the TestPyPI rehearsal defined by #13 succeed for the release commit.

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
