# Gate 6C Canonical Benchmark Package Freeze

Freeze date: 2026-10-26
Status: APPROVED / FROZEN

## Canonical benchmark population

Total model-visible benchmark items: 133

- CTU-SME-11 DEV: 87
- Muhstik External-DEV: 46

CTU campaign composition:

- Redline: 68
- Remcos: 19

CTU ground truth:

- ESCALATE: 12
- DO_NOT_ESCALATE: 75

Muhstik External-DEV:

- 46 deterministic 5-minute GLOBAL episode representatives
- all ground-truth ESCALATE

## Frozen evidence coverage

CTU DEV with non-empty Gate 6B evidence:

73 / 87

Muhstik External-DEV with non-empty Gate 6B evidence:

46 / 46

The 14 CTU cases without additional evidence remain in the benchmark as
explicit no-additional-evidence stress cases.

## Frozen model-visible inputs

Canonical model input file:

benchmarks/gate6c/canonical_model_inputs.jsonl

SHA256:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

Canonical system prompt:

benchmarks/gate6c/canonical_prompt.txt

SHA256:

58c21362374142766269d0b11cba538b257a16a82df9f4bc679329c1deafd3c0

Ground truth is NOT contained in the model-visible input.

Structural hidden-data leakage scan:

PASS — no forbidden hidden-label fields detected.

## Frozen hidden ground truth

benchmarks/gate6c/hidden_ground_truth.csv

SHA256:

a54dda3cea2414cfddd6a49f19afc885e008d6c5edbe4cb85186e11fcd3b39af

Ground truth must never be supplied to a candidate model during benchmark
execution.

## Frozen item metadata

benchmarks/gate6c/item_metadata.csv

SHA256:

442b486e3bd1f5e098ab49cf4ebf990b9d2c6d3786fb66c73839ee9ce155c9b9

## Frozen scoring specification

benchmarks/gate6c/scoring_spec.md

SHA256:

56d07ed3bfc7cc715ebe883a41cdc0209b2e4ba638ab477bfb39446527372009

Primary model-selection metric:

CTU evidence-covered balanced accuracy.

Expected primary subset:

73 CTU cases with non-empty frozen evidence.

Mandatory separate analyses include:

- CTU overall balanced accuracy
- Redline-only performance
- Remcos-only performance
- class-specific errors
- invalid-output rate
- Muhstik External-DEV malicious recall
- three-run stability
- latency
- cost

Redline is the principal CTU discrimination subset.

Remcos is treated as smoke/stability evidence because some alert
signatures are unusually explicit.

Muhstik is supplementary external robustness evidence and must not be
pooled with CTU in a way that allows the single external campaign to
dominate model selection.

## Candidate models

Frozen primary candidate families:

- gpt-6.1-sol
- claude-sonnet-5-5
- deepseek-v4-pro

The exact provider model identifier/version actually available at
execution time must be recorded before benchmarking.

External search, browsing, provider retrieval tools, and other external
tools must be disabled during benchmark execution.

## Repeated-run design

Each candidate model is evaluated three times per item using the lowest
practically available stochasticity configuration.

Canonical item recommendation:

majority vote of the three valid runs.

No correctness feedback is supplied between runs.

Exact provider configuration, timestamps, response hashes, latency and
cost must be recorded.

## Competence floor

A model is eligible for winner selection only if:

1. at least 99% of benchmark responses are valid labels;
2. CTU canonical predictions contain both decision classes;
3. CTU evidence-covered balanced accuracy is greater than 0.50.

If every primary candidate fails the competence floor, Gate 6C must be
formally reopened before testing an escalation candidate.

## Winner rule

Among eligible primary candidates:

1. higher CTU evidence-covered balanced accuracy;
2. if top-two difference < 0.02, higher Redline-only balanced accuracy;
3. if still tied within < 0.02, higher Muhstik malicious recall;
4. if still tied, higher three-run stability;
5. if still tied, lower median latency;
6. if still tied, lower benchmark cost.

No model errors may be manually injected or labels flipped.

## Held-out External-TEST protection

The following scenarios remain untouched by model selection:

- hideandseek1
- mirai34
- trojan42

They must not influence:

- prompt design
- model selection
- retrieval design
- calibration method
- thresholds
- winner selection

## Authoritative EVE sources

Redline:

data/processed/gate6/windows7full2-2023-02-21-suricata-root/eve.json

Remcos:

data/processed/gate6/windows7full3-2023-02-22-verified-suricata-root/eve.json

Muhstik:

data/processed/gate6/iot23-external/muhstik3-suricata/eve.json

The verified Remcos replay is the sole authoritative Remcos source for
this benchmark.

## Gate status

Gate 6B:
PASSED / FROZEN

Gate 6C-1:
PASSED / FROZEN

Gate 6C-2 candidate set:
PASSED / FROZEN

Muhstik episode sampling:
PASSED / FROZEN

Canonical benchmark package:
PASSED / FROZEN

Actual three-model benchmark:
NOT YET EXECUTED

Gate 6C model winner:
OPEN

Any change to benchmark membership, prompt, evidence construction,
scoring rules, hidden GT mapping, or model-visible representation now
requires formally reopening the affected Gate 6C design decision.
