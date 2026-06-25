---
name: audit-orphan-source-sweep-to-find-omissions
description: "Audit a structured dataset built from a larger source corpus for OMISSIONS by sweeping every uncited (orphan) source file and classifying it against an included-item index. Use when: (1) a curated index/schedule/inventory is derived from many underlying source documents and an item could be silently dropped, (2) prior validation only re-checked already-cited sources and so cannot detect a missing item, (3) you need defensible 100% source coverage rather than a sampled spot-check."
category: testing
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [audit, omission-detection, source-coverage, multi-agent, data-validation]
---

# Audit: Orphan Source Sweep to Find Omissions

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Detect items present in a source corpus but never carried into a derived structured dataset (omissions) |
| **Outcome** | Success — swept a ~900-document corpus at 100% coverage; surfaced a material previously-omitted item that three prior single-pass reviews missed |
| **Verification** | verified-local (executed end-to-end locally; not in CI) |
| **Category** | testing |

---

## When to Use

Apply this pattern when:

- A structured dataset (a curated index, schedule, inventory, or summary) is built **from** a larger corpus of source documents, and the dangerous failure mode is **omission** — a real item present in the sources but never carried into the output.
- Existing validation only re-checks sources that are **already cited** by output items. Such validation can *never* find an omission, because an omitted item by definition has no citation to re-check.
- You need defensible, auditable **100% source coverage** rather than a sampled spot-check — omissions hide precisely in the unsampled tail.
- An item may be hiding **in plain sight** inside a partly-cited source (e.g. a periodic statement cited for one identifier also lists a second identifier on the same page that was never broken out into the output).

This generalizes `orphan-config-detection` (which warns when a config file is referenced by nothing) from config files to **any** source-corpus → structured-output audit. There, an orphan is an unreferenced config; here, an orphan is an uncited source document, and the goal is to discover what real-world item it represents that the output failed to capture.

---

## Verified Workflow

### Quick Reference

```text
1. CITED   = set of source files referenced by any output item
2. ALL     = every file in the source corpus
3. ORPHANS = ALL - CITED            # in the observed run ~75% of corpus was uncited
4. INDEX   = compact included-item index from the structured output
              [{id, name, known_identifiers[]}, ...]
5. READ every orphan (100%, never sample); classify each into one bucket:
     DUPLICATE     - byte/content copy of an already-cited source
     SUPPORTING    - older/additional instance of an INCLUDED item
                     (match by institution + identifier)
     CONTRADICTING - value/date/owner conflicts with an INCLUDED item
     UNDISCLOSED   - matches NO included item   <-- THE critical bucket
     UNREADABLE    - format-blocked, cannot classify
     NON_EVIDENCE  - marketing / analysis / projection / blank
6. CONTRADICTING -> reopen the affected output item
   UNDISCLOSED    -> draft a stub for HUMAN review; DO NOT add to totals
7. VERIFY the single most material finding yourself (read the real source)
   before escalating.
```

### 1. Compute the orphan set

Enumerate every file in the source corpus. Subtract the set of files actually **cited** by any output item. The remainder is the **orphan set** — sources that exist but contribute to nothing in the output. In the observed run roughly three quarters of the corpus was uncited, which is exactly the blind spot a citation-only re-check ignores.

### 2. Build a compact included-item index

From the structured output, build an `included-item index`: one row per output item with its `id`, `name`, and all `known identifiers` (account-like identifiers, reference numbers, institution names — whatever distinguishes one item from another). This index is the matcher: it lets a classifier decide whether an orphan "matches nothing." **Pass this index to every classifier agent** so they can detect omissions rather than just describe documents.

### 3. Read 100% of orphans and classify each

Do **not** sample. Read every orphan and assign exactly one bucket per document:

- **DUPLICATE** — a content copy of an already-cited source; no new information.
- **SUPPORTING** — an older or additional instance of an *already-included* item; match by **institution + identifier** against the index.
- **CONTRADICTING** — a value, date, or owner that conflicts with an included item. Highest-urgency non-omission finding.
- **UNDISCLOSED** — matches **no** included item. This is the critical bucket: a candidate omission.
- **UNREADABLE** — format-blocked (corrupt/scanned/encrypted); log it, don't guess.
- **NON_EVIDENCE** — marketing, analysis, forward-looking projection, or blank.

The highest-value discovery mode: an item hiding **in plain sight** inside a partly-cited source. A periodic statement may be cited for identifier X yet also list a second identifier Y on the same page that was never broken out. Matching every identifier found in an orphan against the included-item index surfaces Y as UNDISCLOSED even though the document itself *was* cited for X.

### 4. Drive the sweep with a multi-agent workflow

Batch orphans at **~20 documents per classifier agent**. Each agent returns one classification row per document (`document, bucket, matched_item_id_or_null, rationale`). **Embed the orphan list and the included-item index as `const` literals inside the workflow script** — large args objects do not reliably reach the script, so inline them.

### 5. Run a catch-up pass to reach 100%

Under token pressure some batches return short or incomplete. After the main pass, diff classified documents against the full orphan list and run a **catch-up pass over the unclassified remainder with smaller batches (~8/agent)**. Never declare the sweep done while a silent gap remains; log any drops explicitly.

### 6. Re-bucket obvious false positives

A classifier may tag a planning/projection document as UNDISCLOSED because it names an unfamiliar entity. A quick check re-buckets those to **NON_EVIDENCE**. Forward-looking projections are not evidence of an existing item.

### 7. Escalate correctly — discovery is a recommendation, not an edit

- **CONTRADICTING** → reopen the affected output item for correction.
- **UNDISCLOSED** → draft a stub for **human review**. Do **not** silently add it to any totals. A discovered item is a recommendation, not an auto-edit.
- Before escalating the single most material omission, **verify it yourself** by reading the actual source. Never escalate a high-stakes omission on one agent's word.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust prior framing | Adopted a prior pass's "uncited duplicates aren't an error, skip them" rule | That exact framing is what hides omissions — an uncited source is the only place an omission can live | READ every uncited source; never skip the orphan set |
| Sample the orphans | Classified only a fraction of orphan documents to save effort | Omissions hide in the unsampled tail; the material finding was outside any reasonable sample | Read 100% of orphans, not a sample |
| Large args to script | Passed the orphan list and index as a big args object to the workflow script | Large args objects did not reliably reach the script; batches ran against empty/partial input | Embed the orphan list and included-item index as `const` literals in the script |
| Single full-size pass | Ran one pass at ~20 docs/agent and called it done | Some batches returned truncated/empty under token limits, leaving a silent coverage gap | Add a smaller-batch (~8) catch-up pass over the remainder; log drops, never silently truncate |
| Auto-trust classifier | Took an agent's UNDISCLOSED flag on a projection doc at face value | The doc was a forward-looking projection naming an unfamiliar entity, not a real item | Re-bucket projections to NON_EVIDENCE; verify the top finding against the real source before escalating |

---

## Results & Parameters

| Metric | Value |
|--------|-------|
| Source corpus size | ~900 documents |
| Orphan fraction (uncited) | ~75% of the corpus |
| Coverage achieved | 100% of orphans read and classified |
| Main batch size | ~20 documents / classifier agent |
| Catch-up batch size | ~8 documents / classifier agent |
| Classification buckets | DUPLICATE, SUPPORTING, CONTRADICTING, UNDISCLOSED, UNREADABLE, NON_EVIDENCE |
| Key finding | A material previously-omitted item, hiding in plain sight inside a partly-cited statement, that three prior single-pass reviews missed |
| Escalation policy | CONTRADICTING reopens the item; UNDISCLOSED drafts a stub for human review (never auto-added to totals); top finding verified against the real source first |

---

## References

- `orphan-config-detection` — the same orphan idea applied to config files (warn when a config is referenced by nothing); this skill generalizes it to any source-corpus → structured-output omission audit.
