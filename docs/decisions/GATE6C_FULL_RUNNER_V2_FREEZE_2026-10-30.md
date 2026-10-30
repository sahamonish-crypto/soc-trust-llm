# Gate 6C Full Runner V2 Freeze

Freeze date: 2026-10-30

Status: APPROVED / FROZEN

## Scope

This freeze creates a successor to the historical Gate 6C full
benchmark runner solely because ZB1 was formally reopened and replaced.

The historical runner remains preserved unchanged.

## Frozen runner

Path:

scripts/gate6/run_gate6c_full_benchmark_v2.py

SHA256:

49077b9bc42db27b57bfdb2082ce3643a69051aff9dd3f5f3cffbdcc2bc64404

## Frozen dependencies

Candidate set:

benchmarks/gate6c/zero_budget_candidate_set_v3.json

SHA256:

b76e05e3a2109bce1a88354ec77aef5ca8b76f76f9f55d9685e3e02723b1ee60

Execution policy:

benchmarks/gate6c/full_benchmark_execution_policy_v2.json

SHA256:

50b1808425d8e2600934a5a5ba10522e901087e5a5f6cbaaacd0a1ab00b86331

Canonical model-visible benchmark:

benchmarks/gate6c/canonical_model_inputs.jsonl

SHA256:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

## ZB1 adapter

Provider:

Cloudflare Workers AI

Model:

@cf/nvidia/nemotron-3-120b-a12b

Configuration:

- max_completion_tokens = 512
- enable_thinking = true
- low_effort = true
- sampling parameters omitted
- stream = false
- sequential requests only
- success delay = 0
- retry delays = [15, 45]
- Retry-After honored by the existing retry framework

## Unchanged implementation behavior

The successor preserves the previously frozen:

- canonical benchmark;
- deterministic three-run ordering;
- logical-run count;
- valid labels;
- retry eligibility;
- recovery-queue semantics;
- request provenance logging;
- no-retry rule for valid HTTP-200 answers;
- hidden-ground-truth isolation;
- External-TEST protection;
- no interim scoring;
- competence floor;
- winner rule.

ZB2 and ZB3 remain unchanged.

## Pre-freeze audit

The successor passed a local zero-API structural audit before freeze.

Verified properties included:

- historical frozen artifacts unchanged;
- canonical input SHA256 unchanged;
- ZB1-only candidate replacement;
- policy-v2 benchmark structure preserved;
- runner-v2 Python syntax valid;
- Cloudflare adapter present;
- old Gemini ZB1 hard-code absent from active successor configuration;
- scientific prohibitions unchanged;
- historical frozen artifacts had zero Git diff.

API requests made by that audit:

0

Benchmark inference executed:

NO

Ground truth loaded:

NO

External-TEST accessed:

NO

## Execution status

Full Nemotron benchmark execution has NOT begun.

This runner must be committed and clean before benchmark execution.
