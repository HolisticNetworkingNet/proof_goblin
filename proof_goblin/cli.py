"""Command-line interface for Proof Goblin."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

from proof_goblin.artifacts import (
    ArtifactMediaTypeError,
    resolve_artifact_media_type,
)
from proof_goblin.builder import PromptBuilder, PromptBuildError
from proof_goblin.cache import ReviewCache, ReviewCacheError
from proof_goblin.config import Config, ConfigError
from proof_goblin.limits import (
    DEFAULT_INPUT_LIMITS,
    InputLimitError,
    InputLimits,
)
from proof_goblin.prompt_rendering import (
    PromptFormat,
    PromptRenderError,
    render_prompt,
)
from proof_goblin.providers import (
    DEFAULT_OPENAI_MODEL,
    OpenAIProvider,
    ProviderError,
)
from proof_goblin.reports import (
    ReportFormat,
    ReportRenderError,
    render_report,
)
from proof_goblin.reviewer import Reviewer, ReviewError


class CliError(RuntimeError):
    """Raised when a CLI request cannot be completed."""


def main(
    argv: Sequence[str] | None = None,
    *,
    limits: InputLimits = DEFAULT_INPUT_LIMITS,
) -> int:
    """Run the Proof Goblin command-line interface."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    args.input_limits = limits

    try:
        return args.handler(args)
    except (
        CliError,
        ArtifactMediaTypeError,
        ConfigError,
        InputLimitError,
        PromptBuildError,
        PromptRenderError,
        ProviderError,
        ReviewCacheError,
        ReportRenderError,
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
    prompt_parser.add_argument(
        "--format",
        choices=tuple(item.value for item in PromptFormat),
        help=(
            "standard output format (default: text; file formats are inferred "
            "from --output extensions)"
        ),
    )
    prompt_parser.add_argument(
        "-o",
        "--output",
        action="append",
        metavar="PATH",
        help="write an assembled prompt inferred from PATH; may be repeated",
    )
    prompt_parser.set_defaults(handler=_prompt_command)

    review_parser = subparsers.add_parser(
        "review",
        help="review an artifact with OpenAI",
    )
    _add_common_arguments(review_parser)
    review_parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        help=(f"OpenAI model name (default: OPENAI_MODEL or {DEFAULT_OPENAI_MODEL})"),
    )
    review_parser.add_argument(
        "--format",
        choices=tuple(item.value for item in ReportFormat),
        help=(
            "standard output format (default: text; file formats are inferred "
            "from --output extensions)"
        ),
    )
    review_parser.add_argument(
        "-o",
        "--output",
        action="append",
        metavar="PATH",
        help="write a report inferred from PATH; may be repeated",
    )
    review_parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="include prompt text in JSON output",
    )
    refresh_group = review_parser.add_mutually_exclusive_group()
    refresh_group.add_argument(
        "--refresh",
        action="store_true",
        help="confirm before replacing a matching cached result",
    )
    refresh_group.add_argument(
        "--force-refresh",
        action="store_true",
        help="replace a matching cached result without prompting",
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
        help="explicit textual media type (inferred from the name when omitted)",
    )


def _prompt_command(args: argparse.Namespace) -> int:
    outputs = _resolve_prompt_outputs(args.format, args.output)
    config, artifact, artifact_name, media_type = _load_inputs(
        args,
        limits=args.input_limits,
    )
    prompt = PromptBuilder(config, limits=args.input_limits).build(
        review=args.review,
        artifact=artifact,
        artifact_name=artifact_name,
        artifact_media_type=media_type,
    )
    rendered_outputs = [
        (path, render_prompt(prompt, prompt_format)) for path, prompt_format in outputs
    ]
    for path, rendered in rendered_outputs:
        if path is None:
            sys.stdout.write(rendered)
        else:
            _write_output(path, rendered, noun="prompt")
    return 0


def _review_command(args: argparse.Namespace) -> int:
    outputs = _resolve_outputs(args.format, args.output)
    if args.include_prompt and not any(
        report_format is ReportFormat.JSON for _, report_format in outputs
    ):
        raise CliError("--include-prompt requires JSON output")

    config, artifact, artifact_name, media_type = _load_inputs(
        args,
        limits=args.input_limits,
    )
    reviewer = Reviewer(
        OpenAIProvider(model=args.model),
        limits=args.input_limits,
    )
    prepared = reviewer.prepare(
        config=config,
        review=args.review,
        artifact=artifact,
        artifact_name=artifact_name,
        artifact_media_type=media_type,
    )
    prompt = prepared.prompt
    cache = ReviewCache()
    cache_key = cache.key_for(prepared.request)
    refresh_requested = args.refresh or args.force_refresh
    current_entry_exists = cache.has_entry(cache_key)
    cached = cache.load(
        cache_key,
        request=prepared.request,
        prompt=prompt,
        invalid_as_miss=refresh_requested,
    )
    replace_cached = args.force_refresh
    result = cached
    if args.refresh and (cached is not None or current_entry_exists):
        replace_cached = _confirm_refresh(args.artifact)
        if replace_cached:
            result = None
        elif cached is None:
            raise CliError("the matching cached result is invalid and was not replaced")
    elif cached is not None and args.force_refresh:
        result = None

    if result is None:
        with cache.reserve(cache_key):
            latest = cache.load(
                cache_key,
                request=prepared.request,
                prompt=prompt,
                invalid_as_miss=refresh_requested,
            )
            if latest is not None and not refresh_requested:
                result = latest
            else:
                result = reviewer.review_prepared(prepared)
                cache.store(
                    cache_key,
                    result,
                    request=prepared.request,
                )

    rendered_outputs = [
        (
            path,
            render_report(
                result,
                report_format,
                include_prompt=(
                    args.include_prompt and report_format is ReportFormat.JSON
                ),
            ),
        )
        for path, report_format in outputs
    ]
    for path, rendered in rendered_outputs:
        if path is None:
            sys.stdout.write(rendered)
        else:
            _write_output(path, rendered, noun="report")
    return 0


def _confirm_refresh(artifact_path: str) -> bool:
    if artifact_path == "-" or not sys.stdin.isatty():
        raise CliError(
            "--refresh needs an interactive terminal when a cached result exists; "
            "use --force-refresh for noninteractive replacement"
        )
    sys.stderr.write(
        "A matching cached review exists. Contact the provider and replace it? [y/N] "
    )
    sys.stderr.flush()
    answer = sys.stdin.readline()
    return answer.strip().lower() in {"y", "yes"}


def _load_inputs(
    args: argparse.Namespace,
    *,
    limits: InputLimits = DEFAULT_INPUT_LIMITS,
) -> tuple[Config, str, str, str]:
    config = Config.load(args.config, limits=limits)
    artifact, default_name = _read_artifact(args.artifact, limits=limits)
    artifact_name = args.artifact_name or default_name
    media_type = resolve_artifact_media_type(artifact_name, args.media_type)
    return config, artifact, artifact_name, media_type


def _read_artifact(
    path_value: str,
    *,
    limits: InputLimits = DEFAULT_INPUT_LIMITS,
) -> tuple[str, str]:
    if path_value == "-":
        try:
            return _read_limited_stdin(limits), "stdin"
        except (OSError, UnicodeError) as exc:
            raise CliError(
                f"could not read artifact from standard input: {exc}"
            ) from exc

    path = Path(path_value)
    try:
        size = path.stat().st_size
        limits.enforce_artifact(size)
        with path.open("rb") as stream:
            content = stream.read(limits.max_artifact_bytes + 1)
        limits.enforce_artifact(len(content))
        return content.decode("utf-8"), path.name
    except (OSError, UnicodeError) as exc:
        raise CliError(f"could not read artifact {path}: {exc}") from exc


def _read_limited_stdin(limits: InputLimits) -> str:
    chunks: list[str] = []
    measured = 0
    while chunk := sys.stdin.read(8192):
        measured += len(chunk.encode("utf-8"))
        limits.enforce_artifact(measured)
        chunks.append(chunk)
    return "".join(chunks)


_FORMAT_EXTENSIONS = {
    ".txt": ReportFormat.TEXT,
    ".text": ReportFormat.TEXT,
    ".json": ReportFormat.JSON,
    ".md": ReportFormat.MARKDOWN,
    ".markdown": ReportFormat.MARKDOWN,
    ".html": ReportFormat.HTML,
    ".htm": ReportFormat.HTML,
}

_PROMPT_FORMAT_EXTENSIONS = {
    ".txt": PromptFormat.TEXT,
    ".text": PromptFormat.TEXT,
    ".json": PromptFormat.JSON,
    ".md": PromptFormat.MARKDOWN,
    ".markdown": PromptFormat.MARKDOWN,
    ".html": PromptFormat.HTML,
    ".htm": PromptFormat.HTML,
}


def _resolve_prompt_format(
    format_value: str | None,
    output_value: str | None,
) -> PromptFormat:
    if format_value:
        return PromptFormat(format_value)
    if not output_value:
        return PromptFormat.TEXT
    suffix = Path(output_value).suffix.lower()
    try:
        return _PROMPT_FORMAT_EXTENSIONS[suffix]
    except KeyError as exc:
        supported_extensions = ", ".join(_PROMPT_FORMAT_EXTENSIONS)
        raise CliError(
            f"unsupported output extension {suffix!r} in {output_value!r}; "
            f"use one of: {supported_extensions}"
        ) from exc


def _resolve_report_format(
    format_value: str | None,
    output_value: str | None,
) -> ReportFormat:
    if format_value:
        return ReportFormat(format_value)
    if not output_value:
        return ReportFormat.TEXT
    suffix = Path(output_value).suffix.lower()
    try:
        return _FORMAT_EXTENSIONS[suffix]
    except KeyError as exc:
        supported_extensions = ", ".join(_FORMAT_EXTENSIONS)
        raise CliError(
            f"unsupported output extension {suffix!r} in {output_value!r}; "
            f"use one of: {supported_extensions}"
        ) from exc


def _resolve_outputs(
    format_value: str | None,
    output_values: list[str] | None,
) -> tuple[tuple[Path | None, ReportFormat], ...]:
    if not output_values:
        return ((None, _resolve_report_format(format_value, None)),)
    if format_value:
        raise CliError("--format cannot be combined with --output; use file extensions")

    paths = tuple(Path(value) for value in output_values)
    if len(set(paths)) != len(paths):
        raise CliError("each --output path must be unique")
    return tuple((path, _resolve_report_format(None, str(path))) for path in paths)


def _resolve_prompt_outputs(
    format_value: str | None,
    output_values: list[str] | None,
) -> tuple[tuple[Path | None, PromptFormat], ...]:
    if not output_values:
        return ((None, _resolve_prompt_format(format_value, None)),)
    if format_value:
        raise CliError("--format cannot be combined with --output; use file extensions")

    paths = tuple(Path(value) for value in output_values)
    if len(set(paths)) != len(paths):
        raise CliError("each --output path must be unique")
    return tuple((path, _resolve_prompt_format(None, str(path))) for path in paths)


def _write_output(path: Path, content: str, *, noun: str) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        assert temporary_path is not None
        if path.exists():
            temporary_path.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary_path, path)
    except (OSError, UnicodeError) as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise CliError(f"could not write {noun} to {path}: {exc}") from exc
