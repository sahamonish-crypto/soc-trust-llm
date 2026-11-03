# Manuscript Evidence Map V1

Status: PRE-RESULTS / PRE-GATE-7 DRAFTING AID  
Gate 6: OPEN  
Gate 7: NOT OPENED  
Purpose: Separate manuscript material that can be drafted now from claims that remain blocked on final evidence.

## 1. Writing rules

1. Do not write outcome claims before the corresponding frozen analysis is executed.
2. Do not treat provisional human-study choices as final.
3. Distinguish trust (attitude) from reliance (behavior).
4. Do not claim novelty for basic LLM SOC triage, human-LLM SOC collaboration, LLM confidence estimation, calibration, RAG incident analysis, or automation-bias research.
5. Final novelty wording requires a fresh literature/novelty audit before submission.
6. Technical methods must reflect frozen repository decisions rather than retrospective simplification.
7. EVAL and External-TEST results must never be implied before execution.
8. Use primary papers for manuscript citations; the project spreadsheet and AI SOC Triage synthesis are navigation aids only.

## 2. Sections safe to draft now

### 2.1 Introduction — problem motivation

Safe themes:
- SOC analysts operate under high alert volume and alert-fatigue pressure.
- AI/LLM systems are increasingly investigated as analyst decision-support tools.
- Human oversight remains important because technical performance alone does not establish appropriate reliance.
- Trust and reliance must be calibrated to system capability rather than maximized.

Primary-source families:
- Papers 3–7: SOC human-AI teaming, alert prioritisation, alert fatigue.
- Paper 22: trust in automation / appropriate reliance.
- Paper 23: human factors, cognitive bias, and trust in cybersecurity.
- Paper 1: empirical human-LLM collaboration in SOCs.

### 2.2 Related work — LLMs in SOC operations

Safe themes:
- Prior work already studies LLM use in SOC workflows.
- Prior work already studies alert classification/prioritisation and incident analysis.
- Existing SOC literature motivates hybrid human-AI operation and continued analyst authority.

Primary-source families:
- Paper 1: empirical human-AI SOC collaboration.
- Paper 2: LLM alert classification/prioritisation.
- Papers 3–5: human-AI teaming / trusted autonomy / trust-aware SOC operation.
- Papers 26–28: broader LLM cybersecurity reviews.
- Paper 31: retrieval-augmented security incident analysis.

### 2.3 Related work — trust, reliance, and human factors

Safe themes:
- Trust is an attitude; reliance is observable behavior.
- Appropriate reliance requires correspondence between human reliance/trust and system capability.
- Over-reliance and under-reliance are distinct failure modes.
- Cybersecurity decision-making can be affected by automation bias, confirmation bias, cognitive load, and time pressure.

Primary-source families:
- Paper 22: foundational appropriate reliance / trust calibration.
- Paper 23: cybersecurity-specific human factors and trust.
- Paper 29: appropriate trust using human and AI correctness likelihood.
- Papers 8–10 and related corpus: uncertainty expression and reliance.

### 2.4 Related work — uncertainty and calibration

Safe themes:
- LLM confidence is not automatically calibrated.
- Confidence estimation and calibration are distinct problems.
- Sample consistency is a candidate uncertainty signal.
- Brier score is an established calibration metric.
- ECE/reliability analysis is useful but should not replace the primary calibration criterion.

Primary-source families:
- Paper 30: LLM confidence judgment accuracy.
- Paper 33: confidence estimation/calibration survey.
- Paper 34: sample-consistency calibration.
- Paper 35: modern neural-network calibration.
- ICLR uncertainty-expression work in the active corpus.

### 2.5 Technical methodology — model selection

Safe because already frozen:
- The project used a prospective Gate 6C model-selection benchmark.
- Three zero-budget candidate configurations were evaluated over the canonical benchmark.
- Selection used predeclared criteria and a Redline tiebreak.
- The frozen winner is the Cloudflare Workers AI NVIDIA Nemotron configuration.
- External TEST captures remain untouched.

Repository evidence:
- Gate 6C canonical benchmark freezes.
- Gate 6C model-selection result freeze.
- Gate 6C winner-configuration freeze.

### 2.6 Technical methodology — uncertainty/calibration protocol

Safe because protocol is frozen:
- DEV and EVAL are separated.
- Human-study items are separated from calibration evaluation.
- The primary uncertainty candidate is SC5 agreement.
- A separate verbal/self-evaluation candidate is evaluated independently.
- DEV selection uses grouped cross-validation.
- Brier score is the primary selection metric.
- AUROC for correctness and AUPRC for incorrect cases are secondary.
- Identity and Platt calibration are considered prospectively; isotonic is conditional on support.
- The selected method must be frozen before untouched EVAL execution.
- EVAL uses a predefined pass/halt safeguard.

Repository evidence:
- Gate 6D data-boundary freeze.
- Gate 6D uncertainty-estimator protocol freeze.
- Gate 6D Brier-tie freeze.
- Gate 6D DEV500 resource amendment.
- Gate 6D EVAL safeguard protocol.
- Gate 6D EVAL collection/scoring executor freezes.

### 2.7 Reproducibility

Safe themes:
- Frozen inputs, protocols, implementations, and execution boundaries are cryptographically hash-bound.
- Authoritative pre-outcome artifacts are independently verifiable.
- Mutable operational state is excluded from the authoritative reproducibility manifest.
- Superseded implementations remain provenance rather than current authoritative methods.

Repository evidence:
- REPRODUCIBILITY_MANIFEST_V1.
- REPRODUCIBILITY_VERIFICATION_EVIDENCE_V1.
- REPRODUCIBILITY_INFRASTRUCTURE_FREEZE_V1.

## 3. Sections that may be outlined but not finalized

### 3.1 Human-study design

Current status: BLOCKED ON GATE 6.

May describe only:
- conceptual aim to evaluate human interaction with AI-supported SOC triage;
- distinction between performance, workload, trust, and behavioral reliance;
- requirement for participant/item repeated-measures modeling;
- current preparation-only analysis infrastructure.

Do not yet finalize:
- experimental condition names or semantics;
- calibrated-confidence display;
- participant population;
- participant count;
- trial count;
- item allocation;
- trust questionnaire;
- NASA-TLX scoring/timing;
- randomization/counterbalancing;
- exclusion rules;
- hypotheses or primary contrasts;
- confirmatory software/backend.

Authoritative source:
- PRE_GATE7_HUMAN_STUDY_DECISION_FRAMEWORK_FREEZE_V1.

### 3.2 Human-study statistical analysis

Infrastructure validated but final specification not frozen.

Currently validated:
- binary trial-level mixed-model infrastructure;
- participant random effects;
- item random effects;
- continuous mixed-model infrastructure;
- fail-closed rejection of real participant data before Gate 7.

Do not state that statsmodels is the final confirmatory backend.

Authoritative source:
- PRE_GATE7_STATISTICAL_ANALYSIS_FREEZE_V1.

## 4. Sections blocked until outcomes exist

Do not draft substantive claims for:
- Gate 6D DEV results;
- selected uncertainty estimator/calibrator;
- Gate 6D EVAL results;
- calibration safeguard outcome;
- human-study results;
- External-TEST results;
- final discussion of observed effects;
- final abstract;
- final conclusion.

Placeholders are allowed only when explicitly marked TODO/RESULT PENDING.

## 5. Prohibited novelty claims

Do not claim:
- “first use of LLMs in SOCs”;
- “first LLM SOC triage system”;
- “first human-AI SOC study”;
- “first LLM uncertainty calibration method”;
- “first use of sample consistency for calibration”;
- “first RAG security incident-analysis system”;
- “first study of automation bias or over-reliance”;
- “first trust-aware SOC framework”.

## 6. Provisional contribution frame

Do not label this final.

Potential contribution direction:
- a rigorously separated technical calibration and human-evaluation pipeline for LLM-assisted SOC triage;
- prospective selection and untouched evaluation of confidence estimation/calibration before participant exposure;
- controlled measurement of behavioral reliance separately from subjective trust;
- evaluation of analyst performance, reliance, and workload under a trust-calibrated SOC decision-support intervention;
- reproducible execution boundaries that reduce post-hoc tuning risk.

Final wording depends on:
1. Gate 6D EVAL safeguard outcome;
2. final Gate 7 intervention design;
3. final human-study results;
4. fresh novelty audit immediately before manuscript submission.

## 7. Planned manuscript structure

1. Introduction
2. Background and Related Work
   2.1 SOC Alert Triage and Alert Fatigue
   2.2 LLMs in Security Operations
   2.3 Trust, Reliance, and Human Factors
   2.4 LLM Uncertainty and Calibration
   2.5 Research Gap and Study Positioning
3. Technical Methodology
   3.1 Data and Alert Construction
   3.2 Model Selection
   3.3 Uncertainty Estimation
   3.4 Calibration and Method Selection
   3.5 Untouched EVAL Safeguard
   3.6 Reproducibility and Leakage Controls
4. Technical Results
5. Human-Study Methodology
6. Human-Study Results
7. Discussion
8. Threats to Validity
9. Conclusion

## 8. Current drafting boundary

Allowed now:
- Introduction background/motivation;
- Related Work;
- frozen technical methodology;
- reproducibility methodology;
- threats-to-validity framework;
- manuscript structure.

Blocked:
- outcome-dependent prose;
- final novelty claims;
- final contribution claims;
- final abstract/conclusion;
- final human-study protocol.

Gate 7 remains closed.
