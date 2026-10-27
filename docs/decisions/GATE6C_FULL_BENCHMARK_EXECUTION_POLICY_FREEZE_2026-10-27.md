# Gate 6C Full-Benchmark Execution Policy Freeze

Freeze date: 2026-10-27  
Status: APPROVED / FROZEN

## Scope

This decision freezes the operational execution policy for the full
Gate 6C zero-budget three-model benchmark before any full benchmark
request or any ground-truth scoring.

The canonical benchmark itself remains unchanged.

Canonical model-input SHA256:

`a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915`

## Frozen candidate set

ZB1:

- provider: Google Gemini API
- model: `gemini-3.6-flash`

ZB2:

- provider: Groq
- model: `openai/gpt-oss-120b`

ZB3:

- provider: Groq
- model: `qwen/qwen3.8-27b`

## Smoke-gate result

All three replacement candidates demonstrated compatibility with the
frozen benchmark interface before full execution.

### ZB1 — Gemini 3.6 Flash

Three predetermined benchmark smoke items:

- DEV-CTU-001
- DEV-CTU-012
- DEV-MUH-001

Logical compatibility:

3 / 3 PASS

Transient HTTP 503 failures were observed and resolved through bounded
retry.

### ZB2 — GPT-OSS 120B via Groq

Three predetermined benchmark smoke items:

3 / 3 PASS

### ZB3 — Qwen 3.8 27B via Groq

Three predetermined benchmark smoke items:

3 / 3 PASS

One HTTP 429 output-token-per-minute rate limit was observed and
resolved through bounded retry.

Smoke testing:

- did not load ground truth
- did not perform accuracy scoring
- did not perform winner selection
- did not access External-TEST

## Full benchmark size

133 frozen benchmark items.

3 candidates.

3 logical runs per item.

Total planned logical model requests:

1,197

Infrastructure retry attempts do not count as additional logical runs.

## Deterministic run ordering

Three item orders must be generated before execution.

For each logical run, the ordering must be derived deterministically
from the frozen item ID and logical run number using SHA-256.

The same logical-run item order must be used for all candidate models.

Ground truth, model outputs, correctness, uncertainty, and prior
performance must not influence ordering.

## Provider execution configuration

### ZB1 — Gemini 3.6 Flash

- `thinkingLevel = low`
- `maxOutputTokens = 512`
- no custom temperature
- no custom top-p
- no custom top-k
- sequential requests only

### ZB2 — GPT-OSS 120B via Groq

- `reasoning_effort = low`
- `temperature = 0`
- `max_completion_tokens = 512`
- `include_reasoning = false`
- sequential requests only
- minimum 10 seconds after successful requests unless live provider
  limits require a longer delay

### ZB3 — Qwen 3.8 27B via Groq

- `reasoning_effort = low`
- `temperature = 0`
- `max_completion_tokens = 512`
- `include_reasoning = false`
- sequential requests only
- minimum 65 seconds after successful requests

The longer Qwen interval is frozen because the smoke test exposed an
organization-level output-token-per-minute limit.

## Run scheduling

Each logical run is executed as a separate candidate/run execution
session.

A candidate therefore has three independently recorded logical runs.

Quota constraints may require execution across multiple sessions or
quota days.

Execution timing must not depend on observed model correctness because
ground truth is prohibited during collection.

## Retry policy

Retries are allowed only for infrastructure/transient failures.

Permitted transient classes:

- transport/network failure represented as status 0
- HTTP 408
- HTTP 429
- HTTP 498
- HTTP 500
- HTTP 502
- HTTP 503
- HTTP 504

Within the initial execution session:

- initial attempt plus at most two retries
- maximum three attempts for one logical request
- provider `Retry-After` must be honored when present
- otherwise bounded increasing backoff is used

The exact implemented delay must be recorded in the execution script
before the full benchmark begins.

An HTTP-200 answer must NOT be retried because:

- it is incorrect
- it is surprising
- it disagrees with another run
- it produces an unwanted class
- it later proves inconvenient for model selection

An HTTP-200 response that is not exactly:

`ESCALATE`

or

`DO_NOT_ESCALATE`

is retained as an invalid model response.

Non-transient configuration/authentication failures such as:

- 400
- 401
- 403
- 404

stop that provider execution session.

The prompt, model, or configuration must not be silently changed.

## Recovery queue

If all permitted attempts for a logical request fail only because of
transient infrastructure conditions, that logical request enters the
recovery queue.

Exactly one later recovery session is permitted under the same frozen
payload and policy.

If recovery is also exhausted, the logical request is recorded as:

`OPERATIONAL_MISSING`

No additional attempts are allowed merely to improve benchmark
completeness.

## Canonical recommendation

Three logical runs are planned per item.

A canonical recommendation requires a valid majority.

At least two valid logical runs are required.

If fewer than two valid runs exist, or no valid majority can be
established, that item is marked invalid for that candidate according
to the frozen scoring framework.

## Ground-truth isolation

`hidden_ground_truth.csv` must NOT be opened by the execution scripts.

No interim accuracy, balanced accuracy, recall, confusion matrix, or
winner table may be calculated while model collection is active.

The required sequence is:

1. complete model collection;
2. complete permitted recovery;
3. freeze and SHA256-hash raw result artifacts;
4. commit raw execution results to Git;
5. only then load hidden ground truth;
6. perform the frozen scoring procedure;
7. apply competence floor;
8. apply frozen winner rule.

## Required provenance

Every request attempt must preserve:

- candidate ID
- requested model
- provider-returned model/version
- item ID
- logical run
- deterministic order position
- attempt number
- UTC timestamp
- HTTP status
- finish reason
- latency
- provider usage metadata
- output
- output SHA256
- raw-response SHA256
- provider error information
- transport error information

Secrets must never be recorded.

## Prohibited adaptive behavior

The following are forbidden during benchmark collection:

- prompt tuning
- evidence tuning
- output-label tuning
- changing model reasoning level
- changing model based on early results
- adding a fourth logical run because of disagreement
- rerunning valid HTTP-200 answers
- inspecting hidden GT
- inspecting held-out External-TEST
- generating interim winner tables

## Zero-budget constraint

The execution must remain $0.

The paid OpenAI API must not be used.

If a provider requires payment before completion, the affected Gate
6C-2 decision must be formally reopened.

## External-TEST

The following remain untouched:

- hideandseek1
- mirai34
- trojan42

## Gate status

Gate 6B:
PASSED / FROZEN

Gate 6C-1:
PASSED / FROZEN

Gate 6C-2 zero-budget candidate set v2:
PASSED / FROZEN

Canonical benchmark:
PASSED / FROZEN

Smoke compatibility:
PASSED

Full-benchmark execution policy:
PASSED / FROZEN

Full benchmark:
NOT YET EXECUTED

Ground-truth scoring:
NOT YET EXECUTED

Gate 6C model winner:
OPEN
