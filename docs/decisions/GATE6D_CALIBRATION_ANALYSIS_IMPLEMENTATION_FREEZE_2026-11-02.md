# Gate 6D Calibration Analysis Implementation Freeze V1

**Date:** 2026-11-02
**Status:** FROZEN

## Purpose

Freeze the statistical/calibration implementation before the code is
permitted to inspect real Gate 6D DEV correctness outcomes.

## Frozen implementation

The analysis core implements:

- grouped five-fold out-of-fold evaluation;
- Brier score as the primary metric;
- AUROC for correctness discrimination;
- AUPRC with incorrectness as the positive class;
- fixed 10-bin ECE and reliability tables;
- grouped out-of-fold constant-prevalence baseline;
- identity calibration;
- unregularized Platt scaling;
- isotonic regression under the predeclared eligibility criteria;
- the frozen absolute Brier effective-tie threshold `< 0.01`;
- AUROC as the first tie breaker;
- SC5_AGREEMENT as the remaining estimator tie breaker.

No additional post-hoc tie breaker is introduced. If the frozen rules
cannot uniquely select a method, the implementation halts for protocol
review.

## Isotonic eligibility

Isotonic is eligible only when the DEV data contain:

- at least 20 correct outcomes;
- at least 20 incorrect outcomes;
- at least 3 distinct raw confidence scores.

## Synthetic validation

The implementation was validated using deterministic synthetic data
with 500 rows and the frozen DEV500 fold counts:

`97, 101, 102, 98, 102`

The synthetic test passed before any real DEV correctness data were
examined.

## Safety state at freeze

- Real SC5/VC outputs inspected by analysis implementation: NO
- Real DEV ground truth inspected: NO
- Correctness-based method comparison performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- New model calls: 0

The core remains self-test-only. A separate wrapper will later be
created for real DEV analysis after collection is complete and the raw
collection is frozen.
