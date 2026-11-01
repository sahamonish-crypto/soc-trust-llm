# Gate 6C All-Candidate Raw-Collection Lock

Status: FROZEN
Locked UTC: 2026-11-01T17:42:44.897459+00:00

## Final raw collection

ZB1:
- 399/399 terminal results
- VALID_HTTP200: 399
- INVALID_HTTP200: 0

ZB2:
- 399/399 final terminal results
- VALID_HTTP200: 399
- INVALID_HTTP200: 0
- ZB2 Run 3 retains five historical RECOVERY_QUEUED records;
  all five subsequently resolved to VALID_HTTP200.

ZB3:
- 399/399 terminal results
- VALID_HTTP200: 386
- INVALID_HTTP200: 13
- invalid-format HTTP-200 outputs remain frozen observed model behavior
  and were not selectively retried.

All candidates combined:
- terminal results: 1,197 / 1,197
- valid-format HTTP-200: 1,184
- invalid-format HTTP-200: 13

## Cross-candidate checks

- all nine candidate/run combinations contain exactly the canonical
  133 item IDs;
- each final run covers order positions 1 through 133;
- requested models match the frozen candidate configuration;
- no unresolved recovery item remains;
- no provider model-ID mismatch remains;
- protected benchmark, candidate, policy, runner, and order artifacts
  remain committed and clean.

## Scientific isolation

Ground truth loaded: NO
Scoring performed: NO
Interim candidate comparison: NO
External-TEST accessed: NO
Gate 6C winner: OPEN

This lock closes model-output collection before hidden ground truth is
opened.
