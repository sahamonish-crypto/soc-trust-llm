# Gate 6D DEV Collection Protocol Freeze

**Date:** 2026-11-02
**Status:** FROZEN

## Scope

This freeze governs model collection on Calibration-DEV only.

Calibration-EVAL remains sealed.

## Model

`@cf/nvidia/nemotron-3-120b-a12b`

## SC5_MAJORITY

For each of the 1,222 frozen DEV items:

- `n = 5`
- temperature `0.4`
- max completion tokens `512`
- thinking enabled
- low effort enabled
- streaming disabled
- frozen item-specific seed

All five returned choices must be exact labels:

- `ESCALATE`
- `DO_NOT_ESCALATE`

Any HTTP-200 semantic malformation is terminal for that logical
collection result and is not silently regenerated.

The frozen recommendation is the strict majority of the five valid
samples.

`SC5_AGREEMENT = majority vote count / 5`.

## VC_SELF_EVAL

A separate deterministic request evaluates the probability that the
already-frozen SC5 majority recommendation is correct.

- `n = 1`
- temperature `0`
- max completion tokens `512`
- thinking enabled
- low effort enabled
- output must be exactly one integer from 0 through 100
- raw confidence = integer / 100
- the recommendation cannot be changed

VC prompt SHA256:

`51bb3bb0912123a315dba5c34cb08bed103f2a6b51795febbe2125e31cb47f2d`

## Retry / resume policy

Retryable infrastructure failures:

- transport/status 0;
- HTTP 429;
- HTTP 5xx.

HTTP-200 malformed outputs are semantic invalids, not retryable
infrastructure failures.

Cloudflare internal code 3036 causes a clean session pause without
resolving or changing the logical item.

Terminal SC5/VC records are not recollected during resume.

## EVAL seal

The collector contains no reference to:

- sealed EVAL model inputs;
- sealed EVAL manifest;
- hidden EVAL ground truth.

Calibration-EVAL inference and scoring remain prohibited until the
DEV-selected estimator and calibration mapping are formally frozen.

## Network safety

Collection requires both:

`--collect-dev`

and

`GATE6D_ALLOW_DEV_COLLECTION=YES`

The explicit gate was tested before this freeze.

## Hashes

Collector:

`fd942351e591877429469b3f5b54fc3d7e7afbd54ea6f8bd71e1efc5d922e1f2`

VC prompt:

`51bb3bb0912123a315dba5c34cb08bed103f2a6b51795febbe2125e31cb47f2d`

Collection specification:

`848455c1ad80bb64551f9675d097147567d63dff028c9c9e0bb231c0df924b3b`

Canonical-input freeze:

`4c92b50fe1bd909d13b9b80df8624acd6982cf00f31af32363e0990a95e9c87c`

## State at freeze

- Calibration-DEV model calls: 0
- Calibration-EVAL model calls: 0
- External-TEST accessed: NO

## Next step

Begin frozen DEV-only collection. Do not access Calibration-EVAL.
