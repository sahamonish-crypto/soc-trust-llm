# Gate 6C Full Benchmark Runner Freeze

Freeze date: 2026-10-28  
Status: APPROVED / FROZEN

## Purpose

Freeze the audited implementation that will execute the already-frozen
Gate 6C full model benchmark.

No full benchmark inference had been executed before this freeze.

## Frozen runner

`scripts/gate6/run_gate6c_full_benchmark.py`

SHA256:

`9771d0e05fd37b6727a09553be58c24701401886ae3312c788f6772f049f153f`

## Canonical model-visible benchmark

133 items.

Canonical input SHA256:

`a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915`

## Frozen deterministic orders

Logical run 1:

`8e6df4aee59586ed43803418dd75595ab917a88985c84b6ab908b6eec5f7c7bc`

Logical run 2:

`c9e81cbd881f76c3635b2ae6b8fcdefe72a9f26a648436d7ea3ada2e093df624`

Logical run 3:

`5f2464951c934398717681bf26115bc1fc9fd8f5b3c74cddfe51a277bfde0142`

Each order contains exactly 133 unique frozen benchmark item IDs.

The same logical-run order is used for all candidates.

## Frozen candidates

ZB1:

`gemini-3.6-flash`

ZB2:

`openai/gpt-oss-120b`

ZB3:

`qwen/qwen3.8-27b`

## Implementation audit

The runner passed audit before freeze.

Verified properties include:

- canonical benchmark SHA256 match
- frozen candidate-set match
- frozen execution-policy match
- three deterministic and distinct 133-item orders
- no hidden-ground-truth filename/path referenced by execution code
- no External-TEST source path referenced
- no interim scoring implementation
- no paid OpenAI API implementation
- explicit execution flag required
- explicit confirmation token required
- one candidate/run session per invocation
- sequential provider calls
- bounded transient retry behavior
- no retry of an HTTP-200 invalid model answer
- recovery queue support
- crash-safe reconciliation of persisted HTTP-200 attempts
- interrupted recovery-session resume support
- already resolved logical items skipped on resume
- execution blocked unless runner and frozen order artifacts are committed
  and clean

## Pre-execution state

Before this runner freeze:

- full benchmark API requests executed: 0
- raw full-benchmark result files: 0
- hidden ground truth loaded during model collection: NO
- External-TEST accessed: NO
- interim model scoring performed: NO
- Gate 6C winner selected: NO

## Scientific policy

This runner implements the already-frozen full-benchmark execution policy.

The implementation freeze does not modify:

- benchmark cases
- prompt
- evidence
- candidate models
- reasoning settings
- retry eligibility
- number of logical runs
- scoring specification
- competence floor
- winner rule

Any later scientific change requires explicit reopening of the affected
Gate 6C decision.

## Status after freeze

Gate 6C full runner:
FROZEN

Full benchmark:
NOT YET EXECUTED

Ground-truth scoring:
NOT YET EXECUTED

Gate 6C winner:
OPEN
