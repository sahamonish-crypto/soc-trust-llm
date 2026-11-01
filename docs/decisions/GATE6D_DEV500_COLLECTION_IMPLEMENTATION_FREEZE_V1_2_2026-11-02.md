# Gate 6D DEV500 Collector v1.2 Freeze

**Date:** 2026-11-02
**Status:** FROZEN

## Purpose

Collector v1.2 restricts future Calibration-DEV inference to the frozen
outcome-blind 500-item DEV subset.

It prevents Cloudflare quota from being spent on DEV items that are no
longer part of estimator/calibrator selection.

## Frozen subset

- selected DEV items: **500**
- all 48 episode groups represented
- fold counts: **97 / 101 / 102 / 98 / 102**
- selected-manifest SHA256:

`db1016850df42736c1851b66a296550f82e4509e90b33f08fff8a73bad2e0f87`

## Existing reusable collection

A membership-only check was performed after the 500-item subset had
already been frozen.

- selected items already complete in both SC5 and VC: **58**
- selected items still requiring collection: **442**

This check used item IDs only.

It did not inspect correctness, SC5 agreement, VC confidence, ground
truth, or calibration performance.

## Scientific settings unchanged

The following remain unchanged:

- model: `@cf/nvidia/nemotron-3-120b-a12b`
- SC5 `n=5`
- SC5 temperature `0.4`
- frozen item seeds
- strict-majority recommendation
- SC5 agreement definition
- VC prompt
- VC `n=1`
- VC temperature `0`
- malformed semantic-output policy
- quota-handling amendment v1.1
- Calibration-EVAL seal

## Network safety

Actual collection still requires both:

`--collect-dev`

and:

`GATE6D_ALLOW_DEV_COLLECTION=YES`

## Hashes

Collector v1.2:

`25da7632efd3fc49352652c08ce8deed8f09f00d6c16334e56e7d4de2568ac99`

VC prompt:

`51bb3bb0912123a315dba5c34cb08bed103f2a6b51795febbe2125e31cb47f2d`

Collection spec:

`f604cf73fb03d2623cae6e86eecd57ab34956c749ad4e51ec861831930726d61`

## Next step

Resume collection with v1.2 only.

The collector must reuse the 58 selected terminal items and collect only
the remaining 442 selected items.

Calibration-EVAL remains sealed.
