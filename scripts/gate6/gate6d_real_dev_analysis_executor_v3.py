#!/usr/bin/env python3

"""
Gate 6D real DEV analysis executor V3.

CURRENT V3 STATE:
- working implementation for future real DEV execution;
- real execution remains hard-gated and must fail closed while DEV500 is incomplete;
- blocked real preflight remains available;
- no DEV correctness-bearing files opened;
- no Calibration-EVAL/Test access;
- no model calls.

V2 prospectively validates the future item-level OOF construction
and cross-binding transaction before any real DEV analysis is enabled.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import tempfile
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

NORMALIZATION_CORE = Path(
    "scripts/gate6/gate6d_dev_normalization_core_v1.py"
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

    NORMALIZATION_CORE:
        "7983ed4320908fd87913bc7a3b03113350763efb0fed1d8d00ba675da81e7ba0",

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


REAL_ANALYSIS_ENV = "GATE6D_ALLOW_REAL_DEV_ANALYSIS"



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


def build_oof_rows(primary: dict, cal) -> list[dict]:
    paired = primary["paired_rows"]
    candidates = primary["candidate_objects"]

    expected_slots = {
        ("SC5_AGREEMENT", "identity"),
        ("SC5_AGREEMENT", "platt"),
        ("SC5_AGREEMENT", "isotonic"),
        ("VC_SELF_EVAL", "identity"),
        ("VC_SELF_EVAL", "platt"),
        ("VC_SELF_EVAL", "isotonic"),
    }

    got_slots = {
        (x.estimator, x.calibrator)
        for x in candidates
    }

    if got_slots != expected_slots:
        raise RuntimeError("Candidate-slot set mismatch.")

    n = len(paired)

    for x in candidates:
        if x.valid:
            if x.oof_prob is None or len(x.oof_prob) != n:
                raise RuntimeError("Valid candidate OOF mismatch.")
        elif x.oof_prob is not None:
            raise RuntimeError("Invalid candidate must have null OOF.")

    baseline = cal.grouped_constant_baseline_oof(
        [r["correctness"] for r in paired],
        [r["cv_fold"] for r in paired],
    )

    if len(baseline) != n:
        raise RuntimeError("Baseline OOF length mismatch.")

    rows = []

    for i, src in enumerate(paired):
        if "capture" not in src or "episode_start_utc" not in src:
            raise RuntimeError("Episode metadata missing.")

        probs = {
            "SC5_AGREEMENT": {},
            "VC_SELF_EVAL": {},
        }

        for x in candidates:
            value = (
                None
                if not x.valid
                else float(x.oof_prob[i])
            )

            if value is not None and (
                not math.isfinite(value)
                or value < 0.0
                or value > 1.0
            ):
                raise RuntimeError("Invalid candidate probability.")

            probs[x.estimator][x.calibrator] = value

        base = float(baseline[i])

        if (
            not math.isfinite(base)
            or base < 0.0
            or base > 1.0
        ):
            raise RuntimeError("Invalid baseline probability.")

        rows.append({
            "item_id": src["item_id"],
            "capture": src["capture"],
            "episode_start_utc": src["episode_start_utc"],
            "cv_fold": int(src["cv_fold"]),
            "ground_truth": src["ground_truth"],
            "correctness": int(src["correctness"]),
            "sc5_agreement": float(src["sc5_agreement"]),
            "vc_raw_confidence": float(src["vc_raw_confidence"]),
            "oof_probabilities": probs,
            "constant_baseline_oof_probability": base,
        })

    ids = [r["item_id"] for r in rows]

    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate OOF item_id.")

    rows.sort(key=lambda r: r["item_id"])

    return rows


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


def serialize_oof_rows(rows: list[dict]) -> bytes:
    text = "".join(
        json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ) + "\n"
        for row in rows
    )

    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bind_oof_to_method_freeze(
    method_payload: dict,
    rows: list[dict],
    oof_bytes: bytes,
    method,
) -> dict:
    paired_sha = method.item_id_set_sha256(
        rows
    )

    expected_sha = method_payload[
        "primary_comparison"
    ][
        "item_id_set_sha256"
    ]

    if paired_sha != expected_sha:
        raise RuntimeError(
            "OOF/method paired item-set SHA mismatch."
        )

    if len(rows) != method_payload[
        "primary_comparison"
    ][
        "n"
    ]:
        raise RuntimeError(
            "OOF/method paired row-count mismatch."
        )

    bound = dict(method_payload)

    bound["oof_predictions"] = {
        "path": str(OOF_PATH),
        "sha256": sha256_bytes(
            oof_bytes
        ),
        "rows": len(rows),
        "item_id_set_sha256": paired_sha,
        "deterministic_order":
            "lexicographic item_id",
    }

    return bound


def validate_oof_method_cross_binding(
    method_payload: dict,
    rows: list[dict],
    oof_bytes: bytes,
    method,
) -> None:
    binding = method_payload.get(
        "oof_predictions"
    )

    if not isinstance(binding, dict):
        raise RuntimeError(
            "Method freeze lacks OOF binding."
        )

    if binding.get("path") != str(OOF_PATH):
        raise RuntimeError(
            "OOF path binding mismatch."
        )

    if binding.get("sha256") != sha256_bytes(
        oof_bytes
    ):
        raise RuntimeError(
            "OOF SHA binding mismatch."
        )

    if binding.get("rows") != len(rows):
        raise RuntimeError(
            "OOF row-count binding mismatch."
        )

    paired_sha = method.item_id_set_sha256(
        rows
    )

    if (
        binding.get(
            "item_id_set_sha256"
        )
        != paired_sha
    ):
        raise RuntimeError(
            "OOF item-set binding mismatch."
        )

    if (
        method_payload[
            "primary_comparison"
        ][
            "item_id_set_sha256"
        ]
        != paired_sha
    ):
        raise RuntimeError(
            "Method primary item-set mismatch."
        )


def serialize_json_object(obj: dict) -> bytes:
    return (
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def frozen_dependency_bindings() -> dict:
    contract = json.loads(
        CONTRACT.read_text(
            encoding="utf-8"
        )
    )

    deps = contract.get(
        "frozen_dependencies"
    )

    if not isinstance(deps, dict) or not deps:
        raise RuntimeError(
            "Output contract frozen_dependencies missing."
        )

    out = {}

    for name, info in sorted(deps.items()):
        if not isinstance(info, dict):
            raise RuntimeError(
                "Invalid frozen dependency record: "
                + str(name)
            )

        path_text = info.get("path")
        expected_sha = info.get("sha256")

        if (
            not isinstance(path_text, str)
            or not isinstance(expected_sha, str)
            or len(expected_sha) != 64
        ):
            raise RuntimeError(
                "Invalid frozen dependency binding: "
                + str(name)
            )

        path = Path(path_text)

        if not path.exists():
            raise RuntimeError(
                "Frozen dependency missing: "
                + path_text
            )

        actual = sha256_file(path)

        if actual != expected_sha:
            raise RuntimeError(
                "Frozen dependency SHA mismatch: "
                + path_text
            )

        out[name] = {
            "path": path_text,
            "sha256": expected_sha,
        }

    return out


def build_commit_marker(
    *,
    oof_bytes: bytes,
    method_bytes: bytes,
    rows: list[dict],
    method,
) -> dict:
    return {
        "artifact":
            "GATE6D_DEV_OOF_PREDICTIONS_FREEZE_V1",
        "status":
            "FROZEN_OOF_PREDICTIONS",
        "transaction_role":
            "FINAL_SCIENTIFIC_COMMIT_MARKER",
        "oof_predictions": {
            "path": str(OOF_PATH),
            "sha256": sha256_bytes(oof_bytes),
            "rows": len(rows),
            "item_id_set_sha256":
                method.item_id_set_sha256(rows),
        },
        "method_freeze": {
            "path": str(METHOD_FREEZE),
            "sha256": sha256_bytes(method_bytes),
        },
        "output_contract": {
            "path": str(CONTRACT),
            "sha256": EXPECTED[CONTRACT],
        },
        "output_contract_freeze": {
            "path": str(CONTRACT_FREEZE),
            "sha256": EXPECTED[CONTRACT_FREEZE],
        },
        "frozen_dependencies":
            frozen_dependency_bindings(),
        "governance": {
            "commit_marker_written_last": True,
            "eval_unlock_requires_this_marker": True,
            "secondary_consumption_requires_this_marker": True,
            "overwrite_existing_final_artifact_permitted":
                False,
        },
        "safety": {
            "calibration_eval_accessed": False,
            "external_test_accessed": False,
            "model_calls": 0,
            "gate7_opened": False,
        },
    }


def validate_commit_marker(
    marker_obj: dict,
    *,
    oof_bytes: bytes,
    method_bytes: bytes,
    rows: list[dict],
    method,
) -> None:
    if (
        marker_obj.get("status")
        != "FROZEN_OOF_PREDICTIONS"
    ):
        raise RuntimeError(
            "Commit marker status mismatch."
        )

    oof = marker_obj.get("oof_predictions")

    if not isinstance(oof, dict):
        raise RuntimeError(
            "Commit marker OOF binding missing."
        )

    if oof.get("path") != str(OOF_PATH):
        raise RuntimeError(
            "Commit marker OOF path mismatch."
        )

    if oof.get("sha256") != sha256_bytes(
        oof_bytes
    ):
        raise RuntimeError(
            "Commit marker OOF SHA mismatch."
        )

    if oof.get("rows") != len(rows):
        raise RuntimeError(
            "Commit marker OOF row count mismatch."
        )

    if (
        oof.get("item_id_set_sha256")
        != method.item_id_set_sha256(rows)
    ):
        raise RuntimeError(
            "Commit marker OOF item-set mismatch."
        )

    mf = marker_obj.get("method_freeze")

    if not isinstance(mf, dict):
        raise RuntimeError(
            "Commit marker method binding missing."
        )

    if mf.get("path") != str(METHOD_FREEZE):
        raise RuntimeError(
            "Commit marker method path mismatch."
        )

    if mf.get("sha256") != sha256_bytes(
        method_bytes
    ):
        raise RuntimeError(
            "Commit marker method SHA mismatch."
        )

    contract_binding = marker_obj.get(
        "output_contract"
    )

    if (
        not isinstance(contract_binding, dict)
        or contract_binding.get("path") != str(CONTRACT)
        or contract_binding.get("sha256") != EXPECTED[CONTRACT]
        or sha256_file(CONTRACT) != EXPECTED[CONTRACT]
    ):
        raise RuntimeError(
            "Commit marker output-contract binding mismatch."
        )

    contract_freeze_binding = marker_obj.get(
        "output_contract_freeze"
    )

    if (
        not isinstance(contract_freeze_binding, dict)
        or contract_freeze_binding.get("path")
            != str(CONTRACT_FREEZE)
        or contract_freeze_binding.get("sha256")
            != EXPECTED[CONTRACT_FREEZE]
        or sha256_file(CONTRACT_FREEZE)
            != EXPECTED[CONTRACT_FREEZE]
    ):
        raise RuntimeError(
            "Commit marker contract-freeze binding mismatch."
        )

    expected_dependencies = frozen_dependency_bindings()

    if (
        marker_obj.get("frozen_dependencies")
        != expected_dependencies
    ):
        raise RuntimeError(
            "Commit marker frozen-dependency binding mismatch."
        )

    governance = marker_obj.get(
        "governance",
        {},
    )

    if governance.get(
        "commit_marker_written_last"
    ) is not True:
        raise RuntimeError(
            "Commit marker ordering governance mismatch."
        )


def write_new_only(
    path: Path,
    data: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open("xb") as f:
        f.write(data)
        f.flush()


def synthetic_filesystem_transaction_test() -> dict:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        oof = root / "oof_predictions.jsonl"
        method = root / "method_freeze.json"
        marker = root / "commit_marker.json"

        # Empty transaction.
        assert not oof.exists()
        assert not method.exists()
        assert not marker.exists()

        # OOF installed first.
        install_bytes_new_only(oof, b"OOF\n")
        assert oof.exists()
        assert not method.exists()
        assert not marker.exists()

        # Simulated crash here must be partial/uncommitted.
        state1 = classify_transaction_state({
            "oof_predictions": oof.exists(),
            "method_freeze": method.exists(),
            "commit_marker": marker.exists(),
        })
        assert state1["state"] == "PARTIAL_UNCOMMITTED"

        # Method installed second.
        install_bytes_new_only(method, b"METHOD\n")
        assert oof.exists()
        assert method.exists()
        assert not marker.exists()

        state2 = classify_transaction_state({
            "oof_predictions": oof.exists(),
            "method_freeze": method.exists(),
            "commit_marker": marker.exists(),
        })
        assert state2["state"] == "PARTIAL_UNCOMMITTED"

        # Commit marker installed last.
        install_bytes_new_only(marker, b"MARKER\n")

        state3 = classify_transaction_state({
            "oof_predictions": oof.exists(),
            "method_freeze": method.exists(),
            "commit_marker": marker.exists(),
        })
        assert state3["state"] == "COMMITTED"

        overwrite_blocked = False

        try:
            install_bytes_new_only(oof, b"REPLACEMENT\n")
        except FileExistsError:
            overwrite_blocked = True

        assert overwrite_blocked is True

    return {
        "status": "PASS",
        "oof_first": True,
        "method_second": True,
        "marker_last": True,
        "crash_after_oof_is_partial": True,
        "crash_after_method_is_partial": True,
        "existing_final_overwrite_blocked": True,
        "real_final_paths_written": False,
        "real_dev_outputs_opened": False,
        "hidden_dev_ground_truth_opened": False,
        "calibration_eval_accessed": False,
        "external_test_accessed": False,
        "model_calls": 0,
        "gate7_opened": False,
    }


def synthetic_oof_self_test() -> dict:
    verify_dependencies()

    norm = load_module(
        NORMALIZATION_CORE,
        "gate6d_v2_norm",
    )
    cal = load_module(
        CAL_CORE,
        "gate6d_v2_cal",
    )
    method = load_module(
        METHOD_CORE,
        "gate6d_v2_method",
    )

    normalized = norm.normalize_dev500(
        **norm.synthetic_fixture()
    )

    paired = normalized["paired_rows"]

    for i, row in enumerate(paired):
        group = i % 48

        if group < 12:
            capture = "AmazonEcho-SYNTHETIC"
        else:
            capture = "Windows7AD-SYNTHETIC"

        row["capture"] = capture
        row["episode_start_utc"] = (
            f"2026-01-01T{group:02d}:00:00+00:00"
        )

    primary = method.evaluate_primary(
        normalized,
        cal,
    )

    rows = build_oof_rows(
        primary,
        cal,
    )

    oof_bytes = serialize_oof_rows(
        rows
    )

    method_payload = (
        method.build_method_freeze_payload(
            normalized,
            cal,
            synthetic=True,
        )
    )

    method_payload = bind_oof_to_method_freeze(
        method_payload,
        rows,
        oof_bytes,
        method,
    )

    method_bytes = serialize_json_object(
        method_payload
    )

    marker_obj = build_commit_marker(
        oof_bytes=oof_bytes,
        method_bytes=method_bytes,
        rows=rows,
        method=method,
    )

    validate_commit_marker(
        marker_obj,
        oof_bytes=oof_bytes,
        method_bytes=method_bytes,
        rows=rows,
        method=method,
    )

    validate_oof_method_cross_binding(
        method_payload,
        rows,
        oof_bytes,
        method,
    )

    required = {
        "item_id",
        "capture",
        "episode_start_utc",
        "cv_fold",
        "ground_truth",
        "correctness",
        "sc5_agreement",
        "vc_raw_confidence",
        "oof_probabilities",
        "constant_baseline_oof_probability",
    }

    assert len(rows) == 488
    assert all(set(r) == required for r in rows)
    assert [r["item_id"] for r in rows] == sorted(
        r["item_id"] for r in rows
    )
    assert len({
        (r["capture"], r["episode_start_utc"])
        for r in rows
    }) == 48

    candidates = primary["candidate_objects"]

    invalid = [
        x for x in candidates
        if not x.valid
    ]

    assert len(candidates) == 6
    assert len(invalid) == 1

    bad = invalid[0]

    assert all(
        r["oof_probabilities"][
            bad.estimator
        ][bad.calibrator] is None
        for r in rows
    )

    assert all(
        0.0 <= r[
            "constant_baseline_oof_probability"
        ] <= 1.0
        for r in rows
    )

    assert (
        method_payload[
            "oof_predictions"
        ][
            "sha256"
        ]
        == sha256_bytes(
            oof_bytes
        )
    )

    assert (
        method_payload[
            "oof_predictions"
        ][
            "item_id_set_sha256"
        ]
        == method_payload[
            "primary_comparison"
        ][
            "item_id_set_sha256"
        ]
    )

    tamper_blocked = False

    try:
        validate_oof_method_cross_binding(
            method_payload,
            rows,
            oof_bytes + b"X",
            method,
        )
    except RuntimeError:
        tamper_blocked = True

    assert tamper_blocked is True

    marker_tamper_blocked = False

    try:
        validate_commit_marker(
            marker_obj,
            oof_bytes=oof_bytes,
            method_bytes=method_bytes + b"X",
            rows=rows,
            method=method,
        )
    except RuntimeError:
        marker_tamper_blocked = True

    assert marker_tamper_blocked is True

    dependency_tamper_blocked = False

    tampered_marker = json.loads(
        json.dumps(marker_obj)
    )

    first_dep = sorted(
        tampered_marker[
            "frozen_dependencies"
        ]
    )[0]

    tampered_marker[
        "frozen_dependencies"
    ][
        first_dep
    ][
        "sha256"
    ] = "0" * 64

    try:
        validate_commit_marker(
            tampered_marker,
            oof_bytes=oof_bytes,
            method_bytes=method_bytes,
            rows=rows,
            method=method,
        )
    except RuntimeError:
        dependency_tamper_blocked = True

    assert dependency_tamper_blocked is True

    return {
        "status": "PASS",
        "paired_rows": len(rows),
        "candidate_slots": len(candidates),
        "invalid_candidate_slots": len(invalid),
        "episode_groups": 48,
        "lexicographic_order": True,
        "invalid_candidate_null_semantics": True,
        "baseline_probability_validation": True,
        "method_freeze_oof_cross_binding": True,
        "oof_sha_tamper_blocked": True,
        "commit_marker_cross_binding": True,
        "method_sha_tamper_blocked": True,
        "frozen_dependency_bindings": True,
        "dependency_sha_tamper_blocked": True,
        "real_dev_outputs_opened": False,
        "hidden_dev_ground_truth_opened": False,
        "calibration_eval_accessed": False,
        "external_test_accessed": False,
        "model_calls": 0,
        "gate7_opened": False,
    }


def install_bytes_new_only(
    final_path: Path,
    data: bytes,
) -> str:
    final_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, tmp_name = tempfile.mkstemp(
        prefix=final_path.name + ".tmp.",
        dir=str(final_path.parent),
    )

    tmp = Path(tmp_name)

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        digest = sha256_file(tmp)

        if digest != sha256_bytes(data):
            raise RuntimeError(
                "Temporary artifact SHA validation failed: "
                + str(final_path)
            )

        # Atomic no-overwrite install on the same filesystem.
        os.link(tmp, final_path)

    finally:
        if tmp.exists():
            tmp.unlink()

    if sha256_file(final_path) != sha256_bytes(data):
        raise RuntimeError(
            "Installed artifact SHA validation failed: "
            + str(final_path)
        )

    return sha256_file(final_path)


def execute_real_analysis() -> dict:
    gate = preflight()

    if not gate["ready_for_real_analysis"]:
        return {
            "status": "BLOCKED",
            "reasons":
                gate["loader_gate_reasons"]
                + (
                    []
                    if gate["real_analysis_env_allowed"]
                    else [
                        REAL_ANALYSIS_ENV
                        + " is not YES"
                    ]
                )
                + (
                    []
                    if gate["transaction_state"] == "EMPTY"
                    else [
                        "transaction state is "
                        + gate["transaction_state"]
                    ]
                ),
            "real_dev_outputs_opened": False,
            "hidden_dev_ground_truth_opened": False,
            "correctness_computed": False,
            "calibration_eval_accessed": False,
            "external_test_accessed": False,
            "model_calls": 0,
            "gate7_opened": False,
        }

    # Re-check final artifact state immediately before opening
    # correctness-bearing DEV data.
    if any([
        OOF_PATH.exists(),
        METHOD_FREEZE.exists(),
        COMMIT_MARKER.exists(),
    ]):
        raise RuntimeError(
            "Real execution refused: final artifact appeared "
            "after preflight."
        )

    verify_dependencies()

    loader = load_module(
        LOADER,
        "gate6d_v3_real_loader",
    )
    cal = load_module(
        CAL_CORE,
        "gate6d_v3_real_cal",
    )
    method = load_module(
        METHOD_CORE,
        "gate6d_v3_real_method",
    )

    normalized = loader.load_real_dev_rows()

    primary = method.evaluate_primary(
        normalized,
        cal,
    )

    rows = build_oof_rows(
        primary,
        cal,
    )

    oof_bytes = serialize_oof_rows(
        rows
    )

    method_payload = (
        method.build_method_freeze_payload(
            normalized,
            cal,
            synthetic=False,
        )
    )

    method_payload = bind_oof_to_method_freeze(
        method_payload,
        rows,
        oof_bytes,
        method,
    )

    validate_oof_method_cross_binding(
        method_payload,
        rows,
        oof_bytes,
        method,
    )

    method_bytes = serialize_json_object(
        method_payload
    )

    marker_obj = build_commit_marker(
        oof_bytes=oof_bytes,
        method_bytes=method_bytes,
        rows=rows,
        method=method,
    )

    validate_commit_marker(
        marker_obj,
        oof_bytes=oof_bytes,
        method_bytes=method_bytes,
        rows=rows,
        method=method,
    )

    marker_bytes = serialize_json_object(
        marker_obj
    )

    # Frozen transaction order:
    # OOF first, method freeze second, marker last.
    oof_sha = install_bytes_new_only(
        OOF_PATH,
        oof_bytes,
    )

    method_sha = install_bytes_new_only(
        METHOD_FREEZE,
        method_bytes,
    )

    # Before the scientific commit marker is installed,
    # verify both finals still equal the bound bytes.
    if oof_sha != marker_obj[
        "oof_predictions"
    ][
        "sha256"
    ]:
        raise RuntimeError(
            "Final OOF SHA differs from marker binding."
        )

    if method_sha != marker_obj[
        "method_freeze"
    ][
        "sha256"
    ]:
        raise RuntimeError(
            "Final method SHA differs from marker binding."
        )

    marker_sha = install_bytes_new_only(
        COMMIT_MARKER,
        marker_bytes,
    )

    final_state = classify_transaction_state({
        "oof_predictions": OOF_PATH.exists(),
        "method_freeze": METHOD_FREEZE.exists(),
        "commit_marker": COMMIT_MARKER.exists(),
    })

    if final_state["state"] != "COMMITTED":
        raise RuntimeError(
            "Scientific transaction did not reach COMMITTED."
        )

    return {
        "status": "COMMITTED",
        "paired_rows": len(rows),
        "winner_estimator":
            method_payload[
                "primary_comparison"
            ][
                "selection"
            ][
                "winner_estimator"
            ],
        "winner_calibrator":
            method_payload[
                "primary_comparison"
            ][
                "selection"
            ][
                "winner_calibrator"
            ],
        "oof_sha256": oof_sha,
        "method_freeze_sha256": method_sha,
        "commit_marker_sha256": marker_sha,
        "transaction_state":
            final_state["state"],
        "real_dev_outputs_opened": True,
        "hidden_dev_ground_truth_opened": True,
        "correctness_computed": True,
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

    analysis_env_allowed = (
        os.environ.get(
            REAL_ANALYSIS_ENV
        )
        == "YES"
    )

    ready = (
        loader_gate["allowed"]
        and analysis_env_allowed
        and tx["state"] == "EMPTY"
    )

    return {
        "ready_for_real_analysis":
            ready,

        "loader_gate_allowed":
            loader_gate["allowed"],

        "loader_gate_reasons":
            loader_gate["reasons"],

        "real_analysis_env_allowed":
            analysis_env_allowed,

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

    parser.add_argument(
        "--oof-self-test",
        action="store_true",
    )

    parser.add_argument(
        "--filesystem-self-test",
        action="store_true",
    )

    parser.add_argument(
        "--real-execute",
        action="store_true",
    )

    args = parser.parse_args()

    if (
        int(args.real_preflight)
        + int(args.self_test)
        + int(args.oof_self_test)
        + int(args.filesystem_self_test)
        + int(args.real_execute)
        != 1
    ):
        print(
            "BLOCKED: choose exactly one of "
            "--real-preflight, --self-test, "
            "--oof-self-test, --filesystem-self-test, "
            "or --real-execute."
        )
        print(
            "No real DEV analysis was run."
        )
        return

    if args.real_execute:
        result = execute_real_analysis()

        print("=== GATE 6D V3 REAL DEV EXECUTION ===")

        for key, value in result.items():
            print(f"{key}: {value}")

        return

    if args.filesystem_self_test:
        result = synthetic_filesystem_transaction_test()

        print("=== GATE 6D V2 FILESYSTEM TRANSACTION SELF-TEST ===")

        for key, value in result.items():
            print(f"{key}: {value}")

        return

    if args.oof_self_test:
        result = synthetic_oof_self_test()

        print("=== GATE 6D V2 SYNTHETIC OOF SELF-TEST ===")

        for key, value in result.items():
            print(f"{key}: {value}")

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

    print(
        "Real analysis env allowed:",
        result["real_analysis_env_allowed"],
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
