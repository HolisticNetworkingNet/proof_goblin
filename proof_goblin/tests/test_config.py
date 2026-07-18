from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

import pytest

from proof_goblin import (
    DEFAULT_INPUT_LIMITS,
    ComponentNotFoundError,
    Config,
    ConfigParseError,
    ConfigValidationError,
    InputLimitError,
)


def test_from_mapping_bounds_canonical_json_before_validation() -> None:
    data = valid_config()
    limits = replace(DEFAULT_INPUT_LIMITS, max_config_bytes=20)

    with pytest.raises(InputLimitError, match="configuration input"):
        Config.from_mapping(data, limits=limits)


EXAMPLE_CONFIG = Path(__file__).parents[1] / "examples" / "restaurants.pgcfg"


def valid_config() -> dict[str, object]:
    return {
        "format": "proof-goblin-config",
        "schema_version": "1.0",
        "name": "test",
        "version": "0.1.0",
        "lenses": {"reader": {"description": "A reader-centered perspective."}},
        "missions": {"clarity": {"questions": ["What is unclear?"]}},
        "protocols": {"questions_only": {"ask_questions": True}},
        "output_schemas": {"observation.v1": {"type": "array"}},
        "reviews": {
            "first_pass": {
                "title": "Reader Clarity Review",
                "description": "Evaluates whether the artifact is clear to a reader.",
                "lens": "reader",
                "mission": "clarity",
                "protocol": "questions_only",
                "output_schema": "observation.v1",
            }
        },
    }


def test_loads_example_bundle_with_provenance() -> None:
    config = Config.load(EXAMPLE_CONFIG)

    assert config.name == "restaurants"
    assert config.version == "0.2.0"
    assert config.source_path == EXAMPLE_CONFIG.resolve()
    assert config.sha256 == hashlib.sha256(EXAMPLE_CONFIG.read_bytes()).hexdigest()
    assert config.lens("first_time_diner")["goals"]
    assert config.review("homepage_first_pass").mission == "homepage_clarity"
    assert config.review("homepage_first_pass").title == "Restaurant Homepage Review"
    assert config.review("homepage_first_pass").description.startswith("Evaluates")
    assert config.metadata["description"].startswith("Reusable review definitions")


@pytest.mark.skipif(os.name == "nt", reason="symlink creation requires privileges")
def test_load_follows_one_resolved_configuration_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.pgcfg"
    selected = tmp_path / "selected.pgcfg"
    target.write_text(json.dumps(valid_config()), encoding="utf-8")
    selected.symlink_to(target)

    config = Config.load(selected)

    assert config.name == "test"
    assert config.source_path == target.resolve()
    assert config.sha256 == hashlib.sha256(target.read_bytes()).hexdigest()


def test_rejects_non_pgcfg_extension(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(valid_config()))

    with pytest.raises(ConfigValidationError, match=r"\.pgcfg extension"):
        Config.load(path)


def test_reports_invalid_json_location(tmp_path: Path) -> None:
    path = tmp_path / "broken.pgcfg"
    path.write_text('{"format": }')

    with pytest.raises(ConfigParseError, match=r"line 1, column 12"):
        Config.load(path)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("format", "something-else", "configuration.format"),
        ("schema_version", "2.0", "Unsupported schema_version"),
        ("name", "", "configuration.name"),
        ("lenses", [], "lenses must be a JSON object"),
    ],
)
def test_rejects_invalid_top_level_values(
    key: str, value: object, message: str
) -> None:
    data = valid_config()
    data[key] = value

    with pytest.raises(ConfigValidationError, match=message):
        Config.from_mapping(data)


def test_rejects_unknown_review_reference() -> None:
    data = valid_config()
    reviews = data["reviews"]
    assert isinstance(reviews, dict)
    review = reviews["first_pass"]
    assert isinstance(review, dict)
    review["lens"] = "missing"

    with pytest.raises(
        ConfigValidationError,
        match="reviews.first_pass.lens references unknown lens 'missing'",
    ):
        Config.from_mapping(data)


@pytest.mark.parametrize("field", ["title", "description"])
@pytest.mark.parametrize("value", [None, "", "  "])
def test_rejects_missing_or_empty_review_presentation_metadata(
    field: str, value: object
) -> None:
    data = valid_config()
    reviews = data["reviews"]
    assert isinstance(reviews, dict)
    review = reviews["first_pass"]
    assert isinstance(review, dict)
    if value is None:
        review.pop(field)
    else:
        review[field] = value

    with pytest.raises(
        ConfigValidationError,
        match=rf"reviews\.first_pass\.{field} must be a non-empty string",
    ):
        Config.from_mapping(data)


def test_named_accessor_reports_missing_component() -> None:
    config = Config.from_mapping(valid_config())

    with pytest.raises(ComponentNotFoundError, match="Unknown lens 'missing'"):
        config.lens("missing")


def test_config_detaches_and_freezes_nested_input_state() -> None:
    data = valid_config()
    data["metadata"] = {"owners": ["original"]}
    reviews = data["reviews"]
    lenses = data["lenses"]
    assert isinstance(reviews, dict)
    assert isinstance(lenses, dict)
    review = reviews["first_pass"]
    lens = lenses["reader"]
    assert isinstance(review, dict)
    assert isinstance(lens, dict)
    review["audiences"] = ["writers"]

    config = Config.from_mapping(data)

    lens["description"] = "Changed after validation"
    review["audiences"].append("attackers")
    data["metadata"]["owners"].append("changed")

    assert config.lens("reader")["description"] == "A reader-centered perspective."
    assert config.review("first_pass").metadata["audiences"] == ("writers",)
    assert config.metadata["metadata"]["owners"] == ("original",)
    assert isinstance(config.lenses, MappingProxyType)
    assert isinstance(config.review("first_pass").metadata, MappingProxyType)


def test_component_accessors_return_independent_mutable_copies() -> None:
    config = Config.from_mapping(valid_config())

    first = config.mission("clarity")
    questions = first["questions"]
    assert isinstance(questions, list)
    first["description"] = "Caller mutation"
    questions.append("A new question")

    second = config.mission("clarity")
    assert second == {"questions": ["What is unclear?"]}
    assert first is not second
    assert first["questions"] is not second["questions"]


def test_public_config_mappings_are_recursively_immutable() -> None:
    config = Config.from_mapping(valid_config())

    with pytest.raises(TypeError):
        config.lenses["new"] = {}  # type: ignore[index]
    lens = config.lenses["reader"]
    with pytest.raises(TypeError):
        lens["description"] = "changed"  # type: ignore[index]
    questions = config.missions["clarity"]["questions"]
    assert isinstance(questions, tuple)


def test_from_mapping_rejects_non_json_nested_values() -> None:
    data = valid_config()
    lenses = data["lenses"]
    assert isinstance(lenses, dict)
    reader = lenses["reader"]
    assert isinstance(reader, dict)
    reader["unsupported"] = {"set value"}

    with pytest.raises(ConfigValidationError, match="JSON-compatible values"):
        Config.from_mapping(data)
