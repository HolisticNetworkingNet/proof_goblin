"""Deterministic input limits shared by every Proof Goblin interface."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


class InputLimitError(ValueError):
    """Raised when an input exceeds a configured deterministic boundary."""

    def __init__(
        self,
        boundary: str,
        measured: int,
        limit: int,
        *,
        unit: str = "UTF-8 bytes",
        limit_unit: str = "bytes",
    ) -> None:
        self.boundary = boundary
        self.measured = measured
        self.limit = limit
        super().__init__(
            f"{boundary} is {measured} {unit}; configured limit is {limit} {limit_unit}"
        )


@dataclass(frozen=True, slots=True)
class InputLimits:
    """Configurable ceilings for inputs, decoded output, and rendered output."""

    max_config_bytes: int = 1_048_576
    max_artifact_bytes: int = 262_144
    max_total_artifact_bytes: int = 262_144
    max_system_prompt_bytes: int = 131_072
    max_prompt_bytes: int = 524_288
    max_provider_response_bytes: int = 1_048_576
    max_rendered_output_bytes: int = 8_388_608
    max_json_depth: int = 64

    def __post_init__(self) -> None:
        for name in (
            "max_config_bytes",
            "max_artifact_bytes",
            "max_total_artifact_bytes",
            "max_system_prompt_bytes",
            "max_prompt_bytes",
            "max_provider_response_bytes",
            "max_rendered_output_bytes",
            "max_json_depth",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

    def enforce(self, boundary: str, measured: int, limit: int) -> None:
        """Reject a measured boundary that exceeds its configured ceiling."""

        if isinstance(measured, bool) or not isinstance(measured, int) or measured < 0:
            raise ValueError("measured byte count must be a non-negative integer")
        if measured > limit:
            raise InputLimitError(boundary, measured, limit)

    def enforce_config(self, measured: int) -> None:
        self.enforce("configuration input", measured, self.max_config_bytes)

    def enforce_artifact(self, measured: int) -> None:
        self.enforce("artifact input", measured, self.max_artifact_bytes)
        self.enforce(
            "aggregate artifact input",
            measured,
            self.max_total_artifact_bytes,
        )

    def enforce_system_prompt(self, measured: int) -> None:
        self.enforce(
            "assembled system prompt",
            measured,
            self.max_system_prompt_bytes,
        )

    def enforce_prompt(self, measured: int) -> None:
        self.enforce("total assembled prompt", measured, self.max_prompt_bytes)

    def enforce_provider_response(self, measured: int) -> None:
        self.enforce(
            "decoded provider response",
            measured,
            self.max_provider_response_bytes,
        )

    def enforce_rendered_output(self, measured: int) -> None:
        self.enforce(
            "rendered output",
            measured,
            self.max_rendered_output_bytes,
        )

    def enforce_json_depth(self, measured: int, boundary: str) -> None:
        if measured > self.max_json_depth:
            raise InputLimitError(
                boundary,
                measured,
                self.max_json_depth,
                unit="levels",
                limit_unit="levels",
            )


DEFAULT_INPUT_LIMITS = InputLimits()


def measure_json_utf8_bytes(
    value: object,
    *,
    limits: InputLimits,
    boundary: str,
) -> int:
    """Measure compact JSON without constructing one complete serialized copy."""

    def measure(item: object, depth: int) -> int:
        limits.enforce_json_depth(depth, boundary)
        if isinstance(item, Mapping):
            total = 2
            for index, (key, child) in enumerate(item.items()):
                if not isinstance(key, str):
                    raise TypeError(f"{boundary} JSON object keys must be strings")
                if index:
                    total += 1
                total += scalar_size(key) + 1 + measure(child, depth + 1)
            return total
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            return (
                2
                + max(0, len(item) - 1)
                + sum(measure(child, depth + 1) for child in item)
            )
        return scalar_size(item)

    def scalar_size(item: object) -> int:
        if item is not None and not isinstance(item, (str, int, float, bool)):
            raise TypeError(
                f"{boundary} must contain only JSON-compatible values, got "
                f"{type(item).__name__}"
            )
        return len(
            json.dumps(
                item,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )

    return measure(value, 1)


@dataclass(frozen=True, slots=True)
class PromptMeasurements:
    """Safe UTF-8 byte counts for an assembled prompt and its artifact."""

    artifact_bytes: int
    system_prompt_bytes: int
    user_prompt_bytes: int
    total_prompt_bytes: int

    @classmethod
    def measure(cls, *, artifact: str, system: str, user: str) -> PromptMeasurements:
        """Measure exact strings without retaining another copy of their content."""

        artifact_bytes = len(artifact.encode("utf-8"))
        system_prompt_bytes = len(system.encode("utf-8"))
        user_prompt_bytes = len(user.encode("utf-8"))
        return cls(
            artifact_bytes=artifact_bytes,
            system_prompt_bytes=system_prompt_bytes,
            user_prompt_bytes=user_prompt_bytes,
            total_prompt_bytes=system_prompt_bytes + user_prompt_bytes,
        )

    def enforce(self, limits: InputLimits) -> None:
        """Apply every assembled-input ceiling to these measurements."""

        limits.enforce_artifact(self.artifact_bytes)
        limits.enforce_system_prompt(self.system_prompt_bytes)
        limits.enforce_prompt(self.total_prompt_bytes)
