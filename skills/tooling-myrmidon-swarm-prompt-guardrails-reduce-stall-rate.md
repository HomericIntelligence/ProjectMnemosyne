---
name: tooling-myrmidon-swarm-prompt-guardrails-reduce-stall-rate
description: "Prompt-design guardrails that reduce Myrmidon swarm agent stall rate from 80% to 0% on multi-agent dispatches. Use when: (1) preparing to dispatch 5+ Opus agents in parallel via Task isolation=worktree, (2) prior swarm round had high stall rate (stream-idle / no-progress watchdog), (3) tasks touch architectural / cross-cutting / multi-file work, (4) deciding between full-fix and partial-fix scope for a single PR."
category: tooling
date: 2026-05-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [myrmidon, swarm, prompt-design, scope-guardrails, partial-fix, refs-not-closes, agent-dispatch, stall-prevention]
---

# Skill: Myrmidon Swarm Prompt Guardrails to Reduce Stall Rate

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-06 |
| **Objective** | Eliminate Myrmidon swarm agent stalls on architectural / cross-cutting GitHub issues by changing only the dispatch prompt, not the model or harness |
| **Outcome** | Stall rate dropped from 4 of 5 (80%) on round 1 to 0 of 7 (0%) on round 2 in a single ProjectScylla session — same Opus model, same `Task isolation=worktree` dispatch, only the prompts changed |
| **Verification** | verified-local — measured 2026-05-06 across two consecutive Myrmidon dispatch rounds in the ProjectScylla repo |

## When to Use

- You are about to dispatch 5+ Opus agents in parallel against GitHub issues via `Task isolation=worktree`
- A prior swarm round had a high stall rate (stream-idle watchdog firing, agents giving up mid-plan)
- The issues being dispatched touch architectural / cross-cutting / multi-file refactor work
- You are deciding between a full-fix scope and a partial-fix scope for a single PR
- You want to write a dispatch prompt that does NOT depend on the agent self-discovering repo policies (merge method, pre-commit skip flags, etc.)

## Verified Workflow

The seven guardrails below are listed in approximate order of impact. Apply ALL of them when dispatching against hard issues — they compose.

### 1. `Refs #N` instead of `Closes #N` for partial fixes

`Closes #N` puts psychological pressure on the agent to ship the entire issue. On a multi-file refactor (e.g. "decompose 4 files into modules"), this triggers analysis paralysis: the agent maps all 4 files, runs out of token budget, and stalls.

`Refs #N` lets the agent ship a slice and move on. Combine with explicit "this is a partial fix; the rest is tracked in #M and #L" wording in the PR body.

**Example:** ProjectScylla #1876 originally said "decompose 4 files." Round-2 prompt scoped it to "decompose ONE file (`loader.py`); the other three need their own follow-up PRs. Use `Refs #1876`, not `Closes`." Agent finished cleanly.

### 2. Scope down to one file or one piece

For cross-cutting work, pick one slice now and file the rest. The "one slice" framing avoids the wide-refactor stall mode where the agent gets stuck mapping the whole thing before writing any code.

**Examples:**
- #1887 ("structured logging + tracing") → "JSON logging foundation only; tracing is out of scope."
- #1888 ("scaffold + wire call sites") → "scaffold only; do NOT touch existing call sites."

### 3. Hard LOC budgets per agent

State the cap explicitly: `Scope ≤ ~400 LOC of net change` or `≤ ~250 LOC including tests`. Agents that exceeded the budget on round 1 stalled while planning maximalist solutions; agents under the budget on round 2 finished in under 8 minutes.

Round-2 budgets that worked: 250–600 LOC depending on the slice.

### 4. Gated verification with explicit STOP path

Build a Step 1 verification gate into the prompt, with an explicit STOP condition that does NOT open a PR.

**Example (#1537):** "Step 1 must be: verify which entry points actually exist and which are true duplicates. If FEWER than 5 of 9 entry points exist OR fewer than 3 are true duplicates, STOP and comment on the issue without opening a PR." The agent verified 9 of 9 existed but found only 3 were true duplicates — and consolidated those 3 instead of forcing all 9. No stall.

### 5. Explicit scope-out boundaries for foundation/scaffold PRs

Write the *don'ts* into the prompt: `Do NOT modify production code in <area>`, `Do NOT touch existing call sites`, `Do NOT migrate any existing tests`. Without these, the agent expands scope mid-task and stalls when the expanded scope blows the LOC budget.

### 6. Real-evidence requirement for documentation tasks

For any "produce a doc / table / report" issue, require:
- Real `path/to/file.py:LINE` citations for every claim
- An explicit `TBD` marker for every numeric cell that lacks a citation

This kills the stall mode where the agent invents data, doubts itself, and freezes mid-table.

**Example (#1892):** Round-2 prompt produced 41 real code citations + 44 explicit `TBD` cells. No stall.

### 7. PR protocol block, copy-paste ready, with the repo's actual merge method

Embed a literal PR protocol block in the prompt so the agent does not rediscover repo policy:

```text
git push -u origin <N>-<slug>
gh pr create --title "..." --body "...Refs #<N>."
gh pr merge --auto --squash    # repo only allows squash, not rebase
```

Include the parenthetical "(Repo only allows squash auto-merge)" so the agent doesn't try `--rebase` first, fail, and waste tokens investigating.

### Quick Reference

Fill-in-the-blank prompt template — paste into a Task call with `subagent_type="general-purpose"` and `isolation=worktree`:

```text
You are an L4 implementation agent in the Myrmidon swarm. You are running
in an isolated git worktree on branch `<N>-<slug>` based on `main`
(HEAD `<sha>`). Implement <full|partial> GitHub issue #<N> in <repo>
and open a single PR.

## Your task — <one-sentence scope>

<short context>

## Hard constraints (READ FIRST)

- Branch name: `<N>-<slug>`. Do not create any other branch.
- Scope ≤ ~<LOC> LOC of net change.
- Do NOT modify <area-out-of-scope>.
- <Optional Step-1 STOP gate: if condition X is not met, STOP and comment on
  the issue without opening a PR>
- Run `SKIP=audit-doc-policy pre-commit run --all-files` before pushing — must pass.
- Use `Refs #<N>` (NOT `Closes #<N>`) since this is a partial fix.

## PR protocol

```
git push -u origin <N>-<slug>
gh pr create --title "..." --body "...Refs #<N>."
gh pr merge --auto --squash    # repo only allows squash, not rebase
```

## Output (under 150 words)

- <metric 1>
- <metric 2>
- PR URL

The user does NOT see your tool calls — only this final summary.
```

## Failed Attempts (Round 1 Anti-Patterns)

| # | What Was Tried | Why It Failed | Lesson Learned |
|---|----------------|---------------|----------------|
| 1 | Generic "implement #N" with full-issue scope | Agent gets lost in analysis when the issue spans 4 files / cross-cutting work | Scope to one slice; use `Refs` not `Closes` |
| 2 | No LOC budget | Agent attempts a maximalist solution then stalls when it cannot fit it together | Hard LOC ceiling forces decomposition early |
| 3 | `Closes #N` on a partial-fix scope | Agent feels obligated to do the whole issue → analysis paralysis | `Refs #N` + explicit "this is a partial fix" wording in PR body |
| 4 | Telling the agent "auto-merge with `--rebase`" without checking repo policy | Repo only allows squash; agent's `gh pr merge --auto --rebase` errors out and the agent investigates instead of trying squash | Tell the agent the merge method up front (squash vs rebase) |
| 5 | Letting the agent invent test cases / numbers / design rationale | Agent stalls when it cannot find supporting evidence in the codebase | Require real `file:line` citations for all docs; require an explicit test-name list |

## Results & Parameters

### Measured comparison (single ProjectScylla session, 2026-05-06)

| Metric | Round 1 (medium issues) | Round 2 (hard issues) |
|---|---|---|
| Agents dispatched | 5 | 7 |
| Model | Opus, `isolation=worktree` | Opus, `isolation=worktree` |
| Stall rate | 4 of 5 (80%) | 0 of 7 (0%) |
| PRs delivered | 5 (4 via manual recovery) | 7 (all clean agent finish) |
| Avg duration per finished agent | mixed (recovery-heavy) | 305–455s, all under 8 min |
| Token budget per finished agent | unbounded | 60k–83k, mostly under 100k |

### Parameters that worked on round 2

- LOC budget: 250–600 per agent (varied by slice)
- All seven guardrails applied to every dispatch prompt
- All seven dispatches used `Refs #N`, not `Closes #N`, since each was a deliberate partial fix
- One dispatch (#1537) used a Step-1 STOP gate; it triggered correctly (3 duplicates found instead of 9)

### Known follow-on issue (out of scope here)

Two of the 7 round-2 PRs (capacity planning + ADRs) needed a manual rebase post-merge due to a `docs/README.md` collision when both agents added entries to the same index file. That is a multi-agent docs/README collision pattern and belongs in its own skill — not addressed by these prompt guardrails.
