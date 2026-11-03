#!/usr/bin/env python3

"""
Pre-Gate-7 synthetic-only statistical analysis core V1.

Preparation only:
- Gate 7 is NOT opened.
- Real participants are rejected.
- Final study conditions are NOT frozen.
- Final sample size / trial count are NOT frozen.
- Final calibrated confidence is NOT used.
- Calibration-EVAL and External-TEST are NOT accessed.

Current purpose:
Validate trial-level binary mixed-model infrastructure using
synthetic placeholder data only.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM


STATUS_PATH = Path(
    "docs/pre_gate7/PRE_GATE7_STATUS_V1.json"
)

ALLOWED_BINARY = {0, 1}


def assert_pre_gate7_boundary() -> dict:
    status = json.loads(
        STATUS_PATH.read_text(
            encoding="utf-8"
        )
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
                "Fail-closed pre-Gate-7 boundary: "
                + key
            )

    permitted = set(
        status.get("permitted_now", [])
    )

    if (
        "statistical analysis skeleton development"
        not in permitted
    ):
        raise RuntimeError(
            "Statistical skeleton development "
            "is not permitted by status file."
        )

    return status


def validate_synthetic_trial_frame(
    df: pd.DataFrame,
    outcome: str,
) -> None:
    required = {
        "participant_id",
        "item_id",
        "condition",
        outcome,
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + repr(sorted(missing))
        )

    if len(df) == 0:
        raise ValueError(
            "Synthetic trial frame is empty."
        )

    if not df["participant_id"].map(
        lambda x: str(x).startswith("SYN-")
    ).all():
        raise ValueError(
            "Real/non-synthetic participant ID rejected."
        )

    if not df["item_id"].map(
        lambda x: str(x).startswith("SYN-")
    ).all():
        raise ValueError(
            "Real/non-synthetic item ID rejected."
        )

    if not df["condition"].map(
        lambda x: str(x).startswith("SYN_")
    ).all():
        raise ValueError(
            "Non-placeholder condition rejected."
        )

    observed = set(
        int(x)
        for x in df[outcome].dropna()
    )

    if not observed.issubset(
        ALLOWED_BINARY
    ):
        raise ValueError(
            "Binary outcome must contain only 0/1."
        )

    if len(observed) < 2:
        raise ValueError(
            "Binary outcome must contain both classes "
            "for synthetic model validation."
        )

    if df[
        [
            "participant_id",
            "item_id",
            "condition",
            outcome,
        ]
    ].isna().any().any():
        raise ValueError(
            "Missing values are not permitted "
            "in synthetic validation input."
        )


def fit_binary_crossed_mixed_model(
    df: pd.DataFrame,
    outcome: str,
) -> dict:
    assert_pre_gate7_boundary()

    validate_synthetic_trial_frame(
        df,
        outcome,
    )

    model = (
        BinomialBayesMixedGLM.from_formula(
            f"{outcome} ~ C(condition)",
            {
                "participant":
                    "0 + C(participant_id)",
                "item":
                    "0 + C(item_id)",
            },
            df,
        )
    )

    result = model.fit_vb()

    if result is None:
        raise RuntimeError(
            "Synthetic binary mixed model "
            "returned no result."
        )

    fixed_names = list(
        model.exog_names
    )

    fixed_mean = [
        float(x)
        for x in result.fe_mean
    ]

    fixed_sd = [
        float(x)
        for x in result.fe_sd
    ]

    if not (
        len(fixed_names)
        == len(fixed_mean)
        == len(fixed_sd)
    ):
        raise RuntimeError(
            "Fixed-effect result dimensions mismatch."
        )

    return {
        "outcome": outcome,
        "model_family":
            "binomial_logit_mixed_model",
        "fixed_effects":
            [
                {
                    "term": name,
                    "posterior_mean": mean,
                    "posterior_sd": sd,
                }
                for name,mean,sd
                in zip(
                    fixed_names,
                    fixed_mean,
                    fixed_sd,
                )
            ],
        "random_intercepts": [
            "participant_id",
            "item_id",
        ],
        "fit_backend":
            "statsmodels.BinomialBayesMixedGLM.fit_vb",
        "synthetic_only": True,
        "gate7_opened": False,
    }



def validate_synthetic_continuous_frame(
    df: pd.DataFrame,
    outcome: str,
) -> None:
    required = {
        "participant_id",
        "item_id",
        "condition",
        outcome,
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Missing required columns: "
            + repr(sorted(missing))
        )

    if len(df) == 0:
        raise ValueError(
            "Synthetic continuous frame is empty."
        )

    if not df["participant_id"].map(
        lambda x: str(x).startswith("SYN-")
    ).all():
        raise ValueError(
            "Real/non-synthetic participant ID rejected."
        )

    if not df["item_id"].map(
        lambda x: str(x).startswith("SYN-")
    ).all():
        raise ValueError(
            "Real/non-synthetic item ID rejected."
        )

    if not df["condition"].map(
        lambda x: str(x).startswith("SYN_")
    ).all():
        raise ValueError(
            "Non-placeholder condition rejected."
        )

    values = pd.to_numeric(
        df[outcome],
        errors="coerce",
    )

    if values.isna().any():
        raise ValueError(
            "Continuous outcome must be finite numeric."
        )

    if not np.isfinite(
        values.to_numpy(dtype=float)
    ).all():
        raise ValueError(
            "Continuous outcome contains non-finite values."
        )


def fit_continuous_crossed_mixed_model(
    df: pd.DataFrame,
    outcome: str,
) -> dict:
    assert_pre_gate7_boundary()

    validate_synthetic_continuous_frame(
        df,
        outcome,
    )

    model = smf.mixedlm(
        f"{outcome} ~ C(condition)",
        df,
        groups=df["participant_id"],
        re_formula="1",
        vc_formula={
            "item":
                "0 + C(item_id)"
        },
    )

    result = model.fit(
        method="lbfgs",
        reml=False,
    )

    if not bool(result.converged):
        raise RuntimeError(
            "Synthetic continuous mixed model "
            "did not converge."
        )

    return {
        "outcome": outcome,
        "model_family":
            "linear_mixed_model",
        "fixed_effects": [
            {
                "term": str(name),
                "estimate": float(value),
            }
            for name,value
            in result.fe_params.items()
        ],
        "participant_random_intercept":
            True,
        "item_variance_component":
            True,
        "fit_backend":
            "statsmodels.MixedLM.fit",
        "synthetic_only":
            True,
        "gate7_opened":
            False,
    }


def make_synthetic_trials() -> pd.DataFrame:
    rng = np.random.default_rng(
        20261103
    )

    participants = [
        f"SYN-P{i:03d}"
        for i in range(1, 61)
    ]

    items = [
        f"SYN-I{i:03d}"
        for i in range(1, 13)
    ]

    conditions = [
        "SYN_A",
        "SYN_B",
        "SYN_C",
    ]

    participant_re = {
        p: rng.normal(0.0, 0.55)
        for p in participants
    }

    item_re = {
        item: rng.normal(0.0, 0.35)
        for item in items
    }

    condition_effect = {
        "SYN_A": 0.0,
        "SYN_B": 0.40,
        "SYN_C": 0.80,
    }

    rows = []

    for p_index,p in enumerate(
        participants
    ):
        for item_index,item in enumerate(
            items
        ):
            condition = conditions[
                (p_index + item_index)
                % len(conditions)
            ]

            eta_correct = (
                -0.15
                + condition_effect[
                    condition
                ]
                + participant_re[p]
                + item_re[item]
            )

            p_correct = (
                1.0
                / (
                    1.0
                    + np.exp(-eta_correct)
                )
            )

            correct = int(
                rng.random()
                < p_correct
            )

            eta_reliance = (
                -0.35
                + 0.75
                * condition_effect[
                    condition
                ]
                + 0.8
                * correct
                + 0.6
                * participant_re[p]
                + 0.4
                * item_re[item]
            )

            p_reliance = (
                1.0
                / (
                    1.0
                    + np.exp(-eta_reliance)
                )
            )

            appropriate_reliance = int(
                rng.random()
                < p_reliance
            )

            rows.append(
                {
                    "participant_id": p,
                    "item_id": item,
                    "condition":
                        condition,
                    "correct_decision":
                        correct,
                    "appropriate_reliance":
                        appropriate_reliance,
                    "synthetic_workload_score":
                        float(
                            58.0
                            - 5.0
                            * condition_effect[
                                condition
                            ]
                            + 3.0
                            * participant_re[p]
                            + 2.0
                            * item_re[item]
                            + rng.normal(
                                0.0,
                                4.5,
                            )
                        ),
                }
            )

    return pd.DataFrame(rows)


def synthetic_self_test() -> dict:
    assert_pre_gate7_boundary()

    df = make_synthetic_trials()

    correctness = (
        fit_binary_crossed_mixed_model(
            df,
            "correct_decision",
        )
    )

    reliance = (
        fit_binary_crossed_mixed_model(
            df,
            "appropriate_reliance",
        )
    )

    workload = (
        fit_continuous_crossed_mixed_model(
            df,
            "synthetic_workload_score",
        )
    )

    fail_closed = 0

    bad = df.copy()
    bad.loc[
        bad.index[0],
        "participant_id",
    ] = "REAL-001"

    try:
        validate_synthetic_trial_frame(
            bad,
            "correct_decision",
        )
    except Exception:
        fail_closed += 1
    else:
        raise RuntimeError(
            "Real participant was not rejected."
        )

    bad = df.copy()
    bad.loc[
        bad.index[0],
        "condition",
    ] = "FINAL_CONDITION"

    try:
        validate_synthetic_trial_frame(
            bad,
            "correct_decision",
        )
    except Exception:
        fail_closed += 1
    else:
        raise RuntimeError(
            "Final/non-placeholder condition "
            "was not rejected."
        )

    bad = df.copy()
    bad.loc[
        bad.index[0],
        "correct_decision",
    ] = 2

    try:
        validate_synthetic_trial_frame(
            bad,
            "correct_decision",
        )
    except Exception:
        fail_closed += 1
    else:
        raise RuntimeError(
            "Invalid binary outcome "
            "was not rejected."
        )

    bad = df.copy()
    bad.loc[
        bad.index[0],
        "synthetic_workload_score",
    ] = np.inf

    try:
        validate_synthetic_continuous_frame(
            bad,
            "synthetic_workload_score",
        )
    except Exception:
        fail_closed += 1
    else:
        raise RuntimeError(
            "Non-finite continuous outcome "
            "was not rejected."
        )

    return {
        "artifact":
            "PRE_GATE7_STATISTICAL_ANALYSIS_CORE_SELF_TEST_V1",
        "status": "PASS",
        "synthetic_rows":
            int(len(df)),
        "synthetic_participants":
            int(
                df[
                    "participant_id"
                ].nunique()
            ),
        "synthetic_items":
            int(
                df[
                    "item_id"
                ].nunique()
            ),
        "placeholder_conditions":
            sorted(
                df[
                    "condition"
                ].unique().tolist()
            ),
        "binary_models_validated": [
            correctness["outcome"],
            reliance["outcome"],
        ],
        "continuous_models_validated": [
            workload["outcome"],
        ],
        "crossed_random_intercepts": [
            "participant_id",
            "item_id",
        ],
        "fail_closed_tests":
            fail_closed,
        "real_participants_used":
            False,
        "final_conditions_frozen":
            False,
        "final_sample_size_frozen":
            False,
        "final_trial_count_frozen":
            False,
        "final_calibrated_confidence_used":
            False,
        "calibration_eval_accessed":
            False,
        "external_test_accessed":
            False,
        "gate7_opened":
            False,
    }


if __name__ == "__main__":
    result = synthetic_self_test()

    print(
        "=== PRE-GATE-7 STATISTICAL CORE V1 ==="
    )

    for key,value in result.items():
        print(f"{key}: {value}")
