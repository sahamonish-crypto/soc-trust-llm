#!/usr/bin/env python3

from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import csv
import hashlib
import json
import shutil

ROOT = Path(".")
OUT = Path("benchmarks/gate6d/canonical_v1")
HIDDEN = OUT / "hidden"

INVENTORY = Path(
    "data/processed/gate6/gate6_partition_inventory_items.csv"
)

SOURCE_BINDING = Path(
    "benchmarks/gate6d/GATE6D_CANONICAL_SOURCE_BINDING_V1.json"
)

BOUNDARY = Path(
    "benchmarks/gate6d/GATE6D_CALIBRATION_DATA_BOUNDARY_V1.json"
)

PROTOCOL = Path(
    "benchmarks/gate6d/GATE6D_UNCERTAINTY_ESTIMATOR_PROTOCOL_V1.json"
)

VALIDITY = Path(
    "benchmarks/gate6d/GATE6D_ALERT_CARD_VALIDITY_FREEZE_V1.json"
)

GATE6C_PROMPT = Path(
    "benchmarks/gate6c/canonical_prompt.txt"
)

EXPECTED_INVENTORY_SHA = (
    "84975b00dfcd012e4f2f7ec0ad7b2cb820217753e39239fdef555208e78f1dde"
)

EXPECTED_PROMPT_SHA = (
    "58c21362374142766269d0b11cba538b257a16a82df9f4bc679329c1deafd3c0"
)

DEV_CAPTURES = {
    "AmazonEcho-2023-02-21",
    "Windows7AD-2023-02-21",
}

EVAL_CAPTURES = {
    "Windows7AD-2023-02-22",
}

WINDOW = 30.0
BUDGET = 6
N_FOLDS = 5

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


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
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


def ground_truth_to_label(raw):
    x = str(raw).strip().lower()

    if x == "malicious":
        return "ESCALATE"

    if x == "benign":
        return "DO_NOT_ESCALATE"

    raise RuntimeError(
        f"Unexpected ground-truth label value: {raw!r}"
    )


def sc5_seed(item_id):
    """
    Frozen Gate 6D SC5 seed derivation.

    digest = SHA256(
        UTF8("GATE6D_SC5_V1|" + item_id)
    )

    Take first 4 bytes as unsigned big-endian integer,
    clear the sign bit to obtain [0, 2^31-1],
    and replace zero with one.
    """
    b = hashlib.sha256(
        (
            "GATE6D_SC5_V1|"
            + item_id
        ).encode("utf-8")
    ).digest()

    value = int.from_bytes(
        b[:4],
        "big",
        signed=False,
    ) & 0x7FFFFFFF

    return value if value != 0 else 1


def group_hash(capture, episode):
    return hashlib.sha256(
        (
            "GATE6D_FOLD_GROUP_V1|"
            + capture
            + "|"
            + episode
        ).encode("utf-8")
    ).hexdigest()


def assign_dev_folds(dev_items):
    """
    Outcome-blind deterministic grouped allocation.

    Group:
      capture + episode_start_utc

    Inputs used for assignment:
      - capture identity
      - episode identity
      - group size
      - current fold item/group load

    Explicitly NOT used:
      - ground truth
      - model predictions
      - model correctness
      - confidence
      - calibration performance
    """

    groups = defaultdict(list)

    for item in dev_items:
        key = (
            item["capture"],
            item["episode_start_utc"],
        )
        groups[key].append(item)

    ordered = sorted(
        groups.items(),
        key=lambda kv: (
            -len(kv[1]),
            kv[0][0],
            group_hash(
                kv[0][0],
                kv[0][1],
            ),
            kv[0][1],
        ),
    )

    fold_total_items = {
        f: 0
        for f in range(1, N_FOLDS + 1)
    }

    fold_group_count = {
        f: 0
        for f in range(1, N_FOLDS + 1)
    }

    fold_capture_items = {
        f: Counter()
        for f in range(1, N_FOLDS + 1)
    }

    assignments = {}

    for (
        capture,
        episode,
    ), members in ordered:

        chosen = min(
            range(1, N_FOLDS + 1),
            key=lambda f: (
                fold_capture_items[f][capture],
                fold_total_items[f],
                fold_group_count[f],
                f,
            ),
        )

        assignments[
            (capture, episode)
        ] = chosen

        n = len(members)

        fold_capture_items[
            chosen
        ][capture] += n

        fold_total_items[
            chosen
        ] += n

        fold_group_count[
            chosen
        ] += 1

    return (
        assignments,
        fold_total_items,
        fold_group_count,
        fold_capture_items,
        groups,
    )


def write_jsonl(path, records):
    with path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:

        for record in records:
            f.write(
                canonical_json(record)
                + "\n"
            )


def write_csv(path, fieldnames, records):
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            lineterminator="\n",
        )

        writer.writeheader()
        writer.writerows(records)


# ============================================================
# Preflight
# ============================================================

required = [
    INVENTORY,
    SOURCE_BINDING,
    BOUNDARY,
    PROTOCOL,
    VALIDITY,
    GATE6C_PROMPT,
]

missing = [
    p for p in required
    if not p.exists()
]

if missing:
    raise RuntimeError(
        "Missing required artifacts: "
        + ", ".join(str(p) for p in missing)
    )

if sha256_file(INVENTORY) != EXPECTED_INVENTORY_SHA:
    raise RuntimeError(
        "Gate 6 partition inventory SHA mismatch."
    )

if sha256_file(GATE6C_PROMPT) != EXPECTED_PROMPT_SHA:
    raise RuntimeError(
        "Frozen Gate 6C prompt SHA mismatch."
    )

prompt_file_text = GATE6C_PROMPT.read_text(
    encoding="utf-8"
)

if not prompt_file_text.endswith("\n"):
    raise RuntimeError(
        "Frozen Gate 6C prompt lacks expected trailing newline."
    )

SYSTEM_PROMPT = prompt_file_text[:-1]

# Avoid accidentally accepting an extra blank line.
if SYSTEM_PROMPT.endswith("\n"):
    raise RuntimeError(
        "Unexpected multiple trailing newlines in Gate 6C prompt."
    )


# ============================================================
# Load canonical source bindings
# ============================================================

binding = json.loads(
    SOURCE_BINDING.read_text(
        encoding="utf-8"
    )
)

source_records = binding[
    "selected_sources"
]

SOURCE_BY_CAPTURE = {}

for capture in (
    DEV_CAPTURES
    | EVAL_CAPTURES
):
    rec = source_records[capture]

    path = Path(rec["path"])

    if not path.exists():
        raise RuntimeError(
            f"Missing frozen source: {path}"
        )

    actual = sha256_file(path)
    expected = rec["expected_sha256"]

    if actual != expected:
        raise RuntimeError(
            "Frozen source SHA mismatch: "
            f"{path}"
        )

    SOURCE_BY_CAPTURE[
        capture
    ] = path


# ============================================================
# Load frozen eligible inventory
# ============================================================

with INVENTORY.open(
    newline="",
    encoding="utf-8",
) as f:
    rows = list(
        csv.DictReader(f)
    )

eligible = [
    r for r in rows
    if str(
        r["rich_context"]
    ).strip() == "1"
    and r["capture"]
    in (
        DEV_CAPTURES
        | EVAL_CAPTURES
    )
]

dev_rows = [
    r for r in eligible
    if r["capture"]
    in DEV_CAPTURES
]

eval_rows = [
    r for r in eligible
    if r["capture"]
    in EVAL_CAPTURES
]

if len(dev_rows) != 1222:
    raise RuntimeError(
        f"Expected DEV=1222, got {len(dev_rows)}"
    )

if len(eval_rows) != 458:
    raise RuntimeError(
        f"Expected EVAL=458, got {len(eval_rows)}"
    )

if len(eligible) != 1680:
    raise RuntimeError(
        f"Expected total=1680, got {len(eligible)}"
    )

identity_pairs = [
    (
        r["capture"],
        r["community_id"],
    )
    for r in eligible
]

if len(set(identity_pairs)) != 1680:
    raise RuntimeError(
        "Duplicate capture/community identity detected."
    )

for r in eligible:
    if not str(
        r["episode_start_utc"]
    ).strip():
        raise RuntimeError(
            "Empty episode_start_utc detected."
        )


# ============================================================
# Deterministic item IDs
# ============================================================

def row_sort_key(r):
    return (
        r["capture"],
        r["episode_start_utc"],
        r["community_id"],
    )


dev_rows = sorted(
    dev_rows,
    key=row_sort_key,
)

eval_rows = sorted(
    eval_rows,
    key=row_sort_key,
)

items = []

for i, r in enumerate(
    dev_rows,
    start=1,
):
    items.append({
        "item_id": f"G6D-D-{i:04d}",
        "pool": "CALIBRATION_DEV",
        "capture": r["capture"],
        "episode_start_utc": r[
            "episode_start_utc"
        ],
        "community_id": r[
            "community_id"
        ],
        "source_path": SOURCE_BY_CAPTURE[
            r["capture"]
        ],
        "ground_truth": ground_truth_to_label(
            r["ground_truth_label"]
        ),
    })

for i, r in enumerate(
    eval_rows,
    start=1,
):
    items.append({
        "item_id": f"G6D-E-{i:04d}",
        "pool": "CALIBRATION_EVAL",
        "capture": r["capture"],
        "episode_start_utc": r[
            "episode_start_utc"
        ],
        "community_id": r[
            "community_id"
        ],
        "source_path": SOURCE_BY_CAPTURE[
            r["capture"]
        ],
        "ground_truth": ground_truth_to_label(
            r["ground_truth_label"]
        ),
    })

if len({
    x["item_id"]
    for x in items
}) != 1680:
    raise RuntimeError(
        "Duplicate opaque item ID."
    )


# ============================================================
# First pass: alerts and flows
#
# Gate 6C semantic rule is preserved.
#
# Adaptation:
# source_path is included in the lookup key because the two
# Windows capture files contain overlapping Community IDs.
# Without source scoping, events from distinct frozen captures
# could be incorrectly mixed.
# ============================================================

by_source = defaultdict(list)

for item in items:
    by_source[
        item["source_path"]
    ].append(item)

alerts = defaultdict(list)
flows = defaultdict(list)

for path, source_items in by_source.items():

    wanted = {
        x["community_id"]
        for x in source_items
    }

    with path.open(
        encoding="utf-8",
        errors="replace",
    ) as f:

        for line in f:

            try:
                x = json.loads(line)
            except Exception:
                continue

            cid = x.get(
                "community_id"
            )

            if cid not in wanted:
                continue

            key = (
                str(path),
                cid,
            )

            et = x.get(
                "event_type"
            )

            if et == "alert":
                alerts[
                    key
                ].append(x)

            elif et == "flow":
                flows[
                    key
                ].append(x)


# ============================================================
# Primary alert, anchor, endpoint pair
# ============================================================

for item in items:

    key = (
        str(item["source_path"]),
        item["community_id"],
    )

    if not alerts[key]:
        raise RuntimeError(
            "No alert event for "
            f"{item['item_id']}"
        )

    if not flows[key]:
        raise RuntimeError(
            "No flow event for "
            f"{item['item_id']}"
        )

    def alert_sort_key(a):
        return (
            epoch(a["timestamp"]),
            a.get(
                "alert",
                {},
            ).get(
                "signature",
                "",
            ),
        )

    primary = min(
        alerts[key],
        key=alert_sort_key,
    )

    anchor = epoch(
        primary["timestamp"]
    )

    flow = next(
        (
            x for x
            in flows[key]
            if x.get(
                "flow",
                {},
            ).get("start")
        ),
        flows[key][0],
    )

    pair = endpoint_pair(
        flow
    )

    if pair is None:
        raise RuntimeError(
            "No endpoint pair for "
            f"{item['item_id']}"
        )

    item[
        "primary_alert"
    ] = primary

    item[
        "anchor"
    ] = anchor

    item[
        "pair"
    ] = pair


# ============================================================
# Evidence retrieval: exact Gate 6C semantics
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
        errors="replace",
    ) as f:

        for line in f:

            try:
                x = json.loads(line)
            except Exception:
                continue

            et = x.get(
                "event_type"
            )

            if et not in WHITELIST:
                continue

            ts = x.get(
                "timestamp"
            )

            if not ts:
                continue

            try:
                t = epoch(ts)
            except Exception:
                continue

            cid = x.get(
                "community_id"
            )

            pair = endpoint_pair(
                x
            )

            candidate_items = {}

            # Exact CID priority 0.
            for item in items_by_cid.get(
                cid,
                [],
            ):
                if (
                    item["item_id"]
                    in source_item_ids
                ):
                    candidate_items[
                        item["item_id"]
                    ] = (
                        item,
                        0,
                        "exact_flow",
                    )

            # Endpoint pair priority 1.
            for item in items_by_pair.get(
                pair,
                [],
            ):
                if (
                    item["item_id"]
                    not in source_item_ids
                ):
                    continue

                if (
                    item["item_id"]
                    not in candidate_items
                ):
                    candidate_items[
                        item["item_id"]
                    ] = (
                        item,
                        1,
                        "endpoint_pair",
                    )

            if not candidate_items:
                continue

            payload = evidence_payload(
                x
            )

            pattern_key = canonical_json(
                payload
            )

            for (
                item,
                priority,
                relation,
            ) in candidate_items.values():

                delta = (
                    t
                    - item["anchor"]
                )

                if (
                    delta < -WINDOW
                    or delta > WINDOW
                ):
                    continue

                groups = pattern_groups[
                    item["item_id"]
                ]

                rec = groups.get(
                    pattern_key
                )

                if rec is None:

                    groups[
                        pattern_key
                    ] = {
                        "payload": payload,
                        "priority": priority,
                        "relation": relation,
                        "first_delta": delta,
                        "last_delta": delta,
                        "closest_abs_delta": abs(
                            delta
                        ),
                        "occurrence_count": 1,
                    }

                else:

                    rec[
                        "occurrence_count"
                    ] += 1

                    rec[
                        "first_delta"
                    ] = min(
                        rec[
                            "first_delta"
                        ],
                        delta,
                    )

                    rec[
                        "last_delta"
                    ] = max(
                        rec[
                            "last_delta"
                        ],
                        delta,
                    )

                    candidate_rank = (
                        priority,
                        abs(delta),
                        delta,
                    )

                    current_rank = (
                        rec[
                            "priority"
                        ],
                        rec[
                            "closest_abs_delta"
                        ],
                        rec[
                            "first_delta"
                        ],
                    )

                    if (
                        candidate_rank
                        < current_rank
                    ):
                        rec[
                            "priority"
                        ] = priority

                        rec[
                            "relation"
                        ] = relation

                        rec[
                            "closest_abs_delta"
                        ] = abs(
                            delta
                        )


# ============================================================
# Freeze max-6 evidence bundle
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
            r[
                "closest_abs_delta"
            ],
            canonical_json(
                r["payload"]
            ),
        )
    )

    selected = groups[
        :BUDGET
    ]

    bundle = []

    for idx, rec in enumerate(
        selected,
        start=1,
    ):

        bundle.append({
            "evidence_id": f"E{idx}",
            "relation": rec[
                "relation"
            ],
            "event_type": rec[
                "payload"
            ][
                "event_type"
            ],
            "facts": rec[
                "payload"
            ][
                "facts"
            ],
            "occurrence_count": rec[
                "occurrence_count"
            ],
            "first_offset_seconds": round(
                rec[
                    "first_delta"
                ],
                3,
            ),
            "last_offset_seconds": round(
                rec[
                    "last_delta"
                ],
                3,
            ),
        })

    item[
        "evidence"
    ] = bundle

    item[
        "evidence_hash"
    ] = sha256_bytes(
        canonical_json(
            bundle
        ).encode("utf-8")
    )


# ============================================================
# Exact Gate 6C user-message semantics
# ============================================================

def build_user_message(item):

    card = alert_card(
        item[
            "primary_alert"
        ]
    )

    if item["evidence"]:
        evidence_obj = item[
            "evidence"
        ]
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
# Outcome-blind grouped folds
# ============================================================

dev_items = [
    x for x in items
    if x["pool"]
    == "CALIBRATION_DEV"
]

eval_items = [
    x for x in items
    if x["pool"]
    == "CALIBRATION_EVAL"
]

(
    group_to_fold,
    fold_total_items,
    fold_group_count,
    fold_capture_items,
    dev_groups,
) = assign_dev_folds(
    dev_items
)

for item in dev_items:
    item["cv_fold"] = (
        group_to_fold[
            (
                item["capture"],
                item[
                    "episode_start_utc"
                ],
            )
        ]
    )

for item in items:
    item["sc5_seed"] = sc5_seed(
        item["item_id"]
    )


# ============================================================
# Output directory
# ============================================================

if OUT.exists():
    shutil.rmtree(OUT)

HIDDEN.mkdir(
    parents=True,
    exist_ok=True,
)

# Copy exact frozen prompt bytes.
shutil.copyfile(
    GATE6C_PROMPT,
    OUT / "canonical_prompt.txt",
)


# ============================================================
# Model-visible inputs
# ============================================================

def model_record(item):
    return {
        "item_id": item[
            "item_id"
        ],
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_message(
                    item
                ),
            },
        ],
    }


dev_model_records = [
    model_record(x)
    for x in dev_items
]

eval_model_records = [
    model_record(x)
    for x in eval_items
]

write_jsonl(
    OUT
    / "canonical_dev_model_inputs.jsonl",
    dev_model_records,
)

write_jsonl(
    OUT
    / "sealed_eval_model_inputs.jsonl",
    eval_model_records,
)


# ============================================================
# Non-model-visible collection manifests
# ============================================================

dev_manifest_fields = [
    "item_id",
    "capture",
    "episode_start_utc",
    "community_id",
    "source_path",
    "sc5_seed",
    "cv_fold",
    "evidence_hash",
]

dev_manifest_records = [
    {
        "item_id": x[
            "item_id"
        ],
        "capture": x[
            "capture"
        ],
        "episode_start_utc": x[
            "episode_start_utc"
        ],
        "community_id": x[
            "community_id"
        ],
        "source_path": str(
            x["source_path"]
        ),
        "sc5_seed": x[
            "sc5_seed"
        ],
        "cv_fold": x[
            "cv_fold"
        ],
        "evidence_hash": x[
            "evidence_hash"
        ],
    }
    for x in dev_items
]

write_csv(
    OUT
    / "dev_collection_manifest.csv",
    dev_manifest_fields,
    dev_manifest_records,
)

eval_manifest_fields = [
    "item_id",
    "capture",
    "episode_start_utc",
    "community_id",
    "source_path",
    "sc5_seed",
    "evidence_hash",
]

eval_manifest_records = [
    {
        "item_id": x[
            "item_id"
        ],
        "capture": x[
            "capture"
        ],
        "episode_start_utc": x[
            "episode_start_utc"
        ],
        "community_id": x[
            "community_id"
        ],
        "source_path": str(
            x["source_path"]
        ),
        "sc5_seed": x[
            "sc5_seed"
        ],
        "evidence_hash": x[
            "evidence_hash"
        ],
    }
    for x in eval_items
]

write_csv(
    OUT
    / "sealed_eval_manifest.csv",
    eval_manifest_fields,
    eval_manifest_records,
)


# ============================================================
# Group-fold manifest
# ============================================================

fold_rows = []

for (
    capture,
    episode,
), members in sorted(
    dev_groups.items()
):
    fold_rows.append({
        "capture": capture,
        "episode_start_utc": episode,
        "group_sha256": group_hash(
            capture,
            episode,
        ),
        "cv_fold": group_to_fold[
            (
                capture,
                episode,
            )
        ],
        "n_items": len(
            members
        ),
    })

write_csv(
    OUT
    / "dev_group_folds.csv",
    [
        "capture",
        "episode_start_utc",
        "group_sha256",
        "cv_fold",
        "n_items",
    ],
    fold_rows,
)


# ============================================================
# Hidden GT
# ============================================================

write_jsonl(
    HIDDEN
    / "dev_ground_truth.jsonl",
    [
        {
            "item_id": x[
                "item_id"
            ],
            "ground_truth": x[
                "ground_truth"
            ],
        }
        for x in dev_items
    ],
)

write_jsonl(
    HIDDEN
    / "eval_ground_truth.jsonl",
    [
        {
            "item_id": x[
                "item_id"
            ],
            "ground_truth": x[
                "ground_truth"
            ],
        }
        for x in eval_items
    ],
)


# ============================================================
# Structural assertions
# ============================================================

if len(
    dev_model_records
) != 1222:
    raise RuntimeError(
        "DEV output count mismatch."
    )

if len(
    eval_model_records
) != 458:
    raise RuntimeError(
        "EVAL output count mismatch."
    )

# Model-visible records must expose only item_id + messages.
for record in (
    dev_model_records
    + eval_model_records
):
    if set(
        record.keys()
    ) != {
        "item_id",
        "messages",
    }:
        raise RuntimeError(
            "Unexpected model-visible key."
        )

# EVAL manifest is deliberately label-free.
if (
    "ground_truth"
    in eval_manifest_fields
):
    raise RuntimeError(
        "Ground truth leaked into EVAL manifest."
    )

# No DEV episode may span folds.
seen_groups = {}

for x in dev_items:

    key = (
        x["capture"],
        x[
            "episode_start_utc"
        ],
    )

    fold = x[
        "cv_fold"
    ]

    if (
        key in seen_groups
        and seen_groups[key]
        != fold
    ):
        raise RuntimeError(
            "DEV group split across folds."
        )

    seen_groups[
        key
    ] = fold

if len(set(
    x["sc5_seed"]
    for x in items
)) != 1680:
    raise RuntimeError(
        "SC5 seed collision detected."
    )


# ============================================================
# Preview metadata + hashes
# ============================================================

artifact_files = [
    OUT
    / "canonical_prompt.txt",

    OUT
    / "canonical_dev_model_inputs.jsonl",

    OUT
    / "sealed_eval_model_inputs.jsonl",

    OUT
    / "dev_collection_manifest.csv",

    OUT
    / "sealed_eval_manifest.csv",

    OUT
    / "dev_group_folds.csv",

    HIDDEN
    / "dev_ground_truth.jsonl",

    HIDDEN
    / "eval_ground_truth.jsonl",
]

file_hashes = {
    str(p): sha256_file(
        p
    )
    for p in artifact_files
}

preview = {
    "artifact": (
        "GATE6D_CANONICAL_INPUTS_PREVIEW_V1"
    ),
    "status": (
        "PRE_FREEZE_LOCAL_PREVIEW"
    ),
    "counts": {
        "dev_items": len(
            dev_items
        ),
        "eval_items": len(
            eval_items
        ),
        "total_items": len(
            items
        ),
        "dev_groups": len(
            dev_groups
        ),
        "folds": N_FOLDS,
    },
    "prompt": {
        "source_path": str(
            GATE6C_PROMPT
        ),
        "sha256": sha256_file(
            OUT
            / "canonical_prompt.txt"
        ),
    },
    "seed_algorithm": {
        "namespace": (
            "GATE6D_SC5_V1"
        ),
        "input": (
            "UTF8('GATE6D_SC5_V1|' + item_id)"
        ),
        "hash": "SHA256",
        "integer_bytes": (
            "first 4 digest bytes, unsigned big-endian"
        ),
        "range_rule": (
            "value & 0x7fffffff; replace 0 with 1"
        ),
    },
    "fold_algorithm": {
        "group_unit": (
            "capture + episode_start_utc"
        ),
        "n_folds": N_FOLDS,
        "uses_ground_truth": False,
        "uses_model_output": False,
        "uses_model_correctness": False,
        "uses_calibration_performance": False,
        "ordering": (
            "descending group size, capture, deterministic "
            "SHA256 group hash, episode"
        ),
        "allocation_objective": (
            "minimum capture-specific item load, then total "
            "item load, then group count, then fold number"
        ),
    },
    "gate6c_semantics": {
        "primary_alert": (
            "earliest alert timestamp; signature lexical tie-break"
        ),
        "anchor": (
            "primary alert timestamp"
        ),
        "flow": (
            "first flow with flow.start else first flow"
        ),
        "retrieval_window_seconds": 30,
        "evidence_budget": 6,
        "exact_cid_priority": 0,
        "endpoint_pair_priority": 1,
        "model_visible_schema_changed": False,
    },
    "source_scope_adaptation": (
        "Alert/flow first-pass lookup is keyed by "
        "(source_path, community_id) because frozen Windows "
        "capture files contain overlapping Community IDs. "
        "This prevents cross-capture event mixing while "
        "preserving Gate 6C per-source semantics."
    ),
    "prior_artifact_hashes": {
        str(INVENTORY): sha256_file(
            INVENTORY
        ),
        str(BOUNDARY): sha256_file(
            BOUNDARY
        ),
        str(PROTOCOL): sha256_file(
            PROTOCOL
        ),
        str(SOURCE_BINDING): sha256_file(
            SOURCE_BINDING
        ),
        str(VALIDITY): sha256_file(
            VALIDITY
        ),
    },
    "generated_file_hashes": (
        file_hashes
    ),
    "collection_state": {
        "calibration_dev_model_calls": 0,
        "calibration_eval_model_calls": 0,
        "external_test_accessed": False,
    },
}

preview_path = (
    OUT
    / "GATE6D_CANONICAL_INPUTS_PREVIEW_V1.json"
)

preview_path.write_text(
    json.dumps(
        preview,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)


# ============================================================
# Console audit — aggregate only
# ============================================================

print(
    "=== GATE 6D CANONICAL INPUT BUILD PREVIEW ==="
)

print(
    "DEV items:",
    len(dev_items),
)

print(
    "EVAL items:",
    len(eval_items),
)

print(
    "Total:",
    len(items),
)

print(
    "DEV episode groups:",
    len(dev_groups),
)

print()

print(
    "=== DEV FOLD BALANCE ==="
)

for f in range(
    1,
    N_FOLDS + 1,
):
    print(
        f"Fold {f}: "
        f"items={fold_total_items[f]}, "
        f"groups={fold_group_count[f]}, "
        + ", ".join(
            f"{cap}={fold_capture_items[f][cap]}"
            for cap in sorted(
                DEV_CAPTURES
            )
        )
    )

print()

print(
    "=== MODEL-VISIBLE FILES ==="
)

for p in [
    OUT
    / "canonical_dev_model_inputs.jsonl",

    OUT
    / "sealed_eval_model_inputs.jsonl",
]:
    print(
        p,
        sha256_file(p),
    )

print()

print(
    "=== NON-MODEL-VISIBLE MANIFESTS ==="
)

for p in [
    OUT
    / "dev_collection_manifest.csv",

    OUT
    / "sealed_eval_manifest.csv",

    OUT
    / "dev_group_folds.csv",
]:
    print(
        p,
        sha256_file(p),
    )

print()

print(
    "=== HIDDEN GT ==="
)

for p in [
    HIDDEN
    / "dev_ground_truth.jsonl",

    HIDDEN
    / "eval_ground_truth.jsonl",
]:
    print(
        p,
        sha256_file(p),
    )

print()

print(
    "Prompt SHA256:",
    sha256_file(
        OUT
        / "canonical_prompt.txt"
    ),
)

print(
    "Preview metadata SHA256:",
    sha256_file(
        preview_path
    ),
)

print()

print(
    "Ground-truth values printed: NO"
)

print(
    "Individual Community IDs printed: NO"
)

print(
    "Calibration-DEV model calls: 0"
)

print(
    "Calibration-EVAL model calls: 0"
)

print(
    "External-TEST accessed: NO"
)

print()

print(
    "BUILD STATUS: PRE-FREEZE PREVIEW COMPLETE"
)
