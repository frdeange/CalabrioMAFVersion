from __future__ import annotations

from typing import Any


class GuardrailViolation(Exception):
    """Raised when a middleware guardrail detects a policy violation."""

    def __init__(
        self,
        layer: str,
        reason: str,
        details: dict[str, Any] | None = None,
        severity: str = "high",
    ) -> None:
        self.layer = layer
        self.reason = reason
        self.details = details or {}
        self.severity = severity
        super().__init__(f"[{layer}] {reason}")

    def __repr__(self) -> str:
        return (
            f"GuardrailViolation(layer={self.layer!r}, reason={self.reason!r}, "
            f"severity={self.severity!r})"
        )
