#!/usr/bin/env python3

"""
Gate 6D DEV500 normalization/join core V1.

Current scope:
- pure normalization/validation logic;
- deterministic synthetic self-test only;
- does NOT open real DEV collection files;
- does NOT open hidden DEV ground truth;
- does NOT access Calibration-EVAL;
- does NOT access External-TEST.

Primary comparison follows the frozen paired-common-valid policy.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
import re
from pathlib import Path


ALLOWED_LABELS = {
    "ESCALATE",
    "DO_NOT_ESCALATE",
}

EXPECTED_FOLD_COUNTS = {
    1: 97,
    2: 101,
    3: 102,
    4: 98,
    5: 102,
}

ALLOWED_SC5_AGREEMENT = {
    0.6,
    0.8,
    1.0,
}


def unique_map(
    records,
    *,
    source_name,
    selected_ids=None,
):
    out = {}

    for r in records:
        item_id = r.get("item_id")

        if not isinstance(item_id, str):
            raise ValueError(
                f"{source_name}: missing/invalid item_id"
            )

        if (
            selected_ids is not None
            and item_id not in selected_ids
        ):
            # Historical nonselected records are permitted
            # and ignored.
            continue

        if item_id in out:
            raise ValueError(
                f"{source_name}: duplicate terminal/item "
                f"record for {item_id}"
            )

        out[item_id] = r

    return out


def validate_selected_ids(selected_ids):
    ids = list(selected_ids)

    if len(ids) != 500:
        raise ValueError(
            f"Expected exactly 500 selected IDs, got {len(ids)}"
        )

    if len(set(ids)) != 500:
        raise ValueError(
            "Selected DEV500 IDs are not unique."
        )

    if not all(
        isinstance(x, str)
        and x.startswith("G6D-D-")
        for x in ids
    ):
        raise ValueError(
            "Selected IDs contain non-DEV identifier."
        )

    return set(ids)


def validate_manifest(
    selected,
    manifest_records,
):
    manifest = unique_map(
        manifest_records,
        source_name="manifest",
        selected_ids=selected,
    )

    if set(manifest) != selected:
        missing = sorted(
            selected - set(manifest)
        )

        raise ValueError(
            "Manifest does not cover DEV500 exactly; "
            f"missing={missing[:5]}"
        )

    folds = Counter()

    for item_id, row in manifest.items():
        try:
            fold = int(row["cv_fold"])
        except Exception as exc:
            raise ValueError(
                f"Manifest invalid cv_fold for {item_id}"
            ) from exc

        if fold not in {1, 2, 3, 4, 5}:
            raise ValueError(
                f"Manifest invalid fold {fold} for {item_id}"
            )

        folds[fold] += 1

    if dict(sorted(folds.items())) != EXPECTED_FOLD_COUNTS:
        raise ValueError(
            "Frozen DEV500 fold counts mismatch: "
            f"{dict(sorted(folds.items()))}"
        )

    return manifest


def validate_ground_truth(
    selected,
    gt_records,
):
    gt = unique_map(
        gt_records,
        source_name="ground_truth",
        selected_ids=selected,
    )

    if set(gt) != selected:
        raise ValueError(
            "Ground truth does not cover DEV500 exactly."
        )

    for item_id, row in gt.items():
        label = row.get("ground_truth")

        if label not in ALLOWED_LABELS:
            raise ValueError(
                f"Invalid ground truth for {item_id}: "
                f"{label!r}"
            )

    return gt


def validate_sc5_valid_record(
    item_id,
    row,
):
    outputs = row.get("outputs")

    if (
        not isinstance(outputs, list)
        or len(outputs) != 5
    ):
        raise ValueError(
            f"{item_id}: valid SC5 record must "
            "contain exactly five outputs."
        )

    if any(
        x not in ALLOWED_LABELS
        for x in outputs
    ):
        raise ValueError(
            f"{item_id}: valid SC5 outputs contain "
            "non-exact label."
        )

    counts = Counter(outputs)

    majority, majority_n = max(
        counts.items(),
        key=lambda kv: (
            kv[1],
            kv[0],
        ),
    )

    if majority_n < 3:
        raise ValueError(
            f"{item_id}: impossible SC5 majority."
        )

    expected_agreement = majority_n / 5.0

    if row.get("majority") != majority:
        raise ValueError(
            f"{item_id}: SC5 majority field mismatch."
        )

    try:
        agreement = float(row.get("agreement"))
    except Exception as exc:
        raise ValueError(
            f"{item_id}: SC5 agreement invalid."
        ) from exc

    if agreement not in ALLOWED_SC5_AGREEMENT:
        raise ValueError(
            f"{item_id}: SC5 agreement outside "
            "frozen domain."
        )

    if abs(
        agreement - expected_agreement
    ) > 1e-12:
        raise ValueError(
            f"{item_id}: SC5 agreement does not "
            "match five outputs."
        )

    return majority, agreement


def validate_vc_valid_record(
    item_id,
    row,
    expected_recommendation,
):
    if (
        row.get("frozen_recommendation")
        != expected_recommendation
    ):
        raise ValueError(
            f"{item_id}: VC frozen recommendation "
            "does not equal SC5 majority."
        )

    try:
        value = int(
            row.get("confidence_integer")
        )
    except Exception as exc:
        raise ValueError(
            f"{item_id}: VC confidence_integer invalid."
        ) from exc

    if value < 0 or value > 100:
        raise ValueError(
            f"{item_id}: VC integer outside 0..100."
        )

    raw = row.get("raw_confidence")

    try:
        raw = float(raw)
    except Exception as exc:
        raise ValueError(
            f"{item_id}: VC raw confidence invalid."
        ) from exc

    if not 0.0 <= raw <= 1.0:
        raise ValueError(
            f"{item_id}: VC raw confidence outside [0,1]."
        )

    if abs(
        raw - value / 100.0
    ) > 1e-12:
        raise ValueError(
            f"{item_id}: VC raw/integer mismatch."
        )

    output = str(
        row.get("output", "")
    )

    # Mirror the frozen collector parser exactly:
    # 0..100 represented by one/two digits or exactly 100.
    # Leading-zero forms such as "08" are accepted by the
    # collector and must normalize to integer 8 consistently.
    if not re.fullmatch(
        r"(?:100|[0-9]{1,2})",
        output,
    ):
        raise ValueError(
            f"{item_id}: VC output text is not an "
            "accepted integer 0..100."
        )

    if int(output) != value:
        raise ValueError(
            f"{item_id}: VC output numeric value does not "
            "match confidence_integer."
        )

    return raw


def normalize_dev500(
    *,
    selected_ids,
    manifest_records,
    sc5_records,
    vc_records,
    gt_records,
):
    selected = validate_selected_ids(
        selected_ids
    )

    manifest = validate_manifest(
        selected,
        manifest_records,
    )

    gt = validate_ground_truth(
        selected,
        gt_records,
    )

    sc5 = unique_map(
        sc5_records,
        source_name="sc5_terminal",
        selected_ids=selected,
    )

    vc = unique_map(
        vc_records,
        source_name="vc_terminal",
        selected_ids=selected,
    )

    # Collection-complete requirement:
    # every selected item must have an SC5 terminal.
    if set(sc5) != selected:
        missing = sorted(
            selected - set(sc5)
        )

        raise ValueError(
            "Collection incomplete: missing SC5 terminal "
            f"records: {missing[:5]}"
        )

    paired_rows = []
    sc5_all_valid_rows = []

    invalid_reasons = Counter()

    for item_id in sorted(selected):
        s = sc5[item_id]
        s_valid = s.get("valid") is True

        if not s_valid:
            reason = (
                s.get("invalid_reason")
                or "SC5_UNKNOWN_INVALID"
            )

            invalid_reasons[
                f"SC5:{reason}"
            ] += 1

            # VC is not expected when SC5 is invalid.
            if item_id in vc:
                raise ValueError(
                    f"{item_id}: VC record exists despite "
                    "terminal-invalid SC5."
                )

            continue

        recommendation, agreement = (
            validate_sc5_valid_record(
                item_id,
                s,
            )
        )

        truth = gt[item_id][
            "ground_truth"
        ]

        correctness = int(
            recommendation == truth
        )

        fold = int(
            manifest[item_id]["cv_fold"]
        )

        sc5_all_valid_rows.append({
            "item_id": item_id,
            "cv_fold": fold,
            "recommendation": recommendation,
            "ground_truth": truth,
            "correctness": correctness,
            "sc5_agreement": agreement,
        })

        # VC terminal is required for every valid SC5 item
        # in a collection-complete state.
        if item_id not in vc:
            raise ValueError(
                f"Collection incomplete: valid SC5 item "
                f"{item_id} has no VC terminal."
            )

        v = vc[item_id]

        if v.get("valid") is not True:
            reason = (
                v.get("invalid_reason")
                or "VC_UNKNOWN_INVALID"
            )

            invalid_reasons[
                f"VC:{reason}"
            ] += 1

            continue

        vc_raw = validate_vc_valid_record(
            item_id,
            v,
            recommendation,
        )

        paired_rows.append({
            "item_id": item_id,
            "cv_fold": fold,
            "recommendation": recommendation,
            "ground_truth": truth,
            "correctness": correctness,
            "sc5_agreement": agreement,
            "vc_raw_confidence": vc_raw,
        })

    # No selected VC records may exist outside valid-SC5 items.
    valid_sc5_ids = {
        x["item_id"]
        for x in sc5_all_valid_rows
    }

    unexpected_vc = (
        set(vc)
        - valid_sc5_ids
    )

    if unexpected_vc:
        raise ValueError(
            "VC records exist for non-valid-SC5 items: "
            + ", ".join(
                sorted(unexpected_vc)[:5]
            )
        )

    paired_fold_counts = Counter(
        row["cv_fold"]
        for row in paired_rows
    )

    missing_folds = [
        fold
        for fold in range(1, 6)
        if paired_fold_counts[fold] == 0
    ]

    if missing_folds:
        raise ValueError(
            "Paired common-valid population lost frozen "
            f"fold(s): {missing_folds}"
        )

    return {
        "paired_rows": paired_rows,
        "sc5_all_valid_rows":
            sc5_all_valid_rows,
        "summary": {
            "selected_items": 500,
            "sc5_terminal_items":
                len(sc5),
            "sc5_valid_items":
                len(sc5_all_valid_rows),
            "vc_terminal_items":
                len(vc),
            "vc_valid_items":
                sum(
                    1
                    for r in vc.values()
                    if r.get("valid") is True
                ),
            "paired_common_valid_items":
                len(paired_rows),
            "paired_fold_counts": {
                str(k): paired_fold_counts[k]
                for k in range(1, 6)
            },
            "invalid_reasons":
                dict(sorted(
                    invalid_reasons.items()
                )),
        },
    }


def make_sc5_valid(
    item_id,
    agreement,
    recommendation,
):
    other = (
        "DO_NOT_ESCALATE"
        if recommendation == "ESCALATE"
        else "ESCALATE"
    )

    n_majority = int(
        round(agreement * 5)
    )

    outputs = (
        [recommendation] * n_majority
        + [other] * (5 - n_majority)
    )

    return {
        "item_id": item_id,
        "valid": True,
        "invalid_reason": None,
        "outputs": outputs,
        "majority": recommendation,
        "agreement": agreement,
    }


def synthetic_fixture():
    selected_ids = [
        f"G6D-D-{i:04d}"
        for i in range(1, 501)
    ]

    folds = []

    for fold, n in EXPECTED_FOLD_COUNTS.items():
        folds.extend(
            [fold] * n
        )

    manifest = []
    gt = []
    sc5 = []
    vc = []

    # Five SC5 invalids.
    sc5_invalid_ids = {
        selected_ids[10],
        selected_ids[110],
        selected_ids[210],
        selected_ids[310],
        selected_ids[410],
    }

    # Seven VC invalids among otherwise-valid SC5.
    vc_invalid_ids = {
        selected_ids[20],
        selected_ids[120],
        selected_ids[220],
        selected_ids[320],
        selected_ids[420],
        selected_ids[470],
        selected_ids[490],
    }

    agreements = [
        0.6,
        0.8,
        1.0,
    ]

    for i, (
        item_id,
        fold,
    ) in enumerate(
        zip(
            selected_ids,
            folds,
        ),
        start=1,
    ):
        manifest.append({
            "item_id": item_id,
            "cv_fold": str(fold),
        })

        truth = (
            "ESCALATE"
            if i % 4 == 0
            else "DO_NOT_ESCALATE"
        )

        gt.append({
            "item_id": item_id,
            "ground_truth": truth,
        })

        if item_id in sc5_invalid_ids:
            sc5.append({
                "item_id": item_id,
                "valid": False,
                "invalid_reason":
                    "SYNTHETIC_SC5_INVALID",
                "outputs": [
                    "BAD_OUTPUT"
                ],
                "majority": None,
                "agreement": None,
            })

            continue

        recommendation = (
            truth
            if i % 5 != 0
            else (
                "DO_NOT_ESCALATE"
                if truth == "ESCALATE"
                else "ESCALATE"
            )
        )

        agreement = agreements[
            i % len(agreements)
        ]

        sc5.append(
            make_sc5_valid(
                item_id,
                agreement,
                recommendation,
            )
        )

        if item_id in vc_invalid_ids:
            vc.append({
                "item_id": item_id,
                "frozen_recommendation":
                    recommendation,
                "valid": False,
                "invalid_reason":
                    "SYNTHETIC_VC_INVALID",
                "output": "BAD",
                "confidence_integer": None,
                "raw_confidence": None,
            })

            continue

        confidence_integer = (
            82
            if recommendation == truth
            else 36
        )

        vc.append({
            "item_id": item_id,
            "frozen_recommendation":
                recommendation,
            "valid": True,
            "invalid_reason": None,
            "output":
                str(confidence_integer),
            "confidence_integer":
                confidence_integer,
            "raw_confidence":
                confidence_integer / 100.0,
        })

    # Historical nonselected outputs are allowed and ignored.
    sc5.append({
        "item_id": "G6D-D-0999",
        "valid": True,
        "outputs": [
            "ESCALATE"
        ] * 5,
        "majority": "ESCALATE",
        "agreement": 1.0,
    })

    vc.append({
        "item_id": "G6D-D-0999",
        "frozen_recommendation":
            "ESCALATE",
        "valid": True,
        "output": "80",
        "confidence_integer": 80,
        "raw_confidence": 0.8,
    })

    return {
        "selected_ids": selected_ids,
        "manifest_records": manifest,
        "sc5_records": sc5,
        "vc_records": vc,
        "gt_records": gt,
    }


def expect_failure(
    name,
    fixture,
    expected_text,
):
    try:
        normalize_dev500(
            **fixture
        )
    except Exception as exc:
        text = str(exc)

        if expected_text not in text:
            raise AssertionError(
                f"{name}: wrong failure: {text}"
            )

        return {
            "test": name,
            "status": "PASS",
            "failure_detected": text,
        }

    raise AssertionError(
        f"{name}: expected failure was not detected"
    )


def synthetic_self_test():
    fixture = synthetic_fixture()

    # Regression test: the frozen collector accepts leading-zero
    # integer text such as "08". Normalization must preserve that
    # semantic validity rather than requiring canonical "8" text.
    leading_zero_tested = False

    for row in fixture["vc_records"]:
        if row["item_id"] == "G6D-D-0002":
            row["output"] = "08"
            row["confidence_integer"] = 8
            row["raw_confidence"] = 0.08
            leading_zero_tested = True
            break

    assert leading_zero_tested is True

    result = normalize_dev500(
        **fixture
    )

    summary = result["summary"]

    assert summary[
        "selected_items"
    ] == 500

    assert summary[
        "sc5_terminal_items"
    ] == 500

    assert summary[
        "sc5_valid_items"
    ] == 495

    assert summary[
        "vc_terminal_items"
    ] == 495

    assert summary[
        "vc_valid_items"
    ] == 488

    assert summary[
        "paired_common_valid_items"
    ] == 488

    assert len(
        result["paired_rows"]
    ) == 488

    assert len(
        result["sc5_all_valid_rows"]
    ) == 495

    assert all(
        row["correctness"] in {0, 1}
        for row in result["paired_rows"]
    )

    assert all(
        row["sc5_agreement"]
        in ALLOWED_SC5_AGREEMENT
        for row in result["paired_rows"]
    )

    assert all(
        0.0
        <= row["vc_raw_confidence"]
        <= 1.0
        for row in result["paired_rows"]
    )

    # Fail-closed test 1: duplicate selected SC5 terminal.
    duplicate_fixture = synthetic_fixture()

    duplicate_fixture[
        "sc5_records"
    ].append(
        dict(
            duplicate_fixture[
                "sc5_records"
            ][0]
        )
    )

    duplicate_test = expect_failure(
        "duplicate_sc5_terminal",
        duplicate_fixture,
        "duplicate terminal/item record",
    )

    # Fail-closed test 2:
    # valid SC5 without required VC terminal.
    missing_vc_fixture = synthetic_fixture()

    target = "G6D-D-0001"

    missing_vc_fixture[
        "vc_records"
    ] = [
        r
        for r in missing_vc_fixture[
            "vc_records"
        ]
        if r["item_id"] != target
    ]

    missing_vc_test = expect_failure(
        "missing_vc_for_valid_sc5",
        missing_vc_fixture,
        "has no VC terminal",
    )

    # Fail-closed test 3:
    # VC recommendation inconsistent with SC5 majority.
    mismatch_fixture = synthetic_fixture()

    for row in mismatch_fixture[
        "vc_records"
    ]:
        if (
            row["item_id"] == "G6D-D-0001"
        ):
            row[
                "frozen_recommendation"
            ] = (
                "ESCALATE"
                if row[
                    "frozen_recommendation"
                ] == "DO_NOT_ESCALATE"
                else "DO_NOT_ESCALATE"
            )
            break

    mismatch_test = expect_failure(
        "vc_recommendation_mismatch",
        mismatch_fixture,
        "does not equal SC5 majority",
    )

    return {
        "artifact":
            "GATE6D_DEV_NORMALIZATION_SYNTHETIC_TEST_V1",
        "status": "PASS",
        "primary_analysis_set":
            "PAIRED_COMMON_VALID",
        "synthetic_selected_items": 500,
        "synthetic_sc5_valid": 495,
        "synthetic_vc_valid": 488,
        "synthetic_paired_common_valid": 488,
        "vc_leading_zero_integer_format_test": True,
        "paired_fold_counts":
            summary["paired_fold_counts"],
        "invalid_reasons":
            summary["invalid_reasons"],
        "fail_closed_tests": [
            duplicate_test,
            missing_vc_test,
            mismatch_test,
        ],
        "real_dev_outputs_read": False,
        "real_dev_ground_truth_read": False,
        "correctness_based_real_comparison":
            False,
        "calibration_eval_accessed": False,
        "external_test_accessed": False,
        "model_calls": 0,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--self-test",
        action="store_true",
    )

    args = parser.parse_args()

    if not args.self_test:
        print(
            "BLOCKED: normalization V1 currently "
            "permits --self-test only."
        )
        print(
            "Real DEV files were NOT opened."
        )
        return

    result = synthetic_self_test()

    out = Path(
        "benchmarks/gate6d/"
        "dev_normalization_v1/"
        "synthetic_self_test.json"
    )

    out.write_text(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "=== GATE 6D DEV NORMALIZATION "
        "SYNTHETIC TEST ==="
    )

    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
