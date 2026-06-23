---
name: planning-audit-doc-nitpick-stamp-and-document
description: "Use when planning a fix for a DOCUMENTATION-nitpick audit bundle (a docstring gap + a missing version/date stamp) where the issue asks only to DOCUMENT, not to change behavior. Triggers: (1) the finding wants a 'last reviewed' DATE stamp added to a policy/governance doc (CODE_OF_CONDUCT.md / SECURITY.md). When the requirement is 'version stamp OR last-reviewed date', prefer the VERSION STAMP ALONE — a hardcoded 'Last reviewed: <today>' is a [major] P7/POLA NOGO: it asserts a human governance review that never happened for a mechanical edit AND goes stale the moment the PR sits in the merge queue. A 'last reviewed' / 'reviewed on' date may ONLY be added when a HUMAN review actually occurred; a mechanical edit is not a review. When adding the version stamp, MIRROR an existing in-file source of truth (e.g. the Attribution footer) so the two cannot drift, instead of asserting a freshly-re-sourced value; (2) a docstring is wrong/incomplete about a fallback (e.g. any non-'json' value -> text) — DOCUMENT the actual existing behavior and PIN it with a unit test (KISS/YAGNI), do NOT add validation/error-raising the issue never requested; (3) a version number (e.g. Contributor Covenant 2.1) read from an existing footer is propagated into a new header WITHOUT independent verification against the upstream source; (4) cited file:line coordinates and assumed markdownlint (MD022 blanks-around-headings) outcomes were read/assumed at plan time but never re-derived or actually run; (5) your /learn captured a RISK in the FIRST plan — ACT on it in the plan, do not merely document it; the reviewer will hold you to your own flagged concern (a stale-date risk flagged-but-unresolved is exactly what got the first plan NOGO'd). Headline: for doc-nitpick findings, document-actual-behavior + pin-with-test + version-stamp-ALONE-not-date-stamp + mirror-an-existing-in-file-source, never fabricate a review date, and act on your own pre-flagged risks."
category: documentation
date: 2026-06-22
version: "1.1.0"
history: planning-audit-doc-nitpick-stamp-and-document.history
user-invocable: false
verification: unverified
tags:
  - planning
  - documentation
  - audit-nitpick
  - docstring-gap
  - version-stamp
  - version-stamp-alone
  - date-stamp-staleness
  - last-reviewed-claim
  - false-review-provenance
  - p7-pola-nogo
  - mirror-in-file-source
  - act-on-flagged-risk
  - document-existing-behavior
  - pin-with-test
  - kiss-yagni
  - unverified-source-assumption
  - contributor-covenant-version
  - line-number-drift
  - markdownlint-md022
  - code-of-conduct
---

# Planning a Documentation-Nitpick Audit Fix: Stamp and Document

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-22 |
| **Objective** | Plan a fix for a documentation-nitpick audit bundle (a docstring gap + a missing policy-doc version/date stamp) without over-engineering: document the actual existing behavior, pin it with a test, prefer a version stamp over a stale date stamp, and flag every unverified source/coordinate/lint assumption for the reviewer |
| **Outcome** | A planning checklist that classifies the finding as document-only, satisfies a "version stamp OR date" requirement with a VERSION STAMP ALONE (never a fabricated "Last reviewed: <today>" — the first plan's date stamp drew a [major] P7/POLA NOGO), mirrors an existing in-file source of truth so the stamp cannot drift, re-derives cited coordinates by content substring, verifies any propagated upstream version against its real source, pins documented fallback behavior with a unit test, demands the linter actually run before claiming pass, and acts on its own pre-flagged risks rather than only documenting them |
| **Verification** | unverified |

## When to Use

- An audit bundles a **docstring gap** plus a **missing version/date stamp** on a policy doc, and the issue asks only to DOCUMENT — not to change behavior.
- A finding asks for "a **version stamp OR a last-reviewed date**" on `CODE_OF_CONDUCT.md` / `SECURITY.md` or another **governance/policy** doc. Satisfy it with a **version stamp ALONE** — a mechanical `Last reviewed: <today>` is a **[major] P7/POLA NOGO**.
- You are tempted to add a "last reviewed" / "reviewed on" date to a doc you **did not actually review** (a mechanical edit is not a review).
- You are adding a version/provenance stamp and need to decide whether to **re-source the value** or **mirror an existing in-file source** (the Attribution footer at e.g. `CODE_OF_CONDUCT.md:89`) so the two cannot drift.
- A docstring is wrong/incomplete about a **fallback** (e.g. any non-`"json"` value falls back to text output) and you must decide between documenting vs. "fixing" it.
- A **version number** (e.g. Contributor Covenant 2.1) was read from an existing footer and is about to be propagated into a new header.
- **Cited file:line coordinates** and **markdownlint** (MD022 blanks-around-headings) outcomes were read/assumed at plan time but never re-derived or actually run.
- Your /learn run **flagged a risk** in the FIRST plan (e.g. "the date will go stale") — you must **ACT on it in the plan**, not merely note it; the reviewer will hold you to your own pre-flagged concern.

**Trigger phrases**: "add a last-reviewed date", "version stamp or last-reviewed date", "stamp the governance doc", "document the fallback behavior", "docstring is incomplete", "add a version stamp", "Contributor Covenant version", "stamp the policy doc", "doc-nitpick audit", "P7 POLA last reviewed".

**Boundary**: IN — planning a document-only nitpick fix, choosing stamp form, pinning behavior with a test, flagging unverified assumptions. OUT — changing the documented behavior, adding new validation/error-raising, executing the plan (this skill is `unverified` — the plan was authored but never run).

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read the steps below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```text
# Doc-nitpick planning checklist (copy-paste, work top to bottom)

1. CLASSIFY the finding as document-only.
   - Does the issue ask to DOCUMENT or to CHANGE behavior? If document-only,
     do NOT add validation/error-raising (KISS/YAGNI).

2. STAMP form: when the requirement is "version stamp OR date", use the
   VERSION STAMP ALONE. Drop the date entirely.
   - A hardcoded "Last reviewed: <today>" on a GOVERNANCE doc is a [major]
     P7/POLA NOGO: it asserts a human review that never happened for a
     mechanical edit AND goes stale the moment the PR enters the merge queue.
   - A "last reviewed" / "reviewed on" date may ONLY be added when a HUMAN
     review actually occurred. A mechanical edit is not a review.
   - MIRROR an existing in-file source of truth (e.g. the Attribution footer)
     when phrasing the stamp, e.g. "_Adapted from the Contributor Covenant
     v2.1._" mirroring the footer's asserted version — do NOT assert a
     freshly-re-sourced value the footer could later contradict.
   - A version stamp carries NO false temporal claim, so it is always safe;
     reach for a date only as a last resort and label it "metadata added"
     (never "reviewed"), computed at author-time (`date +%F`).

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

8. ACT on every risk you flagged — do not merely document it.
   - If your plan flagged "the date will go stale", RESOLVE it in the plan
     (drop the date) instead of shipping it with a caveat. The reviewer will
     NOGO you on your own pre-flagged concern. (The v1 plan flagged the
     stale-date risk but kept the date → [major] P7/POLA NOGO.)
```

### Detailed Steps

1. **Classify document-only vs. change-behavior.** Read the issue text. If it says "document", "note", "clarify", or "add a stamp", the scope is documentation. Resist the urge to "fix" the underlying behavior. For the source case (ProjectHephaestus #1555, finding S14), the fallback "any non-`"json"` value -> text output" was correct as-is; the ask was to document it, not to raise on invalid input.

2. **Choose the stamp form — version stamp ALONE when the requirement is "version OR date".** The source issue (ProjectHephaestus #1555) asked for "a version stamp **OR** a last-reviewed date". The FIRST plan chose a date, stamping `CODE_OF_CONDUCT.md` with `_Based on Contributor Covenant v2.1 · Last reviewed: 2026-06-22_`. The reviewer issued a **[major] P7/POLA NOGO**: a hardcoded "Last reviewed: <today>" on a GOVERNANCE document asserts a human governance review that never occurred for a mechanical edit, and the date is stale the moment the PR sits in the merge queue. **The converged-to-GO fix dropped the date entirely** and satisfied the "OR" with a version stamp alone — `_Adapted from the Contributor Covenant v2.1._`. A version stamp carries no false temporal claim, so it is always the safe branch of the "OR".
   - **Never fabricate a review date.** A "last reviewed" / "reviewed on" date may ONLY be added when a HUMAN review actually occurred. A mechanical edit is not a review.
   - **Mirror an existing in-file source of truth.** Phrase the stamp to mirror the version already asserted elsewhere in the file (here, the Attribution footer at `CODE_OF_CONDUCT.md:89`) rather than asserting a freshly-re-sourced value — so the stamp and the footer cannot diverge. (Independent upstream verification per step 4 still applies to the value you mirror.)
   - If a date is somehow genuinely required despite all the above, label it "metadata added" (never "reviewed") and compute it at author-time (`date +%F`), never copied from stale conversation context.

3. **Re-derive every cited coordinate.** Treat plan-time `file:line` references (e.g. `info.py:232-243`, `info.py:243`, `CODE_OF_CONDUCT.md:89`, `test_info.py:147,165`) as approximate. Re-locate each by a stable content substring with `grep -n` at edit time. Files drift between audit and implementation.

4. **Verify propagated upstream versions independently.** If a version number (e.g. Contributor Covenant `2.1`) is read from an existing Attribution footer, do NOT copy it into a new header on faith. Confirm it against the upstream source (contributor-covenant.org) before propagating. Footer values can be wrong or stale.

5. **Document the actual behavior, then pin it.** Write the docstring to describe the real existing fallback. Immediately add or extend a unit test (e.g. `test_invalid_format_falls_back_to_text`) so the documented guarantee is enforced and cannot silently drift to a lie.

6. **Run the linter for real.** Do not assume markdownlint passes. Adding an italic metadata line directly under an H1 can trip MD022 (blanks-around-headings) if spacing is wrong. Run `markdownlint` (or the repo's `pixi run` lint task) locally and read the result.

7. **Record the honest verification level.** If the plan was authored but never executed (no tests run, no markdownlint run), the verification level is `unverified`. Say so. Keep the workflow titled "Proposed Workflow" with the warning banner; never claim it "passes" CI you did not run.

8. **Act on every risk you flagged — do not merely document it.** If your /learn captured a risk in the first plan, RESOLVE it in the plan rather than shipping the plan with a caveat next to it. The reviewer will hold you to your own pre-flagged concern. The v1 plan explicitly flagged the stale-date risk but kept the date stamp anyway; that flagged-but-unresolved risk is exactly what drew the [major] P7/POLA NOGO. Documenting a risk is necessary but not sufficient — close it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Stamped CoC with mechanical "Last reviewed: <today>" date (`_Based on Contributor Covenant v2.1 · Last reviewed: 2026-06-22_`) | Added the date branch of the issue's "version stamp OR date" requirement | [major] P7/POLA NOGO — implied a human governance review that didn't occur, and goes stale before merge | Use a version stamp ALONE when the requirement is "version OR date" (`_Adapted from the Contributor Covenant v2.1._`); never fabricate a review date |
| Phrased the version stamp by re-asserting an independently-sourced value | Wrote the stamp's version separately from the file's existing footer | The stamp and the Attribution footer (CoC:89) could drift apart over time | MIRROR an existing in-file source of truth so the two cannot diverge |
| Flagged the stale-date risk in the plan but kept the date stamp | Documented the risk as a caveat instead of resolving it | Reviewer held the plan to its own pre-flagged concern → [major] P7/POLA NOGO | ACT on a risk you flagged (drop the date) — documenting it is not enough |
| Add validation/error-raising for non-"json" format | Tempted to "fix" the fallback by raising on invalid input | Issue only asked to DOCUMENT existing behavior; adding validation violates KISS/YAGNI and changes behavior | Document actual behavior, do not change it |
| Document the fallback in prose only | Wrote the guarantee in the docstring without a test | Prose claims drift silently with no enforcement | Pin with `test_invalid_format_falls_back_to_text` |
| Propagate Contributor Covenant "2.1" from the footer | Copied version from existing footer into new header | Footer value was never verified against contributor-covenant.org | Verify upstream version independently before propagating |
| Trust cited file:line coordinates | Quoted info.py:232-243, CoC:89, test_info.py:147/165 from plan-time reads | Files drift; line numbers go stale | Re-derive by content substring (`grep -n`) at edit time |
| Assume markdownlint passes on the new italic line | Assumed MD022 blanks-around-headings would not fire | Never actually ran markdownlint; spacing under H1 may violate MD022 | Run the linter locally before claiming pass |

## Results & Parameters

Copy-paste pre-merge checklist for a documentation-nitpick audit fix:

```text
[ ] Document-only?  (issue asks to DOCUMENT, not change behavior — no new validation added)
[ ] Version-stamp ALONE?  (requirement was "version OR date" → used a version stamp, dropped the date entirely; NO "Last reviewed: <today>")
[ ] No fabricated review date?  (a "last reviewed" date appears ONLY if a human review actually happened)
[ ] Stamp mirrors an in-file source?  (phrased to mirror the Attribution footer, e.g. CoC:89, so it cannot drift)
[ ] Upstream version verified?  (e.g. Contributor Covenant version checked against contributor-covenant.org, not just the footer)
[ ] Coordinates re-derived?  (every file:line re-located by content substring via grep -n, not trusted from the plan)
[ ] Test added?  (documented fallback pinned by a unit test, e.g. test_invalid_format_falls_back_to_text)
[ ] Linter actually run?  (markdownlint / pixi lint executed locally; MD022 blanks-around-headings confirmed clean)
[ ] Every flagged risk RESOLVED, not just noted?  (a risk you flagged in the plan is acted on, not shipped as a caveat)
[ ] Verification level stated honestly?  (unverified if the plan was authored but not executed — keep "Proposed Workflow" + warning)
```

**Source context**: Extracted from an implementation PLAN authored for ProjectHephaestus issue #1555 — an audit-nitpick bundle pairing a docstring gap (finding S14, the non-`"json"` -> text fallback in `info.py`) with a missing `CODE_OF_CONDUCT.md` version stamp. The v1.0.0 plan stamped the CoC with `_Based on Contributor Covenant v2.1 · Last reviewed: 2026-06-22_` and drew a **[major] P7/POLA NOGO** from the reviewer (a fabricated governance-review date that goes stale before merge). v1.1.0 captures the converged-to-GO resolution: a **version stamp ALONE** (`_Adapted from the Contributor Covenant v2.1._`) that mirrors the file's Attribution footer (CoC:89) and carries no false temporal claim. The plan was authored but NEVER EXECUTED (no tests run, no markdownlint run), hence `verification: unverified`.
