# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Tests for the Proof Goblin command-line interface."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest

from proof_goblin import ProviderResponse, TokenUsage, cli

PACKAGE_ROOT = Path(__file__).parents[1]
EXAMPLE_CONFIG = PACKAGE_ROOT / "examples" / "restaurants.pgcfg"


class FakeProvider:
    """Return a deterministic response without contacting OpenAI."""

    calls = 0
    response_model: str | None = None

    def __init__(self, *, model: str) -> None:
        self.model = model

    def generate(self, prompt, output_schema) -> ProviderResponse:
        type(self).calls += 1
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
            model=self.response_model or self.model,
            response_id="resp_cli_test",
            usage=TokenUsage(input_tokens=50, output_tokens=20, total_tokens=70),
        )


@pytest.fixture
def artifact_path(tmp_path: Path) -> Path:
    path = tmp_path / "homepage.html"
    path.write_text("<main>Welcome</main>", encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def isolated_review_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROOF_GOBLIN_CACHE_DIR", str(tmp_path / "cache"))
    FakeProvider.calls = 0
    FakeProvider.response_model = None


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


def test_prompt_command_prints_versioned_json(
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
            "--format",
            "json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert captured.err == ""
    assert payload["format"] == "proof-goblin-prompt"
    assert payload["review"]["name"] == "homepage_first_pass"
    assert payload["prompt"]["user"].endswith("--- END UNTRUSTED ARTIFACT ---")


def test_prompt_writes_multiple_formats_without_provider_execution(
    artifact_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    markdown_path = artifact_path.with_name("prompt.md")
    html_path = artifact_path.with_name("prompt.html")
    json_path = artifact_path.with_name("prompt.json")

    exit_code = cli.main(
        [
            "prompt",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--output",
            str(markdown_path),
            "--output",
            str(html_path),
            "--output",
            str(json_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert FakeProvider.calls == 0
    assert markdown_path.read_text(encoding="utf-8").startswith("# Proof Goblin Prompt")
    assert html_path.read_text(encoding="utf-8").startswith("<!doctype html>")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["artifact"]["name"] == "homepage.html"


def test_prompt_rejects_format_with_file_output(
    artifact_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = artifact_path.with_name("prompt.md")

    exit_code = cli.main(
        [
            "prompt",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--format",
            "html",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "--format cannot be combined with --output" in captured.err
    assert not output_path.exists()


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
    assert captured.out.startswith("Restaurant Homepage Review\n")
    assert "Review ID: homepage_first_pass" in captured.out
    assert "Evaluates whether a first-time diner" in captured.out
    assert "Proof Lens: first_time_diner" in captured.out
    assert "Mission: homepage_clarity" in captured.out
    assert "Artifact: homepage.html" in captured.out
    assert "Configuration: restaurants" in captured.out
    assert "Created:" in captured.out
    assert "Provider: openai" in captured.out
    assert "Model: test-model" in captured.out
    assert "Response ID: resp_cli_test" in captured.out
    assert "Input tokens: 50" in captured.out
    assert "Output tokens: 20" in captured.out
    assert "Total tokens: 70" in captured.out
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
            "--format",
            "json",
            "--include-prompt",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["format"] == "proof-goblin-review-result"
    assert payload["review"]["title"] == "Restaurant Homepage Review"
    assert payload["review"]["lens"] == "first_time_diner"
    assert payload["review"]["mission"] == "homepage_clarity"
    assert payload["review"]["protocol"] == "questions_only"
    assert payload["review"]["output_schema"] == "observation.v1"
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
    assert "--include-prompt requires JSON output" in captured.err


def test_review_command_writes_inferred_markdown_file(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)
    output_path = artifact_path.with_name("review.md")

    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--artifact-name",
            "café-homepage.html",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    rendered = output_path.read_text(encoding="utf-8")
    assert rendered.startswith("# Restaurant Homepage Review\n")
    assert "`café-homepage.html`" in rendered
    assert "### Observation 1" in rendered


def test_review_rejects_format_with_file_output(
    artifact_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = artifact_path.with_name("review.md")

    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--format",
            "html",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "--format cannot be combined with --output" in captured.err
    assert not output_path.exists()


def test_review_writes_multiple_formats_from_one_provider_response(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)
    markdown_path = artifact_path.with_name("review.md")
    html_path = artifact_path.with_name("review.html")
    json_path = artifact_path.with_name("review.json")

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
            "--output",
            str(markdown_path),
            "--output",
            str(html_path),
            "--output",
            str(json_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert FakeProvider.calls == 1
    assert markdown_path.read_text(encoding="utf-8").startswith("# Restaurant")
    assert html_path.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert (
        json.loads(json_path.read_text(encoding="utf-8"))["execution"]["response_id"]
        == "resp_cli_test"
    )


def test_review_reuses_cached_result_for_later_format(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)
    markdown_path = artifact_path.with_name("review.md")
    html_path = artifact_path.with_name("review.html")
    common_arguments = [
        "review",
        str(artifact_path),
        "--config",
        str(EXAMPLE_CONFIG),
        "--review",
        "homepage_first_pass",
        "--model",
        "test-model",
    ]

    assert cli.main([*common_arguments, "--output", str(markdown_path)]) == 0
    assert cli.main([*common_arguments, "--output", str(html_path)]) == 0

    assert FakeProvider.calls == 1
    assert "resp_cli_test" in markdown_path.read_text(encoding="utf-8")
    assert "resp_cli_test" in html_path.read_text(encoding="utf-8")


def test_review_caches_resolved_provider_model_under_requested_model(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)
    FakeProvider.response_model = "test-model-2026-07-14"
    output_path = artifact_path.with_name("review.txt")
    arguments = [
        "review",
        str(artifact_path),
        "--config",
        str(EXAMPLE_CONFIG),
        "--review",
        "homepage_first_pass",
        "--model",
        "test-model",
        "--output",
        str(output_path),
    ]

    assert cli.main(arguments) == 0
    assert cli.main(arguments) == 0

    assert FakeProvider.calls == 1
    assert "Model: test-model-2026-07-14" in output_path.read_text(encoding="utf-8")


def test_refresh_replaces_matching_cached_result(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)
    output_path = artifact_path.with_name("review.txt")
    arguments = [
        "review",
        str(artifact_path),
        "--config",
        str(EXAMPLE_CONFIG),
        "--review",
        "homepage_first_pass",
        "--model",
        "test-model",
        "--output",
        str(output_path),
    ]

    assert cli.main(arguments) == 0
    assert cli.main([*arguments, "--refresh"]) == 0

    assert FakeProvider.calls == 2


def test_cached_result_excludes_prompt_and_artifact_body(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)

    assert (
        cli.main(
            [
                "review",
                str(artifact_path),
                "--config",
                str(EXAMPLE_CONFIG),
                "--review",
                "homepage_first_pass",
            ]
        )
        == 0
    )

    cache_files = list((tmp_path / "cache").glob("*.json"))
    assert len(cache_files) == 1
    cached_text = cache_files[0].read_text(encoding="utf-8")
    assert '"prompt"' not in cached_text
    assert "<main>Welcome</main>" not in cached_text


def test_review_rejects_unknown_output_extension_before_execution(
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
            "--output",
            str(artifact_path.with_name("review.report")),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "unsupported output extension '.report'" in captured.err
    assert "use one of: .txt, .text, .json, .md" in captured.err
    assert "--format" not in captured.err


@pytest.mark.parametrize(
    ("extension", "expected"),
    [
        (".txt", cli.ReportFormat.TEXT),
        (".text", cli.ReportFormat.TEXT),
        (".json", cli.ReportFormat.JSON),
        (".md", cli.ReportFormat.MARKDOWN),
        (".markdown", cli.ReportFormat.MARKDOWN),
        (".html", cli.ReportFormat.HTML),
        (".htm", cli.ReportFormat.HTML),
    ],
)
def test_report_format_is_inferred_from_recognized_extension(
    extension: str,
    expected: cli.ReportFormat,
) -> None:
    assert cli._resolve_report_format(None, f"review{extension}") is expected


@pytest.mark.parametrize(
    ("extension", "expected"),
    [
        (".txt", cli.PromptFormat.TEXT),
        (".text", cli.PromptFormat.TEXT),
        (".json", cli.PromptFormat.JSON),
        (".md", cli.PromptFormat.MARKDOWN),
        (".markdown", cli.PromptFormat.MARKDOWN),
        (".html", cli.PromptFormat.HTML),
        (".htm", cli.PromptFormat.HTML),
    ],
)
def test_prompt_format_is_inferred_from_recognized_extension(
    extension: str,
    expected: cli.PromptFormat,
) -> None:
    assert cli._resolve_prompt_format(None, f"prompt{extension}") is expected


def test_failed_atomic_write_preserves_existing_report(
    artifact_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "OpenAIProvider", FakeProvider)
    output_path = artifact_path.with_name("review.txt")
    output_path.write_text("existing report\n", encoding="utf-8")

    def fail_replace(source: object, destination: object) -> None:
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(cli.os, "replace", fail_replace)

    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
            "--output",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "could not write report" in captured.err
    assert output_path.read_text(encoding="utf-8") == "existing report\n"
    assert not list(output_path.parent.glob(f".{output_path.name}.*.tmp"))


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
