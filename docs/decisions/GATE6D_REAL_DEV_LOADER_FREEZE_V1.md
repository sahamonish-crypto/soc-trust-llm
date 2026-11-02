# Gate 6D Real-DEV Loader Freeze V1

Status: FROZEN DISABLED / SYNTHETIC-VALIDATED

This freeze locks the future correctness-bearing DEV loading path before
the DEV500 collection is complete.

## Purpose

The loader is the controlled bridge between:

1. the future frozen DEV500 collection-complete state;
2. the already-frozen DEV normalization core;
3. the already-frozen primary calibration analysis;
4. the already-frozen secondary uncertainty analysis.

It does not itself select an estimator or calibrator.

## Two-factor real-data gate

The loader may open real correctness-bearing DEV artifacts only when
both of the following conditions hold:

1. `GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1.json` exists and
   validates as `FROZEN_COMPLETE` with 500/500 selected DEV items and
   zero remaining; and

2. the explicit environment gate is set:

   `GATE6D_ALLOW_REAL_DEV_LOAD=YES`

Failure of either condition blocks loading before SC5 outputs, VC
outputs, or hidden DEV ground truth are opened.

## Collection integrity

After the gate opens, the loader must verify that the current SC5 and VC
terminal files exactly match the SHA256 values frozen in the
collection-complete artifact.

Any post-freeze mutation fails closed.

## Static DEV integrity

After the gate opens, the loader verifies the frozen hashes for:

- DEV500 selected manifest;
- canonical DEV collection manifest;
- hidden DEV ground truth.

These checks occur only after the real-data gate is satisfied.

## Normalization

The loader invokes the already-frozen DEV normalization core.

It does not modify its paired-common-valid rules, invalid-output policy,
fold assignments, confidence values, recommendations, or correctness
definition.

## Episode metadata

Because the frozen normalization core intentionally contains only the
calibration fields needed for method selection, this loader adds
read-only metadata from the canonical DEV manifest:

- `capture`;
- `episode_start_utc`.

The loader requires exactly 48 frozen selected episode groups and the
capture set:

- AmazonEcho-2023-02-21;
- Windows7AD-2023-02-21.

This metadata enables the separately frozen cluster-bootstrap and
episode-sensitivity analysis without changing the normalization core.

## EVAL/Test boundary

The loader contains no Calibration-EVAL or External-TEST input paths.

Opening DEV does not unlock EVAL.

Calibration-EVAL remains sealed until the selected DEV uncertainty
estimator/calibration method is analyzed and separately frozen.

External-TEST remains untouched.

## Current state

At this freeze:

- selected DEV complete: 58/500;
- selected DEV remaining: 442;
- collection-complete freeze: absent;
- real load environment gate: absent;
- real DEV loader execution: blocked.

## Safety state

- Real DEV outputs read: NO
- Real DEV ground truth read: NO
- Correctness computed: NO
- Correctness-based real analysis performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Model calls: 0
