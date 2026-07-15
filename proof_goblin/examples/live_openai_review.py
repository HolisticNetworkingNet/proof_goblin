"""Run the restaurant example against OpenAI for a manual smoke test."""

from __future__ import annotations

import os
from pathlib import Path

from proof_goblin import Config, OpenAIProvider, ProviderError, Reviewer

EXAMPLES = Path(__file__).parent


def main() -> None:
    """Run and print a live homepage review."""

    config = Config.load(EXAMPLES / "restaurants.pgcfg")
    artifact = (EXAMPLES / "homepage.html").read_text()
    provider = OpenAIProvider(model=os.getenv("OPENAI_MODEL", "gpt-5.6"))
    result = Reviewer(provider).review(
        config=config,
        review="homepage_first_pass",
        artifact=artifact,
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )

    print(f"Provider: {result.provider}")
    print(f"Model: {result.model}")
    print(f"Response: {result.response_id}")
    print(f"Observations: {len(result.observations)}")
    for index, observation in enumerate(result.observations, start=1):
        print(f"\n{index}. {observation.question}")
        print(f"   Evidence: {observation.evidence}")


if __name__ == "__main__":
    try:
        main()
    except ProviderError as exc:
        raise SystemExit(f"Review failed: {exc}") from None
