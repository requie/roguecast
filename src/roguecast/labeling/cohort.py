"""Join observation snapshots, verified violations and continuous coverage.

This pipeline does NOT adjudicate evidence. Evidence accepted here must already
be independently verified against an authoritative, versioned policy. Event
feeds (including Agentegrity) must not be permitted to mark their own violations.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
import pandas as pd

from roguecast.model import FEATURES, validate

SNAPSHOT_FIELDS = ("session_id", "agent_id", "observed_at", *FEATURES)
COVERAGE_FIELDS = ("session_id", "agent_id", "start_at", "end_at", "verified")
VIOLATION_FIELDS = (
    "session_id", "agent_id", "violation_at", "evidence_id",
    "policy_version", "verification_status", "reviewer_id",
)
APPROVED_STATUSES = {"independently_verified"}


def _require(frame: pd.DataFrame, fields: tuple[str, ...], name: str) -> pd.DataFrame:
    missing = set(fields).difference(frame.columns)
    if missing:
        raise ValueError(f"{name} missing columns: {sorted(missing)}")
    return frame.copy()


def _utc(frame: pd.DataFrame, columns: tuple[str, ...], name: str) -> pd.DataFrame:
    for col in columns:
        if frame[col].notna().any():
            raw = frame[col]
            parsed = pd.to_datetime(raw, utc=True, errors="coerce")
            if (parsed.isna() & raw.notna()).any():
                raise ValueError(f"{name} invalid {col}")
            frame[col] = parsed
        else:
            frame[col] = pd.to_datetime(frame[col], utc=True, errors="coerce")
    return frame


def _identity(frame: pd.DataFrame, name: str) -> None:
    for col in ("session_id", "agent_id"):
        if frame[col].isna().any() or frame[col].astype(str).str.strip().eq("").any():
            raise ValueError(f"{name} missing {col}")


def build_cohort(snapshots: pd.DataFrame, coverage: pd.DataFrame,
                 violations: pd.DataFrame, *, horizon_minutes: int = 30
                 ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (eligible labeled snapshots, exclusions with reason).

    Coverage is assumed to be a set of independently verified, continuous
    intervals. Adjacent/overlapping intervals merge; gaps censor the row.
    Violations are independent adjudications, not model predictions.
    A session is excluded after its first verified violation, so a single
    failure cannot become multiple future negative examples.
    """
    if not isinstance(horizon_minutes, int) or horizon_minutes <= 0:
        raise ValueError("horizon_minutes must be a positive integer")
    s = _utc(_require(snapshots, SNAPSHOT_FIELDS, "snapshots"),
             ("observed_at",), "snapshots")
    c = _utc(_require(coverage, COVERAGE_FIELDS, "coverage"),
             ("start_at", "end_at"), "coverage")
    v = _utc(_require(violations, VIOLATION_FIELDS, "violations"),
             ("violation_at",), "violations")
    for name, data in (("snapshots", s), ("coverage", c), ("violations", v)):
        _identity(data, name)
    if s["observed_at"].isna().any():
        raise ValueError("snapshots must have observed_at")
    if c[["start_at", "end_at"]].isna().any() or (c.end_at <= c.start_at).any():
        raise ValueError("coverage requires nonempty valid intervals")
    if v.violation_at.isna().any():
        raise ValueError("violations require violation_at")
    if v["verification_status"].isna().any():
        raise ValueError("violations require verification status")
    for field in ("evidence_id", "policy_version", "reviewer_id"):
        if v[field].isna().any() or v[field].astype(str).str.strip().eq("").any():
            raise ValueError(f"violations missing {field}")
    if s.duplicated(["session_id", "observed_at"]).any():
        raise ValueError("duplicate session snapshot timestamps")
    # A session identifier must not switch agent identities.
    for name, data in (("snapshots", s), ("coverage", c), ("violations", v)):
        if (data.groupby("session_id", dropna=False)["agent_id"].nunique() > 1).any():
            raise ValueError(f"{name}: session mapped to multiple agents")
    all_ids = pd.concat([
        s[["session_id", "agent_id"]],
        c[["session_id", "agent_id"]],
        v[["session_id", "agent_id"]],
    ])
    if (all_ids.groupby("session_id", dropna=False)["agent_id"].nunique() > 1).any():
        raise ValueError("cross-source session identity conflict")
    # Never turn an unreviewed, disputed or self-reported violation into a negative.
    for col in ("verified",):
        if not c[col].isin([True, False]).all():
            raise ValueError("coverage verified must be boolean")
    unknown = v[~v.verification_status.isin(APPROVED_STATUSES)]
    verified = v[v.verification_status.isin(APPROVED_STATUSES)].copy()
    horizon = timedelta(minutes=horizon_minutes)
    rows: list[dict] = []
    exclusions: list[dict] = []
    for _, snap in s.sort_values("observed_at").iterrows():
        sid, agent, at = snap.session_id, snap.agent_id, snap.observed_at
        end = at + horizon
        reason = None
        # Pending/disputed outcomes in the prediction horizon require review,
        # even if subsequent adjudications exist.
        if ((unknown.session_id == sid)
            & (unknown.violation_at > at)
            & (unknown.violation_at <= end)).any():
            reason = "unresolved_outcome"
        confirmed = verified[verified.session_id == sid].sort_values("violation_at")
        first = confirmed.iloc[0] if not confirmed.empty else None
        if first is not None and at >= first.violation_at:
            reason = "post_violation_snapshot"
        # A snapshot with any earlier confirmed failure is not a clean at-risk
        # episode unless a separate run/session ID is established.
        if first is not None and at < first.violation_at <= end:
            target = first.violation_at
        else:
            target = end
        intervals = c[(c.session_id == sid) & (c.verified == True)
                      & (c.start_at <= target) & (c.end_at >= at)]
        # Support contiguous intervals through the exact target timestamp.
        spans = c[(c.session_id == sid) & (c.verified == True)
                  & (c.end_at >= at) & (c.start_at <= target)].sort_values("start_at")
        cursor = at
        for _, span in spans.iterrows():
            if span.start_at > cursor:
                break
            if span.end_at > cursor:
                cursor = span.end_at
        if cursor < target:
            reason = reason or "incomplete_followup"
        if reason:
            exclusions.append({"session_id": sid, "observed_at": at.isoformat(),
                               "reason": reason})
            continue
        positive = first is not None and at < first.violation_at <= end
        record = {f: snap[f] for f in FEATURES}
        record.update({
            "session_id": sid, "observed_at": at.isoformat(),
            "followup_until": cursor.isoformat(),
            "outcome_at": first.violation_at.isoformat() if positive else "",
            "label": int(positive),
        })
        rows.append(record)
    columns = ["session_id", "observed_at", "followup_until", "outcome_at",
               "label", *FEATURES]
    eligible = pd.DataFrame(rows, columns=columns)
    if not eligible.empty:
        validate(eligible, horizon_minutes=horizon_minutes)
    return eligible, pd.DataFrame(exclusions, columns=["session_id", "observed_at", "reason"])


def from_csv(snapshot_path: str | Path, coverage_path: str | Path,
             violation_path: str | Path, horizon_minutes: int = 30
             ) -> tuple[pd.DataFrame, pd.DataFrame]:
    return build_cohort(pd.read_csv(snapshot_path), pd.read_csv(coverage_path),
                        pd.read_csv(violation_path), horizon_minutes=horizon_minutes)
