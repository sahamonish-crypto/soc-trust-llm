# Gate 6D Canonical Source Binding Freeze

**Date:** 2026-11-02  
**Status:** FROZEN

## Purpose

Freeze the exact Suricata `eve.json` sources used to construct Gate 6D
Calibration-DEV and Calibration-EVAL model inputs before any calibration
model inference.

## Selected canonical sources

- `AmazonEcho-2023-02-21`
  - `data/processed/gate5/run3-single/eve.json`
  - SHA256 `5cd3457fa55c55c92727379e4a8fbf840f94cbd8127a74dfdd93be414f1e06f4`

- `Windows7AD-2023-02-21`
  - `data/processed/gate5/windows7ad-2023-02-21-run1/eve.json`
  - SHA256 `b76860bfc4bd48b0c84bd4fbb85b9b40b3850bcbd5a68ba77f69df0fa1a03736`

- `Windows7AD-2023-02-22`
  - `data/processed/gate5/windows7ad-2023-02-22-run1/eve.json`
  - SHA256 `de33c0bcd08c9fa56fea630666f2dd32fdc14d179eed439cbbe0651849336331`

## Amazon provenance resolution

Historical provenance could not be uniquely reconstructed.

Six Amazon EVE files contained all frozen Community IDs. Two candidates
(`run1` and `run2`) failed to reproduce 47/885 pre-existing audit
`event_types` / core rows and were excluded.

The remaining four candidates all satisfied the predeclared outcome-blind
operational qualification criteria:

- 885/885 Community-ID coverage;
- 885/885 cases with alert plus flow;
- 299/299 frozen rich-context eligible cases with rich evidence;
- zero malformed JSON records;
- 885/885 reproduction of the recoverable pre-existing core audit fields.

The four qualified files were not byte-identical and did not produce
identical model-relevant projections. The historical audit's signature
strings were not reproduced by any candidate, so signature similarity
could not identify historical provenance.

To prevent post-hoc source shopping, the deterministic tie-break was
frozen **before any calibration inference**:

> Among operationally qualified Amazon sources, sort normalized
> repository-relative EVE paths lexicographically ascending and select
> the first.

This selects:

`data/processed/gate5/run3-single/eve.json`

The tie-break did not use model output, model correctness, calibration
performance, or malicious/benign composition.

## Windows provenance

Each Windows capture had exactly one full Community-ID source:

- 2023-02-21 → `windows7ad-2023-02-21-run1/eve.json`
- 2023-02-22 → `windows7ad-2023-02-22-run1/eve.json`

## Required next validity gate

This freeze establishes **source identity only**.

It does **not** establish that the selected files' model-visible alert
signatures are free from answer leakage. Because the historical audit
signature strings do not match these EVE files, source-specific
alert-card/signature leakage must be validated before canonical Gate 6D
inputs are frozen or any Calibration-DEV inference is made.

Failure of that validity gate must stop collection and trigger explicit
protocol review. It must not trigger source-shopping among the previously
rejected/tied EVE files.

## Prior frozen bindings

- Calibration data boundary SHA256: `8b5ed36ad1561f3afe78b0d44f29f27ace5f0748ff0074ad64d678840866a3b8`
- Uncertainty estimator protocol SHA256: `e80093b719f63647d102d5d95d8990cc1e9f08eb872a2bf2d7e90379560b573d`

## Collection state at freeze

- Calibration-DEV model calls: **0**
- Calibration-EVAL model calls: **0**
- External-TEST accessed: **NO**
