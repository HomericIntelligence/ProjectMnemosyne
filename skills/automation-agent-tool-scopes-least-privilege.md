---
name: automation-agent-tool-scopes-least-privilege
description: "Enforce least-privilege tool scopes for headless agent invocations via a central per-role policy map resolved at the single invocation chokepoint, failing closed to read-only for unknown roles, with parametrized policy-lock tests. Use when: (1) an automation pipeline invokes `claude -p` (or another agent CLI) without explicit `--allowedTools` / `--permission-mode`, so every agent role inherits the default unrestricted tool surface; (2) per-role scopes exist but are copy-pasted string literals scattered across call sites and have started to drift; (3) adding a new agent role (planner, reviewer, implementer, CI driver) and deciding which tools it minimally needs; (4) a security review flags that read-only roles (reviewers, classifiers) can write or execute; (5) writing tests that lock a tool-scope policy so a permissive scope cannot be added silently."
category: architecture
date: 2026-07-17
version: "1.0.0"
user-invocable: false
tags:
  - automation
  - least-privilege
  - allowed-tools
  - permission-mode
  - tool-scope
  - security
  - fail-closed
  - chokepoint
  - policy-map
  - claude-cli
  - worker-pool
  - agent-roles
  - policy-lock-tests
---

# Automation Agent Tool Scopes: Least Privilege via a Central Fail-Closed Policy Map

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-17 |
| **Objective** | Stop headless pipeline agents from running with the CLI's default unrestricted tool surface: define one per-role scope policy, apply it at the single invocation chokepoint, and fail closed for unknown roles. |
| **Outcome** | Success — per-role scopes are production-verified in Hephaestus legacy phase modules; the central policy-map consolidation is the reviewed plan for Hephaestus issue #2160 (worker-pool chokepoint omitted both flags entirely). |
| **Verification** | verified-production (per-role scope values run in the live Hephaestus automation loop); chokepoint consolidation verified by plan review for issue #2160 |

## When to Use

- A pipeline/worker pool calls `invoke_claude_with_session(...)` (or `claude -p` directly)
  without `allowed_tools` / `permission_mode`, so reviewers and classifiers get write+exec
  by default.
- Per-role scope strings are duplicated at many call sites and reviewers cannot tell which
  role grants what.
- You are adding a new agent role and must choose its minimal tool set.
- A security audit asks "can the read-only reviewer write files or run commands?" and the
  answer requires grepping N call sites.
- You need tests that make widening a scope a visible, reviewed diff instead of a silent
  string edit.

## Verified Workflow

### Quick Reference

Production-verified per-role scopes (Hephaestus automation loop):

| Role | `--allowedTools` | `--permission-mode` |
| ------ | ------------------ | --------------------- |
| Plan reviewer / PR reviewer / comment classifier | `Read,Glob,Grep` | `dontAsk` |
| Planner (explores repo, writes nothing) | `Read,Glob,Grep,Bash` | `dontAsk` |
| Implementer / CI-fix driver | `Read,Write,Edit,Glob,Grep,Bash` | `dontAsk` |
| Review addresser (runs skills/subagents) | `Read,Write,Edit,Glob,Grep,Bash,Task,Skill` | `dontAsk` |
| Knowledge-base advise turn | `Read,Glob,Grep,Bash,Skill,Task` | `dontAsk` |
| Unknown / unmapped role (fail closed) | `Read,Glob,Grep` | `dontAsk` |

### Detailed Steps

1. **Find the chokepoint, not the call sites.** Count how many job/stage constructors funnel
   into one CLI invocation. In Hephaestus, 17 `AgentJob` sites across 6 stage modules all
   reach one `invoke_claude_with_session` call in the worker pool, keyed by an existing
   role constant (`session_agent`). Add the policy at that one call; do not add two fields
   to every job dataclass and edit every constructor.
2. **Define the policy as data in its own module** (frozen dataclass + `MappingProxyType`)
   keyed by the role constants that already exist:

   ```python
   @dataclass(frozen=True)
   class ToolScope:
       allowed_tools: str
       permission_mode: str = "dontAsk"

   DEFAULT_TOOL_SCOPE = ToolScope("Read,Glob,Grep")  # fail closed

   AGENT_TOOL_SCOPES: Mapping[str, ToolScope] = MappingProxyType({
       AGENT_PR_REVIEWER: ToolScope("Read,Glob,Grep"),
       AGENT_IMPLEMENTER: ToolScope("Read,Write,Edit,Glob,Grep,Bash"),
       # ... one entry per role constant actually used by stages
   })

   def tool_scope_for(agent: str) -> ToolScope:
       scope = AGENT_TOOL_SCOPES.get(agent)
       if scope is None:
           logger.warning("no tool scope for agent %r; using read-only default", agent)
           return DEFAULT_TOOL_SCOPE
       return scope
   ```

3. **Fail closed, never open.** An unmapped role must degrade to the most restrictive
   scope (read-only) with a warning log — a security control that defaults to permissive
   is not a control. This also transparently covers roles added later.
4. **Mirror scope values from already-trusted code, not from intuition.** Grep the codebase
   for existing `allowed_tools=` literals; the legacy per-phase modules encode what each
   role actually needs in production. Copy those values into the map, then delete-by-
   consolidation over time.
5. **Thread the scope through the chokepoint** and pass both flags explicitly on every
   invocation (`allowed_tools=scope.allowed_tools, permission_mode=scope.permission_mode`).
6. **Lock the policy with parametrized tests** so widening a scope is a reviewed diff:
   - every role constant used by stages has a map entry;
   - reviewer/classifier scopes are exactly `{Read, Glob, Grep}` (no Write/Edit/Bash);
   - unknown role resolves to the read-only default (identity check);
   - `permission_mode == "dontAsk"` for every entry;
   - the map itself is immutable (`pytest.raises(TypeError)` on item assignment).
   Plus one mock-based test at the chokepoint asserting the CLI wrapper received the
   expected `allowed_tools` / `permission_mode` kwargs per role.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Attempt 1 | Rely on the agent CLI's defaults for headless pipeline calls | Every role — including read-only reviewers — ran with the full default tool surface; flagged as a MAJOR security finding (Hephaestus #2160) | Headless automation must pass explicit `--allowedTools` and `--permission-mode` on every call; defaults are for interactive use |
| Attempt 2 | Copy-paste per-role scope strings at each call site (legacy pattern across 12+ modules) | Values drifted and new call sites (the pipeline worker pool) simply omitted them; nothing enforced coverage | Cross-cutting policy belongs in one data module resolved at the invocation chokepoint, with tests that fail when a role is unmapped |
| Attempt 3 | Consider adding `allowed_tools`/`permission_mode` fields to the job dataclass with permissive defaults | 17 construction sites to edit; a defaulted field lets new sites silently inherit write scope | Key the policy on the existing role constant and fail closed to read-only instead of defaulting open |

## Results & Parameters

### Configuration

```python
# Read-only trio for anything that only inspects the repo
_READ_ONLY = "Read,Glob,Grep"
# Explorer roles that grep/inspect via shell but must not edit
_READ_EXPLORE = "Read,Glob,Grep,Bash"
# Writer roles (implementer, CI fixer)
_WRITE = "Read,Write,Edit,Glob,Grep,Bash"
# Skill-running roles append ",Task,Skill" explicitly
```

### Expected Output

- Every headless agent invocation carries explicit `--allowedTools` and
  `--permission-mode dontAsk`; no call site relies on CLI defaults.
- `pytest -k tool_scopes` locks: full role coverage, read-only reviewers, fail-closed
  default, immutable map.
- A chokepoint unit test (mocked CLI wrapper) proves the kwargs actually reach the
  subprocess layer per role.
- Widening any scope requires editing the policy module and its test — a visible diff.

## Verified On

- Hephaestus automation loop (legacy per-phase modules `_implement_phase`,
  `pr_review_core`, `address_review_core`, `ci_fix_orchestrator`,
  `comment_difficulty`, `plan_reviewer`) — scope values in production.
- Hephaestus issue #2160 — reviewed implementation plan consolidating the values into
  `hephaestus/automation/pipeline/tool_scopes.py` at the worker-pool chokepoint.
