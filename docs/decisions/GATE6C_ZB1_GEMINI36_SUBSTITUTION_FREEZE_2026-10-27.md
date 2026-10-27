# Gate 6C ZB1 Gemini Substitution Freeze

Freeze date: 2026-10-27
Status: APPROVED / FROZEN

## Previous ZB1

gemini-3.8-flash

## Reason for substitution

The frozen zero-budget smoke test showed repeated operational failures for
gemini-3.8-flash:

- two transport timeouts
- repeated HTTP 503 provider-capacity failures
- bounded retry attempts did not resolve compatibility

These failures occurred before benchmark scoring and without loading
ground truth.

The failures were treated as an execution-feasibility problem, not model
performance.

## Candidate feasibility check

gemini-3.6-flash was tested only with synthetic compatibility prompts.

No benchmark items were used.

Initial 64-token feasibility test:

- HTTP 200 on all requests
- one response exhausted the output budget with MAX_TOKENS because
  thinking tokens consumed the small 64-token limit
- two requests returned exact OK

The configuration was then corrected to the intended benchmark-compatible
maximum output budget:

- thinkingLevel: low
- maxOutputTokens: 512

Corrected synthetic feasibility result:

- attempt 1: HTTP 200, exact OK
- attempt 2: HTTP 200, exact OK
- attempt 3: HTTP 200, exact OK

Result:

3 / 3 PASS

No ground truth was loaded.
No benchmark item was shown to gemini-3.6-flash.
No winner selection occurred.

## Frozen replacement

ZB1:

gemini-3.6-flash

ZB2 remains:

openai/gpt-oss-120b via Groq

ZB3 remains:

qwen/qwen3.8-27b via Groq

## Unchanged research artifacts

The following remain frozen and unchanged:

- canonical 133-item benchmark
- canonical model input SHA256:
  a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915
- Gate 6B evidence configuration
- hidden ground truth
- scoring specification
- competence floor
- winner rule
- Muhstik External-DEV episode selection
- held-out External-TEST protection

## Gate status

Gate 6C-2 zero-budget candidate set v2:
FROZEN

Smoke compatibility for ZB2:
PASS

Smoke compatibility for ZB3:
PASS

Smoke compatibility for replacement ZB1:
NOT YET TESTED ON BENCHMARK ITEMS

Full benchmark:
NOT YET EXECUTED

Gate 6C model winner:
OPEN
