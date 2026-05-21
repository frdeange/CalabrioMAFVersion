"""HMAC signing/verification for inter-agent payload integrity."""
from __future__ import annotations

import hashlib
import hmac
import logging

from opentelemetry import trace

from app.middleware.exceptions import GuardrailViolation

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class HMACSigner:
    """Signs and verifies string payloads with HMAC-SHA256."""

    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("HMAC_SECRET must not be empty")
        self._key = secret.encode()

    def sign(self, payload: str) -> str:
        """Return a hex-encoded HMAC-SHA256 signature for *payload*."""
        with tracer.start_as_current_span("guardrail.hmac") as span:
            span.set_attribute("guardrail.layer", "hmac")
            try:
                sig = hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()
                span.set_attribute("guardrail.outcome", "signed")
                return sig
            except Exception as exc:
                span.set_attribute("guardrail.outcome", "error")
                span.record_exception(exc)
                raise

    def verify(self, payload: str, signature: str) -> bool:
        """Return True if *signature* is valid for *payload* (timing-safe)."""
        expected = hmac.new(self._key, payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected.encode(), signature.encode())

    def verify_or_raise(self, payload: str, signature: str) -> None:
        """Verify and raise GuardrailViolation if the signature is invalid."""
        with tracer.start_as_current_span("guardrail.hmac") as span:
            span.set_attribute("guardrail.layer", "hmac")
            try:
                valid = self.verify(payload, signature)
                outcome = "valid" if valid else "invalid"
                span.set_attribute("guardrail.outcome", outcome)
                if not valid:
                    raise GuardrailViolation(
                        layer="hmac",
                        reason="HMAC signature mismatch — payload may have been tampered",
                        severity="critical",
                    )
            except GuardrailViolation:
                raise
            except Exception as exc:
                span.set_attribute("guardrail.outcome", "error")
                span.record_exception(exc)
                raise
