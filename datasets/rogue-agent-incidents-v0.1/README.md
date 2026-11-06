---
pretty_name: Cogensec Rogue Agent Incident Reference Set
language:
- en
tags:
- ai-security
- agentic-security
- rogue-agents
- incident-analysis
- provenance
license: other
license_name: source-specific-review-required
task_categories:
- text-classification
size_categories:
- n<1K
---
# Cogensec Rogue Agent Incident Reference Set (v0.1)

**Status: review-stage research artifact, not published on Hugging Face.** This candidate release contains **25** source-linked records extracted from two public Cogensec database migrations. The rows were explicitly marked `published` in those seed files, but neither their claims nor the live database status have been independently rechecked. Do not treat the set as 25 independently verified real-world rogue-agent episodes.

## What the records contain
Editorial incident titles, summaries, descriptions of failure mechanisms and impacts, source links, dates and curated categorizations. Every record includes its exact GitHub source file and source blob SHA. `verification_status` is explicit and `attack_success_verified` is false to indicate **no independent outcome verification by this release**, not evidence that attacks failed.

## Recommended uses
Retrieval-augmented incident research, taxonomy comparison, incident triage annotation pilots, evidence reconciliation, and building reviewer workflows. Labels `category_as_curated` and `severity_as_curated` are original editorial values, not gold truth. Audit and source-check each record before using it as an evaluation target.

## Not supported
Do **not** use this set to estimate rates of rogue behavior, calibrate a probability of misalignment, claim attack success, train a reliable behavioral precursor detector, or evaluate autonomous control systems. It has no ordinary-operation denominator, no direct tool-call trajectories, no verified safe controls, no model response traces, and no deployment- or task-group holdout. This is not a train/validation/test benchmark; each row has `split=reference_only`.

## Curation and provenance
Sources: [initial registry seed](https://github.com/requie/cogensec/blob/main/supabase/migrations/20260430230608_857968b4-ecd9-4e77-ae87-a6ab273d0175.sql) and [subsequent incident seed](https://github.com/requie/cogensec/blob/main/supabase/migrations/20260609160157_b4766f05-c93e-4e1d-9302-5d546bdf305b.sql). The registry includes research scenarios as well as publicly reported incidents; distinguish simulated studies from actual deployment failures before stronger claims. Excluded the July 2026 backlog because its rows were explicitly `pending` analyst review. Data was extracted mechanically from the migration `VALUES` statements. URL presence does not establish validity, license or continued availability.

## Licensing and access
**License unresolved.** Source summaries and derived annotations require a provenance, redistribution and rights audit before public Hugging Face release. This repository file is a preparation artifact, not authorization to redistribute third-party reports. Do not apply Apache-2.0 or CC-BY by assumption.

## Fields
`record_id`, `case_group`, `incident_title`, `reported_summary`, `reported_mechanism`, `reported_impact`, `source_url`, `source_name`, `incident_date`, `category_as_curated`, `severity_as_curated`, `agent_type`, `attack_surface`, `affected_vendor`, `evidence_type`, `verification_status`, `behavior_observed_directly`, `agent_action_trace_available`, `attack_success_verified`, `synthetic`, `label_provenance`, `risk_score`, `split`, `source_repository`, `source_path`, `source_blob_sha`.

## Publication gates
1. Validate every link and reconcile cases representing the same underlying episode. 2. Confirm publication rights and data minimization. 3. Human-review source type (simulation vs incident), event identity, evidence, category and severity. 4. Remove speculative claims. 5. Add independent adjudicators and quality statistics. 6. Release only after account write authorization and explicit dataset version approval.

## Citation
Cogensec. (2026). *Rogue Agent Incident Reference Set*, candidate v0.1. Source repository: https://github.com/requie/cogensec. **Not a validated behavior benchmark.**
