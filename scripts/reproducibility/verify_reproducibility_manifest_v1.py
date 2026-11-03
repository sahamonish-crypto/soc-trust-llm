#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


DEFAULT_MANIFEST = Path(
    "benchmarks/reproducibility/"
    "REPRODUCIBILITY_MANIFEST_V1.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def verify_manifest(path: Path) -> dict:
    obj = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if obj.get("artifact") != "REPRODUCIBILITY_MANIFEST_V1":
        raise RuntimeError(
            "Unexpected manifest artifact."
        )

    if obj.get("status") != "PRE_OUTCOME_REPRODUCIBILITY_SNAPSHOT":
        raise RuntimeError(
            "Unexpected manifest status."
        )

    repo = obj["repository"]

    anchor = repo["anchor_commit"]
    generation_head = repo["generation_head"]

    subprocess.run(
        [
            "git",
            "cat-file",
            "-e",
            generation_head + "^{commit}",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            anchor,
            generation_head,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    entries = (
        obj["authoritative_freezes"]
        + obj["authoritative_implementations"]
    )

    seen = set()

    for entry in entries:
        rel = entry["path"]

        if rel in seen:
            raise RuntimeError(
                "Duplicate authoritative path: "
                + rel
            )

        seen.add(rel)

        p = Path(rel)

        if not p.is_file():
            raise RuntimeError(
                "Missing authoritative file: "
                + rel
            )

        actual = sha256(p)

        if actual != entry["sha256"]:
            raise RuntimeError(
                "SHA256 mismatch: "
                + rel
            )

        if p.stat().st_size != entry["bytes"]:
            raise RuntimeError(
                "Byte-size mismatch: "
                + rel
            )

    counts = obj["counts"]

    if counts["authoritative_freezes"] != len(
        obj["authoritative_freezes"]
    ):
        raise RuntimeError(
            "Freeze count mismatch."
        )

    if counts["authoritative_implementations"] != len(
        obj["authoritative_implementations"]
    ):
        raise RuntimeError(
            "Implementation count mismatch."
        )

    governance = obj["governance"]

    forbidden_true = [
        "hidden_dev_ground_truth_opened",
        "hidden_eval_ground_truth_opened",
        "eval_scoring_performed",
        "external_test_accessed",
        "real_participants_used",
        "gate7_opened",
        "mutable_current_audit_included",
        "superseded_executor_freezes_authoritative",
    ]

    for key in forbidden_true:
        if governance.get(key) is not False:
            raise RuntimeError(
                "Governance violation: "
                + key
            )

    return {
        "status": "PASS",
        "verified_files": len(entries),
        "verified_freezes":
            len(obj["authoritative_freezes"]),
        "verified_implementations":
            len(obj["authoritative_implementations"]),
        "anchor_commit": anchor,
        "generation_head": generation_head,
    }


def self_test() -> dict:
    good = verify_manifest(
        DEFAULT_MANIFEST
    )

    fail_closed = 0

    original = json.loads(
        DEFAULT_MANIFEST.read_text(
            encoding="utf-8"
        )
    )

    tampered = json.loads(
        json.dumps(original)
    )

    tampered[
        "authoritative_freezes"
    ][0]["sha256"] = "0" * 64

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "tampered.json"

        p.write_text(
            json.dumps(
                tampered,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

        try:
            verify_manifest(p)
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Tampered hash was not rejected."
            )

    tampered = json.loads(
        json.dumps(original)
    )
    tampered[
        "governance"
    ]["gate7_opened"] = True

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "tampered.json"

        p.write_text(
            json.dumps(
                tampered,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

        try:
            verify_manifest(p)
        except Exception:
            fail_closed += 1
        else:
            raise RuntimeError(
                "Governance tamper was not rejected."
            )

    return {
        **good,
        "fail_closed_tests":
            fail_closed,
        "tampered_authoritative_files":
            False,
        "hidden_gt_accessed":
            False,
        "eval_scoring_performed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


if __name__ == "__main__":
    result = self_test()

    for key,value in result.items():
        print(f"{key}: {value}")
