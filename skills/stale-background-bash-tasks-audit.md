---
name: stale-background-bash-tasks-audit
description: "Background Bash tasks (via run_in_background) have no built-in completion timeout. If their command hangs (tmpdir cleanup, missing dependency, polling loop with no deadline), they stay 'running' indefinitely with no parent notification. Use when: (1) a parent agent realizes it dispatched a background bash task hours ago and never heard back, (2) the user reports 'X is still running' from their UI panel, (3) writing a polling loop that needs to wait on an external condition, (4) writing a repro harness that depends on transient tmpdirs."
category: tooling
date: 2026-05-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - bash
  - run_in_background
  - background-task
  - stale-task
  - timeout
  - polling-loop
  - tmpdir-cleanup
  - task-audit
---

# Stale Background Bash Tasks: Audit and Prevention

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-25 |
| **Objective** | Detect, stop, and prevent stale `Bash run_in_background: true` tasks whose shell command hung on a vanished dependency or an unbounded polling loop |
| **Outcome** | Successful — root cause identified, audit + prevention workflow confirmed |
| **Verification** | verified-local |

## When to Use

- A parent agent realizes it dispatched a background bash task hours ago and never heard back.
- The user reports "X is still running" from their UI panel, with a Runtime far exceeding what the task should need.
- Writing a polling loop that needs to wait on an external condition (PR merge, file appearance, build completion).
- Writing a repro harness that depends on transient `/tmp` directories or stub binaries.

This skill is about **shell commands dispatched via `Bash run_in_background: true`**. For the DIFFERENT case of silent API-connection failures inside background AGENT dispatches, see [[agent-background-task-failure-recovery]].

## Verified Workflow

### Quick Reference

```bash
# PREVENTION 1: Always wrap one-shot repro/diagnostic bash in `timeout`
timeout 60 bash -c "..."

# PREVENTION 2: Polling loops MUST have a deadline + forced-failure clause
deadline=$(( $(date +%s) + 3600 ))   # 1 hour max
while [ "$(date +%s)" -lt "$deadline" ]; do
  if <success-condition>; then break; fi
  sleep 60
done
if ! <success-condition>; then
  echo "FATAL: deadline expired without success" >&2
  exit 1
fi

# DETECTION: Inspect mtimes of background-task output files for stale entries
ls -lat /tmp/claude-*/-home-*/$SESSION_ID/tasks/b*.output 2>/dev/null | head -20

# REMEDIATION: Stop a confirmed-stale task
# (use TaskStop with the task-id reported by the user's UI)
```

### Detailed Steps

1. **After every major task transition** (epic closed, swarm completed, user changed direction), audit live background bash tasks. The parent agent cannot natively enumerate them, but `.output` symlink mtimes provide a hint:
   ```bash
   ls -lat /tmp/claude-*/-home-*/$SESSION_ID/tasks/b*.output 2>/dev/null | head -20
   ```
   Old mtimes on tasks that were never followed up are candidates. False positives possible (completed tasks also have old mtimes); the user's UI panel is the authoritative source.

2. **When the user reports a stale task**, identify it by the command text shown in their UI panel, then stop it with `TaskStop`. Do not try to "let it finish" — if it has run far past expectation, the terminal condition is not coming.

3. **For repro harnesses specifically**: prefer foreground invocation with explicit `timeout`:
   ```bash
   timeout 60 bash -c "<heredoc>"
   ```
   The `timeout` guarantees terminal state regardless of inner-command behavior. Do **NOT** use `run_in_background: true` for repro work that depends on `/tmp` directories or stub binaries — the OS may clean those mid-run, leaving any `wait` call hung indefinitely.

4. **For polling loops**: always combine an explicit deadline AND a condition AND a forced-failure clause (see Quick Reference). Never write `until <cond>; do sleep N; done` without a deadline — if `<cond>` never becomes true (PR closed without merge, build cancelled, etc.), the loop runs forever.

5. **When a task notification arrives with `summary: completed` but `result: No output available`**: the task may have finished cleanly with output to a redirected file, or may have crashed silently. Distinguish by reading the `.output` file directly with `tail`:
   ```bash
   tail -20 /tmp/claude-*/-home-*/$SESSION_ID/tasks/$TASK_ID.output
   ```
   Do **not** read the symlink target (the JSONL transcript) — it overflows context.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `Bash run_in_background: true` for a one-shot repro with `/tmp` dir dependency | Wrote stub binaries into `/tmp/repro-XXXX/bin/` and dispatched a backgrounded harness that `wait`ed on a child subshell calling those stubs | OS cleaned `/tmp` mid-run; stubs disappeared; the inner `wait` hung; task stayed "running" for 2h 15m with zero output | One-shot repros must run foreground with an explicit `timeout` prefix — never `run_in_background` when the command depends on transient tmpdirs |
| `until <condition>; do sleep 60; done` with no deadline | Polled for an external state change (PR merge, file appearance) in a loop with no timeout | When the awaited condition never became true (e.g., the PR was closed without merge), the loop ran indefinitely with no terminal state | Every polling loop MUST have a deadline AND a forced-failure clause that `exit 1`s after the deadline expires |
| Forgetting which background tasks were still alive | Parent agent moved on to other diagnostics ~3 hours earlier; never re-checked the background task it had dispatched | Background bash tasks have no built-in completion timeout; one accidentally-stuck task ran for hours and burned compute | Audit live background tasks at every major session transition; the user's UI is the only authoritative list |
| Reading the `.output` symlink's TARGET file directly | Used `cat` on the JSONL transcript pointed to by the symlink | Overflows context — the JSONL is the full subagent transcript | Use `ls -la` for mtime only, or `tail -20` on the `.output` path; never `cat` the target JSONL |

## Results & Parameters

**Concrete incident (2026-05-25 ProjectHephaestus session):**

- **Task-id**: `b7v9j872p`
- **Command**: a heredoc that wrote stub binaries into `/tmp/repro-XXXX/bin/hephaestus-plan-issues`, sourced `/tmp/repro.env`, spawned `process_repo fake_repo 1 &`, then called `wait "${ACTIVE_PIDS[0]}"`.
- **Runtime before detection**: 2h 15m 41s.
- **Detection path**: user noticed the running task in their UI panel and reported it (parent agent had no native enumeration).
- **UI panel signature**:
  ```
  Status:   running
  Runtime:  2h 15m 41s
  Command:  source /tmp/repro.env
            # More realistic planner stub: spawns a child...
  Output:   No output available
  ```
- **Root cause**: either (a) `/tmp/repro-XXXX` was cleaned by the OS during normal cleanup, removing the stub binaries the `wait`ed child needed, or (b) the subshell's `process_repo` invoked the now-deleted stub and hung on its own subshell. No terminal condition would have ever fired.
- **Remediation**: `TaskStop` on `b7v9j872p`; audit pass for other stale tasks via `.output` mtimes.

**Prevention parameters:**

| Knob | Recommended value |
| ---- | ----------------- |
| Foreground `timeout` prefix for one-shot diagnostics | `timeout 60` (raise as needed but always set one) |
| Polling-loop deadline | `$(date +%s) + 3600` (1 hour) unless the task genuinely needs longer |
| Polling-loop sleep interval | `60` seconds (balance between responsiveness and noise) |
| Audit cadence | After every major task transition (epic closed, swarm done, user pivot) |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Background bash repro harness `b7v9j872p` ran 2h 15m 41s before user UI report; `wait` hung after `/tmp/repro-XXXX` cleanup removed stub binaries | Session 2026-05-25 |

## See Also

- [[agent-background-task-failure-recovery]] — sibling skill for the DIFFERENT case of silent API errors in background AGENT dispatches. That skill covers `Task` / sub-agent failures (status: completed + result: API Error). THIS skill covers `Bash run_in_background: true` shell commands that hang on vanished dependencies or unbounded polling. The two failure modes look superficially similar (parent agent loses track of a background unit of work) but require completely different remediation: foreground re-dispatch for agents, vs `timeout`/deadline patterns for shells.
- [[swarm-agent-status-misread-as-premature-exit]] — related inverse failure mode: parent re-dispatches an agent that's still running. Both this skill and that one arise from poor parent-agent observability of child task state.
