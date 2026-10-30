# Gate 6C Full Runner V3 Freeze

Freeze date: 2026-10-30

Status: APPROVED / FROZEN

## Scope

This freeze closes the runner-only reopening caused by the absence
of quota-safe multi-day session control in runner v2.

It does NOT reopen or modify:

- ZB1 candidate selection;
- NVIDIA Nemotron 3 Super 120B A12B;
- candidate set v3;
- execution policy v2;
- canonical 133-item benchmark;
- canonical prompt;
- Gate 6B evidence configuration;
- three logical runs per item;
- deterministic item orders;
- ZB2;
- ZB3;
- retry eligibility;
- scoring specification;
- competence floor;
- winner rule;
- hidden-ground-truth isolation;
- held-out External-TEST protection.

## Frozen runner

Path:

scripts/gate6/run_gate6c_full_benchmark_v3.py

SHA256:

f3a77c1774f2dff285490900b3fc4906dad5330f7074a774ca6214b6de15fb6d

## Source runner retained unchanged

Path:

scripts/gate6/run_gate6c_full_benchmark_v2.py

SHA256:

49077b9bc42db27b57bfdb2082ce3643a69051aff9dd3f5f3cffbdcc2bc64404

## Frozen scientific dependencies

Candidate set v3 SHA256:

b76e05e3a2109bce1a88354ec77aef5ca8b76f76f9f55d9685e3e02723b1ee60

Execution policy v2 SHA256:

50b1808425d8e2600934a5a5ba10522e901087e5a5f6cbaaacd0a1ab00b86331

Canonical model-visible benchmark SHA256:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

## Runner-v3 implementation change

Runner v3 changes implementation behavior only for the Cloudflare
daily free-allocation boundary.

Cloudflare HTTP 429 responses containing internal error code 3036
are treated as a clean quota-day session boundary.

Such an event:

- is preserved in a separate quota-pause provenance log;
- consumes no logical attempt;
- does not resolve the benchmark item;
- does not create a recovery-queue entry;
- does not produce OPERATIONAL_MISSING;
- ends the current session cleanly;
- permits the same candidate/run/item to resume after provider reset.

Other HTTP 429 responses remain governed by the previously frozen
transient retry policy.

Cloudflare temporary-capacity code 3040 is NOT special-cased.

## Audit provenance change

Runner v3 uses the versioned built-in audit path:

benchmarks/gate6c/full/audit/runner_v3_audit.json

The runner refuses to overwrite that audit artifact once it exists.

Historical runner_audit.json and runner_audit.txt remain unchanged.

## Static readiness audit

Artifact:

benchmarks/gate6c/full/audit/runner_v3_static_readiness_audit.json

SHA256:

3d3a93f5b5cfce5a79b233e33fd2a8205d09f94a2d6475be6954ab574d3c67ef

Result:

PASS

Verified properties include:

- historical frozen/provenance hashes unchanged;
- exact runner-v3 draft hash verified;
- Python syntax valid;
- quota-safe constructs present;
- 3036 detected before logical-attempt persistence;
- quota pause logged separately before clean return;
- quota pause consumes no logical attempt;
- quota pause does not modify the recovery queue;
- 3040 remains under the original transient retry policy;
- initial and recovery sessions both support clean pause;
- frozen Cloudflare adapter unchanged;
- candidate execution configuration unchanged;
- no active ZB1 execution state existed before inference;
- historical frozen/provenance files had zero Git diff.

## Pre-freeze execution state

API calls made during runner-v3 build/audit:

0

Benchmark inference under runner v3:

NOT STARTED

Ground truth loaded:

NO

External-TEST accessed:

NO

Active ZB1 execution artifacts:

0

## Gate status

Gate 6C runner-only reopening:

CLOSED / FROZEN

ZB1:

FROZEN / UNCHANGED

Gate 6C model winner:

OPEN
