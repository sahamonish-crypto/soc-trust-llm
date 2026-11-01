# Gate 6D Alert-Card Validity Freeze

**Date:** 2026-11-02
**Status:** FROZEN — PASS WITH CAVEAT

## Result

The model-visible primary-alert validity gate passes with a documented
caveat.

Across all 1,680 frozen Gate 6D calibration items:

- direct ground-truth leakage flag: 0 / 1,680;
- Tier-A overt-cue flag: 4 / 1,680;
- Tier-B strong-cue flag: 18 / 1,680;
- any historical Tier-A/Tier-B cue: 21 / 1,680;
- current high-specificity lexical cue union: 6 / 1,680.

The current lexical review was outcome-blind and did not use model
correctness, calibration performance, or item ground-truth labels.

## Frozen decision

Retain the entire frozen calibration pool.

Do not:

- remove cue-flagged items;
- remove the six high-specificity lexical-cue items;
- mask or rewrite primary signatures;
- mask or rewrite categories;
- change the frozen Gate 6C alert-card schema.

No eligible item was established as direct answer leakage. Rare strong
NIDS cues are retained as realistic SOC telemetry.

## Reporting caveat

The final methods/limitations record must disclose that a small fraction
of cases contain high-specificity security wording, while no frozen
eligible case was identified as direct ground-truth leakage by the
pre-existing audit.

## Collection state

- Calibration-DEV model calls: 0
- Calibration-EVAL model calls: 0
- External-TEST accessed: NO

## Next step

Before the first Calibration-DEV inference, freeze:

1. canonical Gate 6D model-visible inputs;
2. opaque item IDs;
3. deterministic SC5 item seeds;
4. grouped five-fold Calibration-DEV assignments;
5. sealed Calibration-EVAL manifest.
