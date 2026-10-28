# Gate 6C-2 ZB1 Reopening — Operational Infeasibility

Date: 2026-10-28

Status: ZB1 ONLY REOPENED

## Scope

This decision reopens only the ZB1 candidate selection within Gate 6C-2.

It does not reopen ZB2, ZB3, the canonical benchmark, prompt, evidence,
three-run requirement, scoring specification, competence floor, winner
rule, or External-TEST protection.

## Previous ZB1

Provider:

Google Gemini API

Model:

gemini-3.6-flash

## New evidence discovered after freeze

During the frozen full-benchmark execution, the provider returned repeated
HTTP 429 RESOURCE_EXHAUSTED responses.

The provider response explicitly identified:

quotaId:

GenerateRequestsPerDayPerProjectPerModel-FreeTier

quotaValue:

20

Description:

Generate content requests per day limit exceeded on Free Tier.

Therefore, the project's verified free-tier limit for gemini-3.6-flash is
20 generate-content requests per day.

The frozen ZB1 benchmark requires 399 logical responses before accounting
for infrastructure retries.

At 20 requests/day, completion would require approximately 20 quota days
even in the impossible best case of zero retries.

This is judged operationally infeasible under the project's frozen
zero-budget constraint.

## Scientific interpretation

This reopening is caused by provider infrastructure/quota feasibility.

It is NOT caused by:

- benchmark accuracy;
- model correctness;
- class distribution;
- comparison against ground truth;
- interim winner analysis.

Ground truth remained unopened.

No scoring was performed.

## Partial Gemini provenance

All partial Gemini 3.6 full-benchmark artifacts are retained under:

benchmarks/gate6c/full/superseded/ZB1_gemini36_2026-10-28/

These observations are superseded operational provenance and MUST NOT be
included in final model-performance scoring.

They must not be deleted.

## Replacement-selection principles

The replacement must:

1. remain zero-cost;
2. provide sustainable capacity for 399 logical responses;
3. be a strong current general-purpose reasoning/instruction model;
4. preserve evidence-grounded binary task comparability;
5. use the identical frozen benchmark and prompt;
6. have tools/search disabled;
7. be tested for access/quota compatibility before benchmark exposure;
8. be frozen before receiving benchmark items;
9. not use hidden ground truth during selection;
10. not alter ZB2 or ZB3 results.

## Current externally researched replacement hierarchy

Preferred candidate:

NVIDIA Nemotron 3 Super 120B A12B via Cloudflare Workers AI.

Fallback hierarchy if the preferred candidate fails synthetic
access/capacity testing:

1. Mistral Small 4 through Mistral Studio Free mode.
2. Google Gemma 4 26B A4B through Cloudflare Workers AI.
3. GLM-4.7-Flash through Cloudflare Workers AI.

The preferred candidate is NOT yet frozen.

No replacement benchmark inference has been executed.

## Unchanged frozen components

ZB2 openai/gpt-oss-120b collection remains COMPLETE / FROZEN.

ZB3 qwen/qwen3.8-27b remains unchanged.

Canonical 133-item benchmark remains frozen.

Canonical model input SHA256 remains:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

Ground-truth scoring remains prohibited.

External-TEST remains untouched.

## Gate status

Gate 6C-2:

REOPENED FOR ZB1 ONLY

ZB1 replacement:

OPEN

ZB2:

COMPLETE / FROZEN

ZB3:

FROZEN CANDIDATE / COLLECTION NOT YET COMPLETE

Gate 6C winner:

OPEN
