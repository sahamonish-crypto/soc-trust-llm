# Gate 6D Brier Effective-Tie Threshold Freeze

**Date:** 2026-11-02
**Status:** FROZEN

## Primary selection metric

Grouped five-fold out-of-fold Brier score remains the primary criterion
for uncertainty-estimator/calibrator selection.

## Effective tie

Two leading methods are treated as effectively tied when:

`|Brier_A - Brier_B| < 0.01`

If effectively tied, the method with better AUROC for correctness
discrimination is selected.

If still tied, `SC5_AGREEMENT` is preferred.

## Sensitivity analysis

For reporting only, the robustness of the selection will also be
described under margins of:

- 0.005
- 0.020

These sensitivity margins cannot change the frozen primary winner.

## Reason

There is no universal Brier-score practical-equivalence cutoff.
Therefore, the 0.01 margin is fixed prospectively before inspecting
DEV correctness or calibration performance, preventing a post-hoc
threshold chosen to favor a particular estimator.

## State at freeze

- DEV correctness inspected for method selection: NO
- Calibration metrics inspected: NO
- New model calls: 0
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
