---
name: feature-dev-code-reviewer-cannot-execute-shell-commands
description: "The `feature-dev:code-reviewer` agent type has only read-only tools — it can analyze a PR but cannot post `gh pr review`. Use this skill to (1) choose the right agent type for tasks that need to write back, (2) structure prompts so analysis-only agents return parseable bodies the orchestrator can post, (3) avoid wasting agent tokens composing `gh` commands the agent cannot execute, (4) detect the failure signature (`I cannot run shell commands` / `Available tools: Read, WebFetch, ...`) when sub-agents report blockers, (5) decide between `general-purpose` (full toolset, can post) and `feature-dev:code-reviewer` (read-only, analysis only) for PR-review delegation."
category: tooling
date: 2026-05-31
version: "1.0.0"
user-invocable: false
tags:
  - agent-types
  - code-review
  - sub-agents
  - shell-access
  - gh-cli
  - tool-availability
  - read-only-agent
  - prompt-design
  - delegation
  - orchestrator-pattern
  - write-back
  - feature-dev
  - general-purpose
  - analysis-only
---

# Skill: feature-dev:code-reviewer Cannot Execute Shell Commands

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Document the discovery that the `feature-dev:code-reviewer` sub-agent type has a read-only toolset (Read, WebFetch, WebSearch, Grep, Glob, TaskStop) and therefore cannot execute `gh pr review`, `gh issue create`, or any shell command. Prevent the orchestrator from wasting tokens prompting analysis-only agents with action verbs. |
| **Outcome** | verified-local. Observed across 11 `feature-dev:code-reviewer` dispatches in a single session reviewing HomericIntelligence/AchaeanFleet Dependabot PRs. Every agent returned the same blocker verbatim: "I cannot run shell commands. Available tools: Read, WebFetch, WebSearch, Grep, Glob, TaskStop." The orchestrator had to post all 11 reviews itself, costing ~5 extra turns. Two prompt patterns now eliminate the waste. |
| **Verification** | verified-local (no CI gate exists to verify agent-toolset capabilities). |

## When to Use

Apply this skill when:

- You are about to delegate a PR review to a sub-agent and the workflow REQUIRES posting the review back to GitHub (write-back).
- You are choosing between `feature-dev:code-reviewer` and `general-purpose` agent types for a code-review task.
- A swarm of code-reviewer agents has returned long output strings containing `gh pr review ...` command templates instead of actually posting the reviews.
- Sub-agent output contains any of the detection signatures:
  - "I cannot run shell commands"
  - "I cannot execute shell commands"
  - "no Bash tool available"
  - "WebFetch is read-only"
  - "Available tools: Read, WebFetch, WebSearch, Grep, Glob, TaskStop"
  - "the command above is ready for an operator to run"
  - "the review body is composed below, ready for the orchestrator to post"
- You are writing prompts for multi-PR review swarms and need to decide whether the agent itself or the orchestrator owns the write step.
- You are about to instruct an agent to "post via `gh pr review ...`" — STOP and verify the agent has Bash first.

## Verified Workflow

### Quick Reference

**Decision rule**: Does the task require executing a shell command (gh, git, sed, etc.)?

| Need to write back? | Agent type | Prompt pattern |
|----|----|----|
| YES (post review, create issue, commit, push) | `general-purpose` | "Analyze the PR AND post the review with `gh pr review ...`" |
| NO (analysis only, orchestrator posts) | `feature-dev:code-reviewer` | "Return verdict + Markdown body ONLY. Do NOT include `gh` syntax." |

**Pattern A — Write-back with `general-purpose`** (recommended when the agent must post):

```text
Use general-purpose agent. Prompt:
"Review PR #N in repo OWNER/NAME. Analyze for correctness, security, and policy.
Then POST the review using:
  gh pr review N --repo OWNER/NAME --approve|--request-changes|--comment --body \"$BODY\"
Return the gh command exit code and the URL of the posted review."
```

**Pattern B — Analysis-only with `feature-dev:code-reviewer`** (when you want isolated read-only analysis and the orchestrator posts):

```text
Use feature-dev:code-reviewer agent. Prompt:
"Analyze PR #N in repo OWNER/NAME using Read/Grep/Glob/WebFetch only.
Return ONLY:
  VERDICT: APPROVE|REQUEST_CHANGES|COMMENT
  BODY:
  <markdown review body>
Do NOT include any `gh` command syntax in your output.
Do NOT attempt to execute shell commands — you do not have Bash."
```

Then the orchestrator wraps the body itself:

```bash
gh pr review "$N" --repo "$OWNER/$NAME" \
  "$([ "$VERDICT" = "APPROVE" ] && echo --approve || \
     [ "$VERDICT" = "REQUEST_CHANGES" ] && echo --request-changes || \
     echo --comment)" \
  --body "$BODY"
```

### Detailed Steps

1. **Before dispatching**: Identify whether the task requires write-back (post review, create issue, push commit) or analysis only.
2. **Inspect the agent type's toolset** before composing the prompt. The `feature-dev:code-reviewer` toolset is exactly: Read, WebFetch, WebSearch, Grep, Glob, TaskStop. The `general-purpose` toolset includes Bash, Edit, Write in addition to read tools.
3. **If write-back is required**: Use `general-purpose`. Prompt MUST include the explicit `gh` command for the agent to execute.
4. **If analysis-only is required**: Use `feature-dev:code-reviewer`. Prompt MUST forbid `gh` syntax in the output and MUST tell the agent it does not have Bash (this is faster than letting the agent discover it mid-task).
5. **Parse the agent's output**: For Pattern B, extract `VERDICT:` and `BODY:` deterministically. Reject outputs that contain `gh pr review` — the agent ignored the instruction.
6. **Post yourself**: For Pattern B, the orchestrator wraps the body in the appropriate `gh pr review` flag and runs it.
7. **Verify the post**: After running, confirm with `gh pr view N --repo OWNER/NAME --json reviews --jq '.reviews[-1]'` that the review actually landed.

### Related Skills

- `[[parallel-agent-swarm-dispatch-patterns]]` — covers the broader "know your agent's toolset before delegating an action verb" pattern, including model-tier routing and pre-dispatch re-grading. This skill is a specialization for the read-only-toolset trap.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Wave 1 (6 agents) | Prompted 6 `feature-dev:code-reviewer` agents with full `gh pr review N --repo HomericIntelligence/AchaeanFleet --approve --body "..."` command templates expecting the agent to execute them. | All 6 agents responded identically: "I cannot run shell commands. Available tools: Read, WebFetch, WebSearch, Grep, Glob, TaskStop. The review body is composed below, ready for the orchestrator to post." Each agent burned tokens composing the full `gh` command string verbatim in its output. | The `feature-dev:code-reviewer` type has NO Bash. Action-verb prompts (post, push, create) waste tokens. |
| Wave 2 (5 agents) | Same prompt pattern as Wave 1, dispatched in parallel to cover the remaining 5 Dependabot PRs. Did not change the prompt because Wave 1 results had not yet been parsed. | Same blocker, 5 more times. Orchestrator now had 11 review bodies to post manually. | Verify the toolset of one agent before fanning out to N. One probe call would have saved 10 wasted dispatches. |
| Naive fix: switch to `general-purpose` mid-stream | Considered re-dispatching all 11 PRs to `general-purpose` so the agent could post. | Would have re-paid the analysis cost (each agent reads the diff again). The analysis from Wave 1+2 was correct; only the posting step was missing. | When analysis already exists, just extract verdict + body and post yourself. Do not re-analyze. |
| Tell `feature-dev:code-reviewer` to "use Bash anyway" | Tested adding "you have Bash, use it" to the prompt. | The agent still reports "I do not have access to Bash." The toolset is enforced by the harness, not the prompt. | Prompt cannot grant tools the agent type does not have. Only the agent-type registration controls capability. |

## Results & Parameters

### Configuration

**Agent type capability matrix** (verified 2026-05-31):

| Agent type | Read | Grep | Glob | WebFetch | WebSearch | Bash | Edit | Write | TaskStop |
|---|---|---|---|---|---|---|---|---|---|
| `feature-dev:code-reviewer` | yes | yes | yes | yes | yes | NO | NO | NO | yes |
| `general-purpose` | yes | yes | yes | yes | yes | yes | yes | yes | yes |

**Pattern A — `general-purpose` prompt skeleton** (write-back):

```text
You are reviewing PR #<N> in <OWNER>/<NAME>.

Steps:
1. Fetch the PR diff: `gh pr diff <N> --repo <OWNER>/<NAME>`
2. Read changed files via Read tool.
3. Analyze for: correctness, security, KISS/YAGNI/DRY/SOLID, policy compliance.
4. Compose review body as Markdown.
5. Post via `gh pr review <N> --repo <OWNER>/<NAME> [--approve|--request-changes|--comment] --body "$BODY"`.
6. Verify with `gh pr view <N> --repo <OWNER>/<NAME> --json reviews --jq '.reviews[-1]'`.
7. Report: verdict, posted review URL, gh exit code.
```

**Pattern B — `feature-dev:code-reviewer` prompt skeleton** (analysis-only):

```text
You are an ANALYSIS-ONLY reviewer. You do NOT have Bash, Edit, or Write tools.
Your tools: Read, WebFetch, WebSearch, Grep, Glob, TaskStop.

Analyze PR #<N> in <OWNER>/<NAME>:
1. Use WebFetch on https://github.com/<OWNER>/<NAME>/pull/<N>.diff to read the diff.
2. Read changed files via Read on the local checkout if available.
3. Compose verdict + body.

Return EXACTLY this format, nothing else:

VERDICT: APPROVE
BODY:
<markdown review body here>

Rules:
- VERDICT must be one of: APPROVE, REQUEST_CHANGES, COMMENT.
- Do NOT include any `gh` command syntax in your output.
- Do NOT attempt to execute commands.
- Do NOT include shell scripts, the orchestrator will post.
```

### Orchestrator Post Snippet (Pattern B)

```bash
# Assuming agent output is in $AGENT_OUTPUT
VERDICT=$(printf '%s\n' "$AGENT_OUTPUT" | sed -n 's/^VERDICT: \(.*\)$/\1/p' | head -1)
BODY=$(printf '%s\n' "$AGENT_OUTPUT" | sed -n '/^BODY:$/,$p' | tail -n +2)

case "$VERDICT" in
  APPROVE)         FLAG=--approve ;;
  REQUEST_CHANGES) FLAG=--request-changes ;;
  COMMENT)         FLAG=--comment ;;
  *) echo "Bad verdict: $VERDICT" >&2; exit 1 ;;
esac

gh pr review "$N" --repo "$OWNER/$NAME" "$FLAG" --body "$BODY"
```

### Expected Output

For Pattern A success: the agent reports a posted review URL and exit code 0.
For Pattern B success: the agent returns VERDICT + BODY (no `gh` syntax), the orchestrator's `gh pr review` exits 0, and `gh pr view --json reviews` shows the new review at index -1.

### Detection Signatures (in agent output)

If any of these phrases appear in a sub-agent's response, the agent is read-only and the orchestrator MUST post:

- "I cannot run shell commands"
- "I cannot execute shell commands"
- "no Bash tool available"
- "Available tools: Read, WebFetch, WebSearch, Grep, Glob, TaskStop"
- "WebFetch is read-only"
- "the command above is ready for an operator to run"
- "the review body is composed below, ready for the orchestrator to post"

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/AchaeanFleet | 11 Dependabot PRs reviewed in a single session 2026-05-31; all 11 agents returned the read-only blocker; orchestrator posted all 11 reviews. | Discovery session — no notes file. |

## References

- Related skill: [parallel-agent-swarm-dispatch-patterns](parallel-agent-swarm-dispatch-patterns.md) — broader patterns for agent toolset verification and pre-dispatch checks.
- Claude Code sub-agent types documentation (per agent type, the registered toolset is fixed at registration; prompts cannot extend capability).
