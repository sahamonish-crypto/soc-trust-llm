#!/usr/bin/env python3

"""Gate 6D real-capable EVAL collection executor V1 (working copy).

Prospective only. Real collection is not implemented yet.
Metadata-only preflight must not open sealed EVAL inputs, manifest, or GT.
"""

from __future__ import annotations

import argparse
import csv
import json
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import time

EVAL_EXECUTOR = Path(
    "scripts/gate6/gate6d_eval_collection_executor_v1.py"
)

BOUNDARY = Path("scripts/gate6/gate6d_eval_collection_gate_v2.py")
BOUNDARY_FREEZE = Path(
    "benchmarks/gate6d/GATE6D_EVAL_COLLECTION_GATE_FREEZE_V2.json"
)
DEV_COLLECTOR = Path(
    "scripts/gate6/run_gate6d_dev_uncertainty_collection_v1_2.py"
)
EVAL_COLLECTION_FREEZE = Path(
    "benchmarks/gate6d/GATE6D_EVAL_COLLECTION_FREEZE_V1.json"
)


DEV_METHOD_FREEZE = Path(
    "benchmarks/gate6d/GATE6D_DEV_METHOD_FREEZE_V1.json"
)


DEV_COMMIT_MARKER = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV_OOF_PREDICTIONS_FREEZE_V1.json"
)

EVAL_SAFEGUARD = Path(
    "benchmarks/gate6d/"
    "GATE6D_EVAL_EXECUTION_SAFEGUARD_PROTOCOL_V1.json"
)

VC_SYSTEM_PROMPT = Path(
    "benchmarks/gate6d/collector_v1_2/"
    "vc_self_eval_system_prompt.txt"
)

EXPECTED_EVAL_SAFEGUARD_SHA = (
    "48f187e146510a578fac405fc06d8b39"
    "b5159b57c1433889e276e40f380d7c0e"
)

EXPECTED_VC_SYSTEM_PROMPT_SHA = (
    "51bb3bb0912123a315dba5c34cb08bed"
    "103f2a6b51795febbe2125e31cb47f2d"
)

EVAL_OUTPUT_DIR = Path(
    "benchmarks/gate6d/eval_collection_real_v1"
)

EVAL_RAW_ATTEMPTS = (
    EVAL_OUTPUT_DIR / "raw_attempts.jsonl"
)

EVAL_SESSION_EVENTS = (
    EVAL_OUTPUT_DIR / "session_events.jsonl"
)

EVAL_SC5_TERMINAL = (
    EVAL_OUTPUT_DIR / "sc5_terminal.jsonl"
)

EVAL_VC_TERMINAL = (
    EVAL_OUTPUT_DIR / "vc_terminal.jsonl"
)


SEALED_EVAL_INPUTS = Path(
    "benchmarks/gate6d/canonical_v1/"
    "sealed_eval_model_inputs.jsonl"
)

SEALED_EVAL_MANIFEST = Path(
    "benchmarks/gate6d/canonical_v1/"
    "sealed_eval_manifest.csv"
)


SEALED_EVAL_GT = Path(
    "benchmarks/gate6d/canonical_v1/hidden/"
    "eval_ground_truth.jsonl"
)

EXPECTED_EVAL_GT_SHA = (
    "9ffb438d26a7f0b1e9d981998c66edab"
    "1c96a1348a90db0eb5769bc674e6ed55"
)

EXPECTED_EVAL_INPUT_SHA = (
    "ba9870fcb9223fb3acc46e87a24b6f8"
    "c490171b79cc49c08fc433bd7d4ef8d9c"
)

EXPECTED_EVAL_MANIFEST_SHA = (
    "084501099471ec1b5289cd99e44305e9"
    "c824bea62676f389b8d13485544636a7"
)

EXPECTED_EVAL_ITEMS = 458
EXPECTED_EVAL_CAPTURE = "Windows7AD-2023-02-22"

REAL_COLLECTION_ENV = "GATE6D_ALLOW_REAL_EVAL_COLLECTION"

EXPECTED_BOUNDARY_SHA = (
    "d666300f059ee6052461982cb3c7f412"
    "e0b41c079a363bf65499a902462f05cf"
)
EXPECTED_BOUNDARY_FREEZE_SHA = (
    "ee715f8798b3308a654ddc7fd39ef7b"
    "ac6b496ca48d5e6bc2450566fb05f96f9"
)
EXPECTED_DEV_COLLECTOR_SHA = (
    "25da7632efd3fc49352652c08ce8deed8"
    "f09f00d6c16334e56e7d4de2568ac99"
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
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


def verify_frozen_dependencies() -> dict:
    expected = {
        BOUNDARY: EXPECTED_BOUNDARY_SHA,
        BOUNDARY_FREEZE:
            EXPECTED_BOUNDARY_FREEZE_SHA,
        DEV_COLLECTOR:
            EXPECTED_DEV_COLLECTOR_SHA,
    }

    out = {}

    for path, wanted in expected.items():
        if not path.exists():
            raise RuntimeError(
                "Frozen dependency missing: "
                + str(path)
            )

        actual = sha256_file(path)

        if actual != wanted:
            raise RuntimeError(
                "Frozen dependency SHA mismatch: "
                + str(path)
            )

        out[str(path)] = actual

    return out


def executor_preflight() -> dict:
    frozen = verify_frozen_dependencies()

    boundary = load_module(
        BOUNDARY,
        "gate6d_eval_boundary_v2_executor",
    )

    collection_gate = boundary.current_real_gate()

    extra_env = (
        os.getenv(REAL_COLLECTION_ENV)
        == "YES"
    )

    freeze_exists = (
        EVAL_COLLECTION_FREEZE.exists()
    )

    reasons = list(
        collection_gate["reasons"]
    )

    if not extra_env:
        reasons.append(
            REAL_COLLECTION_ENV
            + " is not YES"
        )

    if freeze_exists:
        reasons.append(
            "EVAL collection freeze already exists"
        )

    ready = (
        collection_gate["allowed"]
        and extra_env
        and not freeze_exists
    )

    return {
        "ready": ready,
        "frozen_dependencies": frozen,
        "boundary_collection_gate_allowed":
            collection_gate["allowed"],
        "real_collection_env_allowed":
            extra_env,
        "collection_freeze_exists":
            freeze_exists,
        "reasons": reasons,
    }


def load_frozen_dev_collector():
    if (
        sha256_file(DEV_COLLECTOR)
        != EXPECTED_DEV_COLLECTOR_SHA
    ):
        raise RuntimeError(
            "Frozen DEV collector SHA mismatch."
        )

    return load_module(
        DEV_COLLECTOR,
        "gate6d_dev_collector_for_eval",
    )


def eval_request_with_retry(
    stage: str,
    item_id: str,
    payload: dict,
    *,
    network_fn=None,
    sleep_fn=None,
    raw_path: Path = EVAL_RAW_ATTEMPTS,
    events_path: Path = EVAL_SESSION_EVENTS,
) -> tuple:
    collector = load_frozen_dev_collector()

    if network_fn is None:
        network_fn = collector.cloudflare_call

    if sleep_fn is None:
        sleep_fn = time.sleep

    for attempt in range(
        1,
        collector.MAX_TRANSPORT_ATTEMPTS_PER_SESSION + 1,
    ):
        started_utc = collector.utcnow()

        response = network_fn(payload)

        raw_body = (
            response.get("raw_body")
            or ""
        )

        collector.append_jsonl(
            raw_path,
            {
                "stage": stage,
                "item_id": item_id,
                "attempt_in_session": attempt,
                "request_started_utc": started_utc,
                "http_status":
                    response.get("http_status"),
                "retry_after":
                    response.get("retry_after"),
                "latency_ms":
                    response.get("latency_ms"),
                "transport_error":
                    response.get("transport_error"),
                "raw_response_sha256":
                    collector.sha256_bytes(
                        raw_body.encode("utf-8")
                    ),
                "raw_body": raw_body,
            },
        )

        if collector.cloudflare_daily_quota_exhausted(
            response
        ):
            collector.append_jsonl(
                events_path,
                {
                    "event_type":
                        "CLOUDFLARE_DAILY_QUOTA_PAUSE",
                    "stage": stage,
                    "item_id": item_id,
                    "detected_utc":
                        collector.utcnow(),
                    "logical_attempt_consumed":
                        False,
                    "logical_item_resolved":
                        False,
                },
            )

            return (
                "QUOTA_PAUSE",
                response,
            )

        if collector.retryable_transport(
            response
        ):
            if (
                attempt
                == collector.MAX_TRANSPORT_ATTEMPTS_PER_SESSION
            ):
                collector.append_jsonl(
                    events_path,
                    {
                        "event_type":
                            "INFRASTRUCTURE_RETRY_LIMIT_PAUSE",
                        "stage": stage,
                        "item_id": item_id,
                        "detected_utc":
                            collector.utcnow(),
                        "logical_item_resolved":
                            False,
                    },
                )

                return (
                    "INFRASTRUCTURE_PAUSE",
                    response,
                )

            retry_after = response.get(
                "retry_after"
            )

            fallback = collector.BACKOFF_SECONDS[
                min(
                    attempt - 1,
                    len(collector.BACKOFF_SECONDS) - 1,
                )
            ]

            delay = (
                retry_after
                if retry_after is not None
                else fallback
            )

            sleep_fn(
                max(0, float(delay))
            )

            continue

        return (
            "RESPONSE",
            response,
        )

    raise RuntimeError(
        "Unreachable retry state."
    )


def synthetic_transport_self_test() -> dict:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw = root / "raw.jsonl"
        events = root / "events.jsonl"

        calls = []

        def ok(_payload):
            calls.append("ok")
            return {
                "http_status": 200,
                "body": {"success": True},
                "raw_body": "{\"success\":true}",
                "retry_after": None,
                "latency_ms": 1,
                "transport_error": "",
            }

        status, _ = eval_request_with_retry(
            "SC5_MAJORITY",
            "G6D-E-0001",
            {"synthetic": True},
            network_fn=ok,
            sleep_fn=lambda _x: None,
            raw_path=raw,
            events_path=events,
        )

        if status != "RESPONSE":
            raise RuntimeError(
                "Synthetic success response failed."
            )

        quota_raw = root / "quota_raw.jsonl"
        quota_events = root / "quota_events.jsonl"

        def quota(_payload):
            return {
                "http_status": 429,
                "body": {
                    "errors": [
                        {"code": 3036}
                    ]
                },
                "raw_body": "daily free allocation neurons",
                "retry_after": None,
                "latency_ms": 1,
                "transport_error": "",
            }

        quota_status, _ = eval_request_with_retry(
            "SC5_MAJORITY",
            "G6D-E-0002",
            {"synthetic": True},
            network_fn=quota,
            sleep_fn=lambda _x: None,
            raw_path=quota_raw,
            events_path=quota_events,
        )

        retry_raw = root / "retry_raw.jsonl"
        retry_events = root / "retry_events.jsonl"
        sequence = [
            {
                "http_status": 500,
                "body": {},
                "raw_body": "retry",
                "retry_after": None,
                "latency_ms": 1,
                "transport_error": "",
            },
            {
                "http_status": 200,
                "body": {"success": True},
                "raw_body": "ok",
                "retry_after": None,
                "latency_ms": 1,
                "transport_error": "",
            },
        ]

        sleeps = []

        def retry(_payload):
            return sequence.pop(0)

        retry_status, _ = eval_request_with_retry(
            "VC_SELF_EVAL",
            "G6D-E-0003",
            {"synthetic": True},
            network_fn=retry,
            sleep_fn=lambda x: sleeps.append(x),
            raw_path=retry_raw,
            events_path=retry_events,
        )

        if quota_status != "QUOTA_PAUSE":
            raise RuntimeError(
                "Synthetic quota pause failed."
            )

        if retry_status != "RESPONSE":
            raise RuntimeError(
                "Synthetic retry recovery failed."
            )

        raw_lines = raw.read_text().strip().splitlines()
        quota_event_lines = (
            quota_events.read_text().strip().splitlines()
        )
        retry_lines = (
            retry_raw.read_text().strip().splitlines()
        )

        if len(raw_lines) != 1:
            raise RuntimeError(
                "Synthetic raw-attempt count mismatch."
            )

        if len(quota_event_lines) != 1:
            raise RuntimeError(
                "Synthetic quota-event count mismatch."
            )

        if len(retry_lines) != 2:
            raise RuntimeError(
                "Synthetic retry-attempt count mismatch."
            )

        if len(sleeps) != 1:
            raise RuntimeError(
                "Synthetic retry sleep count mismatch."
            )

        return {
            "status": "PASS",
            "success_status": status,
            "quota_status": quota_status,
            "retry_status": retry_status,
            "success_raw_attempts": len(raw_lines),
            "quota_events": len(quota_event_lines),
            "retry_raw_attempts": len(retry_lines),
            "retry_sleeps": len(sleeps),
            "real_model_calls": 0,
            "sealed_eval_model_inputs_opened": False,
            "sealed_eval_manifest_opened": False,
            "sealed_eval_ground_truth_opened": False,
            "gate7_opened": False,
        }


def collection_plan_from_method_freeze(
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
        selected = (
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
    except Exception as exc:
        raise RuntimeError(
            "Malformed DEV method freeze."
        ) from exc

    if selected != refit_estimator:
        raise RuntimeError(
            "DEV winner-estimator binding mismatch."
        )

    if selected == "SC5_AGREEMENT":
        return {
            "selected_estimator": selected,
            "attempt_sc5_for_all_items": True,
            "attempt_vc_after_valid_sc5": False,
            "required_eval_items": EXPECTED_EVAL_ITEMS,
        }

    if selected == "VC_SELF_EVAL":
        return {
            "selected_estimator": selected,
            "attempt_sc5_for_all_items": True,
            "attempt_vc_after_valid_sc5": True,
            "required_eval_items": EXPECTED_EVAL_ITEMS,
        }

    raise RuntimeError(
        "Unknown selected estimator: "
        + repr(selected)
    )


def load_terminal_map_strict(
    path: Path,
) -> dict:
    if not path.exists():
        return {}

    collector = load_frozen_dev_collector()

    rows = collector.load_jsonl(path)

    out = {}

    for row in rows:
        item_id = row.get("item_id")

        if not isinstance(item_id, str):
            raise RuntimeError(
                "Terminal record missing item_id."
            )

        if item_id in out:
            raise RuntimeError(
                "Duplicate terminal item_id: "
                + item_id
            )

        out[item_id] = row

    return out


def synthetic_collection_plan_self_test() -> dict:
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
        },
    }

    sc5 = collection_plan_from_method_freeze(
        base
    )

    vc_obj = json.loads(
        json.dumps(base)
    )

    vc_obj[
        "primary_comparison"
    ][
        "selection"
    ][
        "winner_estimator"
    ] = "VC_SELF_EVAL"

    vc_obj[
        "post_selection_refit"
    ][
        "estimator"
    ] = "VC_SELF_EVAL"

    vc = collection_plan_from_method_freeze(
        vc_obj
    )

    if sc5["attempt_vc_after_valid_sc5"]:
        raise RuntimeError(
            "SC5 plan unexpectedly requires VC."
        )

    if not vc["attempt_vc_after_valid_sc5"]:
        raise RuntimeError(
            "VC plan failed to require VC."
        )

    blocked = 0

    cases = []

    bad = json.loads(json.dumps(base))
    bad["status"] = "WRONG"
    cases.append(bad)

    bad = json.loads(json.dumps(base))
    bad["artifact"] = "WRONG"
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
    bad[
        "post_selection_refit"
    ][
        "estimator"
    ] = "UNKNOWN"
    cases.append(bad)

    for obj in cases:
        try:
            collection_plan_from_method_freeze(
                obj
            )
        except RuntimeError:
            blocked += 1
        else:
            raise RuntimeError(
                "Fail-closed method-freeze test passed."
            )

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "terminal.jsonl"

        collector = load_frozen_dev_collector()

        collector.append_jsonl(
            path,
            {
                "item_id": "G6D-E-0001",
                "valid": True,
            },
        )

        one = load_terminal_map_strict(
            path
        )

        if len(one) != 1:
            raise RuntimeError(
                "Terminal map load mismatch."
            )

        collector.append_jsonl(
            path,
            {
                "item_id": "G6D-E-0001",
                "valid": False,
            },
        )

        duplicate_blocked = False

        try:
            load_terminal_map_strict(
                path
            )
        except RuntimeError:
            duplicate_blocked = True

        if not duplicate_blocked:
            raise RuntimeError(
                "Duplicate terminal ID was accepted."
            )

    return {
        "status": "PASS",
        "sc5_selected_estimator":
            sc5["selected_estimator"],
        "sc5_requires_vc":
            sc5["attempt_vc_after_valid_sc5"],
        "vc_selected_estimator":
            vc["selected_estimator"],
        "vc_requires_vc":
            vc["attempt_vc_after_valid_sc5"],
        "method_freeze_fail_closed_tests":
            blocked,
        "duplicate_terminal_blocked":
            duplicate_blocked,
        "real_model_calls": 0,
        "sealed_eval_model_inputs_opened": False,
        "sealed_eval_manifest_opened": False,
        "sealed_eval_ground_truth_opened": False,
        "gate7_opened": False,
    }


def item_collection_action(
    plan: dict,
    item_id: str,
    sc5_done: dict,
    vc_done: dict,
) -> str:
    if item_id not in sc5_done:
        if item_id in vc_done:
            raise RuntimeError(
                "VC terminal exists without SC5 terminal: "
                + item_id
            )

        return "SC5"

    sc5 = sc5_done[item_id]

    if sc5.get("item_id") != item_id:
        raise RuntimeError(
            "SC5 terminal item binding mismatch."
        )

    if not isinstance(sc5.get("valid"), bool):
        raise RuntimeError(
            "SC5 terminal validity is not boolean."
        )

    if not sc5["valid"]:
        if item_id in vc_done:
            raise RuntimeError(
                "VC terminal exists after invalid SC5: "
                + item_id
            )

        # Frozen policy: semantic-invalid SC5 is terminal.
        return "DONE"

    if not plan["attempt_vc_after_valid_sc5"]:
        if item_id in vc_done:
            raise RuntimeError(
                "Unexpected VC terminal for SC5-selected EVAL: "
                + item_id
            )

        return "DONE"

    if item_id not in vc_done:
        return "VC"

    vc = vc_done[item_id]

    if vc.get("item_id") != item_id:
        raise RuntimeError(
            "VC terminal item binding mismatch."
        )

    if not isinstance(vc.get("valid"), bool):
        raise RuntimeError(
            "VC terminal validity is not boolean."
        )

    # Frozen policy: valid or semantic-invalid VC is terminal.
    return "DONE"


def synthetic_item_state_machine_self_test() -> dict:
    sc5_plan = {
        "selected_estimator": "SC5_AGREEMENT",
        "attempt_sc5_for_all_items": True,
        "attempt_vc_after_valid_sc5": False,
        "required_eval_items": EXPECTED_EVAL_ITEMS,
    }

    vc_plan = {
        "selected_estimator": "VC_SELF_EVAL",
        "attempt_sc5_for_all_items": True,
        "attempt_vc_after_valid_sc5": True,
        "required_eval_items": EXPECTED_EVAL_ITEMS,
    }

    item = "G6D-E-0001"

    if item_collection_action(
        sc5_plan, item, {}, {}
    ) != "SC5":
        raise RuntimeError(
            "Empty SC5 state did not request SC5."
        )

    valid_sc5 = {
        item: {
            "item_id": item,
            "valid": True,
        }
    }

    invalid_sc5 = {
        item: {
            "item_id": item,
            "valid": False,
        }
    }

    if item_collection_action(
        sc5_plan,
        item,
        valid_sc5,
        {},
    ) != "DONE":
        raise RuntimeError(
            "SC5 winner requested unnecessary VC."
        )

    if item_collection_action(
        sc5_plan,
        item,
        invalid_sc5,
        {},
    ) != "DONE":
        raise RuntimeError(
            "Invalid SC5 was regenerated."
        )

    if item_collection_action(
        vc_plan,
        item,
        valid_sc5,
        {},
    ) != "VC":
        raise RuntimeError(
            "VC winner did not request VC after valid SC5."
        )

    valid_vc = {
        item: {
            "item_id": item,
            "valid": True,
        }
    }

    invalid_vc = {
        item: {
            "item_id": item,
            "valid": False,
        }
    }

    if item_collection_action(
        vc_plan,
        item,
        valid_sc5,
        valid_vc,
    ) != "DONE":
        raise RuntimeError(
            "Valid VC did not terminate item."
        )

    if item_collection_action(
        vc_plan,
        item,
        valid_sc5,
        invalid_vc,
    ) != "DONE":
        raise RuntimeError(
            "Semantic-invalid VC was regenerated."
        )

    fail_closed = 0

    impossible = [
        (
            vc_plan,
            {},
            valid_vc,
        ),
        (
            vc_plan,
            invalid_sc5,
            valid_vc,
        ),
        (
            sc5_plan,
            valid_sc5,
            valid_vc,
        ),
        (
            vc_plan,
            {
                item: {
                    "item_id": "WRONG",
                    "valid": True,
                }
            },
            {},
        ),
        (
            vc_plan,
            {
                item: {
                    "item_id": item,
                    "valid": "true",
                }
            },
            {},
        ),
    ]

    for plan, sc5, vc in impossible:
        try:
            item_collection_action(
                plan,
                item,
                sc5,
                vc,
            )
        except RuntimeError:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Impossible terminal state was accepted."
            )

    return {
        "status": "PASS",
        "empty_state_action": "SC5",
        "sc5_winner_valid_action": "DONE",
        "sc5_invalid_action": "DONE",
        "vc_winner_after_valid_sc5_action": "VC",
        "vc_valid_action": "DONE",
        "vc_semantic_invalid_action": "DONE",
        "fail_closed_tests": fail_closed,
        "semantic_invalid_regeneration": False,
        "real_model_calls": 0,
        "sealed_eval_model_inputs_opened": False,
        "sealed_eval_manifest_opened": False,
        "sealed_eval_ground_truth_opened": False,
        "gate7_opened": False,
    }


def eval_seed(item_id: str) -> int:
    digest = hashlib.sha256(
        ("GATE6D_SC5_V1|" + item_id).encode("utf-8")
    ).digest()

    value = int.from_bytes(
        digest[:4],
        "big",
        signed=False,
    ) & 0x7FFFFFFF

    return value if value != 0 else 1


def validate_eval_records(
    inputs: list,
    manifest: list,
) -> dict:
    if len(inputs) != EXPECTED_EVAL_ITEMS:
        raise RuntimeError(
            "EVAL model-input count mismatch."
        )

    if len(manifest) != EXPECTED_EVAL_ITEMS:
        raise RuntimeError(
            "EVAL manifest count mismatch."
        )

    expected_ids = [
        f"G6D-E-{i:04d}"
        for i in range(1, EXPECTED_EVAL_ITEMS + 1)
    ]

    input_ids = [
        x.get("item_id")
        for x in inputs
    ]

    manifest_ids = [
        x.get("item_id")
        for x in manifest
    ]

    if input_ids != expected_ids:
        raise RuntimeError(
            "EVAL model-input ID/order mismatch."
        )

    if manifest_ids != expected_ids:
        raise RuntimeError(
            "EVAL manifest ID/order mismatch."
        )

    expected_manifest_fields = {
        "item_id",
        "capture",
        "episode_start_utc",
        "community_id",
        "source_path",
        "sc5_seed",
        "evidence_hash",
    }

    for record, row in zip(inputs, manifest):
        if set(record) != {"item_id", "messages"}:
            raise RuntimeError(
                "Unexpected model-input schema."
            )

        messages = record["messages"]

        if (
            not isinstance(messages, list)
            or len(messages) != 2
            or messages[0].get("role") != "system"
            or messages[1].get("role") != "user"
        ):
            raise RuntimeError(
                "Unexpected EVAL message structure."
            )

        if set(row) != expected_manifest_fields:
            raise RuntimeError(
                "Unexpected EVAL manifest schema."
            )

        if row["capture"] != EXPECTED_EVAL_CAPTURE:
            raise RuntimeError(
                "Unexpected EVAL capture."
            )

        if int(row["sc5_seed"]) != eval_seed(row["item_id"]):
            raise RuntimeError(
                "Frozen EVAL seed mismatch."
            )

        if "ground_truth" in record:
            raise RuntimeError(
                "Ground truth leaked into model input."
            )

        if "ground_truth" in row:
            raise RuntimeError(
                "Ground truth leaked into manifest."
            )

    return {
        "status": "PASS",
        "items": EXPECTED_EVAL_ITEMS,
        "first_item_id": expected_ids[0],
        "last_item_id": expected_ids[-1],
        "capture": EXPECTED_EVAL_CAPTURE,
    }


def synthetic_eval_record_validation_self_test() -> dict:
    inputs = []
    manifest = []

    for i in range(1, EXPECTED_EVAL_ITEMS + 1):
        item_id = f"G6D-E-{i:04d}"

        inputs.append({
            "item_id": item_id,
            "messages": [
                {"role": "system", "content": "synthetic"},
                {"role": "user", "content": "synthetic"},
            ],
        })

        manifest.append({
            "item_id": item_id,
            "capture": EXPECTED_EVAL_CAPTURE,
            "episode_start_utc": "SYNTHETIC",
            "community_id": f"synthetic-{i}",
            "source_path": "SYNTHETIC",
            "sc5_seed": str(eval_seed(item_id)),
            "evidence_hash": "SYNTHETIC",
        })

    validate_eval_records(inputs, manifest)

    blocked = 0

    tests = []

    bad = [dict(x) for x in manifest]
    bad[0]["sc5_seed"] = "1"
    tests.append((inputs, bad))

    bad = [dict(x) for x in manifest]
    bad[0]["capture"] = "WRONG"
    tests.append((inputs, bad))

    bad_inputs = [dict(x) for x in inputs]
    bad_inputs[0]["ground_truth"] = "ESCALATE"
    tests.append((bad_inputs, manifest))

    bad = [dict(x) for x in manifest]
    bad[0]["ground_truth"] = "ESCALATE"
    tests.append((inputs, bad))

    bad_inputs = list(inputs)
    bad_inputs[0], bad_inputs[1] = (
        bad_inputs[1],
        bad_inputs[0],
    )
    tests.append((bad_inputs, manifest))

    for a, b in tests:
        try:
            validate_eval_records(a, b)
        except RuntimeError:
            blocked += 1
        else:
            raise RuntimeError(
                "Synthetic fail-closed test unexpectedly passed."
            )

    return {
        "status": "PASS",
        "valid_items": EXPECTED_EVAL_ITEMS,
        "fail_closed_tests": blocked,
        "sealed_eval_model_inputs_opened": False,
        "sealed_eval_manifest_opened": False,
        "sealed_eval_ground_truth_opened": False,
        "model_calls": 0,
        "gate7_opened": False,
    }


def run_eval_collection_session(
    inputs: list,
    manifest: list,
    plan: dict,
    *,
    network_fn=None,
    sleep_fn=None,
    raw_path: Path = EVAL_RAW_ATTEMPTS,
    events_path: Path = EVAL_SESSION_EVENTS,
    sc5_path: Path = EVAL_SC5_TERMINAL,
    vc_path: Path = EVAL_VC_TERMINAL,
) -> dict:
    collector = load_frozen_dev_collector()

    input_map = {
        x["item_id"]: x
        for x in inputs
    }

    manifest_ids = [
        row["item_id"]
        for row in manifest
    ]

    if (
        len(input_map) != len(inputs)
        or len(set(manifest_ids)) != len(manifest_ids)
    ):
        raise RuntimeError(
            "Duplicate collection item IDs."
        )

    if set(input_map) != set(manifest_ids):
        raise RuntimeError(
            "Collection input/manifest ID mismatch."
        )

    sc5_done = load_terminal_map_strict(
        sc5_path
    )

    vc_done = load_terminal_map_strict(
        vc_path
    )

    allowed_ids = set(manifest_ids)

    if not set(sc5_done) <= allowed_ids:
        raise RuntimeError(
            "Unexpected SC5 terminal item ID."
        )

    if not set(vc_done) <= allowed_ids:
        raise RuntimeError(
            "Unexpected VC terminal item ID."
        )

    for position, row in enumerate(
        manifest,
        start=1,
    ):
        item_id = row["item_id"]
        seed = int(row["sc5_seed"])
        item = input_map[item_id]

        while True:
            action = item_collection_action(
                plan,
                item_id,
                sc5_done,
                vc_done,
            )

            if action == "DONE":
                break

            if action == "SC5":
                status, response = (
                    eval_request_with_retry(
                        "SC5_MAJORITY",
                        item_id,
                        collector.sc5_payload(
                            item["messages"],
                            seed,
                        ),
                        network_fn=network_fn,
                        sleep_fn=sleep_fn,
                        raw_path=raw_path,
                        events_path=events_path,
                    )
                )

                if status != "RESPONSE":
                    return {
                        "status": status,
                        "paused_item_id": item_id,
                        "paused_stage": "SC5_MAJORITY",
                        "sc5_terminal":
                            len(sc5_done),
                        "vc_terminal":
                            len(vc_done),
                    }

                parsed = collector.validate_sc5(
                    response
                )

                result = collector.extract_result(
                    response
                )

                raw_body = (
                    response.get("raw_body")
                    or ""
                )

                terminal = {
                    "item_id": item_id,
                    "order_position": position,
                    "seed": seed,
                    "valid": parsed["valid"],
                    "invalid_reason":
                        parsed["reason"],
                    "outputs":
                        parsed["outputs"],
                    "majority":
                        parsed.get("majority"),
                    "agreement":
                        parsed.get("agreement"),
                    "vote_counts":
                        parsed.get("vote_counts"),
                    "http_status":
                        response.get("http_status"),
                    "cloudflare_success":
                        (
                            response.get("body")
                            or {}
                        ).get("success"),
                    "returned_model":
                        result.get("model"),
                    "usage":
                        result.get("usage"),
                    "latency_ms":
                        response.get("latency_ms"),
                    "raw_response_sha256":
                        collector.sha256_bytes(
                            raw_body.encode("utf-8")
                        ),
                    "terminal_utc":
                        collector.utcnow(),
                }

                collector.append_jsonl(
                    sc5_path,
                    terminal,
                )

                sc5_done[item_id] = terminal
                continue

            if action == "VC":
                sc5_record = sc5_done[item_id]

                if not sc5_record["valid"]:
                    raise RuntimeError(
                        "VC requested after invalid SC5."
                    )

                majority = sc5_record.get(
                    "majority"
                )

                if majority not in collector.ALLOWED_LABELS:
                    raise RuntimeError(
                        "Valid SC5 lacks frozen recommendation."
                    )

                status, response = (
                    eval_request_with_retry(
                        "VC_SELF_EVAL",
                        item_id,
                        collector.vc_payload(
                            item["messages"],
                            majority,
                            seed,
                        ),
                        network_fn=network_fn,
                        sleep_fn=sleep_fn,
                        raw_path=raw_path,
                        events_path=events_path,
                    )
                )

                if status != "RESPONSE":
                    return {
                        "status": status,
                        "paused_item_id": item_id,
                        "paused_stage": "VC_SELF_EVAL",
                        "sc5_terminal":
                            len(sc5_done),
                        "vc_terminal":
                            len(vc_done),
                    }

                parsed = collector.validate_vc(
                    response
                )

                result = collector.extract_result(
                    response
                )

                raw_body = (
                    response.get("raw_body")
                    or ""
                )

                outputs = parsed["outputs"]

                terminal = {
                    "item_id": item_id,
                    "order_position": position,
                    "seed": seed,
                    "frozen_recommendation":
                        majority,
                    "valid": parsed["valid"],
                    "invalid_reason":
                        parsed["reason"],
                    "output":
                        (
                            outputs[0]
                            if outputs
                            else ""
                        ),
                    "confidence_integer":
                        parsed.get(
                            "confidence_integer"
                        ),
                    "raw_confidence":
                        parsed.get(
                            "raw_confidence"
                        ),
                    "http_status":
                        response.get("http_status"),
                    "cloudflare_success":
                        (
                            response.get("body")
                            or {}
                        ).get("success"),
                    "returned_model":
                        result.get("model"),
                    "usage":
                        result.get("usage"),
                    "latency_ms":
                        response.get("latency_ms"),
                    "raw_response_sha256":
                        collector.sha256_bytes(
                            raw_body.encode("utf-8")
                        ),
                    "terminal_utc":
                        collector.utcnow(),
                }

                collector.append_jsonl(
                    vc_path,
                    terminal,
                )

                vc_done[item_id] = terminal
                continue

            raise RuntimeError(
                "Unknown collection action."
            )

    for item_id in manifest_ids:
        if (
            item_collection_action(
                plan,
                item_id,
                sc5_done,
                vc_done,
            )
            != "DONE"
        ):
            raise RuntimeError(
                "Collection ended with unresolved item."
            )

    return {
        "status": "COMPLETE",
        "selected_estimator":
            plan["selected_estimator"],
        "items": len(manifest),
        "sc5_terminal": len(sc5_done),
        "sc5_valid": sum(
            1
            for x in sc5_done.values()
            if x["valid"]
        ),
        "vc_terminal": len(vc_done),
        "vc_valid": sum(
            1
            for x in vc_done.values()
            if x["valid"]
        ),
    }


def synthetic_collection_session_self_test() -> dict:
    collector = load_frozen_dev_collector()

    def make_inputs_and_manifest():
        inputs = []
        manifest = []

        for i in range(1, 4):
            item_id = f"G6D-E-{i:04d}"
            seed = eval_seed(item_id)

            inputs.append({
                "item_id": item_id,
                "messages": [
                    {
                        "role": "system",
                        "content": "synthetic",
                    },
                    {
                        "role": "user",
                        "content":
                            "synthetic"
                            + collector.DECISION_SUFFIX,
                    },
                ],
            })

            manifest.append({
                "item_id": item_id,
                "sc5_seed": str(seed),
            })

        return inputs, manifest

    def response(outputs):
        return {
            "http_status": 200,
            "body": {
                "success": True,
                "result": {
                    "choices": [
                        {
                            "message": {
                                "content": x,
                            }
                        }
                        for x in outputs
                    ],
                    "model": "synthetic-model",
                    "usage": {},
                },
            },
            "raw_body":
                json.dumps(outputs),
            "retry_after": None,
            "latency_ms": 1,
            "transport_error": "",
        }

    inputs, manifest = (
        make_inputs_and_manifest()
    )

    seed_to_index = {
        int(row["sc5_seed"]): i
        for i, row in enumerate(
            manifest,
            start=1,
        )
    }

    sc5_plan = {
        "selected_estimator":
            "SC5_AGREEMENT",
        "attempt_sc5_for_all_items": True,
        "attempt_vc_after_valid_sc5": False,
        "required_eval_items": 3,
    }

    sc5_calls = []

    def sc5_network(payload):
        idx = seed_to_index[
            int(payload["seed"])
        ]

        sc5_calls.append(
            (idx, int(payload["n"]))
        )

        if int(payload["n"]) != 5:
            raise RuntimeError(
                "SC5 plan unexpectedly called VC."
            )

        if idx == 1:
            return response(
                ["ESCALATE"] * 5
            )

        if idx == 2:
            return response([
                "ESCALATE",
                "ESCALATE",
                "ESCALATE",
                "ESCALATE",
                "MAYBE",
            ])

        return response(
            ["DO_NOT_ESCALATE"] * 5
        )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        kwargs = {
            "raw_path":
                root / "raw.jsonl",
            "events_path":
                root / "events.jsonl",
            "sc5_path":
                root / "sc5.jsonl",
            "vc_path":
                root / "vc.jsonl",
        }

        first_sc5 = run_eval_collection_session(
            inputs,
            manifest,
            sc5_plan,
            network_fn=sc5_network,
            sleep_fn=lambda _x: None,
            **kwargs,
        )

        calls_after_first = len(
            sc5_calls
        )

        second_sc5 = run_eval_collection_session(
            inputs,
            manifest,
            sc5_plan,
            network_fn=sc5_network,
            sleep_fn=lambda _x: None,
            **kwargs,
        )

        if first_sc5["status"] != "COMPLETE":
            raise RuntimeError(
                "Synthetic SC5 session incomplete."
            )

        if first_sc5["sc5_terminal"] != 3:
            raise RuntimeError(
                "Synthetic SC5 terminal count mismatch."
            )

        if first_sc5["sc5_valid"] != 2:
            raise RuntimeError(
                "Synthetic SC5 validity mismatch."
            )

        if first_sc5["vc_terminal"] != 0:
            raise RuntimeError(
                "SC5 winner produced VC terminals."
            )

        if len(sc5_calls) != calls_after_first:
            raise RuntimeError(
                "Completed SC5 items were regenerated."
            )

        if second_sc5 != first_sc5:
            raise RuntimeError(
                "SC5 resume summary changed."
            )

    vc_plan = {
        "selected_estimator":
            "VC_SELF_EVAL",
        "attempt_sc5_for_all_items": True,
        "attempt_vc_after_valid_sc5": True,
        "required_eval_items": 3,
    }

    vc_calls = []

    def vc_network(payload):
        idx = seed_to_index[
            int(payload["seed"])
        ]

        n = int(payload["n"])
        vc_calls.append((idx, n))

        if n == 5:
            return response(
                ["ESCALATE"] * 5
            )

        if n == 1:
            if idx == 2:
                return response(
                    ["not-an-integer"]
                )

            return response(
                ["80"]
            )

        raise RuntimeError(
            "Unexpected synthetic n."
        )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        kwargs = {
            "raw_path":
                root / "raw.jsonl",
            "events_path":
                root / "events.jsonl",
            "sc5_path":
                root / "sc5.jsonl",
            "vc_path":
                root / "vc.jsonl",
        }

        first_vc = run_eval_collection_session(
            inputs,
            manifest,
            vc_plan,
            network_fn=vc_network,
            sleep_fn=lambda _x: None,
            **kwargs,
        )

        calls_after_first = len(
            vc_calls
        )

        second_vc = run_eval_collection_session(
            inputs,
            manifest,
            vc_plan,
            network_fn=vc_network,
            sleep_fn=lambda _x: None,
            **kwargs,
        )

        if first_vc["status"] != "COMPLETE":
            raise RuntimeError(
                "Synthetic VC session incomplete."
            )

        if first_vc["sc5_terminal"] != 3:
            raise RuntimeError(
                "Synthetic VC SC5 count mismatch."
            )

        if first_vc["vc_terminal"] != 3:
            raise RuntimeError(
                "Synthetic VC terminal count mismatch."
            )

        if first_vc["vc_valid"] != 2:
            raise RuntimeError(
                "Synthetic VC validity mismatch."
            )

        if len(vc_calls) != calls_after_first:
            raise RuntimeError(
                "Completed VC items were regenerated."
            )

        if second_vc != first_vc:
            raise RuntimeError(
                "VC resume summary changed."
            )

    return {
        "status": "PASS",
        "sc5_branch_terminal": 3,
        "sc5_branch_valid": 2,
        "sc5_branch_vc_terminal": 0,
        "vc_branch_sc5_terminal": 3,
        "vc_branch_vc_terminal": 3,
        "vc_branch_vc_valid": 2,
        "resume_generated_new_calls": False,
        "semantic_invalid_regeneration": False,
        "real_model_calls": 0,
        "sealed_eval_model_inputs_opened": False,
        "sealed_eval_manifest_opened": False,
        "sealed_eval_ground_truth_opened": False,
        "gate7_opened": False,
    }


def validate_collection_complete(
    plan: dict,
    manifest: list,
    sc5_path: Path,
    vc_path: Path,
) -> dict:
    manifest_ids = [
        row["item_id"]
        for row in manifest
    ]

    if len(manifest_ids) != plan["required_eval_items"]:
        raise RuntimeError(
            "Collection completeness item-count mismatch."
        )

    if len(manifest_ids) != len(set(manifest_ids)):
        raise RuntimeError(
            "Duplicate manifest item IDs."
        )

    sc5_done = load_terminal_map_strict(
        sc5_path
    )

    vc_done = load_terminal_map_strict(
        vc_path
    )

    manifest_set = set(manifest_ids)

    if set(sc5_done) != manifest_set:
        raise RuntimeError(
            "SC5 terminal population is not complete."
        )

    valid_sc5_ids = set()

    for position, item_id in enumerate(
        manifest_ids,
        start=1,
    ):
        row = sc5_done[item_id]

        if row.get("order_position") != position:
            raise RuntimeError(
                "SC5 terminal order-position mismatch."
            )

        if not isinstance(row.get("valid"), bool):
            raise RuntimeError(
                "SC5 terminal validity is not boolean."
            )

        if row["valid"]:
            valid_sc5_ids.add(item_id)

    if plan["selected_estimator"] == "SC5_AGREEMENT":
        if vc_done:
            raise RuntimeError(
                "VC terminals exist for SC5-selected EVAL."
            )

    elif plan["selected_estimator"] == "VC_SELF_EVAL":
        if set(vc_done) != valid_sc5_ids:
            raise RuntimeError(
                "VC terminal population does not equal "
                "valid-SC5 population."
            )

        for item_id in valid_sc5_ids:
            row = vc_done[item_id]

            if not isinstance(row.get("valid"), bool):
                raise RuntimeError(
                    "VC terminal validity is not boolean."
                )

            expected_position = (
                manifest_ids.index(item_id) + 1
            )

            if row.get("order_position") != expected_position:
                raise RuntimeError(
                    "VC terminal order-position mismatch."
                )

    else:
        raise RuntimeError(
            "Unknown selected estimator."
        )

    for item_id in manifest_ids:
        if (
            item_collection_action(
                plan,
                item_id,
                sc5_done,
                vc_done,
            )
            != "DONE"
        ):
            raise RuntimeError(
                "Collection contains unresolved item."
            )

    return {
        "status": "COMPLETE",
        "selected_estimator":
            plan["selected_estimator"],
        "items": len(manifest_ids),
        "sc5_terminal": len(sc5_done),
        "sc5_valid": len(valid_sc5_ids),
        "sc5_invalid":
            len(sc5_done) - len(valid_sc5_ids),
        "vc_terminal": len(vc_done),
        "vc_valid": sum(
            1
            for row in vc_done.values()
            if row["valid"]
        ),
        "vc_invalid": sum(
            1
            for row in vc_done.values()
            if not row["valid"]
        ),
    }


def synthetic_collection_complete_self_test() -> dict:
    collector = load_frozen_dev_collector()

    manifest = [
        {
            "item_id": f"G6D-E-{i:04d}",
        }
        for i in range(1, 5)
    ]

    sc5_plan = {
        "selected_estimator":
            "SC5_AGREEMENT",
        "attempt_sc5_for_all_items": True,
        "attempt_vc_after_valid_sc5": False,
        "required_eval_items": 4,
    }

    vc_plan = {
        "selected_estimator":
            "VC_SELF_EVAL",
        "attempt_sc5_for_all_items": True,
        "attempt_vc_after_valid_sc5": True,
        "required_eval_items": 4,
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        sc5 = root / "sc5.jsonl"
        vc = root / "vc.jsonl"

        for i in range(1, 5):
            item_id = f"G6D-E-{i:04d}"

            collector.append_jsonl(
                sc5,
                {
                    "item_id": item_id,
                    "order_position": i,
                    "valid": (i != 4),
                },
            )

        sc5_result = validate_collection_complete(
            sc5_plan,
            manifest,
            sc5,
            vc,
        )

        for i in range(1, 4):
            item_id = f"G6D-E-{i:04d}"

            collector.append_jsonl(
                vc,
                {
                    "item_id": item_id,
                    "order_position": i,
                    "valid": (i != 3),
                },
            )

        vc_result = validate_collection_complete(
            vc_plan,
            manifest,
            sc5,
            vc,
        )

        fail_closed = 0

        # Missing SC5 terminal.
        missing_sc5 = root / "missing_sc5.jsonl"

        for i in range(1, 4):
            collector.append_jsonl(
                missing_sc5,
                {
                    "item_id": f"G6D-E-{i:04d}",
                    "order_position": i,
                    "valid": True,
                },
            )

        cases = [
            (
                sc5_plan,
                missing_sc5,
                root / "none.jsonl",
            ),
            (
                sc5_plan,
                sc5,
                vc,
            ),
        ]

        # VC missing one valid-SC5 terminal.
        vc_missing = root / "vc_missing.jsonl"

        for i in range(1, 3):
            collector.append_jsonl(
                vc_missing,
                {
                    "item_id": f"G6D-E-{i:04d}",
                    "order_position": i,
                    "valid": True,
                },
            )

        cases.append(
            (
                vc_plan,
                sc5,
                vc_missing,
            )
        )

        # Wrong SC5 order position.
        wrong_order = root / "wrong_order.jsonl"

        for i in range(1, 5):
            collector.append_jsonl(
                wrong_order,
                {
                    "item_id": f"G6D-E-{i:04d}",
                    "order_position":
                        99 if i == 2 else i,
                    "valid": True,
                },
            )

        cases.append(
            (
                sc5_plan,
                wrong_order,
                root / "none2.jsonl",
            )
        )

        for plan, a, b in cases:
            try:
                validate_collection_complete(
                    plan,
                    manifest,
                    a,
                    b,
                )
            except RuntimeError:
                fail_closed += 1
            else:
                raise RuntimeError(
                    "Incomplete/invalid collection "
                    "was accepted."
                )

    return {
        "status": "PASS",
        "sc5_complete":
            sc5_result["status"],
        "sc5_terminal":
            sc5_result["sc5_terminal"],
        "sc5_invalid":
            sc5_result["sc5_invalid"],
        "sc5_vc_terminal":
            sc5_result["vc_terminal"],
        "vc_complete":
            vc_result["status"],
        "vc_sc5_terminal":
            vc_result["sc5_terminal"],
        "vc_terminal":
            vc_result["vc_terminal"],
        "vc_invalid":
            vc_result["vc_invalid"],
        "fail_closed_tests":
            fail_closed,
        "real_model_calls": 0,
        "sealed_eval_model_inputs_opened": False,
        "sealed_eval_manifest_opened": False,
        "sealed_eval_ground_truth_opened": False,
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

    if final_path.exists():
        raise RuntimeError(
            "Refusing to overwrite existing artifact: "
            + str(final_path)
        )

    expected_sha = hashlib.sha256(
        data
    ).hexdigest()

    fd, tmp_name = tempfile.mkstemp(
        prefix="."
        + final_path.name
        + ".tmp.",
        dir=str(final_path.parent),
    )

    tmp_path = Path(tmp_name)

    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

        if sha256_file(tmp_path) != expected_sha:
            raise RuntimeError(
                "Temporary artifact SHA mismatch."
            )

        try:
            os.link(
                tmp_path,
                final_path,
            )
        except FileExistsError as exc:
            raise RuntimeError(
                "Refusing to overwrite existing artifact: "
                + str(final_path)
            ) from exc

        if sha256_file(final_path) != expected_sha:
            raise RuntimeError(
                "Installed artifact SHA mismatch."
            )

        return expected_sha

    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def synthetic_new_only_installer_self_test() -> dict:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        final = root / "freeze.json"

        payload = (
            b"{\"synthetic\":true}\n"
        )

        first_sha = install_bytes_new_only(
            final,
            payload,
        )

        if final.read_bytes() != payload:
            raise RuntimeError(
                "Installed bytes mismatch."
            )

        overwrite_blocked = False

        try:
            install_bytes_new_only(
                final,
                b"{\"different\":true}\n",
            )
        except RuntimeError:
            overwrite_blocked = True

        if not overwrite_blocked:
            raise RuntimeError(
                "Existing artifact was overwritten."
            )

        if final.read_bytes() != payload:
            raise RuntimeError(
                "Existing artifact changed after "
                "overwrite attempt."
            )

        temp_leftovers = [
            x
            for x in root.iterdir()
            if x.name.startswith(
                "." + final.name + ".tmp."
            )
        ]

        if temp_leftovers:
            raise RuntimeError(
                "Temporary installer files remain."
            )

    return {
        "status": "PASS",
        "installed_sha256": first_sha,
        "overwrite_blocked": overwrite_blocked,
        "original_bytes_preserved": True,
        "temporary_files_remaining": 0,
        "real_collection_freeze_created": False,
        "real_model_calls": 0,
        "sealed_eval_model_inputs_opened": False,
        "sealed_eval_manifest_opened": False,
        "sealed_eval_ground_truth_opened": False,
        "gate7_opened": False,
    }


def collection_freeze_bytes(
    payload: dict,
) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def install_collection_freeze(
    payload: dict,
    *,
    final_path: Path = EVAL_COLLECTION_FREEZE,
) -> dict:
    data = collection_freeze_bytes(
        payload
    )

    digest = install_bytes_new_only(
        final_path,
        data,
    )

    if (
        sha256_file(final_path)
        != digest
    ):
        raise RuntimeError(
            "Installed collection freeze SHA mismatch."
        )

    installed = json.loads(
        final_path.read_text(
            encoding="utf-8"
        )
    )

    if installed != payload:
        raise RuntimeError(
            "Installed collection freeze payload mismatch."
        )

    return {
        "path": str(final_path),
        "sha256": digest,
        "bytes": len(data),
    }


def synthetic_collection_freeze_install_self_test() -> dict:
    collector = load_frozen_dev_collector()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        sc5 = root / "sc5.jsonl"
        vc = root / "vc.jsonl"
        raw = root / "raw.jsonl"
        events = root / "events.jsonl"
        marker_path = root / "dev_marker.json"
        method_path = root / "method.json"
        freeze_path = root / "freeze.json"

        marker_path.write_text(
            "{\"synthetic\":true}\n",
            encoding="utf-8",
        )

        method_path.write_text(
            "{\"synthetic\":true}\n",
            encoding="utf-8",
        )

        manifest = [
            {
                "item_id":
                    f"G6D-E-{i:04d}"
            }
            for i in range(
                1,
                EXPECTED_EVAL_ITEMS + 1,
            )
        ]

        for i in range(
            1,
            EXPECTED_EVAL_ITEMS + 1,
        ):
            collector.append_jsonl(
                sc5,
                {
                    "item_id":
                        f"G6D-E-{i:04d}",
                    "order_position": i,
                    "valid": True,
                },
            )

        collector.append_jsonl(
            raw,
            {"synthetic": True},
        )

        plan = {
            "selected_estimator":
                "SC5_AGREEMENT",
            "attempt_sc5_for_all_items":
                True,
            "attempt_vc_after_valid_sc5":
                False,
            "required_eval_items":
                EXPECTED_EVAL_ITEMS,
        }

        payload = build_collection_freeze_payload(
            plan,
            manifest,
            sc5_path=sc5,
            vc_path=vc,
            raw_path=raw,
            events_path=events,
            dev_commit_marker_path=marker_path,
            dev_method_freeze_path=method_path,
        )

        validate_collection_freeze_payload(
            payload,
            sc5_path=sc5,
            vc_path=vc,
            raw_path=raw,
            events_path=events,
            dev_commit_marker_path=marker_path,
            dev_method_freeze_path=method_path,
        )

        installed = install_collection_freeze(
            payload,
            final_path=freeze_path,
        )

        overwrite_blocked = False

        try:
            install_collection_freeze(
                payload,
                final_path=freeze_path,
            )
        except RuntimeError:
            overwrite_blocked = True

        if not overwrite_blocked:
            raise RuntimeError(
                "Collection freeze overwrite was accepted."
            )

    return {
        "status": "PASS",
        "installed_sha256":
            installed["sha256"],
        "installed_bytes":
            installed["bytes"],
        "overwrite_blocked":
            overwrite_blocked,
        "real_collection_freeze_created":
            False,
        "real_model_calls": 0,
        "sealed_eval_model_inputs_opened":
            False,
        "sealed_eval_manifest_opened":
            False,
        "sealed_eval_ground_truth_opened":
            False,
        "gate7_opened":
            False,
    }


def artifact_binding(
    path: Path,
    *,
    required: bool,
) -> dict:
    exists = path.exists()

    if required and not exists:
        raise RuntimeError(
            "Required collection artifact missing: "
            + str(path)
        )

    return {
        "path": str(path),
        "exists": exists,
        "sha256":
            sha256_file(path)
            if exists
            else None,
        "bytes":
            path.stat().st_size
            if exists
            else 0,
    }


def build_collection_freeze_payload(
    plan: dict,
    manifest: list,
    *,
    sc5_path: Path,
    vc_path: Path,
    raw_path: Path,
    events_path: Path,
    dev_commit_marker_path: Path,
    dev_method_freeze_path: Path,
) -> dict:
    completeness = validate_collection_complete(
        plan,
        manifest,
        sc5_path,
        vc_path,
    )

    if not dev_commit_marker_path.exists():
        raise RuntimeError(
            "DEV scientific commit marker missing."
        )

    if not dev_method_freeze_path.exists():
        raise RuntimeError(
            "DEV method freeze missing."
        )

    vc_required = (
        plan["selected_estimator"]
        == "VC_SELF_EVAL"
    )

    return {
        "artifact":
            "GATE6D_EVAL_COLLECTION_FREEZE_V1",
        "status":
            "FROZEN_EVAL_MODEL_OUTPUTS",

        "selected_estimator":
            plan["selected_estimator"],

        "sealed_eval": {
            "model_inputs": {
                "path": str(SEALED_EVAL_INPUTS),
                "sha256": EXPECTED_EVAL_INPUT_SHA,
            },
            "manifest": {
                "path": str(SEALED_EVAL_MANIFEST),
                "sha256": EXPECTED_EVAL_MANIFEST_SHA,
            },
            "ground_truth": {
                "path": str(SEALED_EVAL_GT),
                "expected_sha256":
                    EXPECTED_EVAL_GT_SHA,
                "opened_during_collection":
                    False,
            },
        },

        "dev_scientific_transaction": {
            "commit_marker": artifact_binding(
                dev_commit_marker_path,
                required=True,
            ),
            "method_freeze": artifact_binding(
                dev_method_freeze_path,
                required=True,
            ),
        },

        "frozen_dependencies": {
            "eval_collection_executor_v1": {
                "path": str(EVAL_EXECUTOR),
                "sha256":
                    sha256_file(EVAL_EXECUTOR),
            },
            "eval_boundary_v2": {
                "path": str(BOUNDARY),
                "sha256":
                    EXPECTED_BOUNDARY_SHA,
            },
            "eval_boundary_freeze_v2": {
                "path": str(BOUNDARY_FREEZE),
                "sha256":
                    EXPECTED_BOUNDARY_FREEZE_SHA,
            },
            "dev_collector_v1_2": {
                "path": str(DEV_COLLECTOR),
                "sha256":
                    EXPECTED_DEV_COLLECTOR_SHA,
            },
            "eval_safeguard_v1": {
                "path": str(EVAL_SAFEGUARD),
                "sha256":
                    EXPECTED_EVAL_SAFEGUARD_SHA,
            },
            "vc_system_prompt": {
                "path": str(VC_SYSTEM_PROMPT),
                "sha256":
                    EXPECTED_VC_SYSTEM_PROMPT_SHA,
            },
        },

        "collection_outputs": {
            "raw_attempts": artifact_binding(
                raw_path,
                required=True,
            ),
            "session_events": artifact_binding(
                events_path,
                required=False,
            ),
            "sc5_terminal": artifact_binding(
                sc5_path,
                required=True,
            ),
            "vc_terminal": artifact_binding(
                vc_path,
                required=vc_required,
            ),
        },

        "completeness": completeness,

        "governance": {
            "all_458_attempted":
                completeness["items"]
                == EXPECTED_EVAL_ITEMS,
            "semantic_invalid_regeneration":
                False,
            "ground_truth_opened":
                False,
            "correctness_computed":
                False,
            "eval_refit_performed":
                False,
            "eval_reselection_performed":
                False,
            "external_test_accessed":
                False,
            "gate7_opened":
                False,
        },
    }


def validate_collection_freeze_payload(
    payload: dict,
    *,
    sc5_path: Path,
    vc_path: Path,
    raw_path: Path,
    events_path: Path,
    dev_commit_marker_path: Path,
    dev_method_freeze_path: Path,
) -> dict:
    if (
        payload.get("artifact")
        != "GATE6D_EVAL_COLLECTION_FREEZE_V1"
    ):
        raise RuntimeError(
            "Wrong EVAL collection-freeze artifact."
        )

    if (
        payload.get("status")
        != "FROZEN_EVAL_MODEL_OUTPUTS"
    ):
        raise RuntimeError(
            "Wrong EVAL collection-freeze status."
        )

    selected = payload.get(
        "selected_estimator"
    )

    if selected not in {
        "SC5_AGREEMENT",
        "VC_SELF_EVAL",
    }:
        raise RuntimeError(
            "Unknown frozen EVAL estimator."
        )

    sealed = payload["sealed_eval"]

    if (
        sealed["model_inputs"]["path"]
        != str(SEALED_EVAL_INPUTS)
        or sealed["model_inputs"]["sha256"]
        != EXPECTED_EVAL_INPUT_SHA
    ):
        raise RuntimeError(
            "EVAL input binding mismatch."
        )

    if (
        sealed["manifest"]["path"]
        != str(SEALED_EVAL_MANIFEST)
        or sealed["manifest"]["sha256"]
        != EXPECTED_EVAL_MANIFEST_SHA
    ):
        raise RuntimeError(
            "EVAL manifest binding mismatch."
        )

    gt = sealed["ground_truth"]

    if (
        gt["path"] != str(SEALED_EVAL_GT)
        or gt["expected_sha256"]
        != EXPECTED_EVAL_GT_SHA
        or gt["opened_during_collection"]
        is not False
    ):
        raise RuntimeError(
            "EVAL ground-truth boundary mismatch."
        )

    deps = payload["frozen_dependencies"]

    expected_deps = {
        "eval_collection_executor_v1":
            (
                EVAL_EXECUTOR,
                sha256_file(EVAL_EXECUTOR),
            ),
        "eval_boundary_v2":
            (BOUNDARY, EXPECTED_BOUNDARY_SHA),
        "eval_boundary_freeze_v2":
            (
                BOUNDARY_FREEZE,
                EXPECTED_BOUNDARY_FREEZE_SHA,
            ),
        "dev_collector_v1_2":
            (
                DEV_COLLECTOR,
                EXPECTED_DEV_COLLECTOR_SHA,
            ),
        "eval_safeguard_v1":
            (
                EVAL_SAFEGUARD,
                EXPECTED_EVAL_SAFEGUARD_SHA,
            ),
        "vc_system_prompt":
            (
                VC_SYSTEM_PROMPT,
                EXPECTED_VC_SYSTEM_PROMPT_SHA,
            ),
    }

    if set(deps) != set(expected_deps):
        raise RuntimeError(
            "Frozen dependency set mismatch."
        )

    for name, (path, expected_sha) in (
        expected_deps.items()
    ):
        rec = deps[name]

        if (
            rec["path"] != str(path)
            or rec["sha256"] != expected_sha
            or sha256_file(path) != expected_sha
        ):
            raise RuntimeError(
                "Frozen dependency binding mismatch: "
                + name
            )

    transaction = payload[
        "dev_scientific_transaction"
    ]

    for name, path in {
        "commit_marker":
            dev_commit_marker_path,
        "method_freeze":
            dev_method_freeze_path,
    }.items():
        rec = transaction[name]

        if (
            rec["path"] != str(path)
            or rec["exists"] is not True
            or rec["sha256"]
            != sha256_file(path)
        ):
            raise RuntimeError(
                "DEV transaction binding mismatch: "
                + name
            )

    outputs = payload[
        "collection_outputs"
    ]

    expected_outputs = {
        "raw_attempts":
            (raw_path, True),
        "session_events":
            (events_path, False),
        "sc5_terminal":
            (sc5_path, True),
        "vc_terminal":
            (
                vc_path,
                selected == "VC_SELF_EVAL",
            ),
    }

    for name, (path, required) in (
        expected_outputs.items()
    ):
        actual = artifact_binding(
            path,
            required=required,
        )

        if outputs[name] != actual:
            raise RuntimeError(
                "Collection-output binding mismatch: "
                + name
            )

    gov = payload["governance"]

    required_false = [
        "semantic_invalid_regeneration",
        "ground_truth_opened",
        "correctness_computed",
        "eval_refit_performed",
        "eval_reselection_performed",
        "external_test_accessed",
        "gate7_opened",
    ]

    if gov["all_458_attempted"] is not True:
        raise RuntimeError(
            "EVAL completeness flag is false."
        )

    for key in required_false:
        if gov[key] is not False:
            raise RuntimeError(
                "Unsafe governance flag: "
                + key
            )

    return {
        "status": "PASS",
        "selected_estimator": selected,
        "collection_outputs_bound": True,
        "dev_transaction_bound": True,
        "ground_truth_opened": False,
    }


def synthetic_collection_freeze_payload_self_test() -> dict:
    collector = load_frozen_dev_collector()

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)

        sc5 = root / "sc5.jsonl"
        vc = root / "vc.jsonl"
        raw = root / "raw.jsonl"
        events = root / "events.jsonl"
        marker = root / "dev_marker.json"
        method = root / "method.json"

        marker.write_text(
            "{\"synthetic\":true}\n",
            encoding="utf-8",
        )

        method.write_text(
            "{\"synthetic\":true}\n",
            encoding="utf-8",
        )

        manifest = [
            {
                "item_id":
                    f"G6D-E-{i:04d}"
            }
            for i in range(
                1,
                EXPECTED_EVAL_ITEMS + 1,
            )
        ]

        for i in range(
            1,
            EXPECTED_EVAL_ITEMS + 1,
        ):
            item_id = f"G6D-E-{i:04d}"

            collector.append_jsonl(
                sc5,
                {
                    "item_id": item_id,
                    "order_position": i,
                    "valid": True,
                },
            )

        collector.append_jsonl(
            raw,
            {
                "synthetic": True,
            },
        )

        plan = {
            "selected_estimator":
                "SC5_AGREEMENT",
            "attempt_sc5_for_all_items":
                True,
            "attempt_vc_after_valid_sc5":
                False,
            "required_eval_items":
                EXPECTED_EVAL_ITEMS,
        }

        payload = build_collection_freeze_payload(
            plan,
            manifest,
            sc5_path=sc5,
            vc_path=vc,
            raw_path=raw,
            events_path=events,
            dev_commit_marker_path=marker,
            dev_method_freeze_path=method,
        )

        valid = validate_collection_freeze_payload(
            payload,
            sc5_path=sc5,
            vc_path=vc,
            raw_path=raw,
            events_path=events,
            dev_commit_marker_path=marker,
            dev_method_freeze_path=method,
        )

        fail_closed = 0

        tampered = []

        x=json.loads(json.dumps(payload))
        x["status"]="WRONG"
        tampered.append(x)

        x=json.loads(json.dumps(payload))
        x["selected_estimator"]="VC_SELF_EVAL"
        tampered.append(x)

        x=json.loads(json.dumps(payload))
        x["collection_outputs"]["sc5_terminal"][
            "sha256"
        ]="0"*64
        tampered.append(x)

        x=json.loads(json.dumps(payload))
        x["dev_scientific_transaction"][
            "commit_marker"
        ]["sha256"]="0"*64
        tampered.append(x)

        x=json.loads(json.dumps(payload))
        x["sealed_eval"]["ground_truth"][
            "opened_during_collection"
        ]=True
        tampered.append(x)

        x=json.loads(json.dumps(payload))
        x["governance"][
            "correctness_computed"
        ]=True
        tampered.append(x)

        for x in tampered:
            try:
                validate_collection_freeze_payload(
                    x,
                    sc5_path=sc5,
                    vc_path=vc,
                    raw_path=raw,
                    events_path=events,
                    dev_commit_marker_path=marker,
                    dev_method_freeze_path=method,
                )
            except RuntimeError:
                fail_closed += 1
            else:
                raise RuntimeError(
                    "Tampered collection freeze accepted."
                )

    return {
        "status": "PASS",
        "selected_estimator":
            valid["selected_estimator"],
        "collection_outputs_bound":
            valid["collection_outputs_bound"],
        "dev_transaction_bound":
            valid["dev_transaction_bound"],
        "fail_closed_tests":
            fail_closed,
        "real_collection_freeze_created":
            False,
        "sealed_eval_model_inputs_opened":
            False,
        "sealed_eval_manifest_opened":
            False,
        "sealed_eval_ground_truth_opened":
            False,
        "model_calls": 0,
        "gate7_opened": False,
    }


def load_eval_inputs_after_unlock() -> dict:
    pf = executor_preflight()

    if not pf["ready"]:
        raise RuntimeError(
            "Sealed EVAL load refused: "
            "executor preflight is not ready."
        )

    if (
        sha256_file(SEALED_EVAL_INPUTS)
        != EXPECTED_EVAL_INPUT_SHA
    ):
        raise RuntimeError(
            "Sealed EVAL model-input SHA mismatch."
        )

    if (
        sha256_file(SEALED_EVAL_MANIFEST)
        != EXPECTED_EVAL_MANIFEST_SHA
    ):
        raise RuntimeError(
            "Sealed EVAL manifest SHA mismatch."
        )

    inputs = []

    with SEALED_EVAL_INPUTS.open(
        encoding="utf-8"
    ) as f:
        for line in f:
            line = line.strip()
            if line:
                inputs.append(
                    json.loads(line)
                )

    with SEALED_EVAL_MANIFEST.open(
        newline="",
        encoding="utf-8",
    ) as f:
        manifest = list(
            csv.DictReader(f)
        )

    structure = validate_eval_records(
        inputs,
        manifest,
    )

    return {
        "inputs": inputs,
        "manifest": manifest,
        "structure": structure,
        "input_sha256":
            EXPECTED_EVAL_INPUT_SHA,
        "manifest_sha256":
            EXPECTED_EVAL_MANIFEST_SHA,
    }


def load_collection_plan_after_unlock() -> dict:
    pf = executor_preflight()

    if not pf["ready"]:
        raise RuntimeError(
            "DEV method-freeze load refused: "
            "executor preflight is not ready."
        )

    if not DEV_METHOD_FREEZE.exists():
        raise RuntimeError(
            "DEV method freeze is missing."
        )

    method_freeze = json.loads(
        DEV_METHOD_FREEZE.read_text(
            encoding="utf-8"
        )
    )

    return collection_plan_from_method_freeze(
        method_freeze
    )


def execute_real_collection() -> dict:
    pf = executor_preflight()

    if not pf["ready"]:
        return {
            "status": "BLOCKED",
            "reasons": pf["reasons"],
            "sealed_eval_model_inputs_opened": False,
            "sealed_eval_manifest_opened": False,
            "sealed_eval_ground_truth_opened": False,
            "real_eval_collection_performed": False,
            "model_calls": 0,
            "external_test_accessed": False,
            "gate7_opened": False,
        }

    loaded = load_eval_inputs_after_unlock()
    plan = load_collection_plan_after_unlock()

    if (
        loaded["structure"]["items"]
        != plan["required_eval_items"]
    ):
        raise RuntimeError(
            "EVAL item count does not match "
            "frozen collection plan."
        )

    result = run_eval_collection_session(
        loaded["inputs"],
        loaded["manifest"],
        plan,
    )

    if result["status"] != "COMPLETE":
        return {
            "status": result["status"],
            "selected_estimator":
                plan["selected_estimator"],
            "collection_summary": result,
            "collection_freeze_created": False,
            "sealed_eval_model_inputs_opened": True,
            "sealed_eval_manifest_opened": True,
            "sealed_eval_ground_truth_opened": False,
            "real_eval_collection_performed": True,
            "external_test_accessed": False,
            "gate7_opened": False,
        }

    freeze_payload = build_collection_freeze_payload(
        plan,
        loaded["manifest"],
        sc5_path=EVAL_SC5_TERMINAL,
        vc_path=EVAL_VC_TERMINAL,
        raw_path=EVAL_RAW_ATTEMPTS,
        events_path=EVAL_SESSION_EVENTS,
        dev_commit_marker_path=DEV_COMMIT_MARKER,
        dev_method_freeze_path=DEV_METHOD_FREEZE,
    )

    validate_collection_freeze_payload(
        freeze_payload,
        sc5_path=EVAL_SC5_TERMINAL,
        vc_path=EVAL_VC_TERMINAL,
        raw_path=EVAL_RAW_ATTEMPTS,
        events_path=EVAL_SESSION_EVENTS,
        dev_commit_marker_path=DEV_COMMIT_MARKER,
        dev_method_freeze_path=DEV_METHOD_FREEZE,
    )

    freeze_binding = install_collection_freeze(
        freeze_payload,
        final_path=EVAL_COLLECTION_FREEZE,
    )

    return {
        "status": "COMPLETE_AND_FROZEN",
        "selected_estimator":
            plan["selected_estimator"],
        "collection_summary": result,
        "collection_freeze_created": True,
        "collection_freeze": freeze_binding,
        "sealed_eval_model_inputs_opened": True,
        "sealed_eval_manifest_opened": True,
        "sealed_eval_ground_truth_opened": False,
        "real_eval_collection_performed": True,
        "external_test_accessed": False,
        "gate7_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", action="store_true")

    parser.add_argument(
        "--collect-real",
        action="store_true",
    )
    args = parser.parse_args()

    if (
        int(args.preflight)
        + int(args.collect_real)
        != 1
    ):
        parser.error(
            "Choose exactly one of "
            "--preflight or --collect-real."
        )

    if args.collect_real:
        result = execute_real_collection()

        print(
            "=== GATE 6D REAL EVAL COLLECTION EXECUTOR ==="
        )

        for key, value in result.items():
            print(f"{key}: {value}")

        return

    pf = executor_preflight()

    print("EVAL EXECUTOR V1 WORKING COPY")
    print("Frozen dependency validation: PASS")
    print("Real collection ready:", pf["ready"])
    print(
        "Boundary collection gate allowed:",
        pf["boundary_collection_gate_allowed"],
    )
    print(
        "Real collection env allowed:",
        pf["real_collection_env_allowed"],
    )
    print(
        "Collection freeze exists:",
        pf["collection_freeze_exists"],
    )

    for reason in pf["reasons"]:
        print("-", reason)

    print("Real collection implemented: YES, HARD-GATED")
    print("Sealed EVAL model inputs opened: NO")
    print("Sealed EVAL manifest opened: NO")
    print("Hidden EVAL ground truth opened: NO")
    print("Model calls: 0")
    print("Gate 7 opened: NO")


if __name__ == "__main__":
    main()
