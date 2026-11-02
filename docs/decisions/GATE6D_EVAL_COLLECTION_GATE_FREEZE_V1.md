# Gate 6D EVAL Collection Gate Freeze V1

Status: FROZEN DISABLED SYNTHETIC-VALIDATED

## Purpose

This freeze locks the pre-EVAL collection gate and synthetic collection
semantics before any real Calibration-EVAL file is opened.

V1 deliberately contains no real EVAL collection mode.

## Frozen collector reuse

Future EVAL collection must reuse the frozen Gate 6D DEV collector V1.2
request construction and parsing semantics rather than independently
reimplementing them.

This locks:

- Nemotron winner model;
- SC5 n=5;
- SC5 temperature=0.4;
- thinking enabled with low effort;
- maximum completion tokens=512;
- frozen per-item SC5 seed;
- exact ESCALATE / DO_NOT_ESCALATE parsing;
- five-sample strict majority recommendation;
- SC5 agreement as majority count / 5;
- VC n=1;
- VC temperature=0;
- same frozen item seed for VC;
- frozen VC system prompt;
- exact integer 0 through 100 parser;
- raw VC confidence as integer / 100;
- frozen transport retry and terminal semantic-invalid behavior.

## Selected estimator branches

SC5 is required for every EVAL item because it creates the frozen
recommendation.

If SC5_AGREEMENT is the selected estimator:

- SC5 is collected;
- VC is prohibited;
- terminal-valid SC5 observations form the valid scoring population.

If VC_SELF_EVAL is the selected estimator:

- SC5 is collected first;
- VC is collected only after terminal-valid SC5;
- valid scoring observations require both terminal-valid SC5 and
  terminal-valid VC.

Terminal semantic-invalid outputs are never regenerated.

## Synthetic evidence

A 12-item synthetic fixture validates both estimator branches.

SC5-selected branch:

- SC5 terminal records: 12;
- one terminal-invalid SC5;
- VC terminal records: 0;
- valid scoring observations: 11.

VC-selected branch:

- SC5 terminal records: 12;
- one terminal-invalid SC5;
- VC terminal records: 11;
- one terminal-invalid VC;
- valid scoring observations: 10.

Three fail-closed tests validate:

- missing required SC5 terminal record;
- duplicate terminal record;
- VC record after invalid SC5.

## Real unlock boundary

Real EVAL collection remains blocked unless BOTH exist:

1. the real DEV method-freeze artifact with status
   FROZEN_METHOD_SELECTED;
2. explicit environment authorization
   GATE6D_ALLOW_EVAL_COLLECTION=YES.

Even if those conditions later become true, this frozen V1 still has no
real collection mode. A separately reviewed and frozen real-capable
implementation is required.

## EVAL sealing

This implementation does not open or hash:

- sealed EVAL model inputs;
- sealed EVAL manifest;
- hidden EVAL ground truth.

Future collection must keep ground truth sealed until the complete
model-output collection has itself been frozen.

## Safety state at freeze

- Real DEV method-freeze artifact exists: NO
- Real EVAL collection gate open: NO
- Sealed EVAL model inputs opened: NO
- Sealed EVAL manifest opened: NO
- Hidden EVAL ground truth opened: NO
- Real EVAL collection performed: NO
- Real EVAL model calls: 0
- External-TEST accessed: NO
- Gate 7 opened: NO
