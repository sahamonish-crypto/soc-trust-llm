# 8. Threats to Validity

**Draft status:** PRE-RESULTS / PRE-GATE-7  
**Purpose:** Prospectively document known validity risks and the design controls intended to mitigate them. Outcome-dependent limitations will be added after the corresponding analyses are complete.

## 8.1 Construct Validity

### 8.1.1 Confidence is not equivalent to model correctness

The project estimates the probability that an LLM recommendation is correct; it does not assume that a confidence signal is identical to correctness itself. Sample-consistency agreement and verbalized self-evaluation are therefore treated as candidate uncertainty estimators whose usefulness must be demonstrated empirically.

A raw estimator may discriminate correct from incorrect recommendations while still being numerically miscalibrated. Conversely, a post-hoc calibrator may improve probability calibration without materially improving discrimination. The protocol therefore evaluates both calibration and correctness-discrimination properties rather than reducing confidence quality to a single metric.

### 8.1.2 Technical calibration is not human trust calibration

Statistical calibration of an LLM confidence score and calibration of human trust are distinct constructs.

Technical calibration concerns correspondence between numerical confidence and observed model correctness. Human trust calibration concerns whether a person’s trust or reliance is appropriate relative to system capability.

The project therefore separates:

1. uncertainty estimation;
2. post-hoc calibration;
3. participant-facing presentation;
4. subjective trust; and
5. behavioral reliance.

The later human study must not treat a subjective trust questionnaire as a substitute for behavioral reliance measures.

### 8.1.3 Reliance requires behavioral operationalization

Appropriate reliance, over-reliance, and under-reliance depend on observable participant decisions relative to AI recommendations and AI correctness.

The final operational definitions remain unfrozen until the human-study protocol is finalized. This avoids prematurely fixing a behavioral measure before the intervention and trial structure are known.

### 8.1.4 Workload is multidimensional

NASA-TLX is currently the leading candidate measure for subjective workload, but workload should not be interpreted as a single objective property of the interface.

An uncertainty-aware interface may reduce some forms of uncertainty while increasing verification effort. Consequently, the study should not assume prospectively that the intervention must reduce workload.

The exact NASA-TLX scoring and administration procedure remains unresolved until Gate 7 design is finalized.

## 8.2 Internal Validity

### 8.2.1 Information leakage between model-selection and calibration stages

Using the same alerts for model selection and calibration could favor a configuration that has already been optimized to those cases.

To reduce this threat, Gate 6C benchmark items are excluded from Gate 6D calibration development and EVAL.

### 8.2.2 Leakage from calibration DEV into calibration EVAL

Repeated inspection of EVAL outcomes during estimator selection would invalidate the interpretation of EVAL as untouched evidence.

The protocol therefore prohibits:

- estimator selection on EVAL;
- calibration fitting on EVAL;
- EVAL-based threshold tuning;
- EVAL-based method reselection;
- regeneration solely because an EVAL output is unfavorable.

The selected estimator/calibration mapping must be frozen before EVAL scoring.

### 8.2.3 Ground-truth exposure during confidence generation

Providing the true label to an uncertainty-generation prompt would trivially contaminate the confidence estimate.

Ground truth is therefore excluded from SC5 and verbalized-confidence generation. Terminal model outputs are collected before recommendation correctness is computed.

### 8.2.4 Alert-card lexical cues

The prospective alert-card audit found no direct ground-truth leakage but identified a small number of high-specificity lexical cues that could correlate with malicious status.

The project retained those alerts rather than retrospectively editing the input representation after inspection. This preserves the frozen data boundary but introduces a limitation: measured performance may partly reflect domain-specific lexical regularities.

This caveat should remain visible in the final paper.

### 8.2.5 Episode-level dependence

Alerts originating from the same capture or episode may not be statistically independent.

DEV method selection therefore uses grouped cross-validation based on frozen capture and episode-start groupings rather than arbitrary item-level splits.

The later human analysis is likewise designed to account for repeated observations across both participants and alert items.

### 8.2.6 Post-hoc analytical flexibility

Flexible selection among uncertainty estimators, calibrators, metrics, or thresholds after observing outcomes would increase researcher degrees of freedom.

The project mitigates this threat through prospective freezes for:

- candidate uncertainty estimators;
- calibration mappings;
- isotonic eligibility requirements;
- primary and secondary metrics;
- Brier effective-tie threshold;
- deterministic tiebreaking;
- grouped folds;
- EVAL pass/halt criteria.

Sensitivity analyses are explicitly prevented from overriding the primary frozen winner.

## 8.3 Statistical Conclusion Validity

### 8.3.1 Limited raw-confidence support

SC5 agreement with five samples can take only a small number of raw values. This limits the complexity of calibration mappings that can be supported reliably.

The protocol therefore constrains isotonic regression through minimum class-support and distinct-score requirements and retains identity and Platt-style mappings as prospectively defined alternatives.

### 8.3.2 Calibration metric limitations

No single calibration statistic fully characterizes confidence quality.

Brier score is the primary method-selection criterion, while AUROC, AUPRC for incorrect recommendations, ECE, and reliability summaries provide complementary information.

ECE is interpreted cautiously because its value depends on binning choices.

### 8.3.3 Constant-baseline comparison

A candidate confidence mechanism could appear numerically plausible while providing little value beyond a constant estimate of average model correctness.

The untouched-EVAL safeguard therefore requires the selected method to outperform a constant confidence baseline derived from DEV correctness prevalence on Brier score.

It also requires correctness AUROC to be finite and strictly greater than 0.50.

### 8.3.4 Human-study clustering

Human-study trials will contain repeated observations from participants and repeated alert items. Treating all trials as independent would underestimate uncertainty.

The pre-Gate-7 statistical infrastructure therefore supports participant and item random effects for trial-level binary outcomes.

The final random-effects structure, contrasts, power assumptions, and confirmatory backend remain unfrozen until the human-study design is finalized.

### 8.3.5 Sample size and power

No participant sample size is frozen at this stage.

The final sample-size decision must follow the finalized study design, primary contrast, expected trial structure, recruitment constraints, and an appropriate power analysis, preferably simulation-based for the mixed-effects design.

This avoids presenting an unsupported fixed participant number before the confirmatory model is defined.

## 8.4 External Validity

### 8.4.1 Dataset representativeness

The technical calibration data originate from a bounded set of frozen SOC/network-security captures and may not represent the full diversity of production SOC environments.

Performance may vary across:

- organizations;
- network architectures;
- telemetry sources;
- attack families;
- benign background traffic;
- alert-generation rules;
- analyst workflows.

Accordingly, calibration performance on the frozen evaluation data should not be interpreted automatically as universal SOC performance.

### 8.4.2 Model and provider dependence

Gate 6D uses one frozen LLM configuration selected under the project’s zero-budget constraints.

Results may depend on:

- the underlying model;
- provider implementation;
- inference settings;
- future model updates;
- API behavior.

The project therefore records exact model configuration and implementation artifacts to support reproducibility, but conclusions should remain bounded to the evaluated configuration unless replicated elsewhere.

### 8.4.3 Participant population

The final participant population remains unresolved.

Professional SOC analysts or cybersecurity practitioners are preferred, while screened advanced cybersecurity participants may be considered if practitioner recruitment is infeasible.

If non-professional participants are used, the manuscript must describe them accurately rather than labeling them as SOC analysts.

Generalization to experienced operational analysts must then be treated cautiously.

### 8.4.4 Laboratory versus operational SOC behavior

A controlled experiment cannot reproduce every aspect of live SOC work.

Real SOC decision making may involve:

- multiple tools;
- organizational procedures;
- collaboration with colleagues;
- changing incident context;
- escalation policies;
- interruptions;
- fatigue accumulated over long shifts;
- consequences that exceed those of an experimental task.

The human study can therefore test causal or behavioral relationships under controlled conditions but cannot alone establish full production effectiveness.

## 8.5 Ecological Validity

### 8.5.1 Alert representation

Participant-facing alert cards necessarily compress security context into an experimental representation.

This may differ from the full interface and investigative context available to analysts in operational SIEM, EDR, XDR, or case-management tools.

The final experiment should therefore preserve realistic evidence where feasible while controlling the information presented across study conditions.

### 8.5.2 Time pressure and alert fatigue

Operational alert fatigue emerges over extended exposure and workload accumulation.

A laboratory session may capture local verification effort and decision workload but may not reproduce chronic fatigue experienced across prolonged SOC shifts.

Any conclusions about alert-fatigue mitigation must therefore be framed carefully unless the final design measures it directly.

## 8.6 Human–AI Interaction Validity

### 8.6.1 Confidence-display effects

A participant may respond differently to the same numerical confidence depending on wording, visual emphasis, explanation, or training.

The participant-facing display is therefore not treated as interchangeable with the underlying calibrated probability.

The exact display remains blocked until Gate 6D EVAL establishes whether the technical confidence mechanism is suitable for participant-facing evaluation.

### 8.6.2 Automation bias and skepticism

AI assistance may produce both excessive acceptance and excessive rejection.

The study therefore avoids framing greater trust as inherently desirable. The target is appropriate reliance conditioned on the actual correctness of the recommendation.

### 8.6.3 Learning and order effects

Repeated exposure to alerts or assistance conditions can change participant behavior over time.

The final design must address randomization, ordering, counterbalancing, and potential learning effects. These choices remain unresolved in the current pre-Gate-7 decision framework.

## 8.7 Reproducibility and Researcher Degrees of Freedom

The project uses version-controlled prospective freeze artifacts for major data boundaries, model-selection rules, uncertainty estimators, calibration procedures, analysis logic, and EVAL safeguards.

A cryptographic reproducibility manifest binds the authoritative pre-outcome implementation and freeze files. An independent verifier recomputes these hashes and rejects tampering.

Mutable operational state is deliberately excluded from the authoritative manifest.

These controls cannot eliminate every source of researcher judgment, but they create an auditable distinction between decisions made before and after outcome access.

## 8.8 Current Outcome-Independent Limitations

At the time of this draft, several important limitations cannot yet be assessed empirically because the corresponding stages are incomplete.

These include:

- actual DEV calibration performance;
- the selected estimator/calibrator;
- untouched EVAL discrimination and calibration;
- whether the EVAL safeguard passes;
- participant recruitment feasibility;
- actual human-study statistical power;
- intervention adherence;
- participant learning effects;
- observed reliance behavior;
- observed workload effects;
- external TEST generalization.

These items will be added or revised only after the relevant frozen analyses are completed.

## 8.9 Interpretation Boundary

The final manuscript should distinguish carefully among:

- evidence supported by the frozen technical benchmark;
- evidence supported by untouched calibration EVAL;
- evidence supported by the controlled human study;
- evidence supported by external TEST;
- broader operational implications that remain inferential.

This distinction is necessary to avoid extending conclusions beyond the evidence supplied by each evaluation stage.

**END OF PRE-RESULTS THREATS TO VALIDITY DRAFT**
