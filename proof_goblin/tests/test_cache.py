from __future__ import annotations

import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from proof_goblin import Config, PromptBuilder, ProviderRequest
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


def make_request(prompt, model: str = "model-a") -> ProviderRequest:
    return ProviderRequest(
        provider="openai",
        model=model,
        parameters={
            "model": model,
            "instructions": prompt.system,
            "input": prompt.user,
            "max_output_tokens": 8192,
            "truncation": "disabled",
        },
    )


def test_cache_key_changes_with_model_or_prompt(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()

    baseline = cache.key_for(make_request(prompt))

    assert baseline != cache.key_for(make_request(prompt, "model-b"))
    changed_prompt = PromptBuilder(Config.load(EXAMPLE_CONFIG)).build(
        review="homepage_first_pass",
        artifact="<main>Changed</main>",
        artifact_name="homepage.html",
        artifact_media_type="text/html",
    )
    assert baseline != cache.key_for(make_request(changed_prompt))


def test_cache_key_includes_framed_artifact_metadata(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    builder = PromptBuilder(Config.load(EXAMPLE_CONFIG))
    first = builder.build(
        review="homepage_first_pass",
        artifact="Same content",
        artifact_name="first.txt",
    )
    second = builder.build(
        review="homepage_first_pass",
        artifact="Same content",
        artifact_name="second.txt",
    )

    assert cache.key_for(make_request(first)) != cache.key_for(make_request(second))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("max_output_tokens", 4096),
        ("truncation", "auto"),
        ("text", {"format": {"type": "json_object"}}),
    ],
)
def test_cache_key_includes_every_provider_parameter(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    cache = ReviewCache(tmp_path)
    request = make_request(make_prompt())
    changed_parameters = dict(request.parameters)
    changed_parameters[field] = value
    changed = replace(request, parameters=changed_parameters)

    assert cache.key_for(request) != cache.key_for(changed)


def test_cache_key_rejects_non_json_provider_parameters(tmp_path: Path) -> None:
    request = replace(
        make_request(make_prompt()),
        parameters={"unsupported": object()},
    )

    with pytest.raises(ReviewCacheError, match="JSON-compatible"):
        ReviewCache(tmp_path).key_for(request)


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
def test_cache_key_ignores_provenance_absent_from_provider_request(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()
    baseline = cache.key_for(make_request(prompt))

    changed_prompt = replace(prompt, **{field: value})

    assert baseline == cache.key_for(make_request(changed_prompt))


def test_cache_round_trip(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    request = make_request(result.prompt, result.model)
    key = cache.key_for(request)

    cache.store(
        key,
        result,
        request=request,
    )
    loaded = cache.load(
        key,
        request=request,
        prompt=result.prompt,
    )

    assert loaded is not None
    assert loaded.to_dict() == result.to_dict()


def test_request_equivalent_hit_preserves_original_cached_provenance(
    tmp_path: Path,
) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    request = make_request(result.prompt, result.model)
    key = cache.key_for(request)
    cache.store(key, result, request=request)
    renamed_prompt = replace(result.prompt, config_name="renamed-config")

    loaded = cache.load(key, request=request, prompt=renamed_prompt)

    assert loaded is not None
    assert loaded.prompt.config_name == result.prompt.config_name
    assert loaded.to_dict() == result.to_dict()


@pytest.mark.skipif(
    os.name == "nt",
    reason="Windows does not expose POSIX permission bits",
)
def test_cache_uses_private_posix_permissions(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    request = make_request(result.prompt, result.model)
    key = cache.key_for(request)

    cache.store(
        key,
        result,
        request=request,
    )

    assert (tmp_path / "cache").stat().st_mode & 0o777 == 0o700
    assert (tmp_path / "cache" / f"{key}.json").stat().st_mode & 0o777 == 0o600


def test_cache_distinguishes_requested_model_from_resolved_response_model(
    tmp_path: Path,
) -> None:
    cache = ReviewCache(tmp_path / "cache")
    result = make_result()
    requested_model = "gpt-model-alias"
    request = make_request(result.prompt, requested_model)
    key = cache.key_for(request)

    cache.store(
        key,
        result,
        request=request,
    )
    loaded = cache.load(
        key,
        request=request,
        prompt=result.prompt,
    )

    assert loaded is not None
    assert loaded.model == result.model


def test_invalid_cache_requires_explicit_refresh(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    prompt = make_prompt()
    request = make_request(prompt)
    key = cache.key_for(request)
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{key}.json").write_text("not json", encoding="utf-8")

    with pytest.raises(ReviewCacheError, match="--refresh"):
        cache.load(key, request=request, prompt=prompt)


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
    request = make_request(result.prompt, result.model)
    current_key = cache.key_for(request)

    loaded = cache.load(
        current_key,
        request=request,
        prompt=result.prompt,
    )

    assert loaded is not None
    assert loaded.to_dict() == result.to_dict()


def test_compatible_version_two_cache_entry_remains_reusable(tmp_path: Path) -> None:
    cache = ReviewCache(tmp_path)
    result = make_result()
    version_two_key = cache._version_two_key_for(
        result.prompt,
        provider="openai",
        model=result.model,
    )
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / f"{version_two_key}.json").write_text(
        result.to_json(),
        encoding="utf-8",
    )
    request = make_request(result.prompt, result.model)

    loaded = cache.load(
        cache.key_for(request),
        request=request,
        prompt=result.prompt,
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
    request = make_request(changed_prompt, result.model)
    current_key = cache.key_for(request)

    loaded = cache.load(
        current_key,
        request=request,
        prompt=changed_prompt,
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
    request = make_request(prompt, model)
    current_key = cache.key_for(request)

    with pytest.raises(ReviewCacheError, match="--refresh"):
        cache.load(
            current_key,
            request=request,
            prompt=prompt,
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
