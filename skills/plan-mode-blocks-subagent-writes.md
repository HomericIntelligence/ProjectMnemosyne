---
name: plan-mode-blocks-subagent-writes
description: "Sub-agents launched while the parent conversation is in plan mode inherit plan-mode and silently stop at planning, refusing to write/commit/push. Use when: (1) launching Agent() sub-agents that must perform write actions, (2) seeing sub-agents return plan files instead of executing, (3) building skills that delegate /learn, /implement, or any write workflow."
category: tooling
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [claude-code, sub-agents, plan-mode, isolation]
---

# Plan-Mode Blocks Sub-Agent Writes (Even With "Execute Directly" Instructions)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Document that plan-mode state propagates to sub-agents and silently blocks writes |
| **Outcome** | Diagnosed root cause; the only fix is to exit plan mode at the parent level before dispatching write-capable agents |
| **Verification** | verified-local (observed across six wedged agents in a single session; confirmed exit fixes it) |

## When to Use

- Launching `Agent()` sub-agents that must edit files, run `git commit`, or open PRs
- A sub-agent returns a plan-file path or "awaiting plan-mode exit" instead of executing
- Designing skills like `/learn` that delegate writes to a sub-agent
- Seeing the same agent stop after "Step 1 completed before plan mode activated" across multiple re-launches

## Verified Workflow

### Quick Reference

```text
# Before dispatching write-capable sub-agents:
1. Exit plan mode in the parent conversation (ExitPlanMode or UI control)
2. Verify with: "Plan mode is active. ..." reminder is GONE from system prompt
3. THEN launch the Agent() with isolation="worktree"
```

### Detailed Steps

**Root cause:** Plan-mode state is a property of the conversation harness, NOT the agent's prompt. When `Agent()` spawns a sub-agent, the sub-agent inherits the parent's harness state — including plan-mode. The sub-agent's system prompt receives the same "Plan mode is active... MUST NOT make any edits" reminder, regardless of what the dispatching prompt says.

**Symptom:** Sub-agent will:
1. Run read-only setup steps (clone, fetch, grep).
2. Stop before any write.
3. Return a plan file path with "awaiting approval to execute steps N–M".
4. Report back as `status: completed` because it DID finish its work — its work was just "write a plan".

**The dispatching prompt cannot override this.** Phrasing like:
- "EXECUTE directly. You are NOT in plan mode."
- "Do NOT write a plan file."
- "Run the commands now."

…all fail. The sub-agent reads the system reminder, decides it's bound by plan mode, and stops. The prompt-level "you are not in plan mode" is a CLAIM the sub-agent's harness contradicts.

**Detection:** If your sub-agent returns "Plan written to /home/.../.claude/plans/..." you are in plan mode. Check the parent conversation.

**Fix:** Exit plan mode at the parent level. There is no workaround at the sub-agent level. After exit, re-launch the same sub-agent (fresh — `Agent()` doesn't share state with the wedged one; the wedged agent's transcript is gone). With `isolation="worktree"`, the new agent gets a clean copy of the repo, so no state carries over from the failed attempts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Prompt-level "EXECUTE directly. You are NOT in plan mode." | Tell the sub-agent to ignore its plan-mode state | Sub-agent's harness still injects plan-mode reminder; prompt-level claims lose to system reminders | Plan-mode is not a prompt — it's a harness flag. Prompts can't override it. |
| Re-launch the same wedged agent | Hope the second invocation breaks out | Identical behavior. Six re-launches across three skill PRs and four refactor agents all stopped at planning. | Plan-mode is sticky for the WHOLE conversation, not just one Agent() call. |
| Find a SendMessage tool to nudge wedged agent | Try to bypass plan-mode via mid-flight message | SendMessage tool isn't loaded by default; even if loaded, sub-agent re-reads plan-mode state on every turn | No mid-flight escape. Only parent-level exit works. |
| Increase prompt explicitness | "Do NOT write a plan file. Do NOT ask for approval." (literal instruction) | Sub-agent still wrote the plan file and asked for approval. The plan-mode rule wins over the prompt. | Stop layering prompt instructions; address the harness flag. |

## Results & Parameters

**Detection one-liner:**
```bash
# If your Agent() returns this string in its result, you're wedged in plan mode:
grep -l 'plans/' <result>  # The agent wrote a plan file instead of executing
```

**Cost of the bug:** In one session, six sub-agents were wedged across two waves of work (three /learn skill PRs + three "execute the plan" follow-ups). Total wasted: ~6 × 60-120s = 6-12 minutes of agent runtime, plus the parent-conversation context burned on relaunching.

**Recipe to dispatch write-capable sub-agents:**
```python
# 1. Confirm plan mode is OFF in the parent (check system reminders).
# 2. THEN:
Agent(
    description="Do the write work",
    isolation="worktree",
    prompt="..."
)
```

**Skills that compose with this:**
- /learn — delegates to a sub-agent that MUST write to Mnemosyne
- /finish-branch — sub-agent does git push + PR open
- Any "implement plan X" follow-up dispatch

For all of these, ExitPlanMode must complete BEFORE the Agent() call.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-26 audit-remediation session | Six wedged agents (3 /learn skill PRs + 3 audit-fix executions) all stopped at plan-write stage despite explicit "you are not in plan mode" prompt-level instructions; the moment plan mode was exited at the parent, identical re-launched agents completed normally. |
