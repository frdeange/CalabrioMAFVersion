"""PromptShields middleware — Azure Content Safety /text:shieldPrompt."""
from __future__ import annotations

import logging
from typing import Any

import httpx
from opentelemetry import trace

from app.middleware.exceptions import GuardrailViolation

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_SHIELD_PATH = "/text:shieldPrompt?api-version=2024-09-01"


class PromptShieldsMiddleware:
    """Calls Azure Content Safety Prompt Shields before passing the prompt to an agent."""

    def __init__(
        self,
        endpoint: str,
        api_key: str = "",
        fail_mode: str = "closed",
        timeout_seconds: float = 5.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._fail_mode = fail_mode.lower()
        self._timeout = timeout_seconds

    async def check(self, user_prompt: str, documents: list[str] | None = None) -> None:
        """Analyse user_prompt for injection / jailbreak attempts."""
        with tracer.start_as_current_span("guardrail.prompt_shields") as span:
            span.set_attribute("guardrail.layer", "prompt_shields")
            try:
                result = await self._call_api(user_prompt, documents or [])
                outcome, attack_type, confidence = self._evaluate(result)
                span.set_attribute("guardrail.outcome", outcome)
                if attack_type:
                    span.set_attribute("guardrail.attack_type", attack_type)
                if outcome == "block":
                    details: dict[str, Any] = {"attack_type": attack_type}
                    if confidence is not None:
                        details["confidence"] = confidence
                    raise GuardrailViolation(
                        layer="prompt_shields",
                        reason=f"Prompt injection / jailbreak detected: {attack_type}",
                        details=details,
                        severity="critical",
                    )
            except GuardrailViolation:
                raise
            except Exception as exc:
                span.set_attribute("guardrail.outcome", "error")
                span.record_exception(exc)
                logger.warning("PromptShields service error: %s", exc)
                if self._fail_mode == "closed":
                    raise GuardrailViolation(
                        layer="prompt_shields",
                        reason="Content Safety service unavailable (fail-closed)",
                        details={"error": str(exc)},
                        severity="high",
                    ) from exc
                logger.warning("PromptShields fail-open: continuing despite service error")

    async def _call_api(self, user_prompt: str, documents: list[str]) -> dict[str, Any]:
        headers = {
            "Ocp-Apim-Subscription-Key": self._api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {"userPrompt": user_prompt}
        if documents:
            payload["documents"] = documents
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                self._endpoint + _SHIELD_PATH,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _evaluate(result: dict[str, Any]) -> tuple[str, str, float | None]:
        """Return (outcome, attack_type, confidence)."""
        user_result: dict[str, Any] = result.get("userPromptAnalysis", {})
        attacks: list[dict[str, Any]] = user_result.get("attacksDetected", [])
        if attacks:
            first_attack = attacks[0]
            return "block", first_attack.get("attackType", "unknown"), first_attack.get("confidence")
        for doc in result.get("documentsAnalysis", []):
            doc_attacks: list[dict[str, Any]] = doc.get("attacksDetected", [])
            if doc_attacks:
                first_attack = doc_attacks[0]
                return "block", first_attack.get("attackType", "unknown"), first_attack.get("confidence")
        return "pass", "", None