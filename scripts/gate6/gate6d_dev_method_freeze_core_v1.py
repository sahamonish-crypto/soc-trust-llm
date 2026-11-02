#!/usr/bin/env python3

"""
Gate 6D DEV method-freeze core V1.

SYNTHETIC-ONLY command-line interface.

Purpose
-------
Convert already-normalized DEV rows into the future immutable
method-selection result that will unlock Calibration-EVAL.

Frozen semantics:
- primary comparison uses paired-common-valid DEV observations;
- SC5_AGREEMENT and VC_SELF_EVAL each evaluate
  identity / Platt / eligible isotonic calibration;
- grouped 5-fold OOF Brier is primary;
- frozen 0.01 effective-tie rule;
- AUROC correctness first tie-break;
- SC5_AGREEMENT remaining tie-break;
- coverage does not alter winner;
- post-selection refit uses ALL valid DEV observations
  available for the winning estimator;
- empirical correctness prevalence is frozen from that same
  winner-valid refit population for later EVAL constant baseline.

This module does NOT:
- load real DEV files;
- load hidden real DEV ground truth;
- access Calibration-EVAL;
- access External-TEST;
- make model calls;
- open Gate 7.
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


NORMALIZATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_dev_normalization_core_v1.py"
)

CALIBRATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_calibration_analysis_core.py"
)

INVALID_POLICY = Path(
    "benchmarks/gate6d/"
    "GATE6D_INVALID_OUTPUT_COMPARISON_POLICY_V1.json"
)

EXPECTED_NORMALIZATION_SHA = (
    "7983ed4320908fd87913bc7a3b031133"
    "50763efb0fed1d8d00ba675da81e7ba0"
)

EXPECTED_CALIBRATION_SHA = (
    "47a03118614e68c000101047c680b3992"
    "9f1355ab9a8f1ba1565abcb81d52eba"
)

EXPECTED_INVALID_POLICY_SHA = (
    "afeb4cc1919c79014998db090410092c3"
    "7e45d342036712f2ba9d2f0b0e0a0b1"
)

OUT = Path(
    "benchmarks/gate6d/"
    "dev_method_freeze_v1/"
    "synthetic_self_test.json"
)


def sha256_file(
    path: Path,
) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def item_id_set_sha256(
    rows: list[dict],
) -> str:
    ids = sorted(
        row["item_id"]
        for row in rows
    )

    if len(ids) != len(set(ids)):
        raise ValueError(
            "Duplicate item_id in analysis population."
        )

    text = (
        "\n".join(ids)
        + "\n"
    )

    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def verify_frozen_inputs() -> dict:
    checks = {
        "normalization_core": (
            NORMALIZATION_CORE,
            EXPECTED_NORMALIZATION_SHA,
        ),
        "calibration_core": (
            CALIBRATION_CORE,
            EXPECTED_CALIBRATION_SHA,
        ),
        "invalid_output_policy": (
            INVALID_POLICY,
            EXPECTED_INVALID_POLICY_SHA,
        ),
    }

    actual = {}

    for name, (
        path,
        expected,
    ) in checks.items():

        if not path.exists():
            raise RuntimeError(
                f"Missing frozen dependency: {path}"
            )

        digest = sha256_file(
            path
        )

        if digest != expected:
            raise RuntimeError(
                f"{name} SHA mismatch: "
                f"expected {expected}, got {digest}"
            )

        actual[name] = digest

    policy = json.loads(
        INVALID_POLICY.read_text(
            encoding="utf-8"
        )
    )

    assert (
        policy["status"]
        == "FROZEN"
    )

    assert (
        policy[
            "primary_estimator_comparison"
        ][
            "analysis_set"
        ]
        == "PAIRED_COMMON_VALID"
    )

    assert (
        policy[
            "coverage_reporting"
        ][
            "coverage_used_to_change_winner"
        ]
        is False
    )

    assert (
        policy[
            "post_selection_refit"
        ][
            "consistency_with_parent_protocol"
        ]
        is True
    )

    return actual


def load_module(
    path: Path,
    name: str,
):
    spec = (
        importlib.util
        .spec_from_file_location(
            name,
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
        .module_from_spec(
            spec
        )
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def json_float(
    value,
):
    value = float(value)

    if not math.isfinite(
        value
    ):
        return None

    return value


def candidate_record(
    result,
) -> dict:
    return {
        "estimator":
            result.estimator,
        "calibrator":
            result.calibrator,
        "valid":
            bool(
                result.valid
            ),
        "reason":
            result.reason,
        "n":
            int(
                result.n
            ),
        "brier":
            (
                json_float(
                    result.brier
                )
                if result.valid
                else None
            ),
        "auroc_correct":
            (
                json_float(
                    result.auroc_correct
                )
                if result.valid
                else None
            ),
        "auprc_incorrect":
            (
                json_float(
                    result.auprc_incorrect
                )
                if result.valid
                else None
            ),
        "ece10":
            (
                json_float(
                    result.ece10
                )
                if result.valid
                else None
            ),
    }


def metric_record(
    metrics: dict,
) -> dict:
    return {
        "brier":
            json_float(
                metrics[
                    "brier"
                ]
            ),
        "auroc_correct":
            json_float(
                metrics[
                    "auroc_correct"
                ]
            ),
        "auprc_incorrect":
            json_float(
                metrics[
                    "auprc_incorrect"
                ]
            ),
        "ece10":
            json_float(
                metrics[
                    "ece10"
                ]
            ),
    }


def evaluate_primary(
    normalized: dict,
    cal,
) -> dict:
    paired = normalized[
        "paired_rows"
    ]

    if not paired:
        raise ValueError(
            "Paired common-valid population is empty."
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
        row[
            "vc_raw_confidence"
        ]
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

    results = (
        sc5_results
        + vc_results
    )

    if len(results) != 6:
        raise AssertionError(
            "Expected exactly six candidate rows."
        )

    selection = (
        cal.select_method(
            results
        )
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

    winner_matches = [
        r
        for r in results
        if (
            r.estimator
            == selection[
                "winner_estimator"
            ]
            and r.calibrator
            == selection[
                "winner_calibrator"
            ]
            and r.valid
        )
    ]

    if len(
        winner_matches
    ) != 1:
        raise RuntimeError(
            "Selected method does not map to exactly "
            "one valid candidate row."
        )

    return {
        "paired_rows":
            paired,
        "candidate_objects":
            results,
        "candidate_records": [
            candidate_record(r)
            for r in results
        ],
        "selection":
            selection,
        "winner_candidate":
            winner_matches[0],
        "constant_baseline":
            metric_record(
                baseline_metrics
            ),
    }


def winner_valid_rows(
    normalized: dict,
    winner_estimator: str,
) -> list[dict]:
    if (
        winner_estimator
        == "SC5_AGREEMENT"
    ):
        rows = normalized[
            "sc5_all_valid_rows"
        ]

    elif (
        winner_estimator
        == "VC_SELF_EVAL"
    ):
        # By the frozen invalid-output policy,
        # all valid VC items are the paired-common-valid
        # population: VC only exists after valid SC5.
        rows = normalized[
            "paired_rows"
        ]

    else:
        raise ValueError(
            "Unknown winner estimator: "
            + repr(
                winner_estimator
            )
        )

    if not rows:
        raise ValueError(
            "Winner-valid refit population is empty."
        )

    ids = [
        row["item_id"]
        for row in rows
    ]

    if len(ids) != len(
        set(ids)
    ):
        raise ValueError(
            "Winner-valid refit population "
            "contains duplicate IDs."
        )

    return rows


def raw_values_for_estimator(
    rows: list[dict],
    estimator: str,
) -> np.ndarray:
    if estimator == "SC5_AGREEMENT":
        values = [
            row[
                "sc5_agreement"
            ]
            for row in rows
        ]

    elif estimator == "VC_SELF_EVAL":
        values = [
            row[
                "vc_raw_confidence"
            ]
            for row in rows
        ]

    else:
        raise ValueError(
            "Unknown estimator."
        )

    raw = np.asarray(
        values,
        dtype=float,
    )

    if not np.all(
        np.isfinite(raw)
    ):
        raise ValueError(
            "Winner raw confidence contains "
            "non-finite values."
        )

    if np.any(
        (raw < 0.0)
        | (raw > 1.0)
    ):
        raise ValueError(
            "Winner raw confidence outside [0,1]."
        )

    return raw


def correctness_values(
    rows: list[dict],
) -> np.ndarray:
    y = np.asarray(
        [
            row[
                "correctness"
            ]
            for row in rows
        ],
        dtype=float,
    )

    if not np.all(
        np.isin(
            y,
            [0.0, 1.0],
        )
    ):
        raise ValueError(
            "Winner refit correctness is not binary."
        )

    return y


def stable_sigmoid(
    z: np.ndarray,
) -> np.ndarray:
    z = np.asarray(
        z,
        dtype=float,
    )

    out = np.empty_like(
        z,
        dtype=float,
    )

    positive = (
        z >= 0.0
    )

    out[
        positive
    ] = (
        1.0
        / (
            1.0
            + np.exp(
                -z[
                    positive
                ]
            )
        )
    )

    ez = np.exp(
        z[
            ~positive
        ]
    )

    out[
        ~positive
    ] = (
        ez
        / (
            1.0
            + ez
        )
    )

    return out


def apply_serialized_mapping(
    mapping: dict,
    raw_values,
) -> np.ndarray:
    raw = np.asarray(
        raw_values,
        dtype=float,
    )

    method = mapping[
        "calibrator"
    ]

    if method == "identity":
        return np.clip(
            raw,
            0.0,
            1.0,
        )

    if method == "platt":
        a = float(
            mapping[
                "coefficient"
            ]
        )

        b = float(
            mapping[
                "intercept"
            ]
        )

        return stable_sigmoid(
            a * raw
            + b
        )

    if method == "isotonic":
        x = np.asarray(
            mapping[
                "x_thresholds"
            ],
            dtype=float,
        )

        y = np.asarray(
            mapping[
                "y_thresholds"
            ],
            dtype=float,
        )

        if (
            len(x) != len(y)
            or len(x) < 2
        ):
            raise ValueError(
                "Invalid serialized isotonic mapping."
            )

        return np.interp(
            raw,
            x,
            y,
            left=float(
                y[0]
            ),
            right=float(
                y[-1]
            ),
        )

    raise ValueError(
        "Unknown serialized calibrator."
    )


def fit_serializable_mapping(
    calibrator: str,
    raw: np.ndarray,
    y: np.ndarray,
    cal,
) -> dict:
    raw = np.asarray(
        raw,
        dtype=float,
    )

    y = np.asarray(
        y,
        dtype=float,
    )

    if len(raw) != len(y):
        raise ValueError(
            "Refit raw/y length mismatch."
        )

    if not len(raw):
        raise ValueError(
            "Empty refit population."
        )

    if calibrator == "identity":
        mapping = {
            "calibrator":
                "identity",
            "definition":
                "p = clip(raw_confidence, 0, 1)",
        }

        reference = np.clip(
            raw,
            0.0,
            1.0,
        )

    elif calibrator == "platt":
        if len(
            np.unique(y)
        ) < 2:
            raise ValueError(
                "Platt all-DEV refit has only one class."
            )

        model = cal.LogisticRegression(
            C=np.inf,
            solver="lbfgs",
            max_iter=5000,
        )

        model.fit(
            raw.reshape(
                -1,
                1,
            ),
            y.astype(int),
        )

        coefficient = float(
            model.coef_[
                0,
                0,
            ]
        )

        intercept = float(
            model.intercept_[0]
        )

        mapping = {
            "calibrator":
                "platt",
            "definition":
                "sigmoid(a * raw_confidence + b)",
            "coefficient":
                coefficient,
            "intercept":
                intercept,
            "C":
                "infinity",
            "solver":
                "lbfgs",
            "max_iter":
                5000,
        }

        reference = (
            model.predict_proba(
                raw.reshape(
                    -1,
                    1,
                )
            )[:, 1]
        )

    elif calibrator == "isotonic":
        eligible, reason = (
            cal.isotonic_global_eligible(
                raw,
                y,
            )
        )

        if not eligible:
            raise ValueError(
                "Selected isotonic method is not "
                "eligible on all-valid refit population: "
                + reason
            )

        model = cal.IsotonicRegression(
            y_min=0.0,
            y_max=1.0,
            increasing=True,
            out_of_bounds="clip",
        )

        model.fit(
            raw,
            y,
        )

        mapping = {
            "calibrator":
                "isotonic",
            "definition":
                "piecewise-linear isotonic mapping "
                "with out-of-bounds clipping",
            "x_thresholds": [
                float(x)
                for x
                in model.X_thresholds_
            ],
            "y_thresholds": [
                float(x)
                for x
                in model.y_thresholds_
            ],
            "y_min":
                0.0,
            "y_max":
                1.0,
            "increasing":
                True,
            "out_of_bounds":
                "clip",
        }

        reference = model.predict(
            raw
        )

    else:
        raise ValueError(
            "Unknown calibrator for all-DEV refit."
        )

    serialized_prediction = (
        apply_serialized_mapping(
            mapping,
            raw,
        )
    )

    max_abs_difference = float(
        np.max(
            np.abs(
                serialized_prediction
                - reference
            )
        )
    )

    if max_abs_difference > 1e-12:
        raise AssertionError(
            "Serialized calibrator does not reproduce "
            "fitted calibrator predictions."
        )

    mapping[
        "serialization_validation_max_abs_difference"
    ] = max_abs_difference

    return mapping


def build_method_freeze_payload(
    normalized: dict,
    cal,
    *,
    synthetic: bool,
) -> dict:
    primary = evaluate_primary(
        normalized,
        cal,
    )

    selection = primary[
        "selection"
    ]

    winner_estimator = (
        selection[
            "winner_estimator"
        ]
    )

    winner_calibrator = (
        selection[
            "winner_calibrator"
        ]
    )

    refit_rows = (
        winner_valid_rows(
            normalized,
            winner_estimator,
        )
    )

    raw = (
        raw_values_for_estimator(
            refit_rows,
            winner_estimator,
        )
    )

    y = correctness_values(
        refit_rows
    )

    mapping = (
        fit_serializable_mapping(
            winner_calibrator,
            raw,
            y,
            cal,
        )
    )

    prevalence = float(
        np.mean(y)
    )

    n_correct = int(
        np.sum(y)
    )

    n_incorrect = int(
        len(y)
        - n_correct
    )

    if (
        not 0.0
        <= prevalence
        <= 1.0
    ):
        raise AssertionError(
            "Winner-valid correctness prevalence "
            "outside [0,1]."
        )

    winner_candidate = (
        primary[
            "winner_candidate"
        ]
    )

    paired = primary[
        "paired_rows"
    ]

    return {
        "artifact":
            (
                "GATE6D_DEV_METHOD_FREEZE_"
                "SYNTHETIC_V1"
                if synthetic
                else
                "GATE6D_DEV_METHOD_FREEZE_V1"
            ),

        "status":
            (
                "PASS_SYNTHETIC_ONLY"
                if synthetic
                else
                "FROZEN_METHOD_SELECTED"
            ),

        "primary_comparison": {
            "analysis_set":
                "PAIRED_COMMON_VALID",

            "n":
                len(
                    paired
                ),

            "item_id_set_sha256":
                item_id_set_sha256(
                    paired
                ),

            "candidate_rows":
                primary[
                    "candidate_records"
                ],

            "constant_baseline_oof":
                primary[
                    "constant_baseline"
                ],

            "selection":
                {
                    "winner_estimator":
                        winner_estimator,
                    "winner_calibrator":
                        winner_calibrator,
                    "winner_brier":
                        float(
                            selection[
                                "winner_brier"
                            ]
                        ),
                    "winner_auroc_correct":
                        float(
                            selection[
                                "winner_auroc_correct"
                            ]
                        ),
                    "reason":
                        selection[
                            "reason"
                        ],
                    "brier_effective_tie_threshold":
                        float(
                            selection[
                                "threshold"
                            ]
                        ),
                    "shortlist":
                        list(
                            selection[
                                "shortlist"
                            ]
                        ),
                },

            "winner_oof_metrics": {
                "brier":
                    float(
                        winner_candidate.brier
                    ),
                "auroc_correct":
                    float(
                        winner_candidate.auroc_correct
                    ),
                "auprc_incorrect":
                    float(
                        winner_candidate.auprc_incorrect
                    ),
                "ece10":
                    float(
                        winner_candidate.ece10
                    ),
            },
        },

        "post_selection_refit": {
            "estimator":
                winner_estimator,

            "calibrator":
                winner_calibrator,

            "population_rule":
                "ALL_VALID_DEV_FOR_WINNING_ESTIMATOR",

            "n":
                len(
                    refit_rows
                ),

            "item_id_set_sha256":
                item_id_set_sha256(
                    refit_rows
                ),

            "correct":
                n_correct,

            "incorrect":
                n_incorrect,

            "raw_distinct_values":
                int(
                    len(
                        np.unique(
                            raw
                        )
                    )
                ),

            "mapping":
                mapping,
        },

        "eval_constant_baseline": {
            "source_population":
                "ALL_VALID_DEV_FOR_WINNING_ESTIMATOR",

            "n":
                len(
                    refit_rows
                ),

            "correctness_prevalence":
                prevalence,

            "definition":
                "empirical DEV correctness prevalence "
                "from the same winner-valid population "
                "used for post-selection refit",
        },

        "coverage": {
            "selected_dev_items":
                int(
                    normalized[
                        "summary"
                    ][
                        "selected_items"
                    ]
                ),

            "sc5_valid_items":
                int(
                    normalized[
                        "summary"
                    ][
                        "sc5_valid_items"
                    ]
                ),

            "vc_valid_items":
                int(
                    normalized[
                        "summary"
                    ][
                        "vc_valid_items"
                    ]
                ),

            "paired_common_valid_items":
                int(
                    normalized[
                        "summary"
                    ][
                        "paired_common_valid_items"
                    ]
                ),

            "invalid_reasons":
                dict(
                    normalized[
                        "summary"
                    ][
                        "invalid_reasons"
                    ]
                ),

            "used_to_change_winner":
                False,
        },

        "governance": {
            "secondary_uncertainty_can_change_winner":
                False,

            "coverage_can_change_winner":
                False,

            "eval_used_for_method_selection":
                False,

            "external_test_used_for_method_selection":
                False,

            "method_must_be_frozen_before_eval":
                True,
        },

        "interpretation": {
            "synthetic":
                bool(
                    synthetic
                ),

            "scientific_result":
                not synthetic,
        },

        "safety_state": {
            "real_dev_outputs_read":
                False
                if synthetic
                else True,

            "real_dev_ground_truth_read":
                False
                if synthetic
                else True,

            "calibration_eval_accessed":
                False,

            "external_test_accessed":
                False,

            "model_calls":
                0,
        },
    }


def synthetic_self_test() -> dict:
    frozen = (
        verify_frozen_inputs()
    )

    norm = load_module(
        NORMALIZATION_CORE,
        "gate6d_method_freeze_norm_v1",
    )

    cal = load_module(
        CALIBRATION_CORE,
        "gate6d_method_freeze_cal_v1",
    )

    fixture = (
        norm.synthetic_fixture()
    )

    normalized = (
        norm.normalize_dev500(
            **fixture
        )
    )

    payload = (
        build_method_freeze_payload(
            normalized,
            cal,
            synthetic=True,
        )
    )

    primary = payload[
        "primary_comparison"
    ]

    refit = payload[
        "post_selection_refit"
    ]

    baseline = payload[
        "eval_constant_baseline"
    ]

    if (
        primary["n"]
        != 488
    ):
        raise AssertionError(
            "Expected paired-common-valid n=488."
        )

    if (
        len(
            primary[
                "candidate_rows"
            ]
        )
        != 6
    ):
        raise AssertionError(
            "Expected six candidate rows."
        )

    valid_candidates = [
        row
        for row in primary[
            "candidate_rows"
        ]
        if row["valid"]
    ]

    if len(
        valid_candidates
    ) != 5:
        raise AssertionError(
            "Expected five valid candidates "
            "in frozen synthetic fixture."
        )

    # Existing frozen integration evidence already established
    # this exact synthetic selection. It has no scientific meaning.
    if (
        primary[
            "selection"
        ][
            "winner_estimator"
        ]
        != "VC_SELF_EVAL"
    ):
        raise AssertionError(
            "Synthetic winner estimator changed."
        )

    if (
        primary[
            "selection"
        ][
            "winner_calibrator"
        ]
        != "platt"
    ):
        raise AssertionError(
            "Synthetic winner calibrator changed."
        )

    if (
        primary[
            "selection"
        ][
            "brier_effective_tie_threshold"
        ]
        != 0.01
    ):
        raise AssertionError(
            "Frozen Brier threshold changed."
        )

    # VC-valid population is the paired population.
    if refit["n"] != 488:
        raise AssertionError(
            "VC winner must refit on all 488 valid VC rows."
        )

    if (
        baseline["n"]
        != refit["n"]
    ):
        raise AssertionError(
            "EVAL baseline population differs "
            "from winner-refit population."
        )

    if not (
        0.0
        <= baseline[
            "correctness_prevalence"
        ]
        <= 1.0
    ):
        raise AssertionError(
            "Invalid frozen prevalence."
        )

    if (
        refit[
            "mapping"
        ][
            "calibrator"
        ]
        != "platt"
    ):
        raise AssertionError(
            "Synthetic selected mapping is not Platt."
        )

    if (
        refit[
            "mapping"
        ][
            "serialization_validation_max_abs_difference"
        ]
        > 1e-12
    ):
        raise AssertionError(
            "Selected mapping serialization mismatch."
        )

    # Explicitly verify the alternative SC5 refit-population rule.
    sc5_rows = (
        winner_valid_rows(
            normalized,
            "SC5_AGREEMENT",
        )
    )

    if len(
        sc5_rows
    ) != 495:
        raise AssertionError(
            "SC5 winner would need all 495 valid SC5 rows."
        )

    vc_rows = (
        winner_valid_rows(
            normalized,
            "VC_SELF_EVAL",
        )
    )

    if len(
        vc_rows
    ) != 488:
        raise AssertionError(
            "VC winner should have 488 all-valid VC rows."
        )

    # Validate serializable implementation for every possible
    # calibrator using a synthetic paired population that satisfies
    # the frozen isotonic >=3-distinct-raw-scores eligibility rule.
    #
    # The normalization fixture intentionally gives VC_SELF_EVAL
    # only two distinct confidence values (0.36 / 0.82), so VC
    # isotonic is correctly invalid in the primary candidate table.
    # SC5_AGREEMENT has the frozen 0.6 / 0.8 / 1.0 domain and is
    # therefore the appropriate synthetic fixture for exercising
    # generic isotonic serialization.
    serialization_rows = normalized[
        "paired_rows"
    ]

    y = correctness_values(
        serialization_rows
    )

    serialization_raw = (
        raw_values_for_estimator(
            serialization_rows,
            "SC5_AGREEMENT",
        )
    )

    if len(
        np.unique(
            serialization_raw
        )
    ) < 3:
        raise AssertionError(
            "Serialization fixture lost isotonic eligibility."
        )

    mapping_tests = {}

    for method in [
        "identity",
        "platt",
        "isotonic",
    ]:
        mapping = (
            fit_serializable_mapping(
                method,
                serialization_raw,
                y,
                cal,
            )
        )

        prediction = (
            apply_serialized_mapping(
                mapping,
                serialization_raw,
            )
        )

        if not np.all(
            np.isfinite(
                prediction
            )
        ):
            raise AssertionError(
                f"{method}: non-finite serialized predictions."
            )

        if np.any(
            (prediction < 0.0)
            | (prediction > 1.0)
        ):
            raise AssertionError(
                f"{method}: serialized predictions outside [0,1]."
            )

        mapping_tests[
            method
        ] = {
            "status":
                "PASS",
            "max_abs_difference":
                float(
                    mapping[
                        "serialization_validation_max_abs_difference"
                    ]
                ),
        }

    if (
        payload[
            "coverage"
        ][
            "used_to_change_winner"
        ]
        is not False
    ):
        raise AssertionError(
            "Coverage unexpectedly changes winner."
        )

    if (
        payload[
            "governance"
        ][
            "secondary_uncertainty_can_change_winner"
        ]
        is not False
    ):
        raise AssertionError(
            "Secondary analysis unexpectedly changes winner."
        )

    return {
        "artifact":
            "GATE6D_DEV_METHOD_FREEZE_CORE_"
            "SYNTHETIC_SELF_TEST_V1",

        "status":
            "PASS",

        "frozen_dependencies":
            frozen,

        "synthetic_method_freeze":
            payload,

        "refit_population_contract": {
            "if_SC5_wins_n":
                495,
            "if_VC_wins_n":
                488,
            "synthetic_actual_winner":
                "VC_SELF_EVAL",
            "synthetic_actual_refit_n":
                refit["n"],
        },

        "mapping_serialization_tests":
            mapping_tests,

        "eval_unlock": {
            "real_method_freeze_created":
                False,
            "calibration_eval_unlocked":
                False,
        },

        "interpretation": {
            "synthetic_winner_has_real_scientific_meaning":
                False,
            "real_method_selection_performed":
                False,
        },

        "real_dev_outputs_read":
            False,
        "real_dev_ground_truth_read":
            False,
        "calibration_eval_accessed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
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
            "BLOCKED: V1 permits --self-test only."
        )
        print(
            "Real DEV method selection/freeze was NOT run."
        )
        print(
            "Calibration-EVAL remains sealed."
        )
        return

    result = (
        synthetic_self_test()
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUT.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )

    method = result[
        "synthetic_method_freeze"
    ]

    primary = method[
        "primary_comparison"
    ]

    refit = method[
        "post_selection_refit"
    ]

    baseline = method[
        "eval_constant_baseline"
    ]

    print(
        "=== GATE 6D DEV METHOD-FREEZE CORE "
        "SYNTHETIC TEST ==="
    )

    print(
        "status:",
        result["status"],
    )

    print(
        "paired_common_valid_items:",
        primary["n"],
    )

    print(
        "candidate_rows:",
        len(
            primary[
                "candidate_rows"
            ]
        ),
    )

    print(
        "valid_candidate_rows:",
        sum(
            1
            for row in primary[
                "candidate_rows"
            ]
            if row["valid"]
        ),
    )

    print(
        "synthetic_winner_estimator:",
        primary[
            "selection"
        ][
            "winner_estimator"
        ],
    )

    print(
        "synthetic_winner_calibrator:",
        primary[
            "selection"
        ][
            "winner_calibrator"
        ],
    )

    print(
        "selection_reason:",
        primary[
            "selection"
        ][
            "reason"
        ],
    )

    print(
        "winner_refit_population_n:",
        refit["n"],
    )

    print(
        "winner_refit_mapping:",
        refit[
            "mapping"
        ][
            "calibrator"
        ],
    )

    print(
        "winner_valid_DEV_prevalence:",
        baseline[
            "correctness_prevalence"
        ],
    )

    print(
        "if_SC5_wins_refit_n:",
        result[
            "refit_population_contract"
        ][
            "if_SC5_wins_n"
        ],
    )

    print(
        "if_VC_wins_refit_n:",
        result[
            "refit_population_contract"
        ][
            "if_VC_wins_n"
        ],
    )

    print(
        "identity_serialization:",
        result[
            "mapping_serialization_tests"
        ][
            "identity"
        ][
            "status"
        ],
    )

    print(
        "platt_serialization:",
        result[
            "mapping_serialization_tests"
        ][
            "platt"
        ][
            "status"
        ],
    )

    print(
        "isotonic_serialization:",
        result[
            "mapping_serialization_tests"
        ][
            "isotonic"
        ][
            "status"
        ],
    )

    print(
        "coverage_can_change_winner: False"
    )

    print(
        "secondary_analysis_can_change_winner: False"
    )

    print(
        "real_method_freeze_created: False"
    )

    print(
        "calibration_eval_unlocked: False"
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
        "gate7_opened: False"
    )

    print(
        "model_calls: 0"
    )


if __name__ == "__main__":
    main()
