#!/usr/bin/env python3

"""
Gate 6D calibration-analysis core.

This module contains only mathematical/statistical analysis logic.
It does not load Gate 6D DEV, EVAL, External-TEST, model-output,
or ground-truth artifacts.

Frozen conventions implemented here:
- correctness is the positive class for Brier/AUROC;
- incorrectness is the positive class for AUPRC using 1-confidence;
- primary metric is grouped 5-fold OOF Brier;
- ECE uses 10 fixed equal-width bins;
- calibrators: identity, unregularized Platt, isotonic when eligible;
- isotonic all-DEV eligibility:
    >=20 correct, >=20 incorrect, >=3 distinct raw scores;
- effective Brier tie: absolute difference < 0.01;
- tie breaker: greater AUROC;
- remaining estimator tie: SC5_AGREEMENT.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import math
from typing import Dict, Iterable, List

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    roc_auc_score,
)


FROZEN_BRIER_TIE_THRESHOLD = 0.01
ECE_BINS = 10
ISOTONIC_MIN_CORRECT = 20
ISOTONIC_MIN_INCORRECT = 20
ISOTONIC_MIN_RAW_SCORES = 3


@dataclass
class MethodResult:
    estimator: str
    calibrator: str
    valid: bool
    reason: str
    n: int
    brier: float
    auroc_correct: float
    auprc_incorrect: float
    ece10: float
    oof_prob: np.ndarray | None
    reliability: List[dict] | None


def _as_1d_float(x: Iterable[float]) -> np.ndarray:
    a = np.asarray(list(x), dtype=float)
    if a.ndim != 1:
        raise ValueError("Expected 1-D array.")
    return a


def _validate_inputs(
    raw: np.ndarray,
    y: np.ndarray,
    folds: np.ndarray,
) -> None:
    if not (len(raw) == len(y) == len(folds)):
        raise ValueError("raw, y, and folds must have equal length.")

    if len(raw) == 0:
        raise ValueError("Empty input.")

    if not np.all(np.isfinite(raw)):
        raise ValueError("Raw confidence contains non-finite values.")

    if np.any((raw < 0.0) | (raw > 1.0)):
        raise ValueError("Raw confidence must lie in [0,1].")

    if not np.all(np.isin(y, [0.0, 1.0])):
        raise ValueError("Correctness labels must be binary 0/1.")

    unique_folds = sorted(set(int(v) for v in folds))
    if unique_folds != [1, 2, 3, 4, 5]:
        raise ValueError(
            f"Expected exactly frozen folds [1,2,3,4,5]; "
            f"got {unique_folds}"
        )


def brier(y: np.ndarray, p: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def reliability_table(
    y: np.ndarray,
    p: np.ndarray,
    n_bins: int = ECE_BINS,
) -> List[dict]:
    rows: List[dict] = []

    # Fixed bins:
    # [0,.1), [.1,.2), ... [.9,1.0]
    edges = np.linspace(0.0, 1.0, n_bins + 1)

    for i in range(n_bins):
        lo = float(edges[i])
        hi = float(edges[i + 1])

        if i == n_bins - 1:
            mask = (p >= lo) & (p <= hi)
        else:
            mask = (p >= lo) & (p < hi)

        n = int(mask.sum())

        if n:
            mean_conf = float(np.mean(p[mask]))
            accuracy = float(np.mean(y[mask]))
            gap = abs(mean_conf - accuracy)
        else:
            mean_conf = math.nan
            accuracy = math.nan
            gap = math.nan

        rows.append(
            {
                "bin": i + 1,
                "lower": lo,
                "upper": hi,
                "n": n,
                "mean_confidence": mean_conf,
                "accuracy": accuracy,
                "absolute_gap": gap,
            }
        )

    return rows


def ece10(
    y: np.ndarray,
    p: np.ndarray,
) -> float:
    rows = reliability_table(y, p, ECE_BINS)
    n_total = len(y)

    return float(
        sum(
            (r["n"] / n_total) * r["absolute_gap"]
            for r in rows
            if r["n"] > 0
        )
    )


def metric_bundle(
    y: np.ndarray,
    p: np.ndarray,
) -> dict:
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("Calibrated probabilities outside [0,1].")

    if len(np.unique(y)) < 2:
        auroc = math.nan
    else:
        auroc = float(roc_auc_score(y, p))

    incorrect = 1.0 - y
    incorrect_score = 1.0 - p

    if incorrect.sum() == 0:
        auprc_incorrect = math.nan
    else:
        auprc_incorrect = float(
            average_precision_score(
                incorrect,
                incorrect_score,
            )
        )

    rel = reliability_table(y, p)

    return {
        "brier": brier(y, p),
        "auroc_correct": auroc,
        "auprc_incorrect": auprc_incorrect,
        "ece10": ece10(y, p),
        "reliability": rel,
    }


def isotonic_global_eligible(
    raw: np.ndarray,
    y: np.ndarray,
) -> tuple[bool, str]:
    n_correct = int(y.sum())
    n_incorrect = int(len(y) - n_correct)
    n_scores = int(len(np.unique(raw)))

    if n_correct < ISOTONIC_MIN_CORRECT:
        return False, f"correct<{ISOTONIC_MIN_CORRECT}"

    if n_incorrect < ISOTONIC_MIN_INCORRECT:
        return False, f"incorrect<{ISOTONIC_MIN_INCORRECT}"

    if n_scores < ISOTONIC_MIN_RAW_SCORES:
        return False, f"raw_scores<{ISOTONIC_MIN_RAW_SCORES}"

    return True, "eligible"


def _fit_predict(
    method: str,
    train_raw: np.ndarray,
    train_y: np.ndarray,
    test_raw: np.ndarray,
) -> np.ndarray:

    if method == "identity":
        return np.clip(test_raw, 0.0, 1.0)

    if len(np.unique(train_y)) < 2:
        raise ValueError(
            f"{method} training fold contains only one class."
        )

    if method == "platt":
        # Platt scaling here is explicitly:
        # sigmoid(a * raw_confidence + b).
        #
        # C=np.inf is scikit-learn's current unregularized
        # logistic-regression specification.
        model = LogisticRegression(
            C=np.inf,
            solver="lbfgs",
            max_iter=5000,
        )

        model.fit(
            train_raw.reshape(-1, 1),
            train_y.astype(int),
        )

        return model.predict_proba(
            test_raw.reshape(-1, 1)
        )[:, 1]

    if method == "isotonic":
        if len(np.unique(train_raw)) < 3:
            raise ValueError(
                "Isotonic training split has fewer than "
                "3 distinct raw scores."
            )

        model = IsotonicRegression(
            y_min=0.0,
            y_max=1.0,
            increasing=True,
            out_of_bounds="clip",
        )

        model.fit(train_raw, train_y)
        return model.predict(test_raw)

    raise ValueError(f"Unknown calibrator: {method}")


def grouped_oof_predictions(
    raw: np.ndarray,
    y: np.ndarray,
    folds: np.ndarray,
    calibrator: str,
) -> np.ndarray:
    pred = np.full(len(raw), np.nan, dtype=float)

    if calibrator == "identity":
        return np.clip(raw.copy(), 0.0, 1.0)

    for fold in [1, 2, 3, 4, 5]:
        test_mask = folds == fold
        train_mask = ~test_mask

        if int(test_mask.sum()) == 0:
            raise ValueError(f"Fold {fold} is empty.")

        pred[test_mask] = _fit_predict(
            calibrator,
            raw[train_mask],
            y[train_mask],
            raw[test_mask],
        )

    if not np.all(np.isfinite(pred)):
        raise ValueError("OOF predictions contain missing values.")

    return np.clip(pred, 0.0, 1.0)


def evaluate_estimator(
    estimator: str,
    raw_values: Iterable[float],
    correctness: Iterable[int],
    folds_values: Iterable[int],
) -> List[MethodResult]:
    raw = _as_1d_float(raw_values)
    y = _as_1d_float(correctness)
    folds = np.asarray(list(folds_values), dtype=int)

    _validate_inputs(raw, y, folds)

    iso_ok, iso_reason = isotonic_global_eligible(raw, y)

    results: List[MethodResult] = []

    for calibrator in ["identity", "platt", "isotonic"]:

        if calibrator == "isotonic" and not iso_ok:
            results.append(
                MethodResult(
                    estimator=estimator,
                    calibrator=calibrator,
                    valid=False,
                    reason=iso_reason,
                    n=len(y),
                    brier=math.nan,
                    auroc_correct=math.nan,
                    auprc_incorrect=math.nan,
                    ece10=math.nan,
                    oof_prob=None,
                    reliability=None,
                )
            )
            continue

        try:
            p = grouped_oof_predictions(
                raw,
                y,
                folds,
                calibrator,
            )

            metrics = metric_bundle(y, p)

            results.append(
                MethodResult(
                    estimator=estimator,
                    calibrator=calibrator,
                    valid=True,
                    reason="valid",
                    n=len(y),
                    brier=metrics["brier"],
                    auroc_correct=metrics["auroc_correct"],
                    auprc_incorrect=metrics[
                        "auprc_incorrect"
                    ],
                    ece10=metrics["ece10"],
                    oof_prob=p,
                    reliability=metrics["reliability"],
                )
            )

        except Exception as exc:
            results.append(
                MethodResult(
                    estimator=estimator,
                    calibrator=calibrator,
                    valid=False,
                    reason=(
                        type(exc).__name__
                        + ": "
                        + str(exc)
                    ),
                    n=len(y),
                    brier=math.nan,
                    auroc_correct=math.nan,
                    auprc_incorrect=math.nan,
                    ece10=math.nan,
                    oof_prob=None,
                    reliability=None,
                )
            )

    return results


def grouped_constant_baseline_oof(
    y_values: Iterable[int],
    folds_values: Iterable[int],
) -> np.ndarray:
    """
    Fair DEV OOF comparison baseline:
    each held-out fold receives correctness prevalence estimated
    only from the other four folds.

    The all-DEV correctness prevalence is separately the quantity
    to freeze after DEV analysis for later untouched-EVAL comparison.
    """
    y = _as_1d_float(y_values)
    folds = np.asarray(list(folds_values), dtype=int)

    p = np.full(len(y), np.nan, dtype=float)

    for fold in [1, 2, 3, 4, 5]:
        test_mask = folds == fold
        train_mask = ~test_mask

        if not np.any(test_mask):
            raise ValueError(f"Fold {fold} is empty.")

        p[test_mask] = float(np.mean(y[train_mask]))

    return p


def select_method(
    results: List[MethodResult],
    threshold: float = FROZEN_BRIER_TIE_THRESHOLD,
) -> dict:
    valid = [
        r
        for r in results
        if r.valid
        and np.isfinite(r.brier)
        and np.isfinite(r.auroc_correct)
    ]

    if not valid:
        raise ValueError("No valid candidate methods.")

    # Primary criterion.
    best_brier = min(r.brier for r in valid)

    # Frozen strict '< threshold' rule.
    shortlist = [
        r
        for r in valid
        if abs(r.brier - best_brier) < threshold
    ]

    if len(shortlist) == 1:
        winner = shortlist[0]
        reason = "lowest_brier_not_effectively_tied"

    else:
        # Frozen first tie breaker: greater AUROC.
        best_auc = max(r.auroc_correct for r in shortlist)

        auc_tied = [
            r
            for r in shortlist
            if math.isclose(
                r.auroc_correct,
                best_auc,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ]

        if len(auc_tied) == 1:
            winner = auc_tied[0]
            reason = "effective_brier_tie_broken_by_auroc"

        else:
            # Frozen second tie breaker:
            # prefer SC5_AGREEMENT estimator.
            sc5 = [
                r
                for r in auc_tied
                if r.estimator == "SC5_AGREEMENT"
            ]

            if len(sc5) == 1:
                winner = sc5[0]
                reason = (
                    "brier_and_auroc_tie_broken_by_"
                    "SC5_AGREEMENT"
                )
            elif len(sc5) > 1:
                raise RuntimeError(
                    "Selection remains ambiguous between multiple "
                    "SC5_AGREEMENT calibrators. No unplanned "
                    "post-hoc tie breaker is permitted."
                )
            else:
                raise RuntimeError(
                    "Selection remains ambiguous after all frozen "
                    "tie breakers. Protocol review required."
                )

    return {
        "winner_estimator": winner.estimator,
        "winner_calibrator": winner.calibrator,
        "winner_brier": winner.brier,
        "winner_auroc_correct": winner.auroc_correct,
        "reason": reason,
        "threshold": threshold,
        "shortlist": [
            f"{r.estimator}+{r.calibrator}"
            for r in shortlist
        ],
    }


def synthetic_self_test() -> None:
    rng = np.random.default_rng(20261102)

    n = 500

    fold_counts = [97, 101, 102, 98, 102]
    folds = np.concatenate(
        [
            np.full(c, i + 1, dtype=int)
            for i, c in enumerate(fold_counts)
        ]
    )

    assert len(folds) == n

    # Synthetic correctness only. This is not based on real DEV.
    latent = rng.normal(0.25, 1.0, n)
    correctness = (
        latent + rng.normal(0.0, 0.70, n) > 0
    ).astype(int)

    # Synthetic SC5-like confidence restricted to frozen
    # majority-agreement values 0.6 / 0.8 / 1.0.
    strength = (
        0.65
        + 0.20 * correctness
        + rng.normal(0.0, 0.11, n)
    )

    sc5 = np.where(
        strength >= 0.90,
        1.0,
        np.where(strength >= 0.74, 0.8, 0.6),
    )

    # Synthetic VC-like confidence on a denser grid.
    vc = np.clip(
        0.52
        + 0.31 * correctness
        + rng.normal(0.0, 0.16, n),
        0.0,
        1.0,
    )

    vc = np.round(vc, 2)

    all_results: List[MethodResult] = []

    all_results.extend(
        evaluate_estimator(
            "SC5_AGREEMENT",
            sc5,
            correctness,
            folds,
        )
    )

    all_results.extend(
        evaluate_estimator(
            "VC_SELF_EVAL",
            vc,
            correctness,
            folds,
        )
    )

    baseline_p = grouped_constant_baseline_oof(
        correctness,
        folds,
    )

    baseline = metric_bundle(
        correctness.astype(float),
        baseline_p,
    )

    valid = [r for r in all_results if r.valid]

    assert len(valid) >= 4
    assert all(r.n == 500 for r in valid)
    assert all(0.0 <= r.brier <= 1.0 for r in valid)
    assert all(0.0 <= r.ece10 <= 1.0 for r in valid)

    for r in valid:
        assert r.oof_prob is not None
        assert len(r.oof_prob) == 500
        assert np.all(np.isfinite(r.oof_prob))
        assert np.all(
            (r.oof_prob >= 0.0)
            & (r.oof_prob <= 1.0)
        )
        assert r.reliability is not None
        assert sum(x["n"] for x in r.reliability) == 500

    assert FROZEN_BRIER_TIE_THRESHOLD == 0.01
    assert sum(fold_counts) == 500

    winner = select_method(all_results)

    print("=== GATE 6D SYNTHETIC ANALYSIS SELF-TEST ===")
    print("SELF-TEST: PASS")
    print("Synthetic rows:", n)
    print("Fold counts:", fold_counts)
    print("Candidate estimator/calibrator rows:", len(all_results))
    print("Valid candidate rows:", len(valid))
    print(
        "Synthetic constant-baseline Brier:",
        f"{baseline['brier']:.6f}",
    )
    print(
        "Synthetic winner:",
        winner["winner_estimator"],
        "+",
        winner["winner_calibrator"],
    )
    print(
        "Frozen Brier tie threshold:",
        FROZEN_BRIER_TIE_THRESHOLD,
    )
    print("ECE bins:", ECE_BINS)
    print(
        "Platt definition:",
        "sigmoid(a * raw_confidence + b)",
    )
    print(
        "Isotonic DEV eligibility:",
        ">=20 correct, >=20 incorrect, >=3 raw scores",
    )
    print()
    print("Real SC5/VC outputs read: NO")
    print("Real DEV ground truth read: NO")
    print("Calibration-EVAL accessed: NO")
    print("External-TEST accessed: NO")
    print("Model calls: 0")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run deterministic synthetic-only validation.",
    )
    args = parser.parse_args()

    if not args.self_test:
        raise SystemExit(
            "This core module currently permits only --self-test. "
            "Real DEV analysis is intentionally not enabled yet."
        )

    synthetic_self_test()


if __name__ == "__main__":
    main()
