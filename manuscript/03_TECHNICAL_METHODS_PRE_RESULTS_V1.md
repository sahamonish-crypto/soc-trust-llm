# 3. Technical Methodology

**Draft status:** PRE-RESULTS / GATE 6D OPEN  
**Scope:** Frozen technical design only. Pending DEV/EVAL outcomes are not reported here.

## 3.1 Experimental Separation and Evaluation Boundaries

The technical evaluation was designed prospectively to separate model selection, uncertainty-estimator development, calibration, untouched evaluation, human-subject evaluation, and external testing. This separation was used to reduce information leakage and post-hoc adaptation.

Gate 6C was used for LLM configuration selection. Gate 6D was reserved for uncertainty estimation and calibration. Data used for Gate 6C model selection were excluded from Gate 6D calibration development and evaluation.

Within Gate 6D, the calibration data were divided into development (DEV) and untouched evaluation (EVAL) partitions. Human-study items constitute a separate downstream evidence pool and are not used to select or calibrate the technical confidence mechanism. External TEST captures are also kept separate and remain untouched during calibration development and EVAL.

The resulting hierarchy is therefore:

1. model-selection benchmark;
2. calibration DEV;
3. untouched calibration EVAL;
4. later human-study material;
5. external TEST.

No EVAL outcome is used to fit, select, or revise an uncertainty estimator or calibration mapping.

## 3.2 Canonical Alert Inputs and Leakage Controls

Gate 6D inputs were constructed from canonical SOC alert representations under a frozen source-binding procedure. Only alerts satisfying the required rich-context criterion were eligible for calibration analysis.

The original eligible Gate 6D pool contained:

- 1,222 DEV alerts; and
- 458 untouched EVAL alerts.

The DEV data were drawn from the frozen AmazonEcho and Windows7AD source partitions, while the EVAL partition consisted of the frozen Windows7AD evaluation capture. Alert identifiers and manifests were generated prospectively and cryptographically hash-bound before calibration analysis.

A dedicated alert-card validity audit was performed before uncertainty estimation. The audit found no direct ground-truth leakage in the 1,680 eligible DEV+EVAL alert cards. A small number of alerts contained high-specificity lexical cues that could correlate with attack status. These alerts were retained rather than retrospectively removed or masked, and this limitation is treated as a validity caveat rather than corrected after inspection.

Gate 6C benchmark items were excluded from Gate 6D calibration data. The external TEST captures were not used for model selection, uncertainty development, calibration, or calibration EVAL.

## 3.3 Resource-Constrained DEV Subsample

Because repeated stochastic inference substantially increases model-call requirements, the frozen 1,222-item DEV pool was prospectively reduced to a 500-item calibration-development subset under a zero-budget resource amendment.

The DEV500 subset was selected without using prediction correctness, model outcomes, confidence scores, or ground-truth labels. Selection preserved all 48 frozen capture/episode groups and used proportional allocation with largest remainders.

Within each group, alerts were ranked deterministically using a SHA-256 function of the item identifier. The resulting DEV500 subset contained:

- 500 alerts;
- all 48 capture/episode groups;
- 122 AmazonEcho alerts; and
- 378 Windows7AD alerts.

The five frozen grouped cross-validation folds contained 97, 101, 102, 98, and 102 items, respectively.

The untouched EVAL set was not reduced and remains fixed at 458 items.

## 3.4 Model Configuration

Model configuration selection was completed prospectively in Gate 6C before calibration development. Three zero-budget candidate configurations were evaluated using the frozen canonical benchmark over three repeated runs per candidate.

The model-selection protocol, candidate outputs, scorer, and tiebreak rules were frozen before the final configuration was carried forward into Gate 6D.

The selected Gate 6D LLM configuration is:

`@cf/nvidia/nemotron-3-120b-a12b`

served through Cloudflare Workers AI.

No alternative model configuration is substituted during Gate 6D calibration development or EVAL.

## 3.5 Recommendation Output

For each SOC alert, the model produces one of two frozen triage recommendations:

- `ESCALATE`; or
- `DO_NOT_ESCALATE`.

The recommendation task and the confidence-estimation process are treated as distinct components. In particular, a confidence-estimation prompt is not permitted to revise the frozen recommendation generated for an alert.

## 3.6 Candidate 1: Sample-Consistency Agreement

The first candidate uncertainty estimator is sample-consistency agreement.

For each DEV item, five stochastic recommendation samples are generated:

- number of samples: \(n = 5\);
- temperature: 0.4;
- reasoning mode: frozen low-effort configuration;
- maximum generation length: 512 tokens.

The majority-voted recommendation is treated as the SC5 recommendation.

The raw confidence signal is the fraction of the five samples agreeing with the majority recommendation. Consequently, possible raw agreement values are:

- 0.6;
- 0.8; and
- 1.0.

This signal is denoted `SC5_AGREEMENT`.

Sampling uses a deterministic item-level seed derived from:

`SHA256("GATE6D_SC5_V1|" + item_id)`

with the frozen conversion procedure applied to generate a positive integer seed. This allows the stochastic protocol to be reproduced without selecting seeds according to outcomes.

Sample entropy is retained as a diagnostic quantity only and is not a candidate primary confidence estimator.

## 3.7 Candidate 2: Verbalized Correctness Self-Evaluation

The second candidate is an independent model self-evaluation of the probability that its already-frozen recommendation is correct.

For each item, the model receives a separate deterministic prompt requesting an integer correctness probability from 0 to 100.

The self-evaluation call uses:

- temperature: 0;
- one generation;
- the already-frozen recommendation;
- no ground-truth information.

The self-evaluation step is explicitly prohibited from changing the recommendation.

This raw confidence candidate is denoted `VC_SELF_EVAL`.

Visible-label token log probabilities were considered during capability assessment but excluded from the final uncertainty-estimator protocol because the available API exposed reasoning-stream log probabilities rather than a reliable probability associated with the final visible triage label.

## 3.8 Ground-Truth Separation

Ground truth is not included in either uncertainty-generation prompt.

During collection, terminal model outputs are recorded before correctness is computed. Ground truth is introduced only in the downstream analysis transaction after the collection-completeness and protocol gates have passed.

This separation ensures that uncertainty generation cannot condition directly on the known correctness of the recommendation.

Hidden DEV and EVAL ground-truth files are treated as controlled analysis inputs rather than ordinary model-collection inputs.

## 3.9 Grouped Cross-Validation

Uncertainty-estimator and calibration-method selection is performed exclusively on DEV500.

Five-fold grouped cross-validation is used, with grouping defined prospectively from capture and episode-start information. Alerts belonging to the same frozen episode group are therefore not split arbitrarily across training and validation folds.

The full untouched 458-item EVAL set is excluded from:

- estimator comparison;
- calibration fitting;
- calibration-method selection;
- threshold selection;
- tie resolution; and
- sensitivity-based winner changes.

## 3.10 Calibration Candidates

For each uncertainty estimator, the protocol evaluates prospectively defined post-hoc calibration mappings.

The baseline mapping is:

1. **Identity mapping**, which leaves the raw confidence unchanged.

The primary parametric post-hoc mapping is:

2. **Platt-style logistic calibration**, fitted using logistic regression on DEV correctness.

A nonparametric mapping is permitted only when the available DEV support satisfies the frozen eligibility requirements:

3. **Isotonic regression**, allowed only when the applicable DEV data contain:
   - at least 20 correct predictions;
   - at least 20 incorrect predictions; and
   - at least three distinct raw confidence values.

Calibration mappings are fitted within the appropriate DEV cross-validation structure for method comparison. The ultimately selected estimator/mapping combination is refitted using all valid DEV500 observations only after method selection is complete.

No calibration mapping is fitted on EVAL.

## 3.11 Primary and Secondary Technical Metrics

The primary model-selection metric for uncertainty/calibration is the out-of-fold Brier score.

For correctness label \(y_i \in \{0,1\}\) and confidence \(p_i\), the Brier score is the mean squared probabilistic prediction error:

\[
\mathrm{Brier}
=
\frac{1}{N}
\sum_{i=1}^{N}
(p_i-y_i)^2.
\]

Lower values indicate better probabilistic prediction of recommendation correctness.

Secondary metrics include:

- AUROC for discriminating correct from incorrect recommendations;
- AUPRC with incorrect recommendations treated as the positive error class;
- 10-bin Expected Calibration Error;
- reliability-bin summaries; and
- capture/episode sensitivity analyses.

The constant-confidence baseline is defined prospectively as the empirical correctness prevalence of the valid selected DEV population.

## 3.12 Prospective Method-Selection Rule

Estimator/calibrator selection follows a frozen hierarchical rule.

First, the candidate with the lower grouped cross-validated Brier score is preferred.

Two Brier scores are treated as effectively tied when:

\[
|\mathrm{Brier}_A-\mathrm{Brier}_B| < 0.01.
\]

If this condition is met, the candidate with better correctness-discrimination AUROC is preferred.

If the candidates remain tied after the AUROC comparison, `SC5_AGREEMENT` is selected by the prospectively frozen deterministic tiebreak rule.

Sensitivity thresholds of 0.005 and 0.02 are examined only as robustness diagnostics. They are not permitted to retrospectively change the primary winner defined by the frozen 0.01 rule.

Once the DEV method is selected, its estimator and calibration mapping are frozen before EVAL is opened for scoring.

## 3.13 Untouched EVAL Execution

The final selected confidence pipeline is evaluated once on the frozen 458-item EVAL partition.

EVAL collection and EVAL scoring are implemented as separate guarded execution stages.

The collection stage generates only the uncertainty outputs required by the already-selected DEV method. It does not compute correctness or calibration metrics.

Only after collection completeness, provenance, and freeze checks pass can the hidden EVAL ground truth be loaded by the scoring executor.

No EVAL regeneration is permitted merely because an output is unfavorable or semantically invalid. No EVAL refitting or method reselection is permitted.

## 3.14 Predefined EVAL Safeguard

Before participant-facing calibrated confidence can be finalized, the selected confidence mechanism must satisfy both frozen EVAL criteria:

1. correctness AUROC must be finite and strictly greater than 0.50; and
2. selected-method Brier score must be strictly lower than the constant baseline derived from DEV correctness prevalence.

Equality does not constitute a pass.

If either requirement fails, the protocol transitions to:

`HALT_PROTOCOL_REVIEW`

rather than continuing automatically to a participant-facing calibrated-confidence intervention.

Secondary EVAL statistics, bootstrap analyses, AUPRC, ECE, reliability summaries, or coverage diagnostics cannot override this primary pass/halt decision.

Passing the safeguard also does not automatically open Gate 7; the human-study protocol must still be reviewed and finalized separately.

## 3.15 Separation from the Human Study

Calibration DEV and calibration EVAL are not the human-study evaluation data.

The human-study intervention, participant-facing confidence representation, final conditions, participant population, sample size, trial count, item allocation, questionnaires, exclusions, hypotheses, and confirmatory contrasts remain unfrozen while Gate 6 is open.

This design prevents participant outcomes from being used to choose the underlying uncertainty estimator or post-hoc calibration method.

## 3.16 External TEST Preservation

The external TEST evidence remains outside the Gate 6D estimator-selection and calibration process.

The frozen external captures are not used for:

- DEV500 construction;
- calibration fitting;
- uncertainty-estimator selection;
- EVAL decision rules;
- human-study design tuning.

External TEST is reserved for its later predefined role and remains untouched at the present stage.

## 3.17 Reproducibility and Prospective Freezing

Major Gate 6D inputs, protocols, model-call implementations, metric definitions, analysis executors, and execution boundaries are stored as version-controlled freeze artifacts.

The pre-outcome reproducibility snapshot cryptographically binds the current authoritative implementation and freeze files using SHA-256 hashes. An independent verifier recomputes these hashes and fails closed when a bound artifact is changed or when protected governance conditions are altered.

Mutable operational artifacts, including the current in-progress DEV collection audit, are deliberately excluded from the authoritative reproducibility manifest.

Superseded implementation versions are retained for provenance but are not treated as the current authoritative execution path.

## 3.18 Current Analysis Boundary

At the time of this pre-results draft:

- Gate 6D DEV collection is incomplete;
- no final DEV estimator/calibrator result is reported here;
- the untouched calibration EVAL has not been scored;
- hidden EVAL ground truth has not been opened for scoring;
- External TEST has not been accessed;
- no real participant data have been collected; and
- Gate 7 has not been opened.

Accordingly, this section documents the prospective technical methodology without anticipating the pending technical outcomes.

**END OF PRE-RESULTS TECHNICAL METHODOLOGY DRAFT**
