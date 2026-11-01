# Gate 6C Deterministic Scorer V1 Freeze

Status: FROZEN BEFORE AUTOMATED CORRECTNESS SCORING

## Scorer

Path:

scripts/gate6/score_gate6c_v1.py

SHA256:

6e4216609af0fdc880055a7b47c958d547455d165c1cee7f98d3ff9d4721a678

## Frozen bindings

Scoring specification SHA256:

56d07ed3bfc7cc715ebe883a41cdc0209b2e4ba638ab477bfb39446527372009

Pre-scoring implementation contract SHA256:

cff42db4d76f8a4879000a4fe3843d617b5cebe2479f1f64b8dd78095889a855

Ground-truth exposure deviation artifact SHA256:

51ccd08724fc35f16f4825ba945706ff31493df43116678e704dac4cf21a8cd1

All-candidate raw-collection lock SHA256:

ca1b350e6933a8d65e1c871f4cea33164ef42355692566802835e7f1577e3e5c

Item metadata SHA256:

442b486e3bd1f5e098ab49cf4ebf990b9d2c6d3786fb66c73839ee9ce155c9b9

Canonical benchmark SHA256:

a4cb01041ed16de2eae6fce2abb8036317fc068653b8abdd0812d6424b3a4915

## Scoring behavior frozen

The scorer implements:

- majority of the three valid logical runs;
- minimum two valid runs for a canonical majority;
- INVALID_FOR_CANDIDATE when no valid majority exists;
- strict invalid-canonical handling fixed in the pre-scoring contract;
- CTU evidence-covered balanced accuracy as the primary metric;
- CTU overall balanced accuracy;
- Redline-only balanced accuracy;
- Remcos-only balanced accuracy;
- class-specific CTU error counts;
- logical-response invalid-output rate;
- Muhstik External-DEV malicious ESCALATE recall;
- three-run stability;
- median successful HTTP-200 latency;
- provider usage totals;
- frozen competence floor;
- frozen winner hierarchy.

No comparable USD cost is invented post hoc.

If the final cost tie-break is required without comparable cost data, the
scorer returns an unresolved protocol-review state.

## Protection

At freeze time:

Ground-truth correctness read by scorer: NO

Automated correctness scoring performed: NO

External-TEST accessed: NO

The scorer requires an explicit confirmation token before scoring and
requires itself plus protected scientific artifacts to be committed and
clean before ground-truth scoring can execute.
