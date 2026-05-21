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

    @staticmethod
    def _as_bytes(value: str | bytes) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, str):
            return value.encode()
        raise TypeError("HMAC payload/signature must be str or bytes")

    def sign(self, payload: str | bytes) -> str:
        """Return a hex-encoded HMAC-SHA256 signature for *payload*."""
        with tracer.start_as_current_span("guardrail.hmac") as span:
            span.set_attribute("guardrail.layer", "hmac")
            try:
                sig = hmac.new(self._key, self._as_bytes(payload), hashlib.sha256).hexdigest()
                span.set_attribute("guardrail.outcome", "signed")
                return sig
            except Exception as exc:
                span.set_attribute("guardrail.outcome", "error")
                span.record_exception(exc)
                raise

    def verify(self, payload: str | bytes, signature: str | bytes) -> bool:
        """Return True if *signature* is valid for *payload* (timing-safe)."""
        if not signature or not isinstance(signature, (str, bytes)):
            return False
        expected = hmac.new(self._key, self._as_bytes(payload), hashlib.sha256).hexdigest()
        if isinstance(signature, bytes):
            return hmac.compare_digest(expected.encode(), signature)
        return hmac.compare_digest(expected, signature)

    def verify_or_raise(self, payload: str | bytes, signature: str | bytes) -> None:
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