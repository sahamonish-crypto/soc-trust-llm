# Gate 6D Metric-Semantics Parity Freeze V1

Status: FROZEN SYNTHETIC-VALIDATED

## Purpose

The secondary uncertainty core independently implements weighted versions
of the Gate 6D metrics because episode-cluster bootstrap multiplicities
must be represented as observation weights.

Before any real DEV analysis, this freeze verifies that those weighted
metric semantics are compatible with the already-frozen calibration
analysis core.

Neither frozen core is modified.

## Reference comparison

For integer bootstrap multiplicities, the secondary uncertainty core is
compared against the frozen calibration core after explicitly duplicating
each synthetic observation according to its multiplicity.

Therefore the comparison tests the exact mathematical interpretation of
cluster-bootstrap resampling rather than a second hand-written reference
formula.

## Metrics validated

The parity harness validates:

- Brier score with correctness as the target;
- AUROC with correctness as the positive class;
- AUPRC with incorrectness as the positive class using 1-confidence;
- fixed-bin 10-bin ECE.

## ECE boundary semantics

The frozen bin rule is:

`[0,.1), [.1,.2), ..., [.9,1.0]`

The synthetic harness explicitly places probabilities at:

`0.0, 0.1, 0.2, ..., 0.9, 1.0`

and verifies exact bin membership under integer multiplicities.

Boundary semantics passed.

## Weighted equivalence

The harness validates weighted metrics against explicit row duplication,
including:

- ordinary multiplicities;
- zero-weight observations;
- tied prediction scores;
- deterministic random cases;
- all fixed ECE boundaries.

This directly verifies scikit-learn sample-weight behavior for both
AUROC and average precision against duplication semantics.

## Result

Total parity cases: 33

Deterministic random parity cases: 25

Maximum absolute metric difference:

`2.7755575615628914e-16`

Predeclared absolute tolerance:

`1e-12`

Therefore all tested metric differences are safely within tolerance.

The residual difference is ordinary floating-point roundoff and is over
three orders of magnitude below the frozen tolerance.

## Scientific conclusion

The concern that the secondary uncertainty core reimplements metric
semantics independently of the calibration core is resolved by this
compatibility bridge.

For integer bootstrap multiplicities:

- weighted Brier is equivalent to explicit row duplication;
- weighted AUROC is equivalent to explicit row duplication;
- weighted AUPRC is equivalent to explicit row duplication;
- weighted ECE10 is equivalent to explicit row duplication.

The secondary bootstrap may therefore use its frozen weighted
metric_bundle without changing Gate 6D metric semantics.

This validation does not alter:

- primary DEV estimator/calibrator selection;
- the frozen Gate 6D winner-selection rule;
- the secondary-only status of uncertainty intervals.

## Fail-closed validation

Three malformed weighted-input conditions were tested and rejected:

- zero total weight;
- negative weight;
- probability outside [0,1].

## Safety state

- Real DEV model outputs read: NO
- Real DEV ground truth read: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Model calls: 0
- Gate 7 opened: NO
