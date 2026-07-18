from __future__ import annotations

from dataclasses import replace
from io import StringIO
from pathlib import Path

import pytest

from proof_goblin import (
    DEFAULT_INPUT_LIMITS,
    Config,
    InputLimitError,
    InputLimits,
    PromptBuilder,
    PromptMeasurements,
    cli,
)
from proof_goblin.limits import measure_json_utf8_bytes

EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"


def test_json_measurement_counts_compact_utf8_and_rejects_depth() -> None:
    assert measure_json_utf8_bytes(
        {"é": [True, None]},
        limits=DEFAULT_INPUT_LIMITS,
        boundary="decoded value",
    ) == len('{"é":[true,null]}'.encode())

    limits = replace(DEFAULT_INPUT_LIMITS, max_json_depth=2)
    with pytest.raises(InputLimitError, match="3 levels"):
        measure_json_utf8_bytes(
            {"outer": [{"inner": True}]},
            limits=limits,
            boundary="decoded value",
        )


def test_prompt_measurements_count_multibyte_utf8() -> None:
    measured = PromptMeasurements.measure(
        artifact="café",
        system="é",
        user="☃",
    )

    assert measured.artifact_bytes == 5
    assert measured.system_prompt_bytes == 2
    assert measured.user_prompt_bytes == 3
    assert measured.total_prompt_bytes == 5


def test_artifact_accepts_exact_limit_and_rejects_one_byte_over() -> None:
    config = Config.load(EXAMPLE_CONFIG)
    artifact = "éé"
    exact_limits = replace(
        DEFAULT_INPUT_LIMITS,
        max_artifact_bytes=4,
        max_total_artifact_bytes=4,
    )

    prompt = PromptBuilder(config, limits=exact_limits).build(
        review="homepage_first_pass",
        artifact=artifact,
    )

    assert prompt.measurements.artifact_bytes == 4
    with pytest.raises(InputLimitError) as captured:
        PromptBuilder(
            config,
            limits=replace(exact_limits, max_artifact_bytes=3),
        ).build(review="homepage_first_pass", artifact=artifact)
    assert captured.value.boundary == "artifact input"
    assert captured.value.measured == 4
    assert captured.value.limit == 3
    assert artifact not in str(captured.value)


def test_aggregate_artifact_limit_is_independent() -> None:
    limits = replace(
        DEFAULT_INPUT_LIMITS,
        max_artifact_bytes=10,
        max_total_artifact_bytes=3,
    )

    with pytest.raises(InputLimitError, match="aggregate artifact input"):
        PromptBuilder(Config.load(EXAMPLE_CONFIG), limits=limits).build(
            review="homepage_first_pass",
            artifact="four",
        )


def test_system_and_total_prompt_exact_boundaries() -> None:
    config = Config.load(EXAMPLE_CONFIG)
    baseline = PromptBuilder(config).build(
        review="homepage_first_pass",
        artifact="Welcome",
    )
    measured = baseline.measurements
    exact_limits = replace(
        DEFAULT_INPUT_LIMITS,
        max_system_prompt_bytes=measured.system_prompt_bytes,
        max_prompt_bytes=measured.total_prompt_bytes,
    )

    assert (
        PromptBuilder(config, limits=exact_limits)
        .build(review="homepage_first_pass", artifact="Welcome")
        .measurements
        == measured
    )

    with pytest.raises(InputLimitError, match="assembled system prompt"):
        PromptBuilder(
            config,
            limits=replace(
                exact_limits,
                max_system_prompt_bytes=measured.system_prompt_bytes - 1,
            ),
        ).build(review="homepage_first_pass", artifact="Welcome")

    with pytest.raises(InputLimitError, match="total assembled prompt"):
        PromptBuilder(
            config,
            limits=replace(
                exact_limits,
                max_prompt_bytes=measured.total_prompt_bytes - 1,
            ),
        ).build(review="homepage_first_pass", artifact="Welcome")


def test_configuration_accepts_exact_limit_and_rejects_one_byte_over(
    tmp_path: Path,
) -> None:
    content = EXAMPLE_CONFIG.read_bytes()
    path = tmp_path / "review.pgcfg"
    path.write_bytes(content)

    config = Config.load(
        path,
        limits=replace(DEFAULT_INPUT_LIMITS, max_config_bytes=len(content)),
    )

    assert config.name == "restaurants"
    with pytest.raises(InputLimitError) as captured:
        Config.load(
            path,
            limits=replace(
                DEFAULT_INPUT_LIMITS,
                max_config_bytes=len(content) - 1,
            ),
        )
    assert captured.value.boundary == "configuration input"
    assert captured.value.measured == len(content)


def test_cli_stdin_enforces_multibyte_limit_before_prompt_assembly(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("éé"))
    limits = replace(
        DEFAULT_INPUT_LIMITS,
        max_artifact_bytes=3,
        max_total_artifact_bytes=3,
    )

    exit_code = cli.main(
        [
            "prompt",
            "-",
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
        ],
        limits=limits,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "artifact input is 4 UTF-8 bytes; configured limit is 3 bytes" in (
        captured.err
    )
    assert "éé" not in captured.err


def test_cli_rejects_oversized_file_before_cache_or_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    artifact_path = tmp_path / "artifact.txt"
    artifact_path.write_text("four", encoding="utf-8")
    cache_path = tmp_path / "cache"
    provider_constructed = False

    class NeverProvider:
        def __init__(self, *, model: str) -> None:
            nonlocal provider_constructed
            provider_constructed = True

    monkeypatch.setattr(cli, "OpenAIProvider", NeverProvider)
    monkeypatch.setenv("PROOF_GOBLIN_CACHE_DIR", str(cache_path))
    limits = replace(
        DEFAULT_INPUT_LIMITS,
        max_artifact_bytes=3,
        max_total_artifact_bytes=3,
    )

    exit_code = cli.main(
        [
            "review",
            str(artifact_path),
            "--config",
            str(EXAMPLE_CONFIG),
            "--review",
            "homepage_first_pass",
        ],
        limits=limits,
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "artifact input is 4 UTF-8 bytes" in captured.err
    assert provider_constructed is False
    assert not cache_path.exists()


@pytest.mark.parametrize(
    "field",
    [
        "max_config_bytes",
        "max_artifact_bytes",
        "max_total_artifact_bytes",
        "max_system_prompt_bytes",
        "max_prompt_bytes",
    ],
)
@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_limits_require_positive_integers(field: str, value: object) -> None:
    values = {
        "max_config_bytes": 1,
        "max_artifact_bytes": 1,
        "max_total_artifact_bytes": 1,
        "max_system_prompt_bytes": 1,
        "max_prompt_bytes": 1,
    }
    values[field] = value

    with pytest.raises(ValueError, match=field):
        InputLimits(**values)
