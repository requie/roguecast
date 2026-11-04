import pytest

from roguecast.ingestion.agentegrity import normalize, snapshot


def event(event_id="e1", event_type="tool.intent", occurred_at="2026-01-01T00:03:00Z",
          outcome=None):
    return {
        "schema_version": "1.0", "event_id": event_id, "event_type": event_type,
        "occurred_at": occurred_at, "agent_id": "agent-1", "run_id": "run-1",
        "source": {"host": "trusted-gateway", "integration": "sdk",
                   "assurance": "authenticated", "evidence_ref": "r1"},
        **({"outcome": outcome} if outcome else {}),
    }


def test_does_not_trust_self_reported_source_assurance():
    with pytest.raises(ValueError, match="independently verified"):
        snapshot([event()], "2026-01-01T00:04:00Z", "run-1")


def test_counts_verified_pre_event_metadata_only():
    rows = [
        event(), event("e2", "policy.verdict", "2026-01-01T00:03:20Z", "denied"),
        event("future", "tool.intent", "2026-01-01T00:06:00Z"),
    ]
    s = snapshot(rows, "2026-01-01T00:04:00Z", "run-1",
                 verified_receipts={"e1", "e2", "future"})
    assert s["tool_calls_5m"] == 1
    assert s["denied_actions_5m"] == 1
    assert s["permission_scope_count"] is None
    assert "label" not in s


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="Duplicate"):
        normalize([event(), event()])


def test_timezone_required():
    with pytest.raises(ValueError, match="UTC"):
        normalize([event(occurred_at="2026-01-01T00:03:00")])


def test_mixed_agent_identity_rejected():
    other = event("e2")
    other["agent_id"] = "another-agent"
    with pytest.raises(ValueError, match="Mixed agent"):
        snapshot([event(), other], "2026-01-01T00:04:00Z",
                 "run-1", verified_receipts={"e1", "e2"})
