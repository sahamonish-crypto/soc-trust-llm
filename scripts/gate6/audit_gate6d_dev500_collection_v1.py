#!/usr/bin/env python3

"""
Gate 6D DEV500 collection-complete audit/freeze tool V1.

Permitted inputs:
- frozen DEV500 selected-item manifest;
- SC5 terminal collection records;
- VC terminal collection records;
- collection provenance files for hashes only.

Explicitly outside this tool:
- correctness;
- labels/ground truth;
- calibration metrics;
- estimator comparison;
- Calibration-EVAL;
- External-TEST.

A collection item is logically complete when:
1. it has a terminal SC5 record; and
2a. SC5 is terminal-invalid, in which case VC must not exist; OR
2b. SC5 is valid, in which case a terminal VC record must exist
    (VC itself may be valid or terminal-invalid).

The FROZEN_COMPLETE artifact can be produced only when all 500
selected items satisfy the above rule and an explicit environment
gate is enabled.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


SELECTED_MANIFEST = Path(
    "benchmarks/gate6d/dev500_v1/"
    "dev500_selected_items.csv"
)

COLLECTION_DIR = Path(
    "benchmarks/gate6d/dev_collection_v1"
)

SC5_PATH = COLLECTION_DIR / "sc5_terminal.jsonl"
VC_PATH = COLLECTION_DIR / "vc_terminal.jsonl"
RAW_PATH = COLLECTION_DIR / "raw_attempts.jsonl"
EVENTS_PATH = COLLECTION_DIR / "session_events.jsonl"

COLLECTOR_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV500_COLLECTION_IMPLEMENTATION_FREEZE_V1_2.json"
)

EXPECTED_SELECTED_SHA = (
    "db1016850df42736c1851b66a296550f82e4509e90b33f08fff8a73bad2e0f87"
)

EXPECTED_COLLECTOR_FREEZE_SHA = (
    "b6a8dfb8115d6a1acac4ec751ee3d4c5844e60709b60b2ceaaf24f2a6d9edcb1"
)

AUDIT_DIR = Path(
    "benchmarks/gate6d/dev_collection_audit_v1"
)

CURRENT_AUDIT = AUDIT_DIR / "current_audit.json"

SYNTHETIC_AUDIT = (
    AUDIT_DIR / "synthetic_self_test.json"
)

COMPLETE_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1.json"
)

FREEZE_ENV = (
    "GATE6D_ALLOW_COLLECTION_COMPLETE_FREEZE"
)


def utcnow() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


def file_info(path: Path) -> dict:
    if not path.exists():
        return {
            "path": str(path),
            "exists": False,
            "sha256": None,
            "bytes": 0,
        }

    return {
        "path": str(path),
        "exists": True,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    rows = []

    with path.open(
        encoding="utf-8"
    ) as f:
        for lineno, line in enumerate(
            f,
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                row = json.loads(line)
            except Exception as exc:
                raise ValueError(
                    f"{path}: malformed JSON on "
                    f"line {lineno}"
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"{path}: non-object JSON on "
                    f"line {lineno}"
                )

            rows.append(row)

    return rows


def selected_ids_from_manifest() -> list[str]:
    if not SELECTED_MANIFEST.exists():
        raise RuntimeError(
            "Frozen DEV500 selected manifest missing."
        )

    actual = sha256_file(
        SELECTED_MANIFEST
    )

    if actual != EXPECTED_SELECTED_SHA:
        raise RuntimeError(
            "Frozen DEV500 selected manifest "
            "SHA mismatch."
        )

    with SELECTED_MANIFEST.open(
        newline="",
        encoding="utf-8",
    ) as f:
        rows = list(
            csv.DictReader(f)
        )

    ids = [
        row["item_id"]
        for row in rows
    ]

    if len(ids) != 500:
        raise RuntimeError(
            f"Expected 500 selected IDs, "
            f"got {len(ids)}."
        )

    if len(set(ids)) != 500:
        raise RuntimeError(
            "Duplicate IDs in frozen DEV500 manifest."
        )

    if not all(
        x.startswith("G6D-D-")
        for x in ids
    ):
        raise RuntimeError(
            "Non-DEV ID in selected manifest."
        )

    return ids


def validate_parent_freeze() -> None:
    if not COLLECTOR_FREEZE.exists():
        raise RuntimeError(
            "Frozen DEV500 collector implementation "
            "record missing."
        )

    actual = sha256_file(
        COLLECTOR_FREEZE
    )

    if actual != EXPECTED_COLLECTOR_FREEZE_SHA:
        raise RuntimeError(
            "DEV500 collector implementation "
            "freeze SHA mismatch."
        )


def selected_terminal_map(
    rows: list[dict],
    selected: set[str],
    source_name: str,
) -> tuple[dict[str, dict], int]:
    """
    Returns:
      selected-ID terminal map,
      count of historical/nonselected records.

    Duplicate selected terminal records are fail-closed.
    """
    selected_map = {}
    nonselected = 0

    for row in rows:
        item_id = row.get("item_id")

        if not isinstance(
            item_id,
            str,
        ):
            raise ValueError(
                f"{source_name}: terminal record "
                "without valid item_id."
            )

        if item_id not in selected:
            nonselected += 1
            continue

        if item_id in selected_map:
            raise ValueError(
                f"{source_name}: duplicate selected "
                f"terminal record for {item_id}"
            )

        selected_map[item_id] = row

    return (
        selected_map,
        nonselected,
    )


def terminal_validity(
    row: dict,
    *,
    source_name: str,
    item_id: str,
) -> bool:
    value = row.get("valid")

    if not isinstance(value, bool):
        raise ValueError(
            f"{source_name}: {item_id} has "
            "non-boolean valid field."
        )

    return value


def audit_records(
    *,
    selected_ids: list[str],
    sc5_rows: list[dict],
    vc_rows: list[dict],
) -> dict:
    selected = set(
        selected_ids
    )

    if len(selected_ids) != 500:
        raise ValueError(
            "Audit requires exactly 500 "
            "selected item IDs."
        )

    if len(selected) != 500:
        raise ValueError(
            "Selected IDs are not unique."
        )

    (
        sc5,
        nonselected_sc5,
    ) = selected_terminal_map(
        sc5_rows,
        selected,
        "sc5_terminal",
    )

    (
        vc,
        nonselected_vc,
    ) = selected_terminal_map(
        vc_rows,
        selected,
        "vc_terminal",
    )

    sc5_valid = 0
    sc5_invalid = 0
    vc_valid = 0
    vc_invalid = 0

    logical_complete = 0

    missing_sc5 = []
    missing_vc = []

    sc5_invalid_reasons = {}
    vc_invalid_reasons = {}

    # A selected VC may never precede/exist without
    # a selected SC5 terminal.
    orphan_vc = sorted(
        set(vc)
        - set(sc5)
    )

    if orphan_vc:
        raise ValueError(
            "VC terminal exists without selected "
            "SC5 terminal: "
            + ", ".join(
                orphan_vc[:5]
            )
        )

    for item_id in selected_ids:
        if item_id not in sc5:
            missing_sc5.append(
                item_id
            )
            continue

        s = sc5[item_id]

        s_valid = terminal_validity(
            s,
            source_name="sc5_terminal",
            item_id=item_id,
        )

        if not s_valid:
            sc5_invalid += 1

            reason = (
                s.get("invalid_reason")
                or "UNKNOWN_INVALID"
            )

            sc5_invalid_reasons[
                reason
            ] = (
                sc5_invalid_reasons.get(
                    reason,
                    0,
                )
                + 1
            )

            # Frozen collection semantics:
            # VC must not be generated after a
            # terminal-invalid SC5 record.
            if item_id in vc:
                raise ValueError(
                    f"{item_id}: VC terminal exists "
                    "after terminal-invalid SC5."
                )

            logical_complete += 1
            continue

        sc5_valid += 1

        if item_id not in vc:
            missing_vc.append(
                item_id
            )
            continue

        v = vc[item_id]

        v_valid = terminal_validity(
            v,
            source_name="vc_terminal",
            item_id=item_id,
        )

        if v_valid:
            vc_valid += 1
        else:
            vc_invalid += 1

            reason = (
                v.get("invalid_reason")
                or "UNKNOWN_INVALID"
            )

            vc_invalid_reasons[
                reason
            ] = (
                vc_invalid_reasons.get(
                    reason,
                    0,
                )
                + 1
            )

        # Valid or terminal-invalid VC both resolve
        # the logical item after valid SC5.
        logical_complete += 1

    selected_sc5_terminal = len(
        sc5
    )

    selected_vc_terminal = len(
        vc
    )

    remaining = (
        500 - logical_complete
    )

    status = (
        "COMPLETE"
        if logical_complete == 500
        else "INCOMPLETE"
    )

    return {
        "status": status,
        "selected_target": 500,
        "selected_dev_complete":
            logical_complete,
        "selected_dev_remaining":
            remaining,

        "selected_sc5_terminal":
            selected_sc5_terminal,
        "selected_sc5_valid":
            sc5_valid,
        "selected_sc5_invalid":
            sc5_invalid,

        "selected_vc_terminal":
            selected_vc_terminal,
        "selected_vc_valid":
            vc_valid,
        "selected_vc_invalid":
            vc_invalid,

        "missing_sc5_terminal_count":
            len(missing_sc5),
        "missing_sc5_terminal_sample":
            missing_sc5[:10],

        "missing_vc_after_valid_sc5_count":
            len(missing_vc),
        "missing_vc_after_valid_sc5_sample":
            missing_vc[:10],

        "sc5_invalid_reasons":
            dict(sorted(
                sc5_invalid_reasons.items()
            )),
        "vc_invalid_reasons":
            dict(sorted(
                vc_invalid_reasons.items()
            )),

        "historical_nonselected_sc5_records":
            nonselected_sc5,
        "historical_nonselected_vc_records":
            nonselected_vc,

        "correctness_inspected": False,
        "ground_truth_accessed": False,
        "calibration_metrics_computed":
            False,
        "calibration_eval_accessed":
            False,
        "external_test_accessed":
            False,
        "model_calls": 0,
    }


def current_audit() -> dict:
    validate_parent_freeze()

    selected_ids = (
        selected_ids_from_manifest()
    )

    sc5_rows = load_jsonl(
        SC5_PATH
    )

    vc_rows = load_jsonl(
        VC_PATH
    )

    result = audit_records(
        selected_ids=selected_ids,
        sc5_rows=sc5_rows,
        vc_rows=vc_rows,
    )

    result.update({
        "artifact":
            "GATE6D_DEV500_COLLECTION_AUDIT_V1",
        "audit_utc":
            utcnow(),
        "selected_manifest": {
            "path":
                str(SELECTED_MANIFEST),
            "sha256":
                sha256_file(
                    SELECTED_MANIFEST
                ),
        },
        "collector_implementation_freeze": {
            "path":
                str(COLLECTOR_FREEZE),
            "sha256":
                sha256_file(
                    COLLECTOR_FREEZE
                ),
        },
        "collection_files": {
            "sc5_terminal":
                file_info(SC5_PATH),
            "vc_terminal":
                file_info(VC_PATH),
            "raw_attempts":
                file_info(RAW_PATH),
            "session_events":
                file_info(EVENTS_PATH),
        },
    })

    return result


def synthetic_fixture(
    *,
    complete: bool,
) -> tuple[
    list[str],
    list[dict],
    list[dict],
]:
    ids = [
        f"G6D-D-{i:04d}"
        for i in range(1, 501)
    ]

    sc5 = []
    vc = []

    # 10 terminal-invalid SC5 items.
    sc5_invalid = set(
        ids[0:10]
    )

    # 7 terminal-invalid VC items among
    # otherwise-valid SC5.
    vc_invalid = set(
        ids[100:107]
    )

    for item_id in ids:
        if item_id in sc5_invalid:
            sc5.append({
                "item_id": item_id,
                "valid": False,
                "invalid_reason":
                    "SYN_SC5_INVALID",
            })
            continue

        sc5.append({
            "item_id": item_id,
            "valid": True,
            "invalid_reason": None,
        })

        vc.append({
            "item_id": item_id,
            "valid":
                item_id not in vc_invalid,
            "invalid_reason": (
                "SYN_VC_INVALID"
                if item_id in vc_invalid
                else None
            ),
        })

    # Historical/nonselected provenance.
    sc5.append({
        "item_id": "G6D-D-0999",
        "valid": True,
        "invalid_reason": None,
    })

    vc.append({
        "item_id": "G6D-D-0999",
        "valid": True,
        "invalid_reason": None,
    })

    if not complete:
        # Remove VC for one valid SC5 item,
        # making logical completion 499.
        vc = [
            row
            for row in vc
            if row["item_id"]
            != "G6D-D-0500"
        ]

    return ids, sc5, vc


def expect_failure(
    name,
    ids,
    sc5,
    vc,
    expected_text,
) -> dict:
    try:
        audit_records(
            selected_ids=ids,
            sc5_rows=sc5,
            vc_rows=vc,
        )
    except Exception as exc:
        text = str(exc)

        if expected_text not in text:
            raise AssertionError(
                f"{name}: wrong failure: "
                f"{text}"
            )

        return {
            "test": name,
            "status": "PASS",
            "failure_detected": text,
        }

    raise AssertionError(
        f"{name}: expected failure "
        "was not detected."
    )


def synthetic_self_test() -> dict:
    ids, sc5, vc = synthetic_fixture(
        complete=True
    )

    complete = audit_records(
        selected_ids=ids,
        sc5_rows=sc5,
        vc_rows=vc,
    )

    assert complete[
        "status"
    ] == "COMPLETE"

    assert complete[
        "selected_dev_complete"
    ] == 500

    assert complete[
        "selected_dev_remaining"
    ] == 0

    assert complete[
        "selected_sc5_terminal"
    ] == 500

    assert complete[
        "selected_sc5_valid"
    ] == 490

    assert complete[
        "selected_sc5_invalid"
    ] == 10

    assert complete[
        "selected_vc_terminal"
    ] == 490

    assert complete[
        "selected_vc_valid"
    ] == 483

    assert complete[
        "selected_vc_invalid"
    ] == 7

    assert complete[
        "historical_nonselected_sc5_records"
    ] == 1

    assert complete[
        "historical_nonselected_vc_records"
    ] == 1

    ids2, sc52, vc2 = synthetic_fixture(
        complete=False
    )

    incomplete = audit_records(
        selected_ids=ids2,
        sc5_rows=sc52,
        vc_rows=vc2,
    )

    assert incomplete[
        "status"
    ] == "INCOMPLETE"

    assert incomplete[
        "selected_dev_complete"
    ] == 499

    assert incomplete[
        "selected_dev_remaining"
    ] == 1

    # Duplicate selected SC5 terminal:
    ids3, sc53, vc3 = synthetic_fixture(
        complete=True
    )

    sc53.append(
        dict(sc53[20])
    )

    duplicate_test = expect_failure(
        "duplicate_selected_sc5",
        ids3,
        sc53,
        vc3,
        "duplicate selected terminal record",
    )

    # VC after terminal-invalid SC5:
    ids4, sc54, vc4 = synthetic_fixture(
        complete=True
    )

    vc4.append({
        "item_id": "G6D-D-0001",
        "valid": True,
        "invalid_reason": None,
    })

    invalid_sc5_vc_test = expect_failure(
        "vc_after_invalid_sc5",
        ids4,
        sc54,
        vc4,
        "after terminal-invalid SC5",
    )

    # VC with no SC5 at all:
    ids5, sc55, vc5 = synthetic_fixture(
        complete=True
    )

    sc55 = [
        row
        for row in sc55
        if row["item_id"]
        != "G6D-D-0020"
    ]

    orphan_vc_test = expect_failure(
        "vc_without_sc5_terminal",
        ids5,
        sc55,
        vc5,
        "VC terminal exists without selected "
        "SC5 terminal",
    )

    return {
        "artifact":
            "GATE6D_DEV500_COLLECTION_AUDIT_"
            "SYNTHETIC_SELF_TEST_V1",
        "status": "PASS",
        "complete_fixture": {
            "selected_dev_complete": 500,
            "selected_sc5_valid": 490,
            "selected_sc5_invalid": 10,
            "selected_vc_valid": 483,
            "selected_vc_invalid": 7,
        },
        "incomplete_fixture": {
            "selected_dev_complete": 499,
            "selected_dev_remaining": 1,
            "status": "INCOMPLETE",
        },
        "fail_closed_tests": [
            duplicate_test,
            invalid_sc5_vc_test,
            orphan_vc_test,
        ],
        "correctness_inspected": False,
        "ground_truth_accessed": False,
        "calibration_metrics_computed":
            False,
        "calibration_eval_accessed":
            False,
        "external_test_accessed":
            False,
        "model_calls": 0,
    }


def write_json(
    path: Path,
    obj: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            obj,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def print_summary(
    result: dict,
) -> None:
    print(
        "Status:",
        result["status"],
    )

    print(
        "Selected complete:",
        f"{result['selected_dev_complete']}/500",
    )

    print(
        "Selected remaining:",
        result["selected_dev_remaining"],
    )

    print(
        "Selected SC5 terminal:",
        result["selected_sc5_terminal"],
    )

    print(
        "Selected SC5 valid:",
        result["selected_sc5_valid"],
    )

    print(
        "Selected SC5 invalid:",
        result["selected_sc5_invalid"],
    )

    print(
        "Selected VC terminal:",
        result["selected_vc_terminal"],
    )

    print(
        "Selected VC valid:",
        result["selected_vc_valid"],
    )

    print(
        "Selected VC invalid:",
        result["selected_vc_invalid"],
    )

    print(
        "Historical nonselected SC5:",
        result[
            "historical_nonselected_sc5_records"
        ],
    )

    print(
        "Historical nonselected VC:",
        result[
            "historical_nonselected_vc_records"
        ],
    )

    print()
    print("Correctness inspected: NO")
    print("Ground truth accessed: NO")
    print("Calibration metrics computed: NO")
    print("Calibration-EVAL accessed: NO")
    print("External-TEST accessed: NO")
    print("Model calls: 0")


def freeze_complete() -> None:
    result = current_audit()

    print(
        "=== GATE 6D DEV500 "
        "COLLECTION-COMPLETE FREEZE ==="
    )

    print_summary(result)

    if os.environ.get(
        FREEZE_ENV
    ) != "YES":
        print()
        print(
            "FREEZE BLOCKED: explicit environment "
            f"gate {FREEZE_ENV}=YES is absent."
        )
        return

    if result["status"] != "COMPLETE":
        print()
        print(
            "FREEZE BLOCKED: DEV500 collection "
            "is not complete."
        )
        return

    if result[
        "selected_dev_complete"
    ] != 500:
        print()
        print(
            "FREEZE BLOCKED: logical-complete "
            "count is not 500."
        )
        return

    freeze = {
        "artifact":
            "GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1",
        "status":
            "FROZEN_COMPLETE",
        "frozen_utc":
            utcnow(),
        "selected_dev_complete":
            500,
        "selected_dev_target":
            500,
        "selected_dev_remaining":
            0,
        "audit_summary": {
            key: value
            for key, value
            in result.items()
            if key not in {
                "artifact",
                "audit_utc",
                "selected_manifest",
                "collector_implementation_freeze",
                "collection_files",
            }
        },
        "selected_manifest":
            result["selected_manifest"],
        "collector_implementation_freeze":
            result[
                "collector_implementation_freeze"
            ],
        "collection_files":
            result["collection_files"],
        "audit_tool": {
            "path":
                "scripts/gate6/"
                "audit_gate6d_dev500_collection_v1.py",
            "sha256":
                sha256_file(
                    Path(__file__)
                ),
        },
        "analysis_unlock": {
            "real_dev_metadata_gate":
                "SATISFIED",
            "correctness_analysis_performed":
                False,
            "note":
                "This artifact permits the separately "
                "frozen real-DEV analysis workflow to "
                "proceed; it contains no correctness "
                "or calibration results."
        },
        "safety_state": {
            "correctness_inspected":
                False,
            "ground_truth_accessed":
                False,
            "calibration_metrics_computed":
                False,
            "calibration_eval_accessed":
                False,
            "external_test_accessed":
                False,
            "model_calls":
                0,
        },
    }

    write_json(
        COMPLETE_FREEZE,
        freeze,
    )

    print()
    print(
        "FROZEN_COMPLETE artifact written:"
    )
    print(COMPLETE_FREEZE)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    parser.add_argument(
        "--audit-current",
        action="store_true",
    )

    parser.add_argument(
        "--freeze-complete",
        action="store_true",
    )

    args = parser.parse_args()

    modes = sum([
        args.self_test,
        args.audit_current,
        args.freeze_complete,
    ])

    if modes != 1:
        print(
            "BLOCKED: choose exactly one of "
            "--self-test, --audit-current, "
            "or --freeze-complete."
        )
        return

    if args.self_test:
        result = synthetic_self_test()

        write_json(
            SYNTHETIC_AUDIT,
            result,
        )

        print(
            "=== GATE 6D DEV500 COLLECTION "
            "AUDIT SYNTHETIC TEST ==="
        )

        print(
            "SELF-TEST:",
            result["status"],
        )

        print(
            "Complete fixture:",
            result[
                "complete_fixture"
            ]["selected_dev_complete"],
            "/500",
        )

        print(
            "Incomplete fixture:",
            result[
                "incomplete_fixture"
            ]["selected_dev_complete"],
            "/500",
        )

        print(
            "Fail-closed tests:",
            len(
                result[
                    "fail_closed_tests"
                ]
            ),
            "PASS",
        )

        print()
        print("Correctness inspected: NO")
        print("Ground truth accessed: NO")
        print("Calibration metrics computed: NO")
        print("Calibration-EVAL accessed: NO")
        print("External-TEST accessed: NO")
        print("Model calls: 0")
        return

    if args.audit_current:
        result = current_audit()

        write_json(
            CURRENT_AUDIT,
            result,
        )

        print(
            "=== GATE 6D DEV500 "
            "CURRENT COLLECTION AUDIT ==="
        )

        print_summary(result)

        print()
        print(
            "Audit artifact:",
            CURRENT_AUDIT,
        )
        return

    freeze_complete()


if __name__ == "__main__":
    main()
