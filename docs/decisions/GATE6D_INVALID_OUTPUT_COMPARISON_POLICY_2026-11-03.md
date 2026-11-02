# Gate 6D Invalid-Output Comparison Policy

Status: FROZEN

## Reason for this amendment

The frozen Gate 6D uncertainty protocol already specifies that malformed
successful outputs are terminal semantic invalids and are not silently
regenerated.

It also specifies that, after method selection, the winning calibration
mapping is refit on all valid DEV observations.

The parent protocol did not explicitly define the comparison population
when SC5 and VC have different validity coverage. This document resolves
that edge case prospectively, before real correctness analysis.

## Primary comparison population

Estimator/calibrator selection uses the paired common-valid DEV set:

- valid SC5_MAJORITY terminal output; and
- valid VC_SELF_EVAL terminal output.

Both candidate estimators are therefore evaluated on exactly the same
items and frozen recommendations.

This avoids confounding estimator quality with different validity
subsets.

## Invalid outputs

If SC5 is terminal semantic-invalid:

- do not regenerate it;
- VC is not expected;
- exclude that item from both estimators in the primary comparison.

If SC5 is valid but VC is terminal semantic-invalid:

- do not regenerate VC;
- exclude the item from both estimators in the primary comparison;
- if SC5 later wins, that valid SC5 observation may still be used when
  the winning mapping is refit on all valid SC5 DEV observations.

Missing terminal records after a claimed collection-complete state are
not treated as semantic invalids. Collection completion must fail.

Duplicate terminal records cause normalization to halt.

## Coverage

Validity counts and invalid-reason distributions must be reported
separately.

Coverage differences cannot change the frozen primary winner.

Estimator-specific valid-set metrics may be reported as sensitivity
analyses only and cannot replace the paired primary comparison.

## Constant baseline

For primary DEV comparison, the constant baseline uses training-fold
correctness prevalence on the paired common-valid set.

After method selection, the winning method is refit on all valid DEV
observations for that estimator. The empirical correctness prevalence
of that same winner-valid DEV population becomes the frozen constant
baseline for the later untouched EVAL comparison.

## Fail closed

Correctness analysis must stop for protocol review if:

- the paired common-valid population loses any of the five frozen folds;
- no candidate can be evaluated by the frozen analysis core;
- frozen winner rules remain ambiguous;
- collection completeness or identifier consistency fails.

## Safety state at freeze

- Real DEV correctness inspected for this decision: NO
- Correctness-based real method comparison performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- New model calls: 0
