from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from roguecast.labeling.cohort import build_cohort
from roguecast.model import FEATURES

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def ts(minutes):
    return (BASE + timedelta(minutes=minutes)).isoformat()


def snapshot(minute=10, session="s1"):
    row = {f: None for f in FEATURES}
    row.update(session_id=session, agent_id="agent-1", observed_at=ts(minute))
    return row


def coverage(start=0, end=60, verified=True, session="s1"):
    return dict(session_id=session, agent_id="agent-1", start_at=ts(start),
                end_at=ts(end), verified=verified)


def violation(at=20, status="independently_verified", session="s1"):
    return dict(session_id=session, agent_id="agent-1", violation_at=ts(at),
                evidence_id="evidence-1", policy_version="v1",
                verification_status=status, reviewer_id="reviewer-1")


def build(snaps=None, spans=None, outcomes=None):
    s = [snapshot()] if snaps is None else snaps
    c = [coverage()] if spans is None else spans
    v = [violation()] if outcomes is None else outcomes
    return build_cohort(pd.DataFrame(s), pd.DataFrame(c),
                        pd.DataFrame(v, columns=[
                            "session_id", "agent_id", "violation_at",
                            "evidence_id", "policy_version",
                            "verification_status", "reviewer_id"]))


def test_verified_positive():
    df, excluded = build()
    assert df.label.tolist() == [1]
    assert df.outcome_at.iloc[0] == ts(20)
    assert excluded.empty


def test_full_observation_negative():
    df, _ = build(outcomes=[])
    assert df.label.tolist() == [0]
    assert df.outcome_at.iloc[0] == ""


def test_incomplete_negative_is_censored():
    df, excluded = build(outcomes=[], spans=[coverage(end=30)])
    assert df.empty
    assert excluded.reason.tolist() == ["incomplete_followup"]


def test_gap_before_outcome_is_censored():
    df, excluded = build(spans=[coverage(0, 14), coverage(16, 60)])
    assert df.empty
    assert excluded.reason.tolist() == ["incomplete_followup"]


def test_adjacent_spans_are_continuous():
    df, _ = build(spans=[coverage(0, 15), coverage(15, 60)])
    assert df.label.tolist() == [1]


def test_unreviewed_violation_not_mislabeled_negative():
    df, excluded = build(outcomes=[violation(status="pending")])
    assert df.empty
    assert excluded.reason.tolist() == ["unresolved_outcome"]


def test_post_violation_observation_disallowed():
    df, excluded = build(snaps=[snapshot(21)])
    assert df.empty
    assert excluded.reason.tolist() == ["post_violation_snapshot"]


def test_unverified_coverage_does_not_count():
    df, excluded = build(spans=[coverage(verified=False)])
    assert df.empty
    assert excluded.reason.tolist() == ["incomplete_followup"]


def test_session_identity_conflict():
    bad = coverage()
    bad["agent_id"] = "another-agent"
    with pytest.raises(ValueError, match="identity conflict"):
        build(spans=[bad])


def test_missing_evidence_rejected():
    invalid = violation()
    invalid["evidence_id"] = None
    with pytest.raises(ValueError, match="missing evidence_id"):
        build(outcomes=[invalid])
