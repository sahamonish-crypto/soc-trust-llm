#!/usr/bin/env python3

"""
Gate 6D secondary uncertainty/sensitivity core V1.

SYNTHETIC-ONLY in V1.

Implements the prospectively frozen secondary protocol:
- 10,000 capture-stratified episode-cluster bootstrap replicates;
- deterministic frozen seed;
- 95% percentile CIs;
- same cluster draws across methods;
- no silent redraw of undefined metrics;
- paired metric differences;
- ground-truth-class sensitivity;
- capture sensitivity;
- leave-one-episode-out influence.

This V1 does NOT:
- read real DEV terminal outputs;
- read hidden DEV ground truth;
- read Calibration-EVAL;
- read External-TEST;
- refit estimators/calibrators inside bootstrap;
- alter primary method selection;
- make model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
)


PROTOCOL = Path(
    "benchmarks/gate6d/"
    "GATE6D_SECONDARY_UNCERTAINTY_SENSITIVITY_PROTOCOL_V1.json"
)

NORMALIZATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_dev_normalization_core_v1.py"
)

CALIBRATION_CORE = Path(
    "scripts/gate6/"
    "gate6d_calibration_analysis_core.py"
)

EXPECTED_PROTOCOL_SHA = (
    "6859c2ac8df4b36d392ec820461401b6"
    "ea5610dbc20db9dd24f3c59a460d4a33"
)

EXPECTED_NORMALIZATION_SHA = (
    "7983ed4320908fd87913bc7a3b031133"
    "50763efb0fed1d8d00ba675da81e7ba0"
)

EXPECTED_CALIBRATION_SHA = (
    "47a03118614e68c000101047c680b3992"
    "9f1355ab9a8f1ba1565abcb81d52eba"
)

BOOTSTRAP_REPLICATES = 10000
CI_LO = 0.025
CI_HI = 0.975
MIN_VALID = 9500

SEED_NAMESPACE = "GATE6D_SECONDARY_BOOTSTRAP_V1"
SEED_SHA256 = (
    "bc9ed85d9834fe9da0849c7c6f19f4e"
    "202eba21b59ab510b51e1ae0510ca04b6"
)
SEED_UINT63 = 4368166585093127837

ALLOWED_GT = {
    "ESCALATE",
    "DO_NOT_ESCALATE",
}

OUT = Path(
    "benchmarks/gate6d/"
    "secondary_uncertainty_v1/"
    "synthetic_self_test.json"
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


def verify_frozen_inputs() -> dict:
    checks = {
        "protocol": (
            PROTOCOL,
            EXPECTED_PROTOCOL_SHA,
        ),
        "normalization_core": (
            NORMALIZATION_CORE,
            EXPECTED_NORMALIZATION_SHA,
        ),
        "calibration_core": (
            CALIBRATION_CORE,
            EXPECTED_CALIBRATION_SHA,
        ),
    }

    actual = {}

    for name, (
        path,
        expected,
    ) in checks.items():

        if not path.exists():
            raise RuntimeError(
                f"Missing frozen dependency: {path}"
            )

        digest = sha256_file(path)

        if digest != expected:
            raise RuntimeError(
                f"{name} SHA mismatch: "
                f"expected {expected}, got {digest}"
            )

        actual[name] = digest

    ns = SEED_NAMESPACE.encode(
        "utf-8"
    )

    digest = hashlib.sha256(
        ns
    ).digest()

    seed = (
        int.from_bytes(
            digest[:8],
            "big",
            signed=False,
        )
        & ((1 << 63) - 1)
    )

    if seed == 0:
        seed = 1

    if (
        hashlib.sha256(ns).hexdigest()
        != SEED_SHA256
    ):
        raise RuntimeError(
            "Frozen seed namespace SHA mismatch."
        )

    if seed != SEED_UINT63:
        raise RuntimeError(
            "Frozen uint63 seed mismatch."
        )

    protocol = json.loads(
        PROTOCOL.read_text(
            encoding="utf-8"
        )
    )

    b = protocol["bootstrap"]

    assert (
        b["bootstrap_replicates"]
        == BOOTSTRAP_REPLICATES
    )
    assert (
        b["confidence_interval"]
        == "percentile"
    )
    assert b["lower_quantile"] == CI_LO
    assert b["upper_quantile"] == CI_HI
    assert (
        b[
            "undefined_metric_replicate"
        ][
            "minimum_valid_replicates_when_B_10000"
        ]
        == MIN_VALID
    )

    return actual


def metric_bundle(
    y,
    p,
    weights=None,
) -> dict:
    y = np.asarray(
        y,
        dtype=float,
    )

    p = np.asarray(
        p,
        dtype=float,
    )

    if y.ndim != 1 or p.ndim != 1:
        raise ValueError(
            "y and p must be 1-D."
        )

    if len(y) != len(p):
        raise ValueError(
            "y and p length mismatch."
        )

    if len(y) == 0:
        raise ValueError(
            "Empty metric input."
        )

    if np.any(
        (p < 0.0)
        | (p > 1.0)
    ):
        raise ValueError(
            "Probability outside [0,1]."
        )

    if not np.all(
        np.isin(
            y,
            [0.0, 1.0],
        )
    ):
        raise ValueError(
            "Correctness must be binary."
        )

    if weights is None:
        w = np.ones(
            len(y),
            dtype=float,
        )
    else:
        w = np.asarray(
            weights,
            dtype=float,
        )

        if len(w) != len(y):
            raise ValueError(
                "Weight length mismatch."
            )

        if np.any(
            ~np.isfinite(w)
        ):
            raise ValueError(
                "Non-finite weight."
            )

        if np.any(w < 0):
            raise ValueError(
                "Negative weight."
            )

    total = float(
        np.sum(w)
    )

    if total <= 0:
        raise ValueError(
            "Zero total bootstrap weight."
        )

    active = w > 0

    ya = y[active]
    pa = p[active]
    wa = w[active]

    brier = float(
        np.average(
            (pa - ya) ** 2,
            weights=wa,
        )
    )

    weighted_correct = float(
        np.sum(
            wa * ya
        )
    )

    weighted_incorrect = float(
        np.sum(
            wa * (1.0 - ya)
        )
    )

    if (
        weighted_correct <= 0
        or weighted_incorrect <= 0
    ):
        auroc = math.nan
    else:
        auroc = float(
            roc_auc_score(
                ya,
                pa,
                sample_weight=wa,
            )
        )

    incorrect = (
        1.0 - ya
    )

    incorrect_score = (
        1.0 - pa
    )

    if weighted_incorrect <= 0:
        auprc_incorrect = math.nan
    else:
        auprc_incorrect = float(
            average_precision_score(
                incorrect,
                incorrect_score,
                sample_weight=wa,
            )
        )

    ece = 0.0

    edges = np.linspace(
        0.0,
        1.0,
        11,
    )

    for i in range(10):
        lo = edges[i]
        hi = edges[i + 1]

        if i == 9:
            mask = (
                (pa >= lo)
                & (pa <= hi)
            )
        else:
            mask = (
                (pa >= lo)
                & (pa < hi)
            )

        if not np.any(mask):
            continue

        bin_w = wa[mask]
        bin_total = float(
            np.sum(bin_w)
        )

        mean_conf = float(
            np.average(
                pa[mask],
                weights=bin_w,
            )
        )

        accuracy = float(
            np.average(
                ya[mask],
                weights=bin_w,
            )
        )

        ece += (
            bin_total
            / total
        ) * abs(
            mean_conf
            - accuracy
        )

    return {
        "brier":
            brier,
        "auroc_correct":
            auroc,
        "auprc_incorrect":
            auprc_incorrect,
        "ece10":
            float(ece),
    }


def validate_rows(
    rows: list[dict],
) -> None:
    if not rows:
        raise ValueError(
            "No rows supplied."
        )

    seen = set()

    for row in rows:
        item_id = row.get(
            "item_id"
        )

        if not isinstance(
            item_id,
            str,
        ):
            raise ValueError(
                "Missing item_id."
            )

        if item_id in seen:
            raise ValueError(
                f"Duplicate item_id: {item_id}"
            )

        seen.add(item_id)

        capture = row.get(
            "capture"
        )

        episode = row.get(
            "episode_start_utc"
        )

        if not isinstance(
            capture,
            str,
        ) or not capture:
            raise ValueError(
                f"{item_id}: invalid capture"
            )

        if not isinstance(
            episode,
            str,
        ) or not episode:
            raise ValueError(
                f"{item_id}: invalid episode_start_utc"
            )

        if (
            row.get("ground_truth")
            not in ALLOWED_GT
        ):
            raise ValueError(
                f"{item_id}: invalid ground_truth"
            )

        if row.get(
            "correctness"
        ) not in {0, 1}:
            raise ValueError(
                f"{item_id}: invalid correctness"
            )


def build_cluster_index(
    rows: list[dict],
) -> dict:
    validate_rows(rows)

    groups = sorted({
        (
            row["capture"],
            row["episode_start_utc"],
        )
        for row in rows
    })

    group_to_index = {
        group: i
        for i, group
        in enumerate(groups)
    }

    row_group = np.asarray(
        [
            group_to_index[
                (
                    row["capture"],
                    row[
                        "episode_start_utc"
                    ],
                )
            ]
            for row in rows
        ],
        dtype=int,
    )

    captures = sorted({
        capture
        for capture, _
        in groups
    })

    capture_groups = {}

    for capture in captures:
        capture_groups[
            capture
        ] = [
            i
            for i, group
            in enumerate(groups)
            if group[0] == capture
        ]

    return {
        "groups":
            groups,
        "row_group":
            row_group,
        "capture_groups":
            capture_groups,
    }


def generate_draw_plan(
    rows: list[dict],
    *,
    B: int = BOOTSTRAP_REPLICATES,
    seed: int = SEED_UINT63,
) -> dict:
    structure = build_cluster_index(
        rows
    )

    groups = structure[
        "groups"
    ]

    capture_groups = structure[
        "capture_groups"
    ]

    rng = np.random.default_rng(
        seed
    )

    counts = np.zeros(
        (
            B,
            len(groups),
        ),
        dtype=np.int16,
    )

    for capture in sorted(
        capture_groups
    ):
        indices = capture_groups[
            capture
        ]

        k = len(indices)

        if k < 1:
            raise ValueError(
                f"No groups for capture {capture}"
            )

        local = rng.multinomial(
            k,
            np.full(
                k,
                1.0 / k,
            ),
            size=B,
        )

        counts[
            :,
            indices,
        ] = local.astype(
            np.int16
        )

    # Every replicate must contain exactly the
    # original number of clusters within each capture.
    for capture, indices in (
        capture_groups.items()
    ):
        observed = np.sum(
            counts[
                :,
                indices,
            ],
            axis=1,
        )

        if not np.all(
            observed
            == len(indices)
        ):
            raise AssertionError(
                "Capture-stratified draw count mismatch."
            )

    draw_hash = hashlib.sha256(
        counts.tobytes()
    ).hexdigest()

    return {
        "counts":
            counts,
        "draw_plan_sha256":
            draw_hash,
        "groups":
            groups,
        "row_group":
            structure[
                "row_group"
            ],
        "capture_groups":
            capture_groups,
    }


def bootstrap_metric_arrays(
    rows: list[dict],
    probabilities,
    draw_plan: dict,
) -> dict:
    p = np.asarray(
        probabilities,
        dtype=float,
    )

    if len(p) != len(rows):
        raise ValueError(
            "Probability length mismatch."
        )

    y = np.asarray(
        [
            row["correctness"]
            for row in rows
        ],
        dtype=float,
    )

    counts = draw_plan[
        "counts"
    ]

    row_group = draw_plan[
        "row_group"
    ]

    arrays = {
        "brier":
            np.full(
                len(counts),
                np.nan,
            ),
        "auroc_correct":
            np.full(
                len(counts),
                np.nan,
            ),
        "auprc_incorrect":
            np.full(
                len(counts),
                np.nan,
            ),
        "ece10":
            np.full(
                len(counts),
                np.nan,
            ),
    }

    for b in range(
        len(counts)
    ):
        weights = counts[
            b,
            row_group,
        ].astype(
            float
        )

        m = metric_bundle(
            y,
            p,
            weights,
        )

        for key in arrays:
            arrays[key][b] = (
                m[key]
            )

    return arrays


def percentile_summary(
    values,
) -> dict:
    a = np.asarray(
        values,
        dtype=float,
    )

    valid = a[
        np.isfinite(a)
    ]

    n_valid = int(
        len(valid)
    )

    n_total = int(
        len(a)
    )

    result = {
        "total_replicates":
            n_total,
        "valid_replicates":
            n_valid,
        "undefined_replicates":
            n_total - n_valid,
        "minimum_valid_required":
            MIN_VALID,
    }

    if n_valid < MIN_VALID:
        result.update({
            "ci_available":
                False,
            "lower":
                None,
            "upper":
                None,
            "reason":
                "VALID_REPLICATES_BELOW_FROZEN_THRESHOLD",
        })

        return result

    lo, hi = np.quantile(
        valid,
        [
            CI_LO,
            CI_HI,
        ],
        method="linear",
    )

    result.update({
        "ci_available":
            True,
        "lower":
            float(lo),
        "upper":
            float(hi),
        "reason":
            "AVAILABLE",
    })

    return result


def uncertainty_summary(
    rows,
    probabilities,
    draw_plan,
) -> dict:
    y = np.asarray(
        [
            row["correctness"]
            for row in rows
        ],
        dtype=float,
    )

    p = np.asarray(
        probabilities,
        dtype=float,
    )

    point = metric_bundle(
        y,
        p,
    )

    arrays = (
        bootstrap_metric_arrays(
            rows,
            p,
            draw_plan,
        )
    )

    return {
        "point_estimate":
            point,
        "bootstrap_ci": {
            key:
                percentile_summary(
                    values
                )
            for key, values
            in arrays.items()
        },
        "_bootstrap_arrays":
            arrays,
    }


def paired_difference_summary(
    arrays_a: dict,
    arrays_b: dict,
) -> dict:
    """
    Difference is B - A.

    For intended real use:
      A = SC5_AGREEMENT
      B = VC_SELF_EVAL

    Same bootstrap draws must have generated both.
    """
    out = {}

    for metric in [
        "brier",
        "auroc_correct",
        "auprc_incorrect",
        "ece10",
    ]:
        a = np.asarray(
            arrays_a[metric],
            dtype=float,
        )

        b = np.asarray(
            arrays_b[metric],
            dtype=float,
        )

        if len(a) != len(b):
            raise ValueError(
                "Paired bootstrap array length mismatch."
            )

        diff = b - a

        out[metric] = (
            percentile_summary(
                diff
            )
        )

        finite = diff[
            np.isfinite(diff)
        ]

        out[metric][
            "mean_bootstrap_difference"
        ] = (
            float(
                np.mean(finite)
            )
            if len(finite)
            else None
        )

    return out


def subgroup_point_summary(
    rows,
    probabilities,
    field,
) -> dict:
    p = np.asarray(
        probabilities,
        dtype=float,
    )

    values = sorted({
        row[field]
        for row in rows
    })

    out = {}

    for value in values:
        mask = np.asarray(
            [
                row[field] == value
                for row in rows
            ],
            dtype=bool,
        )

        y = np.asarray(
            [
                row["correctness"]
                for row in rows
            ],
            dtype=float,
        )[mask]

        pp = p[mask]

        out[str(value)] = {
            "n":
                int(mask.sum()),
            "metrics":
                metric_bundle(
                    y,
                    pp,
                ),
        }

    return out


def leave_one_episode_out(
    rows,
    probabilities,
) -> dict:
    p = np.asarray(
        probabilities,
        dtype=float,
    )

    y = np.asarray(
        [
            row["correctness"]
            for row in rows
        ],
        dtype=float,
    )

    full = metric_bundle(
        y,
        p,
    )

    groups = sorted({
        (
            row["capture"],
            row[
                "episode_start_utc"
            ],
        )
        for row in rows
    })

    per_group = []

    for capture, episode in groups:
        keep = np.asarray(
            [
                not (
                    row["capture"]
                    == capture
                    and row[
                        "episode_start_utc"
                    ]
                    == episode
                )
                for row in rows
            ],
            dtype=bool,
        )

        metrics = metric_bundle(
            y[keep],
            p[keep],
        )

        per_group.append({
            "capture":
                capture,
            "episode_start_utc":
                episode,
            "metrics":
                metrics,
        })

    summary = {}

    for metric in [
        "brier",
        "auroc_correct",
        "auprc_incorrect",
        "ece10",
    ]:
        candidates = [
            x
            for x in per_group
            if math.isfinite(
                x["metrics"][metric]
            )
        ]

        if not candidates:
            summary[metric] = {
                "available":
                    False,
            }
            continue

        min_row = min(
            candidates,
            key=lambda x:
                x["metrics"][metric],
        )

        max_row = max(
            candidates,
            key=lambda x:
                x["metrics"][metric],
        )

        influence_row = max(
            candidates,
            key=lambda x:
                abs(
                    x["metrics"][metric]
                    - full[metric]
                ),
        )

        summary[metric] = {
            "available":
                True,
            "full_value":
                float(
                    full[metric]
                ),
            "minimum_value":
                float(
                    min_row[
                        "metrics"
                    ][metric]
                ),
            "maximum_value":
                float(
                    max_row[
                        "metrics"
                    ][metric]
                ),
            "maximum_absolute_deviation":
                float(
                    abs(
                        influence_row[
                            "metrics"
                        ][metric]
                        - full[metric]
                    )
                ),
            "max_influence_capture":
                influence_row[
                    "capture"
                ],
            "max_influence_episode_start_utc":
                influence_row[
                    "episode_start_utc"
                ],
        }

    return {
        "episode_count":
            len(groups),
        "metrics":
            summary,
    }


def synthetic_rows() -> list[dict]:
    """
    488 synthetic paired-common-valid observations,
    48 episode clusters, two capture strata.

    No real Gate 6D data are read.
    """
    captures = (
        [
            "AmazonEcho-2023-02-21"
        ] * 12
        + [
            "Windows7AD-2023-02-21"
        ] * 36
    )

    episodes = []

    for i, capture in enumerate(
        captures,
        start=1,
    ):
        episodes.append(
            (
                capture,
                f"2026-01-{((i - 1) % 28) + 1:02d}"
                f"T{((i - 1) % 24):02d}:"
                f"{((i * 7) % 60):02d}:00Z"
                f"-E{i:02d}"
            )
        )

    rows = []

    for i in range(
        488
    ):
        capture, episode = (
            episodes[
                i % 48
            ]
        )

        ground_truth = (
            "ESCALATE"
            if i % 4 == 0
            else "DO_NOT_ESCALATE"
        )

        correctness = (
            0
            if (
                i % 5 == 0
                or i % 17 == 0
            )
            else 1
        )

        rows.append({
            "item_id":
                f"SYN-G6D-{i + 1:04d}",
            "capture":
                capture,
            "episode_start_utc":
                episode,
            "ground_truth":
                ground_truth,
            "correctness":
                correctness,
        })

    return rows


def synthetic_probabilities(
    rows,
) -> dict:
    n = len(rows)

    y = np.asarray(
        [
            row["correctness"]
            for row in rows
        ],
        dtype=float,
    )

    index = np.arange(
        n,
        dtype=float,
    )

    # SC5-like discrete confidence.
    sc5 = np.asarray(
        [
            [0.6, 0.8, 1.0][
                i % 3
            ]
            for i in range(n)
        ],
        dtype=float,
    )

    # VC-like synthetic confidence with useful,
    # but intentionally imperfect, discrimination.
    vc = (
        0.48
        + 0.28 * y
        + 0.16
        * np.sin(
            index * 0.71
        )
    )

    vc = np.clip(
        vc,
        0.02,
        0.98,
    )

    prevalence = float(
        np.mean(y)
    )

    constant = np.full(
        n,
        prevalence,
        dtype=float,
    )

    return {
        "SC5_SYNTHETIC":
            sc5,
        "VC_SYNTHETIC":
            vc,
        "CONSTANT_SYNTHETIC":
            constant,
    }


def expect_failure(
    name,
    fn,
    expected_text,
) -> dict:
    try:
        fn()
    except Exception as exc:
        text = str(exc)

        if expected_text not in text:
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
        f"{name}: expected failure not detected."
    )


def synthetic_self_test() -> dict:
    frozen = verify_frozen_inputs()

    rows = synthetic_rows()

    validate_rows(rows)

    structure = build_cluster_index(
        rows
    )

    if len(
        structure["groups"]
    ) != 48:
        raise AssertionError(
            "Expected exactly 48 synthetic episode groups."
        )

    capture_counts = {
        capture:
            len(groups)
        for capture, groups
        in structure[
            "capture_groups"
        ].items()
    }

    expected_capture_counts = {
        "AmazonEcho-2023-02-21":
            12,
        "Windows7AD-2023-02-21":
            36,
    }

    if (
        capture_counts
        != expected_capture_counts
    ):
        raise AssertionError(
            "Synthetic capture group counts changed."
        )

    plan1 = generate_draw_plan(
        rows
    )

    plan2 = generate_draw_plan(
        rows
    )

    if (
        plan1[
            "draw_plan_sha256"
        ]
        != plan2[
            "draw_plan_sha256"
        ]
    ):
        raise AssertionError(
            "Bootstrap draw plan is not deterministic."
        )

    if not np.array_equal(
        plan1["counts"],
        plan2["counts"],
    ):
        raise AssertionError(
            "Bootstrap draw matrices differ."
        )

    probs = synthetic_probabilities(
        rows
    )

    summaries = {}

    arrays = {}

    for name, p in probs.items():
        result = uncertainty_summary(
            rows,
            p,
            plan1,
        )

        arrays[name] = result.pop(
            "_bootstrap_arrays"
        )

        summaries[name] = result

    paired = paired_difference_summary(
        arrays[
            "SC5_SYNTHETIC"
        ],
        arrays[
            "VC_SYNTHETIC"
        ],
    )

    class_sensitivity = (
        subgroup_point_summary(
            rows,
            probs[
                "VC_SYNTHETIC"
            ],
            "ground_truth",
        )
    )

    capture_sensitivity = (
        subgroup_point_summary(
            rows,
            probs[
                "VC_SYNTHETIC"
            ],
            "capture",
        )
    )

    episode_influence = (
        leave_one_episode_out(
            rows,
            probs[
                "VC_SYNTHETIC"
            ],
        )
    )

    for method in summaries.values():
        for metric, ci in (
            method[
                "bootstrap_ci"
            ].items()
        ):
            if not ci[
                "ci_available"
            ]:
                raise AssertionError(
                    f"Synthetic CI unavailable for {metric}"
                )

            if (
                ci["valid_replicates"]
                < MIN_VALID
            ):
                raise AssertionError(
                    "Valid replicate threshold violated."
                )

    for metric, ci in paired.items():
        if not ci[
            "ci_available"
        ]:
            raise AssertionError(
                f"Paired CI unavailable for {metric}"
            )

    if (
        set(
            class_sensitivity
        )
        != ALLOWED_GT
    ):
        raise AssertionError(
            "Ground-truth-class sensitivity labels changed."
        )

    if (
        len(
            capture_sensitivity
        )
        != 2
    ):
        raise AssertionError(
            "Expected two synthetic capture summaries."
        )

    if (
        episode_influence[
            "episode_count"
        ]
        != 48
    ):
        raise AssertionError(
            "Expected 48 leave-one-episode-out analyses."
        )

    missing_episode_rows = [
        dict(row)
        for row in rows
    ]

    missing_episode_rows[
        0
    ]["episode_start_utc"] = ""

    failure_missing_episode = (
        expect_failure(
            "missing_episode_metadata",
            lambda:
                validate_rows(
                    missing_episode_rows
                ),
            "invalid episode_start_utc",
        )
    )

    duplicate_rows = (
        [
            dict(row)
            for row in rows
        ]
        + [
            dict(rows[0])
        ]
    )

    failure_duplicate = (
        expect_failure(
            "duplicate_item_id",
            lambda:
                validate_rows(
                    duplicate_rows
                ),
            "Duplicate item_id",
        )
    )

    result = {
        "artifact":
            "GATE6D_SECONDARY_UNCERTAINTY_"
            "SYNTHETIC_SELF_TEST_V1",

        "status":
            "PASS",

        "frozen_dependencies":
            frozen,

        "bootstrap_protocol": {
            "replicates":
                BOOTSTRAP_REPLICATES,
            "ci":
                "95_PERCENT_PERCENTILE",
            "minimum_valid_replicates":
                MIN_VALID,
            "seed_namespace":
                SEED_NAMESPACE,
            "seed_uint63":
                SEED_UINT63,
            "capture_stratified":
                True,
            "episode_cluster_resampling":
                True,
            "row_level_resampling":
                False,
            "calibrator_refit_inside_bootstrap":
                False,
        },

        "synthetic_structure": {
            "rows":
                len(rows),
            "episode_groups":
                len(
                    structure[
                        "groups"
                    ]
                ),
            "capture_episode_group_counts":
                capture_counts,
        },

        "determinism": {
            "draw_plan_sha256":
                plan1[
                    "draw_plan_sha256"
                ],
            "repeated_generation_identical":
                True,
            "same_draw_plan_reused_across_methods":
                True,
        },

        "method_uncertainty":
            summaries,

        "paired_difference": {
            "definition":
                "VC_SYNTHETIC - SC5_SYNTHETIC",
            "metrics":
                paired,
            "can_change_primary_winner":
                False,
        },

        "ground_truth_class_sensitivity":
            class_sensitivity,

        "capture_sensitivity":
            capture_sensitivity,

        "episode_influence":
            episode_influence,

        "fail_closed_tests": [
            failure_missing_episode,
            failure_duplicate,
        ],

        "interpretation": {
            "synthetic_results_have_real_"
            "scientific_meaning":
                False,
            "secondary_analysis_can_change_"
            "primary_winner":
                False,
            "formal_null_hypothesis_test":
                False,
        },

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
            "BLOCKED: V1 permits --self-test only."
        )
        print(
            "Real secondary uncertainty analysis "
            "was NOT run."
        )
        return

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
        "=== GATE 6D SECONDARY UNCERTAINTY "
        "SYNTHETIC TEST ==="
    )
    print(
        "status:",
        result["status"],
    )
    print(
        "bootstrap_replicates:",
        result[
            "bootstrap_protocol"
        ]["replicates"],
    )
    print(
        "synthetic_rows:",
        result[
            "synthetic_structure"
        ]["rows"],
    )
    print(
        "episode_groups:",
        result[
            "synthetic_structure"
        ]["episode_groups"],
    )
    print(
        "capture_episode_groups:",
        result[
            "synthetic_structure"
        ][
            "capture_episode_group_counts"
        ],
    )
    print(
        "draw_plan_sha256:",
        result[
            "determinism"
        ]["draw_plan_sha256"],
    )
    print(
        "draw_plan_reproducible:",
        result[
            "determinism"
        ][
            "repeated_generation_identical"
        ],
    )

    for method in [
        "SC5_SYNTHETIC",
        "VC_SYNTHETIC",
        "CONSTANT_SYNTHETIC",
    ]:
        ci = (
            result[
                "method_uncertainty"
            ][method][
                "bootstrap_ci"
            ]
        )

        print(
            f"{method}_valid_Brier_replicates:",
            ci["brier"][
                "valid_replicates"
            ],
        )

        print(
            f"{method}_valid_AUROC_replicates:",
            ci[
                "auroc_correct"
            ][
                "valid_replicates"
            ],
        )

        print(
            f"{method}_valid_AUPRC_replicates:",
            ci[
                "auprc_incorrect"
            ][
                "valid_replicates"
            ],
        )

    print(
        "paired_difference_CIs_available:",
        all(
            x["ci_available"]
            for x in result[
                "paired_difference"
            ]["metrics"].values()
        ),
    )
    print(
        "ground_truth_classes:",
        sorted(
            result[
                "ground_truth_class_sensitivity"
            ]
        ),
    )
    print(
        "capture_summaries:",
        len(
            result[
                "capture_sensitivity"
            ]
        ),
    )
    print(
        "leave_one_episode_out_count:",
        result[
            "episode_influence"
        ]["episode_count"],
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
        "secondary_analysis_can_change_winner: False"
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


if __name__ == "__main__":
    main()
