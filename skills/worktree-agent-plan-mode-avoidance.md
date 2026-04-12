---
name: worktree-agent-plan-mode-avoidance
description: "Prevent worktree-isolated agents from stopping to plan instead of executing. Use when: (1) Agent(isolation='worktree') returns a plan but no PR URL, (2) launching mechanical tasks like import migrations or config file edits, (3) agents ignore 'complete all steps' instructions and stop after planning."
category: tooling
date: 2026-04-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [worktree, agent, plan-mode, execution, myrmidon, haiku]
---

# Worktree Agent Plan-Mode Avoidance

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-12 |
| **Objective** | Prevent worktree-isolated agents from presenting plans instead of executing end-to-end |
| **Outcome** | Resolved — Haiku model + imperative-only prompts eliminated plan-mode stalling |
| **Verification** | verified-local (26 PRs created in ProjectOdyssey without manual intervention once pattern applied) |

## When to Use

- An `Agent(isolation="worktree")` returns with only a plan summary and no PR URL
- Launching mechanical tasks: import migrations, config edits, single-file cleanups
- Agent ignores "complete all steps end-to-end" or "DO NOT PLAN" instructions
- Need to relaunch a stuck agent with higher execution reliability

## Verified Workflow

### Quick Reference

```python
# For mechanical tasks: use Haiku and imperative-only prompts
Agent(
    description="Fix #N: one-line description",
    isolation="worktree",
    model="haiku",           # ← Haiku doesn't over-plan
    prompt="""Fix GitHub issue #N in ORG/REPO.

1. Run: gh issue view N --repo ORG/REPO
2. Run: cat path/to/file
3. Edit path/to/file — change X to Y on line ~50
4. Run: pre-commit run --files path/to/file
5. Run: git checkout -b N-slug
6. Run: git add path/to/file
7. Run: git commit -m "fix: description\n\nCloses #N"
8. Run: git push -u origin N-slug
9. Run: gh pr create --repo ORG/REPO --title "fix: description" --body "Closes #N"
10. Run: gh pr merge --auto --rebase --repo ORG/REPO"""
)
```

### Detailed Steps

1. **Identify task type**: Mechanical (single-file edit, import migration, config change) → use Haiku.
   Requires judgment (multi-file refactor, architecture decision) → use Sonnet but keep prompt minimal.

2. **Use `model="haiku"` for mechanical tasks**. Haiku skips planning preamble and executes directly.

3. **Write imperative-only prompts**: No `## Context`, `## Steps`, `## Rules` sections.
   Just numbered `Run:` lines plus one-line edit instructions.

4. **Specify the exact change**, not the reason: "Edit file X, add
   `elif self._dtype == DType.bfloat16:` after the `elif self._dtype == DType.float64:` line"
   rather than "fix the bfloat16 bug as described in the issue."

5. **Detect plan-mode stall**: If agent output contains a plan summary but no PR URL → stalled.
   Relaunch with Haiku + imperative format.

6. **No SendMessage recovery**: Worktree agents cannot be continued with SendMessage after returning.
   Each launch is independent — always relaunch fresh.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Preamble text | "DO NOT PLAN. EXECUTE IMMEDIATELY." at prompt start | Sonnet agents ignored preamble and planned anyway | Text instructions are unreliable; model selection and prompt structure matter more |
| End-of-prompt instruction | "Complete all steps end-to-end, don't stop and ask for help" | Same agents still stopped after planning phase | Post-hoc instructions don't override planning behavior |
| Section headers | Prompts with `## Context`, `## Steps`, `## Rules` sections | Headers trigger planning mode — agent treats each section as something to process before acting | Remove all section headers; use flat numbered `Run:` list |
| Sonnet for mechanical tasks | Used Sonnet for import migration and config edits | Sonnet over-plans simple tasks; returned plans 3/5 times | Mechanical tasks don't need Sonnet reasoning; Haiku executes directly |
| SendMessage continuation | Tried to send follow-up "now execute" message to stuck agent | SendMessage not available for worktree agents in this context | Each worktree agent launch is fully independent; plan and relaunch instead |

## Results & Parameters

### Model Selection Guide

| Task Type | Model | Reasoning |
|-----------|-------|-----------|
| Single-file edit (<50 lines) | Haiku | Fully specified; no judgment needed |
| Import migration (mechanical) | Haiku | Pattern-based; no design decisions |
| Config file restructuring | Haiku | Well-defined; deterministic |
| Multi-file refactor | Sonnet | Requires reading multiple files and making decisions |
| Bug fix requiring investigation | Sonnet | May need to read error context and reason |
| Architectural change | Sonnet/Opus | Requires judgment beyond mechanical execution |

### Prompt Format Comparison

**Plan-triggering format (avoid):**

```text
You are fixing GitHub issue #N in ORG/REPO.

## Context
The bug is in shared/tensor/any_tensor.mojo. The to_fp8() method...

## Steps
1. Read the issue to understand requirements
2. Find the relevant file and identify the bug
3. Make the minimal fix
4. Run pre-commit and verify
5. Create branch, commit, push, create PR
6. Enable auto-merge

## Rules
- Read files before editing
- Never use git add -A
```

**Execution-triggering format (use this):**

```text
Fix GitHub issue #N in ORG/REPO.

1. Run: gh issue view N --repo ORG/REPO
2. Run: cat shared/tensor/any_tensor.mojo | grep -n "to_fp8\|to_bf8" | head -20
3. Edit shared/tensor/any_tensor.mojo — add after the `elif self._dtype == DType.float64:` line
   in to_fp8(): `elif self._dtype == DType.bfloat16:\n    val = ...`
4. Run: pre-commit run --files shared/tensor/any_tensor.mojo
5. Run: git checkout -b N-fix-bfloat16
6. Run: git add shared/tensor/any_tensor.mojo
7. Run: git commit -m "fix: description\n\nCloses #N"
8. Run: git push -u origin N-fix-bfloat16
9. Run: gh pr create --repo ORG/REPO --title "fix: description" --body "Closes #N"
10. Run: gh pr merge --auto --rebase --repo ORG/REPO
```

### Detection Heuristic

Agent got stuck in plan mode if its output:

- Contains a plan summary with "Here is my plan:" or "Plan is ready"
- Does NOT contain a PR URL (https://github.com/...)
- Contains phrases like "ready to execute when plan mode is lifted" or "switch out of plan mode to proceed"

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Wave D/E bulk issue fixing — 26 PRs, 2026-04-12 | 5/8 Sonnet agents stalled; Haiku relaunches all executed |
