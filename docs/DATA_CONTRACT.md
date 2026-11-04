# Training data contract (v0.1)

**One row = one agent-session snapshot**, at the exact time at which the prediction would have been made. Require all rows to have independently verifiable source and timestamp lineage.

## Required columns

- `session_id`: stable pseudonymous session identifier; hold out entire sessions during validation.
- `observed_at`: UTC observation cutoff; only features known at or before this time may be used.
- `followup_until`: UTC last verified observation time.
- `outcome_at`: UTC time of independently verified authorization-boundary violation, or blank.
- `label`: 1 for verified violation strictly within 30 minutes after snapshot; 0 for *complete* negative follow-up. Do not include censored or unknown examples.
- `agent_type`, `attack_surface`: categorical values from the Cogensec registry taxonomy when known.
- `tool_calls_5m`, `denied_actions_5m`, `untrusted_content_events_5m`, `permission_scope_count`, `external_egress_attempts_5m`, `task_plan_deviation_count_5m`: nonnegative values recorded before `observed_at`. Missing values are allowed but **missing is not zero**.

## Label verification

An incident must have a specific agent, prohibited action, policy version, action timestamp and independent evidence. Prompt injection attempts, published reports, synthetic attack patterns and high severity do not themselves prove a violation. Count harmless rejected tool attempts as risk signals, not positives. Repeated snapshots from the same underlying incident must be grouped in evaluation.

## Data provenance / sampling

Track separately (outside training CSV): `source_system`, `event_id`, `deployment_id`, `policy_version`, `capture_window`, `reviewer`, `verification_status`, `synthetic`, `consent_basis`, `dataset_version`, `schema_version`.

Never combine simulated CAAP attacks, public incident narratives and production telemetry into one probabilistic cohort without stratified evaluation, documented sampling and a representative deployment base rate.

No post-incident severity, impact, mitigation, reviewer judgments, disclosure date, or future telemetry may be used as predictors.

## Privacy

Allowlisted structured aggregates only. Do not ingest prompt content, secrets, raw tool arguments or personal data by default. Retain sensitive evidence in access-controlled storage outside the repository.
