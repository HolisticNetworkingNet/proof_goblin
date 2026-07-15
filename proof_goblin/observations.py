

"""Structured review observations and their provenance."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from proof_goblin.builder import Prompt

REVIEW_RESULT_FORMAT = "proof-goblin-review-result"
REVIEW_RESULT_SCHEMA_VERSION = "1.0"


class ReviewResultProvenanceError(ValueError):
    """Raised when a serialized result does not match its supplied prompt."""


@dataclass(frozen=True, slots=True)
class Observation:
    """A question and the artifact evidence that prompted it."""

    question: str
    evidence: str


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token counts reported by a model provider."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ReviewAttribution:
    """Stable and human-readable identity of the resolved review."""

    name: str
    title: str
    description: str
    lens: str
    mission: str
    protocol: str
    output_schema: str


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """Validated observations plus execution and input provenance."""

    observations: tuple[Observation, ...]
    prompt: Prompt
    review: ReviewAttribution
    provider: str
    model: str
    response_id: str | None
    usage: TokenUsage
    raw_output: Mapping[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must include timezone information")
        if self.review.name != self.prompt.review_name:
            raise ValueError("review attribution must match prompt review name")

    def to_dict(self, *, include_prompt: bool = False) -> dict[str, Any]:
        """Return a versioned, JSON-compatible host-application record.

        Prompt text is excluded by default because its user portion contains the
        complete reviewed artifact.
        """

        record: dict[str, Any] = {
            "format": REVIEW_RESULT_FORMAT,
            "schema_version": REVIEW_RESULT_SCHEMA_VERSION,
            "created_at": _format_datetime(self.created_at),
            "review": {
                "name": self.review.name,
                "title": self.review.title,
                "description": self.review.description,
                "lens": self.review.lens,
                "mission": self.review.mission,
                "protocol": self.review.protocol,
                "output_schema": self.review.output_schema,
            },
            "config": {
                "name": self.prompt.config_name,
                "version": self.prompt.config_version,
                "sha256": self.prompt.config_sha256,
            },
            "artifact": {
                "name": self.prompt.artifact_name,
                "media_type": self.prompt.artifact_media_type,
                "sha256": self.prompt.artifact_sha256,
            },
            "execution": {
                "provider": self.provider,
                "model": self.model,
                "response_id": self.response_id,
                "usage": {
                    "input_tokens": self.usage.input_tokens,
                    "output_tokens": self.usage.output_tokens,
                    "total_tokens": self.usage.total_tokens,
                },
            },
            "observations": [
                {
                    "question": observation.question,
                    "evidence": observation.evidence,
                }
                for observation in self.observations
            ],
        }
        if include_prompt:
            record["prompt"] = {
                "system": self.prompt.system,
                "user": self.prompt.user,
            }
        return record

    def to_json(
        self,
        *,
        include_prompt: bool = False,
        indent: int | None = 2,
    ) -> str:
        """Serialize the versioned result record as JSON."""

        return json.dumps(
            self.to_dict(include_prompt=include_prompt),
            ensure_ascii=False,
            indent=indent,
            sort_keys=True,
        )

    @classmethod
    def from_dict(
        cls,
        record: Mapping[str, Any],
        *,
        prompt: Prompt,
    ) -> ReviewResult:
        """Reconstruct a result record using a separately assembled prompt.

        Canonical result records omit prompt text by default. Requiring the
        caller to supply the prompt keeps reviewed artifact bodies out of
        caches while still allowing their provenance to be verified.
        """

        if record.get("format") != REVIEW_RESULT_FORMAT:
            raise ValueError("unsupported review result format")
        if record.get("schema_version") != REVIEW_RESULT_SCHEMA_VERSION:
            raise ValueError("unsupported review result schema version")

        review_record = _require_mapping(record, "review")
        config_record = _require_mapping(record, "config")
        artifact_record = _require_mapping(record, "artifact")
        execution_record = _require_mapping(record, "execution")
        usage_record = _require_mapping(execution_record, "usage")

        cached_review_name = review_record.get("name")
        if cached_review_name != prompt.review_name:
            raise ReviewResultProvenanceError(
                "cached review.name does not match current prompt"
            )

        expected_provenance = {
            "config.name": (config_record.get("name"), prompt.config_name),
            "config.version": (config_record.get("version"), prompt.config_version),
            "config.sha256": (config_record.get("sha256"), prompt.config_sha256),
            "artifact.name": (artifact_record.get("name"), prompt.artifact_name),
            "artifact.media_type": (
                artifact_record.get("media_type"),
                prompt.artifact_media_type,
            ),
            "artifact.sha256": (
                artifact_record.get("sha256"),
                prompt.artifact_sha256,
            ),
        }
        for field_name, (cached_value, prompt_value) in expected_provenance.items():
            if cached_value != prompt_value:
                raise ReviewResultProvenanceError(
                    f"cached {field_name} does not match current prompt"
                )

        observation_records = record.get("observations")
        if not isinstance(observation_records, list):
            raise ValueError("observations must be an array")
        observations_list: list[Observation] = []
        for value in observation_records:
            observation_record = _require_observation_mapping(value)
            observations_list.append(
                Observation(
                    question=_require_string(observation_record, "question"),
                    evidence=_require_string(observation_record, "evidence"),
                )
            )
        observations = tuple(observations_list)

        created_at_value = _require_string(record, "created_at")
        try:
            created_at = datetime.fromisoformat(created_at_value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("created_at must be an ISO 8601 datetime") from exc

        response_id = execution_record.get("response_id")
        if response_id is not None and not isinstance(response_id, str):
            raise ValueError("execution.response_id must be a string or null")

        raw_output = {
            "observations": [
                {
                    "question": observation.question,
                    "evidence": observation.evidence,
                }
                for observation in observations
            ]
        }
        return cls(
            observations=observations,
            prompt=prompt,
            review=ReviewAttribution(
                name=_require_string(review_record, "name"),
                title=_require_string(review_record, "title"),
                description=_require_string(review_record, "description"),
                lens=_require_string(review_record, "lens"),
                mission=_require_string(review_record, "mission"),
                protocol=_require_string(review_record, "protocol"),
                output_schema=_require_string(review_record, "output_schema"),
            ),
            provider=_require_string(execution_record, "provider"),
            model=_require_string(execution_record, "model"),
            response_id=response_id,
            usage=TokenUsage(
                input_tokens=_optional_non_negative_int(usage_record, "input_tokens"),
                output_tokens=_optional_non_negative_int(usage_record, "output_tokens"),
                total_tokens=_optional_non_negative_int(usage_record, "total_tokens"),
            ),
            raw_output=raw_output,
            created_at=created_at,
        )


def _format_datetime(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_mapping(record: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    value = record.get(field)
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _require_observation_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("each observation must be an object")
    return value


def _require_string(record: Mapping[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _optional_non_negative_int(record: Mapping[str, Any], field: str) -> int | None:
    value = record.get(field)
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer or null")
    return value
