#!/usr/bin/env python3

"""
Pre-Gate-7 synthetic-only logging/randomization framework.

IMPORTANT:
- Gate 7 is NOT opened by this script.
- Real participants are NOT supported.
- Final study conditions are NOT encoded.
- Final calibrated confidence is NOT used.
- Calibration-EVAL and External-TEST are NOT accessed.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Iterable


STATUS_PATH = Path(
    "docs/pre_gate7/PRE_GATE7_STATUS_V1.json"
)

NAMESPACE = "PRE_GATE7_SYNTHETIC_V1"

REQUIRED_EVENT_KEYS = {
    "participant_id",
    "session_id",
    "trial_index",
    "event_type",
    "monotonic_ms",
    "condition",
    "item_id",
    "payload",
}


def assert_pre_gate7_boundary() -> dict:
    if not STATUS_PATH.exists():
        raise RuntimeError(
            "Pre-Gate-7 status file is missing."
        )

    status = json.loads(
        STATUS_PATH.read_text(encoding="utf-8")
    )

    required_false = [
        "gate7_open",
        "gate6_closed",
        "real_participants_allowed",
        "final_calibrated_confidence_allowed",
        "external_test_allowed",
    ]

    for key in required_false:
        if status.get(key) is not False:
            raise RuntimeError(
                f"Fail-closed boundary violation: {key}"
            )

    return status


def sha256_hex(*parts: str) -> str:
    text = "|".join([NAMESPACE, *parts])
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def synthetic_participant_id(index: int) -> str:
    if index < 1:
        raise ValueError("index must be >= 1")

    return "SYN-" + sha256_hex(
        "participant",
        str(index),
    )[:12]


def counterbalanced_order(
    participant_index: int,
    conditions: Iterable[str],
) -> tuple[str, ...]:
    """
    Generic synthetic counterbalancing helper.

    This is infrastructure only. It does not freeze the final
    experimental design or final study conditions.
    """
    values = tuple(conditions)

    if len(values) < 2:
        raise ValueError(
            "At least two synthetic conditions required."
        )

    if len(set(values)) != len(values):
        raise ValueError(
            "Synthetic conditions must be unique."
        )

    perms = sorted(itertools.permutations(values))

    return perms[
        (participant_index - 1) % len(perms)
    ]


def deterministic_trial_order(
    participant_id: str,
    trial_ids: Iterable[str],
) -> list[str]:
    ids = list(trial_ids)

    if len(ids) != len(set(ids)):
        raise ValueError("Trial IDs must be unique.")

    return sorted(
        ids,
        key=lambda item: sha256_hex(
            "trial-order",
            participant_id,
            item,
        ),
    )


def validate_event(event: dict) -> None:
    missing = REQUIRED_EVENT_KEYS - set(event)

    if missing:
        raise ValueError(
            f"Missing event fields: {sorted(missing)}"
        )

    extra = set(event) - REQUIRED_EVENT_KEYS

    if extra:
        raise ValueError(
            f"Unexpected event fields: {sorted(extra)}"
        )

    if not str(event["participant_id"]).startswith(
        "SYN-"
    ):
        raise ValueError(
            "Synthetic-only framework rejects "
            "non-synthetic participant IDs."
        )

    if not isinstance(event["trial_index"], int):
        raise ValueError("trial_index must be integer.")

    if event["trial_index"] < 1:
        raise ValueError("trial_index must be >= 1.")

    if not isinstance(
        event["monotonic_ms"],
        (int, float),
    ):
        raise ValueError(
            "monotonic_ms must be numeric."
        )

    if not isinstance(event["payload"], dict):
        raise ValueError("payload must be an object.")


def synthetic_self_test() -> dict:
    assert_pre_gate7_boundary()

    conditions = (
        "SYN_CONDITION_A",
        "SYN_CONDITION_B",
        "SYN_CONDITION_C",
    )

    trial_ids = [
        f"SYN_ITEM_{i:03d}"
        for i in range(1, 13)
    ]

    participants = []

    for i in range(1, 61):
        pid = synthetic_participant_id(i)

        order1 = deterministic_trial_order(
            pid,
            trial_ids,
        )

        order2 = deterministic_trial_order(
            pid,
            trial_ids,
        )

        if order1 != order2:
            raise AssertionError(
                "Trial randomization is not deterministic."
            )

        condition_order = counterbalanced_order(
            i,
            conditions,
        )

        event = {
            "participant_id": pid,
            "session_id":
                "SYN_SESSION_" + str(i).zfill(3),
            "trial_index": 1,
            "event_type": "synthetic_trial_view",
            "monotonic_ms": 1000.0 + i,
            "condition": condition_order[0],
            "item_id": order1[0],
            "payload": {
                "synthetic": True
            },
        }

        validate_event(event)

        participants.append(
            {
                "participant_id": pid,
                "condition_order":
                    list(condition_order),
                "trial_order": order1,
            }
        )

    all_perms = sorted(
        itertools.permutations(conditions)
    )

    counts = {
        ",".join(p): 0
        for p in all_perms
    }

    for row in participants:
        key = ",".join(
            row["condition_order"]
        )
        counts[key] += 1

    # 60 participants / 6 permutations = 10 each.
    if set(counts.values()) != {10}:
        raise AssertionError(
            "Synthetic counterbalancing failed."
        )

    if len({
        p["participant_id"]
        for p in participants
    }) != 60:
        raise AssertionError(
            "Synthetic participant IDs not unique."
        )

    result = {
        "artifact":
            "PRE_GATE7_SYNTHETIC_FRAMEWORK_SELF_TEST_V1",
        "status": "PASS",
        "synthetic_participants": 60,
        "synthetic_conditions": 3,
        "condition_permutations": 6,
        "participants_per_permutation": 10,
        "synthetic_trials_per_participant": 12,
        "deterministic_trial_order": True,
        "event_schema_validation": True,
        "gate7_opened": False,
        "real_participants": False,
        "final_calibrated_confidence_used": False,
        "calibration_eval_accessed": False,
        "external_test_accessed": False,
        "model_calls": 0,
    }

    return result


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.self_test:
        print(
            "BLOCKED: synthetic-only framework "
            "currently permits --self-test only."
        )
        return

    result = synthetic_self_test()

    out = Path(
        "benchmarks/pre_gate7/synthetic_v1/"
        "self_test_result.json"
    )

    out.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        "=== PRE-GATE-7 SYNTHETIC FRAMEWORK ==="
    )

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
