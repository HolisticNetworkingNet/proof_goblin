"""Validate the public contents of built Proof Goblin distributions."""

from __future__ import annotations

import argparse
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

PACKAGE_FILES = {
    "proof_goblin/__init__.py",
    "proof_goblin/__main__.py",
    "proof_goblin/artifacts.py",
    "proof_goblin/builder.py",
    "proof_goblin/cache.py",
    "proof_goblin/cli.py",
    "proof_goblin/config.py",
    "proof_goblin/configs/documentation.pgcfg",
    "proof_goblin/filesystem.py",
    "proof_goblin/limits.py",
    "proof_goblin/observations.py",
    "proof_goblin/prompt_rendering.py",
    "proof_goblin/providers/__init__.py",
    "proof_goblin/providers/base.py",
    "proof_goblin/providers/openai.py",
    "proof_goblin/reports.py",
    "proof_goblin/reviewer.py",
    "proof_goblin/schemas/prompt.v1.schema.json",
    "proof_goblin/schemas/review-result.v1.schema.json",
}
FORBIDDEN_PACKAGE_PREFIXES = (
    "proof_goblin/docs/",
    "proof_goblin/examples/",
    "proof_goblin/tests/",
)
REQUIRED_PROJECT_URL_LABELS = {"Documentation", "Issues", "Release notes", "Source"}
REQUIRED_CLASSIFIERS = {
    "Development Status :: 3 - Alpha",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3 :: Only",
    *(f"Programming Language :: Python :: 3.{minor}" for minor in range(11, 15)),
}


def _one_artifact(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {pattern} artifact in {directory}, found {len(matches)}"
        )
    return matches[0]


def _validate_package_files(names: set[str], artifact: Path) -> None:
    forbidden = sorted(
        name for name in names if name.startswith(FORBIDDEN_PACKAGE_PREFIXES)
    )
    if forbidden:
        raise ValueError(
            f"{artifact.name} contains forbidden package paths: {forbidden}"
        )

    package_files = {name for name in names if name.startswith("proof_goblin/")}
    missing = sorted(PACKAGE_FILES - package_files)
    unexpected = sorted(package_files - PACKAGE_FILES)
    if missing or unexpected:
        raise ValueError(
            f"{artifact.name} package boundary mismatch; "
            f"missing={missing}, unexpected={unexpected}"
        )


def _validate_metadata(raw_metadata: bytes, artifact: Path) -> None:
    metadata = BytesParser().parsebytes(raw_metadata)
    expected_scalars = {
        "Name": "proof-goblin",
        "Version": "0.1.0",
        "Author": "Thomas Belknap",
        "License-Expression": "MIT",
        "Requires-Python": ">=3.11",
    }
    mismatches = {
        key: (metadata.get(key), value)
        for key, value in expected_scalars.items()
        if metadata.get(key) != value
    }
    if mismatches:
        raise ValueError(f"{artifact.name} metadata mismatch: {mismatches}")

    url_labels = {
        value.split(",", 1)[0].strip() for value in metadata.get_all("Project-URL", [])
    }
    missing_urls = REQUIRED_PROJECT_URL_LABELS - url_labels
    if missing_urls:
        raise ValueError(
            f"{artifact.name} is missing project URL labels: {sorted(missing_urls)}"
        )

    classifiers = set(metadata.get_all("Classifier", []))
    missing_classifiers = REQUIRED_CLASSIFIERS - classifiers
    if missing_classifiers:
        raise ValueError(
            f"{artifact.name} is missing classifiers: {sorted(missing_classifiers)}"
        )


def validate_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = {name for name in archive.namelist() if not name.endswith("/")}
        _validate_package_files(names, path)

        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        if len(metadata_names) != 1:
            raise ValueError(f"{path.name} must contain exactly one METADATA file")
        dist_info = metadata_names[0].removesuffix("METADATA")
        required = {
            f"{dist_info}METADATA",
            f"{dist_info}WHEEL",
            f"{dist_info}entry_points.txt",
            f"{dist_info}licenses/LICENSE",
            f"{dist_info}RECORD",
        }
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"{path.name} is missing wheel files: {missing}")

        entry_points = archive.read(f"{dist_info}entry_points.txt").decode("utf-8")
        if "proof-goblin = proof_goblin.cli:main" not in entry_points:
            raise ValueError(
                f"{path.name} does not define the proof-goblin console script"
            )
        _validate_metadata(archive.read(metadata_names[0]), path)


def validate_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        files = {member.name for member in archive.getmembers() if member.isfile()}
        roots = {PurePosixPath(name).parts[0] for name in files}
        if len(roots) != 1:
            raise ValueError(f"{path.name} must contain exactly one root directory")
        root = roots.pop()
        relative = {str(PurePosixPath(name).relative_to(root)) for name in files}
        _validate_package_files(relative, path)

        required = {
            "LICENSE",
            "MANIFEST.in",
            "PKG-INFO",
            "README.md",
            "pyproject.toml",
        }
        missing = sorted(required - relative)
        if missing:
            raise ValueError(f"{path.name} is missing source files: {missing}")
        metadata_member = archive.extractfile(f"{root}/PKG-INFO")
        if metadata_member is None:
            raise ValueError(f"{path.name} PKG-INFO is unreadable")
        _validate_metadata(metadata_member.read(), path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "directory", type=Path, help="directory containing built artifacts"
    )
    args = parser.parse_args()

    wheel = _one_artifact(args.directory, "*.whl")
    sdist = _one_artifact(args.directory, "*.tar.gz")
    validate_wheel(wheel)
    validate_sdist(sdist)
    print(f"validated {wheel.name} and {sdist.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
