#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy
import pandas
import scipy
import sklearn
import statsmodels


ANCHOR_COMMIT = "67280d5"

AUTHORITATIVE_FREEZES = [
    "benchmarks/gate6d/GATE6D_ALERT_CARD_VALIDITY_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_BRIER_TIE_THRESHOLD_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_CANONICAL_INPUTS_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_DEV500_COLLECTION_AUDIT_TOOL_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_DEV500_COLLECTION_IMPLEMENTATION_FREEZE_V1_2.json",
    "benchmarks/gate6d/analysis_core_v1/GATE6D_CALIBRATION_ANALYSIS_IMPLEMENTATION_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_DEV_METHOD_FREEZE_CORE_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_REAL_DEV_ANALYSIS_EXECUTOR_FREEZE_V3.json",
    "benchmarks/gate6d/GATE6D_EVAL_COLLECTION_GATE_FREEZE_V2.json",
    "benchmarks/gate6d/GATE6D_EVAL_COLLECTION_EXECUTOR_FREEZE_V1.json",
    "benchmarks/gate6d/GATE6D_EVAL_SCORING_EXECUTOR_FREEZE_V1.json",
    "benchmarks/pre_gate7/PRE_GATE7_SYNTHETIC_FRAMEWORK_FREEZE_V1.json",
    "benchmarks/pre_gate7/PRE_GATE7_STATISTICAL_ANALYSIS_FREEZE_V1.json",
    "benchmarks/pre_gate7/PRE_GATE7_HUMAN_STUDY_DECISION_FRAMEWORK_FREEZE_V1.json",
]

AUTHORITATIVE_IMPLEMENTATIONS = [
    "scripts/gate6/run_gate6d_dev_uncertainty_collection_v1_2.py",
    "scripts/gate6/audit_gate6d_dev500_collection_v1.py",
    "scripts/gate6/gate6d_calibration_analysis_core.py",
    "scripts/gate6/gate6d_real_dev_analysis_executor_v3.py",
    "scripts/gate6/gate6d_eval_collection_gate_v2.py",
    "scripts/gate6/gate6d_eval_collection_executor_v1.py",
    "scripts/gate6/gate6d_eval_scoring_executor_v1.py",
    "scripts/pre_gate7/pre_gate7_logging_randomization_v1.py",
    "scripts/pre_gate7/pre_gate7_statistical_analysis_core_v1.py",
    "scripts/pre_gate7/pre_gate7_human_study_decision_framework_v1.py",
]

OUTPUT = Path(
    "benchmarks/reproducibility/"
    "REPRODUCIBILITY_MANIFEST_V1.json"
)


def run(*args: str) -> str:
    return subprocess.check_output(
        args,
        text=True,
    ).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def assert_tracked(path: str) -> None:
    subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            path,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def describe_file(path: str) -> dict:
    p = Path(path)

    if not p.is_file():
        raise RuntimeError(
            f"Missing authoritative file: {path}"
        )

    assert_tracked(path)

    return {
        "path": path,
        "sha256": sha256(p),
        "bytes": p.stat().st_size,
    }


def main() -> None:
    head = run(
        "git",
        "rev-parse",
        "HEAD",
    )

    subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            ANCHOR_COMMIT,
            head,
        ],
        check=True,
    )

    tracked_status = run(
        "git",
        "status",
        "--porcelain",
        "--untracked-files=no",
    )

    if tracked_status:
        raise RuntimeError(
            "Tracked worktree is not clean."
        )

    freezes = [
        describe_file(x)
        for x in AUTHORITATIVE_FREEZES
    ]

    implementations = [
        describe_file(x)
        for x in AUTHORITATIVE_IMPLEMENTATIONS
    ]

    # Validate that every freeze is valid JSON,
    # without following any referenced data paths.
    for entry in freezes:
        json.loads(
            Path(
                entry["path"]
            ).read_text(
                encoding="utf-8"
            )
        )

    payload = {
        "artifact":
            "REPRODUCIBILITY_MANIFEST_V1",
        "status":
            "PRE_OUTCOME_REPRODUCIBILITY_SNAPSHOT",
        "repository": {
            "anchor_commit":
                ANCHOR_COMMIT,
            "generation_head":
                head,
            "tracked_worktree_clean":
                True,
            "untracked_operational_files":
                "EXCLUDED_BY_DESIGN",
        },
        "authoritative_freezes":
            freezes,
        "authoritative_implementations":
            implementations,
        "environment": {
            "python":
                sys.version.split()[0],
            "numpy":
                numpy.__version__,
            "pandas":
                pandas.__version__,
            "scipy":
                scipy.__version__,
            "scikit_learn":
                sklearn.__version__,
            "statsmodels":
                statsmodels.__version__,
        },
        "governance": {
            "hidden_dev_ground_truth_opened":
                False,
            "hidden_eval_ground_truth_opened":
                False,
            "eval_scoring_performed":
                False,
            "external_test_accessed":
                False,
            "real_participants_used":
                False,
            "gate7_opened":
                False,
            "mutable_current_audit_included":
                False,
            "superseded_executor_freezes_authoritative":
                False,
        },
        "counts": {
            "authoritative_freezes":
                len(freezes),
            "authoritative_implementations":
                len(implementations),
        },
    }

    OUTPUT.write_text(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n",
        encoding="utf-8",
    )

    manifest_sha = sha256(
        OUTPUT
    )

    print("status: PASS")
    print(
        "anchor_commit:",
        ANCHOR_COMMIT,
    )
    print(
        "generation_head:",
        head,
    )
    print(
        "authoritative_freezes:",
        len(freezes),
    )
    print(
        "authoritative_implementations:",
        len(implementations),
    )
    print(
        "tracked_worktree_clean: True"
    )
    print(
        "untracked_operational_files_included: False"
    )
    print(
        "hidden_gt_accessed: False"
    )
    print(
        "eval_scoring_performed: False"
    )
    print(
        "external_test_accessed: False"
    )
    print(
        "gate7_opened: False"
    )
    print(
        "manifest_sha256:",
        manifest_sha,
    )


if __name__ == "__main__":
    main()
