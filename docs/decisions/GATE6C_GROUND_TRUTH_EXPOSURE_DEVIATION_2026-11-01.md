# Gate 6C Ground-Truth Exposure Protocol Deviation

Status: DOCUMENTED PROTOCOL DEVIATION

Documented UTC: 2026-11-01T18:00:23.486209+00:00

## Event

The hidden Gate 6C ground-truth CSV was accidentally displayed manually
using:

- `cat benchmarks/gate6c/hidden_ground_truth.csv`
- `head benchmarks/gate6c/hidden_ground_truth.csv`

This occurred after the complete all-candidate raw-model-output collection
had already been frozen and committed.

## Pre-existing protections

Before this exposure:

- all three candidates had completed their frozen three-run collections;
- all 1,197 logical candidate/run/item results were frozen;
- the all-candidate raw-collection lock had been committed;
- the scoring specification had already been frozen;
- no automated ground-truth scoring had been performed;
- the Gate 6C winner remained OPEN.

Frozen scoring specification SHA256:

56d07ed3bfc7cc715ebe883a41cdc0209b2e4ba638ab477bfb39446527372009

Raw-collection lock SHA256:

ca1b350e6933a8d65e1c871f4cea33164ef42355692566802835e7f1577e3e5c

Hidden-ground-truth SHA256 recorded after accidental display:

a54dda3cea2414cfddd6a49f19afc885e008d6c5edbe4cb85186e11fcd3b39af

## Consequence

This is a sequence/provenance deviation and must not be concealed.

It does not authorize any change to:

- model outputs;
- benchmark membership;
- prompt;
- evidence bundles;
- candidate models;
- canonical three-run voting;
- metric definitions;
- competence floor;
- winner rule;
- tie-breaking hierarchy.

No model may be selectively rerun based on the exposed labels.

## Mitigation

The deterministic scoring implementation must now be created strictly
from the already-frozen scoring specification and frozen execution policy.

That implementation must itself be frozen before the first automated
scoring run.

External-TEST remains untouched.
