---
name: planning-defer-tracking-via-append-only-adr
description: "Prefer an append-only ADR over a closeable GitHub issue as the canonical tracker when documentation marks work 'planned/future' and a reviewer flags it as untracked — because issues get auto-closed and go stale. Use when: (1) a reviewer/audit flags documented 'planned'/'future phase'/'not yet implemented' work as having no tracking issue or ADR; (2) you're tempted to open a GitHub issue to track a deferral but issues get auto-closed and go stale; (3) you need a durable canonical tracker for an architectural-state decision in a repo that already uses append-only ADRs; (4) an existing inline doc reference points at a CLOSED or wrong-scope issue and must be replaced; (5) you're planning a docs-only change to a read-mostly meta-repo and must respect ADR append-only conventions."
category: documentation
date: 2026-06-20
version: "1.1.0"
history: planning-defer-tracking-via-append-only-adr.history
user-invocable: false
verification: verified-local
tags:
  - adr
  - planning
  - deferral-tracking
  - stale-plan
  - append-only
  - architecture-decision-record
  - docs-only
  - closed-issue-trap
  - audit-finding
  - nitpick
  - tracker-selection
---

# Planning: Defer-Tracking via an Append-Only ADR (Not a Closeable Issue)

When documentation marks work as "planned" / "future phase" / "not yet
implemented" and a reviewer flags it as having no tracker, the instinct is to
open a GitHub issue. Don't. In a repo that already treats ADRs as append-only
and canonical, a new ADR is the durable tracker; a GitHub issue is a fragile
artifact that gets auto-closed and goes stale — which is the exact failure the
finding warns against.

> **Honest scope:** This skill is validated by static doc checks (grep/ls) only.
> The plan that produced it was **not yet implemented or merged** when this skill
> was written. Treat the implementation/CI step as unverified-in-CI.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-20 |
| **Objective** | Turn an untracked "planned" architecture-doc state into a durably tracked one when a reviewer flags it (Odysseus issue #209, a NITPICK audit finding under epic #174). |
| **Outcome** | Plan written that creates a new append-only ADR (ADR-009) as the canonical tracker and repoints all three `architecture.md` mentions at it. **NOT yet implemented/merged** at time of writing. |
| **Verification** | verified-local — only static `grep`/`ls`/`awk` verification commands; no CI run, no merge yet. The Odysseus plan was reviewed but **not yet implemented or merged**. |

**v1.1.0 learning (this revision):** A brand-new ADR must be created with Status
`Proposed`, **not** `Accepted` — even when the decision describes an already-true
state. Setting `Accepted` on first commit violates the repo's own ADR README
("Set Status to Proposed until the ADR is merged and accepted") and CLAUDE.md,
and contradicts precedent (the two most recent ADRs were both `Proposed`). A
reviewer treated this as a P7/POLA + requirements-alignment **MAJOR** finding and
NOGO'd. Status is only bumped to `Accepted` **after** merge. This revision also
hardened two verification commands (explicit `awk` line-length assertion instead
of an optional `just lint`; a precise tracker-link count grep instead of a
redundant regex alternation).

## When to Use

- A reviewer or audit flags documented "planned" / "future phase" / "not yet
  implemented" work as having **no tracking issue or ADR**.
- You're tempted to open a GitHub issue to track a deferral, but issues get
  **auto-closed and go stale** — the exact failure mode the finding warns about.
- You need a **durable, canonical tracker** for an architectural-state decision
  in a repo that already uses **append-only ADRs**.
- An existing **inline doc reference points at a CLOSED or wrong-scope issue**
  and must be replaced with a live tracker.
- You're planning a **docs-only change to a read-mostly meta-repo** and must
  respect ADR append-only conventions (new ADR, never edit an accepted one).
- You are **creating a brand-new ADR and must decide its initial `Status`
  field** — even if the decision describes an already-true state, the answer is
  `Proposed` on first commit (see Failed Attempts and the ADR Status rule below).

## Verified Workflow

> Validated by static doc checks (grep/ls) only. The plan was not yet implemented
> or merged when this skill was written — treat the implementation step as
> unverified-in-CI.

### Quick Reference

```bash
# Is the inline tracker reference actually live? (the trap: it may be CLOSED/wrong-scope)
gh issue view <N> --repo <owner>/<repo> --json state,title

# Find every "planned/future phase" mention that needs a tracker
grep -n -iE "planned|future phase|not yet implemented" docs/architecture.md

# Next sequential ADR number
ls docs/adr/

# After edits: confirm no mention still points at the stale closed issue
grep -n "<OldIssueRef>" docs/architecture.md   # expect zero
```

### Detailed Steps

1. **Verify the cited tracker's live state before trusting it.** Run
   `gh issue view <N> --json state,title`. Do not assume an inline reference is
   live just because a prior commit added it — it may be CLOSED or scoped to the
   wrong thing (docs vs implementation). An inline link is documentation, not
   proof of tracking.

2. **Choose ADR over issue when the state is long-lived and the repo treats ADRs
   as append-only/canonical.** A GitHub issue is closeable and goes stale; an
   append-only ADR is the durable home for an architectural-state decision. The
   finding typically accepts *either* an issue or an ADR — pick the one that
   survives.

3. **Write the ADR from `docs/adr/template.md` with the next sequential number.**
   Use `ls docs/adr/` to find the next number.

4. **Set `Status: Proposed` on first commit — NEVER `Accepted`.** A brand-new ADR
   always starts `Proposed`, even when the decision describes a state that is
   *already true*. Marking it `Accepted` on first commit violates the repo's ADR
   README ("Set Status to Proposed until the ADR is merged and accepted") and
   CLAUDE.md, and contradicts house precedent — check the two most recent ADRs
   first (they were both `Proposed`). Status is bumped to `Accepted` only AFTER
   merge (README step 6). Verify with
   `grep '^\*\*Status:\*\* Proposed$' docs/adr/<new-adr>.md` and assert there is
   **no** `Accepted` line yet. Do not rationalize against a documented
   convention — conform to it.

5. **Repoint ALL mentions, not just the one a prior fix touched.** A prior partial
   fix often updates only the prose line that had a link and leaves the
   component-table rows still saying "planned" with no tracker. `grep` every
   occurrence (tables AND prose) and repoint each at the new ADR.

6. **Update the ADR README decision-log/index table** with the new ADR row so the
   index reflects on-disk reality.

7. **Verify with `grep`/`ls`/`awk` per acceptance criterion.** Confirm zero
   remaining references to the stale closed issue, that every "planned" mention
   now points at the ADR, that the ADR `Status` is `Proposed`, and that markdown
   line length is within the 80-char limit via an explicit `awk` assertion (see
   the verification commands below).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Track the deferral with a new GitHub issue | Open an issue to satisfy "no tracking issue" | Issues get auto-closed and go stale — the EXACT failure mode the finding warns about; prior trackers Myrmidons#5 and Odysseus#115 were already CLOSED | Use an append-only ADR for long-lived architectural-state deferrals in repos that have ADRs |
| Trust the existing inline reference at `architecture.md:193` as "already tracked" | A prior commit (d1a3df5/#115) added a `Myrmidons#5` link, looked done | `gh issue view 5` showed state=CLOSED and title was "Document Nomad integration STRATEGY" (docs, not impl) — wrong scope AND closed | Always verify a cited tracker's live state and scope with `gh` before assuming the doc is current |
| Fix only the prose mention that had the link | Repoint just line 193 | The two component-table rows (lines 36, 39) still said "planned" with NO tracker — the finding's gap persisted | `grep` ALL occurrences; a partial prior fix often leaves sibling mentions untracked |
| Amend the `architecture-github-labels-as-state-vocabulary` skill | Same "durable state primitive beats fragile artifact" insight | Different mechanism (labels vs ADR) and different search surface — a searcher for "track a deferred architecture item" wouldn't find it under a labels skill | One skill per independent learning when search keywords diverge |
| Set new ADR Status to `Accepted` on first commit | Argued the deferral "is a current, agreed state" so marked ADR-009 Accepted | Violates docs/adr/README.md step 3 ("Set Status to Proposed until merged and accepted"), CLAUDE.md ("set Status to 'Proposed' until merged"), and precedent (the 2 most recent ADRs were both Proposed); reviewer NOGO'd as P7/POLA + requirements-alignment MAJOR | New ADRs ALWAYS start `Proposed`; bump to `Accepted` only after merge (README step 6). Never rationalize against a documented convention — conform. |
| Hedge the lint check with `just lint 2>/dev/null \|\| echo ...` | Left markdown 80-char reflow effectively unverified | reviewer flagged as minor; the recipe may not exist and the check silently passes | Run an explicit `awk 'length>80'` assertion instead of relying on an optional recipe. |
| Verify with `grep -iE "multi-host\|multi-host clustering\|future phase"` | redundant alternation — `multi-host` subsumes `multi-host clustering` | reviewer flagged minor/imprecise | Grep one phrase common to all edited lines and assert an exact count. |

## Results & Parameters

The heart of this skill is honesty about what was and was not verified. The plan
that produced this skill carries the following uncertain assumptions and
unverified sources — surface these to any reviewer:

- **UNCERTAIN ASSUMPTION:** ADR-009 is the correct next number — assumes no
  concurrent ADR PR claims 009; verified only at plan time via `ls docs/adr/`.
- **RESOLVED (was an assumption in v1.0.0):** A brand-new ADR's Status is
  `Proposed`, **not** `Accepted` — this is no longer a judgment call. The README
  ("Set Status to Proposed until merged and accepted"), CLAUDE.md, and precedent
  (the two most recent ADRs were both `Proposed`) all mandate `Proposed` on first
  commit; a reviewer NOGO'd `Accepted` as a P7/POLA + requirements-alignment
  MAJOR. Bump to `Accepted` only AFTER merge. See the ADR Status rule below.
- **UNVERIFIED EXTERNAL:** the repo's markdown-lint mechanism (markdownlint config
  per commit 2059078) was not run end-to-end. Do NOT hedge the 80-char reflow
  check behind an optional `just lint` recipe (it may not exist and would pass
  silently) — run the explicit `awk 'length>80'` assertion below instead.
- **UNVERIFIED:** exact current line numbers (36, 39, 191–193) are from a
  plan-time `grep` snapshot and may drift before implementation.
- **UNVERIFIED:** that linking `architecture.md` to an ADR (rather than reopening a
  tracking issue) actually satisfies the reviewer's intent in #209 ("No GitHub
  issue or ADR tracks this work" — the finding accepts EITHER, so an ADR should
  suffice, but this is an interpretation).
- **RISK FOR REVIEWER:** the ADR claims specific technical preconditions for
  multi-host work (multi-node cluster beyond `bootstrap_expect=1`, Myrmidons→Nomad
  job-submission path, host-fleet placement) that were inferred from
  `configs/nomad` and ADR-003, not confirmed with the Myrmidons maintainers —
  could be inaccurate.

### ADR Status rule

- **New ADR → `Proposed` on first commit.** Always. Even for a decision that
  describes an already-true state. This is mandated by the repo's ADR README and
  CLAUDE.md, not a stylistic preference.
- **`Proposed` → `Accepted` only post-merge**, per the repo's documented ADR
  process (README step 6).
- **Check the two most recent ADRs for the house convention before choosing.**
  In this repo ADR-007 and ADR-008 were both `Proposed`; conforming to that
  precedent is what the reviewer expected. When a documented convention exists,
  conform — do not rationalize a deviation.

### Acceptance-criterion verification commands

```bash
# 1. Cited tracker is genuinely live (not the trap)
gh issue view 5 --repo HomericIntelligence/Myrmidons --json state,title

# 2. Every deferral mention now points at the ADR, none left "planned" untracked
grep -n -iE "planned|future phase|not yet implemented" docs/architecture.md

# 3. The stale closed-issue reference is fully gone
grep -n "Myrmidons#5" docs/architecture.md   # expect zero

# 4. The new ADR exists and is indexed
ls docs/adr/ && grep -n "ADR-009" docs/adr/README.md

# 5. New ADR Status is Proposed, NOT Accepted (the v1.1.0 lesson)
grep '^\*\*Status:\*\* Proposed$' docs/adr/009-*.md   # expect one match
! grep -q '^\*\*Status:\*\* Accepted$' docs/adr/009-*.md  # assert NO Accepted

# 6. Markdown 80-char reflow — verify, don't hedge behind an optional `just lint`.
#    Exits non-zero if any line exceeds 80 chars; do NOT use `just lint 2>/dev/null`.
awk 'length > 80 {print NR": "$0; n++} END{exit(n>0)}' docs/adr/009-*.md

# 7. Tracker links: grep ONE phrase common to all edited lines and assert the
#    exact count — avoid redundant alternations like
#    `multi-host|multi-host clustering` where one term subsumes the other.
test "$(grep -c 'ADR-009' docs/architecture.md)" -eq 3
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Issue #209 (NITPICK §3, part of audit epic #174) | Plan to add ADR-009 + repoint `architecture.md`; verification via `grep`/`ls`. |
| Odysseus | Issue #209 plan revision (after reviewer NOGO on ADR Status) | v1.1.0: ADR Status must be `Proposed` on first commit, not `Accepted`; hardened the awk line-length and tracker-link-count verification commands. Reviewed, NOT yet implemented/merged. |
