# Pre-Gate-7 Readiness Checklist V1

**Status:** PREPARATION ONLY
**Gate 7:** NOT OPENED

This document permits preparation work only. It does not authorize
participant recruitment, participant-facing deployment, or use of
unfrozen calibration results.

## Mandatory Gate 6 prerequisites before Gate 7 can open

- [ ] DEV500 uncertainty collection complete.
- [ ] DEV500 raw collection/provenance frozen.
- [ ] Frozen calibration-analysis implementation used without post-hoc changes.
- [ ] Real DEV correctness analysis completed.
- [ ] Uncertainty estimator selected under frozen rules.
- [ ] Calibrator selected under frozen rules.
- [ ] Selected estimator/calibrator method frozen.
- [ ] Calibration-EVAL run exactly once after method freeze.
- [ ] Calibration-EVAL passes the predeclared stopping criterion.
- [ ] Participant-facing confidence-generation procedure frozen.
- [ ] Gate 6 formally marked PASS/CLOSED.

## Work permitted before Gate 7 opens

The following may be prepared using synthetic or placeholder values:

- experiment UI structure;
- logging/event schema;
- participant/session ID handling;
- trial randomization framework;
- condition-assignment framework;
- timing instrumentation;
- response validation;
- NASA-TLX collection interface;
- trust/reliance questionnaire interface;
- demographic/experience questionnaire structure;
- exclusion-rule implementation;
- statistical-analysis code skeleton;
- reproducibility documentation;
- synthetic integration tests.

## Work prohibited before Gate 7 opens

- recruiting real participants;
- running pilot participants on final study materials;
- exposing provisional calibrated confidence as final study evidence;
- using Calibration-EVAL results before the method freeze;
- changing Gate 6 model-selection/calibration rules based on observed outcomes;
- accessing External-TEST for Gate 7 preparation.

## Safety boundary

All pre-Gate-7 software must use synthetic or placeholder uncertainty
values until Gate 6 is formally closed.

Any component requiring the final selected/calibrated confidence must
fail closed when that frozen artifact is unavailable.

## Current state

- Gate 6D: OPEN
- DEV500 target: 500
- DEV500 collection: INCOMPLETE
- Calibration analysis core: FROZEN
- Brier effective-tie threshold: FROZEN at `< 0.01`
- Calibration-EVAL: UNTOUCHED
- External-TEST: UNTOUCHED
- Gate 7: NOT OPENED
