

"""Load and validate portable Proof Goblin configuration bundles."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_FORMAT = "proof-goblin-config"
SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0"})


class ConfigError(ValueError):
    """Base exception for configuration errors."""


class ConfigParseError(ConfigError):
    """Raised when a configuration file cannot be read or parsed."""


class ConfigValidationError(ConfigError):
    """Raised when parsed configuration data is structurally invalid."""


class ComponentNotFoundError(ConfigError, KeyError):
    """Raised when a named component does not exist in a bundle."""


@dataclass(frozen=True, slots=True)
class ReviewDefinition:
    """References to the components that make up a named review."""

    name: str
    title: str
    description: str
    lens: str
    mission: str
    protocol: str
    output_schema: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Config:
    """A validated Proof Goblin configuration bundle."""

    name: str
    version: str
    schema_version: str
    lenses: Mapping[str, Mapping[str, Any]]
    missions: Mapping[str, Mapping[str, Any]]
    protocols: Mapping[str, Mapping[str, Any]]
    output_schemas: Mapping[str, Mapping[str, Any]]
    reviews: Mapping[str, ReviewDefinition]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    source_path: Path | None = None
    sha256: str | None = None

    @classmethod
    def load(cls, path: str | Path) -> Config:
        """Load and validate a JSON-encoded ``.pgcfg`` file.

        Args:
            path: Path to the configuration bundle.

        Raises:
            ConfigParseError: If the file cannot be read or contains invalid JSON.
            ConfigValidationError: If the decoded data does not match the supported
                Proof Goblin configuration structure.
        """

        source_path = Path(path)
        if source_path.suffix.lower() != ".pgcfg":
            raise ConfigValidationError(
                f"Configuration file must use the .pgcfg extension: {source_path}"
            )

        try:
            content = source_path.read_bytes()
        except OSError as exc:
            raise ConfigParseError(
                f"Could not read configuration file {source_path}: {exc}"
            ) from exc

        try:
            data = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            location = ""
            if isinstance(exc, json.JSONDecodeError):
                location = f" at line {exc.lineno}, column {exc.colno}"
            raise ConfigParseError(
                f"Invalid JSON in configuration file {source_path}{location}: {exc.msg}"
            ) from exc

        return cls.from_mapping(
            data,
            source_path=source_path.resolve(),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    @classmethod
    def from_mapping(
        cls,
        data: object,
        *,
        source_path: Path | None = None,
        sha256: str | None = None,
    ) -> Config:
        """Validate already-decoded configuration data."""

        root = _require_mapping(data, "configuration")
        _require_exact_value(root, "format", CONFIG_FORMAT)
        schema_version = _require_string(root, "schema_version")
        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_SCHEMA_VERSIONS))
            raise ConfigValidationError(
                f"Unsupported schema_version {schema_version!r}; supported: {supported}"
            )

        name = _require_string(root, "name")
        bundle_version = _require_string(root, "version")
        lenses = _require_components(root, "lenses")
        missions = _require_components(root, "missions")
        protocols = _require_components(root, "protocols")
        output_schemas = _require_components(root, "output_schemas")
        reviews_data = _require_mapping(root.get("reviews"), "reviews")

        reviews: dict[str, ReviewDefinition] = {}
        for review_name, value in reviews_data.items():
            _require_component_name(review_name, "reviews")
            review_path = f"reviews.{review_name}"
            review = _require_mapping(value, review_path)
            title = _require_string(review, "title", review_path)
            description = _require_string(review, "description", review_path)
            lens = _require_string(review, "lens", review_path)
            mission = _require_string(review, "mission", review_path)
            protocol = _require_string(review, "protocol", review_path)
            output_schema = _require_string(review, "output_schema", review_path)

            _require_reference(lens, lenses, f"{review_path}.lens", "lens")
            _require_reference(mission, missions, f"{review_path}.mission", "mission")
            _require_reference(
                protocol, protocols, f"{review_path}.protocol", "protocol"
            )
            _require_reference(
                output_schema,
                output_schemas,
                f"{review_path}.output_schema",
                "output schema",
            )

            reviews[review_name] = ReviewDefinition(
                name=review_name,
                title=title,
                description=description,
                lens=lens,
                mission=mission,
                protocol=protocol,
                output_schema=output_schema,
                metadata={
                    key: item
                    for key, item in review.items()
                    if key
                    not in {
                        "title",
                        "description",
                        "lens",
                        "mission",
                        "protocol",
                        "output_schema",
                    }
                },
            )

        metadata = {
            key: value
            for key, value in root.items()
            if key
            not in {
                "format",
                "schema_version",
                "name",
                "version",
                "lenses",
                "missions",
                "protocols",
                "output_schemas",
                "reviews",
            }
        }

        return cls(
            name=name,
            version=bundle_version,
            schema_version=schema_version,
            lenses=lenses,
            missions=missions,
            protocols=protocols,
            output_schemas=output_schemas,
            reviews=reviews,
            metadata=metadata,
            source_path=source_path,
            sha256=sha256,
        )

    def lens(self, name: str) -> Mapping[str, Any]:
        """Return a named Proof Lens."""

        return _get_component(self.lenses, name, "lens")

    def mission(self, name: str) -> Mapping[str, Any]:
        """Return a named mission."""

        return _get_component(self.missions, name, "mission")

    def protocol(self, name: str) -> Mapping[str, Any]:
        """Return a named protocol."""

        return _get_component(self.protocols, name, "protocol")

    def output_schema(self, name: str) -> Mapping[str, Any]:
        """Return a named output schema."""

        return _get_component(self.output_schemas, name, "output schema")

    def review(self, name: str) -> ReviewDefinition:
        """Return a named review definition."""

        try:
            return self.reviews[name]
        except KeyError as exc:
            raise ComponentNotFoundError(f"Unknown review {name!r}") from exc


def _require_mapping(value: object, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigValidationError(f"{path} must be a JSON object")
    return value


def _require_string(
    mapping: Mapping[str, Any], key: str, path: str = "configuration"
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigValidationError(f"{path}.{key} must be a non-empty string")
    return value


def _require_exact_value(mapping: Mapping[str, Any], key: str, expected: str) -> None:
    value = mapping.get(key)
    if value != expected:
        raise ConfigValidationError(
            f"configuration.{key} must be {expected!r}, got {value!r}"
        )


def _require_components(
    root: Mapping[str, Any], collection_name: str
) -> dict[str, Mapping[str, Any]]:
    values = _require_mapping(root.get(collection_name), collection_name)
    components: dict[str, Mapping[str, Any]] = {}
    for name, value in values.items():
        _require_component_name(name, collection_name)
        components[name] = _require_mapping(value, f"{collection_name}.{name}")
    return components


def _require_component_name(name: object, collection_name: str) -> None:
    if not isinstance(name, str) or not name.strip():
        raise ConfigValidationError(
            f"Every key in {collection_name} must be a non-empty string"
        )


def _require_reference(
    name: str,
    collection: Mapping[str, Any],
    path: str,
    component_type: str,
) -> None:
    if name not in collection:
        raise ConfigValidationError(
            f"{path} references unknown {component_type} {name!r}"
        )


def _get_component(
    collection: Mapping[str, Mapping[str, Any]], name: str, component_type: str
) -> Mapping[str, Any]:
    try:
        return collection[name]
    except KeyError as exc:
        raise ComponentNotFoundError(f"Unknown {component_type} {name!r}") from exc
