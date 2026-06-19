---
name: planning-epic-verify-live-child-state
description: "Before planning an epic/tracking/umbrella issue, query the LIVE state of every child issue with gh (state, stateReason, merged PRs, labels) instead of trusting the epic body's status table — the body is a snapshot and drifts. Most children may already be CLOSED+COMPLETED via merged PRs, reframing the epic from 'plan N fixes' to 'dispatch the few remaining state:plan-go children + close-out'. Use when: (1) planning an epic/tracking/umbrella issue, (2) re-planning after a NOGO on a tracking issue, (3) any issue whose body is a checklist of child issues, (4) deciding implementation order across linked issues."
category: tooling
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [epic, tracking-issue, child-issues, planning, gh-cli, state-plan-go, dependency-ordering, orchestration, audit-remediation, stale-body]
---

# Planning: Re-Verify Live Child-Issue State Before Planning an Epic

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Produce a correct implementation plan for an epic/tracking issue whose body lists many child issues — without re-planning children that have already shipped |
| **Outcome** | Successful — the epic body listed all 12 numbered children as "Open" (written 2026-03-28), but a live `gh` sweep showed 9 were already CLOSED+COMPLETED via merged PRs; the plan correctly scoped to ONLY the 3 remaining `state:plan-go` children in re-validated dependency order |
| **Verification** | verified-local — the read-only `gh`/`wc` state sweep was executed and returned the cited results; the downstream child PRs are not yet merged, so end-to-end epic closure is not CI-confirmed |
| **Source** | ProjectOdyssey epic #5191 (strict-mode audit, 13/12 child findings) planning session |

The epic body is a **snapshot** that drifts as children move. The deliverable for an epic is
**orchestration + close-out criteria**, not code — "Files to Create/Modify: None in this epic;
changes live in the children's own approved plans."

## When to Use

- Planning an epic / tracking / umbrella issue (body is a checklist of linked child issues)
- Re-planning after a plan-reviewer NOGO (`state:plan-no-go`) on a tracking issue
- Any issue whose body is a markdown table or checklist of child issues with a "status" column
- Deciding implementation order across linked/dependent issues
- An audit/remediation epic that tracks many findings filed weeks/months ago

## Verified Workflow

### Quick Reference

```bash
# 1. Per-child LIVE state sweep — do NOT trust the epic body's status table.
for n in <child ids>; do
  gh issue view "$n" --json number,state,stateReason \
    --jq '"\(.number) \(.state) \(.stateReason)"'
done
# CLOSED + COMPLETED = done; CLOSED + "not planned" = abandoned, NOT done.

# 2. Confirm each CLOSED child landed via a real merged PR (done vs abandoned).
gh pr list --search "<n> in:body" --state merged --json number,title

# 3. For still-OPEN children, read labels: state:plan-go = reviewer-approved, ready to
#    implement (no PR yet); state:plan-no-go = needs re-planning.
gh issue view "<n>" --json labels --jq '.labels[].name'

# 4. Ground every "approx" number in a FRESH measurement (audit numbers go stale).
wc -l path/to/file_the_audit_counted.mojo   # cite the fresh count, not the audit's
```

### Detailed Steps

1. **Sweep live child state — never trust the epic body's table.** The body is a snapshot
   from when it was written and drifts as children close. Run the per-child loop above. In the
   #5191 session, the body listed all children "Open" but 9 of 12 were already
   CLOSED+COMPLETED.

2. **Distinguish "done" from "abandoned" via `stateReason` + a merged PR.** `state == CLOSED`
   alone is ambiguous: a closed-as-`not planned` issue is NOT complete. Require
   `stateReason == COMPLETED` AND a real merged PR (`gh pr list --search "<n> in:body" --state
   merged`). Only then count the child as shipped.

3. **Read labels on still-OPEN children to reframe the epic.** Children carrying `state:plan-go`
   already have reviewer-approved per-issue plans (just no PR yet). This flips the epic's job
   from "plan N fixes" to "dispatch the M approved children + close-out". In #5191 the 3 open
   children (#5181, #5182, #5184) all held `state:plan-go`.

4. **Re-validate the dependency graph against CURRENT reality, not the audit's original graph.**
   Stale edges produce wrong ordering: in #5191 a downstream child (#5185) was already CLOSED so
   that branch terminated, and a dependency (#5183 graceful shutdown) was already MERGED, which
   UNBLOCKED its dependent (#5184 checkpoint), making it parallelizable.

5. **Re-measure every "approx" the audit cited.** Audit numbers drift: #5191 said
   `any_tensor.mojo` was 4,241 lines; `wc -l` showed it had GROWN to 4,373. Cite the fresh number.

6. **Shape the epic plan as orchestration, not code.** Objective = "drive remaining approved
   children to merged PRs + close-out". Files to Create/Modify = "None in this epic; changes live
   in the children's own approved plans." Implementation Order = dispatch each open child via the
   repo's `impl <n>` skill in dependency order, gate each dependent child behind its prerequisite's
   merge; final step = re-verify all children CLOSED, then close the epic.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trust the epic body's status table | Read the epic body (written 2026-03-28) listing all 12 children as "Open" and planned to fix all 13 | 9 of 12 children were already CLOSED+COMPLETED via merged PRs — the plan would re-do shipped work and risk a NOGO | The epic body is a snapshot that drifts; always query live child state with `gh` before planning |
| Treat `state == CLOSED` as "done" | Counted closed children as complete without checking `stateReason` | A closed-as-`not planned` issue would be mis-counted as complete | Confirm `stateReason == COMPLETED` AND a merged PR before counting a child shipped |
| Re-plan `state:plan-go` children | Considered generating fresh plans for the 3 open children | Discards reviewer-approved per-issue plans — the epic must defer to the children's existing plans, not regenerate them | `state:plan-go` = ready to implement; the epic dispatches, it does not re-plan |
| Use the audit's original dependency graph verbatim | Ordered work by the audit's stated dependency edges | Stale edges (an already-merged dependency, an already-closed downstream) produced a wrong ordering | Re-validate every dependency edge against current child state; merged deps unblock dependents, closed downstreams terminate branches |
| Cite the audit's "approx" LOC | Carried the audit's "4,241 lines" for `any_tensor.mojo` into the plan | The file had GROWN to 4,373 lines since the audit | Re-measure with `wc -l` and cite the fresh number, never the audit's stale approximation |

## Results & Parameters

### Copy-paste reference (ProjectOdyssey epic #5191)

```bash
# Per-child state sweep (children: the 12 numbered audit findings)
for n in <child ids>; do
  gh issue view "$n" --json number,state,stateReason \
    --jq '"\(.number) \(.state) \(.stateReason)"'
done
# Result: 9 of 12 → CLOSED COMPLETED; 3 → OPEN

# Merged-PR confirmation (distinguishes done from closed-as-wontfix)
gh pr list --search "<n> in:body" --state merged --json number,title

# Label check for approved-but-unimplemented children
gh issue view "<n>" --json labels --jq '.labels[].name'
#   state:plan-go    → reviewer-approved, ready to implement (no PR yet)
#   state:plan-no-go → re-plan required

# Fresh measurement (audit said 4,241; reality had grown)
wc -l src/projectodyssey/core/any_tensor.mojo   # → 4373
```

### Epic plan shape (the deliverable)

```text
Objective:            drive the remaining approved children to merged PRs + close-out
                      (NOT "plan/implement the fixes" — those plans already exist)
Files to Create/Modify: None in this epic; changes live in the children's own approved plans
Implementation Order: dispatch each open child via `impl <n>` in dependency order;
                      gate each dependent child behind its prerequisite's MERGE
Close-out:            re-verify all children CLOSED+COMPLETED, then close the epic
```

### Reframing observed in #5191

| Before (trusting body) | After (live sweep) |
|------------------------|--------------------|
| 13 findings, all "Open", plan all fixes | 9 already CLOSED+COMPLETED via merged PRs |
| Re-plan everything | Dispatch only 3 `state:plan-go` children (#5181, #5182, #5184) |
| Audit's original dependency graph | #5185 closed (branch ends); #5183 merged → #5184 unblocked/parallelizable |
| any_tensor.mojo = 4,241 lines | wc -l = 4,373 (grown; cite fresh) |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Epic #5191 strict-mode audit (13/12 child findings) planning session, 2026-06-19 | Read-only `gh`/`wc` state sweep executed: 9 of 12 children CLOSED+COMPLETED via merged PRs, 3 open children carry `state:plan-go`; dispatch/close-out steps are proposed (verified-local) |
