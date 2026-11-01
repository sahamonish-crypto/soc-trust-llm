#!/usr/bin/env python3

from pathlib import Path
from collections import Counter, defaultdict
from statistics import median
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

SPEC = ROOT / "benchmarks/gate6c/scoring_spec.md"
CONTRACT = ROOT / "benchmarks/gate6c/scoring/pre_scoring_implementation_contract_v1.json"
DEVIATION = ROOT / "benchmarks/gate6c/full/audit/GATE6C_GROUND_TRUTH_EXPOSURE_DEVIATION.json"
RAWLOCK = ROOT / "benchmarks/gate6c/full/audit/GATE6C_ALL_CANDIDATE_RAW_COLLECTION_LOCK.json"
META = ROOT / "benchmarks/gate6c/item_metadata.csv"
CANON = ROOT / "benchmarks/gate6c/canonical_model_inputs.jsonl"
GT = ROOT / "benchmarks/gate6c/hidden_ground_truth.csv"
RAW = ROOT / "benchmarks/gate6c/full/raw"

OUTDIR = ROOT / "benchmarks/gate6c/scoring/results"
SUMMARY_OUT = OUTDIR / "gate6c_scoring_summary_v1.json"
ITEM_OUT = OUTDIR / "gate6c_scored_items_v1.csv"

VALID = {"ESCALATE", "DO_NOT_ESCALATE"}
CANDS = ["ZB1", "ZB2", "ZB3"]

EXPECTED_SPEC_SHA = (
    "56d07ed3bfc7cc715ebe883a41cdc0209"
    "b2e4ba638ab477bfb39446527372009"
)

EXPECTED_CANON_SHA = (
    "a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915"
)

# Filled and frozen automatically before commit.
EXPECTED_CONTRACT_SHA = "cff42db4d76f8a4879000a4fe3843d617b5cebe2479f1f64b8dd78095889a855"
EXPECTED_DEVIATION_SHA = "51ccd08724fc35f16f4825ba945706ff31493df43116678e704dac4cf21a8cd1"
EXPECTED_RAWLOCK_SHA = "ca1b350e6933a8d65e1c871f4cea33164ef42355692566802835e7f1577e3e5c"
EXPECTED_METADATA_SHA = "442b486e3bd1f5e098ab49cf4ebf990b9d2c6d3786fb66c73839ee9ce155c9b9"


def stop(msg):
    raise SystemExit("STOP: " + msg)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path):
    return [
        json.loads(x)
        for x in path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]


def rel(path):
    return str(path.relative_to(ROOT))


def committed_clean(path):
    r = subprocess.run(
        ["git", "ls-files", "--error-unmatch", rel(path)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        stop(f"not committed: {rel(path)}")

    r = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", rel(path)],
        cwd=ROOT,
    )
    if r.returncode != 0:
        stop(f"modified since commit: {rel(path)}")


def verify_protected_bindings(require_scorer_committed=False):
    required = [
        SPEC, CONTRACT, DEVIATION, RAWLOCK, META, CANON
    ]

    for p in required:
        if not p.exists():
            stop(f"missing protected artifact: {rel(p)}")

        committed_clean(p)

    bindings = {
        SPEC: EXPECTED_SPEC_SHA,
        CONTRACT: EXPECTED_CONTRACT_SHA,
        DEVIATION: EXPECTED_DEVIATION_SHA,
        RAWLOCK: EXPECTED_RAWLOCK_SHA,
        META: EXPECTED_METADATA_SHA,
        CANON: EXPECTED_CANON_SHA,
    }

    for p, expected in bindings.items():
        actual = sha(p)
        if actual != expected:
            stop(
                f"protected SHA mismatch: {rel(p)}\n"
                f"expected={expected}\nactual={actual}"
            )

    if require_scorer_committed:
        committed_clean(Path(__file__).resolve())


def load_metadata():
    with META.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 133:
        stop(f"item_metadata row count is {len(rows)}, expected 133")

    ids = [r["item_id"] for r in rows]
    if len(set(ids)) != 133:
        stop("item_metadata item IDs are not unique")

    groups = Counter(r["group"] for r in rows)
    campaigns = Counter(r["campaign"] for r in rows)

    if groups != Counter({
        "CTU_DEV": 87,
        "MUHSTIK_EXTERNAL_DEV": 46,
    }):
        stop(f"unexpected group counts: {dict(groups)}")

    if campaigns != Counter({
        "Redline": 68,
        "Remcos": 19,
        "Muhstik": 46,
    }):
        stop(f"unexpected campaign counts: {dict(campaigns)}")

    ctu_evidence = [
        r for r in rows
        if r["group"] == "CTU_DEV"
        and int(r["evidence_count"]) > 0
    ]

    if len(ctu_evidence) != 73:
        stop(
            f"CTU evidence-covered count={len(ctu_evidence)}, expected 73"
        )

    return {r["item_id"]: r for r in rows}


def verify_canonical_ids(metadata):
    rows = load_jsonl(CANON)

    if len(rows) != 133:
        stop("canonical benchmark does not contain 133 rows")

    ids = [r.get("item_id") for r in rows]

    if len(set(ids)) != 133:
        stop("canonical benchmark IDs are duplicated")

    if set(ids) != set(metadata):
        stop("canonical benchmark IDs != item_metadata IDs")


def final_logical(cand, run):
    p = RAW / f"{cand}_run{run}_logical.jsonl"

    if not p.exists():
        stop(f"missing {rel(p)}")

    history = defaultdict(list)

    for x in load_jsonl(p):
        history[x["item_id"]].append(x)

    return {
        item: rows[-1]
        for item, rows in history.items()
    }


def verify_raw_hashes():
    lock = load_json(RAWLOCK)

    protected = lock.get("raw_collection_artifact_sha256", {})

    for cand in CANDS:
        for run in [1, 2, 3]:
            for suffix in ["attempts", "logical"]:
                p = RAW / f"{cand}_run{run}_{suffix}.jsonl"
                key = rel(p)

                if key not in protected:
                    stop(f"raw lock missing artifact: {key}")

                if sha(p) != protected[key]:
                    stop(f"raw artifact SHA mismatch: {key}")


def build_pre_gt_structure(metadata):
    result = {}

    for cand in CANDS:
        by_item = defaultdict(dict)
        valid_responses = 0
        total_responses = 0

        for run in [1, 2, 3]:
            final = final_logical(cand, run)

            if set(final) != set(metadata):
                stop(f"{cand} run {run}: item IDs mismatch")

            for item, x in final.items():
                total_responses += 1

                is_valid = (
                    x.get("status") == "VALID_HTTP200"
                    and x.get("valid_exact_label") is True
                    and x.get("output") in VALID
                )

                if is_valid:
                    valid_responses += 1
                    by_item[item][run] = x["output"]
                else:
                    by_item[item][run] = None

        canonical = {}
        stable = {}

        for item in metadata:
            vals = [
                by_item[item].get(run)
                for run in [1, 2, 3]
                if by_item[item].get(run) in VALID
            ]

            counts = Counter(vals)

            if len(vals) >= 2 and counts and max(counts.values()) >= 2:
                pred = counts.most_common(1)[0][0]
            else:
                pred = None

            canonical[item] = {
                "prediction": pred,
                "valid_run_count": len(vals),
            }

            stable[item] = (
                len(vals) == 3
                and len(set(vals)) == 1
            )

        result[cand] = {
            "valid_responses": valid_responses,
            "total_responses": total_responses,
            "response_validity_rate":
                valid_responses / total_responses,
            "canonical": canonical,
            "stable": stable,
            "stability":
                sum(stable.values()) / 133,
        }

    expected = {
        "ZB1": (399, 399, 133, 0),
        "ZB2": (399, 399, 133, 0),
        "ZB3": (386, 399, 129, 4),
    }

    for cand, (v, t, cv, ci) in expected.items():
        r = result[cand]

        valid_canonical = sum(
            x["prediction"] in VALID
            for x in r["canonical"].values()
        )

        invalid_canonical = 133 - valid_canonical

        if (
            r["valid_responses"] != v
            or r["total_responses"] != t
            or valid_canonical != cv
            or invalid_canonical != ci
        ):
            stop(f"{cand}: frozen pre-GT structure changed")

    return result


def strict_recall(items, candidate, ground_truth, cls):
    denom = sum(
        ground_truth[item] == cls
        for item in items
    )

    if denom == 0:
        return None

    correct = sum(
        ground_truth[item] == cls
        and candidate[item]["prediction"] == cls
        for item in items
    )

    return correct / denom


def valid_only_recall(items, candidate, ground_truth, cls):
    eligible = [
        item for item in items
        if candidate[item]["prediction"] in VALID
        and ground_truth[item] == cls
    ]

    if not eligible:
        return None

    correct = sum(
        candidate[item]["prediction"] == cls
        for item in eligible
    )

    return correct / len(eligible)


def metric_block(items, candidate, ground_truth):
    esc = strict_recall(
        items, candidate, ground_truth, "ESCALATE"
    )

    dne = strict_recall(
        items, candidate, ground_truth, "DO_NOT_ESCALATE"
    )

    if esc is None or dne is None:
        strict_ba = None
    else:
        strict_ba = (esc + dne) / 2

    vesc = valid_only_recall(
        items, candidate, ground_truth, "ESCALATE"
    )

    vdne = valid_only_recall(
        items, candidate, ground_truth, "DO_NOT_ESCALATE"
    )

    if vesc is None or vdne is None:
        valid_only_ba = None
    else:
        valid_only_ba = (vesc + vdne) / 2

    canonical_valid = sum(
        candidate[item]["prediction"] in VALID
        for item in items
    )

    return {
        "n": len(items),
        "canonical_valid_n": canonical_valid,
        "coverage": canonical_valid / len(items),
        "strict": {
            "ESCALATE_recall": esc,
            "DO_NOT_ESCALATE_recall": dne,
            "balanced_accuracy": strict_ba,
        },
        "canonical_valid_only_sensitivity": {
            "ESCALATE_recall": vesc,
            "DO_NOT_ESCALATE_recall": vdne,
            "balanced_accuracy": valid_only_ba,
        },
    }


def class_error_block(items, candidate, ground_truth):
    out = {
        "ESCALATE": {
            "correct": 0,
            "wrong_label": 0,
            "invalid_canonical": 0,
        },
        "DO_NOT_ESCALATE": {
            "correct": 0,
            "wrong_label": 0,
            "invalid_canonical": 0,
        },
    }

    for item in items:
        gt = ground_truth[item]
        pred = candidate[item]["prediction"]

        if pred is None:
            out[gt]["invalid_canonical"] += 1
        elif pred == gt:
            out[gt]["correct"] += 1
        else:
            out[gt]["wrong_label"] += 1

    return out


def attempt_operational_stats(cand):
    latencies = []
    http_counts = Counter()
    usage_totals = defaultdict(float)
    usage_seen = set()

    for run in [1, 2, 3]:
        p = RAW / f"{cand}_run{run}_attempts.jsonl"

        for x in load_jsonl(p):
            status = x.get("http_status")
            http_counts[str(status)] += 1

            if status == 200:
                latency = x.get("latency_ms")
                if isinstance(latency, (int, float)):
                    latencies.append(float(latency))

                usage = x.get("usage")
                if isinstance(usage, dict):
                    for key in [
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                        "neurons",
                    ]:
                        value = usage.get(key)

                        if isinstance(value, (int, float)):
                            usage_totals[key] += value
                            usage_seen.add(key)

    if not latencies:
        stop(f"{cand}: no HTTP-200 latency values")

    return {
        "successful_http200_latency_n": len(latencies),
        "median_successful_http200_latency_ms": median(latencies),
        "http_status_counts": dict(http_counts),
        "usage_totals": {
            k: usage_totals[k]
            for k in sorted(usage_seen)
        },
        "comparable_total_usd_cost": None,
    }


def load_gt_after_authorization(metadata):
    deviation = load_json(DEVIATION)

    expected_gt_sha = deviation.get("ground_truth_sha256")

    if not expected_gt_sha:
        stop("deviation record lacks frozen ground-truth SHA")

    actual = sha(GT)

    if actual != expected_gt_sha:
        stop(
            "hidden ground-truth SHA changed since deviation lock"
        )

    with GT.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if set(rows[0].keys()) != {"item_id", "ground_truth"}:
        stop("unexpected ground-truth schema")

    if len(rows) != 133:
        stop(f"ground-truth rows={len(rows)}, expected 133")

    gt = {}

    for r in rows:
        item = r["item_id"]
        label = r["ground_truth"]

        if item in gt:
            stop(f"duplicate ground-truth item: {item}")

        if label not in VALID:
            stop(
                f"invalid ground-truth label for {item}: {label!r}"
            )

        gt[item] = label

    if set(gt) != set(metadata):
        stop("ground-truth IDs != frozen metadata IDs")

    return gt


def choose_winner(results):
    eligible = [
        c for c in CANDS
        if results[c]["competence"]["eligible"]
    ]

    if not eligible:
        return {
            "status": "NO_ELIGIBLE_CANDIDATE_REOPEN_GATE6C",
            "winner": None,
            "eligible_candidates": [],
        }

    if len(eligible) == 1:
        return {
            "status": "WINNER_SELECTED",
            "winner": eligible[0],
            "eligible_candidates": eligible,
            "deciding_stage": "competence_floor_only_eligible_candidate",
        }

    if len(eligible) > 2:
        stop(
            "more than two eligible candidates; frozen top-two rule "
            "requires explicit protocol review"
        )

    a, b = eligible

    def val(c, path):
        x = results[c]
        for key in path:
            x = x[key]
        if x is None:
            stop(
                f"winner metric unavailable: {c} {'/'.join(path)}"
            )
        return float(x)

    pa = val(a, ["metrics", "ctu_evidence_covered",
                 "strict", "balanced_accuracy"])
    pb = val(b, ["metrics", "ctu_evidence_covered",
                 "strict", "balanced_accuracy"])

    if abs(pa - pb) >= 0.02:
        return {
            "status": "WINNER_SELECTED",
            "winner": a if pa > pb else b,
            "eligible_candidates": eligible,
            "deciding_stage": "primary_balanced_accuracy",
        }

    ra = val(a, ["metrics", "redline",
                 "strict", "balanced_accuracy"])
    rb = val(b, ["metrics", "redline",
                 "strict", "balanced_accuracy"])

    if abs(ra - rb) >= 0.02:
        return {
            "status": "WINNER_SELECTED",
            "winner": a if ra > rb else b,
            "eligible_candidates": eligible,
            "deciding_stage": "redline_balanced_accuracy",
        }

    ma = val(a, ["metrics", "muhstik",
                 "malicious_ESCALATE_recall"])
    mb = val(b, ["metrics", "muhstik",
                 "malicious_ESCALATE_recall"])

    if abs(ma - mb) > 1e-12:
        return {
            "status": "WINNER_SELECTED",
            "winner": a if ma > mb else b,
            "eligible_candidates": eligible,
            "deciding_stage": "muhstik_malicious_recall",
        }

    sa = results[a]["stability"]
    sb = results[b]["stability"]

    if abs(sa - sb) > 1e-12:
        return {
            "status": "WINNER_SELECTED",
            "winner": a if sa > sb else b,
            "eligible_candidates": eligible,
            "deciding_stage": "three_run_stability",
        }

    la = results[a]["operational"][
        "median_successful_http200_latency_ms"
    ]
    lb = results[b]["operational"][
        "median_successful_http200_latency_ms"
    ]

    if abs(la - lb) > 1e-12:
        return {
            "status": "WINNER_SELECTED",
            "winner": a if la < lb else b,
            "eligible_candidates": eligible,
            "deciding_stage": "median_latency",
        }

    return {
        "status":
            "UNRESOLVED_TIE_COST_NOT_COMPARABLE_PROTOCOL_REVIEW_REQUIRED",
        "winner": None,
        "eligible_candidates": eligible,
        "deciding_stage": "cost",
    }


def self_audit():
    print("=== GATE 6C SCORER V1 SELF-AUDIT ===")
    print("Ground truth opened: NO")
    print("Correctness scoring performed: NO")
    print("External-TEST accessed: NO")
    print()

    verify_protected_bindings(
        require_scorer_committed=False
    )

    print("PASS: protected artifact SHA bindings")

    metadata = load_metadata()
    verify_canonical_ids(metadata)

    print("PASS: frozen benchmark strata")
    print("  CTU DEV: 87")
    print("  CTU evidence-covered: 73")
    print("  Redline: 68")
    print("  Remcos: 19")
    print("  Muhstik External-DEV: 46")

    verify_raw_hashes()
    print("PASS: raw collection hashes match all-candidate lock")

    pre = build_pre_gt_structure(metadata)

    print("PASS: canonical-vote structural precheck")
    print(
        "  ZB1:",
        f'{pre["ZB1"]["valid_responses"]}/399 valid responses,',
        "133 canonical valid"
    )
    print(
        "  ZB2:",
        f'{pre["ZB2"]["valid_responses"]}/399 valid responses,',
        "133 canonical valid"
    )
    print(
        "  ZB3:",
        f'{pre["ZB3"]["valid_responses"]}/399 valid responses,',
        "129 canonical valid / 4 invalid"
    )

    contract = load_json(CONTRACT)

    if contract.get(
        "automated_correctness_scoring_performed"
    ) is not False:
        stop("pre-scoring contract state mismatch")

    if contract.get(
        "external_test_accessed"
    ) is not False:
        stop("External-TEST protection state mismatch")

    print("PASS: pre-scoring contract state")
    print()
    print("SELF-AUDIT: PASS")
    print("Ground truth opened: NO")
    print("Correctness scoring performed: NO")


def score():
    verify_protected_bindings(
        require_scorer_committed=True
    )

    verify_raw_hashes()

    metadata = load_metadata()
    verify_canonical_ids(metadata)

    pre = build_pre_gt_structure(metadata)

    # First and only point at which correctness ground truth is loaded.
    gt = load_gt_after_authorization(metadata)

    ctu = [
        i for i, m in metadata.items()
        if m["group"] == "CTU_DEV"
    ]

    ctu_ec = [
        i for i, m in metadata.items()
        if m["group"] == "CTU_DEV"
        and int(m["evidence_count"]) > 0
    ]

    redline = [
        i for i, m in metadata.items()
        if m["group"] == "CTU_DEV"
        and m["campaign"] == "Redline"
    ]

    remcos = [
        i for i, m in metadata.items()
        if m["group"] == "CTU_DEV"
        and m["campaign"] == "Remcos"
    ]

    muhstik = [
        i for i, m in metadata.items()
        if m["group"] == "MUHSTIK_EXTERNAL_DEV"
    ]

    results = {}

    for cand in CANDS:
        canonical = pre[cand]["canonical"]

        metrics = {
            "ctu_evidence_covered":
                metric_block(ctu_ec, canonical, gt),

            "ctu_overall":
                metric_block(ctu, canonical, gt),

            "redline":
                metric_block(redline, canonical, gt),

            "remcos":
                metric_block(remcos, canonical, gt),
        }

        muh_esc_denom = sum(
            gt[i] == "ESCALATE"
            for i in muhstik
        )

        if muh_esc_denom == 0:
            stop("Muhstik has zero ESCALATE ground-truth cases")

        muh_esc_correct = sum(
            gt[i] == "ESCALATE"
            and canonical[i]["prediction"] == "ESCALATE"
            for i in muhstik
        )

        muh_recall = muh_esc_correct / muh_esc_denom

        metrics["muhstik"] = {
            "n": len(muhstik),
            "malicious_ESCALATE_ground_truth_n":
                muh_esc_denom,
            "malicious_ESCALATE_correct_n":
                muh_esc_correct,
            "malicious_ESCALATE_recall":
                muh_recall,
            "canonical_valid_n":
                sum(
                    canonical[i]["prediction"] in VALID
                    for i in muhstik
                ),
        }

        validity_rate = pre[cand][
            "response_validity_rate"
        ]

        ctu_preds = {
            canonical[i]["prediction"]
            for i in ctu
            if canonical[i]["prediction"] in VALID
        }

        primary_ba = metrics[
            "ctu_evidence_covered"
        ]["strict"]["balanced_accuracy"]

        validity_pass = validity_rate >= 0.99
        both_classes_pass = ctu_preds == VALID
        primary_pass = (
            primary_ba is not None
            and primary_ba > 0.50
        )

        competence = {
            "response_validity_rate":
                validity_rate,
            "response_validity_at_least_99_percent":
                validity_pass,
            "ctu_canonical_contains_both_classes":
                both_classes_pass,
            "ctu_evidence_covered_balanced_accuracy_gt_0_50":
                primary_pass,
            "eligible":
                validity_pass
                and both_classes_pass
                and primary_pass,
        }

        results[cand] = {
            "valid_logical_responses":
                pre[cand]["valid_responses"],
            "total_logical_responses":
                pre[cand]["total_responses"],
            "invalid_logical_response_rate":
                1.0 - validity_rate,
            "canonical_valid_items":
                sum(
                    x["prediction"] in VALID
                    for x in canonical.values()
                ),
            "canonical_invalid_items":
                sum(
                    x["prediction"] is None
                    for x in canonical.values()
                ),
            "stability":
                pre[cand]["stability"],
            "metrics":
                metrics,
            "class_specific_errors_ctu":
                class_error_block(
                    ctu, canonical, gt
                ),
            "competence":
                competence,
            "operational":
                attempt_operational_stats(cand),
        }

    winner = choose_winner(results)

    payload = {
        "status": "GATE6C_FROZEN_SCORING_EXECUTED",
        "scored_utc":
            datetime.now(timezone.utc).isoformat(),
        "scorer_sha256":
            sha(Path(__file__).resolve()),
        "scoring_spec_sha256":
            sha(SPEC),
        "pre_scoring_contract_sha256":
            sha(CONTRACT),
        "raw_collection_lock_sha256":
            sha(RAWLOCK),
        "ground_truth_sha256":
            sha(GT),
        "item_metadata_sha256":
            sha(META),
        "candidates":
            results,
        "winner_decision":
            winner,
        "external_test_accessed":
            False,
    }

    OUTDIR.mkdir(parents=True, exist_ok=True)

    if SUMMARY_OUT.exists() or ITEM_OUT.exists():
        stop(
            "scoring output already exists; refusing overwrite"
        )

    SUMMARY_OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    with ITEM_OUT.open(
        "w",
        newline="",
        encoding="utf-8"
    ) as f:
        fields = [
            "item_id",
            "group",
            "campaign",
            "evidence_count",
            "ground_truth",
            "ZB1_prediction",
            "ZB1_valid_runs",
            "ZB1_correct",
            "ZB2_prediction",
            "ZB2_valid_runs",
            "ZB2_correct",
            "ZB3_prediction",
            "ZB3_valid_runs",
            "ZB3_correct",
        ]

        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()

        for item in sorted(metadata):
            row = {
                "item_id": item,
                "group": metadata[item]["group"],
                "campaign": metadata[item]["campaign"],
                "evidence_count":
                    metadata[item]["evidence_count"],
                "ground_truth": gt[item],
            }

            for cand in CANDS:
                cp = pre[cand]["canonical"][item]
                pred = cp["prediction"]

                row[f"{cand}_prediction"] = (
                    pred
                    if pred is not None
                    else "INVALID_FOR_CANDIDATE"
                )

                row[f"{cand}_valid_runs"] = (
                    cp["valid_run_count"]
                )

                row[f"{cand}_correct"] = (
                    pred == gt[item]
                    if pred is not None
                    else False
                )

            w.writerow(row)

    print("=== GATE 6C SCORING COMPLETE ===")

    for cand in CANDS:
        r = results[cand]

        print()
        print(cand)
        print(
            "  response validity:",
            f'{100*r["competence"]["response_validity_rate"]:.3f}%'
        )
        print(
            "  primary CTU evidence-covered BA:",
            f'{r["metrics"]["ctu_evidence_covered"]["strict"]["balanced_accuracy"]:.6f}'
        )
        print(
            "  CTU overall BA:",
            f'{r["metrics"]["ctu_overall"]["strict"]["balanced_accuracy"]:.6f}'
        )
        print(
            "  Redline BA:",
            f'{r["metrics"]["redline"]["strict"]["balanced_accuracy"]:.6f}'
        )
        print(
            "  Remcos BA:",
            f'{r["metrics"]["remcos"]["strict"]["balanced_accuracy"]:.6f}'
        )
        print(
            "  Muhstik malicious recall:",
            f'{r["metrics"]["muhstik"]["malicious_ESCALATE_recall"]:.6f}'
        )
        print(
            "  stability:",
            f'{r["stability"]:.6f}'
        )
        print(
            "  eligible:",
            r["competence"]["eligible"]
        )

    print()
    print("Winner decision:", winner)
    print("Summary:", rel(SUMMARY_OUT))
    print("Items:", rel(ITEM_OUT))
    print("Summary SHA256:", sha(SUMMARY_OUT))
    print("Items SHA256:", sha(ITEM_OUT))
    print("External-TEST accessed: NO")


def main():
    ap = argparse.ArgumentParser()

    group = ap.add_mutually_exclusive_group(
        required=True
    )

    group.add_argument(
        "--self-audit",
        action="store_true"
    )

    group.add_argument(
        "--score",
        action="store_true"
    )

    ap.add_argument(
        "--confirm",
        default=""
    )

    args = ap.parse_args()

    if args.self_audit:
        self_audit()
        return

    if args.score:
        if args.confirm != (
            "OPEN_FROZEN_GATE6C_GROUND_TRUTH"
        ):
            stop(
                "scoring requires --confirm "
                "OPEN_FROZEN_GATE6C_GROUND_TRUTH"
            )

        score()
        return


if __name__ == "__main__":
    main()
