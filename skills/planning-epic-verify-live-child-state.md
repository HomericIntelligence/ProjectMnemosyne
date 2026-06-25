---
name: planning-epic-verify-live-child-state
description: "Before planning an epic/tracking/umbrella issue, query the LIVE state of every child issue with gh (state, stateReason, merged PRs, labels) instead of trusting the epic body's status table — the body is a snapshot and drifts. Most children may already be CLOSED+COMPLETED via merged PRs, reframing the epic from 'plan N fixes' to 'dispatch the few remaining state:plan-go children + close-out'. Use when: (1) planning an epic/tracking/umbrella issue, (2) re-planning after a NOGO on a tracking issue, (3) any issue whose body is a checklist of child issues, (4) deciding implementation order across linked issues."
category: tooling
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: verified-local
history: planning-epic-verify-live-child-state.history
tags: [epic, tracking-issue, child-issues, planning, gh-cli, state-plan-go, dependency-ordering, orchestration, audit-remediation, stale-body, verification-block, path-audit, freshness-gate]
---

# Planning: Re-Verify Live Child-Issue State Before Planning an Epic

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Produce a correct implementation plan for an epic/tracking issue whose body lists many child issues — without re-planning children that have already shipped |
| **Outcome** | R0 NOGO (grade C) — the live `gh` sweep was correct (9 of 12 children already CLOSED+COMPLETED) but the plan INVENTED test paths in the Verification block and assumed an "extend" issue was net-new; R1 re-plan added a Verification-block path audit + a child-plan freshness gate + a capability-absence check and scoped to the 3 remaining `state:plan-go` children in re-validated dependency order |
| **Verification** | verified-local — the read-only `gh`/`find`/`wc`/`grep` queries were executed this session and returned the cited results; the downstream child PRs are not yet merged, so end-to-end epic closure is not CI-confirmed |
| **Source** | ProjectOdyssey epic #5191 (strict-mode audit, 13/12 child findings) planning session — R0 NOGO → R1 re-plan |

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

# 5. VERIFICATION-BLOCK PATH AUDIT — confirm EVERY test path BEFORE writing it.
#    The Verification block IS the only deliverable of an epic plan; a single
#    invented path = file-not-found when the reviewer runs it = NOGO.
find tests -name 'test_<topic>*.mojo'        # substitute the real path or drop the claim

# 6. FRESHNESS GATE — read each approved child's latest plan and confirm its cited
#    paths/line-counts still resolve before dispatching (plans CAN go stale).
gh issue view "<child>" --comments --json comments \
  --jq '.comments[-1].body' | grep -nE '<line-count>|<cited path>'
wc -l <cited file>                            # confirm the child's cited count is current

# 7. CAPABILITY-ABSENCE CHECK before scoping an "extend" issue as net-new. Read the
#    target file; zero keyword matches = genuinely absent = reframe as "extend struct X".
grep -nE 'tmp|rename|atomic|resume|recover|--fresh|retry' path/to/target.mojo
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

6. **Audit every test path in the Verification block before finalizing.** For a tracking/epic
   plan the Verification block IS the only deliverable, so every path must be real. For EACH test
   path you intend to cite, run `find tests -name '<glob>'` (or `ls`) and substitute the confirmed
   path or drop the claim. NEVER infer a test path from a sibling's directory shape — in #5191 R0
   the plan invented `tests/models/test_anytensor_conversion.mojo` and
   `tests/training/test_checkpoint.mojo` from the repo's apparent convention; neither existed (real
   tests live under `tests/projectodyssey/tensor/` and `tests/projectodyssey/training/`), the
   reviewer ran the commands, hit file-not-found, and NOGO'd at grade C (major).

7. **Run a FRESHNESS GATE on each approved child plan — don't trust the `state:plan-go` label
   alone.** An approved-plan label is not proof the plan is still current; child plans CAN go stale
   (e.g. cite an old line count). Read each child's latest plan comment
   (`gh issue view <n> --comments --jq '.comments[-1].body'`) and confirm its cited paths/line-counts
   still resolve (`wc -l`, `grep -n`) before dispatching. In #5191 R1 the child plans WERE current
   (cited `any_tensor.mojo:4383-4413`, a ≤3,000-line target with a #5181-merge contingency, and real
   test paths) — but that had to be VERIFIED, not assumed.

8. **Check for capability ABSENCE before scoping an "extend" issue as net-new work.** Read the
   target file and `grep` for the specific capabilities the issue adds — zero matches = genuinely
   absent = reframe as "extend struct X at file:line", citing the current method inventory. In
   #5191 the plan treated #5184 (checkpoint recovery) as if `checkpoint.mojo` were empty, but
   `CheckpointManager` already existed (381 lines: save/load/metadata), risking duplicate/wrong-scope
   work; `grep -nE 'tmp|rename|atomic|resume|recover|--fresh|retry'` confirmed the recovery
   primitives were absent and the issue was genuinely an extension.

9. **Shape the epic plan as orchestration, not code.** Objective = "drive remaining approved
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
| Invented plausible test paths in the Verification block | Wrote `tests/models/test_anytensor_conversion.mojo` and `tests/training/test_checkpoint.mojo` from memory of the repo's apparent convention | Neither existed; real tests live under `tests/projectodyssey/tensor/` and `tests/projectodyssey/training/`. Reviewer ran the commands → file-not-found, NOGO (major) | For a tracking/epic plan the Verification block IS the only deliverable — EVERY path must be confirmed with `find tests -name '<glob>'` or `ls` BEFORE writing it. Never infer a test path from a sibling's directory shape |
| Assumed a referenced "extend" issue was net-new work without reading the target file | Planned #5184 (checkpoint recovery) as if `checkpoint.mojo` were empty | `CheckpointManager` already existed (381 lines, save/load/metadata) — risk of duplicate work / wrong scope | Read the target file and `grep -nE 'tmp\|rename\|atomic\|resume\|recover\|--fresh\|retry'` for the specific capabilities the issue adds; zero matches = genuinely absent = reframe as "extend struct X at file:line" citing the current method inventory |
| Deferred to children's `state:plan-go` labels without reading the child plan bodies | Trusted the approved-plan label as proof the child plans were current | Child plans CAN go stale (e.g. cite an old line count); reviewer flagged this as an unmitigated risk | Add a FRESHNESS GATE: read each child's latest plan comment (`gh issue view <n> --comments --jq '.comments[-1].body'`) and confirm its cited paths/line-counts still resolve (`wc -l`, `grep -n`) before dispatching. In #5191 R1 the child plans were current (cited `any_tensor.mojo:4383-4413`, ≤3,000 target with a #5181-merge contingency, real test paths) — but that had to be VERIFIED, not assumed |

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

# Verification-block path audit (cite ONLY confirmed paths)
find tests -name 'test_*.mojo'                  # filter by topic; real tensor/training tests
#   live under tests/projectodyssey/tensor/ and tests/projectodyssey/training/, NOT
#   tests/models/ or tests/training/ (invented paths that NOGO'd R0)

# Freshness gate (confirm an approved child plan's cited facts still resolve)
gh issue view <child> --comments --json comments --jq '.comments[-1].body' \
  | grep -nE '<line-count>|<path>'
wc -l <cited file>                              # confirm the child's cited count is current

# Capability-absence check before scoping an "extend" issue
grep -nE 'tmp|rename|atomic|resume|recover|--fresh|retry' \
  src/projectodyssey/training/checkpoint.mojo   # zero matches → net-new → reframe as extend
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
| ProjectOdyssey | Epic #5191 planning — R0 NOGO (grade C, invented test paths) → R1 re-plan with path audit + freshness gate, 2026-06-19 | Read-only `gh`/`find`/`wc`/`grep` queries executed: 9 of 12 children CLOSED+COMPLETED via merged PRs, 3 open children carry `state:plan-go`; R0 NOGO'd on invented Verification paths (`tests/models/...`, `tests/training/...` — real tests under `tests/projectodyssey/{tensor,training}/`); R1 added path audit, child-plan freshness gate, and a capability-absence check (`CheckpointManager` already 381 lines). Dispatch/close-out steps are proposed; downstream child PRs not yet merged (verified-local) |
