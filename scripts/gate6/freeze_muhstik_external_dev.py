import csv
import hashlib
from decimal import Decimal
from pathlib import Path
from statistics import median

SOURCE = Path(
    "data/processed/gate6/"
    "muhstik_external_dev_usable_inventory.csv"
)

SELECTED = Path(
    "data/processed/gate6/freeze/"
    "muhstik_external_dev_46.csv"
)

EPISODES = Path(
    "data/processed/gate6/freeze/"
    "muhstik_external_dev_episodes_46.csv"
)

DECISION = Path(
    "docs/decisions/"
    "GATE6C_MUHSTIK_EXTERNAL_DEV_EPISODE_FREEZE_2026-10-26.md"
)

MANIFEST = Path(
    "data/processed/gate6/freeze/"
    "gate6c_muhstik_external_dev_freeze_sha256.txt"
)

EXPECTED_SOURCE = 4683
EXPECTED_EPISODES = 46
GAP = Decimal("300")


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)

    return h.hexdigest()


# ------------------------------------------------------------
# Load frozen-qualified Muhstik usable inventory
# ------------------------------------------------------------

with SOURCE.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for r in rows:
    r["_anchor"] = Decimal(r["anchor_epoch"])

rows.sort(
    key=lambda r: (
        r["_anchor"],
        r["community_id"],
    )
)

source_count_pass = len(rows) == EXPECTED_SOURCE

cids = [r["community_id"] for r in rows]
unique_source_pass = len(cids) == len(set(cids))

print("=" * 72)
print("MUHSTIK EXTERNAL-DEV FREEZE")
print("=" * 72)

print(
    "SOURCE COUNT:",
    len(rows),
    "| expected:",
    EXPECTED_SOURCE,
    "|",
    "PASS" if source_count_pass else "FAIL",
)

print(
    "SOURCE CID UNIQUENESS:",
    "PASS" if unique_source_pass else "FAIL",
)

if not source_count_pass or not unique_source_pass:
    print()
    print("FREEZE STATUS: FAIL — no freeze artifacts written")
    raise SystemExit(2)


# ------------------------------------------------------------
# GLOBAL temporal episodes
#
# New episode iff consecutive qualified-item gap > 300 seconds.
# No GT labels, signatures, destinations, evidence content,
# model outputs, confidence, uncertainty, or difficulty are
# used to form episodes.
# ------------------------------------------------------------

episodes = []
current = []

for r in rows:

    if not current:
        current = [r]
        continue

    gap = r["_anchor"] - current[-1]["_anchor"]

    if gap > GAP:
        episodes.append(current)
        current = [r]
    else:
        current.append(r)

if current:
    episodes.append(current)


episode_count_pass = len(episodes) == EXPECTED_EPISODES

print(
    "EPISODE COUNT:",
    len(episodes),
    "| expected:",
    EXPECTED_EPISODES,
    "|",
    "PASS" if episode_count_pass else "FAIL",
)

if not episode_count_pass:
    print()
    print("FREEZE STATUS: FAIL — expected 46 episodes")
    raise SystemExit(2)


# ------------------------------------------------------------
# Select one representative per episode:
#
# closest alert anchor to temporal midpoint
# tie-break = lexicographically smallest Community ID
# ------------------------------------------------------------

selected_rows = []
episode_rows = []

for i, ep in enumerate(episodes, start=1):

    episode_id = f"MUH-DEV-E{i:03d}"

    start = ep[0]["_anchor"]
    end = ep[-1]["_anchor"]
    midpoint = (start + end) / Decimal("2")

    chosen = min(
        ep,
        key=lambda r: (
            abs(r["_anchor"] - midpoint),
            r["community_id"],
        ),
    )

    distance = abs(chosen["_anchor"] - midpoint)

    selected_rows.append({
        "episode_id": episode_id,
        "episode_start_utc": ep[0]["anchor_utc"],
        "episode_end_utc": ep[-1]["anchor_utc"],
        "episode_size": str(len(ep)),
        "episode_midpoint_epoch": str(midpoint),
        "midpoint_distance_seconds": str(distance),
        **{
            k: v
            for k, v in chosen.items()
            if not k.startswith("_")
        },
    })

    episode_rows.append({
        "episode_id": episode_id,
        "episode_start_utc": ep[0]["anchor_utc"],
        "episode_end_utc": ep[-1]["anchor_utc"],
        "episode_start_epoch": str(start),
        "episode_end_epoch": str(end),
        "episode_midpoint_epoch": str(midpoint),
        "episode_size": str(len(ep)),
        "selected_community_id": chosen["community_id"],
        "selected_anchor_epoch": chosen["anchor_epoch"],
        "selected_anchor_utc": chosen["anchor_utc"],
        "midpoint_distance_seconds": str(distance),
    })


# ------------------------------------------------------------
# Verification
# ------------------------------------------------------------

selected_cids = [
    r["community_id"]
    for r in selected_rows
]

selected_count_pass = (
    len(selected_rows) == EXPECTED_EPISODES
)

selected_unique_pass = (
    len(selected_cids) == len(set(selected_cids))
)

source_cid_set = set(cids)

membership_pass = all(
    cid in source_cid_set
    for cid in selected_cids
)

# Verify chosen item really is deterministic midpoint winner.
midpoint_rule_pass = True

for ep, s in zip(episodes, selected_rows):

    start = ep[0]["_anchor"]
    end = ep[-1]["_anchor"]
    midpoint = (start + end) / Decimal("2")

    expected = min(
        ep,
        key=lambda r: (
            abs(r["_anchor"] - midpoint),
            r["community_id"],
        ),
    )

    if expected["community_id"] != s["community_id"]:
        midpoint_rule_pass = False
        break


checks = {
    "46 episodes": episode_count_pass,
    "46 selected items": selected_count_pass,
    "selected CIDs unique": selected_unique_pass,
    "all selected items in source inventory": membership_pass,
    "midpoint + CID tie-break reproduced": midpoint_rule_pass,
}

print()
print("VERIFICATION")

for name, ok in checks.items():
    print(
        f"  {name}:",
        "PASS" if ok else "FAIL",
    )

if not all(checks.values()):
    print()
    print("FREEZE STATUS: FAIL — verification failed")
    raise SystemExit(2)


# ------------------------------------------------------------
# Write exact frozen selection
# ------------------------------------------------------------

SELECTED.parent.mkdir(parents=True, exist_ok=True)

selected_fields = [
    "episode_id",
    "episode_start_utc",
    "episode_end_utc",
    "episode_size",
    "episode_midpoint_epoch",
    "midpoint_distance_seconds",
    "community_id",
    "anchor_epoch",
    "anchor_utc",
    "gt_detail",
    "src_ip",
    "src_port",
    "dest_ip",
    "dest_port",
    "proto",
    "signatures",
]

with SELECTED.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    w = csv.DictWriter(
        f,
        fieldnames=selected_fields,
    )

    w.writeheader()

    for r in selected_rows:
        w.writerow({
            k: r.get(k, "")
            for k in selected_fields
        })


episode_fields = [
    "episode_id",
    "episode_start_utc",
    "episode_end_utc",
    "episode_start_epoch",
    "episode_end_epoch",
    "episode_midpoint_epoch",
    "episode_size",
    "selected_community_id",
    "selected_anchor_epoch",
    "selected_anchor_utc",
    "midpoint_distance_seconds",
]

with EPISODES.open(
    "w",
    newline="",
    encoding="utf-8",
) as f:

    w = csv.DictWriter(
        f,
        fieldnames=episode_fields,
    )

    w.writeheader()
    w.writerows(episode_rows)


# ------------------------------------------------------------
# Structural statistics
# ------------------------------------------------------------

sizes = [len(ep) for ep in episodes]

print()
print("REALIZED STRUCTURE")
print("  episodes:", len(episodes))
print("  selected items:", len(selected_rows))
print("  smallest episode:", min(sizes))
print("  median episode size:", median(sizes))
print("  largest episode:", max(sizes))
print("  total qualified source items:", sum(sizes))


# ------------------------------------------------------------
# Write decision record
# ------------------------------------------------------------

source_hash = sha256(SOURCE)
selected_hash = sha256(SELECTED)
episodes_hash = sha256(EPISODES)

decision_text = f"""# Gate 6C Muhstik External-DEV Episode Freeze

Freeze date: 2026-10-26
Status: APPROVED / FROZEN

## Purpose

Create a deterministic, episode-aware supplementary External-DEV
benchmark from the already-qualified Muhstik IoT-23 cases without
allowing highly correlated flows from one long malware campaign to
dominate model selection.

## Frozen source population

Qualified usable Muhstik cases: 4683

Source inventory:

`{SOURCE}`

Source SHA256:

`{source_hash}`

## Frozen episode rule

1. Sort the 4683 qualified cases by alert anchor time.
2. Use GLOBAL temporal segmentation.
3. Start a new episode only when the gap between consecutive
   qualified cases is strictly greater than 300 seconds.
4. A gap equal to 300 seconds remains within the same episode.
5. Ground-truth detailed label is NOT used to form episodes.
6. Signature, destination, evidence content, model output,
   correctness, confidence, uncertainty, and difficulty are NOT
   used to form episodes.
7. The realized segmentation contains exactly 46 episodes.

## Frozen representative-selection rule

Exactly one case is selected from each episode.

The selected case is the case whose alert anchor is closest to the
episode temporal midpoint:

    midpoint = (episode first anchor + episode last anchor) / 2

Tie-break:

    lexicographically smallest Community ID

No model performance may trigger resampling.

Replacement is permitted only for a genuine technical-invalidity
discovered before model evaluation. Any replacement must use the
next-nearest midpoint candidate under the same deterministic ordering,
and the reason must be documented before model results are inspected.

## Realized frozen benchmark

Selected External-DEV cases: 46

Selected inventory:

`{SELECTED}`

Selected inventory SHA256:

`{selected_hash}`

Episode inventory:

`{EPISODES}`

Episode inventory SHA256:

`{episodes_hash}`

## Interpretation constraint

The 46 representatives are temporal representatives from a single
Muhstik source/device campaign.

They must NOT be described as 46 independent malware campaigns.

CTU DEV and Muhstik External-DEV performance must be reported
separately during model selection.

The 46 Muhstik cases must not simply be pooled with the CTU DEV cases
in a way that allows the external campaign to dominate the winner.

## Held-out external test remains untouched

The following scenarios remain External-TEST and may not influence
model selection or tuning:

- hideandseek1
- mirai34
- trojan42

Coverage diagnostics only:

- torii20
- hakai8

## Gate status

Gate 6B: PASSED / FROZEN

Gate 6C-1: PASSED / FROZEN

Gate 6C-2 candidate set: PASSED / FROZEN

Muhstik External-DEV episode/sampling rule: PASSED / FROZEN

Actual model benchmark winner: OPEN
"""

DECISION.write_text(
    decision_text,
    encoding="utf-8",
)

decision_hash = sha256(DECISION)


# ------------------------------------------------------------
# Hash manifest
# ------------------------------------------------------------

script_path = Path(
    "scripts/gate6/freeze_muhstik_external_dev.py"
)

with MANIFEST.open(
    "w",
    encoding="utf-8",
) as f:

    for path in [
        SOURCE,
        SELECTED,
        EPISODES,
        DECISION,
        script_path,
    ]:
        f.write(
            f"{sha256(path)}  {path}\n"
        )


print()
print("=" * 72)
print("FROZEN ARTIFACTS")
print("=" * 72)

print("Source SHA256:  ", source_hash)
print("Selected SHA256:", selected_hash)
print("Episodes SHA256:", episodes_hash)
print("Decision SHA256:", decision_hash)

print()
print("Selected inventory:")
print(SELECTED)

print()
print("Episode inventory:")
print(EPISODES)

print()
print("Decision record:")
print(DECISION)

print()
print("Hash manifest:")
print(MANIFEST)

print()
print("=" * 72)
print("FREEZE STATUS")
print("=" * 72)

print("Muhstik 5-minute GLOBAL episode rule: FROZEN")
print("Realized episodes: 46")
print("Frozen External-DEV items: 46")
print("External-TEST touched by model selection: NO")
print("Gate 6C model winner: OPEN")
print("FREEZE VERIFICATION: PASS")
