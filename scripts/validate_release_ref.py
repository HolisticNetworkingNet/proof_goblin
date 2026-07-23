"""Reject release workflow sources that do not match the version contract."""

from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path


def read_project_version(project_file: Path = Path("pyproject.toml")) -> str:
    with project_file.open("rb") as stream:
        project = tomllib.load(stream)["project"]
    name = project.get("name")
    version = project.get("version")
    if name != "proof-goblin" or not isinstance(version, str) or not version:
        raise ValueError(
            "pyproject.toml must identify a versioned proof-goblin project"
        )
    return version


def validate_event(*, event: str, ref: str, release_tag: str, version: str) -> None:
    if event == "workflow_dispatch":
        if ref != "refs/heads/main":
            raise ValueError("TestPyPI publishing must be dispatched from main")
        if release_tag:
            raise ValueError("a manual TestPyPI run must not carry a release tag")
        return

    if event != "release":
        raise ValueError(f"unsupported release event: {event}")
    expected_tag = f"v{version}"
    if release_tag != expected_tag:
        raise ValueError(
            f"release tag {release_tag!r} does not match project version {expected_tag!r}"
        )
    if ref != f"refs/tags/{expected_tag}":
        raise ValueError(f"release ref {ref!r} does not match tag {expected_tag!r}")


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def validate_commit(*, event: str, release_tag: str, commit: str) -> None:
    head = _git("rev-parse", "HEAD")
    if head != commit:
        raise ValueError(
            f"checked-out commit {head} does not match workflow SHA {commit}"
        )
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", head, "origin/main"],
        check=True,
    )
    if event == "release" and _git("rev-list", "-n", "1", release_tag) != head:
        raise ValueError(f"release tag {release_tag!r} does not identify {head}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--release-tag", default="")
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()

    version = read_project_version()
    validate_event(
        event=args.event,
        ref=args.ref,
        release_tag=args.release_tag,
        version=version,
    )
    validate_commit(
        event=args.event,
        release_tag=args.release_tag,
        commit=args.commit,
    )
    print(f"validated protected release source for proof-goblin {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
