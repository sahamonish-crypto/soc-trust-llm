# Gate 6D Canonical Inputs, Seeds, and DEV Folds Freeze

**Date:** 2026-11-02
**Status:** FROZEN

## Frozen corpus

- Calibration-DEV: **1,222 items**
- Calibration-EVAL: **458 items**
- Total: **1,680 items**
- Calibration-DEV episode groups: **48**
- Grouped CV folds: **5**

Opaque identifiers are used:

- DEV: `G6D-D-NNNN`
- EVAL: `G6D-E-NNNN`

Ground-truth labels are not encoded in the item identifiers.

## Gate 6C semantic continuity

The Gate 6D model inputs preserve the frozen Gate 6C:

- system prompt;
- alert-card schema;
- deterministic primary-alert selection;
- anchor construction;
- ±30-second evidence window;
- exact-CID then endpoint-pair retrieval priority;
- evidence pattern deduplication;
- maximum six evidence patterns;
- user-message structure.

The canonical prompt SHA256 is:

`58c21362374142766269d0b11cba538b257a16a82df9f4bc679329c1deafd3c0`

One source-scoping safety adaptation is required because different frozen
Windows capture files contain overlapping Community IDs. First-pass
alert/flow lookup is therefore keyed by `(source_path, community_id)`.
This prevents cross-capture event mixing and does not change the intended
per-source Gate 6C model-visible semantics.

## SC5 seed freeze

For every opaque item ID:

`SHA256(UTF8("GATE6D_SC5_V1|" + item_id))`

The first four digest bytes are interpreted as an unsigned big-endian
integer, the sign bit is cleared using `& 0x7fffffff`, and zero is replaced
with one.

All 1,680 generated seeds are unique.

## Grouped DEV folds

Grouping unit:

`capture + episode_start_utc`

Fold assignment is deterministic and outcome-blind. It does not use:

- ground truth;
- model predictions;
- model correctness;
- confidence estimates;
- calibration performance.

Frozen item counts:

- Fold 1: **237**
- Fold 2: **249**
- Fold 3: **249**
- Fold 4: **238**
- Fold 5: **249**

No episode group spans multiple folds.

## Calibration-EVAL seal

EVAL model inputs and manifests are frozen now for reproducibility, but
they remain operationally sealed.

Before the DEV-selected estimator and calibration mapping are formally
frozen, the project must not:

- run model inference on Calibration-EVAL;
- inspect EVAL model correctness;
- score uncertainty/calibration on EVAL;
- use EVAL to choose an estimator;
- use EVAL to choose a calibrator;
- use EVAL to choose thresholds or tie-breaks.

The hidden EVAL ground-truth mapping exists only to bind the future
single untouched evaluation deterministically. Its contents must not be
used during DEV method selection.

## Deterministic rebuild

The canonical builder reproduced all eight primary generated artifacts
byte-for-byte on an immediate second build.

Builder SHA256:

`2c4a2eb3d32781ed4f0f6ac021fd6a43ec6ecfd0a256fa4033cab99b03ddc429`

## Important canonical hashes

DEV model inputs:

`f861b49f8d829d05aa0c788e59bbb16e377633ddd57e6e45c346d7abc7e5b45b`

Sealed EVAL model inputs:

`ba9870fcb9223fb3acc46e87a24b6f8c490171b79cc49c08fc433bd7d4ef8d9c`

DEV collection manifest:

`de9bcd31706393abc9c42c249b4bc463e9542a0a34b3705d9aec9acc9ca19626`

Sealed EVAL manifest:

`084501099471ec1b5289cd99e44305e9c824bea62676f389b8d13485544636a7`

DEV grouped folds:

`a50dad3c2c03b1ae78fe42ad6bc77430bb0b7bd2278ce2d3c0a331588d0e4d6f`

Hidden DEV ground truth:

`db3d294d5d5e0653834241b3415f82795ab2d8a3287743a4de7506ae6e3ae40e`

Hidden EVAL ground truth:

`9ffb438d26a7f0b1e9d981998c66edab1c96a1348a90db0eb5769bc674e6ed55`

## Collection state at freeze

- Calibration-DEV model calls: **0**
- Calibration-EVAL model calls: **0**
- External-TEST accessed: **NO**

## Next step

Implement and preflight the frozen Calibration-DEV collection procedure:

1. `SC5_MAJORITY`, five samples per DEV item;
2. `SC5_AGREEMENT`;
3. separate deterministic `VC_SELF_EVAL`;
4. no EVAL access.

No Gate 7 work begins here.
