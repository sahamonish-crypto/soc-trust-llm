# Gate 6D Secondary Uncertainty and Sensitivity Protocol V1

Status: FROZEN PROSPECTIVE SECONDARY PROTOCOL

## Purpose

This protocol prospectively defines uncertainty intervals and
sensitivity analyses before real Gate 6D DEV correctness results are
examined.

These analyses are secondary.

They cannot change the already-frozen primary estimator/calibrator
selection procedure.

## Cluster structure

Alert observations are not treated as independent bootstrap units.

The bootstrap unit is the frozen episode group:

`capture + episode_start_utc`

Episode clusters are sampled with replacement within each capture
stratum. All alert rows belonging to a sampled episode are carried
together, including multiplicity if an episode is drawn more than once.

Capture identity is treated as a fixed stratification variable rather
than a resampling unit because the DEV data contain too few independent
top-level captures for defensible capture-level bootstrap inference.

## Confidence intervals

Use 10,000 deterministic bootstrap replicates.

For each metric, report the 2.5th and 97.5th percentiles using linear
quantile interpolation.

The same cluster draws are reused across candidate methods so paired
comparisons remain paired.

Bootstrap replicates that make AUROC or AUPRC undefined are retained as
undefined and are never silently redrawn.

A CI is reported only if at least 95% of the 10,000 replicates yield a
defined metric.

## Scope of uncertainty

The bootstrap operates on the already-frozen grouped out-of-fold
predictions.

Calibration mappings are not refit inside each bootstrap replicate.

Therefore these intervals quantify conditional sampling uncertainty of
the realized OOF predictions under episode clustering. They are not
claimed to represent full model-training or calibration-fitting
uncertainty.

This choice keeps the secondary interval analysis separate from the
frozen grouped-CV method-selection procedure.

## Metrics

Secondary 95% cluster-bootstrap intervals are produced for:

- Brier score for correctness;
- AUROC for correctness;
- AUPRC with incorrect recommendation as the positive class;
- fixed-bin ECE10.

Reliability diagrams retain the already-frozen ten equal-width bins.
Bin-wise bootstrap intervals are not required.

## Paired estimator sensitivity

On the frozen paired-common-valid population, SC5_AGREEMENT and
VC_SELF_EVAL are compared using identical episode bootstrap draws.

For each calibrator type, a paired difference is calculated only if both
corresponding candidate rows are valid:

`metric(VC_SELF_EVAL) - metric(SC5_AGREEMENT)`

The calibrators are:

- identity;
- Platt;
- isotonic, if both isotonic rows are valid.

These paired intervals are descriptive secondary analyses. They do not
supply a new significance threshold or alter the primary winner.

## Ground-truth-class sensitivity

Class-specific summaries use the frozen decision classes:

- ESCALATE;
- DO_NOT_ESCALATE.

Brier, ECE10, and discrimination metrics when mathematically defined are
reported separately by class.

## Capture sensitivity

Metrics are reported separately for each DEV capture.

No inferential population claim is made from capture-to-capture
variation because there are too few top-level captures.

## Episode influence

A leave-one-episode-out analysis is performed using the frozen OOF
predictions.

For each metric, report:

- minimum leave-one-episode-out value;
- maximum leave-one-episode-out value;
- maximum absolute deviation from the full-data value;
- episode producing that maximum deviation.

Episode influence cannot alter the frozen method-selection winner.

## Determinism

Bootstrap namespace:

`GATE6D_SECONDARY_BOOTSTRAP_V1`

SHA256:

`bc9ed85d9834fe9da0849c7c6f19f4e202eba21b59ab510b51e1ae0510ca04b6`

Frozen uint63 seed:

`4368166585093127837`

## Literature basis

The design follows methodological guidance favoring cluster-level
resampling when observations are nested, rather than treating correlated
lower-level observations as independent.

The use of capture-stratified episode resampling avoids pretending that
the very small number of top-level captures supports conventional
capture-level bootstrap inference.

A percentile interval is frozen for all reported metrics to provide one
prospective, reproducible rule that remains usable for non-smooth
statistics such as fixed-bin ECE.

Relevant methodological references include:

Francis L. Huang (2018), "Using Cluster Bootstrapping to Analyze Nested
Data With a Few Clusters", Educational and Psychological Measurement.

Konrad Menzel (2021), "Bootstrap With Cluster-Dependence in Two or More
Dimensions", Econometrica.

B. Efron and B. Narasimhan (2020), "The automatic construction of
bootstrap confidence intervals", Journal of Computational and Graphical
Statistics.

G. Rousselet, Pernet Cyril, and R. Wilcox (2019), "The Percentile
Bootstrap: A Primer With Step-by-Step Instructions in R", Advances in
Methods and Practices in Psychological Science.

D. Andrews and Moshe Buchinsky (2002), "On the Number of Bootstrap
Repetitions for BCa Confidence Intervals", Econometric Theory.

## Governance

Nothing in this secondary analysis changes:

- the frozen Brier primary criterion;
- the 0.01 effective-tie threshold;
- the AUROC tie-break;
- the SC5 remaining tie-break;
- the requirement to freeze the DEV method before touching EVAL.

## Safety state at freeze

- Real DEV correctness inspected: NO
- Real DEV ground truth read: NO
- Correctness-based real analysis performed: NO
- Calibration-EVAL accessed: NO
- External-TEST accessed: NO
- Model calls: 0
