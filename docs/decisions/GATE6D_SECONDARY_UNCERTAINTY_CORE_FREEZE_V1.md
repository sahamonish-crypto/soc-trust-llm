# Gate 6D Secondary Uncertainty Core Freeze V1

Status: FROZEN SYNTHETIC-VALIDATED

This freeze locks the implementation of the prospectively frozen Gate
6D secondary uncertainty and sensitivity protocol.

## Implemented bootstrap

The implementation performs 10,000 deterministic,
capture-stratified episode-cluster bootstrap replicates.

Within each capture, episode clusters are sampled with replacement.
All alert rows belonging to a sampled episode receive the corresponding
cluster multiplicity.

Individual alert rows are never independently bootstrapped.

## Confidence intervals

The implementation provides frozen 95% percentile confidence intervals
for:

- Brier score;
- AUROC for correctness;
- AUPRC for incorrectness;
- fixed-bin ECE10.

At least 9,500 of 10,000 replicates must produce a defined metric before
a CI is reported.

Undefined metric replicates are retained as undefined. They are not
silently redrawn.

## Deterministic synthetic validation

The complete 10,000-replicate synthetic test passed.

Synthetic structure:

- 488 rows;
- 48 episode clusters;
- 12 synthetic AmazonEcho episode clusters;
- 36 synthetic Windows7AD episode clusters.

Frozen synthetic draw-plan SHA256:

`4e9f29343e7ffb2b4fb2bc645f14243cdbb3b20ccfe5f5682308b73c0ef4d8e1`

Repeating draw-plan generation from the frozen seed produced identical
cluster multiplicities.

## Paired comparisons

The exact same bootstrap episode draws are reused across methods.

The implementation supports paired metric differences defined as:

`metric(VC) - metric(SC5)`

These paired intervals are secondary and cannot alter the primary
method-selection winner.

## Sensitivity analyses

The implementation also validates:

- ground-truth-class summaries;
- capture-specific summaries;
- leave-one-episode-out influence summaries.

These are descriptive secondary analyses.

## Bootstrap estimand

The bootstrap operates on already-produced frozen grouped-OOF
probabilities.

It does not refit Platt scaling, isotonic regression, or any estimator
inside bootstrap replicates.

The resulting intervals therefore quantify conditional sampling
uncertainty of the realized OOF predictions under episode clustering.

They are not presented as full model-training uncertainty.

## Real-data boundary

V1 contains no real DEV loader.

It cannot run real DEV secondary analysis.

Real use remains gated behind:

1. completion of all 500 selected DEV items;
2. the frozen DEV500 collection-complete artifact;
3. the separately controlled real DEV analysis path;
4. the frozen real DEV method-selection result.

Calibration-EVAL remains sealed until the DEV method is frozen.

## Safety state

- Real DEV outputs read: NO
- Real DEV ground truth read: NO
- Correctness-based real analysis performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Model calls: 0
