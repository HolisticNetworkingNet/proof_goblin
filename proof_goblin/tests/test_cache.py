# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from proof_goblin import Config, PromptBuilder
from proof_goblin.cache import ReviewCache, ReviewCacheError, STALE_LOCK_AGE
from proof_goblin.tests.test_result_serialization import make_result


EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"


def make_prompt():
    return PromptBuilder(Config.load(EXAMPLE_CONFIG)).build(
        review="homepage_first_pass",
        artifact="<main>Welcome</main>",
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )


def test_cache_key_changes_with_model_or_prompt(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()

    baseline = cache.key_for(prompt, provider="openai", model="model-a")

    assert baseline != cache.key_for(prompt, provider="openai", model="model-b")
    changed_prompt = PromptBuilder(Config.load(EXAMPLE_CONFIG)).build(
        review="homepage_first_pass",
        artifact="<main>Changed</main>",
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )
    assert baseline != cache.key_for(
        changed_prompt,
        provider="openai",
        model="model-a",
    )


def test_cache_round_trip_uses_private_files(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    key = cache.key_for(result.prompt, provider="openai", model=result.model)

    cache.store(key, result)
    loaded = cache.load(
        key,
        prompt=result.prompt,
        provider="openai",
        model=result.model,
    )

    assert loaded is not None
    assert loaded.to_dict() == result.to_dict()
    assert (tmp_path / "cache").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "cache" / f"{key}.json").stat().st_mode & 0o777 == 0o600


def test_invalid_cache_requires_explicit_refresh(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()
    key = cache.key_for(prompt, provider="openai", model="model-a")
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{key}.json").write_text("not json", encoding="utf-8")

    with pytest.raises(ReviewCacheError, match="--refresh"):
        cache.load(key, prompt=prompt, provider="openai", model="model-a")


def test_reservation_blocks_an_identical_concurrent_request(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)

    with cache.reserve("same-key"):
        with pytest.raises(ReviewCacheError, match="already in progress"):
            with cache.reserve("same-key"):
                pass


def test_reservation_replaces_a_stale_lock(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    tmp_path.mkdir(exist_ok=True)
    lock_path = tmp_path / "same-key.lock"
    lock_path.write_text("abandoned", encoding="utf-8")
    stale_time = datetime.now(timezone.utc) - STALE_LOCK_AGE - timedelta(seconds=1)
    os.utime(lock_path, (stale_time.timestamp(), stale_time.timestamp()))

    with cache.reserve("same-key"):
        assert lock_path.exists()

    assert not lock_path.exists()
