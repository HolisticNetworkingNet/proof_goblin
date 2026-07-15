from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from proof_goblin import (
    ComponentNotFoundError,
    Config,
    ConfigParseError,
    ConfigValidationError,
)

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
