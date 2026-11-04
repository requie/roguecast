from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from roguecast.model import FEATURES, metrics, split_chronological, validate


def row(session, minute, positive=False):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=2 * session)
    t = base + timedelta(minutes=minute)
    return dict(session_id=str(session), observed_at=t.isoformat(),
                followup_until=(t + timedelta(minutes=30)).isoformat(),
                outcome_at=(t + timedelta(minutes=5)).isoformat() if positive else None,
                label=int(positive), agent_type="coding", attack_surface="tool",
                tool_calls_5m=2, denied_actions_5m=0,
                untrusted_content_events_5m=0, permission_scope_count=1,
                external_egress_attempts_5m=0, task_plan_deviation_count_5m=0)


def test_requires_full_negative_followup():
    df = pd.DataFrame([row(1, 0)])
    df.loc[0, "followup_until"] = df.loc[0, "observed_at"]
    with pytest.raises(ValueError, match="full horizon"):
        validate(df)


def test_rejects_future_positive_outcome():
    r = row(1, 0, True)
    r["outcome_at"] = (pd.Timestamp(r["observed_at"]) + pd.Timedelta(hours=2)).isoformat()
    with pytest.raises(ValueError, match="within horizon"):
        validate(pd.DataFrame([r]))


def test_split_is_session_disjoint():
    df = validate(pd.DataFrame([row(i, 0, i % 2 == 0) for i in range(12)]))
    train, test = split_chronological(df)
    assert set(train.session_id).isdisjoint(set(test.session_id))
    assert train.observed_at.max() < test.observed_at.min()


def test_metrics_handle_one_class():
    m = metrics([0, 0], [0.1, 0.3])
    assert m["roc_auc"] is None
    assert m["prevalence"] == 0.0
