"""HMAC-authenticated collector receipts for canonical Agentegrity events.

Trust boundary: trusted, tenant-scoped collector creates receipts, with secrets
provisioned out of band. This verifies collector attestation of event bytes,
NOT the truth of an agent action or a policy violation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from roguecast.ingestion.agentegrity import _when, snapshot


FIELDS = ("version", "issuer", "tenant_id", "event_id", "run_id", "agent_id",
          "event_sha256", "issued_at", "expires_at")
MAX_AGE = timedelta(hours=1)


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _required_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Invalid {name}")
    return value


def event_digest(event: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(event)).hexdigest()


def _mac(payload: Mapping[str, Any], key: bytes) -> str:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Collector HMAC key must be at least 32 bytes")
    return hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()


def sign_receipt(event: Mapping[str, Any], *, tenant_id: str, issuer: str,
                 key: bytes, issued_at: str, expires_at: str) -> dict[str, str]:
    """For use ONLY inside authenticated trusted collector infrastructure."""
    start, end = _when(issued_at), _when(expires_at)
    if end <= start or end - start > MAX_AGE:
        raise ValueError("Invalid receipt validity interval")
    payload = {
        "version": "1", "issuer": _required_string(issuer, "issuer"),
        "tenant_id": _required_string(tenant_id, "tenant_id"),
        "event_id": _required_string(event.get("event_id"), "event_id"),
        "run_id": _required_string(event.get("run_id"), "run_id"),
        "agent_id": _required_string(event.get("agent_id"), "agent_id"),
        "event_sha256": event_digest(event),
        "issued_at": start.isoformat(), "expires_at": end.isoformat(),
    }
    return {**payload, "signature": _mac(payload, key)}


def verify_receipt(event: Mapping[str, Any], receipt: Mapping[str, Any], *,
                   tenant_id: str, issuer: str, key: bytes, at: str) -> str:
    """Verify receipt MAC and bind every identity to canonical event bytes."""
    if not isinstance(receipt, Mapping) or set(receipt) != set(FIELDS) | {"signature"}:
        raise ValueError("Invalid receipt fields")
    if receipt["version"] != "1" or receipt["tenant_id"] != tenant_id or receipt["issuer"] != issuer:
        raise ValueError("Receipt scope mismatch")
    for field in ("event_id", "run_id", "agent_id"):
        if receipt[field] != event.get(field):
            raise ValueError(f"Receipt {field} mismatch")
    if not hmac.compare_digest(str(receipt["event_sha256"]), event_digest(event)):
        raise ValueError("Receipt event digest mismatch")
    signed = {name: receipt[name] for name in FIELDS}
    expected = _mac(signed, key)
    signature = receipt["signature"]
    if not isinstance(signature, str) or not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid receipt signature")
    now, start, end = _when(at), _when(receipt["issued_at"]), _when(receipt["expires_at"])
    if not start <= now < end or end <= start or end - start > MAX_AGE:
        raise ValueError("Receipt expired or not yet valid")
    # Event must predate attestation, allowing small trusted-clock skew.
    occurred = _when(event["occurred_at"])
    if occurred > start + timedelta(minutes=2):
        raise ValueError("Event occurred after receipt issuance")
    return event["event_id"]


def verified_snapshot(events: Sequence[dict[str, Any]],
                      receipts: Sequence[dict[str, Any]], *,
                      tenant_id: str, issuer: str, key: bytes,
                      observed_at: str, run_id: str) -> dict[str, Any]:
    """Generate a snapshot only from events with tenant-bound valid receipts.

    Receipt issuance alone cannot establish continuous observation coverage or
    independently verified incident outcomes.
    """
    if len(events) != len(receipts):
        raise ValueError("Require exactly one receipt per supplied event")
    verified: set[str] = set()
    for event, receipt in zip(events, receipts):
        if event.get("run_id") != run_id:
            raise ValueError("Unexpected run_id in event batch")
        event_id = verify_receipt(event, receipt, tenant_id=tenant_id,
                                  issuer=issuer, key=key, at=observed_at)
        if event_id in verified:
            raise ValueError("Duplicate receipt event_id")
        verified.add(event_id)
    result = snapshot(events, observed_at, run_id, verified_receipts=verified)
    result["tenant_id"] = tenant_id
    result["receipt_scheme"] = "hmac-sha256-v1"
    return result
