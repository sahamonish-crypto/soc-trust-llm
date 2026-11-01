# Gate 6D Calibration-DEV 500-Item Resource Amendment

**Date:** 2026-11-02
**Status:** FROZEN — RESOURCE-DRIVEN AMENDMENT

## Decision

The Calibration-DEV collection target is reduced from **1,222** to
**500** items.

This is an explicitly approved reconsideration of the earlier full-DEV
freeze. It is made because the zero-budget Cloudflare daily free
allocation makes full collection operationally impractical.

The change is frozen **before any correctness or calibration analysis is
used to choose the reduced sample**.

## Outcome-blind selection

The frozen 500-item subset was selected using only:

- opaque item ID;
- capture;
- episode start;
- existing frozen CV fold;
- episode-group size.

The selection did **not** use:

- ground truth;
- model outputs;
- model correctness;
- SC5 agreement;
- VC confidence;
- calibration results;
- whether an item had already been collected.

All **48 frozen episode groups** are represented.

Capture counts:

- AmazonEcho-2023-02-21: **122**
- Windows7AD-2023-02-21: **378**

Frozen fold counts:

- Fold 1: **97**
- Fold 2: **101**
- Fold 3: **102**
- Fold 4: **98**
- Fold 5: **102**

## Scientific protocol retained

The following remain unchanged:

- ZB1 Nemotron winner;
- canonical alert/evidence inputs;
- SC5 `n=5`, temperature `0.4`, and deterministic seeds;
- SC5 majority and agreement;
- VC_SELF_EVAL;
- grouped five-fold CV;
- Brier score as the primary method-selection metric;
- AUROC/AUPRC/ECE/reliability as secondary analyses;
- identity, Platt, and conditional isotonic calibration candidates;
- the untouched **458-item Calibration-EVAL**;
- External-TEST isolation.

## Existing collected outputs

Existing terminal DEV results may be reused **only if their item IDs are
members of the now-frozen 500-item manifest**.

The 500-item selection was completed without consulting which items had
already been collected.

Existing outputs for nonselected items are excluded from estimator and
calibrator selection and remain operational provenance only.

## Important unresolved item

The numerical definition of an **effective Brier-score tie** remains
unresolved and must be frozen before any correctness-based method
comparison.

## Next step

Compute only the membership overlap between the frozen 500-item manifest
and the already-terminal DEV outputs.

Do not inspect correctness or calibration performance during that step.
