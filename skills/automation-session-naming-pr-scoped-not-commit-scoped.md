---
name: automation-session-naming-pr-scoped-not-commit-scoped
description: "When an automation loop drives a long-lived artifact (issue / PR) with short-lived Claude sessions via `claude --resume <session_id>`, the deterministic session id MUST be scoped to the artifact, not to the live trunk commit. Silent session recreation has two independent causes: (1) id-scope drift — tuple includes `githash` so every main-bump mints a new UUID the wrapper cannot resume; (2) cwd mismatch — `invoke_claude_with_session` determines create-vs-resume by checking `transcript = session_jsonl_path(sid, cwd); should_resume = transcript.exists()`, so if turn 1 and turn 2 use different `cwd` values the transcript resolves to a non-existent path and the second turn silently creates a fresh session. Fix (1): drop `githash` from the session-name tuple. Fix (2): all turns in a multi-turn session MUST pass the same `cwd`. Also covers: advise-as-first-implementer-turn two-turn pattern; marketplace-path relativization bug when `cwd=worktree_path`. Use when: session resume silently fails, an agent starts fresh each iteration, implementing multi-turn session patterns with advise + implementation turns."
category: architecture
date: 2026-06-08
version: "1.1.0"
user-invocable: false
history: automation-session-naming-pr-scoped-not-commit-scoped.history
tags:
  - automation
  - claude-session
  - session-resume
  - session-id
  - deterministic-uuid
  - invoke-claude-with-session
  - architecture
  - regression-test
  - static-analyzer
  - github-code-quality
  - kwargs-unpacking
  - session-scope
  - cwd-invariant
  - multi-turn-session
  - advise-as-first-turn
  - worktree-path
  - path-relativization
---

# Automation Session Naming: Scope to the PR, Not the Commit

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-08 |
| **Objective** | Fix two independent causes of silent session recreation in the automation loop: (1) session id that drifts with every main-bump, (2) `cwd` mismatch between turns of the same multi-turn session. Also documents the two-turn advise-as-implementer-turn pattern and its path-relativization hazard. |
| **Outcome** | Success — (1) PR #845 removed `githash` from session tuples; (2) PR #1100 fixed cwd invariant, advise-as-first-turn architecture, and marketplace-path relativization bug. All 1303 tests pass. |
| **Verification** | verified-precommit |
| **History** | [changelog](./automation-session-naming-pr-scoped-not-commit-scoped.history) |

## When to Use

Use this skill when any of the following apply:

- You are **building or modifying an automation loop** that resumes Claude sessions across runs via `claude --resume <session_id>` (typically wrapped as `invoke_claude_with_session`).
- A long-lived artifact (a GitHub **issue** or **PR**) is being worked on by **short-lived agent sessions** that need to share context across many iterations.
- **Session resume is silently failing**: the agent starts fresh each iteration, losing prior context. Check BOTH causes: id-scope drift AND cwd mismatch.
- You see `session_name(...)` or `session_uuid(...)` whose tuple includes the **live trunk SHA** (`current_trunk_githash(repo_root)`), `git rev-parse HEAD`, or any other rapidly-changing identifier alongside the artifact's identity.
- You need to **pin a "argument removed from signature" invariant** with a regression test, but a static analyzer (github-code-quality, mypy, ruff, pyright) flags your intentional bad call as "Wrong name for an argument".
- You are auditing the call graph of an automation pipeline and notice **only some** of the agent invocation sites pass a `githash` (any subset is wrong — a partial removal forks the session family at the boundary between updated and not-updated callers).
- You are implementing a **two-turn session pattern** where turn 1 is an advise/context-gathering step and turn 2 is the main implementation, and you want both to share the same transcript.
- A **path-relativization helper** is called with `repo_root` but the session runs with `cwd=worktree_path` — paths outside the worktree become incorrect relative paths.

## Verified Workflow

> **Note (Partially Verified):** The id-scope sections (Fix 1) are `verified-ci` (PR #845). The cwd invariant, two-turn pattern, and path-relativization sections (Fixes 2–3) are `verified-precommit` — pre-commit hooks pass and 1303 tests are green locally; CI validation is pending for those additions.

### Quick Reference

```python
# ── Cause 1: Id-scope drift ──────────────────────────────────────────────────
# Session id MUST be scoped to the artifact, not the commit.
# Before (BUG):
def session_uuid(repo, issue, agent, githash): ...  # new UUID every main-bump

# After (FIX):
def session_uuid(repo, issue, agent): ...            # stable across main-bumps

# ── Cause 2: cwd mismatch ─────────────────────────────────────────────────────
# CRITICAL INVARIANT: all turns of a multi-turn session MUST use the same cwd.
# invoke_claude_with_session logic:
#   transcript = session_jsonl_path(sid, cwd)   # on-disk path depends on cwd
#   should_resume = transcript.exists()
# If turn 1 uses cwd=worktree_path and turn 2 uses cwd=repo_root,
# the transcript resolves to a different (nonexistent) path → should_resume=False
# → turn 2 silently creates a new session, losing the advise context.

# ── Two-turn advise-as-implementer-turn pattern ───────────────────────────────
# Turn 1 (advise): first turn of AGENT_IMPLEMENTER session, cwd=worktree_path
invoke_claude_with_session(
    repo=repo, issue=issue, agent=AGENT_IMPLEMENTER,
    prompt=advise_prompt,    # includes plan + plan-review fetched from GitHub
    cwd=worktree_path,       # CRITICAL: same cwd as turn 2
)
# Turn 2 (implementation): auto-resumed because transcript already exists
invoke_claude_with_session(
    repo=repo, issue=issue, agent=AGENT_IMPLEMENTER,
    prompt=implementation_prompt,
    cwd=worktree_path,       # CRITICAL: same cwd as turn 1
)
# invoke_claude_with_session detects transcript.exists() → uses --resume automatically

# ── Codex guard ───────────────────────────────────────────────────────────────
# Codex has no multi-turn session support. Use is_codex() to preserve old path:
if is_codex():
    advise_text = run_advise_session(...)   # separate AGENT_ADVISE session
    full_prompt = advise_text + "\n\n" + implementation_prompt
    invoke_claude_with_session(..., prompt=full_prompt, cwd=worktree_path)
else:
    # Two-turn path (turn 1: advise, turn 2: implementation)
    ...

# ── Marketplace path relativization ───────────────────────────────────────────
# get_advise_prompt(repo_root=...) internally calls _relativize_path(marketplace_path, repo_root).
# If repo_root == str(worktree_path), paths OUTSIDE the worktree (e.g. build/Mnemosyne/...)
# cannot be relativized and fall back to absolute paths → correct.
# If repo_root == str(actual_repo_root), paths ARE relativized → resolve incorrectly
# when Claude runs with cwd=worktree_path (worktree is at <repo_root>/build/.worktrees/issue-N).
# FIX: pass repo_root=str(worktree_path) to get_advise_prompt when cwd=worktree_path.
advise_prompt = get_advise_prompt(
    ...,
    repo_root=str(worktree_path),   # not str(repo_root)!
)
```

### Detailed Steps

#### Fix 1: Drop `githash` from session id tuple

1. **Recognize the failure mode.** Symptom: agents act "amnesiac" — each iteration re-asks for context. Transcripts named `<repo>_<issue>_<agent>_<sha1>`, `<repo>_<issue>_<agent>_<sha2>` etc. The wrapper logs show `--session-id` (create) when you expected `--resume`. Root cause: id includes live trunk SHA.

2. **Drop `githash` from `session_name`, `session_uuid`, and `invoke_claude_with_session`.**

   ```python
   # hephaestus/automation/<session_helpers>.py
   def session_name(repo: str, issue: int | str, agent: str) -> str:
       return f"{repo_s}_{issue_s}_{agent_s}"

   def session_uuid(repo: str, issue: int | str, agent: str) -> str:
       return str(uuid.uuid5(uuid.NAMESPACE_DNS, session_name(repo, issue, agent)))
   ```

3. **Walk every caller — all 8 sites in one PR.** (planner, plan_reviewer, implementer, address_review, pr_reviewer, ci_driver). Any partial removal forks the session family.

   ```bash
   rg -n 'session_uuid|session_name|invoke_claude_with_session' hephaestus/ tests/
   rg -n 'current_trunk_githash\(' hephaestus/automation/ tests/
   ```

4. **Pin the invariant with a `**kwargs`-unpacked regression test.**

   ```python
   bad_kwargs = {"githash": "abc1234"}
   with pytest.raises(TypeError):
       session_uuid("R", 1, AGENT_PLANNER, **bad_kwargs)
   ```

#### Fix 2: Enforce cwd invariant for multi-turn sessions

1. **Understand how create-vs-resume is decided.** `invoke_claude_with_session` does:
   ```python
   transcript = session_jsonl_path(sid, cwd)
   should_resume = transcript.exists()
   ```
   Both the session id AND the `cwd` determine the on-disk transcript path. If `cwd` differs between turns, `session_jsonl_path(same_sid, different_cwd)` → different path → `exists()` is False → create instead of resume.

2. **Always pass the same `cwd` for all turns of the same session.** For implementer sessions processing a PR in a worktree, `cwd=worktree_path` is the right choice because (a) the worktree is where the code lives, and (b) the absolute path is stable.

3. **Add `is_codex()` guard for Codex compatibility.** Codex does not support multi-turn sessions. When `is_codex()` is True, use the old AGENT_ADVISE + text-injection path (run advise in a separate session, prepend the text to the implementation prompt).

#### Fix 3: Correct `repo_root` for path-relativization helpers

1. **Understand the relativization logic.** `get_advise_prompt` calls `_relativize_path(marketplace_path, repo_root)` to make the marketplace path relative (so Claude can navigate to it). If `repo_root=worktree_path` and the marketplace is at `<repo_root>/build/Mnemosyne/.claude-plugin/marketplace.json`, the marketplace is NOT under `worktree_path` (worktrees are at `<repo_root>/build/.worktrees/issue-N`), so `_relativize_path` fails to relativize and returns the absolute path — which is correct.

2. **The bug**: if you pass `repo_root=str(actual_repo_root)`, the marketplace IS under `repo_root`, so it relativizes to `build/Mnemosyne/...` — a relative path that only resolves from `repo_root`, not from `worktree_path`. Since Claude runs with `cwd=worktree_path`, this path breaks.

3. **Fix**: always pass `repo_root=str(worktree_path)` (not `str(repo_root)`) when calling `get_advise_prompt` in a worktree context.

### Bounding the Staleness Risk

Long-lived sessions can carry stale assumptions across rebases. Three guards keep this risk bounded:

- The `session_jsonl_path` dot-encoding fix (separate earlier PR) that made `--resume` reliable.
- A worktree pre-sync that resets HEAD to the actual PR head before each iteration (`sync_worktree_to_remote_branch`).
- A HEAD-didn't-advance guard that snapshots pre/post agent run and reports a no-op session honestly.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Derived the deterministic session id from the live trunk SHA: `session_name(repo, issue, agent, githash)` | Every `_drive_issue` call on a freshly-bumped main produced a new UUID. `invoke_claude_with_session` fell back to `--session-id` (create). Agents acted amnesiac. | Scope the session id to the lifetime of the **artifact** (issue + PR). Drop `githash` from the tuple and update **every** caller in one PR. |
| 2 | Pinned the regression with `session_uuid("R", 1, AGENT_PLANNER, githash="abc1234")` in a `pytest.raises` block with `# type: ignore[call-arg]` | github-code-quality's static analyzer resolved the name back to the new signature and reported "Wrong name for an argument in a call" on every PR that touched the file. | Use `bad_kwargs = {"githash": "abc1234"}; session_uuid(**bad_kwargs)` — runtime behavior identical, static analyzer cannot resolve the key. |
| 3 | Used `cwd=repo_root` for turn 2 (implementation) while turn 1 (advise) used `cwd=worktree_path` | `session_jsonl_path(sid, repo_root)` resolved to a different on-disk path than `session_jsonl_path(sid, worktree_path)`. The transcript from turn 1 did not exist at the turn 2 path → `should_resume=False` → new session created, advise context lost. | All turns of the same multi-turn session MUST use the same `cwd`. Use `cwd=worktree_path` for both advise and implementation turns when the session runs in a worktree context. |
| 4 | Passed `repo_root=str(actual_repo_root)` to `get_advise_prompt` when `cwd=worktree_path` | `_relativize_path(marketplace_path, actual_repo_root)` relativized the marketplace path to `build/Mnemosyne/...`. With `cwd=worktree_path`, this relative path resolves to `<worktree>/build/Mnemosyne/...` which does not exist. | Pass `repo_root=str(worktree_path)` so the marketplace path (which lives under actual repo_root, not the worktree) cannot be relativized and falls back to its absolute path. |

## Results & Parameters

### cwd invariant — how `invoke_claude_with_session` decides create-vs-resume

```python
# Pseudocode of the decision logic:
sid = session_uuid(repo, issue, agent)
transcript = session_jsonl_path(sid, cwd)   # path depends on BOTH sid AND cwd
should_resume = transcript.exists()

if should_resume:
    cmd = ["claude", "--resume", str(transcript)]
else:
    cmd = ["claude", "--session-id", sid, "--cwd", str(cwd)]
```

**Critical invariant**: `cwd` must be identical across all turns. A single mismatch silently creates a new session.

### Two-turn advise-as-implementer-turn diff shape

```text
hephaestus/automation/implementer_phase_runner.py
  + def _run_advise_as_implementer_turn(self, ...):
  |     # Turn 1: advise as first turn of AGENT_IMPLEMENTER session
  |     advise_prompt = get_advise_prompt(..., repo_root=str(worktree_path))
  |     invoke_claude_with_session(
  |         repo=repo, issue=issue, agent=AGENT_IMPLEMENTER,
  |         prompt=advise_prompt, cwd=worktree_path,
  |     )
  |
  |     # Turn 2: implementation (auto-resumed — transcript already exists)
  |     invoke_claude_with_session(
  |         repo=repo, issue=issue, agent=AGENT_IMPLEMENTER,
  |         prompt=implementation_prompt, cwd=worktree_path,
  |     )

hephaestus/automation/implementer.py
  + def _run_advise_as_implementer_turn(self, ...):
  |     # Delegating wrapper — required for test-patch compatibility
  |     return self.phase_runner._run_advise_as_implementer_turn(...)

hephaestus/automation/advise_runner.py
  # doc update only

hephaestus/automation/learn.py
  # model= parameter added (separate fix — see tooling-hephaestus-implementer-no-changes-state-skip)
```

### Codex guard

```python
# is_codex() is True when running under the Codex environment (no multi-turn support).
if is_codex():
    # Old path: run advise in a separate session, inject as preamble
    advise_text = _run_separate_advise_session(...)
    invoke_claude_with_session(
        ..., prompt=advise_text + "\n\n" + impl_prompt, cwd=worktree_path
    )
else:
    # New path: two-turn session
    _run_advise_as_implementer_turn(...)
```

### Id-scope diff shape (Fix 1, PR #845)

```text
hephaestus/automation/<session_helpers>.py
  - def session_name(repo, issue, agent, githash) -> str
  + def session_name(repo, issue, agent) -> str
  - def session_uuid(repo, issue, agent, githash) -> str
  + def session_uuid(repo, issue, agent) -> str

hephaestus/automation/<wrapper>.py
  - def invoke_claude_with_session(..., githash, ...)
  + def invoke_claude_with_session(...)

# 8 call sites: planner, plan_reviewer, implementer, address_review, pr_reviewer, ci_driver
# At each: remove `githash = current_trunk_githash(...)` and `githash=githash` kwarg
```

### Verification metrics (PR #1100)

- 1303 unit tests pass
- mypy clean
- ruff clean
- pre-commit hooks pass
- PR #1100 merged (HomericIntelligence/ProjectHephaestus)

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #845 closes #841 — session-naming fix (id-scope) | `session_name` and `session_uuid` lost `githash`; `invoke_claude_with_session` lost the matching kwarg; 8 callers updated in lockstep. Regression test uses `**bad_kwargs` unpacking. PR merged via CI. |
| ProjectHephaestus | PR #1100 — advise session isolation + cwd invariant + marketplace-path fix | Two-turn advise-as-implementer-turn pattern; cwd=worktree_path enforced for both turns; `repo_root=str(worktree_path)` passed to `get_advise_prompt`; Codex guard preserved. 1303 tests pass; pre-commit hooks clean. |
