---
name: workflow-github-issues-individual-per-fix-for-automation-loop
description: "When filing GitHub issues that the HomericIntelligence automation loop (`hephaestus-automation-loop`) will fix, file ONE issue per independently-shippable PR — not one combined issue listing several fixes. Use when: (1) filing a multi-bug audit finding, (2) filing a multi-component refactor, (3) the automation loop will pick up these issues, (4) the Closes #N rule (`pr-policy` CI gate enforces exactly-one closing reference) constrains you to one issue per PR."
category: tooling
date: 2026-05-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [github-issues, automation-loop, pr-policy, homericintelligence, issue-scoping, workflow, closes-n, multi-fix, audit-finding]
---

# Workflow: One GitHub Issue Per Fix for the Automation Loop

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-30 |
| **Objective** | Document the decision rule for splitting multi-fix design bugs into individual GitHub issues so the HomericIntelligence automation loop (`hephaestus-automation-loop`) can pick them up one PR at a time |
| **Outcome** | Decision checklist (4 questions) + concrete worked example from session: issue #817 (combined) split into #818, #819, #820, #821; #817 closed as superseded |
| **Verification** | verified-local — confirmed by reading `pr-policy` CI gate documentation in HomericIntelligence/ProjectHephaestus CLAUDE.md AND by user's explicit instruction during the session to split issue #817 (combined) into individual issues; the 4-question decision checklist is a synthesis that has not yet been applied to a second independent case |

## When to Use

- **Filing a multi-bug audit finding** that the automation loop will fix (e.g., output of `/repo-analyze-strict` containing several distinct CRITICAL findings touching different files)
- **Filing a multi-component refactor** where each component is independently shippable (e.g., "refactor pipeline shape" that touches 4 separate phases)
- **The automation loop will pick up these issues** — i.e., you will run `hephaestus-automation-loop` against the repo and expect it to plan + implement + open PRs for the issues unattended
- **The `Closes #N` rule applies** — the target repo's `pr-policy` CI gate requires exactly one `Closes #<n>` line in the PR body and fails if there are zero or two+; so one PR can only close one issue
- **Filing a multi-bug security advisory** where each finding has its own acceptance criteria and verification
- **Filing a multi-fix design RFC** where implementation work will be done by the automation loop

**Don't use when:**

- A single rename/refactor touches several files but is atomically reverted if any one fails — that is ONE issue (the unit of work is atomic, not the file count)
- Fixes are coupled at the test-suite level (the same test must pass for all fixes to be considered correct) — that is ONE issue
- Implementation will be done manually by a human who can compose a single PR carefully — `pr-policy` still applies but a human can split commits within one PR; the loop cannot
- Issue volume is so small (1–2 fixes) that creating a parent + 2 children adds more overhead than it saves

## Verified Workflow

### Quick Reference

```bash
# DECISION CHECKLIST — answer YES/NO for each before filing
# If ANY answer is YES → split into individual issues.

# 1. Will the fixes ship as SEPARATE PRs?
#    The automation loop is one-issue-per-PR. pr-policy CI gate requires exactly
#    one `Closes #N` line in the PR body — combined issue → either multiple PRs
#    all closing the same #N (fails gate) OR one mega-PR that won't split cleanly.

# 2. Do the fixes have a SEQUENCING DEPENDENCY?
#    "fix B depends on fix A landing first" must be expressed as separately
#    trackable issues with explicit "depends on #N" notes — buried sub-tasks
#    inside one issue's body do not give the loop dependency information.

# 3. Are the ACCEPTANCE CRITERIA distinct?
#    Each fix has its own success state, its own tests, its own grep evidence
#    of done-ness → split. A combined issue's checklist obscures partial
#    progress (closed when "mostly" done is ambiguous).

# 4. Would a combined issue create a GO/NOGO planning BOTTLENECK?
#    The loop's planner-reviewer issues one binary verdict per issue. A
#    NOGO on the combined issue blocks every sub-fix; a NOGO on one child
#    only blocks that child.

# If all four are NO → one issue is correct.
# Otherwise → split into N individual issues + (optionally) close the
# combined one as superseded with pointers to the children.
```

### Detailed Steps

1. **Draft the combined description first** — Write the full design bug or audit finding as one document. This gives you the complete picture before you decide how to chop it.

2. **Apply the 4-question decision checklist** (above). Count YES answers. If >= 1 YES → split.

3. **Identify the natural fix boundaries.** A "fix" is the unit that:
   - Touches a cohesive set of files (the loop's implementer can scope the patch)
   - Has its own acceptance criteria expressible as "do X, verify Y, add tests Z"
   - Could be shipped and merged independently of the other fixes (modulo sequencing notes)

4. **File one issue per fix.** Each child issue MUST contain:
   - **Concrete acceptance criteria** (what done looks like)
   - **File + line citations** for the offending code (e.g., `loop_runner.py:918-924`)
   - **List of unit tests to add** (the loop's planner uses these to scope work)
   - **Sequencing note** if dependent ("depends on #N landing first")
   - **Pointer to the source-of-truth** (the combined RFC / audit / parent issue) in a "Related" section

5. **Optionally file (or amend) the combined issue as a tracker.** Two patterns:
   - **Close as superseded**: Close the combined issue with a comment listing the child issue numbers ("Split into #818, #819, #820, #821 so the automation loop can pick them up one at a time. Closing as superseded.")
   - **Keep open as epic tracker**: Edit the body to be a pointer-only document (the title, a 2-line summary, and a checklist of child issue numbers). Note: the loop will NOT decompose this — it is for human PM only.

6. **Trigger the automation loop.** It will pick up each child issue independently, plan it, implement it as one PR closing one issue, and satisfy `pr-policy` automatically.

### The `pr-policy` Constraint (Why This Matters)

From HomericIntelligence/ProjectHephaestus `CLAUDE.md`:

> The PR body MUST contain the literal line `Closes #<issue-number>` (capital `C`, no colon, on its own line). `Fixes`, `Resolves`, `closes`, and `Closes:` are NOT accepted.

The gate is enforced as a required CI check. It is **exactly one** `Closes #N` line per PR. Two `Closes` lines fail the gate. Zero `Closes` lines fail the gate. This is what forces the one-issue-per-PR shape.

The automation loop's `plan` → `implement` → `pr` cadence runs **one issue at a time**:

- One issue → one branch → one PR → one `Closes #N`.

A combined issue forces either:
- N PRs all containing `Closes #<combined-issue-number>` → first one closes it; the rest become orphan PRs against a closed issue (gate fails or the planner refuses to re-implement), OR
- One mega-PR touching all N components → too large for safe auto-merge; reviewer agent NOGOs it; doesn't split cleanly when the loop tries to recover.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Combined issue listing 4 fixes | Filed issue #817 ("drive-green is a post-loop stage, not a final-loop phase — refactor pipeline shape") with 4 distinct fixes in one body: (1) move drive-green out of per-loop phases, (2) discover work via failing PRs not open issues, (3) remove `--issues required=True` gating, (4) default to `@me`-authored PRs | The automation loop is `Closes #N`-per-PR. With four fixes under one issue number the loop has to make four PRs that all `Closes #817`, which trips `pr-policy` (exactly-one), OR it makes one giant PR that doesn't split cleanly into reviewable units | File ONE issue per independently-shippable fix; each child has its own `Closes #N` target so each PR cleanly satisfies the gate |
| Epic issue with sub-task checklist | Open one parent issue with `- [ ] sub-task 1\n- [ ] sub-task 2\n- [ ] sub-task 3` in the body, expecting the loop to decompose it | The automation loop does NOT decompose epic checklists into separate PRs — it sees one issue, plans one solution, implements one PR. Epics are a human-PM convention; the loop's planner reads the issue body as one unit of work | Epics are for human project management only. For loop consumption, every checkbox becomes its own issue OR the work doesn't happen |
| "Will split later" — file combined, intend to refactor before loop runs | File the combined #817, plan to split it into #818-#821 in a follow-up session before the loop is triggered | In practice the loop gets triggered before the split happens (or someone else triggers it). The combined issue sits in the queue and gets picked up; planner produces one mega-plan; implementer either fails or produces a mega-PR. The "will split later" intent dies in the queue | Split BEFORE filing. Once an issue is in the queue, the loop may consume it at any time. There is no "I'll do this manually first" workflow that survives parallel loop dispatch |
| Putting "sequencing notes" inside one combined issue's body | Add a section "Implementation order: do (1) first, then (2) which depends on it, then (3)..." inside one issue body | The loop's planner reads the issue as one work unit. Burying sequencing inside the body does not produce N separately-trackable PRs that can be merged in the dependency order. Cross-PR dependency tracking requires N separately-numbered issues each citing "depends on #N" | Explicit "depends on #N" sequencing notes only work when there ARE N separate issues with N separate numbers |
| Generalizing to "always file lots of small issues" | After being told to split #817, apply "split everything" as a blanket rule and decompose every multi-line bug into 5+ tiny issues | Over-splitting creates noise: 5 issues for a single atomic rename, 3 issues for a single test fix. The loop's planner has overhead per issue (one plan → one review → one implementation → one PR); breaking atomic units inflates that overhead | The skill is about WHEN to split (the 4-question checklist) — NOT "always split". Atomic work stays as one issue |

## Results & Parameters

### The 4-Question Decision Checklist

| # | Question | If YES → split? |
|---|----------|-----------------|
| 1 | Will the fixes ship as separate PRs? | YES → split (one issue per PR, enforced by `pr-policy`) |
| 2 | Do the fixes have a sequencing dependency? | YES → split into separately-trackable issues with explicit "depends on #N" notes |
| 3 | Are the acceptance criteria distinct? | YES → split (each fix has its own success state, its own tests) |
| 4 | Would a combined issue create a GO/NOGO planning bottleneck? | YES → split (one NOGO on combined gates every sub-fix) |

If **all four are NO** → one issue is correct (e.g., a single rename touching three files, atomically reverted if any one fails).

If **>= 1 is YES** → split.

### Concrete Worked Example (this session, 2026-05-30)

**Initial filing (anti-pattern):**

- **#817** — "drive-green is a post-loop stage, not a final-loop phase — refactor pipeline shape" — combined body listing four distinct fixes.

**User correction:** "Lets file individual github issues for these so we can fix them during an automation loop"

**Refiling (correct pattern):**

| Child # | Scope | File:line citations | Tests to add | Sequencing |
|---------|-------|---------------------|--------------|------------|
| #818 | Make `drive-green` a post-loop terminal stage instead of a per-loop phase | `loop_runner.py:918-924` | Unit test: `drive-green` not invoked inside per-loop iteration | Must land first |
| #819 | Discover work via failing PRs (`gh pr list`), not via open issues | `ci_driver.py:984-990` | Unit test: discovery returns failing PRs even when no open issues | Must land first |
| #820 | Remove `--issues required=True` from `drive_prs_green.py` and the `HEPH_LOOP_INDEX` gating | `drive_prs_green.py`, `loop_runner.py` | Unit test: drive-green runs with no `--issues` arg | Depends on #818 and #819 |
| #821 | Default to `@me`-authored PRs; require `--all` flag for other actors' PRs | `drive_prs_green.py` argparse | Unit test: default scope is `@me` author | Depends on #820 |

**#817** then closed with a comment: "Superseded by #818, #819, #820, #821 so the automation loop can pick them up one at a time. Closing."

Each child issue has the same "Related" footer pointing back to the original combined #817 for full context (so the planner can read the original rationale even though it's closed).

### Anti-Pattern: The "Epic" Issue

It is tempting to file an "epic" issue and add a checklist of sub-tasks:

```markdown
## Sub-tasks
- [ ] Fix A
- [ ] Fix B
- [ ] Fix C
- [ ] Fix D
```

**The automation loop does NOT decompose epic checklists into separate PRs.** It sees one issue, plans one solution, implements one PR. Epics are for human project management, not for automated implementation.

If you want the loop to do the work, every checkbox MUST become its own filed issue.

### Distinction from PR-Sizing Convention

This skill is **about ISSUE scoping**, not PR scoping. The two are related but distinct:

| Convention | Rule | Scope |
|------------|------|-------|
| **PR-sizing** | 1 PR ↔ 1 closing issue (exactly one `Closes #N`) | Enforced by `pr-policy` CI gate at PR submission time |
| **Issue-scoping** (THIS skill) | When the automation loop will fix it, 1 issue ↔ 1 PR ↔ 1 independently-shippable fix | Enforced by the consequences: combined issues trip `pr-policy` or produce un-splittable mega-PRs |

PR-sizing is the CI constraint. Issue-scoping is the upstream choice that makes PR-sizing achievable for unattended loop runs.

### Repos Where This Constraint Applies

All HomericIntelligence repos with the `pr-policy` required CI gate, which currently includes:

- ProjectHephaestus
- ProjectOdyssey
- ProjectKeystone
- ProjectScylla
- Mnemosyne
- ProjectHermes
- ProjectArgus
- ProjectProteus
- ProjectMyrmidons
- ProjectAchaeanFleet

Verify by reading the target repo's `CLAUDE.md` for the line:

> The PR body MUST contain the literal line `Closes #<issue-number>`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/ProjectHephaestus | Session 2026-05-30 — drive-green pipeline refactor | Combined issue #817 split into #818, #819, #820, #821 per user direction so `hephaestus-automation-loop` can pick them up one PR at a time; #817 closed as superseded. Constraint confirmed by reading `pr-policy` documentation in `CLAUDE.md` (PR body must contain exactly one `Closes #<n>` line; the gate is a required CI check) |
