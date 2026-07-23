"""Validate the release workflow's event and version gates."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.validate_release_ref import read_project_version, validate_event

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIRECTORY = REPOSITORY_ROOT / ".github" / "workflows"


def test_project_version_is_the_public_preview_version() -> None:
    assert read_project_version() == "0.1.0"


def test_testpypi_requires_a_manual_main_dispatch() -> None:
    validate_event(
        event="workflow_dispatch",
        ref="refs/heads/main",
        release_tag="",
        version="0.1.0",
    )

    with pytest.raises(ValueError, match="dispatched from main"):
        validate_event(
            event="workflow_dispatch",
            ref="refs/heads/feature/release",
            release_tag="",
            version="0.1.0",
        )


def test_production_release_tag_must_match_project_version() -> None:
    validate_event(
        event="release",
        ref="refs/tags/v0.1.0",
        release_tag="v0.1.0",
        version="0.1.0",
    )

    with pytest.raises(ValueError, match="does not match project version"):
        validate_event(
            event="release",
            ref="refs/tags/v0.1.1",
            release_tag="v0.1.1",
            version="0.1.0",
        )


def test_read_project_version_rejects_the_wrong_project(tmp_path: Path) -> None:
    project_file = tmp_path / "pyproject.toml"
    project_file.write_text(
        '[project]\nname = "another-project"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="versioned proof-goblin"):
        read_project_version(project_file)


def test_external_actions_are_pinned_to_full_commit_shas() -> None:
    action_reference = re.compile(r"^\s*uses:\s+([^\s]+)@([^\s#]+)", re.MULTILINE)
    for workflow_path in WORKFLOW_DIRECTORY.glob("*.yml"):
        workflow = workflow_path.read_text(encoding="utf-8")
        for action, revision in action_reference.findall(workflow):
            assert re.fullmatch(r"[0-9a-f]{40}", revision), (
                f"{workflow_path.name} must pin {action} to a full commit SHA"
            )


def test_release_oidc_permission_is_limited_to_publish_jobs() -> None:
    workflow = (WORKFLOW_DIRECTORY / "release.yml").read_text(encoding="utf-8")

    assert workflow.count("id-token: write") == 2
    assert "secrets." not in workflow
    assert "password:" not in workflow
    assert "environment:\n      name: testpypi" in workflow
    assert "environment:\n      name: pypi" in workflow
