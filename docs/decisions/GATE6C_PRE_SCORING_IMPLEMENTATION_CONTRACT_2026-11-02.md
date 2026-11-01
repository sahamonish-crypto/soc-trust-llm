# Gate 6C Pre-Scoring Implementation Contract

Status: FROZEN BEFORE AUTOMATED CORRECTNESS SCORING

This decision fixes implementation details required to translate the
already-frozen Gate 6C scoring specification into deterministic code.

## Pre-correctness structural observations

These observations use model-output validity only, not ground-truth
correctness.

- ZB1: 399/399 valid logical responses; 133/133 canonical-majority items.
- ZB2: 399/399 valid logical responses; 133/133 canonical-majority items.
- ZB3: 386/399 valid logical responses; 129/133 canonical-majority items;
  four items are INVALID_FOR_CANDIDATE.

The frozen competence criterion requires at least 99% valid benchmark
responses.

Therefore:

- ZB1 passes the validity component.
- ZB2 passes the validity component.
- ZB3 fails the validity component at 96.742%.

This conclusion does not use hidden-ground-truth correctness.

## Invalid canonical predictions

For strict class-recall and balanced-accuracy reporting, an
INVALID_FOR_CANDIDATE canonical prediction cannot count as a correct
prediction. It remains in its true-class denominator and contributes
zero to the correct-prediction numerator.

A canonical-valid-only sensitivity metric and coverage must also be
reported.

If an otherwise competence-eligible candidate has an invalid canonical
prediction relevant to winner selection, automated winner selection
must halt for explicit protocol review rather than silently changing
the denominator rule.

Under the already-observed pre-correctness structure, ZB3 is independently
ineligible because its logical-response validity is below 99%.

## Frozen benchmark strata

- CTU DEV: 87
- CTU evidence-covered: 73
- Redline: 68
- Remcos: 19
- Muhstik External-DEV: 46

Primary metric:

CTU evidence-covered balanced accuracy.

## Stability

Three-run stability is the fraction of the 133 items for which all three
logical runs return the same valid label.

## Latency

The winner-rule latency statistic is the median latency_ms of successful
HTTP-200 model attempts.

HTTP 429 responses, provider waiting periods, and transport failures are
retained as operational provenance but are not interpreted as model
inference latency.

## Cost

The raw attempt files contain usage quantities but no directly comparable
USD cost field across all three providers.

Usage quantities must be reported.

No post-hoc price assumption may be introduced merely to break a tie.

If the frozen winner procedure reaches the final cost criterion and no
comparable frozen cost measure exists, the automated procedure must
return an unresolved tie requiring explicit protocol review.

## Protection

This contract was fixed before automated correctness scoring.

It does not change:

- benchmark membership;
- model outputs;
- majority-vote rule;
- primary metric;
- competence floor;
- winner hierarchy;
- External-TEST protection.

Automated correctness scoring performed: NO

External-TEST accessed: NO
