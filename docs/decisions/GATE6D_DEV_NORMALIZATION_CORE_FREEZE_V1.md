# Gate 6D DEV Normalization Core Freeze V1

Status: FROZEN SYNTHETIC-VALIDATED

This freeze locks the DEV500 normalization and join semantics before
the implementation is permitted to inspect real Gate 6D DEV outputs
or hidden DEV ground truth.

## Frozen primary population

The primary estimator/calibrator comparison uses the paired
common-valid DEV population, consistent with the frozen invalid-output
comparison policy.

## Frozen validation behavior

The normalizer:

- requires exactly 500 selected DEV identifiers;
- requires the frozen five-fold DEV500 structure;
- rejects duplicate selected terminal records;
- requires an SC5 terminal record for every selected item after
  collection is declared complete;
- requires a VC terminal record for every valid SC5 item after
  collection is declared complete;
- verifies exact SC5 recommendation labels;
- verifies SC5 majority and agreement consistency;
- restricts SC5 agreement to 0.6, 0.8 or 1.0;
- verifies VC frozen recommendation equals the SC5 majority;
- verifies VC integer confidence is within 0 through 100;
- verifies VC raw confidence equals integer confidence divided by 100;
- mirrors the frozen collector's integer parser, including valid
  leading-zero strings such as "08";
- ignores historical terminal records outside the frozen DEV500 subset;
- fails closed if paired common-valid data lose any frozen fold.

## Invalid-output policy

Terminal semantic-invalid outputs are not regenerated.

Coverage and invalid reasons remain reportable, but coverage does not
change the frozen primary winner rule.

## Post-selection support

All-valid SC5 normalized rows are retained separately from the paired
primary comparison population so that, if SC5 wins, the winning
calibrator may later be refit on all valid SC5 DEV observations as
required by the parent protocol.

## Safety state at freeze

- Real DEV outputs read: NO
- Real DEV ground truth read: NO
- Correctness-based real comparison performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Model calls: 0

The real file-loading layer remains disabled until DEV500 collection
is complete and separately frozen.
