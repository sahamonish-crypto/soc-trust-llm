# Gate 6C Muhstik External-DEV Episode Freeze

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

`data/processed/gate6/muhstik_external_dev_usable_inventory.csv`

Source SHA256:

`783a88d116c8fcf66f6c7baf15558ccb6df05625643779dd52d3c1205e0c03e5`

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

`data/processed/gate6/freeze/muhstik_external_dev_46.csv`

Selected inventory SHA256:

`9337fcbf8cf200e3e572a38c65c068a7e2f487d029fac49e8694e2a1bb48a661`

Episode inventory:

`data/processed/gate6/freeze/muhstik_external_dev_episodes_46.csv`

Episode inventory SHA256:

`6c31991c8b49358229d1fee1f5fccf5e12848327304097702212bb44ee839f3a`

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
