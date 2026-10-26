# Gate 6C Model Benchmark Scoring Specification

Status: candidate specification generated before any model call.

## Candidate models

- gpt-6.1-sol
- claude-sonnet-5-5
- deepseek-v4-pro

The exact provider model identifier/version used in execution must be
recorded.

External tools, browsing, retrieval services, and provider-side search
must be disabled.

## Benchmark material

Canonical DEV package:

- CTU DEV: 87 cases
- Muhstik External-DEV: 46 frozen temporal representatives
- Total: 133 cases

Held-out External-TEST is not part of this package and must not be
accessed during model selection:

- hideandseek1
- mirai34
- trojan42

## Model-visible information

Each model receives exactly:

1. the same frozen system prompt;
2. one deterministic alert card;
3. the same frozen Gate 6B evidence bundle.

Ground truth, attack labels, model correctness, confidence, uncertainty,
campaign name, dataset name, episode ID, and source metadata are not
included in the model-visible input.

## Output

Exactly one label:

ESCALATE

or

DO_NOT_ESCALATE

Any other output is invalid.

## Repeated-run stability

Each candidate model is evaluated three times on every item under the
lowest practically available stochasticity setting.

The exact temperature / reasoning / seed / sampling configuration must
be recorded for each provider.

Canonical recommendation for an item:

majority vote of the three valid runs.

Stability:

fraction of items for which all three runs return the same valid label.

No model may be given feedback about correctness between runs.

## Primary competence metric

Primary metric:

balanced accuracy on the CTU DEV items that have non-empty frozen Gate
6B evidence.

Expected evidence-covered CTU subset: 73 cases.

Balanced accuracy:

(mean of ESCALATE recall and DO_NOT_ESCALATE recall)

This prevents the 75/12 CTU class imbalance from making raw accuracy the
primary model-selection metric.

## Mandatory sensitivity analyses

Report separately:

1. CTU overall balanced accuracy on all 87 CTU DEV cases.
2. Redline-only balanced accuracy.
3. Remcos-only balanced accuracy.
4. class-specific error counts.
5. invalid-output rate.
6. Muhstik External-DEV malicious recall.
7. three-run stability.
8. latency.
9. estimated/provider-reported cost.

Remcos is treated as a smoke/stability subset because some Remcos alert
signatures are unusually explicit. A model must not be selected solely
because of strong Remcos performance.

Muhstik is an external robustness subset and must not simply be pooled
with CTU DEV to create a larger weighted accuracy score.

## Competence floor

A candidate is eligible for winner selection only if:

1. at least 99% of all benchmark responses are valid labels;
2. its canonical predictions contain both decision classes on CTU DEV;
3. CTU evidence-covered balanced accuracy is greater than 0.50.

If every primary candidate fails the competence floor, Gate 6C is
reopened and the previously approved escalation model may be evaluated.

## Winner rule

Among eligible primary candidates:

1. higher CTU evidence-covered balanced accuracy wins;
2. if the difference between the top two is < 0.02, use higher
   Redline-only balanced accuracy;
3. if still tied within < 0.02, use higher Muhstik malicious recall;
4. if still tied, use higher three-run stability;
5. if still tied, use lower median latency;
6. if still tied, use lower total benchmark cost.

The winner must remain naturally fallible. No errors may be injected or
labels manually flipped.

The final winning model/configuration, canonical recommendation for each
item, provider identifiers, timestamps, and hashes must be frozen before
later calibration or human-study use.
