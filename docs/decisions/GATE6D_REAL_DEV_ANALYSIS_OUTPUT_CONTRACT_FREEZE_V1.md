# Gate 6D Real DEV Analysis Output Contract Freeze V1

Status: FROZEN PROSPECTIVE PRE-REAL-DEV-ANALYSIS

This decision freezes the real DEV analysis/output contract before any real DEV correctness-bearing analysis.

Frozen rules:

- Primary population: PAIRED_COMMON_VALID.
- Candidate slots: 6 total:
  - SC5_AGREEMENT × identity / Platt / isotonic
  - VC_SELF_EVAL × identity / Platt / isotonic
- Primary selection remains grouped 5-fold OOF Brier.
- Effective Brier tie remains abs(delta) < 0.01.
- First tie-break is higher AUROC correctness.
- Remaining estimator tie-break is SC5_AGREEMENT.
- Coverage cannot change the winner.
- Secondary uncertainty cannot change the winner.
- Post-selection refit uses ALL_VALID_DEV_FOR_WINNING_ESTIMATOR.
- Item-level grouped-OOF predictions must be preserved.
- Secondary uncertainty must use frozen OOF predictions without recalibration, CV rerun, estimator refit, or reselection.

Transaction rule:

`benchmarks/gate6d/GATE6D_DEV_OOF_PREDICTIONS_FREEZE_V1.json`

is the final scientific commit marker.

The DEV method-freeze artifact alone cannot unlock Calibration-EVAL.
Partial files created before the commit marker are scientifically invalid and cannot be consumed by EVAL or secondary uncertainty analysis.

Current safety state:

- DEV500 collection-complete freeze: absent
- Real DEV method freeze: absent
- Real DEV OOF predictions: absent
- Real DEV OOF commit marker: absent
- Real DEV outputs opened: no
- Hidden DEV ground truth opened: no
- Calibration-EVAL accessed: no
- External-TEST accessed: no
- Model calls: 0
- Gate 7 opened: no
