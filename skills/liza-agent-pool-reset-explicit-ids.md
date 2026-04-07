---
name: liza-agent-pool-reset-explicit-ids
description: "Reset a dirty Liza workspace and relaunch a clean agent pool with explicit agent IDs so ghost assignments do not reappear. Use when: (1) tasks retain stale `assigned_to` or `worktree` fields after agent failure, (2) `liza` reports invalid state because one agent is assigned to multiple active tasks, (3) leftover task worktrees and local agent processes keep the queue in a bad state, (4) you want to relaunch planners, reviewers, coders, and the orchestrator deterministically."
category: tooling
date: 2026-04-07
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - liza
  - agents
  - worktree
  - recovery
  - orchestration
  - queue
---

# Liza Agent Pool Reset With Explicit IDs

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-07 |
| **Objective** | Clear stale task claims, worktrees, and local Liza processes, then relaunch a deterministic agent pool |
| **Outcome** | Successful -- recovered leftover tasks, removed task worktrees/branches, killed orphaned local `liza` processes, validated state, and resumed the workspace cleanly |
| **Verification** | verified-local |

## When to Use

- `liza status` or the TUI reports invalid state such as one planner assigned to multiple active tasks
- Tasks still show `assigned_to`, `reviewing_by`, or `worktree` long after the worker died
- `git worktree list` still contains `github-issue-*` task worktrees after the queue should be idle
- You need to restart the worker fleet and want to avoid anonymous `code-planner-*` reuse

## Verified Workflow

### Quick Reference

```bash
# 1. Recover stale task claims so Liza removes their worktrees/branches
liza recover-task github-issue-26 --reason "full workspace cleanup before agent relaunch"

# 2. Verify task worktrees are gone
git worktree list | rg 'github-issue-' || true
git branch --list 'task/github-issue-*'

# 3. Stop lingering local liza processes
pgrep -af '^liza ' || true
kill <pid> <pid> ...

# 4. Validate, resume, and relaunch with explicit IDs
liza validate
liza resume
liza agent orchestrator --agent-id orchestrator-1 --cli codex
liza agent code-planner --agent-id code-planner-1 --cli codex
```

### Detailed Steps

1. Check whether the problem is stale execution state rather than real dependency blocking:

   ```bash
   liza status --detailed
   python3 - <<'PY'
   from pathlib import Path
   import yaml
   state = yaml.safe_load(Path('.liza/state.yaml').read_text())
   for task in state.get('tasks', []):
       if task.get('assigned_to') or task.get('reviewing_by') or task.get('worktree'):
           print(task['id'], task.get('status'), task.get('assigned_to'), task.get('reviewing_by'), task.get('worktree'))
   PY
   ```

2. Recover every stale claimed task. This is the cleanest way to get Liza to remove its own worktree and task branch:

   ```bash
   liza recover-task github-issue-16 --reason "full workspace cleanup before agent relaunch"
   liza recover-task github-issue-23 --reason "full workspace cleanup before agent relaunch"
   ```

3. Verify the Git side is actually clean:

   ```bash
   git worktree list | rg 'github-issue-' || true
   git branch --list 'task/github-issue-*'
   ```

4. Kill leftover local `liza` processes, including idle TUIs and agents that are no longer represented in state:

   ```bash
   pgrep -af '^liza ' || true
   kill <pid> <pid> ...
   ```

5. Validate the workspace before relaunch:

   ```bash
   liza validate
   ```

6. Resume the system:

   ```bash
   liza resume
   ```

7. Relaunch the fleet with explicit IDs. Do not rely on bare `liza agent code-planner` if you have already seen ghost IDs or multi-assignment:

   ```bash
   liza agent orchestrator --agent-id orchestrator-1 --cli codex
   liza agent code-planner --agent-id code-planner-1 --cli codex
   liza agent code-planner --agent-id code-planner-2 --cli codex
   liza agent code-plan-reviewer --agent-id code-plan-reviewer-1 --cli codex
   liza agent coder --agent-id coder-1 --cli codex
   liza agent code-reviewer --agent-id code-reviewer-1 --cli codex
   ```

8. If you need the processes to survive your terminal, background them explicitly and keep separate log files:

   ```bash
   nohup bash -lc 'cd /repo && liza agent code-planner --agent-id code-planner-1 --cli codex' >/tmp/liza-code-planner-1.log 2>&1 &
   ```

### Key Rule

Use explicit `--agent-id` values for every relaunched worker. Anonymous launches make it harder to distinguish fresh workers from stale logical agent IDs in the Liza state and were associated with repeated multi-assignment corruption during recovery.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Relaunching bare planners | Started `liza agent code-planner` without `--agent-id` | Anonymous planner IDs were reused and the workspace later showed one planner assigned to multiple tasks | After a dirty recovery, always relaunch with fixed IDs |
| Cleaning only OS processes | Killed local `liza` PIDs but left stale task claims in state | Liza still considered tasks assigned and their worktrees/branches remained on disk | Recover tasks first so Liza clears its own metadata and Git artifacts |
| Ignoring leftover task worktrees | Resumed the queue before checking `git worktree list` and `task/github-issue-*` branches | Old task branches/worktrees kept the repo messy and made it harder to tell whether agents were actually fresh | Verify both Liza state and Git state before relaunch |

## Results & Parameters

### Signals That Cleanup Worked

- `liza validate` returns `VALID`
- `git worktree list` shows no stale `github-issue-*` worktrees
- `git branch --list 'task/github-issue-*'` returns no leftover task branches you intended to clear
- `liza status --detailed` shows no active agents until you relaunch them

### Relaunch Pattern

| Role | Recommended Count | Naming Pattern |
|------|-------------------|----------------|
| Orchestrator | 1 | `orchestrator-1` |
| Code Planner | N | `code-planner-1..N` |
| Code Plan Reviewer | N | `code-plan-reviewer-1..N` |
| Coder | N | `coder-1..N` |
| Code Reviewer | N | `code-reviewer-1..N` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Radiance | Live Liza cleanup before worker relaunch | Recovered stale claims, deleted task worktrees/branches, killed lingering local Liza processes, and restored a clean queue before relaunch |
