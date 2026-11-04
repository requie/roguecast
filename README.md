# RogueCast

**Research-stage predictive risk modeling for autonomous AI agents.**

RogueCast estimates whether a defined *authorization-boundary violation* will occur within a specified future horizon, conditional on information available at prediction time. It is **not** an intent detector, and there is currently **no validated production probability model**.

## Sources and limits

- [Cogensec Agents Gone Rogue registry](https://github.com/requie/cogensec/tree/main/src/components/rogue-registry): curated, published incidents and taxonomies, useful for event definitions and case studies, **not** a denominator of ordinary agent activity.
- [Registry SQL](https://github.com/requie/cogensec/blob/main/supabase/migrations/20260528120000_rogue_registry_schema.sql): AGIR identifiers, agent types, attack surfaces and controls.
- [Review lane](https://github.com/requie/cogensec/blob/main/supabase/migrations/20260731100000_rogue_review_lane.sql): pending/published/hidden curation states.
- [Cogensec dataset catalog](https://github.com/requie/cogensec/blob/main/src/data/datasets.ts): attack prompts and reasoning records with distinct labeling limitations. Do not label jailbreak prompts as successful agent violations.
- Future connectors: Agentegrity runtime events and CAAP/Aversyn controlled evaluations. These are **not** automatically available from this repository.

## Outcome contract

One example is one agent-session snapshot at time `t`. Label `1` only if a verified, predefined authorization-boundary violation occurs in `(t, t + horizon]`. Label `0` only if observation coverage extends through the full horizon with no violation. Incomplete follow-up is **censored**, not negative. Observations or labels after `t` must never become features.

The initial task is `P(verified violation in next 30 minutes | information at t)`. Risk scores must not be reported as probabilities until assessed against independently collected real-world sessions with a representative base rate and documented calibration.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest
roguecast train --input path/to/approved_snapshots.csv --output private_artifacts/model.joblib
roguecast evaluate --input path/to/approved_snapshots.csv --output private_artifacts/evaluation.json
```

See [data contract](docs/DATA_CONTRACT.md), [model card](docs/MODEL_CARD.md), and [threat model](docs/THREAT_MODEL.md). No private data, secrets or trained models belong in Git.

## Governance

- Research only. Do not automatically block agent actions from this model.
- Consent and authorization are required to ingest telemetry.
- Keep training and evaluation cohorts separate by agent/deployment and time.
- Report PR-AUC, baseline prevalence, Brier score, reliability bins, precision/recall at fixed alert budgets, and uncertainty.
- Avoid training on incident severity, disclosure dates, labels or controls derived after the event.
