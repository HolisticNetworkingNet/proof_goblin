# Copyright (c) 2025 We Build Reactions.
# Proprietary and confidential. See LICENSE for details.

"""Structured review observations and their provenance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from proof_goblin.builder import Prompt


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
