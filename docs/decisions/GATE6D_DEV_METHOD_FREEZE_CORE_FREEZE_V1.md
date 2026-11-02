# Gate 6D DEV Method-Freeze Core Freeze V1

Status: FROZEN SYNTHETIC-VALIDATED

This freeze locks the logic that will eventually convert completed
Calibration-DEV results into the single immutable uncertainty estimator
and calibration mapping carried into Calibration-EVAL.

## Primary comparison population

Estimator/calibrator selection is performed only on the frozen
paired-common-valid population.

SC5_AGREEMENT and VC_SELF_EVAL therefore compete on the same DEV items
and the same frozen recommendations.

Coverage differences cannot change the winner.

## Candidate methods

Each estimator is evaluated with:

- identity;
- Platt scaling;
- isotonic regression when eligible under the frozen rule.

The primary criterion remains grouped five-fold OOF Brier score.

An absolute Brier difference strictly below 0.01 is an effective tie.

The frozen tie-break sequence remains:

1. greater AUROC for correctness;
2. SC5_AGREEMENT if the remaining frozen rule uniquely resolves the
   tie;
3. otherwise halt for protocol review.

No secondary uncertainty statistic, coverage statistic, confidence
interval, AUPRC, ECE result, capture sensitivity, or episode sensitivity
may create a new winner-selection rule.

## Post-selection refit

After the winner is selected, the selected calibration mapping is refit
on all valid Calibration-DEV observations available for the winning
estimator.

Therefore:

- if SC5_AGREEMENT wins, valid SC5 observations excluded from the paired
  comparison only because VC was invalid are restored for the final SC5
  mapping refit;

- if VC_SELF_EVAL wins, the refit population is the valid VC population,
  which is necessarily within the paired-common-valid population under
  the frozen collection policy.

## EVAL constant baseline

The empirical DEV correctness prevalence is frozen from exactly the same
winner-valid population used for post-selection refit.

That frozen prevalence becomes the constant baseline for the later
untouched Calibration-EVAL comparison.

The EVAL baseline population may not be redefined after EVAL is opened.

## Serializable mapping

The implementation serializes the selected mapping explicitly:

- identity as clipped raw confidence;
- Platt as `sigmoid(a * raw_confidence + b)`;
- isotonic through its fitted threshold arrays with clipping outside
  the fitted range.

Synthetic validation requires the serialized mapping to reproduce the
fitted mapping predictions to maximum absolute error <= 1e-12.

## Synthetic validation

The frozen normalization fixture produces:

- selected DEV items: 500;
- SC5 valid: 495;
- VC valid / paired common-valid: 488;
- candidate rows: 6;
- valid candidate rows: 5.

The synthetic selection is:

`VC_SELF_EVAL + platt`

This synthetic winner and its synthetic correctness prevalence have no
real scientific meaning.

The fixture also verifies the prospective refit population rule:

- SC5 if winner: 495 observations;
- VC if winner: 488 observations.

Identity, Platt, and isotonic serialization paths all pass synthetic
validation.

## EVAL boundary

This core does not load real DEV data and cannot produce the real method
freeze in V1.

The future real method freeze must be created from completed, gated DEV
data before Calibration-EVAL is accessed.

Calibration-EVAL remains sealed.

External-TEST remains untouched.

Gate 7 remains closed.

## Safety state at freeze

- Real DEV outputs read: NO
- Real DEV ground truth read: NO
- Real method selection performed: NO
- Real method-freeze artifact created: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Gate 7 opened: NO
- Model calls: 0
