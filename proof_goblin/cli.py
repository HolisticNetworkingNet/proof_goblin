# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Command-line interface for Proof Goblin."""

from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path
from typing import Sequence, TextIO

from proof_goblin.builder import PromptBuildError, PromptBuilder
from proof_goblin.config import Config, ConfigError
from proof_goblin.observations import ReviewResult
from proof_goblin.providers import (
    DEFAULT_OPENAI_MODEL,
    OpenAIProvider,
    ProviderError,
)
from proof_goblin.reviewer import ReviewError, Reviewer


class CliError(RuntimeError):
    """Raised when a CLI request cannot be completed."""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Proof Goblin command-line interface."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except (
        CliError,
        ConfigError,
        PromptBuildError,
        ProviderError,
        ReviewError,
    ) as exc:
        print(f"proof-goblin: error: {exc}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proof-goblin",
        description="Review artifacts through reusable Proof Lenses.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prompt_parser = subparsers.add_parser(
        "prompt",
        help="assemble and print a prompt without contacting a provider",
    )
    _add_common_arguments(prompt_parser)
    prompt_parser.set_defaults(handler=_prompt_command)

    review_parser = subparsers.add_parser(
        "review",
        help="review an artifact with OpenAI",
    )
    _add_common_arguments(review_parser)
    review_parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        help=(
            "OpenAI model name (default: OPENAI_MODEL or "
            f"{DEFAULT_OPENAI_MODEL})"
        ),
    )
    review_parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="result output format (default: text)",
    )
    review_parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="include prompt text in JSON output",
    )
    review_parser.set_defaults(handler=_review_command)

    return parser


def _add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "artifact",
        help="UTF-8 artifact path, or - to read from standard input",
    )
    parser.add_argument(
        "-c",
        "--config",
        required=True,
        help="path to a .pgcfg configuration bundle",
    )
    parser.add_argument(
        "-r",
        "--review",
        required=True,
        help="named review from the configuration bundle",
    )
    parser.add_argument(
        "--artifact-name",
        help="artifact name recorded in prompt provenance",
    )
    parser.add_argument(
        "--media-type",
        help="artifact media type (guessed from the filename when omitted)",
    )


def _prompt_command(args: argparse.Namespace) -> int:
    config, artifact, artifact_name, media_type = _load_inputs(args)
    prompt = PromptBuilder(config).build(
        review=args.review,
        artifact=artifact,
        artifact_name=artifact_name,
        artifact_media_type=media_type,
    )
    print(prompt)
    return 0


def _review_command(args: argparse.Namespace) -> int:
    if args.include_prompt and args.output != "json":
        raise CliError("--include-prompt requires --output json")

    config, artifact, artifact_name, media_type = _load_inputs(args)
    result = Reviewer(OpenAIProvider(model=args.model)).review(
        config=config,
        review=args.review,
        artifact=artifact,
        artifact_name=artifact_name,
        artifact_media_type=media_type,
    )

    if args.output == "json":
        print(result.to_json(include_prompt=args.include_prompt))
    else:
        _print_text_result(result, sys.stdout)
    return 0


def _load_inputs(args: argparse.Namespace) -> tuple[Config, str, str, str]:
    config = Config.load(args.config)
    artifact, default_name = _read_artifact(args.artifact)
    artifact_name = args.artifact_name or default_name
    media_type = args.media_type or _guess_media_type(artifact_name)
    return config, artifact, artifact_name, media_type


def _read_artifact(path_value: str) -> tuple[str, str]:
    if path_value == "-":
        try:
            return sys.stdin.read(), "stdin"
        except OSError as exc:
            raise CliError(f"could not read artifact from standard input: {exc}") from exc

    path = Path(path_value)
    try:
        return path.read_text(encoding="utf-8"), path.name
    except (OSError, UnicodeError) as exc:
        raise CliError(f"could not read artifact {path}: {exc}") from exc


def _guess_media_type(artifact_name: str) -> str:
    media_type, _ = mimetypes.guess_type(artifact_name)
    return media_type or "text/plain"


def _print_text_result(result: ReviewResult, stream: TextIO) -> None:
    print(f"Review: {result.review.title}", file=stream)
    print(f"Review ID: {result.review.name}", file=stream)
    print(f"Description: {result.review.description}", file=stream)
    print(f"Lens: {result.review.lens}", file=stream)
    print(f"Mission: {result.review.mission}", file=stream)
    print(f"Provider: {result.provider}", file=stream)
    print(f"Model: {result.model}", file=stream)
    print(f"Response: {result.response_id or '-'}", file=stream)
    print(f"Observations: {len(result.observations)}", file=stream)
    for index, observation in enumerate(result.observations, start=1):
        print(f"\n{index}. {observation.question}", file=stream)
        print(f"   Evidence: {observation.evidence}", file=stream)
