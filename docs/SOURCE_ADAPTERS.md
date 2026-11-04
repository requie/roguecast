# Source adapters and trust boundaries

## Agentegrity v1 canonical events

Reference: [Universal Agent Event Contract](https://github.com/Cogensec/agentegrity/blob/main/docs/UNIVERSAL-AGENT-CONTRACT.md).

The adapter accepts canonical v1 **metadata only** and computes a five-minute
feature snapshot. Supported counts are `tool.intent` and denied `policy.verdict`
events. Fields unsupported by the canonical contract remain **missing**, not zero.

For a snapshot to be emitted, the caller must supply a set of event IDs whose
origin was independently authenticated by a trusted collection system.
An event's `source.assurance: authenticated` field is **not** proof of authentication.
Caller must also bind events to tenant, agent, run, and evidence reference, verify
signatures/transport and protect against replay. The sample adapter does not
make these security decisions; it only filters on verified receipt IDs.

Do not feed these snapshots to the training CLI directly. They have no
`followup_until`, `outcome_at` or independently verified `label`.
An adjudicated outcomes pipeline must join validated, horizon-complete
coverage and policy violation evidence before training.

CAAP observed-reference evaluations must remain a separate synthetic or
controlled-evaluation cohort. CAAP evidence attestation does not guarantee
that the subject actually produced the responses or that the evaluation was
authorized.

## Known gaps

- No production telemetry pulled and no data exported in this PR.
- No signed-receipt verifier or tenant-bound storage service yet.
- No policy-versioned label adjudication or censored-followup handling yet.
- No production training, calibration, or evaluation claims.
