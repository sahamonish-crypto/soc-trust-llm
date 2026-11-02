#!/usr/bin/env python3

"""
Gate 6D synthetic-only DEV analysis integration harness V1.

Purpose:
  Verify the frozen pipeline contract:

    synthetic terminal records
        -> frozen DEV normalization core
        -> paired-common-valid rows
        -> frozen calibration-analysis core
        -> grouped OOF estimator/calibrator metrics
        -> grouped constant baseline
        -> frozen method-selection rule

This V1 does NOT:
- open real DEV SC5/VC terminal files;
- open hidden DEV ground truth;
- open Calibration-EVAL;
- open External-TEST;
- make model calls.

Real analysis remains blocked.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


NORMALIZATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_dev_normalization_core_v1.py"
)

CALIBRATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_calibration_analysis_core.py"
)

AUDIT_TOOL = Path(
    "scripts/gate6/"
    "audit_gate6d_dev500_collection_v1.py"
)

EXPECTED_NORMALIZATION_SHA = (
    "7983ed4320908fd87913bc7a3b031133"
    "50763efb0fed1d8d00ba675da81e7ba0"
)

EXPECTED_CALIBRATION_SHA = (
    "47a03118614e68c000101047c680b3992"
    "9f1355ab9a8f1ba1565abcb81d52eba"
)

EXPECTED_AUDIT_TOOL_SHA = (
    "8df4bf36a3b1bd0213a333f8b9b3deff"
    "f9897e682862856fc35574ad33fa6123"
)

OUT = Path(
    "benchmarks/gate6d/"
    "dev_analysis_integration_v1/"
    "synthetic_self_test.json"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def verify_frozen_component(
    path: Path,
    expected_sha: str,
    name: str,
) -> str:
    if not path.exists():
        raise RuntimeError(
            f"{name} missing: {path}"
        )

    actual = sha256_file(path)

    if actual != expected_sha:
        raise RuntimeError(
            f"{name} SHA mismatch: "
            f"expected {expected_sha}, got {actual}"
        )

    return actual


def load_module(
    path: Path,
    module_name: str,
):
    spec = (
        importlib.util
        .spec_from_file_location(
            module_name,
            path,
        )
    )

    if (
        spec is None
        or spec.loader is None
    ):
        raise RuntimeError(
            f"Unable to import {path}"
        )

    module = (
        importlib.util
        .module_from_spec(spec)
    )

    # Required for Python 3.14 dataclasses and
    # dynamically imported modules.
    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def method_row(r) -> dict:
    return {
        "estimator":
            r.estimator,
        "calibrator":
            r.calibrator,
        "valid":
            bool(r.valid),
        "reason":
            r.reason,
        "n":
            int(r.n),
        "brier":
            (
                float(r.brier)
                if r.valid
                else None
            ),
        "auroc_correct":
            (
                float(
                    r.auroc_correct
                )
                if r.valid
                else None
            ),
        "auprc_incorrect":
            (
                float(
                    r.auprc_incorrect
                )
                if r.valid
                else None
            ),
        "ece10":
            (
                float(r.ece10)
                if r.valid
                else None
            ),
    }


def synthetic_self_test() -> dict:
    normalization_sha = (
        verify_frozen_component(
            NORMALIZATION_CORE,
            EXPECTED_NORMALIZATION_SHA,
            "DEV normalization core",
        )
    )

    calibration_sha = (
        verify_frozen_component(
            CALIBRATION_CORE,
            EXPECTED_CALIBRATION_SHA,
            "calibration-analysis core",
        )
    )

    audit_sha = (
        verify_frozen_component(
            AUDIT_TOOL,
            EXPECTED_AUDIT_TOOL_SHA,
            "DEV500 collection audit tool",
        )
    )

    norm = load_module(
        NORMALIZATION_CORE,
        "gate6d_normalization_frozen_v1",
    )

    cal = load_module(
        CALIBRATION_CORE,
        "gate6d_calibration_frozen_v1",
    )

    # Uses only the normalization core's synthetic
    # fixture. No real collection files are opened.
    fixture = (
        norm.synthetic_fixture()
    )

    normalized = (
        norm.normalize_dev500(
            **fixture
        )
    )

    paired = normalized[
        "paired_rows"
    ]

    if len(paired) != 488:
        raise AssertionError(
            "Expected synthetic paired set n=488."
        )

    correctness = [
        row["correctness"]
        for row in paired
    ]

    folds = [
        row["cv_fold"]
        for row in paired
    ]

    sc5_raw = [
        row["sc5_agreement"]
        for row in paired
    ]

    vc_raw = [
        row["vc_raw_confidence"]
        for row in paired
    ]

    sc5_results = (
        cal.evaluate_estimator(
            "SC5_AGREEMENT",
            sc5_raw,
            correctness,
            folds,
        )
    )

    vc_results = (
        cal.evaluate_estimator(
            "VC_SELF_EVAL",
            vc_raw,
            correctness,
            folds,
        )
    )

    all_results = (
        sc5_results
        + vc_results
    )

    if len(all_results) != 6:
        raise AssertionError(
            "Expected six estimator/calibrator "
            "candidate rows."
        )

    valid_results = [
        r
        for r in all_results
        if r.valid
    ]

    if not valid_results:
        raise AssertionError(
            "Synthetic integration produced no "
            "valid candidate methods."
        )

    baseline_prob = (
        cal.grouped_constant_baseline_oof(
            correctness,
            folds,
        )
    )

    baseline_metrics = (
        cal.metric_bundle(
            cal._as_1d_float(
                correctness
            ),
            baseline_prob,
        )
    )

    selection = (
        cal.select_method(
            all_results
        )
    )

    allowed_estimators = {
        "SC5_AGREEMENT",
        "VC_SELF_EVAL",
    }

    allowed_calibrators = {
        "identity",
        "platt",
        "isotonic",
    }

    if (
        selection[
            "winner_estimator"
        ]
        not in allowed_estimators
    ):
        raise AssertionError(
            "Unexpected synthetic winner estimator."
        )

    if (
        selection[
            "winner_calibrator"
        ]
        not in allowed_calibrators
    ):
        raise AssertionError(
            "Unexpected synthetic winner calibrator."
        )

    if (
        selection["threshold"]
        != 0.01
    ):
        raise AssertionError(
            "Frozen Brier tie threshold mismatch."
        )

    fold_counts = {}

    for fold in folds:
        key = str(int(fold))

        fold_counts[key] = (
            fold_counts.get(
                key,
                0,
            )
            + 1
        )

    expected_paired_folds = {
        "1": 95,
        "2": 99,
        "3": 100,
        "4": 96,
        "5": 98,
    }

    if (
        fold_counts
        != expected_paired_folds
    ):
        raise AssertionError(
            "Synthetic paired fold counts changed."
        )

    return {
        "artifact":
            "GATE6D_DEV_ANALYSIS_INTEGRATION_"
            "SYNTHETIC_TEST_V1",
        "status":
            "PASS",

        "frozen_components": {
            "normalization_core_sha256":
                normalization_sha,
            "calibration_core_sha256":
                calibration_sha,
            "collection_audit_tool_sha256":
                audit_sha,
        },

        "normalization": {
            "selected_items":
                normalized[
                    "summary"
                ][
                    "selected_items"
                ],
            "sc5_valid_items":
                normalized[
                    "summary"
                ][
                    "sc5_valid_items"
                ],
            "vc_valid_items":
                normalized[
                    "summary"
                ][
                    "vc_valid_items"
                ],
            "paired_common_valid_items":
                len(paired),
            "paired_fold_counts":
                fold_counts,
        },

        "analysis": {
            "candidate_rows":
                len(all_results),
            "valid_candidate_rows":
                len(valid_results),
            "constant_baseline": {
                "brier":
                    float(
                        baseline_metrics[
                            "brier"
                        ]
                    ),
                "auroc_correct":
                    float(
                        baseline_metrics[
                            "auroc_correct"
                        ]
                    ),
                "auprc_incorrect":
                    float(
                        baseline_metrics[
                            "auprc_incorrect"
                        ]
                    ),
                "ece10":
                    float(
                        baseline_metrics[
                            "ece10"
                        ]
                    ),
            },
            "candidates": [
                method_row(r)
                for r in all_results
            ],
            "synthetic_selection":
                selection,
        },

        "interpretation": {
            "synthetic_winner_has_no_real_"
            "scientific_meaning":
                True,
            "real_method_selection_performed":
                False,
        },

        "real_dev_outputs_read":
            False,
        "real_dev_ground_truth_read":
            False,
        "correctness_based_real_comparison":
            False,
        "calibration_eval_accessed":
            False,
        "external_test_accessed":
            False,
        "model_calls":
            0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.self_test:
        print(
            "BLOCKED: V1 permits "
            "--self-test only."
        )
        print(
            "Real DEV analysis was NOT run."
        )
        return

    result = synthetic_self_test()

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    selection = (
        result["analysis"][
            "synthetic_selection"
        ]
    )

    print(
        "=== GATE 6D DEV ANALYSIS "
        "INTEGRATION SYNTHETIC TEST ==="
    )
    print(
        "status:",
        result["status"],
    )
    print(
        "paired_common_valid_items:",
        result["normalization"][
            "paired_common_valid_items"
        ],
    )
    print(
        "paired_fold_counts:",
        result["normalization"][
            "paired_fold_counts"
        ],
    )
    print(
        "candidate_rows:",
        result["analysis"][
            "candidate_rows"
        ],
    )
    print(
        "valid_candidate_rows:",
        result["analysis"][
            "valid_candidate_rows"
        ],
    )
    print(
        "constant_baseline_brier:",
        result["analysis"][
            "constant_baseline"
        ]["brier"],
    )
    print(
        "synthetic_winner_estimator:",
        selection[
            "winner_estimator"
        ],
    )
    print(
        "synthetic_winner_calibrator:",
        selection[
            "winner_calibrator"
        ],
    )
    print(
        "selection_reason:",
        selection["reason"],
    )
    print(
        "frozen_brier_tie_threshold:",
        selection["threshold"],
    )
    print(
        "synthetic_winner_has_real_"
        "scientific_meaning: False"
    )
    print(
        "real_dev_outputs_read: False"
    )
    print(
        "real_dev_ground_truth_read: False"
    )
    print(
        "correctness_based_real_comparison: False"
    )
    print(
        "calibration_eval_accessed: False"
    )
    print(
        "external_test_accessed: False"
    )
    print(
        "model_calls: 0"
    )


if __name__ == "__main__":
    main()
