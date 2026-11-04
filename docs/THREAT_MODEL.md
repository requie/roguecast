# Threat model

## Assets
Agent telemetry, policy definitions, labels, training process, model artifacts, risk decisions and the human reviewer workflow.

## Adversaries and failure modes
- Telemetry poisoning and forged event timestamps.
- Training labels influenced by the monitored agent or unreviewed incident extraction.
- Leakage from post-incident narratives, severity, disclosure, mitigations or overlapping sessions.
- Model evasion by changing action frequency or splitting tasks across sessions.
- Agent identity or session spoofing; cross-tenant data exposure.
- Distribution shift across model vendors, tools and deployments.
- Risk score laundering into unsupported claims of probability or automatic punitive actions.

## Controls
Independent signed event trails; timestamp verification; provenance and human adjudication; session/deployment holdouts; feature allowlists; schema checks; access controls; shadow-mode rollouts; monitored drift; fail-open-to-human-review for unreliable predictions. Never trust an agent's self-report as the sole ground truth.
