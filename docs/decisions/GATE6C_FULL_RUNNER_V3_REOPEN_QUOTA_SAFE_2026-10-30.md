# Gate 6C Full Runner V3 Reopening — Quota-Safe Multi-Day Execution

Date: 2026-10-30

Status: APPROVED / RUNNER-ONLY REOPENING

## Scope

This reopening applies ONLY to the Gate 6C full-runner implementation.

It does NOT reopen or modify:

- ZB1 candidate selection;
- NVIDIA Nemotron 3 Super 120B A12B;
- candidate set v3;
- execution policy v2;
- canonical 133-item benchmark;
- canonical prompt;
- Gate 6B evidence;
- three logical runs per item;
- deterministic item orders;
- ZB2;
- ZB3;
- scoring specification;
- competence floor;
- winner rule;
- hidden-ground-truth isolation;
- held-out External-TEST protection.

## Trigger

Runner v2 treated every HTTP 429 as an ordinary transient logical-request
failure.

Cloudflare distinguishes:

- internal code 3036: daily free Neuron allocation exhausted;
- internal code 3040: temporary model capacity exceeded.

The frozen zero-budget design permits execution across multiple quota days.

Without a quota-safe session boundary, a predictable daily allocation
boundary could consume retry attempts and move otherwise valid logical
requests into the recovery queue.

## Runner-v3 implementation rule

Only Cloudflare HTTP 429 responses carrying internal code 3036 are treated
as a quota-day session boundary.

A 3036 response:

- is recorded as a separate quota-pause provenance event;
- does not consume a logical attempt;
- does not resolve the item;
- does not create a recovery-queue entry;
- does not create OPERATIONAL_MISSING;
- ends the current execution session cleanly;
- permits the identical candidate/run/item to resume after quota reset.

Other HTTP 429 responses remain governed by the frozen transient retry
policy.

In particular, code 3040 remains an ordinary transient capacity condition.

## Audit provenance correction

Runner v2's built-in audit path collided with the tracked historical
runner_audit.json artifact.

Runner v3 uses:

benchmarks/gate6c/full/audit/runner_v3_audit.json

and refuses to overwrite that artifact once it exists.

## Source runner

scripts/gate6/run_gate6c_full_benchmark_v2.py

SHA256:

49077b9bc42db27b57bfdb2082ce3643a69051aff9dd3f5f3cffbdcc2bc64404

## Draft successor

scripts/gate6/run_gate6c_full_benchmark_v3.py

SHA256:

f3a77c1774f2dff285490900b3fc4906dad5330f7074a774ca6214b6de15fb6d

## Execution status

Benchmark inference under runner v3 has NOT begun.

Ground truth remains unopened.

External-TEST remains untouched.

Gate 6C winner remains OPEN.
