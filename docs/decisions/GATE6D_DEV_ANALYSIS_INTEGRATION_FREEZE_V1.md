# Gate 6D DEV Analysis Integration Freeze V1

Status: FROZEN SYNTHETIC-VALIDATED

This freeze locks the synthetic end-to-end integration path connecting
the already-frozen DEV normalization logic to the already-frozen
calibration-analysis core.

## Tested pipeline

The synthetic integration test verifies:

1. synthetic SC5/VC/ground-truth fixture generation;
2. frozen DEV500 normalization;
3. paired common-valid population construction;
4. SC5_AGREEMENT and VC_SELF_EVAL extraction;
5. grouped five-fold out-of-fold calibration evaluation;
6. grouped out-of-fold constant-baseline evaluation;
7. frozen estimator/calibrator method-selection rules.

The synthetic fixture yields 488 paired common-valid observations across
all five frozen folds.

Six estimator/calibrator candidate rows are generated. Five are valid in
this synthetic fixture. Candidate invalidity is retained rather than
silently modifying frozen eligibility rules.

## Synthetic results are not scientific findings

The synthetic winner is implementation evidence only.

It cannot:

- establish the real winning estimator;
- establish the real winning calibrator;
- justify participant-facing confidence;
- modify the frozen selection protocol.

## Real-analysis boundary

This V1 permits synthetic self-test only.

Real DEV analysis remains blocked until:

- all 500 selected DEV items are logically complete;
- the collection-complete artifact is frozen;
- the separately controlled real-data loading path is enabled.

Calibration-EVAL remains untouched until the DEV method is selected and
frozen.

## Safety state

- Real DEV outputs read: NO
- Real DEV ground truth read: NO
- Correctness-based real comparison performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Model calls: 0
