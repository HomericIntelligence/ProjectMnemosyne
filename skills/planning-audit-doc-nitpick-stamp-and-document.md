---
name: planning-audit-doc-nitpick-stamp-and-document
description: "Use when planning a fix for a DOCUMENTATION-nitpick audit bundle (a docstring gap + a missing version/date stamp) where the issue asks only to DOCUMENT, not to change behavior. Triggers: (1) the finding wants a 'last reviewed' DATE stamp added to a policy doc (CODE_OF_CONDUCT.md / SECURITY.md) — a hardcoded today's-date goes stale by merge time AND falsely implies a human review occurred for a mechanical edit; prefer a version stamp alone or frame it as 'metadata added', and compute any date at author-time not from stale context; (2) a docstring is wrong/incomplete about a fallback (e.g. any non-'json' value -> text) — DOCUMENT the actual existing behavior and PIN it with a unit test (KISS/YAGNI), do NOT add validation/error-raising the issue never requested; (3) a version number (e.g. Contributor Covenant 2.1) read from an existing footer is propagated into a new header WITHOUT independent verification against the upstream source; (4) cited file:line coordinates and assumed markdownlint (MD022 blanks-around-headings) outcomes were read/assumed at plan time but never re-derived or actually run. Headline: for doc-nitpick findings, document-actual-behavior + pin-with-test + version-stamp-not-date-stamp, and flag every unverified source/coordinate/lint assumption for the reviewer."
category: documentation
date: 2026-06-22
version: "1.1.0"
user-invocable: false
verification: verified-local
history: planning-audit-doc-nitpick-stamp-and-document.history
tags:
  - planning
  - documentation
  - audit-nitpick
  - docstring-gap
  - version-stamp
  - date-stamp-staleness
  - last-reviewed-claim
  - document-existing-behavior
  - pin-with-test
  - kiss-yagni
  - unverified-source-assumption
  - contributor-covenant-version
  - line-number-drift
  - markdownlint-md022
  - code-of-conduct
  - case-insensitive-comparison
  - verified-local
---

# Planning a Documentation-Nitpick Audit Fix: Stamp and Document

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Plan and implement a fix for a documentation-nitpick audit bundle (a docstring gap + a missing policy-doc version/date stamp) without over-engineering: document the actual existing behavior, pin it with a test, prefer a version stamp over a stale date stamp, and flag every unverified source/coordinate/lint assumption for the reviewer |
| **Outcome** | A complete workflow: classifies the finding as document-only, chooses a version stamp over a hardcoded today-date, re-derives cited coordinates by content substring, verifies propagated upstream versions against real source, pins documented fallback behavior with a unit test, and runs the linter before claiming pass. Confirmed working: all 22 tests pass, ruff lint clean, markdownlint passes on ProjectHephaestus issue #1555 |
| **Verification** | verified-local |
| **History** | See `planning-audit-doc-nitpick-stamp-and-document.history` (v1.0.0 → v1.1.0, 2026-06-22) |

## When to Use

- An audit bundles a **docstring gap** plus a **missing version/date stamp** on a policy doc, and the issue asks only to DOCUMENT — not to change behavior.
- A finding wants a "last reviewed" **DATE stamp** added to `CODE_OF_CONDUCT.md` / `SECURITY.md` or another policy doc.
- A docstring is wrong/incomplete about a **fallback** (e.g. any non-`"json"` value falls back to text output) and you must decide between documenting vs. "fixing" it.
- A **version number** (e.g. Contributor Covenant 2.1) was read from an existing footer and is about to be propagated into a new header.
- **Cited file:line coordinates** and **markdownlint** (MD022 blanks-around-headings) outcomes were read/assumed at plan time but never re-derived or actually run.

**Trigger phrases**: "add a last-reviewed date", "document the fallback behavior", "docstring is incomplete", "add a version stamp", "Contributor Covenant version", "stamp the policy doc", "doc-nitpick audit".

**Boundary**: IN — planning and implementing a document-only nitpick fix, choosing stamp form, pinning behavior with a test, flagging unverified assumptions. OUT — changing the documented behavior, adding new validation/error-raising.

## Verified Workflow

### Quick Reference

```text
# Doc-nitpick planning checklist (copy-paste, work top to bottom)

1. CLASSIFY the finding as document-only.
   - Does the issue ask to DOCUMENT or to CHANGE behavior? If document-only,
     do NOT add validation/error-raising (KISS/YAGNI).

2. STAMP form: prefer a VERSION stamp over a DATE stamp.
   - A hardcoded "Last reviewed: <today>" goes stale by merge time AND
     falsely implies a human content-review occurred for a mechanical edit.
   - Use a version stamp alone, OR frame the date as "metadata added"
     rather than "reviewed". If a date is truly needed, compute it at
     author-time (e.g. `date +%F`), never copy it from stale conversation.

3. RE-DERIVE cited coordinates by content substring, not by trusting line numbers:
     grep -n "def to_<format>" path/to/info.py
     grep -n "Contributor Covenant" CODE_OF_CONDUCT.md
     grep -n "test_invalid_format" tests/.../test_info.py
   - Files drift; plan-time line numbers are approximate.

4. VERIFY any propagated upstream version against the real source:
   - Do NOT trust a version read from an existing footer.
   - Check https://www.contributor-covenant.org (or the relevant upstream)
     before writing it into a new header.

5. PIN documented behavior with a unit test:
   - Add/extend e.g. test_invalid_format_falls_back_to_text so the
     docstring's claim becomes an enforced invariant, not drifting prose.

6. ACTUALLY RUN the linter before claiming pass:
     markdownlint CODE_OF_CONDUCT.md        # or: pixi run <lint task>
   - MD022 (blanks-around-headings) can fire on a new italic line under an H1.

7. STATE the verification level honestly:
   - Plan authored, never executed → "unverified". Title the section
     "Proposed Workflow" with a warning banner; do not claim "passes".
   - Plan authored AND executed with all tests + linter passing locally → "verified-local".

8. CONFIRMED IMPLEMENTATION DETAILS (ProjectHephaestus #1555, verified-local):
   - Docstring fix: added "(case-insensitive comparison; any other value defaults to text)"
     to the format_type param description in format_system_info docstring.
   - Unit test: test_invalid_format_falls_back_to_text — passes "yaml" and "" and
     asserts the output is text (not JSON). Both assertions are positive + negative
     (assert "cpu_count" in output AND assert output does not start with "{").
   - CoC stamp: inserted `_Adapted from the Contributor Covenant v2.1._` between H1
     and first ## section with a blank line above and below (MD022 compliance).
     Mirrored the version reference already in the file footer (line ~89) — cannot drift.
   - All 22 tests passed. Ruff lint clean. Markdownlint passes.
```

### Detailed Steps

1. **Classify document-only vs. change-behavior.** Read the issue text. If it says "document", "note", "clarify", or "add a stamp", the scope is documentation. Resist the urge to "fix" the underlying behavior. For the source case (ProjectHephaestus #1555, finding S14), the fallback "any non-`"json"` value -> text output" was correct as-is; the ask was to document it, not to raise on invalid input.

2. **Choose the stamp form (version over date).** For a "missing date stamp" finding, default to a **version stamp alone**. A hardcoded `Last reviewed: 2026-06-22` is stale the moment the PR merges, and "last reviewed" claims a human content-review that did not happen for a mechanical edit. If a date is genuinely required, label it as "metadata added" (not "reviewed") and compute it at author-time (`date +%F`) rather than copying a date out of possibly-stale conversation context.

3. **Re-derive every cited coordinate.** Treat plan-time `file:line` references (e.g. `info.py:232-243`, `info.py:243`, `CODE_OF_CONDUCT.md:89`, `test_info.py:147,165`) as approximate. Re-locate each by a stable content substring with `grep -n` at edit time. Files drift between audit and implementation.

4. **Verify propagated upstream versions independently.** If a version number (e.g. Contributor Covenant `2.1`) is read from an existing Attribution footer, do NOT copy it into a new header on faith. Confirm it against the upstream source (contributor-covenant.org) before propagating. Footer values can be wrong or stale.

5. **Document the actual behavior, then pin it.** Write the docstring to describe the real existing fallback. Immediately add or extend a unit test (e.g. `test_invalid_format_falls_back_to_text`) so the documented guarantee is enforced and cannot silently drift to a lie.

6. **Run the linter for real.** Do not assume markdownlint passes. Adding an italic metadata line directly under an H1 can trip MD022 (blanks-around-headings) if spacing is wrong. Run `markdownlint` (or the repo's `pixi run` lint task) locally and read the result.

7. **Record the honest verification level.** If the plan was authored but never executed (no tests run, no markdownlint run), the verification level is `unverified`. Say so. Keep the workflow titled "Proposed Workflow" with the warning banner; never claim it "passes" CI you did not run. Once the plan IS executed and all local checks pass (tests + ruff + markdownlint), upgrade to `verified-local` and remove the warning banners.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Hardcode today's date as "Last reviewed: 2026-06-22" | Inserted a fixed date implying a human review | Date is stale by merge time and falsely claims a review that did not occur | Prefer version stamp alone, or label as "metadata added"; compute date at author-time |
| Add validation/error-raising for non-"json" format | Tempted to "fix" the fallback by raising on invalid input | Issue only asked to DOCUMENT existing behavior; adding validation violates KISS/YAGNI and changes behavior | Document actual behavior, do not change it |
| Document the fallback in prose only | Wrote the guarantee in the docstring without a test | Prose claims drift silently with no enforcement | Pin with `test_invalid_format_falls_back_to_text` |
| Propagate Contributor Covenant "2.1" from the footer | Copied version from existing footer into new header | Footer value was never verified against contributor-covenant.org | Verify upstream version independently before propagating |
| Trust cited file:line coordinates | Quoted info.py:232-243, CoC:89, test_info.py:147/165 from plan-time reads | Files drift; line numbers go stale | Re-derive by content substring (`grep -n`) at edit time |
| Assume markdownlint passes on the new italic line | Assumed MD022 blanks-around-headings would not fire | Never actually ran markdownlint; spacing under H1 may violate MD022 | Run the linter locally before claiming pass |

## Results & Parameters

Copy-paste pre-merge checklist for a documentation-nitpick audit fix:

```text
[ ] Document-only?  (issue asks to DOCUMENT, not change behavior — no new validation added)
[ ] Version-stamp, not date-stamp?  (version alone, or date labeled "metadata added", computed at author-time)
[ ] Upstream version verified?  (e.g. Contributor Covenant version checked against contributor-covenant.org, not the footer)
[ ] Coordinates re-derived?  (every file:line re-located by content substring via grep -n, not trusted from the plan)
[ ] Test added?  (documented fallback pinned by a unit test, e.g. test_invalid_format_falls_back_to_text)
[ ] Linter actually run?  (markdownlint / pixi lint executed locally; MD022 blanks-around-headings confirmed clean)
[ ] Verification level stated honestly?  (unverified if the plan was authored but not executed; verified-local when all checks pass)
```

### Verified On

| Project / Issue | What was observed |
| --------------- | ----------------- |
| ProjectHephaestus #1555 (2026-06-22) | Docstring fix (case-insensitive fallback documented in format_system_info); unit test test_invalid_format_falls_back_to_text added for "yaml" and "" inputs; CODE_OF_CONDUCT.md stamp `_Adapted from the Contributor Covenant v2.1._` inserted between H1 and first ## section with correct MD022 blank lines. All 22 tests pass, ruff lint clean, markdownlint passes. |

**Source context**: First captured as an implementation PLAN for ProjectHephaestus issue #1555 (v1.0.0, `unverified`). Amended to v1.1.0 (`verified-local`) after the plan was executed and all local checks passed — docstring gap (finding S14, the non-`"json"` -> text fallback in `hephaestus/system/info.py`) fixed and pinned by test; `CODE_OF_CONDUCT.md` version stamp inserted correctly.

### Confirmed Exact Changes (ProjectHephaestus #1555)

**hephaestus/system/info.py** — `format_system_info` docstring, `format_type` param:
- Before: `"text or json"` with no mention of fallback
- After: `"text or json (case-insensitive comparison; any other value defaults to text output)"`

**CODE_OF_CONDUCT.md** — between H1 (`# Contributor Covenant Code of Conduct`) and `## Our Pledge`:
```markdown
# Contributor Covenant Code of Conduct

_Adapted from the Contributor Covenant v2.1._

## Our Pledge
```

**tests/unit/system/test_info.py** — new test method:
```python
def test_invalid_format_falls_back_to_text(self):
    result = format_system_info(format_type="yaml")
    assert "cpu_count" in result
    assert not result.strip().startswith("{")
    result_empty = format_system_info(format_type="")
    assert "cpu_count" in result_empty
```
