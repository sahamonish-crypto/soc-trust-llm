# Gate 6D DEV Collection Implementation Amendment v1.1

**Date:** 2026-11-02
**Status:** FROZEN — IMPLEMENTATION-ONLY AMENDMENT

## Trigger

Frozen collector v1 completed 147 SC5 and 147 VC records successfully.

At unresolved item `G6D-D-0148`, Cloudflare then returned HTTP 429
responses containing provider code `4006` and the explicit message that
the daily free allocation of neurons had been exhausted.

The frozen v1 collector recognized quota code `3036` only. It therefore
treated the observed `4006` quota response as an ordinary retryable
HTTP-429 infrastructure failure and produced two clean
`INFRASTRUCTURE_RETRY_LIMIT_PAUSE` events.

No terminal SC5 or VC record was created for item 0148.

## Amendment

Frozen collector v1 remains unchanged.

Collector v1.1 additionally recognizes daily quota exhaustion when any
of the following is present:

1. provider code `3036`;
2. observed provider code `4006`;
3. an explicit response message containing both
   `daily free allocation` and `neurons`.

Such a response causes a clean session pause. The unresolved logical
item is not made terminal and resumes unchanged later.

Ordinary HTTP-429 retry behavior is unchanged.

## Scientific protocol

**No scientific design element changes.**

The following remain identical:

- canonical DEV inputs;
- model;
- SC5 `n=5`;
- SC5 temperature `0.4`;
- frozen item seeds;
- majority rule;
- SC5 agreement;
- VC prompt;
- VC `n=1`;
- VC temperature `0`;
- semantic-invalid handling;
- grouped DEV folds;
- EVAL seal.

## Provenance

Frozen v1 SHA256:

`fd942351e591877429469b3f5b54fc3d7e7afbd54ea6f8bd71e1efc5d922e1f2`

Collector v1.1 SHA256:

`62a03bb1f028fe41df1fc49fc99673ccc7fa8672a0f59607a4bee28d0a7e9c60`

VC prompt SHA256:

`51bb3bb0912123a315dba5c34cb08bed103f2a6b51795febbe2125e31cb47f2d`

v1.1 collection-spec SHA256:

`5534cbfa7d4549d428d9b78f0547b855e9f24107d80683d6bbf7e22a1ab08efa`

Observed item-0148 infrastructure attempts:

- attempts: **10**
- HTTP status: **429**
- provider code: **4006**
- retry-limit pause events: **2**
- terminal SC5 result: **NO**
- terminal VC result: **NO**

## Collection state

- SC5 terminal: **147 / 1222**
- SC5 valid: **147**
- VC terminal: **147 / 1222**
- VC valid: **147**
- Calibration-EVAL calls: **0**
- External-TEST accessed: **NO**

## Resume rule

Resume only from unresolved item `G6D-D-0148` using collector v1.1 when
the provider permits inference again.

Do not recollect items `G6D-D-0001` through `G6D-D-0147`.
