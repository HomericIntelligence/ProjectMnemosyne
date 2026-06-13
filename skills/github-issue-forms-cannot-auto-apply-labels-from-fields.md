---
name: github-issue-forms-cannot-auto-apply-labels-from-fields
description: "Planning-time learning: GitHub issue forms (.github/ISSUE_TEMPLATE/*.yml) CANNOT map a dropdown/input/checkboxes field SELECTION to a label — only the static top-level `labels:` array applies labels, identically for every submission. A 'Severity' dropdown does NOT auto-apply `severity:minor`; the selected value lands only as text in the rendered body. Any field→label linkage needs a downstream `on: issues:[opened]` Action that parses the body, or a human triager. Use when: (1) planning to add triage/planning fields (severity, area, priority) to a GitHub issue form expecting them to drive labels, (2) reviewing a plan that adds a dropdown whose value nothing automatically consumes (YAGNI risk), (3) wiring an issue form into a label-driven Epic/state workflow, (4) hard-coding form options to mirror a point-in-time `gh label list` (drift risk), (5) using `default: <index>` on a dropdown (brittle index-into-options), (6) putting a relative `../../docs/...` link in an issue-form markdown block (resolves against the issue page URL → 404), (7) writing a static test that asserts form options match a hard-coded python list (guards form edits, NOT live label drift)."
category: architecture
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
tags: ["github-issue-forms", "issue-templates", "labels", "planning", "triage", "yagni"]
---

# GitHub Issue Forms Cannot Auto-Apply Labels From Field Selections

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | Plan adding planning/triage fields (e.g. a Severity dropdown) to ProjectHephaestus GitHub issue-form templates so they tie into a label-driven Epic + `state:*` workflow (issue #1210). |
| **Outcome** | Plan written but NOT executed — no code shipped, no CI ran. The single most load-bearing assumption (a form field can feed the label pipeline) is FALSE on the GitHub-issue-forms platform; several supporting assumptions are unverified. |
| **Verification** | unverified — planning learning only; nothing was executed. |

## When to Use

- You are planning to add triage/planning fields (Severity, Area, Priority) to a GitHub issue form (`.github/ISSUE_TEMPLATE/*.yml`) and expect the selected value to apply a label.
- You are reviewing a plan that adds a `dropdown`/`input`/`checkboxes` field but builds no consumer for its value.
- You are wiring an issue form into a label-driven Epic / `state:*` workflow.
- A plan hard-codes form options to mirror a point-in-time `gh label list`.
- A plan uses `default: <N>` on a dropdown, a relative `../../docs/...` link in a form, or a static test asserting form options match a hard-coded list.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — the plan was written but never executed; no CI ran. Every claim below is a planning-time assumption a reviewer/implementer must still validate.

### Quick Reference

```text
HARD PLATFORM FACT (the heart of this skill):
  GitHub issue forms apply labels ONLY from the static top-level `labels:` array.
  That array is IDENTICAL for every submission, regardless of what the filer picks.
  A dropdown/input/checkboxes SELECTION can NEVER set a label by itself.
  The selected value only renders as TEXT in the issue body.

  field --> label  REQUIRES one of:
    (a) an `on: issues: [opened]` GitHub Action that parses the body and calls
        `gh issue edit --add-label`, OR
    (b) a human triager following a runbook.
  If the plan adds a field but builds neither (a) nor (b): that field's value is
  consumed by NOTHING == YAGNI "added a field nobody reads".
```

### Detailed Steps (reviewer / implementer checklist)

1. **Ground the design in REAL labels + automation before writing fields.** Read the
   actual `.github/ISSUE_TEMPLATE/*.yml`, the auto-label workflow, and run
   `gh label list` — do not trust the issue's (possibly stale) citations.
2. **Decide the source of truth = labels + automation, NOT free-text form fields.**
   This aligns with the anti-drift principle in
   `architecture-github-labels-as-state-vocabulary`.
3. **For every field you add, name its CONSUMER.** If the field is meant to drive a
   label, the deliverable MUST include the body-parsing tagger Action OR a triager
   runbook. No consumer → drop the field or descope.
4. **Do not hard-code option lists as a synced contract.** A static test that asserts
   form options equal a hard-coded python list guards against editing the form; it
   does NOT detect the live labels drifting away from the form.
5. **Verify platform features against current GitHub docs** before relying on them:
   `dropdown` `default:` support and index semantics, relative-link rendering in
   `markdown` blocks. These were UNVERIFIED at planning time.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Field → label linkage | Plan adds a Severity `dropdown` expecting it to apply `severity:*` labels | GitHub issue forms apply labels ONLY from the static top-level `labels:` array — identical for every submission; a selection lands only as body TEXT. The plan's own prose hedges ("auto-applies … isn't possible") yet the field's value then rests on a consumer (tagger/triager) the plan never builds | A form field that nothing reads is YAGNI. Require a body-parsing `on: issues:[opened]` Action OR a triager runbook as part of the deliverable, or drop the field |
| Options mirror live labels | Hard-code options `critical/major/minor/nitpick` to mirror a planning-time `gh label list`, asserted by a static test against a hard-coded python list | `gh label list` is a POINT-IN-TIME snapshot; labels can be renamed/removed later, silently desyncing the form. The test only catches FORM edits, not LABEL drift — giving false confidence about form↔label consistency | Don't treat a hard-coded option list as a synced contract. To detect drift you must compare the form against the LIVE label set, not a frozen python list |
| `default: 4` on dropdown | Set `default: 4` to pick the 5th "unsure / let triage decide" option (0-indexed) | `default:` is an INDEX into the options list — reorder the options and the default silently points elsewhere. Also `dropdown` `default:` support / semantics were NOT verified against current GitHub docs (unverified external-API assumption) | Verify `dropdown` supports `default:` and that the index is correct; brittle index-into-options breaks on reorder. Prefer a named/last-resort option or no default |
| Relative form link | Put `../../docs/auto-label-needs-plan.md` in an issue-form `markdown` block | Relative links in a rendered issue form resolve against the ISSUE PAGE URL, not the file tree, so `../../docs/...` will almost certainly 404. Not verified | Use an absolute `https://github.com/<org>/<repo>/blob/<branch>/docs/...` blob URL, or drop the link |
| `required: true` severity | Make the severity dropdown required, combined with `blank_issues_enabled: false` | Now EVERY issue must pick a severity — a UX/friction decision the audit never asked for (the audit only flagged the linkage GAP). The "unsure" escape-hatch mitigates but doesn't justify | Scope creep beyond the issue. Don't add required-field friction the issue didn't request |
| Trust cited line refs | Rely on `docs/ROADMAP.md:43-49` and `parents[3]` path arithmetic from the issue without re-verifying every line | The issue cited bare `ROADMAP.md:43-49` but the file actually lives at `docs/ROADMAP.md` (not repo-root) — citation contradicted reality. The test's `parents[3]` walk-to-repo-root was NOT executed; off-by-one in `parents[]` is a classic untested-test bug | Re-verify cited paths/line numbers on disk; execute path arithmetic before trusting it |

Every row above is an assumption made (or hedged) during planning that a
reviewer/implementer MUST still validate — nothing here was executed.

## Results & Parameters

### Verified label set (captured live via `gh label list` at planning time, 2026-06-12)

```text
severity:critical   severity:major   severity:minor   severity:nitpick
critical            major            minor            (bare, no severity: prefix)
epic                audit-finding
state:*  family     (e.g. state:needs-plan — auto-applied on issues:opened/reopened)
```

NOTE: this is a POINT-IN-TIME snapshot. Treat it as evidence the form *was* grounded
in reality at planning time, NOT as a permanent contract.

### Verified-during-planning files (read, but not every claimed line re-executed)

```text
.github/ISSUE_TEMPLATE/*.yml                  (the templates being edited)
.github/workflows/auto-label-needs-plan.yml   (read — confirms auto state:needs-plan
                                               on opened/reopened)
docs/ROADMAP.md:43-49                          (read — lives at docs/ROADMAP.md, NOT
                                               repo-root as the issue's bare citation
                                               implied)
config.yml                                     (confirmed blank_issues_enabled: false)
gh label list                                  (captured live — see label set above)
tests/unit/github/test_issue_templates.py      (planned; parents[3] path arithmetic
                                               NOT executed — verify the index)
```

### Reviewer checklist (the 5 risks as checkboxes)

- [ ] **Field has a consumer.** Every triage dropdown that's meant to drive a label
  ships with a body-parsing `on: issues:[opened]` tagger Action OR a triager runbook —
  otherwise drop it (YAGNI: a field nothing reads).
- [ ] **Form↔label drift.** The form options are checked against the LIVE label set,
  not only a hard-coded python list (the static test does not catch label renames).
- [ ] **`dropdown` `default:`.** Confirm GitHub `dropdown` supports `default:` and the
  index points at the intended option (brittle to reorder); verify against current docs.
- [ ] **Form markdown links.** No relative `../../docs/...` link in a `markdown` block
  (resolves against the issue page URL → 404); use an absolute blob URL or drop it.
- [ ] **Scope.** `required: true` on severity (with `blank_issues_enabled: false`) is
  not added unless the issue asked for it — the audit only flagged the linkage gap.

### What worked (verified-during-planning)

- Reading the actual template files, the auto-label workflow, and `gh label list`
  BEFORE designing fields — grounded the plan in real labels/automation rather than
  the issue's possibly-stale citations.
- Choosing labels + automation as the source of truth over free-text form fields,
  consistent with `architecture-github-labels-as-state-vocabulary`'s anti-drift
  principle.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Planning session for issue #1210 (add planning/triage fields to GitHub issue-form templates that tie into a label-driven Epic + `state:*` workflow). Plan written, NOT executed. | unverified — planning learning |

## Related Skills

- `architecture-github-labels-as-state-vocabulary` — the canonical `state:*`
  label vocabulary and the anti-drift "labels are the source of truth" principle this
  plan leans on.
- `monorepo-subproject-gitignore-and-github-template-gotchas` — where GitHub reads
  issue/PR templates from (repo-root `.github/`, root, or `docs/`), the wiring layer
  beneath this field-design layer.
