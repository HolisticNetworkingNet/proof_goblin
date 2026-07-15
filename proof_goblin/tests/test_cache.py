# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from proof_goblin import Config, PromptBuilder
from proof_goblin.cache import STALE_LOCK_AGE, ReviewCache, ReviewCacheError
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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("review_name", "different_review"),
        ("config_name", "different_config"),
        ("config_version", "2.0.0"),
        ("config_sha256", "0" * 64),
        ("artifact_name", "different.md"),
        ("artifact_media_type", "text/plain"),
        ("artifact_sha256", "0" * 64),
    ],
)
def test_cache_key_includes_prompt_provenance(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()
    baseline = cache.key_for(prompt, provider="openai", model="model-a")

    changed_prompt = replace(prompt, **{field: value})

    assert baseline != cache.key_for(
        changed_prompt,
        provider="openai",
        model="model-a",
    )


def test_cache_round_trip(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    key = cache.key_for(result.prompt, provider="openai", model=result.model)

    cache.store(
        key,
        result,
        request_provider="openai",
        request_model=result.model,
    )
    loaded = cache.load(
        key,
        prompt=result.prompt,
        provider="openai",
        model=result.model,
    )

    assert loaded is not None
    assert loaded.to_dict() == result.to_dict()


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows does not expose POSIX permission bits",
)
def test_cache_uses_private_posix_permissions(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    key = cache.key_for(result.prompt, provider="openai", model=result.model)

    cache.store(
        key,
        result,
        request_provider="openai",
        request_model=result.model,
    )

    assert (tmp_path / "cache").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "cache" / f"{key}.json").stat().st_mode & 0o777 == 0o600


def test_cache_distinguishes_requested_model_from_resolved_response_model(
    tmp_path: Path,
) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    requested_model = "gpt-model-alias"
    key = cache.key_for(
        result.prompt,
        provider="openai",
        model=requested_model,
    )

    cache.store(
        key,
        result,
        request_provider="openai",
        request_model=requested_model,
    )
    loaded = cache.load(
        key,
        prompt=result.prompt,
        provider="openai",
        model=requested_model,
    )

    assert loaded is not None
    assert loaded.model == result.model


def test_invalid_cache_requires_explicit_refresh(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()
    key = cache.key_for(prompt, provider="openai", model="model-a")
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{key}.json").write_text("not json", encoding="utf-8")

    with pytest.raises(ReviewCacheError, match="--refresh"):
        cache.load(key, prompt=prompt, provider="openai", model="model-a")


def test_compatible_version_one_cache_entry_remains_reusable(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    result = make_result()
    legacy_key = cache._legacy_key_for(
        result.prompt,
        provider="openai",
        model=result.model,
    )
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{legacy_key}.json").write_text(
        result.to_json(),
        encoding="utf-8",
    )
    current_key = cache.key_for(
        result.prompt,
        provider="openai",
        model=result.model,
    )

    loaded = cache.load(
        current_key,
        prompt=result.prompt,
        provider="openai",
        model=result.model,
    )

    assert loaded is not None
    assert loaded.to_dict() == result.to_dict()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("config_name", "different_config"),
        ("review_name", "different_review"),
    ],
)
def test_colliding_version_one_provenance_is_treated_as_cache_miss(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    cache = ReviewCache(tmp_path)
    result = make_result()
    legacy_key = cache._legacy_key_for(
        result.prompt,
        provider="openai",
        model=result.model,
    )
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{legacy_key}.json").write_text(
        result.to_json(),
        encoding="utf-8",
    )
    changed_prompt = replace(result.prompt, **{field: value})
    current_key = cache.key_for(
        changed_prompt,
        provider="openai",
        model=result.model,
    )

    loaded = cache.load(
        current_key,
        prompt=changed_prompt,
        provider="openai",
        model=result.model,
    )

    assert loaded is None


def test_corrupt_version_one_cache_entry_requires_explicit_refresh(
    tmp_path: Path,
) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()
    model = "model-a"
    legacy_key = cache._legacy_key_for(
        prompt,
        provider="openai",
        model=model,
    )
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{legacy_key}.json").write_text("not json", encoding="utf-8")
    current_key = cache.key_for(prompt, provider="openai", model=model)

    with pytest.raises(ReviewCacheError, match="--refresh"):
        cache.load(
            current_key,
            prompt=prompt,
            provider="openai",
            model=model,
        )


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
    stale_time = datetime.now(UTC) - STALE_LOCK_AGE - timedelta(seconds=1)
    os.utime(lock_path, (stale_time.timestamp(), stale_time.timestamp()))

    with cache.reserve("same-key"):
        assert lock_path.exists()

    assert not lock_path.exists()
