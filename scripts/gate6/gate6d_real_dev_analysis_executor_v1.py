#!/usr/bin/env python3

"""
Gate 6D real DEV analysis executor V1.

CURRENT V1 STATE:
- preflight only;
- no real DEV analysis execution mode;
- no DEV correctness-bearing files opened;
- no Calibration-EVAL/Test access;
- no model calls.

Future execution will be added only after synthetic transaction
validation and a separate review.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


LOADER = Path(
    "scripts/gate6/gate6d_real_dev_loader_v1.py"
)

METHOD_CORE = Path(
    "scripts/gate6/gate6d_dev_method_freeze_core_v1.py"
)

CAL_CORE = Path(
    "scripts/gate6/gate6d_calibration_analysis_core.py"
)

CONTRACT = Path(
    "benchmarks/gate6d/"
    "GATE6D_REAL_DEV_ANALYSIS_OUTPUT_CONTRACT_V1.json"
)

CONTRACT_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_REAL_DEV_ANALYSIS_OUTPUT_CONTRACT_FREEZE_V1.json"
)

PARITY_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_METRIC_SEMANTICS_PARITY_FREEZE_V1.json"
)

EXPECTED = {
    LOADER:
        "f425035fc6114e4dd54db5682fdcc9851514fd072c4b79c5cdc1652b9b565e27",

    METHOD_CORE:
        "7551a3989ff71405f3301a9544dae5a4051f6997aa21f022aefb44cd091b8df8",

    CAL_CORE:
        "47a03118614e68c000101047c680b39929f1355ab9a8f1ba1565abcb81d52eba",

    CONTRACT:
        "b6ef2f678753c34e22fe6834bdc748326fd0cc67716c9e3a6232acd3bd6989cd",

    CONTRACT_FREEZE:
        "6aa1a0bf3954f2a61045148ff0f5bc8af89cf7e1774ce338bdb161580fb4928e",

    PARITY_FREEZE:
        "e48fabc0a9f7f3974a0311c9006299aaab51ab99382d332f6be2371215d0f687",
}

OOF_PATH = Path(
    "benchmarks/gate6d/"
    "dev_analysis_real_v1/"
    "oof_predictions.jsonl"
)

METHOD_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_METHOD_FREEZE_V1.json"
)

COMMIT_MARKER = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_OOF_PREDICTIONS_FREEZE_V1.json"
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
            f"Cannot import {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


def verify_dependencies() -> None:
    for path, expected in EXPECTED.items():
        if not path.exists():
            raise RuntimeError(
                f"Missing frozen dependency: {path}"
            )

        actual = sha256_file(path)

        if actual != expected:
            raise RuntimeError(
                f"SHA mismatch: {path}: "
                f"expected {expected}, got {actual}"
            )

    contract = json.loads(
        CONTRACT.read_text(
            encoding="utf-8"
        )
    )

    freeze = json.loads(
        CONTRACT_FREEZE.read_text(
            encoding="utf-8"
        )
    )

    if (
        contract["primary_analysis_population"]["rule"]
        != "PAIRED_COMMON_VALID"
    ):
        raise RuntimeError(
            "Primary population contract changed."
        )

    if (
        contract["candidate_contract"]["candidate_slots"]
        != 6
    ):
        raise RuntimeError(
            "Candidate-slot contract changed."
        )

    if (
        contract["atomicity_and_immutability"][
            "commit_marker_written_last"
        ]
        is not True
    ):
        raise RuntimeError(
            "Commit-marker contract changed."
        )

    if (
        freeze["contract"]["sha256"]
        != EXPECTED[CONTRACT]
    ):
        raise RuntimeError(
            "Contract-freeze binding mismatch."
        )


def classify_transaction_state(finals: dict) -> dict:
    oof = bool(finals["oof_predictions"])
    method = bool(finals["method_freeze"])
    marker = bool(finals["commit_marker"])

    if marker and not (oof and method):
        state = "INVALID_MARKER_WITH_MISSING_FINAL"
    elif marker:
        state = "COMMITTED"
    elif oof or method:
        state = "PARTIAL_UNCOMMITTED"
    else:
        state = "EMPTY"

    return {
        "state": state,
        "partial_transaction_present":
            state == "PARTIAL_UNCOMMITTED",
        "already_committed":
            state == "COMMITTED",
        "invalid_transaction":
            state == "INVALID_MARKER_WITH_MISSING_FINAL",
    }


def synthetic_transaction_self_test() -> dict:
    expected = {
        (False, False, False): "EMPTY",
        (True, False, False): "PARTIAL_UNCOMMITTED",
        (False, True, False): "PARTIAL_UNCOMMITTED",
        (True, True, False): "PARTIAL_UNCOMMITTED",
        (False, False, True): "INVALID_MARKER_WITH_MISSING_FINAL",
        (True, False, True): "INVALID_MARKER_WITH_MISSING_FINAL",
        (False, True, True): "INVALID_MARKER_WITH_MISSING_FINAL",
        (True, True, True): "COMMITTED",
    }

    checked = 0

    for (oof, method, marker), wanted in expected.items():
        got = classify_transaction_state({
            "oof_predictions": oof,
            "method_freeze": method,
            "commit_marker": marker,
        })

        assert got["state"] == wanted
        checked += 1

    return {
        "status": "PASS",
        "states_checked": checked,
        "all_boolean_combinations_checked": True,
        "real_dev_outputs_opened": False,
        "hidden_dev_ground_truth_opened": False,
        "calibration_eval_accessed": False,
        "external_test_accessed": False,
        "model_calls": 0,
        "gate7_opened": False,
    }


def preflight() -> dict:
    verify_dependencies()

    loader = load_module(
        LOADER,
        "gate6d_executor_loader_v1",
    )

    loader_gate = loader.real_gate_status()

    finals = {
        "oof_predictions":
            OOF_PATH.exists(),

        "method_freeze":
            METHOD_FREEZE.exists(),

        "commit_marker":
            COMMIT_MARKER.exists(),
    }

    tx = classify_transaction_state(
        finals
    )

    ready = (
        loader_gate["allowed"]
        and tx["state"] == "EMPTY"
    )

    return {
        "ready_for_real_analysis":
            ready,

        "loader_gate_allowed":
            loader_gate["allowed"],

        "loader_gate_reasons":
            loader_gate["reasons"],

        "future_final_artifacts":
            finals,

        "transaction_state":
            tx["state"],

        "partial_transaction_present":
            tx["partial_transaction_present"],

        "already_committed":
            tx["already_committed"],

        "invalid_transaction":
            tx["invalid_transaction"],

        "real_dev_outputs_opened":
            False,

        "hidden_dev_ground_truth_opened":
            False,

        "correctness_computed":
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


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--real-preflight",
        action="store_true",
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if (
        int(args.real_preflight)
        + int(args.self_test)
        != 1
    ):
        print(
            "BLOCKED: choose exactly one of "
            "--real-preflight or --self-test."
        )
        print(
            "No real DEV analysis was run."
        )
        return

    if args.self_test:
        result = synthetic_transaction_self_test()

        print(
            "=== GATE 6D REAL DEV EXECUTOR "
            "TRANSACTION SELF-TEST ==="
        )
        print("status:", result["status"])
        print(
            "states_checked:",
            result["states_checked"],
        )
        print(
            "all_boolean_combinations_checked:",
            result[
                "all_boolean_combinations_checked"
            ],
        )
        print("Real DEV outputs opened: NO")
        print("Hidden DEV ground truth opened: NO")
        print("Calibration-EVAL accessed: NO")
        print("External-TEST accessed: NO")
        print("Model calls: 0")
        print("Gate 7 opened: NO")
        return

    result = preflight()

    print(
        "=== GATE 6D REAL DEV ANALYSIS "
        "EXECUTOR PRE-FLIGHT ==="
    )

    print(
        "Frozen dependency validation: PASS"
    )

    print(
        "Real analysis ready:",
        result["ready_for_real_analysis"],
    )

    print(
        "Real loader gate allowed:",
        result["loader_gate_allowed"],
    )

    for reason in result[
        "loader_gate_reasons"
    ]:
        print("-", reason)

    print(
        "OOF final exists:",
        result[
            "future_final_artifacts"
        ][
            "oof_predictions"
        ],
    )

    print(
        "Method freeze exists:",
        result[
            "future_final_artifacts"
        ][
            "method_freeze"
        ],
    )

    print(
        "Commit marker exists:",
        result[
            "future_final_artifacts"
        ][
            "commit_marker"
        ],
    )

    print(
        "Transaction state:",
        result["transaction_state"],
    )

    print(
        "Partial transaction present:",
        result[
            "partial_transaction_present"
        ],
    )

    print(
        "Invalid transaction:",
        result[
            "invalid_transaction"
        ],
    )

    print(
        "Real DEV outputs opened: NO"
    )
    print(
        "Hidden DEV ground truth opened: NO"
    )
    print(
        "Correctness computed: NO"
    )
    print(
        "Calibration-EVAL accessed: NO"
    )
    print(
        "External-TEST accessed: NO"
    )
    print(
        "Model calls: 0"
    )
    print(
        "Gate 7 opened: NO"
    )


if __name__ == "__main__":
    main()
