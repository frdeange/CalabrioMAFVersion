"""Middleware package for the Agent Host safety stack.

Layer order (request path):
  1. PromptShields    - detect prompt injection / jailbreak before any agent call
  2. PIIDetector      - detect / redact PII in the user payload
  3. (agent call)
  4. SQLValidator     - validate SqlBuilder output (SELECT-only, whitelisted views)
  5. HMACSigner.sign  - sign SqlPlan payload leaving SqlBuilder
  6. (next agent call)
  7. HMACSigner.verify_or_raise - verify signature on Executor input
"""
from __future__ import annotations

from app.middleware.exceptions import GuardrailViolation
from app.middleware.hmac_signer import HMACSigner
from app.middleware.pii_detector import PIIDetectorMiddleware
from app.middleware.prompt_shields import PromptShieldsMiddleware
from app.middleware.sql_validator import SQLValidator


def build_middleware_chain(
    *,
    content_safety_endpoint: str = "",
    content_safety_key: str = "",
    prompt_shields_fail_mode: str = "closed",
    pii_action: str = "log",
    hmac_secret: str = "",
    sql_allowed_views: list[str] | str | None = None,
) -> dict[str, object]:
    """Instantiate and return all middleware layers keyed by name."""
    chain: dict[str, object] = {}
    if content_safety_endpoint:
        chain["prompt_shields"] = PromptShieldsMiddleware(
            endpoint=content_safety_endpoint,
            api_key=content_safety_key,
            fail_mode=prompt_shields_fail_mode,
        )
    chain["pii"] = PIIDetectorMiddleware(action=pii_action)
    if hmac_secret:
        chain["hmac"] = HMACSigner(secret=hmac_secret)
    views = [v.strip() for v in sql_allowed_views.split(",") if v.strip()] if isinstance(sql_allowed_views, str) else sql_allowed_views
    chain["sql"] = SQLValidator(allowed_views=views)
    return chain


__all__ = [
    "GuardrailViolation",
    "PromptShieldsMiddleware",
    "PIIDetectorMiddleware",
    "HMACSigner",
    "SQLValidator",
    "build_middleware_chain",
]