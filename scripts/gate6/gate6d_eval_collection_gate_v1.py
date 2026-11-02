#!/usr/bin/env python3

"""
Gate 6D Calibration-EVAL collection gate V1.

SYNTHETIC-ONLY + fail-closed preflight.

This module deliberately has NO real EVAL collection mode.

It verifies that future EVAL collection will:
- require the real frozen DEV method artifact first;
- reuse the exact frozen Gate 6D DEV collector semantics;
- collect SC5 for every EVAL item;
- collect VC only if VC_SELF_EVAL is the frozen estimator and SC5 is valid;
- never regenerate terminal semantic-invalid outputs;
- freeze complete model outputs before EVAL ground truth can be scored.

No sealed EVAL model input, manifest, or ground-truth file is opened here.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


DEV_COLLECTOR = Path(
    "scripts/gate6/"
    "run_gate6d_dev_uncertainty_collection_v1_2.py"
)

SAFEGUARD_PROTOCOL = Path(
    "benchmarks/gate6d/"
    "GATE6D_EVAL_EXECUTION_SAFEGUARD_PROTOCOL_V1.json"
)

METHOD_CORE_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_METHOD_FREEZE_CORE_FREEZE_V1.json"
)

VC_PROMPT = Path(
    "benchmarks/gate6d/"
    "collector_v1_2/"
    "vc_self_eval_system_prompt.txt"
)

REAL_METHOD_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_METHOD_FREEZE_V1.json"
)

# These paths are identifiers only.
# V1 never opens or hashes them.
SEALED_EVAL_INPUTS = Path(
    "benchmarks/gate6d/canonical_v1/"
    "sealed_eval_model_inputs.jsonl"
)

SEALED_EVAL_MANIFEST = Path(
    "benchmarks/gate6d/canonical_v1/"
    "sealed_eval_manifest.csv"
)

SEALED_EVAL_GT = Path(
    "benchmarks/gate6d/canonical_v1/"
    "hidden/eval_ground_truth.jsonl"
)

OUT = Path(
    "benchmarks/gate6d/"
    "eval_collection_gate_v1/"
    "synthetic_self_test.json"
)

EXPECTED_DEV_COLLECTOR_SHA = (
    "25da7632efd3fc49352652c08ce8deed8"
    "f09f00d6c16334e56e7d4de2568ac99"
)

EXPECTED_SAFEGAURD_SHA = (
    "48f187e146510a578fac405fc06d8b39"
    "b5159b57c1433889e276e40f380d7c0e"
)

EXPECTED_METHOD_CORE_FREEZE_SHA = (
    "fd41f251bc5a0f1a932897f5fb419855"
    "0fddb869bf9534bc7ccea525e7e1d92b"
)

EXPECTED_VC_PROMPT_SHA = (
    "51bb3bb0912123a315dba5c34cb08bed"
    "103f2a6b51795febbe2125e31cb47f2d"
)

EXPECTED_EVAL_ITEMS = 458

ALLOWED_ESTIMATORS = {
    "SC5_AGREEMENT",
    "VC_SELF_EVAL",
}

ALLOWED_CALIBRATORS = {
    "identity",
    "platt",
    "isotonic",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def verify_sha(
    path: Path,
    expected: str,
    name: str,
) -> str:
    if not path.exists():
        raise RuntimeError(
            f"{name} missing: {path}"
        )

    actual = sha256_file(path)

    if actual != expected:
        raise RuntimeError(
            f"{name} SHA mismatch: "
            f"expected {expected}, got {actual}"
        )

    return actual


def load_module(
    path: Path,
    name: str,
):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Unable to import {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[
        spec.name
    ] = module

    spec.loader.exec_module(
        module
    )

    return module


def verify_frozen_dependencies() -> dict:
    collector_sha = verify_sha(
        DEV_COLLECTOR,
        EXPECTED_DEV_COLLECTOR_SHA,
        "DEV collector V1.2",
    )

    safeguard_sha = verify_sha(
        SAFEGUARD_PROTOCOL,
        EXPECTED_SAFEGAURD_SHA,
        "EVAL safeguard protocol",
    )

    method_core_sha = verify_sha(
        METHOD_CORE_FREEZE,
        EXPECTED_METHOD_CORE_FREEZE_SHA,
        "DEV method-freeze core freeze",
    )

    vc_prompt_sha = verify_sha(
        VC_PROMPT,
        EXPECTED_VC_PROMPT_SHA,
        "VC system prompt",
    )

    protocol = json.loads(
        SAFEGUARD_PROTOCOL.read_text(
            encoding="utf-8"
        )
    )

    assert (
        protocol["status"]
        == "FROZEN_PROSPECTIVE_EVAL_OPERATIONALIZATION"
    )

    assert (
        protocol["sealed_eval_boundary"]["items"]
        == EXPECTED_EVAL_ITEMS
    )

    assert (
        protocol[
            "one_shot_semantics"
        ][
            "ground_truth_must_remain_unopened_during_model_collection"
        ]
        is True
    )

    assert (
        protocol[
            "one_shot_semantics"
        ][
            "collection_outputs_must_be_frozen_before_ground_truth_scoring"
        ]
        is True
    )

    return {
        "dev_collector_sha256":
            collector_sha,
        "eval_safeguard_sha256":
            safeguard_sha,
        "method_core_freeze_sha256":
            method_core_sha,
        "vc_prompt_sha256":
            vc_prompt_sha,
    }


def synthetic_method_freeze(
    estimator: str,
) -> dict:
    if estimator == "SC5_AGREEMENT":
        calibrator = "identity"
        mapping = {
            "calibrator":
                "identity",
            "definition":
                "p = clip(raw_confidence, 0, 1)",
        }

    elif estimator == "VC_SELF_EVAL":
        calibrator = "platt"
        mapping = {
            "calibrator":
                "platt",
            "definition":
                "sigmoid(a * raw_confidence + b)",
            "coefficient":
                2.0,
            "intercept":
                -1.0,
            "C":
                "infinity",
            "solver":
                "lbfgs",
            "max_iter":
                5000,
        }

    else:
        raise ValueError(
            "Unknown synthetic estimator."
        )

    return {
        "artifact":
            "GATE6D_DEV_METHOD_FREEZE_V1",

        "status":
            "FROZEN_METHOD_SELECTED",

        "primary_comparison": {
            "selection": {
                "winner_estimator":
                    estimator,
                "winner_calibrator":
                    calibrator,
            },
        },

        "post_selection_refit": {
            "estimator":
                estimator,
            "calibrator":
                calibrator,
            "population_rule":
                "ALL_VALID_DEV_FOR_WINNING_ESTIMATOR",
            "mapping":
                mapping,
        },

        "eval_constant_baseline": {
            "source_population":
                "ALL_VALID_DEV_FOR_WINNING_ESTIMATOR",
            "correctness_prevalence":
                0.80,
        },
    }


def validate_method_freeze(
    obj: dict,
) -> dict:
    if (
        obj.get("artifact")
        != "GATE6D_DEV_METHOD_FREEZE_V1"
    ):
        raise ValueError(
            "Wrong method-freeze artifact."
        )

    if (
        obj.get("status")
        != "FROZEN_METHOD_SELECTED"
    ):
        raise ValueError(
            "Method freeze is not FROZEN_METHOD_SELECTED."
        )

    selection = (
        obj.get(
            "primary_comparison",
            {},
        ).get(
            "selection",
            {},
        )
    )

    estimator = selection.get(
        "winner_estimator"
    )

    calibrator = selection.get(
        "winner_calibrator"
    )

    if estimator not in ALLOWED_ESTIMATORS:
        raise ValueError(
            "Unknown frozen estimator."
        )

    if calibrator not in ALLOWED_CALIBRATORS:
        raise ValueError(
            "Unknown frozen calibrator."
        )

    refit = obj.get(
        "post_selection_refit",
        {}
    )

    if (
        refit.get("estimator")
        != estimator
    ):
        raise ValueError(
            "Refit estimator disagrees with selected estimator."
        )

    if (
        refit.get("calibrator")
        != calibrator
    ):
        raise ValueError(
            "Refit calibrator disagrees with selected calibrator."
        )

    mapping = refit.get(
        "mapping"
    )

    if not isinstance(
        mapping,
        dict,
    ):
        raise ValueError(
            "Frozen mapping missing."
        )

    if (
        mapping.get("calibrator")
        != calibrator
    ):
        raise ValueError(
            "Frozen mapping calibrator mismatch."
        )

    baseline = obj.get(
        "eval_constant_baseline",
        {}
    )

    p = baseline.get(
        "correctness_prevalence"
    )

    if not isinstance(
        p,
        (int, float),
    ):
        raise ValueError(
            "Frozen DEV prevalence missing."
        )

    p = float(p)

    if not 0.0 <= p <= 1.0:
        raise ValueError(
            "Frozen DEV prevalence outside [0,1]."
        )

    return {
        "winner_estimator":
            estimator,
        "winner_calibrator":
            calibrator,
        "mapping":
            mapping,
        "eval_constant_baseline":
            p,
    }


def collection_plan(
    method: dict,
) -> dict:
    estimator = method[
        "winner_estimator"
    ]

    return {
        "eval_items":
            EXPECTED_EVAL_ITEMS,

        "sc5_required":
            True,

        "vc_required_after_valid_sc5":
            (
                estimator
                == "VC_SELF_EVAL"
            ),

        "vc_permitted":
            (
                estimator
                == "VC_SELF_EVAL"
            ),

        "terminal_semantic_invalid_regeneration":
            False,

        "ground_truth_open_during_collection":
            False,

        "freeze_outputs_before_ground_truth":
            True,
    }


def fake_response(
    outputs,
    *,
    status=200,
    success=True,
):
    return {
        "http_status":
            status,

        "body": {
            "success":
                success,
            "result": {
                "model":
                    "@cf/nvidia/nemotron-3-120b-a12b",
                "choices": [
                    {
                        "message": {
                            "content":
                                x
                        }
                    }
                    for x in outputs
                ],
            },
        },

        "raw_body":
            json.dumps(
                {
                    "success":
                        success,
                    "outputs":
                        outputs,
                }
            ),

        "latency_ms":
            1.0,
    }


def make_sc5_records(
    collector,
    ids,
):
    records = []

    for index, item_id in enumerate(
        ids,
        start=1,
    ):
        if index == 5:
            response = fake_response(
                [
                    "ESCALATE",
                    "ESCALATE",
                    "ESCALATE",
                    "DO_NOT_ESCALATE",
                    "MALFORMED",
                ]
            )
        else:
            response = fake_response(
                [
                    "ESCALATE",
                    "ESCALATE",
                    "ESCALATE",
                    "DO_NOT_ESCALATE",
                    "DO_NOT_ESCALATE",
                ]
            )

        parsed = collector.validate_sc5(
            response
        )

        records.append(
            {
                "item_id":
                    item_id,
                "valid":
                    bool(
                        parsed["valid"]
                    ),
                "invalid_reason":
                    parsed["reason"],
                "majority":
                    parsed.get(
                        "majority"
                    ),
                "agreement":
                    parsed.get(
                        "agreement"
                    ),
            }
        )

    return records


def make_vc_records(
    collector,
    ids,
    sc5_records,
):
    sc5_by_id = {
        r["item_id"]:
            r
        for r in sc5_records
    }

    records = []

    for index, item_id in enumerate(
        ids,
        start=1,
    ):
        sc5 = sc5_by_id[
            item_id
        ]

        if not sc5["valid"]:
            continue

        if index == 8:
            response = fake_response(
                ["82%"]
            )
        else:
            response = fake_response(
                ["82"]
            )

        parsed = collector.validate_vc(
            response
        )

        records.append(
            {
                "item_id":
                    item_id,
                "frozen_recommendation":
                    sc5["majority"],
                "valid":
                    bool(
                        parsed["valid"]
                    ),
                "invalid_reason":
                    parsed["reason"],
                "confidence_integer":
                    parsed.get(
                        "confidence_integer"
                    ),
                "raw_confidence":
                    parsed.get(
                        "raw_confidence"
                    ),
            }
        )

    return records


def unique_map(
    records,
    name: str,
):
    counts = Counter(
        r["item_id"]
        for r in records
    )

    dup = [
        k
        for k, v in counts.items()
        if v != 1
    ]

    if dup:
        raise ValueError(
            f"Duplicate {name} terminal record."
        )

    return {
        r["item_id"]:
            r
        for r in records
    }


def audit_synthetic_collection(
    ids,
    sc5_records,
    vc_records,
    estimator,
) -> dict:
    sc5 = unique_map(
        sc5_records,
        "SC5",
    )

    vc = unique_map(
        vc_records,
        "VC",
    )

    if set(sc5) != set(ids):
        raise ValueError(
            "Missing SC5 terminal record."
        )

    scoring_ids = []

    for item_id in ids:
        s = sc5[item_id]

        if not s["valid"]:
            if item_id in vc:
                raise ValueError(
                    "VC exists after invalid SC5."
                )
            continue

        if estimator == "SC5_AGREEMENT":
            if item_id in vc:
                raise ValueError(
                    "VC exists although SC5 is selected."
                )

            scoring_ids.append(
                item_id
            )

        elif estimator == "VC_SELF_EVAL":
            if item_id not in vc:
                raise ValueError(
                    "Missing required VC terminal record."
                )

            if vc[item_id]["valid"]:
                scoring_ids.append(
                    item_id
                )

        else:
            raise ValueError(
                "Unknown estimator."
            )

    return {
        "logical_collection_complete":
            True,
        "sc5_terminal":
            len(sc5),
        "vc_terminal":
            len(vc),
        "valid_scoring_items":
            len(scoring_ids),
        "scoring_item_ids":
            scoring_ids,
    }


def current_real_gate() -> dict:
    reasons = []

    env_ok = (
        os.getenv(
            "GATE6D_ALLOW_EVAL_COLLECTION"
        )
        == "YES"
    )

    method_exists = (
        REAL_METHOD_FREEZE.exists()
    )

    if not env_ok:
        reasons.append(
            "GATE6D_ALLOW_EVAL_COLLECTION is not YES"
        )

    if not method_exists:
        reasons.append(
            "real DEV method-freeze artifact does not exist"
        )

    return {
        "allowed":
            (
                env_ok
                and method_exists
            ),
        "env_enabled":
            env_ok,
        "real_method_freeze_exists":
            method_exists,
        "reasons":
            reasons,
    }


def synthetic_self_test() -> dict:
    frozen = (
        verify_frozen_dependencies()
    )

    collector = load_module(
        DEV_COLLECTOR,
        "gate6d_dev_collector_frozen_v1_2",
    )

    synthetic_messages = [
        {
            "role":
                "system",
            "content":
                "SYNTHETIC SYSTEM",
        },
        {
            "role":
                "user",
            "content":
                (
                    "SYNTHETIC ALERT"
                    + collector.DECISION_SUFFIX
                ),
        },
    ]

    sc5_payload = collector.sc5_payload(
        synthetic_messages,
        12345,
    )

    assert sc5_payload["n"] == 5
    assert sc5_payload["temperature"] == 0.4
    assert sc5_payload["seed"] == 12345
    assert (
        sc5_payload[
            "chat_template_kwargs"
        ][
            "enable_thinking"
        ]
        is True
    )
    assert (
        sc5_payload[
            "chat_template_kwargs"
        ][
            "low_effort"
        ]
        is True
    )

    vc_messages = collector.build_vc_messages(
        synthetic_messages,
        "ESCALATE",
    )

    vc_payload = collector.vc_payload(
        synthetic_messages,
        "ESCALATE",
        12345,
    )

    assert vc_payload["n"] == 1
    assert vc_payload["temperature"] == 0
    assert vc_payload["seed"] == 12345
    assert (
        "FROZEN RECOMMENDATION\nESCALATE"
        in vc_messages[1]["content"]
    )

    ids = [
        f"SYN-E-{i:03d}"
        for i in range(
            1,
            13,
        )
    ]

    sc5_records = make_sc5_records(
        collector,
        ids,
    )

    sc5_method = validate_method_freeze(
        synthetic_method_freeze(
            "SC5_AGREEMENT"
        )
    )

    sc5_plan = collection_plan(
        sc5_method
    )

    sc5_audit = audit_synthetic_collection(
        ids,
        sc5_records,
        [],
        "SC5_AGREEMENT",
    )

    assert (
        sc5_plan[
            "vc_permitted"
        ]
        is False
    )

    assert (
        sc5_audit[
            "valid_scoring_items"
        ]
        == 11
    )

    vc_records = make_vc_records(
        collector,
        ids,
        sc5_records,
    )

    vc_method = validate_method_freeze(
        synthetic_method_freeze(
            "VC_SELF_EVAL"
        )
    )

    vc_plan = collection_plan(
        vc_method
    )

    vc_audit = audit_synthetic_collection(
        ids,
        sc5_records,
        vc_records,
        "VC_SELF_EVAL",
    )

    assert (
        vc_plan[
            "vc_required_after_valid_sc5"
        ]
        is True
    )

    assert (
        vc_audit[
            "vc_terminal"
        ]
        == 11
    )

    assert (
        vc_audit[
            "valid_scoring_items"
        ]
        == 10
    )

    fail_closed = 0

    try:
        audit_synthetic_collection(
            ids,
            sc5_records[:-1],
            [],
            "SC5_AGREEMENT",
        )
    except ValueError:
        fail_closed += 1

    try:
        duplicated = (
            sc5_records
            + [dict(sc5_records[0])]
        )

        audit_synthetic_collection(
            ids,
            duplicated,
            [],
            "SC5_AGREEMENT",
        )
    except ValueError:
        fail_closed += 1

    try:
        bad_vc = (
            vc_records
            + [
                {
                    "item_id":
                        ids[4],
                    "valid":
                        True,
                }
            ]
        )

        audit_synthetic_collection(
            ids,
            sc5_records,
            bad_vc,
            "VC_SELF_EVAL",
        )
    except ValueError:
        fail_closed += 1

    if fail_closed != 3:
        raise AssertionError(
            "Expected three fail-closed synthetic tests."
        )

    gate = current_real_gate()

    # Current project state must remain blocked.
    if gate["allowed"]:
        raise AssertionError(
            "Real EVAL gate unexpectedly open."
        )

    return {
        "artifact":
            "GATE6D_EVAL_COLLECTION_GATE_"
            "SYNTHETIC_SELF_TEST_V1",

        "status":
            "PASS",

        "frozen_dependencies":
            frozen,

        "frozen_collector_semantics": {
            "model":
                collector.MODEL,
            "sc5_n":
                sc5_payload["n"],
            "sc5_temperature":
                sc5_payload[
                    "temperature"
                ],
            "vc_n":
                vc_payload["n"],
            "vc_temperature":
                vc_payload[
                    "temperature"
                ],
            "same_seed_for_sc5_and_vc":
                (
                    sc5_payload["seed"]
                    == vc_payload["seed"]
                ),
            "exact_label_parser_reused":
                True,
            "integer_0_100_parser_reused":
                True,
        },

        "synthetic_SC5_selected": {
            "plan":
                sc5_plan,
            "audit":
                sc5_audit,
        },

        "synthetic_VC_selected": {
            "plan":
                vc_plan,
            "audit":
                vc_audit,
        },

        "fail_closed_tests":
            fail_closed,

        "current_real_gate":
            gate,

        "real_eval_files_opened":
            False,

        "sealed_eval_model_inputs_opened":
            False,

        "sealed_eval_manifest_opened":
            False,

        "sealed_eval_ground_truth_opened":
            False,

        "real_eval_collection_performed":
            False,

        "model_calls":
            0,

        "external_test_accessed":
            False,

        "gate7_opened":
            False,
    }


def preflight() -> None:
    verify_frozen_dependencies()

    gate = current_real_gate()

    print(
        "=== GATE 6D EVAL COLLECTION PRE-FLIGHT ==="
    )

    if gate["allowed"]:
        print(
            "REAL EVAL GATE PREREQUISITES: PRESENT"
        )
        print(
            "V1 STILL HAS NO REAL COLLECTION MODE."
        )
    else:
        print(
            "REAL EVAL COLLECTION GATE: BLOCKED"
        )

        for reason in gate["reasons"]:
            print(
                "-",
                reason,
            )

    print(
        "Sealed EVAL model inputs opened: NO"
    )
    print(
        "Sealed EVAL manifest opened: NO"
    )
    print(
        "Hidden EVAL ground truth opened: NO"
    )
    print(
        "Real EVAL model calls: 0"
    )
    print(
        "External-TEST accessed: NO"
    )
    print(
        "Gate 7 opened: NO"
    )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    parser.add_argument(
        "--preflight",
        action="store_true",
    )

    args = parser.parse_args()

    if args.self_test:
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

        print(
            "=== GATE 6D EVAL COLLECTION "
            "GATE SYNTHETIC TEST ==="
        )
        print(
            "status:",
            result["status"],
        )
        print(
            "SC5-selected valid scoring items:",
            result[
                "synthetic_SC5_selected"
            ][
                "audit"
            ][
                "valid_scoring_items"
            ],
            "/ 12",
        )
        print(
            "SC5-selected VC terminal records:",
            result[
                "synthetic_SC5_selected"
            ][
                "audit"
            ][
                "vc_terminal"
            ],
        )
        print(
            "VC-selected valid scoring items:",
            result[
                "synthetic_VC_selected"
            ][
                "audit"
            ][
                "valid_scoring_items"
            ],
            "/ 12",
        )
        print(
            "VC-selected VC terminal records:",
            result[
                "synthetic_VC_selected"
            ][
                "audit"
            ][
                "vc_terminal"
            ],
        )
        print(
            "fail_closed_tests:",
            result[
                "fail_closed_tests"
            ],
            "PASS",
        )
        print(
            "current_real_gate_allowed:",
            result[
                "current_real_gate"
            ][
                "allowed"
            ],
        )
        print(
            "sealed_eval_model_inputs_opened: False"
        )
        print(
            "sealed_eval_manifest_opened: False"
        )
        print(
            "sealed_eval_ground_truth_opened: False"
        )
        print(
            "real_eval_collection_performed: False"
        )
        print(
            "model_calls: 0"
        )
        print(
            "external_test_accessed: False"
        )
        print(
            "gate7_opened: False"
        )

    else:
        preflight()


if __name__ == "__main__":
    main()
