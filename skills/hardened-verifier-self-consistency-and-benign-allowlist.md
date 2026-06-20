---
name: hardened-verifier-self-consistency-and-benign-allowlist
description: "How to harden a final verification script for a validated dataset so it touches substance instead of linting surface, and how to separate genuine errors from the verifier's own regex artifacts using a reviewed-benign allowlist. A weak verifier (link-exists + vocabulary regex + a ~0.5% line-number spot check) gives false assurance; a hardened one re-binds cited sources on a large sample, independently re-checks arithmetic, foots totals across tiers, and asserts the verdict tally is identical everywhere it is reported. Use when: (1) signing off on a large validated dataset of records/fields with derivations and totals and the existing checker only verifies links/vocabulary/format; (2) a process reports its own pass/fail tally in more than one place and you need them to agree; (3) a hardened checker emits many findings and you must distinguish real data errors from regex limitations, public identifiers, and intentional descriptive formatting; (4) you want an auditable clean run where every hard finding is on a reviewed allowlist with a written justification rather than silently suppressed."
category: testing
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - verification
  - dataset
  - self-consistency
  - allowlist
  - false-assurance
  - provenance
---

# Hardened Verifier: Self-Consistency and Reviewed-Benign Allowlist

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Replace a surface-only final verifier for a validated dataset with one that touches substance (sources, arithmetic, cross-tier totals, count self-consistency), then separate genuine errors from the verifier's own regex artifacts. |
| **Outcome** | Successful. Verifier run to a clean exit on a real ~2,900-field dataset. Hardening plus artifact classification took the run from ~131 raw HARD findings to 0 genuine ones — each residual is a verifier-regex limit, a public identifier, an intentional descriptive format, or a manually-reviewed allowlisted item. |
| **Verification** | verified-local (verifier reached a clean exit on a real ~2,900-field dataset; not run in CI) |

## When to Use

- You are about to sign off on a large validated dataset (records/fields with cited sources, derivations, and totals) and the existing verifier only checks that links exist, that vocabulary matches a regex, and a tiny line-number spot check (~0.5% of rows).
- A process reports its own verdict tally (pass/fail counts) in more than one artifact — its run summary, a generated provenance document, a delta/summary report — and you need to guarantee they agree.
- A newly hardened checker is emitting many findings and you cannot tell real data errors apart from artifacts of the checker's own regex, public identifiers, or intentional descriptive formatting.
- You want a clean run to mean "every hard finding is on a reviewed allowlist with a written reason" (auditable sign-off), not "findings were silently deleted."

## Verified Workflow

A final verifier for a validated dataset must TOUCH THE SUBSTANCE, not just lint the surface. Surface checks (link-exists, vocabulary regex, a ~0.5% line-number spot check) give false assurance — they pass while the underlying records are wrong. Harden along five axes, then classify every finding HARD vs soft and route cleared HARD findings to a reviewed-benign allowlist.

### Quick Reference

```text
# Five hardening axes (substance, not surface)
1. SOURCE-EXISTENCE / quote re-binding   — large sample (not ~15 rows): each cited source exists; quote appears in it
2. ARITHMETIC re-check                    — independently recompute EVERY equation in derivations/values
3. CROSS-TIER FOOTING                      — index total == sum(section rows) == sum(item values); gross AND de-duplicated
4. COUNT SELF-CONSISTENCY                  — verdict tally IDENTICAL in run-summary == provenance-doc == delta/summary; FAIL on any divergence
5. PII/VOCAB/FORMAT across ALL tiers       — index + sections + side-notes, not just leaf items

# Classify every finding
HARD = broken link (excluding pre-existing documented), genuine arithmetic mismatch,
       count inconsistency, true PII, missing source file
soft = descriptive-formatting variant (non-blocking)

# For each arithmetic flag: print computed-vs-stated for human adjudication.
# End the run with:  "HARD problems: N"   ;   exit 1 iff N > 0
# Clean run == every HARD finding is on the reviewed-benign allowlist with a one-line reason.
```

### Detailed Steps

1. **Source existence / quote re-binding on a large sample.** Do not spot-check ~15 rows. For a large sample of cited records, confirm the source file exists and the quoted text actually appears in it. A missing source file or an unfindable quote is a HARD finding.
2. **Independent arithmetic re-check.** Re-derive every equation found in derivations and values from its operands; do not trust the stated result. Print `computed vs stated` for each flag so a human can adjudicate — most flags will be artifacts (see Failed Attempts), so never auto-fail on a raw arithmetic flag without showing the numbers.
3. **Cross-tier footing.** Assert the index total equals the sum of section rows equals the sum of item values. Do it twice: once gross, once de-duplicated where holdings/items overlap across sections. A footing break is HARD.
4. **Count self-consistency.** Assert the verdict tally is byte-identical across every place it is reported: the run's own summary file, the generated provenance document, and the delta/summary report. This was the original motivating defect — the prior process reported its tally FOUR different ways. The verifier MUST fail if any two diverge.
5. **Extend PII / vocabulary / format checks across ALL tiers and side-notes,** not only leaf items. Index rows, section headers, and side-notes are where a weak verifier's coverage gap hides.
6. **Classify HARD vs soft, then build the reviewed-benign allowlist.** A hardened verifier produces MANY findings and MOST are limitations of its OWN regex, not data errors — you must separate genuine errors from artifacts or you will chase phantoms. For each cleared HARD finding, do NOT delete it: move it to a "reviewed-benign" bucket with a written one-line justification per entry. Exit nonzero only on un-reviewed HARD findings; descriptive-formatting variants stay soft and non-blocking. A clean run then means "every hard finding is on the reviewed allowlist with a reason" — an auditable sign-off, not a silent deletion.

### Artifact classes observed (and how to neutralize them)

- **Multi-term and waterfall arithmetic.** A naive 2-operand regex flags valid 3+ term sums and "waterfall" calculations (`prev − payment + new = result`). Require a uniform-operator full chain before flagging; treat display-truncated results and a ratio rendered as a product as artifacts, not mismatches.
- **Non-path derivation labels rendered as links.** A doc generator that turns a non-path label (e.g. an "n/a (arithmetic)" annotation) into a markdown link produces broken-link noise. Fix the GENERATOR to emit a link only for a real relative path — do not blame the verifier.
- **Public identifiers that look like account numbers.** Long digit-runs that are public identifiers — registry/CIK numbers, confirmation/order/certificate numbers, identifiers embedded in source filenames — are NOT sensitive account data. Classify them as a separate benign category using surrounding context, not digit length alone.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Surface-only verifier | Trusted a checker that only verified links exist, vocabulary matched a regex, and a ~0.5% line-number spot check | Passed while never touching the substance of the records — false assurance on a large dataset | A final verifier must re-bind sources, re-check arithmetic, foot totals, and assert count self-consistency; surface linting is not verification |
| Naive 2-operand arithmetic regex | Flagged any value that did not equal `a op b` for two operands | ~70 false "mismatches" from valid 3+ term sums and waterfall calcs (`prev − payment + new = result`); also tripped on truncated displays and ratios rendered as products | Require a uniform-operator full chain and add artifact filters for truncation/ratio cases; print computed-vs-stated and only genuine errors remain (here zero) |
| Doc generator linking non-path labels | Generator emitted markdown links for derivation labels including non-paths like "n/a (arithmetic)" | Produced broken-link noise that looked like real failures | Fix the GENERATOR to emit a link only for a real relative path — fix the producer, not the checker |
| Treat every 9+ digit run as PII | Flagged any long digit-run as a sensitive account number | Flagged public registry/confirmation/certificate numbers and identifiers embedded in source filenames | Classify by surrounding context into a benign-docid category; digit length alone does not indicate sensitive data |
| Suppress manually-cleared findings | Deleted findings after a human reviewed them as benign | Lost the audit trail — a later reviewer cannot tell a cleared finding from one that was never raised | Use a reviewed-benign allowlist: keep the finding, attach a one-line justification, and only un-reviewed HARD findings block |

## Results & Parameters

Before/after on a real ~2,900-field dataset:

```text
Raw HARD findings (first hardened run): ~131
Genuine HARD findings after artifact classification + allowlist review: 0

Each residual finding resolved to exactly one of:
  - a verifier-regex limitation (e.g. multi-term / waterfall arithmetic)
  - a public identifier (registry/CIK/confirmation/certificate/filename id)
  - an intentional descriptive format (kept soft, non-blocking)
  - a manually-reviewed allowlisted item (kept, with a one-line justification)
```

HARD vs soft classification used by the verifier:

```text
HARD (exit 1 if any un-reviewed remain):
  - broken link (EXCLUDING pre-existing, documented broken links)
  - genuine arithmetic mismatch (after uniform-operator chain + artifact filters)
  - count inconsistency across the run-summary / provenance-doc / delta-summary
  - true PII (after benign-docid classification)
  - missing source file

soft (non-blocking):
  - descriptive-formatting variants

Run output contract:
  - For each arithmetic flag, print "computed vs stated" for human adjudication.
  - End with a single line:  HARD problems: N
  - exit 1  iff  N > 0
  - A clean exit means every HARD finding is on the reviewed-benign allowlist with a reason.
```

Reviewed-benign allowlist entry shape (one line of justification per entry):

```text
<finding-id> | <category: regex-limit | public-id | descriptive-format | reviewed-benign> | <one-line justification>
```

## Related Skills

This skill builds on `planning-validator-false-assurance-flatten-duplicate-guard` and the `*-verify-*` family of skills, and adds two ideas on top of them: (1) COUNT self-consistency — asserting the verdict tally is identical everywhere it is reported and failing on any divergence; and (2) the REVIEWED-BENIGN ALLOWLIST — clearing a finding by moving it to an auditable bucket with a written justification rather than suppressing it.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| (general) | Final sign-off verifier hardened and run to a clean exit on a real ~2,900-field validated dataset (local only, not CI) | Pattern is domain-agnostic; applies to any large validated dataset with cited sources, derivations, and cross-tier totals. |
