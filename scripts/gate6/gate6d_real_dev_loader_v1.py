#!/usr/bin/env python3

"""
Gate 6D real-DEV loader/gating layer V1.

Purpose
-------
Provide the future controlled bridge from frozen DEV500 collection
artifacts into the already-frozen DEV normalization core.

Real data may be opened only after BOTH:
1. GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1.json exists and
   validates as FROZEN_COMPLETE with 500/500 selected items; and
2. GATE6D_ALLOW_REAL_DEV_LOAD=YES is explicitly set.

Before those conditions are satisfied, this module:
- does not open SC5 terminal outputs;
- does not open VC terminal outputs;
- does not open hidden DEV ground truth;
- does not compute correctness;
- does not access Calibration-EVAL;
- does not access External-TEST.

The real loader does not perform estimator/calibrator selection itself.
It only produces normalized DEV rows with capture/episode metadata for
the separately frozen analysis modules.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys


# ---------------------------------------------------------------------
# Frozen code dependency
# ---------------------------------------------------------------------

NORMALIZATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_dev_normalization_core_v1.py"
)

EXPECTED_NORMALIZATION_SHA = (
    "7983ed4320908fd87913bc7a3b031133"
    "50763efb0fed1d8d00ba675da81e7ba0"
)

AUDIT_TOOL = Path(
    "scripts/gate6/"
    "audit_gate6d_dev500_collection_v1.py"
)

EXPECTED_AUDIT_TOOL_SHA = (
    "8df4bf36a3b1bd0213a333f8b9b3deff"
    "f9897e682862856fc35574ad33fa6123"
)


# ---------------------------------------------------------------------
# Frozen DEV artifacts
# ---------------------------------------------------------------------

SELECTED_MANIFEST = Path(
    "benchmarks/gate6d/dev500_v1/"
    "dev500_selected_items.csv"
)

EXPECTED_SELECTED_MANIFEST_SHA = (
    "db1016850df42736c1851b66a296550f"
    "82e4509e90b33f08fff8a73bad2e0f87"
)

CANONICAL_DEV_MANIFEST = Path(
    "benchmarks/gate6d/canonical_v1/"
    "dev_collection_manifest.csv"
)

EXPECTED_CANONICAL_DEV_MANIFEST_SHA = (
    "de9bcd31706393abc9c42c249b4bc463"
    "e9542a0a34b3705d9aec9acc9ca19626"
)

HIDDEN_DEV_GT = Path(
    "benchmarks/gate6d/canonical_v1/"
    "hidden/dev_ground_truth.jsonl"
)

EXPECTED_HIDDEN_DEV_GT_SHA = (
    "db3d294d5d5e0653834241b3415f827"
    "95ab2d8a3287743a4de7506ae6e3ae40e"
)


# ---------------------------------------------------------------------
# Real collection files
# ---------------------------------------------------------------------

COLLECTION_DIR = Path(
    "benchmarks/gate6d/dev_collection_v1"
)

SC5_TERMINAL = (
    COLLECTION_DIR
    / "sc5_terminal.jsonl"
)

VC_TERMINAL = (
    COLLECTION_DIR
    / "vc_terminal.jsonl"
)


# ---------------------------------------------------------------------
# Required future unlock artifact
# ---------------------------------------------------------------------

COLLECTION_COMPLETE_FREEZE = Path(
    "benchmarks/gate6d/"
    "GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1.json"
)

REAL_LOAD_ENV = (
    "GATE6D_ALLOW_REAL_DEV_LOAD"
)


# ---------------------------------------------------------------------
# Synthetic evidence
# ---------------------------------------------------------------------

SELFTEST_OUT = Path(
    "benchmarks/gate6d/"
    "real_dev_loader_v1/"
    "synthetic_self_test.json"
)


def sha256_file(
    path: Path,
) -> str:
    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:
        for block in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):
            h.update(
                block
            )

    return h.hexdigest()


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


def validate_code_dependencies() -> None:
    if not NORMALIZATION_CORE.exists():
        raise RuntimeError(
            "Frozen normalization core missing."
        )

    if (
        sha256_file(
            NORMALIZATION_CORE
        )
        != EXPECTED_NORMALIZATION_SHA
    ):
        raise RuntimeError(
            "Frozen normalization core SHA mismatch."
        )

    if not AUDIT_TOOL.exists():
        raise RuntimeError(
            "Frozen collection audit tool missing."
        )

    if (
        sha256_file(
            AUDIT_TOOL
        )
        != EXPECTED_AUDIT_TOOL_SHA
    ):
        raise RuntimeError(
            "Frozen collection audit tool SHA mismatch."
        )


def validate_complete_freeze_obj(
    obj: dict,
) -> None:
    if not isinstance(
        obj,
        dict,
    ):
        raise ValueError(
            "Collection-complete freeze is not an object."
        )

    if (
        obj.get("artifact")
        !=
        "GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1"
    ):
        raise ValueError(
            "Unexpected collection-complete artifact name."
        )

    if (
        obj.get("status")
        != "FROZEN_COMPLETE"
    ):
        raise ValueError(
            "Collection-complete freeze status "
            "is not FROZEN_COMPLETE."
        )

    if (
        obj.get(
            "selected_dev_complete"
        )
        != 500
    ):
        raise ValueError(
            "selected_dev_complete is not 500."
        )

    if (
        obj.get(
            "selected_dev_target"
        )
        != 500
    ):
        raise ValueError(
            "selected_dev_target is not 500."
        )

    if (
        obj.get(
            "selected_dev_remaining"
        )
        != 0
    ):
        raise ValueError(
            "selected_dev_remaining is not zero."
        )

    selected = obj.get(
        "selected_manifest"
    )

    if not isinstance(
        selected,
        dict,
    ):
        raise ValueError(
            "Collection freeze selected_manifest missing."
        )

    if (
        selected.get("path")
        != str(
            SELECTED_MANIFEST
        )
    ):
        raise ValueError(
            "Collection freeze selected-manifest "
            "path mismatch."
        )

    if (
        selected.get("sha256")
        != EXPECTED_SELECTED_MANIFEST_SHA
    ):
        raise ValueError(
            "Collection freeze selected-manifest "
            "SHA mismatch."
        )

    audit = obj.get(
        "audit_tool"
    )

    if not isinstance(
        audit,
        dict,
    ):
        raise ValueError(
            "Collection freeze audit_tool missing."
        )

    if (
        audit.get("sha256")
        != EXPECTED_AUDIT_TOOL_SHA
    ):
        raise ValueError(
            "Collection freeze audit-tool SHA mismatch."
        )

    collection_files = obj.get(
        "collection_files"
    )

    if not isinstance(
        collection_files,
        dict,
    ):
        raise ValueError(
            "Collection freeze collection_files missing."
        )

    for key, path in [
        (
            "sc5_terminal",
            SC5_TERMINAL,
        ),
        (
            "vc_terminal",
            VC_TERMINAL,
        ),
    ]:
        info = collection_files.get(
            key
        )

        if not isinstance(
            info,
            dict,
        ):
            raise ValueError(
                f"Collection freeze missing {key} metadata."
            )

        if (
            info.get("path")
            != str(path)
        ):
            raise ValueError(
                f"Collection freeze {key} path mismatch."
            )

        digest = info.get(
            "sha256"
        )

        if (
            not isinstance(
                digest,
                str,
            )
            or len(digest) != 64
        ):
            raise ValueError(
                f"Collection freeze {key} SHA invalid."
            )

    safety = obj.get(
        "safety_state"
    )

    if not isinstance(
        safety,
        dict,
    ):
        raise ValueError(
            "Collection freeze safety_state missing."
        )

    if (
        safety.get(
            "ground_truth_accessed"
        )
        is not False
    ):
        raise ValueError(
            "Collection freeze unexpectedly reports "
            "ground-truth access."
        )

    if (
        safety.get(
            "calibration_eval_accessed"
        )
        is not False
    ):
        raise ValueError(
            "Collection freeze unexpectedly reports "
            "Calibration-EVAL access."
        )

    if (
        safety.get(
            "external_test_accessed"
        )
        is not False
    ):
        raise ValueError(
            "Collection freeze unexpectedly reports "
            "External-TEST access."
        )


def real_gate_status() -> dict:
    """
    Metadata-only gate.

    IMPORTANT:
    Does not open real SC5/VC terminal files,
    selected-manifest rows, canonical DEV manifest,
    or hidden DEV ground truth.
    """

    reasons = []

    if (
        os.environ.get(
            REAL_LOAD_ENV
        )
        != "YES"
    ):
        reasons.append(
            f"{REAL_LOAD_ENV} is not YES"
        )

    freeze_obj = None

    if not (
        COLLECTION_COMPLETE_FREEZE
        .exists()
    ):
        reasons.append(
            "DEV500 collection-complete freeze "
            "artifact does not exist"
        )
    else:
        try:
            freeze_obj = json.loads(
                COLLECTION_COMPLETE_FREEZE
                .read_text(
                    encoding="utf-8"
                )
            )

            validate_complete_freeze_obj(
                freeze_obj
            )

        except Exception as exc:
            reasons.append(
                "collection-complete freeze invalid: "
                + type(exc).__name__
                + ": "
                + str(exc)
            )

    return {
        "allowed":
            len(reasons) == 0,
        "reasons":
            reasons,
        "collection_freeze_valid":
            (
                freeze_obj
                is not None
                and len(reasons) == 0
            ),
    }


def read_csv(
    path: Path,
) -> list[dict]:
    with path.open(
        newline="",
        encoding="utf-8",
    ) as f:
        return list(
            csv.DictReader(f)
        )


def read_jsonl(
    path: Path,
) -> list[dict]:
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
                obj = json.loads(
                    line
                )
            except Exception as exc:
                raise ValueError(
                    f"{path}: malformed JSON "
                    f"line {lineno}"
                ) from exc

            if not isinstance(
                obj,
                dict,
            ):
                raise ValueError(
                    f"{path}: non-object JSON "
                    f"line {lineno}"
                )

            rows.append(
                obj
            )

    return rows


def validate_static_real_inputs() -> None:
    """
    Called ONLY AFTER the real gate is satisfied.

    This includes hashing hidden DEV ground truth,
    so it must never run during blocked preflight.
    """

    checks = [
        (
            SELECTED_MANIFEST,
            EXPECTED_SELECTED_MANIFEST_SHA,
            "DEV500 selected manifest",
        ),
        (
            CANONICAL_DEV_MANIFEST,
            EXPECTED_CANONICAL_DEV_MANIFEST_SHA,
            "canonical DEV manifest",
        ),
        (
            HIDDEN_DEV_GT,
            EXPECTED_HIDDEN_DEV_GT_SHA,
            "hidden DEV ground truth",
        ),
    ]

    for path, expected, name in checks:
        if not path.exists():
            raise RuntimeError(
                f"{name} missing."
            )

        actual = sha256_file(
            path
        )

        if actual != expected:
            raise RuntimeError(
                f"{name} SHA mismatch."
            )


def validate_collection_file_hashes(
    freeze_obj: dict,
) -> None:
    """
    Called ONLY AFTER the real gate is satisfied.
    """

    files = freeze_obj[
        "collection_files"
    ]

    for key, path in [
        (
            "sc5_terminal",
            SC5_TERMINAL,
        ),
        (
            "vc_terminal",
            VC_TERMINAL,
        ),
    ]:
        if not path.exists():
            raise RuntimeError(
                f"{key} collection file missing."
            )

        frozen_sha = files[
            key
        ][
            "sha256"
        ]

        actual_sha = sha256_file(
            path
        )

        if actual_sha != frozen_sha:
            raise RuntimeError(
                f"{key} changed after "
                "collection-complete freeze."
            )


def selected_ids_from_csv(
    rows: list[dict],
) -> list[str]:
    if len(rows) != 500:
        raise ValueError(
            "DEV500 selected manifest does not "
            "contain exactly 500 rows."
        )

    ids = []

    for row in rows:
        item_id = row.get(
            "item_id"
        )

        if (
            not isinstance(
                item_id,
                str,
            )
            or not item_id.startswith(
                "G6D-D-"
            )
        ):
            raise ValueError(
                "Invalid DEV500 selected item_id."
            )

        ids.append(
            item_id
        )

    if len(
        set(ids)
    ) != 500:
        raise ValueError(
            "DEV500 selected IDs are not unique."
        )

    return ids


def add_episode_metadata(
    normalized: dict,
    manifest_records: list[dict],
    selected_ids: list[str],
) -> dict:
    selected = set(
        selected_ids
    )

    manifest = {}

    for row in manifest_records:
        item_id = row.get(
            "item_id"
        )

        if item_id not in selected:
            continue

        if item_id in manifest:
            raise ValueError(
                f"Duplicate canonical manifest "
                f"row for {item_id}."
            )

        capture = row.get(
            "capture"
        )

        episode = row.get(
            "episode_start_utc"
        )

        if (
            not isinstance(
                capture,
                str,
            )
            or not capture
        ):
            raise ValueError(
                f"{item_id}: missing capture metadata."
            )

        if (
            not isinstance(
                episode,
                str,
            )
            or not episode
        ):
            raise ValueError(
                f"{item_id}: missing episode metadata."
            )

        manifest[
            item_id
        ] = {
            "capture":
                capture,
            "episode_start_utc":
                episode,
        }

    if (
        set(manifest)
        != selected
    ):
        missing = sorted(
            selected
            - set(manifest)
        )

        raise ValueError(
            "Canonical manifest does not cover "
            "DEV500 metadata exactly; missing="
            + repr(
                missing[:5]
            )
        )

    def enrich(
        rows: list[dict],
    ) -> list[dict]:
        out = []

        for row in rows:
            item_id = row[
                "item_id"
            ]

            meta = manifest[
                item_id
            ]

            enriched = dict(
                row
            )

            enriched[
                "capture"
            ] = meta[
                "capture"
            ]

            enriched[
                "episode_start_utc"
            ] = meta[
                "episode_start_utc"
            ]

            out.append(
                enriched
            )

        return out

    paired = enrich(
        normalized[
            "paired_rows"
        ]
    )

    sc5_all = enrich(
        normalized[
            "sc5_all_valid_rows"
        ]
    )

    selected_groups = {
        (
            meta["capture"],
            meta[
                "episode_start_utc"
            ],
        )
        for meta in manifest.values()
    }

    if len(
        selected_groups
    ) != 48:
        raise ValueError(
            "Frozen DEV500 metadata must contain "
            "exactly 48 episode groups."
        )

    captures = sorted({
        meta["capture"]
        for meta
        in manifest.values()
    })

    if captures != [
        "AmazonEcho-2023-02-21",
        "Windows7AD-2023-02-21",
    ]:
        raise ValueError(
            "Frozen DEV500 capture set mismatch."
        )

    result = dict(
        normalized
    )

    result[
        "paired_rows"
    ] = paired

    result[
        "sc5_all_valid_rows"
    ] = sc5_all

    result[
        "metadata_summary"
    ] = {
        "selected_episode_groups":
            48,
        "selected_captures":
            captures,
        "paired_episode_groups":
            len({
                (
                    row["capture"],
                    row[
                        "episode_start_utc"
                    ],
                )
                for row in paired
            }),
        "sc5_all_valid_episode_groups":
            len({
                (
                    row["capture"],
                    row[
                        "episode_start_utc"
                    ],
                )
                for row in sc5_all
            }),
    }

    return result


def load_real_dev_rows() -> dict:
    """
    REAL correctness-bearing load.

    This function MUST NOT be called unless real_gate_status()
    is allowed.

    It never references EVAL or External-TEST.
    """

    gate = real_gate_status()

    if not gate[
        "allowed"
    ]:
        raise RuntimeError(
            "REAL DEV LOAD BLOCKED: "
            + "; ".join(
                gate[
                    "reasons"
                ]
            )
        )

    validate_code_dependencies()

    # Only now may correctness-bearing DEV artifacts be touched.
    validate_static_real_inputs()

    freeze_obj = json.loads(
        COLLECTION_COMPLETE_FREEZE
        .read_text(
            encoding="utf-8"
        )
    )

    validate_complete_freeze_obj(
        freeze_obj
    )

    validate_collection_file_hashes(
        freeze_obj
    )

    selected_rows = read_csv(
        SELECTED_MANIFEST
    )

    selected_ids = (
        selected_ids_from_csv(
            selected_rows
        )
    )

    manifest_records = read_csv(
        CANONICAL_DEV_MANIFEST
    )

    sc5_records = read_jsonl(
        SC5_TERMINAL
    )

    vc_records = read_jsonl(
        VC_TERMINAL
    )

    gt_records = read_jsonl(
        HIDDEN_DEV_GT
    )

    norm = load_module(
        NORMALIZATION_CORE,
        "gate6d_real_loader_norm_v1",
    )

    normalized = (
        norm.normalize_dev500(
            selected_ids=
                selected_ids,
            manifest_records=
                manifest_records,
            sc5_records=
                sc5_records,
            vc_records=
                vc_records,
            gt_records=
                gt_records,
        )
    )

    enriched = (
        add_episode_metadata(
            normalized,
            manifest_records,
            selected_ids,
        )
    )

    return enriched


def synthetic_complete_freeze() -> dict:
    return {
        "artifact":
            "GATE6D_DEV500_COLLECTION_COMPLETE_FREEZE_V1",
        "status":
            "FROZEN_COMPLETE",
        "selected_dev_complete":
            500,
        "selected_dev_target":
            500,
        "selected_dev_remaining":
            0,

        "selected_manifest": {
            "path":
                str(
                    SELECTED_MANIFEST
                ),
            "sha256":
                EXPECTED_SELECTED_MANIFEST_SHA,
        },

        "audit_tool": {
            "path":
                str(
                    AUDIT_TOOL
                ),
            "sha256":
                EXPECTED_AUDIT_TOOL_SHA,
        },

        "collection_files": {
            "sc5_terminal": {
                "path":
                    str(
                        SC5_TERMINAL
                    ),
                "sha256":
                    "a" * 64,
            },
            "vc_terminal": {
                "path":
                    str(
                        VC_TERMINAL
                    ),
                "sha256":
                    "b" * 64,
            },
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


def synthetic_fixture_with_metadata(
    norm,
) -> dict:
    fixture = (
        norm.synthetic_fixture()
    )

    # Add frozen-shape episode metadata without
    # changing the normalization fixture semantics.
    for i, row in enumerate(
        fixture[
            "manifest_records"
        ]
    ):
        group = i % 48

        if group < 12:
            capture = (
                "AmazonEcho-2023-02-21"
            )
        else:
            capture = (
                "Windows7AD-2023-02-21"
            )

        row[
            "capture"
        ] = capture

        row[
            "episode_start_utc"
        ] = (
            f"2026-01-01T"
            f"{group:02d}:00:00Z"
        )

    return fixture


def expect_failure(
    name,
    fn,
    expected_text,
) -> dict:
    try:
        fn()

    except Exception as exc:
        text = str(
            exc
        )

        if (
            expected_text
            not in text
        ):
            raise AssertionError(
                f"{name}: wrong failure: {text}"
            )

        return {
            "test":
                name,
            "status":
                "PASS",
            "failure_detected":
                text,
        }

    raise AssertionError(
        f"{name}: expected failure "
        "was not detected."
    )


def synthetic_self_test() -> dict:
    validate_code_dependencies()

    norm = load_module(
        NORMALIZATION_CORE,
        "gate6d_loader_synthetic_norm_v1",
    )

    freeze = (
        synthetic_complete_freeze()
    )

    validate_complete_freeze_obj(
        freeze
    )

    fixture = (
        synthetic_fixture_with_metadata(
            norm
        )
    )

    normalized = (
        norm.normalize_dev500(
            **fixture
        )
    )

    enriched = (
        add_episode_metadata(
            normalized,
            fixture[
                "manifest_records"
            ],
            fixture[
                "selected_ids"
            ],
        )
    )

    paired = enriched[
        "paired_rows"
    ]

    sc5_all = enriched[
        "sc5_all_valid_rows"
    ]

    if len(
        paired
    ) != 488:
        raise AssertionError(
            "Expected synthetic paired n=488."
        )

    if len(
        sc5_all
    ) != 495:
        raise AssertionError(
            "Expected synthetic SC5-valid n=495."
        )

    if not all(
        "capture" in row
        and "episode_start_utc" in row
        for row in paired
    ):
        raise AssertionError(
            "Paired rows missing episode metadata."
        )

    if not all(
        "capture" in row
        and "episode_start_utc" in row
        for row in sc5_all
    ):
        raise AssertionError(
            "SC5 all-valid rows missing episode metadata."
        )

    bad_status = (
        synthetic_complete_freeze()
    )

    bad_status[
        "status"
    ] = "INCOMPLETE"

    status_test = expect_failure(
        "non_frozen_complete_status",
        lambda:
            validate_complete_freeze_obj(
                bad_status
            ),
        "not FROZEN_COMPLETE",
    )

    bad_count = (
        synthetic_complete_freeze()
    )

    bad_count[
        "selected_dev_complete"
    ] = 499

    count_test = expect_failure(
        "selected_complete_not_500",
        lambda:
            validate_complete_freeze_obj(
                bad_count
            ),
        "not 500",
    )

    bad_audit = (
        synthetic_complete_freeze()
    )

    bad_audit[
        "audit_tool"
    ][
        "sha256"
    ] = (
        "0" * 64
    )

    audit_test = expect_failure(
        "audit_tool_sha_mismatch",
        lambda:
            validate_complete_freeze_obj(
                bad_audit
            ),
        "audit-tool SHA mismatch",
    )

    # Current real gate must remain blocked at
    # the present incomplete collection state.
    gate = real_gate_status()

    if gate[
        "allowed"
    ]:
        raise AssertionError(
            "Real DEV gate unexpectedly opened."
        )

    return {
        "artifact":
            "GATE6D_REAL_DEV_LOADER_"
            "SYNTHETIC_SELF_TEST_V1",

        "status":
            "PASS",

        "frozen_dependencies": {
            "normalization_core_sha256":
                sha256_file(
                    NORMALIZATION_CORE
                ),
            "collection_audit_tool_sha256":
                sha256_file(
                    AUDIT_TOOL
                ),
        },

        "synthetic_normalization": {
            "selected_items":
                enriched[
                    "summary"
                ][
                    "selected_items"
                ],
            "sc5_valid_items":
                len(
                    sc5_all
                ),
            "paired_common_valid_items":
                len(
                    paired
                ),
            "selected_episode_groups":
                enriched[
                    "metadata_summary"
                ][
                    "selected_episode_groups"
                ],
            "paired_episode_groups":
                enriched[
                    "metadata_summary"
                ][
                    "paired_episode_groups"
                ],
            "selected_captures":
                enriched[
                    "metadata_summary"
                ][
                    "selected_captures"
                ],
            "episode_metadata_joined":
                True,
        },

        "complete_freeze_schema_validation":
            "PASS",

        "fail_closed_tests": [
            status_test,
            count_test,
            audit_test,
        ],

        "current_real_gate_allowed":
            False,
        "current_real_gate_reasons":
            gate[
                "reasons"
            ],

        "real_loader_function_present":
            True,
        "real_loader_called":
            False,

        "real_dev_outputs_read":
            False,
        "real_dev_ground_truth_read":
            False,
        "correctness_based_real_analysis":
            False,
        "calibration_eval_accessed":
            False,
        "external_test_accessed":
            False,
        "model_calls":
            0,
    }


def print_preflight() -> None:
    validate_code_dependencies()

    gate = real_gate_status()

    print(
        "=== GATE 6D REAL-DEV LOADER PRE-FLIGHT ==="
    )

    if gate[
        "allowed"
    ]:
        print(
            "REAL DEV LOAD GATE: READY"
        )
    else:
        print(
            "REAL DEV LOAD GATE: BLOCKED"
        )

        for reason in gate[
            "reasons"
        ]:
            print(
                "-",
                reason,
            )

    print()
    print(
        "SC5 terminal outputs opened: NO"
    )
    print(
        "VC terminal outputs opened: NO"
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


def attempt_real_load() -> None:
    gate = real_gate_status()

    print(
        "=== GATE 6D REAL-DEV LOAD ATTEMPT ==="
    )

    if not gate[
        "allowed"
    ]:
        print(
            "REAL DEV LOAD: BLOCKED"
        )

        for reason in gate[
            "reasons"
        ]:
            print(
                "-",
                reason,
            )

        print()
        print(
            "Real DEV outputs read: NO"
        )
        print(
            "Real DEV ground truth read: NO"
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
        return

    result = (
        load_real_dev_rows()
    )

    # This branch cannot be reached at the current
    # incomplete collection state. When it is eventually
    # reached, no estimator-selection decision is made here.
    print(
        "REAL DEV LOAD: SUCCESS"
    )
    print(
        "paired_common_valid_items:",
        len(
            result[
                "paired_rows"
            ]
        ),
    )
    print(
        "sc5_all_valid_items:",
        len(
            result[
                "sc5_all_valid_rows"
            ]
        ),
    )
    print(
        "selected_episode_groups:",
        result[
            "metadata_summary"
        ][
            "selected_episode_groups"
        ],
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


def main() -> None:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    parser.add_argument(
        "--real-preflight",
        action="store_true",
    )

    parser.add_argument(
        "--real-load",
        action="store_true",
    )

    args = parser.parse_args()

    modes = sum([
        args.self_test,
        args.real_preflight,
        args.real_load,
    ])

    if modes != 1:
        print(
            "BLOCKED: choose exactly one of "
            "--self-test, --real-preflight, "
            "or --real-load."
        )
        return

    if args.self_test:
        result = (
            synthetic_self_test()
        )

        SELFTEST_OUT.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        SELFTEST_OUT.write_text(
            json.dumps(
                result,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        print(
            "=== GATE 6D REAL-DEV LOADER "
            "SYNTHETIC TEST ==="
        )
        print(
            "status:",
            result[
                "status"
            ],
        )
        print(
            "selected_items:",
            result[
                "synthetic_normalization"
            ][
                "selected_items"
            ],
        )
        print(
            "sc5_valid_items:",
            result[
                "synthetic_normalization"
            ][
                "sc5_valid_items"
            ],
        )
        print(
            "paired_common_valid_items:",
            result[
                "synthetic_normalization"
            ][
                "paired_common_valid_items"
            ],
        )
        print(
            "selected_episode_groups:",
            result[
                "synthetic_normalization"
            ][
                "selected_episode_groups"
            ],
        )
        print(
            "episode_metadata_joined:",
            result[
                "synthetic_normalization"
            ][
                "episode_metadata_joined"
            ],
        )
        print(
            "complete_freeze_schema_validation:",
            result[
                "complete_freeze_schema_validation"
            ],
        )
        print(
            "fail_closed_tests:",
            len(
                result[
                    "fail_closed_tests"
                ]
            ),
            "PASS",
        )
        print(
            "current_real_gate_allowed:",
            result[
                "current_real_gate_allowed"
            ],
        )
        print(
            "real_loader_called: False"
        )
        print(
            "real_dev_outputs_read: False"
        )
        print(
            "real_dev_ground_truth_read: False"
        )
        print(
            "correctness_based_real_analysis: False"
        )
        print(
            "calibration_eval_accessed: False"
        )
        print(
            "external_test_accessed: False"
        )
        print(
            "model_calls: 0"
        )
        return

    if args.real_preflight:
        print_preflight()
        return

    attempt_real_load()


if __name__ == "__main__":
    main()
