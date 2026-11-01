# Gate 6D Uncertainty Estimator Protocol Freeze

Status: **FROZEN**

Frozen UTC: 2026-11-01T19:11:03.286236+00:00

## Model

`@cf/nvidia/nemotron-3-120b-a12b`

## Scientific purpose

This protocol freezes uncertainty-estimation and calibration
methodology before any Calibration-DEV model outputs or correctness
results are observed.

The uncertainty estimator, probability calibrator, and eventual
participant-facing display remain separate components.

## Data use

Calibration-DEV:

- 1222 eligible items;
- full eligible pool is used;
- no label-conditioned subsampling.

Calibration-EVAL:

- 458 eligible items;
- remains untouched until the estimator/calibrator is selected and
  frozen;
- then evaluated once.

Gate 6C benchmark items are not reused.

Gate 6C External-TEST remains untouched.

## Recommendation generation

Each calibration item receives one stochastic five-choice Nemotron
request.

Frozen generation settings:

- n = 5
- temperature = 0.4
- thinking enabled
- low-effort reasoning
- max completion tokens = 512
- exact labels only:
  - ESCALATE
  - DO_NOT_ESCALATE

The canonical recommendation is the strict majority of the five valid
labels.

All five outputs must be valid exact labels for the uncertainty
observation to be valid.

Infrastructure failures may be retried.

A successful HTTP200 containing malformed semantic output is not
silently regenerated.

## Candidate estimator 1 — SC5_AGREEMENT

Raw confidence is the proportion of the five stochastic samples that
agree with the majority recommendation.

Possible raw scores:

- 0.60
- 0.80
- 1.00

## Candidate estimator 2 — VC_SELF_EVAL

After the SC5 majority recommendation is frozen, the same model receives
a separate deterministic self-evaluation request asking for the
probability that that fixed recommendation is correct.

The model must return exactly one integer from 0 to 100.

The model may not revise the recommendation.

Ground truth is never shown to the model.

## Entropy

Binary entropy is retained only as a derived diagnostic.

It is not treated as an independent estimator because with exactly two
labels and five samples it is a monotonic transformation of the same
vote count used by SC5_AGREEMENT.

## Direct logprob estimator — excluded

The synthetic capability probe confirmed that Nemotron returns
token-level top-logprobs.

However, under the thinking-enabled configuration used by the project,
the returned logprob stream corresponds to reasoning-generation tokens
rather than a clean visible final-answer label stream.

The local alignment audit showed reasoning text containing candidate
label strings, including an example where reasoning contained both
candidate labels before the visible answer.

Therefore no direct final-label probability can be identified without
an ad-hoc interpretation rule.

`VISIBLE_LABEL_LOGPROB` is consequently excluded from the primary
Gate 6D estimator comparison.

## Calibration mappings

Always evaluated:

1. raw / identity mapping;
2. Platt-style logistic calibration.

Isotonic regression is a sensitivity candidate only when the DEV data
contain at least:

- 20 correct observations;
- 20 incorrect observations;
- 3 distinct raw confidence scores.

## Development comparison

Use five-fold grouped cross-validation.

Grouping unit:

`capture + episode_start_utc`

The exact fold assignment must be frozen before correctness-based
method comparison.

Primary metric:

**out-of-fold Brier score for recommendation correctness**

Secondary diagnostics:

- AUROC for correct-vs-incorrect discrimination;
- AUPRC with incorrect recommendations as the failure class;
- 10-bin ECE;
- reliability diagram;
- capture and episode sensitivity summaries.

A constant-confidence baseline equal to DEV empirical accuracy must
also be reported.

## Selection

1. lowest grouped-CV Brier score;
2. if effectively tied, better correctness-discrimination AUROC;
3. if still tied, prefer SC5_AGREEMENT because it requires no extra
   confidence query beyond the five samples already used to form the
   recommendation.

After selection, refit the chosen calibration mapping using all valid
Calibration-DEV observations.

## Untouched evaluation safeguard

The selected method must be frozen before any Calibration-EVAL model
collection.

Calibration-EVAL is then evaluated once.

If the selected method fails to demonstrate useful correctness
discrimination or does not improve upon the constant-confidence
baseline on untouched Calibration-EVAL, participant-facing calibrated
confidence must not proceed automatically. The protocol must be
explicitly reviewed.

## Still unresolved

- canonical Gate 6D model-input construction;
- deterministic fold assignment;
- exact self-evaluation prompt text;
- participant-facing confidence representation;
- human-study protocol.

Gate 7 has **not** started.

## Bindings

Calibration-boundary SHA256:

`8b5ed36ad1561f3afe78b0d44f29f27ace5f0748ff0074ad64d678840866a3b8`

Synthetic capability probe SHA256:

`fdee07023269633485e34febbf1237df2814d8ae8b8bb7ca7eb5df2edc83e696`
