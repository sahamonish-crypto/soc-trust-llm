# Gate 6D Calibration-EVAL Execution Safeguard Protocol V1

Status: FROZEN PROSPECTIVE EVAL OPERATIONALIZATION

## Purpose

This decision prospectively operationalizes the already-frozen Gate 6D
Calibration-EVAL safeguard before any EVAL model inference, correctness
inspection, or scoring.

The parent protocol already requires a halt if the selected calibrated
confidence:

1. does not show useful correctness discrimination; or
2. fails to improve on the constant-confidence baseline.

This decision fixes the exact numeric interpretation of that safeguard
without changing or relaxing the parent rule.

## Primary EVAL safeguard

Calibration-EVAL passes only if BOTH conditions hold:

`AUROC_correct > 0.50`

and

`Brier_selected < Brier_constant_DEV_prevalence`

Equivalently:

`delta_Brier = Brier_selected - Brier_constant_DEV_prevalence`

must satisfy:

`delta_Brier < 0`

Equality fails the corresponding condition.

Undefined AUROC or Brier also fails the safeguard.

Failure of either condition requires:

`HALT_BEFORE_PARTICIPANT_FACING_CALIBRATED_CONFIDENCE`

and explicit protocol review.

## AUROC interpretation

AUROC 0.50 is used as the non-informative ranking boundary.

No higher conventional cutoff such as 0.70 is introduced because no
domain-specific prospective utility threshold was established for this
SOC confidence task.

## Brier baseline

The comparator is the empirical correctness prevalence frozen from the
same winner-valid Calibration-DEV population used for the final
post-selection calibration refit.

The baseline probability is therefore fixed before EVAL.

EVAL empirical correctness prevalence is never substituted for it.

The selected method and constant baseline are evaluated on exactly the
same valid EVAL observations.

## Point-estimate gate

This safeguard is an operational tripwire rather than a new
confirmatory null-hypothesis test.

Therefore the primary pass/halt decision uses the strict prospective
point-estimate inequalities above.

The already-frozen 10,000-replicate episode-cluster bootstrap remains
secondary uncertainty reporting and cannot change the pass/halt result.

Bootstrap CI overlap, statistical significance, AUPRC, ECE, coverage,
capture sensitivity, and episode sensitivity cannot override the
primary safeguard.

## One-shot EVAL boundary

Calibration-EVAL contains 458 frozen items from:

`Windows7AD-2023-02-22`

The real DEV method-freeze artifact must exist before EVAL collection
can begin.

Ground truth must remain unopened throughout model-output collection.

All 458 items form one logical final evaluation. Provider quota or
retryable infrastructure interruptions may resume the same logical
collection and do not constitute a second evaluation.

Terminal semantic-invalid outputs are not silently regenerated.

The completed EVAL model-output collection must be frozen before hidden
EVAL ground truth is opened for scoring.

## Selected-estimator execution

If the frozen estimator is `SC5_AGREEMENT`:

- SC5 is collected for all 458 items;
- VC_SELF_EVAL is not called;
- terminal-valid SC5 items form the valid scoring population.

If the frozen estimator is `VC_SELF_EVAL`:

- SC5 is collected for all 458 items;
- VC is called only after terminal-valid SC5;
- valid scoring items require both terminal-valid SC5 and terminal-valid VC.

Missing required terminal records prevent collection completion.

Duplicate selected terminal records require protocol review.

Coverage and invalid reasons are reported but cannot create or replace a
pass criterion.

## No EVAL-driven adaptation

Calibration-EVAL may not be used to:

- reselect the DEV estimator;
- choose another calibrator;
- refit the selected calibration mapping;
- tune a threshold;
- redefine the baseline;
- relax the safeguard;
- initiate another EVAL attempt because the result is unfavorable.

An exact deterministic reproduction from frozen artifacts is an audit,
not a new method-selection opportunity.

## Secondary EVAL reporting

Report:

- selected-method Brier;
- frozen DEV-prevalence constant-baseline Brier;
- paired Brier difference;
- AUROC correctness;
- AUPRC with incorrectness as the positive class;
- ECE10;
- fixed-bin reliability diagram;
- validity and coverage;
- capture and episode sensitivity;
- frozen episode-cluster bootstrap uncertainty.

Because Calibration-EVAL contains one frozen capture, that capture is
treated as fixed and episode clusters are resampled with replacement
within it.

## Governance after EVAL

A PASS permits Gate 6D to proceed toward closure.

A PASS does not automatically open Gate 7.

A FAIL prohibits participant-facing calibrated-confidence use until
explicit protocol review.

External-TEST remains untouched.

## Safety state at freeze

- Real DEV method selection performed: NO
- Real DEV method-freeze artifact exists: NO
- EVAL model inputs opened: NO
- EVAL manifest opened: NO
- EVAL ground truth opened: NO
- EVAL model calls: 0
- EVAL correctness inspected: NO
- External-TEST accessed: NO
- Gate 7 opened: NO
