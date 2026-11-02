#!/usr/bin/env python3

"""
Gate 6D real-DEV analysis wrapper V1.

Current safety design:
- synthetic self-test is enabled;
- real DEV analysis is NOT enabled yet;
- real DEV preflight fails closed until a future frozen
  DEV500 collection-complete artifact exists;
- Calibration-EVAL is never accessed here;
- External-TEST is never accessed here.

A later, separately frozen normalization layer will join frozen
DEV500 uncertainty outputs to hidden DEV ground truth and feed the
normalized arrays into the already-frozen calibration core.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np


CORE = Path(
    "scripts/gate6/gate6d_calibration_analysis_core.py"
)

EXPECTED_CORE_SHA = (
    "47a03118614e68c000101047c680b39929f1355ab9a8f1ba1565abcb81d52eba"
)

# This artifact does not exist yet by design.
# It will be created only after all selected DEV500 collection
# outputs are complete and their provenance is frozen.
REQUIRED_COLLECTION_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1.json"
)

REAL_ANALYSIS_ENV = "GATE6D_ALLOW_REAL_DEV_ANALYSIS"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_frozen_core() -> None:
    if not CORE.exists():
        raise RuntimeError(
            "Frozen calibration core is missing."
        )

    actual = sha256(CORE)

    if actual != EXPECTED_CORE_SHA:
        raise RuntimeError(
            "Frozen calibration core SHA mismatch."
        )


def load_core():
    validate_frozen_core()

    spec = importlib.util.spec_from_file_location(
        "gate6d_core",
        CORE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Could not load frozen calibration core."
        )

    module = importlib.util.module_from_spec(spec)

    # Python 3.14 dataclasses expects dynamically imported
    # modules to be registered in sys.modules before execution.
    import sys
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


def real_dev_gate_status() -> dict:
    """
    Metadata-only gate check.

    This function does NOT open raw SC5/VC files,
    hidden ground truth, EVAL, or External-TEST.
    """
    reasons = []

    if os.environ.get(REAL_ANALYSIS_ENV) != "YES":
        reasons.append(
            f"{REAL_ANALYSIS_ENV} is not YES"
        )

    if not REQUIRED_COLLECTION_FREEZE.exists():
        reasons.append(
            "DEV500 collection-complete freeze "
            "artifact does not exist"
        )
    else:
        try:
            obj = json.loads(
                REQUIRED_COLLECTION_FREEZE.read_text(
                    encoding="utf-8"
                )
            )
        except Exception as exc:
            reasons.append(
                "collection freeze unreadable: "
                + type(exc).__name__
            )
        else:
            if obj.get("status") != "FROZEN_COMPLETE":
                reasons.append(
                    "collection freeze status is not "
                    "FROZEN_COMPLETE"
                )

            if obj.get(
                "selected_dev_complete"
            ) != 500:
                reasons.append(
                    "selected_dev_complete is not 500"
                )

    return {
        "allowed": len(reasons) == 0,
        "reasons": reasons,
    }


def synthetic_self_test() -> dict:
    core = load_core()

    rng = np.random.default_rng(20261102)

    fold_counts = [97, 101, 102, 98, 102]

    folds = np.concatenate(
        [
            np.full(n, i + 1, dtype=int)
            for i, n in enumerate(fold_counts)
        ]
    )

    n = len(folds)

    latent = rng.normal(
        loc=0.15,
        scale=1.0,
        size=n,
    )

    correctness = (
        latent
        + rng.normal(
            loc=0.0,
            scale=0.75,
            size=n,
        )
        > 0
    ).astype(int)

    sc_strength = (
        0.64
        + 0.22 * correctness
        + rng.normal(
            0.0,
            0.12,
            n,
        )
    )

    sc5 = np.where(
        sc_strength >= 0.90,
        1.0,
        np.where(
            sc_strength >= 0.74,
            0.8,
            0.6,
        ),
    )

    vc = np.clip(
        0.50
        + 0.33 * correctness
        + rng.normal(
            0.0,
            0.17,
            n,
        ),
        0.0,
        1.0,
    )

    vc = np.round(vc, 2)

    results = []

    results.extend(
        core.evaluate_estimator(
            "SC5_AGREEMENT",
            sc5,
            correctness,
            folds,
        )
    )

    results.extend(
        core.evaluate_estimator(
            "VC_SELF_EVAL",
            vc,
            correctness,
            folds,
        )
    )

    winner = core.select_method(results)

    baseline_p = (
        core.grouped_constant_baseline_oof(
            correctness,
            folds,
        )
    )

    baseline = core.metric_bundle(
        correctness.astype(float),
        baseline_p,
    )

    valid = [
        r
        for r in results
        if r.valid
    ]

    assert n == 500
    assert fold_counts == [
        97, 101, 102, 98, 102
    ]
    assert len(results) == 6
    assert len(valid) >= 4
    assert core.FROZEN_BRIER_TIE_THRESHOLD == 0.01

    gate = real_dev_gate_status()

    # It MUST still be blocked at this stage.
    assert gate["allowed"] is False

    return {
        "artifact":
            "GATE6D_REAL_DEV_WRAPPER_SYNTHETIC_TEST_V1",
        "status": "PASS",
        "frozen_core_sha":
            sha256(CORE),
        "synthetic_rows": 500,
        "fold_counts": fold_counts,
        "candidate_rows": len(results),
        "valid_candidate_rows": len(valid),
        "constant_baseline_brier":
            baseline["brier"],
        "synthetic_winner_estimator":
            winner["winner_estimator"],
        "synthetic_winner_calibrator":
            winner["winner_calibrator"],
        "frozen_brier_tie_threshold":
            winner["threshold"],
        "real_dev_gate_allowed": False,
        "real_dev_gate_reasons":
            gate["reasons"],
        "real_dev_outputs_read": False,
        "real_dev_ground_truth_read": False,
        "correctness_based_real_comparison":
            False,
        "calibration_eval_accessed": False,
        "external_test_accessed": False,
        "model_calls": 0,
    }


def print_real_preflight() -> None:
    validate_frozen_core()

    gate = real_dev_gate_status()

    print(
        "=== GATE 6D REAL-DEV PRE-FLIGHT ==="
    )

    if gate["allowed"]:
        print(
            "REAL DEV GATE: METADATA CONDITIONS SATISFIED"
        )
        print(
            "REAL ANALYSIS STILL DISABLED IN V1."
        )
    else:
        print("REAL DEV GATE: BLOCKED")

        for reason in gate["reasons"]:
            print("-", reason)

    print()
    print("Real DEV outputs read: NO")
    print("Real DEV ground truth read: NO")
    print("Calibration-EVAL accessed: NO")
    print("External-TEST accessed: NO")
    print("Model calls: 0")


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    parser.add_argument(
        "--real-dev-preflight",
        action="store_true",
    )

    args = parser.parse_args()

    if args.self_test:
        result = synthetic_self_test()

        out = Path(
            "benchmarks/gate6d/"
            "real_dev_wrapper_v1/"
            "synthetic_self_test.json"
        )

        out.write_text(
            json.dumps(
                result,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "=== GATE 6D REAL-DEV WRAPPER "
            "SYNTHETIC TEST ==="
        )

        for key, value in result.items():
            print(f"{key}: {value}")

        return

    if args.real_dev_preflight:
        print_real_preflight()
        return

    print(
        "BLOCKED: V1 permits only --self-test "
        "or --real-dev-preflight."
    )
    print("Real DEV analysis was NOT executed.")


if __name__ == "__main__":
    main()
