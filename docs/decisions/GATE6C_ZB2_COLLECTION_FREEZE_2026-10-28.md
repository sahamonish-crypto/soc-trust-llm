# Gate 6C ZB2 Complete Collection Freeze

Freeze date: 2026-10-28  
Status: COMPLETE / FROZEN

## Candidate

ZB2

Provider:

Groq

Model:

`openai/gpt-oss-120b`

## Frozen collection

The candidate completed all three frozen logical benchmark runs.

Run 1:

- 133 / 133 final logical responses valid
- 133 API attempts
- no recovery required

Run 2:

- 133 / 133 final logical responses valid
- 133 API attempts
- no recovery required

Run 3:

- 133 / 133 final logical responses valid
- 222 total API attempts
- 89 HTTP 429 rate-limit responses
- 5 logical requests entered the frozen recovery queue
- all 5 subsequently recovered successfully
- 0 operationally missing items

## Overall ZB2 result collection

Planned logical responses:

399

Successfully collected valid logical responses:

399 / 399

Total API attempts:

488

HTTP 200 responses:

399

HTTP 429 responses:

89

Permanent operational missing:

0

## Integrity

No hidden ground truth was loaded during collection.

No accuracy, balanced accuracy, recall, confusion matrix, or winner
selection was performed.

No External-TEST scenario was accessed.

No valid HTTP-200 response was repeated merely because of its output.

Rate-limit retries and recovery followed the previously frozen
execution policy.

## Status after freeze

ZB2 full collection:
COMPLETE / FROZEN

ZB1 full collection:
NOT YET COMPLETE

ZB3 full collection:
NOT YET COMPLETE

Ground-truth scoring:
NOT YET PERMITTED

Gate 6C winner:
OPEN
