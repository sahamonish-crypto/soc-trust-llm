# Gate 6C Model-Selection Result Freeze

Status: PASSED / WINNER FROZEN

Frozen UTC: 2026-11-01T18:28:26.064119+00:00

## Winner

Candidate:

ZB1

Model:

`@cf/nvidia/nemotron-3-120b-a12b`

Decision stage:

Redline-only balanced accuracy.

## Frozen competence result

ZB1:
- response validity: 100.000%
- eligible: YES

ZB2:
- response validity: 100.000%
- eligible: YES

ZB3:
- response validity: 96.742%
- eligible: NO

ZB3 fails the frozen requirement that at least 99% of benchmark
logical responses contain valid labels.

## Primary model-selection metric

CTU evidence-covered balanced accuracy:

- ZB1: 0.833333
- ZB2: 0.833333
- ZB3: 0.775273

ZB1 and ZB2 are tied on the primary metric.

Their absolute difference is below 0.02, so the frozen winner rule
requires the Redline-only balanced-accuracy comparison.

## Redline tie-break

- ZB1: 0.625000
- ZB2: 0.492188

ZB1 therefore wins Gate 6C.

No later tie-breaking criterion is required.

## Mandatory robustness observation

Muhstik External-DEV malicious recall:

- ZB1: 0.000000
- ZB2: 0.000000
- ZB3: 0.000000

All three candidates obtained zero malicious recall on the frozen
Muhstik External-DEV subset.

This result does not alter the frozen winner because the winner was
already resolved at the Redline tie-break stage. It must nevertheless
be retained as an important external-robustness limitation and must not
be hidden or discarded.

## Frozen scoring artifacts

Scoring summary SHA256:

2bbcb0080f4dc9fe0f7976c8f242292b1d94a498e368bf0c34f6ba798b2e5565

Scored-items SHA256:

ad1e626ecc109faf4c8d94bb3c2805219fe9e309403faf9e759bb8f3075be85f

Frozen scorer SHA256:

6e4216609af0fdc880055a7b47c958d547455d165c1cee7f98d3ff9d4721a678

## Protection

No model output was changed after ground-truth scoring.

No model was selectively rerun.

No scoring rule, competence criterion, or tie-break was changed after
seeing correctness results.

Held-out External-TEST accessed: NO

Gate 6C model winner: ZB1 / NVIDIA Nemotron 3 Super 120B A12B
