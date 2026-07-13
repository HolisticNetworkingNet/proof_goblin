# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Tests for the Proof Goblin command-line interface."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from proof_goblin import ProviderResponse, TokenUsage
from proof_goblin import cli


PACKAGE_ROOT = Path(__file__).parents[1]
EXAMPLE_CONFIG = PACKAGE_ROOT / "examples" / "restaurants.pgcfg"


class FakeProvider:
    """Return a deterministic response without contacting OpenAI."""

    def __init__(self, *, model: str) -> None:
        self.model = model

    def generate(self, prompt, output_schema) -> ProviderResponse:
        return ProviderResponse(
            data={
                "observations": [
                    {
                        "question": "Where are the opening hours?",
                        "evidence": "No opening hours appear in the artifact.",
                    }
                ]
            },
            provider="openai",
            model=self.model,
            response_id="resp_cli_test",
            usage=TokenUsage(input_tokens=50, output_tokens=20, total_tokens=70),
        )


@pytest.fixture
def artifact_path(tmp_path: Path) -> Path:
    path = tmp_path / "homepage.html"
    path.write_text("<main>Welcome</main>", encoding="utf-8")
    return path


def test_prompt_command_prints_assembled_prompt(
    artifact_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "prompt",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("[SYSTEM]\n")
    assert "Artifact name: homepage.html" in captured.out
    assert "Artifact media type: text/html" in captured.out
    assert "<main>Welcome</main>" in captured.out
    assert captured.err == ""


def test_prompt_command_reads_standard_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("# Documentation"))

    exit_code = cli.main(
        [
            "prompt",
            "-",
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--media-type",
            "text/markdown",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Artifact name: stdin" in captured.out
    assert "Artifact media type: text/markdown" in captured.out
    assert "# Documentation" in captured.out


def test_review_command_prints_text_result(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)

    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--model",
            "test-model",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Provider: openai" in captured.out
    assert "Model: test-model" in captured.out
    assert "Response: resp_cli_test" in captured.out
    assert "Observations: 1" in captured.out
    assert "1. Where are the opening hours?" in captured.out


def test_review_command_prints_serialized_json(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)

    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--output",
            "json",
            "--include-prompt",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["format"] == "proof-goblin-review-result"
    assert payload["observations"][0]["question"] == "Where are the opening hours?"
    assert payload["prompt"]["user"].endswith("--- END UNTRUSTED ARTIFACT ---")


def test_review_rejects_prompt_in_text_output(
    artifact_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--include-prompt",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "--include-prompt requires --output json" in captured.err


def test_cli_reports_missing_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.md"

    exit_code = cli.main(
        [
            "prompt",
            str(missing),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "could not read artifact" in captured.err


def test_cli_reports_unknown_review(
    artifact_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli.main(
        [
            "prompt",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "missing_review",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Unknown review" in captured.err
