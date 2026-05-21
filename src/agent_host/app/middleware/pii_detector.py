"""PII detection middleware — Presidio (local) with regex fallback."""
from __future__ import annotations

import logging
import re
from typing import Any

from opentelemetry import trace

from app.middleware.exceptions import GuardrailViolation

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_DEFAULT_ENTITIES = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "PERSON",
    "US_DRIVER_LICENSE",
    "US_PASSPORT",
    "IBAN_CODE",
    "IP_ADDRESS",
]

_PRESIDIO_AVAILABLE = False
try:
    from presidio_analyzer import AnalyzerEngine  # type: ignore[import-untyped]
    from presidio_anonymizer import AnonymizerEngine  # type: ignore[import-untyped]
    _PRESIDIO_AVAILABLE = True
except ImportError:
    pass


class PIIDetectorMiddleware:
    """Detects (and optionally redacts or blocks) PII in text payloads.

    Action modes: ``log`` (default), ``redact``, ``block``.
    """

    def __init__(
        self,
        action: str = "log",
        entities: list[str] | None = None,
        score_threshold: float = 0.7,
    ) -> None:
        self._action = action.lower()
        self._entities = entities or _DEFAULT_ENTITIES
        self._threshold = score_threshold
        if _PRESIDIO_AVAILABLE:
            self._analyzer: Any = AnalyzerEngine()
            self._anonymizer: Any = AnonymizerEngine()
        else:
            self._analyzer = None
            self._anonymizer = None
            logger.warning("presidio-analyzer not installed; PII detection using regex fallback")

    async def process(self, text: str, language: str = "en") -> str:
        """Analyse text for PII and apply the configured action."""
        with tracer.start_as_current_span("guardrail.pii_detection") as span:
            span.set_attribute("guardrail.layer", "pii")
            found = self._detect(text, language)
            entity_counts: dict[str, int] = {}
            for item in found:
                entity_counts[item["entity_type"]] = entity_counts.get(item["entity_type"], 0) + 1
            total = len(found)
            span.set_attribute("guardrail.entities_found", total)
            if total == 0:
                span.set_attribute("guardrail.outcome", "pass")
                return text
            # Log entity types + counts — NEVER the actual values
            logger.warning("PII detected: %s", {k: v for k, v in entity_counts.items()})
            if self._action == "block":
                span.set_attribute("guardrail.outcome", "block")
                raise GuardrailViolation(
                    layer="pii",
                    reason="PII detected in payload",
                    details={"entity_counts": entity_counts},
                    severity="high",
                )
            if self._action == "redact":
                span.set_attribute("guardrail.outcome", "redacted")
                return self._redact(text, found)
            span.set_attribute("guardrail.outcome", "logged")
            return text

    def _detect(self, text: str, language: str) -> list[dict[str, Any]]:
        if _PRESIDIO_AVAILABLE and self._analyzer is not None:
            results = self._analyzer.analyze(
                text=text,
                language=language,
                entities=self._entities,
                score_threshold=self._threshold,
            )
            return [
                {"entity_type": r.entity_type, "start": r.start, "end": r.end, "score": r.score}
                for r in results
            ]
        return self._regex_fallback(text)

    @staticmethod
    def _regex_fallback(text: str) -> list[dict[str, Any]]:
        patterns: list[tuple[str, str]] = [
            ("EMAIL_ADDRESS", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
            ("PHONE_NUMBER", r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
            ("US_SSN", r"\b\d{3}-\d{2}-\d{4}\b"),
            ("CREDIT_CARD", r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        ]
        found: list[dict[str, Any]] = []
        for entity_type, pattern in patterns:
            for match in re.finditer(pattern, text):
                found.append({"entity_type": entity_type, "start": match.start(), "end": match.end(), "score": 0.85})
        return found

    def _redact(self, text: str, found: list[dict[str, Any]]) -> str:
        if _PRESIDIO_AVAILABLE and self._anonymizer is not None:
            from presidio_analyzer import RecognizerResult  # type: ignore[import-untyped]
            recognizer_results = [
                RecognizerResult(entity_type=item["entity_type"], start=item["start"], end=item["end"], score=item["score"])
                for item in found
            ]
            anonymized = self._anonymizer.anonymize(text=text, analyzer_results=recognizer_results)
            return anonymized.text
        sorted_found = sorted(found, key=lambda x: x["start"], reverse=True)
        chars = list(text)
        for item in sorted_found:
            chars[item["start"]:item["end"]] = list("[REDACTED]")
        return "".join(chars)
