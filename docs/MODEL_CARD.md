# RogueCast model card

**Version:** 0.1.0, research baseline, not fitted or validated in repository.

**Intended use:** Study whether pre-event agent telemetry is predictive of a verified authorization-boundary violation over 30 minutes. Support analyst review, never automatic enforcement.

**Not intended for:** Claims that an agent has intent, irreversible action blocking, employee surveillance, ranking vendors by safety, or production risk probability without externally validated calibration.

**Algorithm:** Median-imputed numeric features, one-hot encoded categorical metadata, logistic regression. Chronological session-disjoint split with horizon purge. No randomized split.

**Required external evaluation before deployment:** representative negatives and class prevalence; temporal and deployment holdouts; calibration curve, Brier score, PR-AUC, alert precision at fixed review budget, subgroup performance, drift, false-positive cost, label quality, independent audit. A calibration set must be separate from training and final holdout.

**Known limitations:** Registry contains selected newsworthy failures, not random deployed sessions. Discovery and synthetic records are selection-biased. Some features are subjective and require instrumentation definitions. Rare-event prediction may fail under domain shift. At this stage all scores are research outputs, not calibrated probabilities.

**Release gate:** No production claim until reproducible validation, calibration and review are documented with artifact hashes and representative data lineage.
