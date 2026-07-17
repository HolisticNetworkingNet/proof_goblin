"""Deterministic input limits shared by every Proof Goblin interface."""

from __future__ import annotations

from dataclasses import dataclass


class InputLimitError(ValueError):
    """Raised when an input exceeds a configured deterministic boundary."""

    def __init__(self, boundary: str, measured: int, limit: int) -> None:
        self.boundary = boundary
        self.measured = measured
        self.limit = limit
        super().__init__(
            f"{boundary} is {measured} UTF-8 bytes; configured limit is {limit} bytes"
        )


@dataclass(frozen=True, slots=True)
class InputLimits:
    """Configurable byte ceilings for configuration, artifacts, and prompts."""

    max_config_bytes: int = 1_048_576
    max_artifact_bytes: int = 262_144
    max_total_artifact_bytes: int = 262_144
    max_system_prompt_bytes: int = 131_072
    max_prompt_bytes: int = 524_288

    def __post_init__(self) -> None:
        for name in (
            "max_config_bytes",
            "max_artifact_bytes",
            "max_total_artifact_bytes",
            "max_system_prompt_bytes",
            "max_prompt_bytes",
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


DEFAULT_INPUT_LIMITS = InputLimits()


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
