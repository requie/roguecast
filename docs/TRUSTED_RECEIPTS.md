# Trusted collector receipt protocol (v1)

A preconfigured, trusted collector signs the SHA-256 digest of the exact
canonical Agentegrity event JSON, tenant ID, issuer, agent ID, run ID, event
ID and bounded validity period using HMAC-SHA256. This is a **collector
attestation**, not an attestation from the agent.

## Usage

`sign_receipt` must run only in an authenticated, tenant-bound collector.
`verify_receipt` is used by the feature service with the correct trusted
collector key obtained out of band. `verified_snapshot` requires every
event to have a matching receipt, then aggregates only events within its
five-minute pre-observation window.

No secret or real telemetry is stored in this repository.

## Production restrictions

- Provision a separate high-entropy key per tenant and issuer in a secret
  manager, never an agent-accessible environment or untrusted request body.
- This is an offline reference implementation, **not** an authentication API.
- Authenticate the upstream transport and operator, authorize the tenant,
  bind key IDs to a versioned rotation policy, and enforce payload size limits.
- Implement a durable atomic replay ledger keyed by tenant + issuer +
  event ID and signature, with an explicit retention policy. In-memory
  duplicate checks only protect an individual batch.
- Enforce ingestion freshness and collector clock synchronization, and
  retain independently validated collection completeness.
- HMAC authenticates the collector's assertion, not the truth of reported
  actions or the completeness of observation. Compromise of the collector
  or key compromises the receipts.
- Use signed receipts only to build UNLABELED snapshots. A separate independent
  process must verify outcomes, policy versions and continuous follow-up.
- Do not use the result as a production probability prediction until
  independent cohort validation and calibration are complete.
