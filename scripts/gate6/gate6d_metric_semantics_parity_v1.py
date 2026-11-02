#!/usr/bin/env python3

"""
Gate 6D metric-semantics parity bridge V1.

Synthetic-only compatibility proof between:

1. frozen calibration-analysis metric_bundle(y, p), and
2. frozen secondary-uncertainty metric_bundle(y, p, weights).

Primary question:
Does an integer bootstrap multiplicity weight produce exactly the same
metric semantics as explicitly duplicating the corresponding rows?

Metrics checked:
- Brier correctness
- AUROC correctness
- AUPRC incorrect-positive using 1-p
- fixed-bin ECE10

Also explicitly checks ECE boundary membership at
0.0, 0.1, ..., 1.0.

No real DEV/EVAL/Test data is loaded.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np


CALIBRATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_calibration_analysis_core.py"
)

UNCERTAINTY_CORE = Path(
    "scripts/gate6/"
    "gate6d_secondary_uncertainty_core_v1.py"
)

OUT = Path(
    "benchmarks/gate6d/"
    "metric_semantics_parity_v1/"
    "synthetic_self_test.json"
)

EXPECTED_CALIBRATION_SHA = (
    "47a03118614e68c000101047c680b3992"
    "9f1355ab9a8f1ba1565abcb81d52eba"
)

EXPECTED_UNCERTAINTY_SHA = (
    "b4bda1429f8476081bd2dc03ed3834f"
    "07a018426b65199fa5873a29560e2b008"
)

METRICS = (
    "brier",
    "auroc_correct",
    "auprc_incorrect",
    "ece10",
)

ABS_TOL = 1e-12


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def verify_file(
    path: Path,
    expected: str,
    label: str,
) -> str:
    if not path.exists():
        raise RuntimeError(
            f"{label} missing: {path}"
        )

    actual = sha256_file(path)

    if actual != expected:
        raise RuntimeError(
            f"{label} SHA mismatch: "
            f"expected {expected}; got {actual}"
        )

    return actual


def load_module(
    path: Path,
    module_name: str,
):
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Cannot import {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[module_name] = module

    spec.loader.exec_module(
        module
    )

    return module


def metric_equal(
    a,
    b,
    tol=ABS_TOL,
) -> tuple[bool, float | None]:
    a = float(a)
    b = float(b)

    if math.isnan(a) and math.isnan(b):
        return True, None

    if (
        not math.isfinite(a)
        or not math.isfinite(b)
    ):
        return a == b, None

    diff = abs(a - b)

    return diff <= tol, diff


def compare_bundles(
    calibration_result: dict,
    uncertainty_result: dict,
) -> dict:
    details = {}
    maximum = 0.0

    for metric in METRICS:
        ok, diff = metric_equal(
            calibration_result[metric],
            uncertainty_result[metric],
        )

        if not ok:
            raise AssertionError(
                f"Metric parity failure for {metric}: "
                f"calibration={calibration_result[metric]!r}; "
                f"uncertainty={uncertainty_result[metric]!r}"
            )

        details[metric] = {
            "equal":
                True,
            "calibration":
                (
                    None
                    if math.isnan(
                        float(
                            calibration_result[
                                metric
                            ]
                        )
                    )
                    else float(
                        calibration_result[
                            metric
                        ]
                    )
                ),
            "uncertainty":
                (
                    None
                    if math.isnan(
                        float(
                            uncertainty_result[
                                metric
                            ]
                        )
                    )
                    else float(
                        uncertainty_result[
                            metric
                        ]
                    )
                ),
            "absolute_difference":
                diff,
        }

        if diff is not None:
            maximum = max(
                maximum,
                diff,
            )

    return {
        "metrics":
            details,
        "max_absolute_difference":
            maximum,
    }


def expand_integer_weights(
    y,
    p,
    weights,
):
    y = np.asarray(
        y,
        dtype=float,
    )

    p = np.asarray(
        p,
        dtype=float,
    )

    w = np.asarray(
        weights,
        dtype=int,
    )

    if np.any(w < 0):
        raise ValueError(
            "Negative multiplicity."
        )

    return (
        np.repeat(
            y,
            w,
        ),
        np.repeat(
            p,
            w,
        ),
    )


def run_weighted_case(
    name: str,
    calibration,
    uncertainty,
    y,
    p,
    weights,
) -> dict:
    y = np.asarray(
        y,
        dtype=float,
    )

    p = np.asarray(
        p,
        dtype=float,
    )

    weights = np.asarray(
        weights,
        dtype=int,
    )

    expanded_y, expanded_p = (
        expand_integer_weights(
            y,
            p,
            weights,
        )
    )

    if len(expanded_y) == 0:
        raise ValueError(
            "Synthetic expanded case is empty."
        )

    weighted = uncertainty.metric_bundle(
        y,
        p,
        weights=weights.astype(
            float
        ),
    )

    duplicated = calibration.metric_bundle(
        expanded_y,
        expanded_p,
    )

    comparison = compare_bundles(
        duplicated,
        weighted,
    )

    return {
        "name":
            name,
        "source_rows":
            int(len(y)),
        "expanded_rows":
            int(len(expanded_y)),
        "weight_sum":
            int(weights.sum()),
        "zero_weight_rows":
            int(
                np.sum(
                    weights == 0
                )
            ),
        "comparison":
            comparison,
    }


def run_unweighted_case(
    name: str,
    calibration,
    uncertainty,
    y,
    p,
) -> dict:
    y = np.asarray(
        y,
        dtype=float,
    )

    p = np.asarray(
        p,
        dtype=float,
    )

    c = calibration.metric_bundle(
        y,
        p,
    )

    u = uncertainty.metric_bundle(
        y,
        p,
    )

    comparison = compare_bundles(
        c,
        u,
    )

    return {
        "name":
            name,
        "rows":
            int(len(y)),
        "comparison":
            comparison,
    }


def boundary_case(
    calibration,
    uncertainty,
) -> dict:
    # Use the exact same floating-point edges generated
    # by the frozen implementation.
    p = np.linspace(
        0.0,
        1.0,
        11,
    )

    y = np.asarray(
        [
            0, 1, 0, 1, 0, 1,
            0, 1, 0, 1, 0,
        ],
        dtype=float,
    )

    weights = np.asarray(
        [
            1, 2, 3, 1, 4, 2,
            5, 1, 3, 2, 4,
        ],
        dtype=int,
    )

    result = run_weighted_case(
        "all_fixed_ece_boundaries",
        calibration,
        uncertainty,
        y,
        p,
        weights,
    )

    expanded_y, expanded_p = (
        expand_integer_weights(
            y,
            p,
            weights,
        )
    )

    reliability = (
        calibration.reliability_table(
            expanded_y,
            expanded_p,
        )
    )

    observed_counts = [
        int(row["n"])
        for row in reliability
    ]

    expected_counts = [
        int(weights[0]),
        int(weights[1]),
        int(weights[2]),
        int(weights[3]),
        int(weights[4]),
        int(weights[5]),
        int(weights[6]),
        int(weights[7]),
        int(weights[8]),
        int(weights[9] + weights[10]),
    ]

    if observed_counts != expected_counts:
        raise AssertionError(
            "ECE boundary-bin assignment mismatch: "
            f"expected {expected_counts}, "
            f"observed {observed_counts}"
        )

    result[
        "boundary_semantics"
    ] = {
        "edges":
            [
                float(x)
                for x in p
            ],

        "rule":
            "[0,.1), [.1,.2), ..., [.9,1.0]",

        "expected_expanded_bin_counts":
            expected_counts,

        "observed_calibration_bin_counts":
            observed_counts,

        "boundary_membership":
            "PASS",
    }

    return result


def random_integer_weight_cases(
    calibration,
    uncertainty,
) -> list[dict]:
    rng = np.random.default_rng(
        20261103
    )

    cases = []

    for case_number in range(
        1,
        26,
    ):
        n = 37

        y = rng.integers(
            0,
            2,
            size=n,
        ).astype(float)

        # Guarantee both classes.
        y[0] = 0.0
        y[1] = 1.0

        # Rounded probabilities deliberately create ties.
        p = np.round(
            rng.uniform(
                0.0,
                1.0,
                size=n,
            ),
            2,
        )

        weights = rng.integers(
            0,
            6,
            size=n,
        )

        # Guarantee active observations from both classes.
        weights[0] = max(
            1,
            int(weights[0]),
        )

        weights[1] = max(
            1,
            int(weights[1]),
        )

        cases.append(
            run_weighted_case(
                f"random_integer_weights_{case_number:02d}",
                calibration,
                uncertainty,
                y,
                p,
                weights,
            )
        )

    return cases


def self_test() -> dict:
    calibration_sha = verify_file(
        CALIBRATION_CORE,
        EXPECTED_CALIBRATION_SHA,
        "frozen calibration core",
    )

    uncertainty_sha = verify_file(
        UNCERTAINTY_CORE,
        EXPECTED_UNCERTAINTY_SHA,
        "frozen secondary uncertainty core",
    )

    calibration = load_module(
        CALIBRATION_CORE,
        "gate6d_calibration_core_parity_v1",
    )

    uncertainty = load_module(
        UNCERTAINTY_CORE,
        "gate6d_uncertainty_core_parity_v1",
    )

    unweighted = []

    unweighted.append(
        run_unweighted_case(
            "ordinary_unweighted",
            calibration,
            uncertainty,
            [
                0, 1, 0, 1, 1,
                0, 1, 0, 1, 0,
            ],
            [
                0.08, 0.91, 0.32, 0.73, 0.62,
                0.47, 0.88, 0.21, 0.55, 0.39,
            ],
        )
    )

    unweighted.append(
        run_unweighted_case(
            "ties_unweighted",
            calibration,
            uncertainty,
            [
                0, 1, 0, 1,
                0, 1, 0, 1,
            ],
            [
                0.2, 0.2, 0.5, 0.5,
                0.8, 0.8, 0.8, 0.8,
            ],
        )
    )

    unweighted.append(
        run_unweighted_case(
            "all_correct",
            calibration,
            uncertainty,
            [1, 1, 1, 1, 1],
            [0.5, 0.6, 0.7, 0.8, 0.9],
        )
    )

    unweighted.append(
        run_unweighted_case(
            "all_incorrect",
            calibration,
            uncertainty,
            [0, 0, 0, 0, 0],
            [0.1, 0.2, 0.3, 0.4, 0.5],
        )
    )

    weighted = []

    weighted.append(
        run_weighted_case(
            "ordinary_integer_multiplicity",
            calibration,
            uncertainty,
            [
                0, 1, 0, 1, 1, 0,
            ],
            [
                0.15, 0.83, 0.41,
                0.71, 0.60, 0.28,
            ],
            [
                1, 4, 2, 3, 5, 2,
            ],
        )
    )

    weighted.append(
        run_weighted_case(
            "zero_weight_rows",
            calibration,
            uncertainty,
            [
                0, 1, 1, 0, 1, 0,
            ],
            [
                0.05, 0.95, 0.65,
                0.35, 0.75, 0.25,
            ],
            [
                0, 3, 2, 4, 1, 0,
            ],
        )
    )

    weighted.append(
        run_weighted_case(
            "weighted_ties",
            calibration,
            uncertainty,
            [
                0, 1, 0, 1, 0, 1,
            ],
            [
                0.25, 0.25, 0.50,
                0.50, 0.75, 0.75,
            ],
            [
                5, 2, 4, 3, 1, 6,
            ],
        )
    )

    boundaries = boundary_case(
        calibration,
        uncertainty,
    )

    random_cases = (
        random_integer_weight_cases(
            calibration,
            uncertainty,
        )
    )

    all_cases = (
        unweighted
        + weighted
        + [boundaries]
        + random_cases
    )

    maximum_difference = 0.0

    for case in all_cases:
        d = (
            case[
                "comparison"
            ][
                "max_absolute_difference"
            ]
        )

        maximum_difference = max(
            maximum_difference,
            float(d),
        )

    # Explicit fail-closed input tests for the weighted core.
    fail_closed = 0

    try:
        uncertainty.metric_bundle(
            [0, 1],
            [0.2, 0.8],
            weights=[0, 0],
        )
    except ValueError:
        fail_closed += 1

    try:
        uncertainty.metric_bundle(
            [0, 1],
            [0.2, 0.8],
            weights=[1, -1],
        )
    except ValueError:
        fail_closed += 1

    try:
        uncertainty.metric_bundle(
            [0, 1],
            [0.2, 1.2],
            weights=[1, 1],
        )
    except ValueError:
        fail_closed += 1

    if fail_closed != 3:
        raise AssertionError(
            "Weighted metric fail-closed checks failed."
        )

    return {
        "artifact":
            "GATE6D_METRIC_SEMANTICS_PARITY_"
            "SYNTHETIC_SELF_TEST_V1",

        "status":
            "PASS",

        "frozen_dependencies": {
            "calibration_core_sha256":
                calibration_sha,
            "secondary_uncertainty_core_sha256":
                uncertainty_sha,
        },

        "comparison_definition":
            "secondary metric_bundle(y,p,integer_weights) "
            "versus frozen calibration metric_bundle on "
            "explicitly duplicated rows",

        "absolute_tolerance":
            ABS_TOL,

        "metrics": list(
            METRICS
        ),

        "unweighted_cases":
            unweighted,

        "weighted_cases":
            weighted,

        "ece_boundary_case":
            boundaries,

        "random_integer_weight_cases":
            random_cases,

        "total_parity_cases":
            len(all_cases),

        "random_parity_cases":
            len(random_cases),

        "maximum_absolute_metric_difference":
            maximum_difference,

        "weighted_multiplicity_equivalent_to_row_duplication":
            True,

        "average_precision_weighting_parity":
            True,

        "auroc_weighting_parity":
            True,

        "ece10_weighting_parity":
            True,

        "brier_weighting_parity":
            True,

        "ece_fixed_boundary_semantics":
            "PASS",

        "fail_closed_input_tests":
            fail_closed,

        "real_dev_outputs_read":
            False,

        "real_dev_ground_truth_read":
            False,

        "calibration_eval_accessed":
            False,

        "external_test_accessed":
            False,

        "model_calls":
            0,

        "gate7_opened":
            False,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.self_test:
        print(
            "BLOCKED: V1 permits --self-test only."
        )
        print(
            "No real DEV/EVAL/Test metric analysis was run."
        )
        return

    result = self_test()

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

    print(
        "=== GATE 6D METRIC-SEMANTICS "
        "PARITY SYNTHETIC TEST ==="
    )
    print(
        "status:",
        result["status"],
    )
    print(
        "total_parity_cases:",
        result["total_parity_cases"],
    )
    print(
        "random_parity_cases:",
        result["random_parity_cases"],
    )
    print(
        "metrics:",
        ", ".join(
            result["metrics"]
        ),
    )
    print(
        "weighted multiplicity == "
        "explicit row duplication:",
        result[
            "weighted_multiplicity_equivalent_to_row_duplication"
        ],
    )
    print(
        "AUPRC weighting parity:",
        result[
            "average_precision_weighting_parity"
        ],
    )
    print(
        "AUROC weighting parity:",
        result[
            "auroc_weighting_parity"
        ],
    )
    print(
        "ECE10 weighting parity:",
        result[
            "ece10_weighting_parity"
        ],
    )
    print(
        "Brier weighting parity:",
        result[
            "brier_weighting_parity"
        ],
    )
    print(
        "ECE boundary semantics:",
        result[
            "ece_fixed_boundary_semantics"
        ],
    )
    print(
        "maximum absolute metric difference:",
        result[
            "maximum_absolute_metric_difference"
        ],
    )
    print(
        "fail_closed_input_tests:",
        result[
            "fail_closed_input_tests"
        ],
        "PASS",
    )
    print(
        "real_dev_outputs_read: False"
    )
    print(
        "real_dev_ground_truth_read: False"
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
    print(
        "gate7_opened: False"
    )


if __name__ == "__main__":
    main()
