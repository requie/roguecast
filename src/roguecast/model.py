"""Leakage-aware tabular baseline with a chronological development/holdout split.

This is a research baseline. Do not interpret uncalibrated values as real-world risk.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

FEATURES = [
    "agent_type", "attack_surface", "tool_calls_5m", "denied_actions_5m",
    "untrusted_content_events_5m", "permission_scope_count",
    "external_egress_attempts_5m", "task_plan_deviation_count_5m",
]
CATEGORICAL = ["agent_type", "attack_surface"]
NUMERIC = [x for x in FEATURES if x not in CATEGORICAL]
REQUIRED = ["session_id", "observed_at", "followup_until", "outcome_at", "label", *FEATURES]


def validate(df: pd.DataFrame, horizon_minutes: int = 30) -> pd.DataFrame:
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("No observations")
    data = df.copy()
    # A malformed nonblank outcome is not evidence of a negative outcome.
    raw_outcome = data["outcome_at"]
    blank_outcome = raw_outcome.isna() | raw_outcome.astype(str).str.strip().eq("")
    for column in ("observed_at", "followup_until", "outcome_at"):
        data[column] = pd.to_datetime(data[column], utc=True, errors="coerce")
    if (data["outcome_at"].isna() & ~blank_outcome).any():
        raise ValueError("Unparseable nonempty outcome_at timestamp")
    if data["observed_at"].isna().any() or data["followup_until"].isna().any():
        raise ValueError("Invalid observed_at or followup_until timestamps")
    if not data["label"].isin([0, 1]).all():
        raise ValueError("Only fully observed binary labels are allowed; exclude censored examples")
    horizon = pd.Timedelta(minutes=horizon_minutes)
    positive = data["label"].eq(1)
    if (positive & (
        data["outcome_at"].isna()
        | (data["outcome_at"] <= data["observed_at"])
        | (data["outcome_at"] > data["observed_at"] + horizon)
    )).any():
        raise ValueError("Positive outcomes must occur strictly after observation and within horizon")
    if ((~positive) & (
        data["outcome_at"].notna()
        | (data["followup_until"] < data["observed_at"] + horizon)
    )).any():
        raise ValueError("Negative examples require no outcome and full horizon coverage")
    if data.duplicated(["session_id", "observed_at"]).any():
        raise ValueError("Duplicate session snapshots")
    for c in NUMERIC:
        data[c] = pd.to_numeric(data[c], errors="coerce")
        if (data[c].dropna() < 0).any():
            raise ValueError(f"Negative count in {c}")
    return data.sort_values("observed_at").reset_index(drop=True)


def split_chronological(data: pd.DataFrame, test_fraction: float = 0.25, horizon_minutes: int = 30):
    """Hold out newest sessions; purge sessions straddling split.

    Test starts after train's last snapshot + full outcome horizon.
    """
    if not 0 < test_fraction < 0.5:
        raise ValueError("test_fraction must be between 0 and 0.5")
    sessions = data.groupby("session_id")["observed_at"].min().sort_values()
    cut = max(1, min(len(sessions)-1, int(np.floor(len(sessions) * (1-test_fraction)))))
    if len(sessions) < 4:
        raise ValueError("Need at least four distinct sessions")
    cutoff = sessions.iloc[cut]
    train_sessions = set(sessions.iloc[:cut].index)
    test_sessions = set(sessions.iloc[cut:].index)
    purge_before = cutoff - pd.Timedelta(minutes=horizon_minutes)
    train = data[data["session_id"].isin(train_sessions) & (data["observed_at"] < purge_before)]
    test = data[data["session_id"].isin(test_sessions) & (data["observed_at"] >= cutoff)]
    if train.empty or test.empty:
        raise ValueError("Insufficient observations after temporal purge")
    if train["label"].nunique() < 2:
        raise ValueError("Train cohort must contain both classes")
    return train, test


def _categorical_object_dtype(values):
    """Allow string imputation when an entire categorical group is NaN float."""
    return values.astype(object)


def baseline() -> Pipeline:
    numeric = Pipeline([("impute", SimpleImputer(strategy="constant", fill_value=0, keep_empty_features=True)),
                        ("scale", StandardScaler())])
    categorical = Pipeline([("as_object", FunctionTransformer(_categorical_object_dtype)),
                            ("impute", SimpleImputer(strategy="constant", fill_value="unknown", keep_empty_features=True)),
                            ("onehot", OneHotEncoder(handle_unknown="ignore"))])
    return Pipeline([
        ("features", ColumnTransformer([
            ("num", numeric, NUMERIC), ("cat", categorical, CATEGORICAL)
        ])),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])


def metrics(y, scores):
    y = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=float)
    if len(y) == 0 or not np.isfinite(scores).all():
        raise ValueError("Invalid predictions")
    result = {
        "n": int(len(y)),
        "positives": int(y.sum()),
        "prevalence": float(y.mean()),
        "average_precision": float(average_precision_score(y, scores)) if y.sum() else None,
        "brier_score": float(brier_score_loss(y, scores)),
        "roc_auc": float(roc_auc_score(y, scores)) if len(set(y)) == 2 else None,
    }
    bins = pd.DataFrame({"y": y, "score": scores})
    bins["bin"] = pd.cut(bins["score"], bins=np.linspace(0, 1, 11), include_lowest=True)
    result["reliability"] = [
        {"bin": str(interval), "n": int(len(group)), "predicted": float(group.score.mean()),
         "observed": float(group.y.mean())}
        for interval, group in bins.groupby("bin", observed=True)
    ]
    return result


def run(input_path: str, output_path: str | None = None, horizon_minutes: int = 30):
    data = validate(pd.read_csv(input_path), horizon_minutes)
    train, test = split_chronological(data, horizon_minutes=horizon_minutes)
    model = baseline()
    model.fit(train[FEATURES], train["label"].astype(int))
    scores = model.predict_proba(test[FEATURES])[:, 1]
    report = {
        "status": "RESEARCH_ONLY_NOT_CALIBRATED",
        "horizon_minutes": horizon_minutes,
        "train_sessions": int(train.session_id.nunique()),
        "holdout_sessions": int(test.session_id.nunique()),
        "train_rows": int(len(train)),
        "holdout": metrics(test.label, scores),
        "note": "Incident-only samples and synthetic trials do not support deployment probability claims.",
    }
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "features": FEATURES, "horizon_minutes": horizon_minutes,
                     "status": "RESEARCH_ONLY_NOT_CALIBRATED"}, path)
    return report
