# Gate 6B + External Corpus Freeze

Freeze date: 2026-10-26
Status: APPROVED / FROZEN

## 1. Gate 6B Exact Retrieval Configuration

The following configuration is frozen for confirmatory use.

1. Evidence snapshot cutoff:
   T_alert + 30 seconds.

2. Retrieval horizon:
   [-30 seconds, +30 seconds] around the first alert.

3. Retrieval priority:
   a. Exact Community ID / validated flow mapping first.
   b. Same direction-independent endpoint pair second.

4. Permitted factual telemetry:
   - dns
   - http
   - tls
   - fileinfo
   - smb
   - dcerpc
   - rdp
   - ldap
   - krb5
   - kerberos
   - ssh

5. Pattern-level factual deduplication:
   Repeated equivalent application/factual telemetry is collapsed into
   distinct evidence patterns.

   Timestamps and ephemeral transport source ports are not used to create
   artificial pattern diversity.

   Occurrence counts/ranges may be retained as factual metadata.

6. Evidence budget:
   Maximum 6 distinct evidence patterns.

7. Ranking:
   Deterministic.

8. Prohibited retrieval inputs:
   - ground-truth label
   - attack label
   - AI correctness
   - confidence
   - uncertainty

9. Insufficient evidence:
   Item may be excluded.
   Evidence must never be fabricated.

10. Experimental-arm invariant:
    C3 and C4 must receive byte-identical evidence and an identical
    evidence hash.

This exact configuration may not be changed silently.
Any change requires formally reopening Gate 6B.

---

## 2. External Validation Corpus

Corpus expansion is CLOSED.

Primary human-study corpus remains CTU-SME-11.

IoT-23 is a secondary external robustness/generalization corpus.

### External-DEV

- muhstik3

This scenario may be used during model-selection development only after
episode/campaign-aware deduplication and sampling are fixed.

### Held-out External-TEST

The following scenarios must not be used to select, tune, or modify the
model, prompt, retrieval method, calibration method, thresholds, or other
system configuration:

- hideandseek1
- mirai34
- trojan42

These remain held out until the relevant system configuration is frozen.

### Coverage diagnostics only

- torii20
- hakai8

These are retained as detector/retrieval coverage diagnostics and are not
used to relax the external-validation criterion.

---

## 3. Corrected IoT-23 Audit Result

A parser defect was identified and corrected before freezing.

Cause:
IoT-23 label files use whitespace formatting that caused the earlier
tab-oriented parser to read the label column as blank.

Corrected source-label sanity checks included:

- trojan42:
  Benign 4420
  Malicious 6

- torii20:
  Benign 3193
  Malicious 16

- muhstik3:
  Benign 4536
  Malicious 151567

- mirai34:
  Benign 1923
  Malicious 21222

- hakai8:
  Benign 2181
  Malicious 8222

- hideandseek1:
  Benign 469275
  Malicious 539473

Corrected Suricata/GT/evidence audit:

- trojan42:
  mapping 100%
  malicious alerted CIDs 5
  non-overt 5
  usable 5

- torii20:
  mapping 100%
  malicious alerted CIDs 3
  non-overt 3
  usable 0

- muhstik3:
  mapping 100%
  malicious alerted CIDs 46935
  non-overt 5153
  usable 4683

- mirai34:
  mapping 100%
  malicious alerted CIDs 1740
  non-overt 1740
  usable 10

- hakai8:
  mapping 0%
  malicious alerted CIDs 0
  usable 0

- hideandseek1:
  mapping 100%
  malicious alerted CIDs 3358
  non-overt 3358
  usable 2557

Predeclared stopping criterion:

- >= 3 scenarios with usable malicious cases
- >= 30 usable non-overt malicious cases

Observed:

- 4 / 6 scenarios with usable malicious cases
- 7255 usable non-overt malicious cases

Result:

OVERALL TARGET PASS = TRUE

Therefore:

CORPUS EXPANSION IS CLOSED.
NO FURTHER DATASET HUNTING IS PERMITTED UNLESS A LATER GATE IS
FORMALLY REOPENED FOR A DOCUMENTED SCIENTIFIC REASON.

---

## 4. Important Statistical Constraint

The 7255 usable external cases are NOT 7255 independent experimental
samples.

Large campaigns such as Muhstik and Hide-and-Seek contain highly
correlated flows.

Before model benchmarking, an episode/campaign-aware deduplication and
sampling procedure must be fixed.

Random flow-level sampling across correlated campaign traffic is not
permitted.

---

## 5. Gate 6C Status

Gate 6C-1:
FROZEN.

Gate 6C-2 candidate models:
FROZEN.

Primary candidate set:

- gpt-6.1-sol
- claude-sonnet-5-5
- deepseek-v4-pro

The actual benchmark winner remains OPEN.

No model winner is frozen by this document.

External-TEST scenarios may not influence model selection.

---

## 6. Previously Frozen Suricata Inputs

Suricata version:
8.0.7

Frozen rule-set SHA256:
23001ce41f828d6b01370a10fe81442d6beddb7f350e07f5fa7f458e223ed2e1

Frozen working configuration SHA256:
e08988a1311423b6823b14408c1425b71d5301fbdc778993a07e4572ccad2ee8

Replay requirement:
--runmode single

Ground truth remains independent of Suricata.
