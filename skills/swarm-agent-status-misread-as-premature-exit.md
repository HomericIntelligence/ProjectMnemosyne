---
name: swarm-agent-status-misread-as-premature-exit
description: "Distinguish in-progress status updates from premature-exit signals when dispatching parallel swarm sub-agents. Use when: (1) a parallel agent's notification arrives with short duration_ms (<60s) and 'waiting'/'polling' result text, (2) deciding whether to re-dispatch an apparently-stuck swarm agent, (3) auditing a multi-agent swarm for duplicate dispatches that caused PR/branch collisions, (4) the parent agent feels tempted to dispatch a retry within the first minute of a parallel agent's life."
category: tooling
date: 2026-05-25
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - swarm
  - sub-agent
  - parallel-agents
  - run_in_background
  - duration_ms
  - status-misread
  - premature-retry
  - duplicate-pr
  - branch-collision
  - myrmidon
---

# Swarm Agent Status Misread as Premature Exit

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-25 |
| **Objective** | Stop misreading in-progress status updates from parallel swarm sub-agents as terminal completions and prevent duplicate dispatches |
| **Outcome** | Successful — diagnostic rules and re-dispatch gate confirmed against a 4-agent swarm session |
| **Verification** | verified-local |

## When to Use

- A parallel swarm agent's notification arrives with short `duration_ms` (under 60,000 ms) and `result` text contains "waiting", "polling", "monitoring", or "stand by".
- You are deciding whether to re-dispatch an apparently-stuck swarm agent that hasn't reported completion yet.
- You are auditing a multi-agent swarm session for duplicate dispatches that caused PR or branch collisions.
- The parent agent feels tempted to dispatch a retry within the first minute of a parallel agent's life.

## Verified Workflow

### Quick Reference

```text
1. On notification arrival: read <duration_ms> FIRST.
2. If duration_ms < 60000 AND result contains wait/poll/monitor/stand-by  -> STILL RUNNING. Do NOT retry.
3. The harness fires ONE terminal notification per agent. Trust only that one.
4. If unsure, check transcript mtime:
     ls -la /tmp/claude-*/-home-*/$SESSION_ID/tasks/agent-$AGENT_ID.output
     ls -la /home/*/.claude/projects/-home-*/$SESSION_ID/subagents/agent-$AGENT_ID.jsonl
   mtime within last 5 minutes => agent is still active.
5. Re-dispatch ONLY when result contains explicit failure semantics
   ("FATAL", "exit 1", "timed out", "could not"). Otherwise wait >= 60 minutes.
```

### Detailed Steps

1. **Read `duration_ms` before reading `result`.** Any task notification with `duration_ms` under 60,000 is almost certainly an intermediate status update, not a terminal exit. Terminal completions for swarm agents that wait on PRs typically run 20-75 minutes (~1,200,000-4,500,000 ms).

2. **Classify the `result` text.** Phrases like "waiting", "polling", "monitoring", "stand by", "I'll notify when", "Monitor is already running" indicate the agent is still alive and has merely surfaced a status string. A real terminal result either contains a concrete PR URL, an explicit no-op detection ("already closed", "no work to do"), or an explicit failure phrase ("FATAL", "exit 1", "timed out", "could not").

3. **Trust the single terminal notification.** The harness fires exactly one notification per agent at terminal state. There is no "ping" notification mechanism — if you appear to receive a "second" notification from the same agent-id, that is the terminal one and the first was an intermediate harness flush, OR a different agent (a retry you launched) is reporting.

4. **If uncertain, check the transcript file's mtime.** The JSONL is for forensics, not for live reading — the parent context overflows if you `cat` it. Use `ls -la` only:

   ```bash
   ls -la /tmp/claude-*/-home-*/$SESSION_ID/tasks/agent-$AGENT_ID.output
   ls -la /home/*/.claude/projects/-home-*/$SESSION_ID/subagents/agent-$AGENT_ID.jsonl
   ```

   An mtime within the last 5 minutes means the agent is still active. Stale mtime + no terminal notification means truly hung; consider re-dispatch.

5. **Gate re-dispatches behind explicit failure semantics.** Only re-dispatch when the terminal notification contains "FATAL", "exit 1", "timed out", or "could not". Otherwise wait at least 60 minutes for the polling step to complete. If you do re-dispatch, plan cleanup ahead of time: `gh pr close --delete-branch <dup-pr>` and `git worktree remove <dup-worktree>` for the inevitable branch-name race.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Re-dispatching after a "waiting" result | Treated "background poll is running, I'll wait" as a completion and launched a retry | The agent was still polling — both originals and retries ran concurrently, producing duplicate PRs and branch collisions | A "waiting" result means alive, not done; do not retry |
| Treating short-duration notification as completion | Read `result` text without checking `duration_ms`; under-60s status flush mistaken for terminal exit | Intermediate harness flushes can surface a `result` string while the agent is still running; only terminal notifications mean exit | Read `duration_ms` first; <60,000 ms is almost never terminal for a wait-on-PR agent |
| Assuming same agent-id reported twice | Believed the harness emits multiple notifications per agent | The harness fires ONE terminal notification per agent-id; a "second" one is actually a different agent (the retry you dispatched) | One agent-id = one terminal notification; multiple notifications mean multiple agents |
| Reading transcript JSONL to "check progress" | Opened the subagent JSONL file to see what the agent was doing | The JSONL is forensic, not live status; reading it overflows the parent context and tells you nothing about whether the agent is still running | Use `ls -la` for mtime only; never `cat` the transcript from the parent |

## Results & Parameters

**Concrete data from the 4-agent ProjectHephaestus Part 2 swarm session (2026-05-25):**

| Agent | When dispatched | Final notification | duration_ms | Final result | All retries needed? |
| ------- | ----------------- | -------------------- | ------------- | --------------- | --------------------- |
| Site 1 original (`ac2c0882d3dfced16`) | 18:54 | ~19:54 | ~3,500,000 (58 min) | "No work to do — task is complete" (no-op detection) | No |
| Site 2 original (`a0dde4c525b4f292b`) | 18:54 | ~20:08 | ~4,500,000 (75 min) | "Issue #579 is already closed" (no-op detection) | No |
| Site 3 original (`a84bf4e3120662fbe`) | 18:54 | ~19:45 | ~3,000,000 (50 min) | PR #587 opened (real work) | No |
| Site 4 original (`a103b58740ca62f1e`) | 18:54 | ~19:15 | ~1,200,000 (20 min) | PR #584 opened (real work) | No |

All 4 originals were still running when their short status messages arrived. Three unnecessary retries were dispatched (Sites 1, 2, 4) which caused:

- 1 duplicate PR (#586) closed manually as a duplicate.
- 1 duplicate `TestImplLoopStrictRubric` test class that a retry agent had to deduplicate.
- 1 forced `-v2` branch suffix to dodge a branch-name collision.
- Wasted compute on 3 retry agents.

**Diagnostic table — still running vs. exited prematurely:**

| Indicator | Still running | Exited prematurely |
| ----------- | ----------------- | -------------------- |
| `status` field | `in_progress` | `completed` |
| `duration_ms` | growing over time | terminal, often < 60,000 for fast no-op but > 1,200,000 for wait-on-PR |
| `result` text | "waiting", "polling", "monitoring", "stand by" — no PR URL | "Done"/"Complete" with concrete PR URL, OR explicit "FATAL"/"exit 1"/"timed out" |
| Worktree state | locked + transcript file still being written | locked + transcript stops growing |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Part 2 multi-repo audit remediation swarm — 4 parallel Site agents dispatched to wait on a baseline PR; parent misread 3 status updates as completions and re-dispatched, causing PR #586 duplicate and `TestImplLoopStrictRubric` deduplication work | Session 2026-05-25, issue #588 |

## Related Skills

- [[multi-repo-pr-orchestration-swarm-pattern]] — established the parallel-direct-Agent pattern; this skill adds the anti-quit-early constraint that prevents duplicate dispatches from racing the originals.
- [[audit-driven-remediation-workflow]] — the v1.2.0 amendment adds cross-module duplication audit; this skill is the related "swarm process hygiene" lesson learned during that remediation.
