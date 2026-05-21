"""Tests for middleware package wiring."""
from __future__ import annotations

import pytest

from app.middleware import build_middleware_chain
from app.middleware.exceptions import GuardrailViolation


def test_build_middleware_chain_splits_allowed_views_string():
    chain = build_middleware_chain(sql_allowed_views="vw_agents, vw_queues , vw_forecast")
    sql_validator = chain["sql"]

    assert sql_validator.validate_and_patch("SELECT agent_id FROM analytics.vw_agents")
    with pytest.raises(GuardrailViolation):
        sql_validator.validate_and_patch("SELECT * FROM analytics.vw_schedule")