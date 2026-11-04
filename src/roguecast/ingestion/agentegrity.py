"""Ingest Agentegrity canonical metadata-only events (schema v1).

Output is an UNLABELED feature snapshot, never a training row. The event's
source.assurance is a claim, not cryptographic authentication; the caller must
verify tenant, issuer, transport, evidence, and authorization independently.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from roguecast.model import FEATURES

SUPPORTED_TYPES = {"tool.intent", "tool.result", "policy.verdict"}
DENIAL_OUTCOMES = {"deny", "denied", "blocked", "rejected"}


def _when(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith(("Z", "+00:00")):
        raise ValueError("occurred_at must be explicit UTC")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0):
        raise ValueError("occurred_at must be UTC")
    return stamp


def normalize(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fail closed on malformed or untrusted event metadata.

    Authentication is explicitly external: verified_receipts must be supplied
    by trusted collection infrastructure, not copied from the event payload.
    """
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        if not isinstance(event, dict) or event.get("schema_version") != "1.0":
            raise ValueError("Expected canonical event schema 1.0")
        for field in ("event_id", "agent_id", "run_id", "event_type", "occurred_at"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                raise ValueError(f"Missing event field: {field}")
        source = event.get("source")
        if not isinstance(source, dict) or not isinstance(source.get("host"), str):
            raise ValueError("Missing host source")
        key = (event["run_id"], event["event_id"])
        if key in seen:
            raise ValueError("Duplicate event ID within run")
        seen.add(key)
        clean = {k: event.get(k) for k in (
            "event_id", "event_type", "agent_id", "run_id", "session_id",
            "action_id", "tool_name", "effect", "outcome",
        )}
        clean["occurred_at"] = _when(event["occurred_at"])
        clean["source_host"] = source["host"]
        clean["assurance_claim"] = source.get("assurance", "unverified")
        normalized.append(clean)
    return sorted(normalized, key=lambda e: e["occurred_at"])


def snapshot(events: Iterable[dict[str, Any]], observed_at: str, run_id: str,
             *, verified_receipts: set[str] | None = None) -> dict[str, Any]:
    """Aggregate the preceding five minutes of independently verified events.

    Caller must provide event IDs verified by its trusted ingestion boundary.
    No positive or negative labels or outcome time can be derived here.
    """
    at = _when(observed_at)
    receipts = verified_receipts or set()
    records = normalize(events)
    eligible = [e for e in records if e["run_id"] == run_id
                and e["event_id"] in receipts
                and at - timedelta(minutes=5) < e["occurred_at"] <= at]
    if not eligible:
        raise ValueError("No independently verified events in observation window")
    agents = {e["agent_id"] for e in eligible}
    if len(agents) != 1:
        raise ValueError("Mixed agent identities in run")
    result: dict[str, Any] = {
        "session_id": eligible[0].get("session_id") or run_id,
        "observed_at": at.isoformat(),
        "agent_id": eligible[0]["agent_id"],
        "source_system": "agentegrity-canonical-v1",
        "verified_event_count": len(eligible),
        "agent_type": None,
        "attack_surface": None,
        "tool_calls_5m": sum(e["event_type"] == "tool.intent" for e in eligible),
        "denied_actions_5m": sum(
            e["event_type"] == "policy.verdict"
            and str(e.get("outcome") or "").lower() in DENIAL_OUTCOMES
            for e in eligible
        ),
        "untrusted_content_events_5m": None,
        "permission_scope_count": None,
        "external_egress_attempts_5m": None,
        "task_plan_deviation_count_5m": None,
    }
    assert set(FEATURES).issubset(result)
    return result


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read authorized JSONL; caller handles access control and retention."""
    with open(path, encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]
