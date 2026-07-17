"""Keep the authoritative configuration reference aligned with public controls."""

from dataclasses import fields
from pathlib import Path

from proof_goblin import cli
from proof_goblin.cache import CACHE_DIRECTORY_ENV
from proof_goblin.limits import DEFAULT_INPUT_LIMITS
from proof_goblin.providers import DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_OPENAI_MODEL

CONFIGURATION_DOC = Path(__file__).resolve().parents[1] / "docs" / "configuration.md"


def _configuration_documentation() -> str:
    return CONFIGURATION_DOC.read_text(encoding="utf-8")


def test_configuration_reference_lists_every_cli_option() -> None:
    documentation = _configuration_documentation()
    parser = cli._build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")

    long_options = {
        option
        for command_parser in subparsers.choices.values()
        for action in command_parser._actions
        for option in action.option_strings
        if option.startswith("--") and option != "--help"
    }

    for option in long_options:
        assert f"`{option}" in documentation


def test_configuration_reference_tracks_environment_and_provider_defaults() -> None:
    documentation = _configuration_documentation()

    assert "`OPENAI_API_KEY`" in documentation
    assert f"`{CACHE_DIRECTORY_ENV}`" in documentation
    assert "`OPENAI_MODEL`" in documentation
    assert f"`{DEFAULT_OPENAI_MODEL}`" in documentation
    assert f"{DEFAULT_MAX_OUTPUT_TOKENS:,}" in documentation


def test_configuration_reference_tracks_input_limit_fields_and_defaults() -> None:
    documentation = _configuration_documentation()

    for limit_field in fields(DEFAULT_INPUT_LIMITS):
        assert f"`{limit_field.name}`" in documentation
        assert f"{getattr(DEFAULT_INPUT_LIMITS, limit_field.name):,}" in documentation
