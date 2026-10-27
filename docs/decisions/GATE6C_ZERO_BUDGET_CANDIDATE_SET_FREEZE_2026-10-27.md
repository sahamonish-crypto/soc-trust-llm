# Gate 6C-2 Zero-Budget Candidate Set Freeze

Freeze date: 2026-10-27

Status: APPROVED / FROZEN

## Reason for reopening Gate 6C-2

The originally frozen commercial candidate set was:

- gpt-6.1-sol
- claude-sonnet-5-5
- deepseek-v4-pro

Before any candidate model was shown a benchmark item, it was established
that the study cannot fund paid API usage.

The researcher explicitly approved reopening Gate 6C-2 solely because
of this zero-budget constraint.

No benchmark inference results had been observed at the time of this
change.

Therefore this change cannot be based on model performance.

## Frozen replacement candidate set

### ZB1

Provider:

Google Gemini API

Model identifier:

gemini-3.8-flash

### ZB2

Provider:

Groq

Model identifier:

openai/gpt-oss-120b

This is the open-weight GPT-OSS model served through Groq.

It is NOT a call to the paid OpenAI API.

### ZB3

Provider:

Groq

Model identifier:

qwen/qwen3.8-27b

## Access verification

Before freezing, metadata-only provider requests verified that all three
exact model identifiers were accessible from the research Codespace.

Verification involved:

- no benchmark prompt
- no benchmark item
- no model inference request
- no ground truth
- no paid OpenAI API call
- no paid Anthropic API call
- no paid DeepSeek API call

The access-verification record is:

data/processed/gate6/gate6c_zero_budget_candidate_access_2026-10-27.txt

## What remains unchanged

This Gate 6C-2 reopening does NOT reopen:

- Gate 6B retrieval configuration
- CTU DEV membership
- Muhstik External-DEV membership
- the frozen 46-item Muhstik episode sample
- the 133-item canonical benchmark
- canonical system prompt
- model-visible alert/evidence representation
- hidden ground truth
- scoring logic
- competence floor
- winner rule
- held-out External-TEST protection

The frozen canonical model-input SHA256 remains:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

## Scoring-spec interpretation

The candidate-model names originally written inside:

benchmarks/gate6c/scoring_spec.md

are superseded ONLY by this formally approved Gate 6C-2 decision.

All metric definitions, competence criteria, tie-breaking logic,
stability requirements, latency reporting, and winner-selection rules
remain unchanged.

The canonical benchmark package itself is not regenerated.

## Execution constraints

All three replacement candidates must receive the identical frozen
model-visible inputs.

External tools, browsing, web search, and provider retrieval tools must
be disabled.

No correctness feedback may be supplied between repeated runs.

Each candidate remains subject to three runs per item for the full
benchmark.

Exact provider-returned model/version metadata, execution configuration,
timestamps, output hashes, latency, and usage must be recorded.

## Zero-budget requirement

The Gate 6C benchmark must not knowingly incur paid API charges.

The existing OPENAI_API_KEY must not be used for the paid OpenAI API
during this zero-budget benchmark.

If a supposedly free provider requires payment before completion, Gate
6C-2 must be reopened again rather than silently substituting another
model.

## Gate status

Gate 6B:
PASSED / FROZEN

Gate 6C-1:
PASSED / FROZEN

Original Gate 6C-2 commercial candidate set:
SUPERSEDED

Zero-budget Gate 6C-2 candidate set:
PASSED / FROZEN

Canonical benchmark package:
PASSED / FROZEN

Smoke test:
NOT YET EXECUTED

Full three-model benchmark:
NOT YET EXECUTED

Gate 6C model winner:
OPEN
