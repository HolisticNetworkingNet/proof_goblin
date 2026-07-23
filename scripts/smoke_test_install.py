"""Exercise an installed distribution without making a provider request."""

from __future__ import annotations

import argparse
import os
from importlib.metadata import version
from importlib.resources import as_file, files

from proof_goblin import Config, OpenAIProvider, PromptBuilder


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openai",
        action="store_true",
        help="also initialize the optional OpenAI SDK without making a request",
    )
    args = parser.parse_args()

    assert version("proof-goblin") == "0.1.0"
    package = files("proof_goblin")
    for relative_path in (
        "configs/documentation.pgcfg",
        "schemas/prompt.v1.schema.json",
        "schemas/review-result.v1.schema.json",
    ):
        assert package.joinpath(relative_path).is_file(), relative_path

    bundle = package.joinpath("configs/documentation.pgcfg")
    with as_file(bundle) as config_path:
        config = Config.load(config_path)
    prompt = PromptBuilder(config).build(
        review="technical_writer_first_pass",
        artifact="# Public preview\n\nCheck this short document.",
        artifact_name="preview.md",
    )
    assert prompt.review_name == "technical_writer_first_pass"
    assert prompt.artifact_media_type == "text/markdown"

    if args.openai:
        os.environ.setdefault("OPENAI_API_KEY", "release-smoke-test-not-a-real-key")
        provider = OpenAIProvider()
        assert provider.client is not None

    print(f"proof-goblin {version('proof-goblin')} installed smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
