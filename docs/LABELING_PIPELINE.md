# Outcome labeling and censoring

RogueCast turns **approved pre-event snapshots** into labels only when a separate
trusted reviewer has adjudicated an authorization-boundary violation and the
collection system supplies independently verified, continuous observation
coverage.

The pipeline consumes three separate tables:

1. **Snapshots**: `session_id`, `agent_id`, `observed_at`, plus the
   allowlisted pre-event fields in `roguecast.model.FEATURES`.
2. **Coverage intervals**: `session_id`, `agent_id`, `start_at`, `end_at`,
   `verified` (true only for independently verified continuous recording).
3. **Violation adjudications**: `session_id`, `agent_id`,
   `violation_at`, `evidence_id`, `policy_version`,
   `verification_status`, `reviewer_id`.

All timestamps must be parseable; the horizon defaults to 30 minutes.
A confirmed violation has `verification_status=independently_verified`.
A negative label requires uninterrupted verified coverage through the horizon.
A positive requires verified coverage through the violation time. A missing
coverage interval, unresolved outcome, or post-violation snapshot is **excluded**
with its reason recorded.

```python
from roguecast.labeling.cohort import from_csv

trainable, exclusions = from_csv(
    "private/snapshots.csv", "private/coverage.csv",
    "private/reviewed_violations.csv"
)
# Store trainable and exclusions only in protected access-controlled storage.
```

## Important operational restrictions

- Adjudications must originate outside the monitored agent.
- Evidence identifiers are references, **not** cryptographic validation.
  The producer must verify evidence signatures, reviewer authority, policy
  versions, tenant and session identities before calling this library.
- Event timestamp correctness and collection completeness are asserted by the
  upstream trusted collection service; a row supplied to this function does not
  itself establish either.
- Pending or disputed outcomes are not auto-negatives.
- Use session- and deployment-isolated temporal splits for final evaluation.
- No incident registry narratives, synthetic test results or attack prompts
  are automatically assigned production outcomes.
- Do not commit private inputs, pseudonymous tracking maps or labeled exports.
