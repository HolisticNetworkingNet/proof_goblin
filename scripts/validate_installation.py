"""Install and smoke-test built distributions in separate clean environments."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def _one_artifact(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one {pattern} artifact in {directory}, found {len(matches)}"
        )
    return matches[0].resolve()


def _python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _run(*command: str | Path) -> None:
    subprocess.run([str(part) for part in command], check=True)


def _validate_install(
    *,
    artifact: Path,
    environment: Path,
    smoke_script: Path,
    openai: bool,
) -> None:
    venv.EnvBuilder(with_pip=True).create(environment)
    python = _python(environment)
    install_target = f"{artifact}[openai]" if openai else artifact
    _run(python, "-m", "pip", "install", install_target)
    _run(python, "-m", "pip", "check")
    _run(python, "-m", "proof_goblin", "--help")
    smoke_command: list[str | Path] = [python, smoke_script]
    if openai:
        smoke_command.append("--openai")
    _run(*smoke_command)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "directory", type=Path, help="directory containing built artifacts"
    )
    args = parser.parse_args()

    wheel = _one_artifact(args.directory, "*.whl")
    sdist = _one_artifact(args.directory, "*.tar.gz")
    smoke_script = Path(__file__).with_name("smoke_test_install.py").resolve()

    with tempfile.TemporaryDirectory(prefix="proof-goblin-release-") as temporary:
        root = Path(temporary)
        _validate_install(
            artifact=wheel,
            environment=root / "wheel",
            smoke_script=smoke_script,
            openai=True,
        )
        _validate_install(
            artifact=sdist,
            environment=root / "sdist",
            smoke_script=smoke_script,
            openai=False,
        )

    print("wheel, OpenAI extra, and source distribution installations validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
