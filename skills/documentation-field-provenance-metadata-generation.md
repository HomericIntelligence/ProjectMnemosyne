---
name: documentation-field-provenance-metadata-generation
description: "Generate a per-field provenance/metadata document for a large document package where every field must be traceable to source documents. Use when: (1) a document set must be auditable field-by-field against source PDFs (legal disclosures, compliance filings, data rooms); (2) the deliverable is a metadata document listing each field, how it was produced, the source document/page, and the exact line where the field lives; (3) multi-agent validation passes produce findings that must be assembled deterministically into one provenance document. Covers JSON row schema for validator agents, fix-then-re-read line-number ordering, deterministic Python assembly, idempotent changelog append, line-reference re-anchoring by token search, and a scripted verification sweep including a PII digit-run scan of audit comments."
category: documentation
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [provenance, source-binding, metadata, line-references, evidence-quotes, validation, pii-sweep]
---
# Skill: Field-Provenance Metadata Document Generation

## Overview

| Property | Value |
| ---------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Produce a per-field provenance document for a 185-item / ~2,900-field legal disclosure package where every field must be traceable to a source document, page, and exact line |
| **Outcome** | Success — 2,904 field rows assembled deterministically; 222 fixes documented with old→new + source + page + reason; spot-checks 25/25 and 30/30 clean after re-anchoring |
| **Method** | Validator agents emit one JSON per item under a strict row schema; fixes applied before line capture; a Python script (not an agent) assembles the metadata document; scripted verification sweep including PII digit-run scan |

## When to Use

Use this skill when:

1. A document set must be **auditable field-by-field against source PDFs** — legal disclosures, compliance filings, data rooms.
2. The deliverable is a **metadata document** listing each field, how it was produced, the source document/page, and the exact line where the field lives.
3. **Multi-agent validation passes** produce per-item findings whose results must be assembled deterministically into a single provenance document.

Not for: citation auditing of academic papers (see the academic citation-audit skills), or doc-drift audits without per-field source binding.

## Verified Workflow

### 1. Schema first

Define the JSON output contract before launching any validator agent. Each agent writes **one JSON file per item** containing rows of:

```json
{
  "field": "...",
  "value": "...",
  "verdict": "OK | OK_SINGLE | FIXED | FLAG | NOT_BOUND",
  "derivation": "short rule, e.g. 'most recent statement closing balance'",
  "md_line": 123,
  "source_pdf": "...",
  "page": 4,
  "quote": "verbatim, <= 15 words",
  "old_value": "only when FIXED",
  "reason": "only when FIXED or FLAG"
}
```

plus a top-level `flags[]` array and a `tier2_row` object for downstream sync.

**Verdict semantics** (controlled vocabulary — enforce by regex later):

- `OK` = at least 2 independent sources, or 1 source + exact arithmetic confirmation
- `OK_SINGLE` = correct but single-sourced
- `FIXED` = value corrected; must carry `old_value`, source, page, reason
- `FLAG` = needs human review
- `NOT_BOUND` = schema-controlled field, not source-derivable

### 2. Critical ordering: fix first, then capture line numbers

Agents must apply **all fixes first**, then **re-read the file** to capture final line numbers. An `md_line` recorded before edits is wrong — every insertion/deletion above it shifts it.

### 3. Deterministic assembly by script, not agent

A Python script reads all JSON fragments and renders the metadata document: derivation-rule table; per-item field tables; verdict summary; fix table; flags; document-integrity stats. Per-item field table header:

```markdown
| Field | Value | Verdict | Derivation | Md line | Source | Page | Evidence quote |
```

Make the changelog append **idempotent** — strip any previously-appended section for the same pass before appending:

```python
marker = f"## Provenance pass: {pass_id}"
if marker in changelog:
    head = changelog[: changelog.index(marker)]
    # cut back to the preceding horizontal rule so re-runs don't stack separators
    cut = head.rstrip().rfind("\n---")
    changelog = head[:cut].rstrip() + "\n" if cut != -1 else head
changelog = changelog.rstrip() + "\n\n---\n\n" + marker + "\n\n" + new_section
```

### 4. Line refs go stale — re-anchor by token search

The moment files are edited again, every `md_line` is suspect. Re-anchor each row by token search:

```python
def reanchor(lines, row):
    value_prefix = str(row["value"])[:20]
    for i, line in enumerate(lines, 1):
        if value_prefix and value_prefix in line:
            return i
    field_tokens = [t for t in row["field"].split() if len(t) > 3]
    for i, line in enumerate(lines, 1):
        if field_tokens and all(t.lower() in line.lower() for t in field_tokens):
            return i
    return None  # flag for manual inspection — do not guess
```

Always put a header caveat in the generated document: `md-line references valid as of <generation date>`.

### 5. Verification sweep (script, not agent)

- **Relative-link resolution audit** — resolve every cited path against the **package root**, not just the documents tree.
- **Controlled-vocabulary regexes** — verdicts, derivation phrasing.
- **Money-field as-of-date regex** — report format variance separately from errors.
- **PII digit-run regexes** — scan field values **and HTML/audit comments** for account/policy/loan number runs.
- **Random spot-check** that each sampled `md_line` actually contains its field or value (sample 25-30 rows; expect 0 mismatches).

### Quick Reference

1. Freeze the JSON row schema; one JSON per item per validator agent.
2. Agents: apply all fixes → re-read file → record final `md_line`.
3. Python script assembles the metadata doc deterministically from JSON fragments.
4. Changelog append is idempotent (strip same-pass section back to preceding `---`).
5. After any later edit: re-anchor `md_line` by value/field token search; stamp validity date.
6. Scripted sweep: link resolution from package root, vocab regexes, PII digit-run scan including comments, 25-30 row spot-check.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Trusting validator agents on PII | Agents redacted PII in field values but quoted FULL account/policy/loan numbers inside their own `<!-- corrected ... -->` audit comments | 11 files leaked full identifiers via comments invisible in rendered markdown | PII sweep must scan comments too; redact in-place WITHOUT adding lines so line refs stay valid |
| Strict as-of-date regex `\(\d{4}-\d{2}` as an error gate | Treated every money field not matching the canonical `(YYYY-MM-DD)` pattern as an error | 57 hits were benign variants ("(Mar 2026)", "as of 2026-05-30", "$0 — closed") | Report format variance separately from errors; don't auto-edit |
| Checking cited-doc existence only under the documents tree | Resolved every citation against the source-documents directory | Agents legitimately cited markdown files and sibling items as sources; all flagged "missing" | Resolve citations against the package root; only out-of-package paths are real errors |
| Naive token spot-check of line refs | Checked that the field label string appears verbatim on the recorded line | One false positive: row label paraphrased the line ("2025 Sch B subtotal" vs "**Schedule B subtotal**") | Match on value tokens OR field-name tokens; treat residual single mismatches as check-noise to inspect manually before "fixing" |

## Results & Parameters

**Verified On**

| Context | Date |
| --- | --- |
| FL-142/FL-150 disclosure working papers, June 2026 (private repo — no case identifiers in this skill) | 2026-06-12 |

**Scale and outcomes**

- 185 items, 2,904 field rows assembled into one provenance document.
- 222 fixes, each documented with old→new value, source document, page, and reason.
- Spot-checks: 25/25 and 30/30 sampled `md_line` references clean after re-anchoring.
- PII sweep caught 11 files leaking full identifiers inside audit comments; redacted in-place without changing line counts.

**JSON row schema (verbatim)**

```json
{
  "field": "...",
  "value": "...",
  "verdict": "OK | OK_SINGLE | FIXED | FLAG | NOT_BOUND",
  "derivation": "...",
  "md_line": 0,
  "source_pdf": "...",
  "page": 0,
  "quote": "...",
  "old_value": "...",
  "reason": "..."
}
```

Plus per-item `flags[]` and `tier2_row`.

**Metadata-doc column header (verbatim)**

```text
| Field | Value | Verdict | Derivation | Md line | Source | Page | Evidence quote |
```

**Idempotent changelog-append snippet** — see step 3 of the Verified Workflow.

**Re-anchoring loop sketch** — see step 4 of the Verified Workflow.

**Key parameters**

- Evidence quote limit: <= 15 words, verbatim.
- Spot-check sample size: 25-30 rows, expected mismatches: 0.
- Verdict vocabulary: `OK`, `OK_SINGLE`, `FIXED`, `FLAG`, `NOT_BOUND` (regex-enforced).
- Assembly and verification are scripts; only per-item validation is agent work.
