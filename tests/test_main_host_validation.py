"""--host must be a loopback IP literal.

Regression test for the QA-hard spec_compliance finding "Spec claims sidecar
listens on 127.0.0.1 only, but --host CLI arg has no validation". Spec says
the sidecar binds to loopback; this enforces it before uvicorn starts.
"""
from __future__ import annotations

import pytest

from worldcanon.main import _require_loopback


def test_loopback_v4_accepted():
    assert _require_loopback("127.0.0.1") == "127.0.0.1"


def test_loopback_v6_accepted():
    assert _require_loopback("::1") == "::1"


def test_zero_zero_zero_zero_rejected():
    with pytest.raises(SystemExit) as exc:
        _require_loopback("0.0.0.0")
    assert "loopback" in str(exc.value).lower()


def test_lan_ip_rejected():
    with pytest.raises(SystemExit):
        _require_loopback("192.168.1.5")


def test_hostname_rejected():
    with pytest.raises(SystemExit):
        _require_loopback("localhost")
