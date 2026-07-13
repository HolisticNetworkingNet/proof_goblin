# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Structured review observations and their provenance."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from proof_goblin.builder import Prompt


REVIEW_RESULT_FORMAT = "proof-goblin-review-result"
REVIEW_RESULT_SCHEMA_VERSION = "1.0"


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
class ReviewResult:
    """Validated observations plus execution and input provenance."""

    observations: tuple[Observation, ...]
    prompt: Prompt
    provider: str
    model: str
    response_id: str | None
    usage: TokenUsage
    raw_output: Mapping[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("created_at must include timezone information")

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
                "name": self.prompt.review_name,
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


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
