"""Tests for HMACSigner."""
from __future__ import annotations

import pytest

from app.middleware.exceptions import GuardrailViolation
from app.middleware.hmac_signer import HMACSigner

SECRET = "super-secret-test-key-32bytes!!"


def _signer() -> HMACSigner:
    return HMACSigner(secret=SECRET)


def test_sign_returns_string():
    s = _signer()
    sig = s.sign('{"sql": "SELECT TOP 10 * FROM analytics.vw_agents"}')
    assert isinstance(sig, str)
    assert len(sig) == 64  # hex SHA-256


def test_verify_valid_signature():
    s = _signer()
    payload = '{"sql": "SELECT TOP 10 * FROM analytics.vw_agents"}'
    sig = s.sign(payload)
    assert s.verify(payload, sig) is True


def test_verify_tampered_payload():
    s = _signer()
    payload = '{"sql": "SELECT TOP 10 * FROM analytics.vw_agents"}'
    sig = s.sign(payload)
    tampered = '{"sql": "DROP TABLE agents"}'
    assert s.verify(tampered, sig) is False


def test_verify_wrong_signature():
    s = _signer()
    payload = '{"sql": "SELECT 1"}'
    assert s.verify(payload, "deadbeef" * 8) is False


def test_verify_empty_signature():
    s = _signer()
    assert s.verify("any payload", "") is False


def test_verify_bytes_payload_and_signature():
    s = _signer()
    payload = b'{"tables": ["vw_agents"]}'
    sig = s.sign(payload).encode()
    assert s.verify(payload, sig) is True


def test_verify_or_raise_valid():
    s = _signer()
    payload = '{"tables": ["vw_agents"]}'
    sig = s.sign(payload)
    s.verify_or_raise(payload, sig)


def test_verify_or_raise_invalid_raises():
    s = _signer()
    payload = '{"tables": ["vw_agents"]}'
    bad_sig = "0" * 64
    with pytest.raises(GuardrailViolation) as exc_info:
        s.verify_or_raise(payload, bad_sig)
    assert exc_info.value.layer == "hmac"
    assert exc_info.value.severity == "critical"
    assert "tampered" in exc_info.value.reason.lower()


def test_sign_is_deterministic():
    s = _signer()
    payload = "same payload"
    assert s.sign(payload) == s.sign(payload)


def test_different_secrets_produce_different_signatures():
    s1 = HMACSigner(secret="secret-one-xxxxxxxxxxxxxxxxxxxxxxx")
    s2 = HMACSigner(secret="secret-two-xxxxxxxxxxxxxxxxxxxxxxx")
    payload = "same payload"
    assert s1.sign(payload) != s2.sign(payload)


def test_empty_secret_raises():
    with pytest.raises(ValueError):
        HMACSigner(secret="")


def test_sign_unicode_payload():
    s = _signer()
    payload = "Consulta con acentos: ¿Cuántos agentes?"
    sig = s.sign(payload)
    assert s.verify(payload, sig) is True