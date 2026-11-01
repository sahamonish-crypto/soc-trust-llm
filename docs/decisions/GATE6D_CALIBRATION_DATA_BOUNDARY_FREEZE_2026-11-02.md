# Gate 6D Calibration Data Boundary Freeze

Status: **FROZEN**

Frozen UTC: 2026-11-01T18:57:04.421744+00:00

## Purpose

Freeze the data boundary for uncertainty-estimation and probability-
calibration development before any Gate 6D model collection or method
selection.

## Eligibility

Only items with `rich_context = 1` are eligible for the primary
calibration-development/evaluation pools.

This restriction is necessary because the pre-freeze audit showed that
evidence availability (`rich_context`) is strongly associated with the
ground-truth class in two captures. Including `rich_context = 0` cases
in the primary calibration pool could therefore create an
evidence-availability shortcut.

## Calibration-DEV

Captures:

- AmazonEcho-2023-02-21
- Windows7AD-2023-02-21

Eligible items: **1222**

Aggregate composition:

- Benign: **1204**
- Malicious: **18**

Permitted uses:

- uncertainty-estimator development;
- candidate calibrator fitting;
- grouped/capture-aware development validation.

## Calibration-EVAL

Capture:

- Windows7AD-2023-02-22

Eligible items: **458**

Aggregate composition:

- Benign: **438**
- Malicious: **20**

Calibration-EVAL is capture/time separated from Calibration-DEV.

Item-level Calibration-EVAL correctness/ground truth must not be used
to select, tune, or fit the uncertainty estimator or calibrator.

Aggregate class counts were inspected during split design and are
therefore not considered blinded.

## Excluded primary-calibration material

`rich_context = 0`: **783 items**

These cases are not eligible for primary estimator/calibrator fitting
or selection. They may only be considered later under a separately
frozen robustness protocol.

## Separation safeguards

- Gate 6C benchmark items are not reused for Gate 6D calibration.
- Community-ID overlap with the Gate 6C benchmark: **0**.
- Gate 6C External-TEST was not accessed.
- Final human-study items must remain separate from these calibration
  development/evaluation pools.
- No Gate 6D model calls have yet been made.

## Deliberately unresolved

This freeze does NOT yet decide:

- exact number of DEV/EVAL items that will receive model calls;
- stochastic sample count;
- sampling temperature;
- uncertainty estimator;
- post-hoc calibrator;
- participant-facing confidence representation.

Those choices require a separate predeclared Gate 6D estimator
protocol before any correctness-based method comparison.

## Source binding

Source inventory:

`data/processed/gate6/gate6_partition_inventory_items.csv`

SHA256:

`84975b00dfcd012e4f2f7ec0ad7b2cb820217753e39239fdef555208e78f1dde`
