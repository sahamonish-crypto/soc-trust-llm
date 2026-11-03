#!/usr/bin/env python3

"""Gate 6D EVAL scoring executor V1 (working copy).

Prospective only.
Ground truth scoring is not implemented yet.
Metadata-only preflight must not open hidden EVAL ground truth.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile

BOUNDARY = Path(
    "scripts/gate6/gate6d_eval_collection_gate_v2.py"
)

COLLECTION_EXECUTOR_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_EVAL_COLLECTION_EXECUTOR_FREEZE_V1.json"
)


COLLECTION_EXECUTOR = Path(
    "scripts/gate6/"
    "gate6d_eval_collection_executor_v1.py"
)

DEV_METHOD_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_METHOD_FREEZE_V1.json"
)


DEV_METHOD_CORE = Path(
    "scripts/gate6/"
    "gate6d_dev_method_freeze_core_v1.py"
)

CALIBRATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_calibration_analysis_core.py"
)

SEALED_EVAL_GT = Path(
    "benchmarks/gate6d/canonical_v1/hidden/"
    "eval_ground_truth.jsonl"
)

EXPECTED_DEV_METHOD_CORE_SHA = (
    "7551a3989ff71405f3301a9544dae5a4"
    "051f6997aa21f022aefb44cd091b8df8"
)

EXPECTED_CALIBRATION_CORE_SHA = (
    "47a03118614e68c000101047c680b399"
    "29f1355ab9a8f1ba1565abcb81d52eba"
)

EXPECTED_EVAL_GT_SHA = (
    "9ffb438d26a7f0b1e9d981998c66edab"
    "1c96a1348a90db0eb5769bc674e6ed55"
)

DEV_COMMIT_MARKER = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_OOF_PREDICTIONS_FREEZE_V1.json"
)

COLLECTION_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_EVAL_COLLECTION_FREEZE_V1.json"
)


EVAL_SCORING_RESULT = Path(
    "benchmarks/gate6d/"
    "GATE6D_EVAL_SCORING_RESULT_V1.json"
)


SCORING_EXECUTOR = Path(
    "scripts/gate6/"
    "gate6d_eval_scoring_executor_v1.py"
)

SCORING_ENV = "GATE6D_ALLOW_EVAL_SCORING"

EXPECTED_BOUNDARY_SHA = (
    "d666300f059ee6052461982cb3c7f412"
    "e0b41c079a363bf65499a902462f05cf"
)

EXPECTED_COLLECTION_EXECUTOR_FREEZE_SHA = (
    "f740786bb92b3c84a4565acf24fd9a594"
    "be077cc0ea41568f0c75fd27badb137"
)


EXPECTED_COLLECTION_EXECUTOR_SHA = (
    "ab0ac860736875dcd03c97047442d08e"
    "abe75f0942a84a94fd1d0f1bb1a81c4f"
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


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to import " + str(path)
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_scoring_dependencies() -> dict:
    expected = {
        DEV_METHOD_CORE:
            EXPECTED_DEV_METHOD_CORE_SHA,
        CALIBRATION_CORE:
            EXPECTED_CALIBRATION_CORE_SHA,
    }

    out = {}

    for path,want in expected.items():
        if not path.exists():
            raise RuntimeError(
                "Missing frozen scoring dependency: "
                + str(path)
            )

        got = sha256_file(path)

        if got != want:
            raise RuntimeError(
                "Frozen scoring dependency SHA mismatch: "
                + str(path)
            )

        out[str(path)] = got

    return out


def raw_confidence_from_terminal(
    selected_estimator: str,
    sc5_record: dict,
    vc_record: dict | None,
) -> float:
    if selected_estimator == "SC5_AGREEMENT":
        value = sc5_record.get("agreement")

    elif selected_estimator == "VC_SELF_EVAL":
        if vc_record is None:
            raise RuntimeError(
                "VC-selected item lacks VC terminal."
            )

        value = vc_record.get(
            "raw_confidence"
        )

    else:
        raise RuntimeError(
            "Unknown selected estimator."
        )

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise RuntimeError(
            "Raw confidence outside [0,1]."
        )

    return value


def correctness_value(
    recommendation: str,
    ground_truth: str,
) -> int:
    allowed = {
        "ESCALATE",
        "DO_NOT_ESCALATE",
    }

    if recommendation not in allowed:
        raise RuntimeError(
            "Invalid recommendation."
        )

    if ground_truth not in allowed:
        raise RuntimeError(
            "Invalid ground truth."
        )

    return int(
        recommendation == ground_truth
    )


def synthetic_scoring_primitives_self_test() -> dict:
    verify_scoring_dependencies()

    method_core = load_module(
        DEV_METHOD_CORE,
        "gate6d_method_core_for_eval_scoring",
    )

    sc5 = {
        "agreement": 0.8,
        "majority": "ESCALATE",
        "valid": True,
    }

    vc = {
        "raw_confidence": 0.73,
        "valid": True,
    }

    sc5_raw = raw_confidence_from_terminal(
        "SC5_AGREEMENT",
        sc5,
        None,
    )

    vc_raw = raw_confidence_from_terminal(
        "VC_SELF_EVAL",
        sc5,
        vc,
    )

    identity = (
        method_core.apply_serialized_mapping(
            {
                "calibrator": "identity",
                "definition":
                    "synthetic",
            },
            [sc5_raw],
        )[0]
    )

    platt = (
        method_core.apply_serialized_mapping(
            {
                "calibrator": "platt",
                "definition":
                    "synthetic",
                "coefficient": 2.0,
                "intercept": -1.0,
            },
            [vc_raw],
        )[0]
    )

    if not 0.0 <= float(identity) <= 1.0:
        raise RuntimeError(
            "Synthetic identity probability invalid."
        )

    if not 0.0 <= float(platt) <= 1.0:
        raise RuntimeError(
            "Synthetic Platt probability invalid."
        )

    if correctness_value(
        "ESCALATE",
        "ESCALATE",
    ) != 1:
        raise RuntimeError(
            "Synthetic correctness=1 failed."
        )

    if correctness_value(
        "ESCALATE",
        "DO_NOT_ESCALATE",
    ) != 0:
        raise RuntimeError(
            "Synthetic correctness=0 failed."
        )

    fail_closed = 0

    bad_cases = [
        lambda: raw_confidence_from_terminal(
            "VC_SELF_EVAL",
            sc5,
            None,
        ),
        lambda: raw_confidence_from_terminal(
            "SC5_AGREEMENT",
            {"agreement": 1.2},
            None,
        ),
        lambda: correctness_value(
            "UNKNOWN",
            "ESCALATE",
        ),
        lambda: correctness_value(
            "ESCALATE",
            "UNKNOWN",
        ),
    ]

    for fn in bad_cases:
        try:
            fn()
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Synthetic scoring fail-closed case passed."
            )

    return {
        "status": "PASS",
        "sc5_raw_confidence": sc5_raw,
        "vc_raw_confidence": vc_raw,
        "identity_probability":
            float(identity),
        "platt_probability":
            float(platt),
        "fail_closed_tests":
            fail_closed,
        "sealed_eval_ground_truth_opened":
            False,
        "real_eval_scoring_performed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def build_scoring_rows(
    selected_estimator: str,
    mapping: dict,
    dev_prevalence: float,
    sc5_done: dict,
    vc_done: dict,
    ground_truth: dict,
) -> list:
    method_core = load_module(
        DEV_METHOD_CORE,
        "gate6d_method_core_scoring_rows",
    )

    prevalence = float(
        dev_prevalence
    )

    if not 0.0 <= prevalence <= 1.0:
        raise RuntimeError(
            "DEV correctness prevalence outside [0,1]."
        )

    rows = []

    for item_id in sorted(ground_truth):
        gt = ground_truth[item_id]

        if item_id not in sc5_done:
            raise RuntimeError(
                "Ground-truth item lacks SC5 terminal: "
                + item_id
            )

        sc5 = sc5_done[item_id]

        if not isinstance(
            sc5.get("valid"),
            bool,
        ):
            raise RuntimeError(
                "SC5 validity is not boolean."
            )

        if not sc5["valid"]:
            if item_id in vc_done:
                raise RuntimeError(
                    "VC exists after invalid SC5."
                )
            continue

        recommendation = sc5.get(
            "majority"
        )

        vc = None

        if (
            selected_estimator
            == "VC_SELF_EVAL"
        ):
            if item_id not in vc_done:
                raise RuntimeError(
                    "Valid SC5 lacks VC terminal."
                )

            vc = vc_done[item_id]

            if not isinstance(
                vc.get("valid"),
                bool,
            ):
                raise RuntimeError(
                    "VC validity is not boolean."
                )

            frozen = vc.get(
                "frozen_recommendation"
            )

            if frozen != recommendation:
                raise RuntimeError(
                    "VC frozen recommendation mismatch."
                )

            if not vc["valid"]:
                continue

        elif (
            selected_estimator
            != "SC5_AGREEMENT"
        ):
            raise RuntimeError(
                "Unknown selected estimator."
            )

        raw = raw_confidence_from_terminal(
            selected_estimator,
            sc5,
            vc,
        )

        calibrated = float(
            method_core.apply_serialized_mapping(
                mapping,
                [raw],
            )[0]
        )

        if not 0.0 <= calibrated <= 1.0:
            raise RuntimeError(
                "Calibrated probability outside [0,1]."
            )

        correctness = correctness_value(
            recommendation,
            gt,
        )

        rows.append({
            "item_id": item_id,
            "recommendation":
                recommendation,
            "ground_truth":
                gt,
            "correctness":
                correctness,
            "raw_confidence":
                raw,
            "calibrated_probability":
                calibrated,
            "constant_baseline_probability":
                prevalence,
        })

    if not rows:
        raise RuntimeError(
            "EVAL valid scoring population is empty."
        )

    ids = [
        row["item_id"]
        for row in rows
    ]

    if len(ids) != len(set(ids)):
        raise RuntimeError(
            "Duplicate EVAL scoring item IDs."
        )

    return rows


def synthetic_scoring_rows_self_test() -> dict:
    gt = {
        "G6D-E-0001": "ESCALATE",
        "G6D-E-0002": "DO_NOT_ESCALATE",
        "G6D-E-0003": "ESCALATE",
        "G6D-E-0004": "DO_NOT_ESCALATE",
    }

    sc5 = {
        "G6D-E-0001": {
            "valid": True,
            "majority": "ESCALATE",
            "agreement": 1.0,
        },
        "G6D-E-0002": {
            "valid": True,
            "majority": "ESCALATE",
            "agreement": 0.6,
        },
        "G6D-E-0003": {
            "valid": False,
            "majority": None,
            "agreement": None,
        },
        "G6D-E-0004": {
            "valid": True,
            "majority": "DO_NOT_ESCALATE",
            "agreement": 0.8,
        },
    }

    vc = {
        "G6D-E-0001": {
            "valid": True,
            "frozen_recommendation":
                "ESCALATE",
            "raw_confidence": 0.9,
        },
        "G6D-E-0002": {
            "valid": False,
            "frozen_recommendation":
                "ESCALATE",
            "raw_confidence": None,
        },
        "G6D-E-0004": {
            "valid": True,
            "frozen_recommendation":
                "DO_NOT_ESCALATE",
            "raw_confidence": 0.7,
        },
    }

    identity = {
        "calibrator": "identity",
        "definition": "synthetic",
    }

    sc5_rows = build_scoring_rows(
        "SC5_AGREEMENT",
        identity,
        0.75,
        sc5,
        {},
        gt,
    )

    vc_rows = build_scoring_rows(
        "VC_SELF_EVAL",
        identity,
        0.75,
        sc5,
        vc,
        gt,
    )

    if len(sc5_rows) != 3:
        raise RuntimeError(
            "Synthetic SC5 scoring population mismatch."
        )

    if len(vc_rows) != 2:
        raise RuntimeError(
            "Synthetic VC scoring population mismatch."
        )

    if [
        r["correctness"]
        for r in sc5_rows
    ] != [1,0,1]:
        raise RuntimeError(
            "Synthetic SC5 correctness mismatch."
        )

    if [
        r["correctness"]
        for r in vc_rows
    ] != [1,1]:
        raise RuntimeError(
            "Synthetic VC correctness mismatch."
        )

    fail_closed = 0

    bad_vc = {
        k: dict(v)
        for k,v in vc.items()
    }

    bad_vc["G6D-E-0001"][
        "frozen_recommendation"
    ] = "DO_NOT_ESCALATE"

    cases = [
        lambda: build_scoring_rows(
            "VC_SELF_EVAL",
            identity,
            0.75,
            sc5,
            bad_vc,
            gt,
        ),
        lambda: build_scoring_rows(
            "SC5_AGREEMENT",
            identity,
            1.5,
            sc5,
            {},
            gt,
        ),
        lambda: build_scoring_rows(
            "UNKNOWN",
            identity,
            0.75,
            sc5,
            vc,
            gt,
        ),
    ]

    for fn in cases:
        try:
            fn()
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Synthetic scoring-row fail-closed case passed."
            )

    return {
        "status": "PASS",
        "sc5_scoring_rows":
            len(sc5_rows),
        "vc_scoring_rows":
            len(vc_rows),
        "sc5_correctness":
            [
                r["correctness"]
                for r in sc5_rows
            ],
        "vc_correctness":
            [
                r["correctness"]
                for r in vc_rows
            ],
        "fail_closed_tests":
            fail_closed,
        "sealed_eval_ground_truth_opened":
            False,
        "real_eval_scoring_performed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def evaluate_eval_safeguard(
    scoring_rows: list,
) -> dict:
    if not scoring_rows:
        raise RuntimeError(
            "Empty EVAL scoring population."
        )

    cal = load_module(
        CALIBRATION_CORE,
        "gate6d_calibration_core_eval_safeguard",
    )

    y = cal._as_1d_float(
        row["correctness"]
        for row in scoring_rows
    )

    selected_p = cal._as_1d_float(
        row["calibrated_probability"]
        for row in scoring_rows
    )

    constant_p = cal._as_1d_float(
        row["constant_baseline_probability"]
        for row in scoring_rows
    )

    selected = cal.metric_bundle(
        y,
        selected_p,
    )

    constant = cal.metric_bundle(
        y,
        constant_p,
    )

    auroc = float(
        selected["auroc_correct"]
    )

    selected_brier = float(
        selected["brier"]
    )

    constant_brier = float(
        constant["brier"]
    )

    delta = (
        selected_brier
        - constant_brier
    )

    discrimination_pass = (
        math.isfinite(auroc)
        and auroc > 0.50
    )

    brier_pass = (
        math.isfinite(selected_brier)
        and math.isfinite(constant_brier)
        and delta < 0.0
    )

    decision = (
        "PASS"
        if (
            discrimination_pass
            and brier_pass
        )
        else
        "HALT_PROTOCOL_REVIEW"
    )

    return {
        "decision": decision,
        "n": len(scoring_rows),

        "primary_safeguard": {
            "auroc_correct":
                auroc
                if math.isfinite(auroc)
                else None,
            "auroc_threshold_strict":
                0.50,
            "auroc_pass":
                discrimination_pass,

            "brier_selected":
                selected_brier,
            "brier_constant_dev_prevalence":
                constant_brier,
            "brier_delta_selected_minus_constant":
                delta,
            "brier_pass":
                brier_pass,

            "pass_requires_both":
                True,
        },

        "selected_metrics": {
            "brier":
                selected["brier"],
            "auroc_correct":
                (
                    selected["auroc_correct"]
                    if math.isfinite(
                        selected["auroc_correct"]
                    )
                    else None
                ),
            "auprc_incorrect":
                (
                    selected["auprc_incorrect"]
                    if math.isfinite(
                        selected["auprc_incorrect"]
                    )
                    else None
                ),
            "ece10":
                selected["ece10"],
            "reliability":
                selected["reliability"],
        },

        "constant_metrics": {
            "brier":
                constant["brier"],
            "auroc_correct":
                (
                    constant["auroc_correct"]
                    if math.isfinite(
                        constant["auroc_correct"]
                    )
                    else None
                ),
            "auprc_incorrect":
                (
                    constant["auprc_incorrect"]
                    if math.isfinite(
                        constant["auprc_incorrect"]
                    )
                    else None
                ),
            "ece10":
                constant["ece10"],
            "reliability":
                constant["reliability"],
        },

        "governance": {
            "eval_refit_performed":
                False,
            "eval_reselection_performed":
                False,
            "secondary_metrics_can_change_decision":
                False,
            "gate7_opened":
                False,
        },
    }


def synthetic_eval_safeguard_self_test() -> dict:
    def rows(y, p, baseline):
        return [
            {
                "item_id":
                    f"SYN-{i:02d}",
                "correctness":
                    int(yy),
                "calibrated_probability":
                    float(pp),
                "constant_baseline_probability":
                    float(baseline),
            }
            for i,(yy,pp) in enumerate(
                zip(y,p),
                start=1,
            )
        ]

    passing = evaluate_eval_safeguard(
        rows(
            [1,1,0,0],
            [0.9,0.8,0.2,0.1],
            0.5,
        )
    )

    bad_discrimination = evaluate_eval_safeguard(
        rows(
            [1,1,0,0],
            [0.1,0.2,0.8,0.9],
            0.5,
        )
    )

    equality = evaluate_eval_safeguard(
        rows(
            [1,1,0,0],
            [0.5,0.5,0.5,0.5],
            0.5,
        )
    )

    undefined = evaluate_eval_safeguard(
        rows(
            [1,1,1,1],
            [0.9,0.8,0.7,0.6],
            0.75,
        )
    )

    if passing["decision"] != "PASS":
        raise RuntimeError(
            "Synthetic passing safeguard failed."
        )

    for result in [
        bad_discrimination,
        equality,
        undefined,
    ]:
        if (
            result["decision"]
            != "HALT_PROTOCOL_REVIEW"
        ):
            raise RuntimeError(
                "Synthetic failing safeguard passed."
            )

    if (
        equality[
            "primary_safeguard"
        ][
            "brier_delta_selected_minus_constant"
        ]
        != 0.0
    ):
        raise RuntimeError(
            "Synthetic equality case mismatch."
        )

    if (
        undefined[
            "primary_safeguard"
        ][
            "auroc_correct"
        ]
        is not None
    ):
        raise RuntimeError(
            "Undefined AUROC was not preserved as null."
        )

    return {
        "status": "PASS",
        "passing_decision":
            passing["decision"],
        "bad_discrimination_decision":
            bad_discrimination["decision"],
        "equality_decision":
            equality["decision"],
        "undefined_auroc_decision":
            undefined["decision"],
        "equality_brier_delta":
            equality[
                "primary_safeguard"
            ][
                "brier_delta_selected_minus_constant"
            ],
        "undefined_auroc":
            undefined[
                "primary_safeguard"
            ][
                "auroc_correct"
            ],
        "sealed_eval_ground_truth_opened":
            False,
        "real_eval_scoring_performed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def validate_eval_ground_truth_records(
    records: list,
) -> dict:
    if len(records) != 458:
        raise RuntimeError(
            f"Expected 458 EVAL GT records, got {len(records)}."
        )

    allowed = {
        "ESCALATE",
        "DO_NOT_ESCALATE",
    }

    out = {}

    for i,record in enumerate(
        records,
        start=1,
    ):
        expected_id = (
            f"G6D-E-{i:04d}"
        )

        if set(record) != {
            "item_id",
            "ground_truth",
        }:
            raise RuntimeError(
                "Unexpected EVAL GT record schema."
            )

        if record["item_id"] != expected_id:
            raise RuntimeError(
                "EVAL GT item ID/order mismatch."
            )

        label = record["ground_truth"]

        if label not in allowed:
            raise RuntimeError(
                "Invalid EVAL GT label."
            )

        if expected_id in out:
            raise RuntimeError(
                "Duplicate EVAL GT item ID."
            )

        out[expected_id] = label

    return out


def load_eval_ground_truth_after_unlock() -> dict:
    # CRITICAL:
    # Full scoring gate must pass before the hidden GT file
    # is hashed, opened, parsed, or otherwise accessed.
    pf = preflight()

    if not pf["ready"]:
        raise RuntimeError(
            "EVAL scoring gate is not ready: "
            + "; ".join(pf["reasons"])
        )

    actual = sha256_file(
        SEALED_EVAL_GT
    )

    if actual != EXPECTED_EVAL_GT_SHA:
        raise RuntimeError(
            "Sealed EVAL ground-truth SHA mismatch."
        )

    records = []

    with SEALED_EVAL_GT.open(
        "r",
        encoding="utf-8",
    ) as f:
        for line_no,line in enumerate(
            f,
            start=1,
        ):
            text = line.strip()

            if not text:
                raise RuntimeError(
                    f"Blank EVAL GT line {line_no}."
                )

            obj = json.loads(text)

            if not isinstance(obj,dict):
                raise RuntimeError(
                    "EVAL GT JSONL record is not an object."
                )

            records.append(obj)

    return validate_eval_ground_truth_records(
        records
    )


def synthetic_eval_ground_truth_validation_self_test() -> dict:
    records = [
        {
            "item_id":
                f"G6D-E-{i:04d}",
            "ground_truth":
                (
                    "ESCALATE"
                    if i % 2
                    else "DO_NOT_ESCALATE"
                ),
        }
        for i in range(1,459)
    ]

    validated = (
        validate_eval_ground_truth_records(
            records
        )
    )

    if len(validated) != 458:
        raise RuntimeError(
            "Synthetic EVAL GT count mismatch."
        )

    fail_closed = 0

    bad_schema = [
        dict(x)
        for x in records
    ]
    bad_schema[0]["extra"] = True

    bad_order = [
        dict(x)
        for x in records
    ]
    bad_order[0]["item_id"] = (
        "G6D-E-0002"
    )

    bad_label = [
        dict(x)
        for x in records
    ]
    bad_label[0]["ground_truth"] = (
        "UNKNOWN"
    )

    short = records[:-1]

    for candidate in [
        bad_schema,
        bad_order,
        bad_label,
        short,
    ]:
        try:
            validate_eval_ground_truth_records(
                candidate
            )
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Synthetic EVAL GT fail-closed case passed."
            )

    return {
        "status": "PASS",
        "validated_items":
            len(validated),
        "first_item":
            next(iter(validated)),
        "last_item":
            list(validated)[-1],
        "fail_closed_tests":
            fail_closed,
        "real_eval_ground_truth_file_opened":
            False,
        "real_eval_scoring_performed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def extract_frozen_scoring_configuration(
    method_freeze: dict,
) -> dict:
    if (
        method_freeze.get("artifact")
        != "GATE6D_DEV_METHOD_FREEZE_V1"
    ):
        raise RuntimeError(
            "Unexpected DEV method-freeze artifact."
        )

    if (
        method_freeze.get("status")
        != "FROZEN_METHOD_SELECTED"
    ):
        raise RuntimeError(
            "DEV method freeze is not final."
        )

    try:
        winner = (
            method_freeze[
                "primary_comparison"
            ][
                "selection"
            ][
                "winner_estimator"
            ]
        )

        refit_estimator = (
            method_freeze[
                "post_selection_refit"
            ][
                "estimator"
            ]
        )

        mapping = (
            method_freeze[
                "post_selection_refit"
            ][
                "mapping"
            ]
        )

        prevalence = float(
            method_freeze[
                "eval_constant_baseline"
            ][
                "correctness_prevalence"
            ]
        )

    except Exception as exc:
        raise RuntimeError(
            "Malformed DEV method freeze."
        ) from exc

    if winner not in {
        "SC5_AGREEMENT",
        "VC_SELF_EVAL",
    }:
        raise RuntimeError(
            "Unknown frozen winner estimator."
        )

    if refit_estimator != winner:
        raise RuntimeError(
            "Winner/refit estimator mismatch."
        )

    if not isinstance(mapping, dict):
        raise RuntimeError(
            "Frozen mapping is not an object."
        )

    if not 0.0 <= prevalence <= 1.0:
        raise RuntimeError(
            "Frozen DEV prevalence outside [0,1]."
        )

    method_core = load_module(
        DEV_METHOD_CORE,
        "gate6d_method_core_config_validation",
    )

    probe = method_core.apply_serialized_mapping(
        mapping,
        [0.5],
    )

    if len(probe) != 1:
        raise RuntimeError(
            "Frozen mapping probe length mismatch."
        )

    mapped = float(probe[0])

    if not 0.0 <= mapped <= 1.0:
        raise RuntimeError(
            "Frozen mapping produces invalid probability."
        )

    return {
        "selected_estimator": winner,
        "mapping": mapping,
        "dev_correctness_prevalence":
            prevalence,
    }


def synthetic_frozen_scoring_configuration_self_test() -> dict:
    base = {
        "artifact":
            "GATE6D_DEV_METHOD_FREEZE_V1",
        "status":
            "FROZEN_METHOD_SELECTED",
        "primary_comparison": {
            "selection": {
                "winner_estimator":
                    "SC5_AGREEMENT",
            },
        },
        "post_selection_refit": {
            "estimator":
                "SC5_AGREEMENT",
            "mapping": {
                "calibrator":
                    "identity",
                "definition":
                    "synthetic",
            },
        },
        "eval_constant_baseline": {
            "correctness_prevalence":
                0.75,
        },
    }

    cfg = (
        extract_frozen_scoring_configuration(
            base
        )
    )

    if (
        cfg["selected_estimator"]
        != "SC5_AGREEMENT"
    ):
        raise RuntimeError(
            "Synthetic estimator extraction failed."
        )

    if (
        cfg["dev_correctness_prevalence"]
        != 0.75
    ):
        raise RuntimeError(
            "Synthetic prevalence extraction failed."
        )

    fail_closed = 0

    cases = []

    bad = json.loads(json.dumps(base))
    bad["status"] = "OPEN"
    cases.append(bad)

    bad = json.loads(json.dumps(base))
    bad[
        "post_selection_refit"
    ][
        "estimator"
    ] = "VC_SELF_EVAL"
    cases.append(bad)

    bad = json.loads(json.dumps(base))
    bad[
        "primary_comparison"
    ][
        "selection"
    ][
        "winner_estimator"
    ] = "UNKNOWN"
    cases.append(bad)

    bad = json.loads(json.dumps(base))
    bad[
        "eval_constant_baseline"
    ][
        "correctness_prevalence"
    ] = 1.1
    cases.append(bad)

    bad = json.loads(json.dumps(base))
    bad[
        "post_selection_refit"
    ][
        "mapping"
    ] = {
        "calibrator": "UNKNOWN",
    }
    cases.append(bad)

    for candidate in cases:
        try:
            extract_frozen_scoring_configuration(
                candidate
            )
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Synthetic method-freeze "
                "fail-closed case passed."
            )

    return {
        "status": "PASS",
        "selected_estimator":
            cfg["selected_estimator"],
        "dev_correctness_prevalence":
            cfg[
                "dev_correctness_prevalence"
            ],
        "fail_closed_tests":
            fail_closed,
        "real_dev_method_freeze_opened":
            False,
        "sealed_eval_ground_truth_opened":
            False,
        "real_eval_scoring_performed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def json_safe(obj):
    if isinstance(obj, float):
        return (
            obj
            if math.isfinite(obj)
            else None
        )

    if isinstance(obj, dict):
        return {
            k: json_safe(v)
            for k,v in obj.items()
        }

    if isinstance(obj, list):
        return [
            json_safe(v)
            for v in obj
        ]

    if isinstance(obj, tuple):
        return [
            json_safe(v)
            for v in obj
        ]

    return obj


def canonical_json_bytes(obj: dict) -> bytes:
    safe = json_safe(obj)

    return (
        json.dumps(
            safe,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def install_bytes_new_only(
    final_path: Path,
    data: bytes,
) -> str:
    final_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if final_path.exists():
        raise RuntimeError(
            "Refusing to overwrite existing artifact: "
            + str(final_path)
        )

    fd,tmp_name = tempfile.mkstemp(
        prefix=final_path.name + ".tmp.",
        dir=str(final_path.parent),
    )

    tmp = Path(tmp_name)

    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        expected = hashlib.sha256(
            data
        ).hexdigest()

        actual_tmp = sha256_file(tmp)

        if actual_tmp != expected:
            raise RuntimeError(
                "Temporary scoring artifact SHA mismatch."
            )

        try:
            os.link(
                tmp,
                final_path,
            )
        except FileExistsError as exc:
            raise RuntimeError(
                "Scoring artifact appeared during install."
            ) from exc

        actual_final = sha256_file(
            final_path
        )

        if actual_final != expected:
            raise RuntimeError(
                "Installed scoring artifact SHA mismatch."
            )

        return expected

    finally:
        if tmp.exists():
            tmp.unlink()


def build_eval_scoring_result_payload(
    *,
    selected_estimator: str,
    scoring_rows: list,
    safeguard: dict,
    collection_freeze_sha256: str,
    dev_method_freeze_sha256: str,
    eval_gt_sha256: str,
) -> dict:
    if selected_estimator not in {
        "SC5_AGREEMENT",
        "VC_SELF_EVAL",
    }:
        raise RuntimeError(
            "Unknown selected estimator in scoring result."
        )

    if not scoring_rows:
        raise RuntimeError(
            "Cannot freeze empty scoring population."
        )

    if safeguard.get("decision") not in {
        "PASS",
        "HALT_PROTOCOL_REVIEW",
    }:
        raise RuntimeError(
            "Invalid safeguard decision."
        )

    if safeguard.get("n") != len(scoring_rows):
        raise RuntimeError(
            "Safeguard/scoring population mismatch."
        )

    for name,value in {
        "collection_freeze_sha256":
            collection_freeze_sha256,
        "dev_method_freeze_sha256":
            dev_method_freeze_sha256,
        "eval_gt_sha256":
            eval_gt_sha256,
    }.items():
        if (
            not isinstance(value,str)
            or len(value) != 64
            or any(
                c not in "0123456789abcdef"
                for c in value
            )
        ):
            raise RuntimeError(
                "Invalid SHA256 binding: " + name
            )

    return {
        "artifact":
            "GATE6D_EVAL_SCORING_RESULT_V1",

        "status":
            "FROZEN_ONE_SHOT_EVAL_DECISION",

        "selected_estimator":
            selected_estimator,

        "scoring_population": {
            "n":
                len(scoring_rows),
            "item_ids": [
                row["item_id"]
                for row in scoring_rows
            ],
        },

        "scoring_rows":
            json_safe(scoring_rows),

        "safeguard":
            json_safe(safeguard),

        "provenance": {
            "eval_collection_freeze_sha256":
                collection_freeze_sha256,
            "dev_method_freeze_sha256":
                dev_method_freeze_sha256,
            "sealed_eval_ground_truth_sha256":
                eval_gt_sha256,
        },

        "governance": {
            "sealed_eval_ground_truth_opened":
                True,
            "correctness_computed":
                True,
            "eval_refit_performed":
                False,
            "eval_reselection_performed":
                False,
            "secondary_metrics_changed_decision":
                False,
            "external_test_accessed":
                False,
            "gate7_opened":
                False,
            "scoring_result_overwrite_permitted":
                False,
        },
    }


def synthetic_scoring_result_transaction_self_test() -> dict:
    rows = [
        {
            "item_id": "SYN-01",
            "correctness": 1,
            "calibrated_probability": 0.9,
            "constant_baseline_probability": 0.5,
        },
        {
            "item_id": "SYN-02",
            "correctness": 1,
            "calibrated_probability": 0.8,
            "constant_baseline_probability": 0.5,
        },
        {
            "item_id": "SYN-03",
            "correctness": 0,
            "calibrated_probability": 0.2,
            "constant_baseline_probability": 0.5,
        },
        {
            "item_id": "SYN-04",
            "correctness": 0,
            "calibrated_probability": 0.1,
            "constant_baseline_probability": 0.5,
        },
    ]

    safeguard = evaluate_eval_safeguard(
        rows
    )

    payload = build_eval_scoring_result_payload(
        selected_estimator=
            "SC5_AGREEMENT",
        scoring_rows=rows,
        safeguard=safeguard,
        collection_freeze_sha256=
            "1" * 64,
        dev_method_freeze_sha256=
            "2" * 64,
        eval_gt_sha256=
            "3" * 64,
    )

    if (
        payload["safeguard"]["decision"]
        != "PASS"
    ):
        raise RuntimeError(
            "Synthetic scoring transaction did not PASS."
        )

    with tempfile.TemporaryDirectory() as td:
        out = (
            Path(td)
            / "GATE6D_EVAL_SCORING_RESULT_V1.json"
        )

        data = canonical_json_bytes(
            payload
        )

        installed_sha = (
            install_bytes_new_only(
                out,
                data,
            )
        )

        overwrite_blocked = False

        try:
            install_bytes_new_only(
                out,
                data,
            )
        except RuntimeError:
            overwrite_blocked = True

        if not overwrite_blocked:
            raise RuntimeError(
                "Synthetic scoring overwrite was not blocked."
            )

        reread = json.loads(
            out.read_text(
                encoding="utf-8"
            )
        )

        if reread != payload:
            raise RuntimeError(
                "Synthetic scoring artifact reread mismatch."
            )

        temp_files = list(
            out.parent.glob(
                out.name + ".tmp.*"
            )
        )

        if temp_files:
            raise RuntimeError(
                "Synthetic scoring temp file leaked."
            )

    fail_closed = 0

    bad_cases = [
        lambda: build_eval_scoring_result_payload(
            selected_estimator=
                "UNKNOWN",
            scoring_rows=rows,
            safeguard=safeguard,
            collection_freeze_sha256=
                "1" * 64,
            dev_method_freeze_sha256=
                "2" * 64,
            eval_gt_sha256=
                "3" * 64,
        ),
        lambda: build_eval_scoring_result_payload(
            selected_estimator=
                "SC5_AGREEMENT",
            scoring_rows=[],
            safeguard=safeguard,
            collection_freeze_sha256=
                "1" * 64,
            dev_method_freeze_sha256=
                "2" * 64,
            eval_gt_sha256=
                "3" * 64,
        ),
        lambda: build_eval_scoring_result_payload(
            selected_estimator=
                "SC5_AGREEMENT",
            scoring_rows=rows,
            safeguard={
                **safeguard,
                "n": 999,
            },
            collection_freeze_sha256=
                "1" * 64,
            dev_method_freeze_sha256=
                "2" * 64,
            eval_gt_sha256=
                "3" * 64,
        ),
        lambda: build_eval_scoring_result_payload(
            selected_estimator=
                "SC5_AGREEMENT",
            scoring_rows=rows,
            safeguard=safeguard,
            collection_freeze_sha256=
                "bad",
            dev_method_freeze_sha256=
                "2" * 64,
            eval_gt_sha256=
                "3" * 64,
        ),
    ]

    for fn in bad_cases:
        try:
            fn()
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Synthetic result fail-closed case passed."
            )

    return {
        "status": "PASS",
        "decision":
            payload["safeguard"]["decision"],
        "scoring_population":
            payload["scoring_population"]["n"],
        "overwrite_blocked":
            overwrite_blocked,
        "fail_closed_tests":
            fail_closed,
        "installed_sha256":
            installed_sha,
        "real_eval_ground_truth_file_opened":
            False,
        "real_eval_scoring_performed":
            False,
        "real_scoring_result_created":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def scientific_collection_freeze_state() -> dict:
    if not COLLECTION_FREEZE.exists():
        return {
            "valid": False,
            "exists": False,
            "reason":
                "EVAL collection-freeze artifact does not exist",
        }

    if (
        sha256_file(COLLECTION_EXECUTOR)
        != EXPECTED_COLLECTION_EXECUTOR_SHA
    ):
        raise RuntimeError(
            "Frozen collection executor SHA mismatch."
        )

    collection = load_module(
        COLLECTION_EXECUTOR,
        "gate6d_eval_collection_executor_for_scoring",
    )

    payload = json.loads(
        COLLECTION_FREEZE.read_text(
            encoding="utf-8"
        )
    )

    if not DEV_METHOD_FREEZE.exists():
        raise RuntimeError(
            "DEV method freeze missing."
        )

    method = json.loads(
        DEV_METHOD_FREEZE.read_text(
            encoding="utf-8"
        )
    )

    plan = (
        collection.collection_plan_from_method_freeze(
            method
        )
    )

    collection.validate_collection_freeze_payload(
        payload,
        sc5_path=collection.EVAL_SC5_TERMINAL,
        vc_path=collection.EVAL_VC_TERMINAL,
        raw_path=collection.EVAL_RAW_ATTEMPTS,
        events_path=collection.EVAL_SESSION_EVENTS,
        dev_commit_marker_path=DEV_COMMIT_MARKER,
        dev_method_freeze_path=DEV_METHOD_FREEZE,
    )

    expected_manifest = [
        {
            "item_id":
                f"G6D-E-{i:04d}"
        }
        for i in range(
            1,
            collection.EXPECTED_EVAL_ITEMS + 1,
        )
    ]

    recomputed = (
        collection.validate_collection_complete(
            plan,
            expected_manifest,
            collection.EVAL_SC5_TERMINAL,
            collection.EVAL_VC_TERMINAL,
        )
    )

    if payload.get("completeness") != recomputed:
        raise RuntimeError(
            "Collection completeness binding mismatch."
        )

    if (
        payload.get("selected_estimator")
        != plan["selected_estimator"]
    ):
        raise RuntimeError(
            "Collection selected-estimator mismatch."
        )

    return {
        "valid": True,
        "exists": True,
        "reason": None,
        "selected_estimator":
            plan["selected_estimator"],
        "collection_freeze_sha256":
            sha256_file(COLLECTION_FREEZE),
        "completeness": recomputed,
    }


def preflight() -> dict:
    if sha256_file(BOUNDARY) != EXPECTED_BOUNDARY_SHA:
        raise RuntimeError(
            "EVAL boundary SHA mismatch."
        )

    if (
        sha256_file(COLLECTION_EXECUTOR_FREEZE)
        != EXPECTED_COLLECTION_EXECUTOR_FREEZE_SHA
    ):
        raise RuntimeError(
            "Collection executor freeze SHA mismatch."
        )

    if (
        sha256_file(COLLECTION_EXECUTOR)
        != EXPECTED_COLLECTION_EXECUTOR_SHA
    ):
        raise RuntimeError(
            "Collection executor SHA mismatch."
        )

    boundary = load_module(
        BOUNDARY,
        "gate6d_eval_boundary_v2_scoring",
    )

    scoring_gate = boundary.current_scoring_gate()

    scientific = (
        scientific_collection_freeze_state()
    )

    env_enabled = (
        os.getenv(SCORING_ENV) == "YES"
    )

    reasons = list(
        scoring_gate["reasons"]
    )

    if (
        scientific["exists"]
        and not scientific["valid"]
    ):
        reasons.append(
            scientific["reason"]
        )

    scoring_result_exists = (
        EVAL_SCORING_RESULT.exists()
    )

    if scoring_result_exists:
        reasons.append(
            "EVAL scoring result already exists"
        )

    ready = (
        env_enabled
        and scoring_gate["allowed"]
        and scientific["valid"]
        and not scoring_result_exists
    )

    return {
        "ready": ready,
        "env_enabled": env_enabled,
        "collection_freeze_exists":
            scientific["exists"],
        "scientific_collection_freeze_valid":
            scientific["valid"],
        "scoring_result_exists":
            scoring_result_exists,
        "reasons": reasons,
    }


def execute_real_scoring() -> dict:
    # Metadata/provenance gate first.
    # No hidden GT access is permitted before this passes.
    pf = preflight()

    if not pf["ready"]:
        return {
            "status": "BLOCKED",
            "reasons": pf["reasons"],
            "sealed_eval_ground_truth_opened":
                False,
            "correctness_computed":
                False,
            "real_eval_scoring_performed":
                False,
            "scoring_result_created":
                False,
            "external_test_accessed":
                False,
            "gate7_opened":
                False,
        }

    verify_scoring_dependencies()

    scientific = (
        scientific_collection_freeze_state()
    )

    if not scientific["valid"]:
        raise RuntimeError(
            "Scientific collection freeze invalid."
        )

    method_freeze = json.loads(
        DEV_METHOD_FREEZE.read_text(
            encoding="utf-8"
        )
    )

    cfg = (
        extract_frozen_scoring_configuration(
            method_freeze
        )
    )

    if (
        cfg["selected_estimator"]
        != scientific["selected_estimator"]
    ):
        raise RuntimeError(
            "Collection/scoring estimator mismatch."
        )

    collection = load_module(
        COLLECTION_EXECUTOR,
        "gate6d_collection_for_real_scoring",
    )

    sc5_done = (
        collection.load_terminal_map_strict(
            collection.EVAL_SC5_TERMINAL
        )
    )

    vc_done = (
        collection.load_terminal_map_strict(
            collection.EVAL_VC_TERMINAL
        )
    )

    # This is the first operation allowed to touch hidden EVAL GT.
    ground_truth = (
        load_eval_ground_truth_after_unlock()
    )

    rows = build_scoring_rows(
        cfg["selected_estimator"],
        cfg["mapping"],
        cfg["dev_correctness_prevalence"],
        sc5_done,
        vc_done,
        ground_truth,
    )

    safeguard = evaluate_eval_safeguard(
        rows
    )

    payload = (
        build_eval_scoring_result_payload(
            selected_estimator=
                cfg["selected_estimator"],
            scoring_rows=rows,
            safeguard=safeguard,
            collection_freeze_sha256=
                sha256_file(
                    COLLECTION_FREEZE
                ),
            dev_method_freeze_sha256=
                sha256_file(
                    DEV_METHOD_FREEZE
                ),
            eval_gt_sha256=
                sha256_file(
                    SEALED_EVAL_GT
                ),
        )
    )

    payload["provenance"][
        "eval_scoring_executor_sha256"
    ] = sha256_file(
        SCORING_EXECUTOR
    )

    data = canonical_json_bytes(
        payload
    )

    result_sha = install_bytes_new_only(
        EVAL_SCORING_RESULT,
        data,
    )

    return {
        "status":
            "COMPLETE_AND_FROZEN",
        "decision":
            safeguard["decision"],
        "selected_estimator":
            cfg["selected_estimator"],
        "scoring_population":
            len(rows),
        "scoring_result_sha256":
            result_sha,
        "sealed_eval_ground_truth_opened":
            True,
        "correctness_computed":
            True,
        "real_eval_scoring_performed":
            True,
        "scoring_result_created":
            True,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preflight",
        action="store_true",
    )
    args = parser.parse_args()

    if not args.preflight:
        parser.error("Use --preflight.")

    pf = preflight()

    print("EVAL SCORING EXECUTOR V1 WORKING COPY")
    print("Real scoring implemented: NO")
    print("Scoring ready:", pf["ready"])
    print("Scoring env enabled:", pf["env_enabled"])
    print(
        "Collection freeze exists:",
        pf["collection_freeze_exists"],
    )
    print(
        "Scientific collection freeze valid:",
        pf["scientific_collection_freeze_valid"],
    )
    print(
        "Scoring result exists:",
        pf["scoring_result_exists"],
    )

    for reason in pf["reasons"]:
        print("-", reason)

    print("Hidden EVAL ground truth opened: NO")
    print("Correctness computed: NO")
    print("External-TEST accessed: NO")
    print("Gate 7 opened: NO")


if __name__ == "__main__":
    main()
