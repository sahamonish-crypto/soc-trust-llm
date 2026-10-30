# Gate 6C-2 ZB1 Nemotron Replacement Freeze

Freeze date: 2026-10-30

Status: APPROVED / FROZEN

## Scope

This decision closes the ZB1-only reopening created after the
operational infeasibility of gemini-3.6-flash.

It does NOT reopen or modify:

- the canonical 133-item benchmark;
- canonical prompt;
- Gate 6B evidence configuration;
- three logical runs per item;
- deterministic item orders;
- ZB2;
- ZB3;
- scoring specification;
- competence floor;
- winner rule;
- hidden-ground-truth isolation;
- held-out External-TEST protection.

## Frozen replacement

Candidate ID:

ZB1

Provider:

Cloudflare Workers AI

Model:

@cf/nvidia/nemotron-3-120b-a12b

## Frozen execution configuration

- reasoning mode: low
- chat_template_kwargs.enable_thinking = true
- chat_template_kwargs.low_effort = true
- max_completion_tokens = 512
- temperature: omitted
- top-p: omitted
- top-k: omitted
- stream = false
- concurrency = 1
- minimum success delay = 0 seconds
- retry delays = [15, 45] seconds
- provider Retry-After remains authoritative when present
- tools disabled
- web/search disabled

## Reason for replacement

The previous frozen ZB1, gemini-3.6-flash, was reopened only because
the verified Free Tier quota was 20 generate-content requests/day.

The frozen ZB1 workload requires:

133 benchmark items x 3 logical runs = 399 logical responses.

That Gemini quota implied approximately 20 quota days even with
zero infrastructure retries and was judged operationally infeasible.

The reopening was not caused by model performance, correctness,
ground truth, class distribution, or interim scoring.

## Nemotron pre-benchmark validation evidence

All replacement-selection tests used synthetic prompts only.

Benchmark items exposed before this freeze:

0

Ground truth loaded before this freeze:

NO

External-TEST accessed:

NO

### Access test

- HTTP 200
- exact synthetic output: PASS
- observed latency: 1.5 seconds

### Initial Stage-1 harness incident

The first five-request Stage-1 run returned HTTP 200 on all five
requests with no 429, 5xx, or network failures, but the local parser
did not handle the provider's choices/message response shape and
therefore produced a false FAIL classification.

A one-request synthetic diagnostic confirmed the response structure,
Cloudflare success=true, and exact synthetic output.

The parser was corrected before the formal Stage-1 rerun.

### Corrected Stage 1

- requests: 5
- successful: 5/5
- exact outputs: 5/5
- HTTP 429: 0
- HTTP 5xx: 0
- network/timeouts: 0
- total Neurons: 16.025

Result:

PASS

### Stage 2 sequential micro-batch

- requests: 20
- successful: 20/20
- exact outputs: 20/20
- HTTP 429: 0
- HTTP 5xx: 0
- network/timeouts: 0
- median latency: 0.712 seconds
- empirical P95 latency: 1.394 seconds
- total Neurons: 74.060

Result:

PASS

### Stage 3 representative benchmark-size synthetic test

Synthetic total-content sizes matched the frozen benchmark:

- median: 1,373 characters
- P95: 2,244 characters
- maximum: 5,318 characters

Observed:

- MEDIAN: 402 prompt tokens, 17 completion tokens, 20.402 Neurons
- P95: 711 prompt tokens, 18 completion tokens, 34.443 Neurons
- MAX: 1,756 prompt tokens, 14 completion tokens, 80.924 Neurons

All 3/3 requests returned HTTP 200, exact expected output, and no
provider/network failure.

Result:

PASS

### Stage 4 conservative max-density synthetic test

Synthetic payload size:

5,318 characters

Observed:

- HTTP 200
- exact output: PASS
- prompt tokens: 3,533
- completion tokens: 22
- total tokens: 3,555
- Neurons: 161.977
- latency: 0.944 seconds
- provider errors: none

Result:

PASS

## Current provider-capacity envelope at freeze

Provider documentation was reverified on 2026-10-30.

Free allocation:

10,000 Neurons/day.

Published Nemotron Neuron rates used for this envelope:

- input: 45,455 Neurons per 1M tokens
- output: 136,364 Neurons per 1M tokens

A deliberately conservative theoretical envelope assumes EVERY one
of the 399 logical requests simultaneously has:

- the Stage-4 dense maximum input: 3,533 prompt tokens; and
- the entire configured 512-token completion ceiling.

Calculated input Neurons/request:

160.592515

Calculated output Neurons/request:

69.818368

Calculated total Neurons/request:

230.410883

Calculated 399-request total:

91933.942317

Equivalent 10,000-Neuron daily allocations:

9.193394

Whole quota days if that extreme held for all requests:

10

This is a conservative capacity bound, NOT a prediction of actual
benchmark usage and NOT a completion-time guarantee.

Permitted infrastructure retries may increase actual usage.

The frozen execution policy already permits quota constraints to
require execution across multiple sessions or quota days.

## Scientific interpretation

The Nemotron replacement is frozen because pre-benchmark evidence
supports operational compatibility and sustainable zero-budget
capacity for the inherited 399 logical-response workload.

This freeze is NOT a model-performance finding.

Nemotron has received zero frozen benchmark items before this freeze.

No hidden ground truth has been loaded.

No interim winner analysis has occurred.

The Gate 6C winner remains OPEN.

## Frozen artifact hashes

Candidate set v3:

b76e05e3a2109bce1a88354ec77aef5ca8b76f76f9f55d9685e3e02723b1ee60

Execution policy v2:

50b1808425d8e2600934a5a5ba10522e901087e5a5f6cbaaacd0a1ab00b86331

Runner v2:

49077b9bc42db27b57bfdb2082ce3643a69051aff9dd3f5f3cffbdcc2bc64404

Canonical model-visible benchmark:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

## Gate status

Gate 6C-2 ZB1 replacement:

FROZEN

ZB2:

UNCHANGED

ZB3:

UNCHANGED

Gate 6C model winner:

OPEN
