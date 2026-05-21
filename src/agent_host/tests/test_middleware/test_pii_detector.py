"""Tests for PIIDetectorMiddleware."""
from __future__ import annotations

import pytest

from app.middleware.exceptions import GuardrailViolation
from app.middleware.pii_detector import PIIDetectorMiddleware, _PRESIDIO_AVAILABLE


def _mw(action: str = "log") -> PIIDetectorMiddleware:
    return PIIDetectorMiddleware(action=action, score_threshold=0.5)


@pytest.mark.asyncio
async def test_clean_text_passes():
    mw = _mw("log")
    result = await mw.process("Show me the top 10 agents by AHT")
    assert result == "Show me the top 10 agents by AHT"


@pytest.mark.asyncio
async def test_email_detected_log_mode():
    mw = _mw("log")
    text = "Contact me at john.doe@example.com for details"
    result = await mw.process(text)
    assert result == text


@pytest.mark.asyncio
async def test_phone_detected_log_mode():
    mw = _mw("log")
    text = "Call me at 555-867-5309 for the report"
    result = await mw.process(text)
    assert result == text


@pytest.mark.asyncio
async def test_ssn_detected_log_mode():
    mw = _mw("log")
    text = "Employee SSN is 123-45-6789"
    result = await mw.process(text)
    assert result == text


@pytest.mark.asyncio
async def test_credit_card_detected_log_mode():
    mw = _mw("log")
    text = "Card number 4111-1111-1111-1111 was flagged"
    result = await mw.process(text)
    assert result == text


@pytest.mark.asyncio
async def test_email_redacted():
    mw = _mw("redact")
    result = await mw.process("Contact me at john.doe@example.com")
    assert "john.doe@example.com" not in result


@pytest.mark.asyncio
async def test_phone_redacted():
    """Phone redaction — uses Presidio (score ~0.75) or regex fallback."""
    mw = PIIDetectorMiddleware(action="redact", score_threshold=0.5)
    result = await mw.process("My phone 555-867-5309")
    assert "555-867-5309" not in result


@pytest.mark.asyncio
async def test_ssn_redacted_via_regex():
    """SSN redaction via built-in regex fallback (threshold 0 forces regex path)."""
    mw = PIIDetectorMiddleware(action="redact", score_threshold=0.0)
    # Force regex: temporarily disable Presidio in the instance
    mw._analyzer = None
    mw._anonymizer = None
    result = await mw.process("SSN: 123-45-6789")
    assert "123-45-6789" not in result


@pytest.mark.asyncio
async def test_email_block_mode_raises():
    mw = _mw("block")
    with pytest.raises(GuardrailViolation) as exc_info:
        await mw.process("Reach me at blocked@company.com")
    assert exc_info.value.layer == "pii"
    assert exc_info.value.severity == "high"


@pytest.mark.asyncio
async def test_clean_text_block_mode_passes():
    mw = _mw("block")
    result = await mw.process("Show me queue metrics for last week")
    assert result == "Show me queue metrics for last week"


@pytest.mark.asyncio
async def test_block_mode_details_contain_no_pii_values():
    mw = _mw("block")
    try:
        await mw.process("my email is secret@test.com and SSN 987-65-4321")
    except GuardrailViolation as exc:
        details_str = str(exc.details)
        assert "secret@test.com" not in details_str
        assert "987-65-4321" not in details_str
        assert "entity_counts" in exc.details