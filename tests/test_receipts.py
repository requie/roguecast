from datetime import datetime, timedelta, timezone

import pytest

from roguecast.ingestion.receipts import (
    event_digest, sign_receipt, verify_receipt, verified_snapshot,
)

KEY = b"trusted-collector-secret-is-32-bytes-minimum-for-tests"
NOW = "2026-01-01T00:04:00+00:00"
ISSUED = "2026-01-01T00:03:30+00:00"
EXPIRES = "2026-01-01T00:10:00+00:00"


def event(event_id="event-1"):
    return {
        "schema_version": "1.0", "event_id": event_id, "event_type": "tool.intent",
        "occurred_at": "2026-01-01T00:03:00Z", "agent_id": "agent-1",
        "run_id": "run-1",
        "source": {"host": "host", "integration": "sdk", "assurance": "unverified"},
    }


def receipt(e):
    return sign_receipt(e, tenant_id="tenant-a", issuer="collector-a",
                        key=KEY, issued_at=ISSUED, expires_at=EXPIRES)


def verify(e, r, **kw):
    return verify_receipt(e, r, tenant_id=kw.get("tenant_id", "tenant-a"),
                          issuer="collector-a", key=KEY, at=kw.get("at", NOW))


def test_valid_signed_snapshot_has_no_labels():
    e = event()
    result = verified_snapshot([e], [receipt(e)], tenant_id="tenant-a",
                               issuer="collector-a", key=KEY,
                               observed_at=NOW, run_id="run-1")
    assert result["tool_calls_5m"] == 1
    assert result["tenant_id"] == "tenant-a"
    assert "label" not in result


def test_rejects_tampered_event():
    e = event()
    r = receipt(e)
    e["event_type"] = "policy.verdict"
    with pytest.raises(ValueError, match="digest mismatch"):
        verify(e, r)


def test_rejects_cross_tenant_receipt():
    e = event()
    with pytest.raises(ValueError, match="scope mismatch"):
        verify(e, receipt(e), tenant_id="tenant-b")


def test_rejects_forged_signature():
    e = event()
    r = receipt(e)
    r["signature"] = "0" * 64
    with pytest.raises(ValueError, match="signature"):
        verify(e, r)


def test_rejects_expired_receipt():
    e = event()
    with pytest.raises(ValueError, match="expired"):
        verify(e, receipt(e), at="2026-01-01T01:00:00+00:00")


def test_rejects_duplicate_event():
    e = event()
    r = receipt(e)
    with pytest.raises(ValueError, match="Duplicate"):
        verified_snapshot([e, e], [r, r], tenant_id="tenant-a",
                          issuer="collector-a", key=KEY,
                          observed_at=NOW, run_id="run-1")


def test_rejects_missing_receipt():
    with pytest.raises(ValueError, match="one receipt"):
        verified_snapshot([event()], [], tenant_id="tenant-a",
                          issuer="collector-a", key=KEY,
                          observed_at=NOW, run_id="run-1")


def test_rejects_wrong_run():
    e = event()
    with pytest.raises(ValueError, match="Unexpected run"):
        verified_snapshot([e], [receipt(e)], tenant_id="tenant-a",
                          issuer="collector-a", key=KEY,
                          observed_at=NOW, run_id="run-2")


def test_rejects_short_key():
    with pytest.raises(ValueError, match="32 bytes"):
        sign_receipt(event(), tenant_id="tenant-a", issuer="collector-a",
                     key=b"short", issued_at=ISSUED, expires_at=EXPIRES)


def test_rejects_event_after_receipt():
    e = event()
    e["occurred_at"] = "2026-01-01T00:06:00Z"
    with pytest.raises(ValueError, match="after receipt"):
        verify(e, receipt(e))


def test_digest_ignores_mapping_key_order():
    a = event()
    b = dict(reversed(list(a.items())))
    assert event_digest(a) == event_digest(b)
