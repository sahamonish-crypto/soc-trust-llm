import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(".")
OUT = Path("benchmarks/gate6c")
OUT.mkdir(parents=True, exist_ok=True)

CTU_INV = Path("data/processed/gate6/gate6_dev_inventory.csv")
MUH_INV = Path(
    "data/processed/gate6/freeze/muhstik_external_dev_46.csv"
)

# Authoritative sources only.
SOURCES = {
    "Redline": Path(
        "data/processed/gate6/"
        "windows7full2-2023-02-21-suricata-root/eve.json"
    ),
    "Remcos": Path(
        "data/processed/gate6/"
        "windows7full3-2023-02-22-verified-suricata-root/eve.json"
    ),
    "Muhstik": Path(
        "data/processed/gate6/"
        "iot23-external/muhstik3-suricata/eve.json"
    ),
}

WINDOW = 30.0
BUDGET = 6

WHITELIST = {
    "dns",
    "http",
    "tls",
    "fileinfo",
    "smb",
    "dcerpc",
    "rdp",
    "ldap",
    "krb5",
    "kerberos",
    "ssh",
}

# Keys excluded from evidence-pattern identity because they are
# transaction/session/stream identifiers rather than substantive
# application-level factual content.
VOLATILE_PAYLOAD_KEYS = {
    "id",
    "tx_id",
    "flow_id",
    "stream_id",
    "sid",
    "call_id",
    "session_id",
    "tree_id",
    "message_id",
    "packet",
    "pcap_cnt",
}


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json(obj):
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def epoch(ts):
    return datetime.fromisoformat(
        ts.replace("Z", "+00:00")
    ).timestamp()


def endpoint_pair(x):
    a = x.get("src_ip")
    b = x.get("dest_ip")

    if not a or not b:
        return None

    return tuple(sorted((str(a), str(b))))


def prune(obj):
    if isinstance(obj, dict):
        return {
            str(k): prune(v)
            for k, v in sorted(obj.items())
            if k not in VOLATILE_PAYLOAD_KEYS
            and v is not None
        }

    if isinstance(obj, list):
        return [prune(v) for v in obj]

    return obj


def evidence_payload(event):
    et = event["event_type"]
    raw = event.get(et, {})

    payload = prune(raw)

    # Factual application-layer payload only.
    # Transport source ports and timestamps are deliberately omitted
    # from pattern identity.
    return {
        "event_type": et,
        "facts": payload,
    }


def alert_card(a):
    alert = a.get("alert", {})

    card = {
        "timestamp_utc": a.get("timestamp"),
        "signature": alert.get("signature"),
        "category": alert.get("category"),
        "severity": alert.get("severity"),
        "protocol": a.get("proto"),
        "app_protocol": a.get("app_proto"),
        "source_ip": a.get("src_ip"),
        "source_port": a.get("src_port"),
        "destination_ip": a.get("dest_ip"),
        "destination_port": a.get("dest_port"),
    }

    return {
        k: v
        for k, v in card.items()
        if v is not None
    }


# ============================================================
# Load frozen inventories
# ============================================================

with CTU_INV.open(
    newline="",
    encoding="utf-8"
) as f:
    ctu_rows = list(csv.DictReader(f))

with MUH_INV.open(
    newline="",
    encoding="utf-8"
) as f:
    muh_rows = list(csv.DictReader(f))

assert len(ctu_rows) == 87
assert len(muh_rows) == 46

items = []

# Stable deterministic ordering.
ctu_rows = sorted(
    ctu_rows,
    key=lambda r: (
        r["campaign"],
        r["community_id"],
    ),
)

for i, r in enumerate(ctu_rows, start=1):

    label = r["ground_truth_label"].strip().lower()

    if label == "malicious":
        gt = "ESCALATE"
    elif label == "benign":
        gt = "DO_NOT_ESCALATE"
    else:
        raise RuntimeError(
            f"Unexpected CTU GT label: {r['ground_truth_label']}"
        )

    items.append({
        "item_id": f"DEV-CTU-{i:03d}",
        "dataset": "CTU-SME-11",
        "group": "CTU_DEV",
        "campaign": r["campaign"],
        "community_id": r["community_id"],
        "source_path": SOURCES[r["campaign"]],
        "ground_truth": gt,
        "episode_id": "",
        "frozen_anchor": None,
    })


muh_rows = sorted(
    muh_rows,
    key=lambda r: r["episode_id"],
)

for i, r in enumerate(muh_rows, start=1):

    items.append({
        "item_id": f"DEV-MUH-{i:03d}",
        "dataset": "IoT-23",
        "group": "MUHSTIK_EXTERNAL_DEV",
        "campaign": "Muhstik",
        "community_id": r["community_id"],
        "source_path": SOURCES["Muhstik"],
        "ground_truth": "ESCALATE",
        "episode_id": r["episode_id"],
        "frozen_anchor": float(r["anchor_epoch"]),
    })


assert len(items) == 133
assert len({x["item_id"] for x in items}) == 133
assert len({x["community_id"] for x in items}) == 133


# ============================================================
# Group by authoritative EVE source
# ============================================================

by_source = defaultdict(list)

for item in items:
    by_source[item["source_path"]].append(item)


# ============================================================
# First pass: find alert + flow for every frozen CID
# ============================================================

alerts = defaultdict(list)
flows = defaultdict(list)

for path, source_items in by_source.items():

    wanted = {
        x["community_id"]
        for x in source_items
    }

    with path.open(
        encoding="utf-8",
        errors="replace"
    ) as f:

        for line in f:

            try:
                x = json.loads(line)
            except Exception:
                continue

            cid = x.get("community_id")

            if cid not in wanted:
                continue

            et = x.get("event_type")

            if et == "alert":
                alerts[cid].append(x)

            elif et == "flow":
                flows[cid].append(x)


# ============================================================
# Resolve deterministic primary alert, anchor, endpoint pair
# ============================================================

for item in items:

    cid = item["community_id"]

    if not alerts[cid]:
        raise RuntimeError(
            f"No alert event for frozen CID {cid}"
        )

    if not flows[cid]:
        raise RuntimeError(
            f"No flow event for frozen CID {cid}"
        )

    def alert_sort_key(a):
        return (
            epoch(a["timestamp"]),
            a.get("alert", {}).get("signature", ""),
        )

    primary = min(
        alerts[cid],
        key=alert_sort_key,
    )

    anchor = epoch(primary["timestamp"])

    flow = next(
        (
            x for x in flows[cid]
            if x.get("flow", {}).get("start")
        ),
        flows[cid][0],
    )

    pair = endpoint_pair(flow)

    if pair is None:
        raise RuntimeError(
            f"No endpoint pair for {cid}"
        )

    # Frozen Muhstik representative inventory must reproduce.
    if item["frozen_anchor"] is not None:
        if abs(anchor - item["frozen_anchor"]) > 0.001:
            raise RuntimeError(
                "Muhstik frozen anchor mismatch: "
                f"{item['item_id']} "
                f"{anchor} vs {item['frozen_anchor']}"
            )

    item["primary_alert"] = primary
    item["anchor"] = anchor
    item["pair"] = pair


# ============================================================
# Second pass:
# frozen ±30 s retrieval
# exact CID first, same endpoint pair second
# ============================================================

items_by_cid = defaultdict(list)
items_by_pair = defaultdict(list)

for item in items:
    items_by_cid[
        item["community_id"]
    ].append(item)

    items_by_pair[
        item["pair"]
    ].append(item)

# Per item, pattern key -> aggregation record.
pattern_groups = {
    item["item_id"]: {}
    for item in items
}


for path, source_items in by_source.items():

    source_item_ids = {
        x["item_id"]
        for x in source_items
    }

    with path.open(
        encoding="utf-8",
        errors="replace"
    ) as f:

        for line in f:

            try:
                x = json.loads(line)
            except Exception:
                continue

            et = x.get("event_type")

            if et not in WHITELIST:
                continue

            ts = x.get("timestamp")

            if not ts:
                continue

            try:
                t = epoch(ts)
            except Exception:
                continue

            cid = x.get("community_id")
            pair = endpoint_pair(x)

            candidate_items = {}

            # Exact CID has priority 0.
            for item in items_by_cid.get(cid, []):
                if item["item_id"] in source_item_ids:
                    candidate_items[
                        item["item_id"]
                    ] = (item, 0, "exact_flow")

            # Endpoint-pair evidence has priority 1.
            for item in items_by_pair.get(pair, []):
                if item["item_id"] not in source_item_ids:
                    continue

                # Do not duplicate an exact event as pair evidence.
                if item["item_id"] not in candidate_items:
                    candidate_items[
                        item["item_id"]
                    ] = (
                        item,
                        1,
                        "endpoint_pair",
                    )

            if not candidate_items:
                continue

            payload = evidence_payload(x)
            pattern_key = canonical_json(payload)

            for item, priority, relation in (
                v for v in candidate_items.values()
            ):

                delta = t - item["anchor"]

                if delta < -WINDOW or delta > WINDOW:
                    continue

                groups = pattern_groups[
                    item["item_id"]
                ]

                rec = groups.get(pattern_key)

                observation = {
                    "priority": priority,
                    "relation": relation,
                    "delta": delta,
                }

                if rec is None:
                    groups[pattern_key] = {
                        "payload": payload,
                        "priority": priority,
                        "relation": relation,
                        "first_delta": delta,
                        "last_delta": delta,
                        "closest_abs_delta": abs(delta),
                        "occurrence_count": 1,
                    }

                else:
                    rec["occurrence_count"] += 1
                    rec["first_delta"] = min(
                        rec["first_delta"],
                        delta,
                    )
                    rec["last_delta"] = max(
                        rec["last_delta"],
                        delta,
                    )

                    candidate_rank = (
                        priority,
                        abs(delta),
                        delta,
                    )

                    current_rank = (
                        rec["priority"],
                        rec["closest_abs_delta"],
                        rec["first_delta"],
                    )

                    if candidate_rank < current_rank:
                        rec["priority"] = priority
                        rec["relation"] = relation
                        rec["closest_abs_delta"] = abs(delta)


# ============================================================
# Freeze max 6 deterministic evidence patterns
# ============================================================

for item in items:

    groups = list(
        pattern_groups[
            item["item_id"]
        ].values()
    )

    groups.sort(
        key=lambda r: (
            r["priority"],
            r["closest_abs_delta"],
            canonical_json(r["payload"]),
        )
    )

    selected = groups[:BUDGET]

    bundle = []

    for idx, rec in enumerate(
        selected,
        start=1,
    ):
        bundle.append({
            "evidence_id": f"E{idx}",
            "relation": rec["relation"],
            "event_type": rec["payload"]["event_type"],
            "facts": rec["payload"]["facts"],
            "occurrence_count": rec["occurrence_count"],
            "first_offset_seconds": round(
                rec["first_delta"],
                3,
            ),
            "last_offset_seconds": round(
                rec["last_delta"],
                3,
            ),
        })

    item["evidence"] = bundle

    evidence_bytes = canonical_json(
        bundle
    ).encode("utf-8")

    item["evidence_hash"] = sha256_bytes(
        evidence_bytes
    )


# ============================================================
# Canonical prompt
# ============================================================

SYSTEM_PROMPT = """You are assisting Tier-1 Security Operations Center alert triage.

Use only the supplied alert and evidence. Do not assume facts that are not present.

Decide whether this case warrants escalation for further security investigation.

Return exactly one of these two labels and nothing else:

ESCALATE
DO_NOT_ESCALATE

Do not provide confidence, probability, explanation, rationale, or additional text."""

PROMPT_PATH = OUT / "canonical_prompt.txt"
PROMPT_PATH.write_text(
    SYSTEM_PROMPT + "\n",
    encoding="utf-8",
)


def build_user_message(item):

    card = alert_card(
        item["primary_alert"]
    )

    if item["evidence"]:
        evidence_obj = item["evidence"]
    else:
        evidence_obj = (
            "NO_ADDITIONAL_EVIDENCE_AVAILABLE"
        )

    return (
        "ALERT\n"
        + json.dumps(
            card,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n\nEVIDENCE\n"
        + (
            json.dumps(
                evidence_obj,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            if not isinstance(
                evidence_obj,
                str,
            )
            else evidence_obj
        )
        + "\n\nDECISION\n"
        + "Return exactly ESCALATE or DO_NOT_ESCALATE."
    )


# ============================================================
# Write model-visible inputs
# ============================================================

MODEL_INPUT = OUT / "canonical_model_inputs.jsonl"

with MODEL_INPUT.open(
    "w",
    encoding="utf-8",
) as f:

    for item in items:

        record = {
            "item_id": item["item_id"],
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": build_user_message(item),
                },
            ],
        }

        f.write(
            canonical_json(record)
            + "\n"
        )


# ============================================================
# Write hidden GT
# ============================================================

GT_PATH = OUT / "hidden_ground_truth.csv"

with GT_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    w = csv.writer(f)

    w.writerow([
        "item_id",
        "ground_truth",
    ])

    for item in items:
        w.writerow([
            item["item_id"],
            item["ground_truth"],
        ])


# ============================================================
# Non-model metadata
# ============================================================

META_PATH = OUT / "item_metadata.csv"

with META_PATH.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    w = csv.writer(f)

    w.writerow([
        "item_id",
        "dataset",
        "group",
        "campaign",
        "episode_id",
        "community_id",
        "authoritative_eve_source",
        "evidence_count",
        "evidence_hash",
    ])

    for item in items:

        w.writerow([
            item["item_id"],
            item["dataset"],
            item["group"],
            item["campaign"],
            item["episode_id"],
            item["community_id"],
            str(item["source_path"]),
            len(item["evidence"]),
            item["evidence_hash"],
        ])


# ============================================================
# Scoring specification
# ============================================================

SCORING = """# Gate 6C Model Benchmark Scoring Specification

Status: candidate specification generated before any model call.

## Candidate models

- gpt-6.1-sol
- claude-sonnet-5-5
- deepseek-v4-pro

The exact provider model identifier/version used in execution must be
recorded.

External tools, browsing, retrieval services, and provider-side search
must be disabled.

## Benchmark material

Canonical DEV package:

- CTU DEV: 87 cases
- Muhstik External-DEV: 46 frozen temporal representatives
- Total: 133 cases

Held-out External-TEST is not part of this package and must not be
accessed during model selection:

- hideandseek1
- mirai34
- trojan42

## Model-visible information

Each model receives exactly:

1. the same frozen system prompt;
2. one deterministic alert card;
3. the same frozen Gate 6B evidence bundle.

Ground truth, attack labels, model correctness, confidence, uncertainty,
campaign name, dataset name, episode ID, and source metadata are not
included in the model-visible input.

## Output

Exactly one label:

ESCALATE

or

DO_NOT_ESCALATE

Any other output is invalid.

## Repeated-run stability

Each candidate model is evaluated three times on every item under the
lowest practically available stochasticity setting.

The exact temperature / reasoning / seed / sampling configuration must
be recorded for each provider.

Canonical recommendation for an item:

majority vote of the three valid runs.

Stability:

fraction of items for which all three runs return the same valid label.

No model may be given feedback about correctness between runs.

## Primary competence metric

Primary metric:

balanced accuracy on the CTU DEV items that have non-empty frozen Gate
6B evidence.

Expected evidence-covered CTU subset: 73 cases.

Balanced accuracy:

(mean of ESCALATE recall and DO_NOT_ESCALATE recall)

This prevents the 75/12 CTU class imbalance from making raw accuracy the
primary model-selection metric.

## Mandatory sensitivity analyses

Report separately:

1. CTU overall balanced accuracy on all 87 CTU DEV cases.
2. Redline-only balanced accuracy.
3. Remcos-only balanced accuracy.
4. class-specific error counts.
5. invalid-output rate.
6. Muhstik External-DEV malicious recall.
7. three-run stability.
8. latency.
9. estimated/provider-reported cost.

Remcos is treated as a smoke/stability subset because some Remcos alert
signatures are unusually explicit. A model must not be selected solely
because of strong Remcos performance.

Muhstik is an external robustness subset and must not simply be pooled
with CTU DEV to create a larger weighted accuracy score.

## Competence floor

A candidate is eligible for winner selection only if:

1. at least 99% of all benchmark responses are valid labels;
2. its canonical predictions contain both decision classes on CTU DEV;
3. CTU evidence-covered balanced accuracy is greater than 0.50.

If every primary candidate fails the competence floor, Gate 6C is
reopened and the previously approved escalation model may be evaluated.

## Winner rule

Among eligible primary candidates:

1. higher CTU evidence-covered balanced accuracy wins;
2. if the difference between the top two is < 0.02, use higher
   Redline-only balanced accuracy;
3. if still tied within < 0.02, use higher Muhstik malicious recall;
4. if still tied, use higher three-run stability;
5. if still tied, use lower median latency;
6. if still tied, use lower total benchmark cost.

The winner must remain naturally fallible. No errors may be injected or
labels manually flipped.

The final winning model/configuration, canonical recommendation for each
item, provider identifiers, timestamps, and hashes must be frozen before
later calibration or human-study use.
"""

SCORING_PATH = OUT / "scoring_spec.md"
SCORING_PATH.write_text(
    SCORING,
    encoding="utf-8",
)


# ============================================================
# Audit
# ============================================================

ctu = [
    x for x in items
    if x["group"] == "CTU_DEV"
]

muh = [
    x for x in items
    if x["group"]
    == "MUHSTIK_EXTERNAL_DEV"
]

ctu_evidence = [
    x for x in ctu
    if len(x["evidence"]) > 0
]

muh_evidence = [
    x for x in muh
    if len(x["evidence"]) > 0
]

by_campaign = Counter(
    x["campaign"]
    for x in ctu
)

gt_ctu = Counter(
    x["ground_truth"]
    for x in ctu
)

all_gt = Counter(
    x["ground_truth"]
    for x in items
)

# Structural leakage scan: forbidden hidden-data field names must
# never appear in the serialized model package.
model_text = MODEL_INPUT.read_text(
    encoding="utf-8"
).lower()

forbidden_tokens = [
    "ground_truth",
    "ground truth",
    "gt_detail",
    "expected_label",
    "correct_label",
    "muhstik_external_dev",
    "ctu-sme-11",
]

leak_hits = [
    token
    for token in forbidden_tokens
    if token in model_text
]

print("=" * 78)
print("GATE 6C CANONICAL BENCHMARK BUILD")
print("=" * 78)

print("Total model inputs:", len(items))
print("CTU DEV:", len(ctu))
print("Muhstik External-DEV:", len(muh))

print()
print("CTU campaigns:")
for k, n in by_campaign.items():
    print(f"  {k}: {n}")

print()
print("CTU GT:")
for k, n in gt_ctu.items():
    print(f"  {k}: {n}")

print()
print("All-package GT:")
for k, n in all_gt.items():
    print(f"  {k}: {n}")

print()
print("Evidence coverage:")
print(
    "  CTU with non-empty evidence:",
    len(ctu_evidence),
    "/ 87"
)
print(
    "  Muhstik with non-empty evidence:",
    len(muh_evidence),
    "/ 46"
)

print()
print("Structural hidden-data leakage scan:")
print(
    "  hits:",
    leak_hits if leak_hits else "NONE"
)

expected = {
    "total_133": len(items) == 133,
    "ctu_87": len(ctu) == 87,
    "muh_46": len(muh) == 46,
    "ctu_evidence_73": len(ctu_evidence) == 73,
    "muh_evidence_46": len(muh_evidence) == 46,
    "redline_68": by_campaign["Redline"] == 68,
    "remcos_19": by_campaign["Remcos"] == 19,
    "ctu_escalate_12": gt_ctu["ESCALATE"] == 12,
    "ctu_no_75": gt_ctu["DO_NOT_ESCALATE"] == 75,
    "no_hidden_field_leak": len(leak_hits) == 0,
}

print()
print("VERIFICATION")

for k, ok in expected.items():
    print(
        f"  {k}:",
        "PASS" if ok else "FAIL"
    )

if not all(expected.values()):
    print()
    print("PACKAGE STATUS: FAIL")
    raise SystemExit(2)


# ============================================================
# Build report
# ============================================================

REPORT = OUT / "build_report.txt"

with REPORT.open(
    "w",
    encoding="utf-8",
) as f:

    f.write(
        "Gate 6C canonical benchmark build\n"
    )
    f.write("===============================\n\n")
    f.write("Total items: 133\n")
    f.write("CTU DEV: 87\n")
    f.write("Muhstik External-DEV: 46\n")
    f.write(
        f"CTU evidence-covered: {len(ctu_evidence)}\n"
    )
    f.write(
        f"Muhstik evidence-covered: {len(muh_evidence)}\n"
    )
    f.write(
        "External-TEST accessed: NO\n"
    )
    f.write(
        "Authoritative Remcos EVE: "
        "windows7full3-2023-02-22-verified-suricata-root/eve.json\n"
    )
    f.write(
        "Frozen retrieval: ±30 s, exact CID first, endpoint pair second, "
        "max 6 pattern-level factual evidence items\n"
    )
    f.write(
        "Package verification: PASS\n"
    )


# ============================================================
# Hash manifest
# ============================================================

MANIFEST = OUT / "manifest.sha256"

manifest_paths = [
    Path(
        "scripts/gate6/"
        "build_gate6c_benchmark.py"
    ),
    CTU_INV,
    MUH_INV,
    SOURCES["Redline"],
    SOURCES["Remcos"],
    SOURCES["Muhstik"],
    PROMPT_PATH,
    MODEL_INPUT,
    GT_PATH,
    META_PATH,
    SCORING_PATH,
    REPORT,
]

with MANIFEST.open(
    "w",
    encoding="utf-8",
) as f:

    for path in manifest_paths:
        f.write(
            f"{sha256_file(path)}  {path}\n"
        )


print()
print("=" * 78)
print("PACKAGE HASHES")
print("=" * 78)

for path in [
    PROMPT_PATH,
    MODEL_INPUT,
    GT_PATH,
    META_PATH,
    SCORING_PATH,
    REPORT,
    MANIFEST,
]:
    print(
        sha256_file(path),
        path
    )

print()
print("=" * 78)
print("PACKAGE STATUS")
print("=" * 78)

print("Canonical model inputs: 133")
print("External-TEST accessed: NO")
print("Ground truth hidden from model inputs: YES")
print("Gate 6B evidence configuration preserved: YES")
print("Three-model benchmark executed: NO")
print("Gate 6C model winner: OPEN")
print("PACKAGE VERIFICATION: PASS")
