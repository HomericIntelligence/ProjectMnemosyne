---
name: automation-session-naming-pr-scoped-not-commit-scoped
description: "When an automation loop drives a long-lived artifact (issue / PR) with short-lived Claude sessions via `claude --resume <session_id>`, the deterministic session id MUST be scoped to the artifact, not to the live trunk commit. Tuple-scoping the id as `(repo, issue, agent, githash)` produces a new UUID on every main-bump and silently fragments transcripts: `invoke_claude_with_session` cannot `--resume` an id it never minted, so it falls back to `--session-id` (create) and the agent starts from scratch every iteration. Fix: drop `githash` from the session-name and session-uuid tuples (`session_name(repo, issue, agent)`, `session_uuid(repo, issue, agent)`), drop the matching kwarg from `invoke_claude_with_session`, and walk EVERY caller (typical sites: planner, plan_reviewer, implementer, address_review, pr_reviewer, ci_driver — 8 in this repo). Pin the regression with a `**kwargs`-unpacked TypeError test so static analyzers (github-code-quality, mypy, ruff) don't flag the intentional bad kwarg. Use when: building automation that resumes Claude sessions across runs, session resume is silently failing because the deterministic id drifts, a long-lived artifact is being worked on by short-lived sessions, or pinning a removed-argument invariant against a static analyzer that resolves names."
category: architecture
date: 2026-05-31
version: "1.0.0"
user-invocable: false
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
---

# Automation Session Naming: Scope to the PR, Not the Commit

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-31 |
| **Objective** | Stop the automation loop from creating a new Claude session every time main is bumped — scope the deterministic session id to the artifact (issue/PR) that persists across iterations, not to the live trunk commit that does not. |
| **Outcome** | Success — removed `githash` from `session_name` / `session_uuid` / `invoke_claude_with_session`, updated all 8 callers (planner, plan_reviewer, implementer, address_review, pr_reviewer, ci_driver), pinned the invariant with a `**kwargs`-unpacked TypeError regression test that github-code-quality cannot statically resolve. PR #845 (rebased successor of conflict-closed #843) closes #841 and merged via CI. |
| **Verification** | verified-ci |

## When to Use

Use this skill when any of the following apply:

- You are **building or modifying an automation loop** that resumes Claude sessions across runs via `claude --resume <session_id>` (typically wrapped as `invoke_claude_with_session`).
- A long-lived artifact (a GitHub **issue** or **PR**) is being worked on by **short-lived agent sessions** that need to share context across many iterations.
- **Session resume is silently failing**: the deterministic id changes across runs so `--resume` cannot find a transcript, and the wrapper falls back to `--session-id` (create) — every iteration starts fresh and the agent loses prior context.
- You see `session_name(...)` or `session_uuid(...)` whose tuple includes the **live trunk SHA** (`current_trunk_githash(repo_root)`), `git rev-parse HEAD`, or any other rapidly-changing identifier alongside the artifact's identity.
- You need to **pin a "argument removed from signature" invariant** with a regression test, but a static analyzer (github-code-quality, mypy, ruff, pyright) flags your intentional bad call as "Wrong name for an argument".
- You are auditing the call graph of an automation pipeline and notice **only some** of the agent invocation sites pass a `githash` (any subset is wrong — a partial removal forks the session family at the boundary between updated and not-updated callers).

## Verified Workflow

### Quick Reference

```python
# Session id MUST be scoped to the artifact, not the commit.
# The artifact (issue, PR) persists across many main-bumps; the session should too.

# Before (BUG):
def session_name(repo: str, issue: int | str, agent: str, githash: str) -> str:
    return f"{repo_s}_{issue_s}_{agent}_{githash_s}"

def session_uuid(repo: str, issue: int | str, agent: str, githash: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, session_name(repo, issue, agent, githash)))

# After (FIX):
def session_name(repo: str, issue: int | str, agent: str) -> str:
    return f"{repo_s}_{issue_s}_{agent}"

def session_uuid(repo: str, issue: int | str, agent: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, session_name(repo, issue, agent)))
```

```python
# Regression test — uses **dict unpacking so static analyzers can't resolve
# the intentional bad kwarg to the new signature.

bad_kwargs = {"githash": "abc1234"}

with pytest.raises(TypeError):
    session_uuid("R", 1, AGENT_PLANNER, **bad_kwargs)
with pytest.raises(TypeError):
    session_name("R", 1, AGENT_PLANNER, **bad_kwargs)
```

### Detailed Steps

1. **Recognize the failure mode.** Symptom: the automation loop's agents act
   "amnesiac" — each iteration on the same issue/PR re-asks for context, repeats
   work, or contradicts decisions from earlier iterations on the same artifact.
   The transcripts on disk look like a *family* of unrelated sessions named
   `<repo>_<issue>_<agent>_<sha1>`, `<repo>_<issue>_<agent>_<sha2>`, ... one
   per main-bump. The wrapper logs show `--session-id` (create) when you expected
   `--resume`. Root cause: the deterministic id includes a live trunk SHA, so
   every main-bump mints a new id that `--resume` cannot match.

2. **Identify the artifact's true lifetime.** Ask: "What is the thing this
   pipeline is working on, and how long does it live?" In an issue/PR-driven
   automation loop the answer is the **issue + PR pair**, and it persists
   across dozens of main-bumps. The session id must be scoped to that
   lifetime — typically `(repo, issue, agent)`. The current trunk SHA is the
   wrong scope because it changes faster than the artifact.

3. **Audit every call site.** Grep the repo for callers of the session helpers
   and the wrapper. In ProjectHephaestus there are **8 sites** across the
   automation loop: planner, plan_reviewer, implementer, address_review,
   pr_reviewer, ci_driver. **Any subset is wrong** — partial removal forks the
   session family at the boundary between updated and not-updated callers.

   ```bash
   # Find every place that derives a session id from githash.
   rg -n 'session_uuid|session_name|invoke_claude_with_session' hephaestus/ tests/
   rg -n 'current_trunk_githash\(' hephaestus/automation/ tests/
   ```

4. **Drop `githash` from the tuple — everywhere — in one PR.**

   ```python
   # hephaestus/automation/<session_helpers>.py
   def session_name(repo: str, issue: int | str, agent: str) -> str:
       repo_s = str(repo).strip()
       issue_s = str(issue).strip()
       agent_s = str(agent).strip()
       return f"{repo_s}_{issue_s}_{agent_s}"

   def session_uuid(repo: str, issue: int | str, agent: str) -> str:
       return str(uuid.uuid5(uuid.NAMESPACE_DNS, session_name(repo, issue, agent)))
   ```

   Update `invoke_claude_with_session` to drop the `githash` kwarg:

   ```python
   def invoke_claude_with_session(
       *,
       repo: str,
       issue: int | str,
       agent: str,
       prompt: str,
       # NO githash kwarg
       ...
   ) -> ClaudeResult:
       sid = session_uuid(repo, issue, agent)
       # Try --resume first, fall back to --session-id (create) only if no transcript exists.
       ...
   ```

   Then walk every caller and **delete both lines** — the local
   `githash = current_trunk_githash(self.repo_root)` and the
   `githash=githash,` kwarg. Do this for all 8 sites in one PR so the session
   family is not forked. Leave `current_trunk_githash` itself in place — other
   callers (state files, log lines, audit trails) still legitimately use it.

5. **Pin the invariant with a `**kwargs`-unpacked regression test.** The naive
   write fails github-code-quality's static analyzer, which resolves the name
   back to the new signature and reports "Wrong name for an argument in a
   call". Intent ("test asserts the kwarg is bad") and signal ("call uses bad
   kwarg") are indistinguishable to a name-resolver, so the bot will keep
   flagging the test on every PR that touches the file.

   ```python
   # BAD — flagged by static analyzer as wrong arg name
   with pytest.raises(TypeError):
       session_uuid("R", 1, AGENT_PLANNER, githash="abc1234")  # type: ignore[call-arg]
   ```

   Make the kwarg invisible to static analysis by unpacking through a dict:

   ```python
   # GOOD — runtime behavior identical (still raises TypeError),
   # but the static analyzer has no fixed name to resolve.
   bad_kwargs = {"githash": "abc1234"}

   with pytest.raises(TypeError):
       session_uuid("R", 1, AGENT_PLANNER, **bad_kwargs)
   with pytest.raises(TypeError):
       session_name("R", 1, AGENT_PLANNER, **bad_kwargs)
   ```

6. **Verify resume actually works in the green path.** Add a positive test
   that two calls with the same `(repo, issue, agent)` produce the same UUID
   regardless of any concurrent trunk advance:

   ```python
   def test_session_uuid_is_stable_across_trunk_bumps(monkeypatch):
       a = session_uuid("R", 1, AGENT_PLANNER)
       # Trunk advances mid-run — should not affect the id.
       monkeypatch.setattr(<...>, "current_trunk_githash", lambda _: "deadbeef")
       b = session_uuid("R", 1, AGENT_PLANNER)
       assert a == b
   ```

7. **Bound the staleness risk.** Long-lived sessions can carry stale
   assumptions across rebases ("I already fixed this," when the file was
   force-pushed away). Three guards land alongside or before this change to
   keep that risk bounded:

   - The `session_jsonl_path` dot-encoding fix that made `--resume` reliable
     in the first place (separate earlier PR).
   - A worktree pre-sync that resets HEAD to the actual PR head before each
     iteration (e.g. `sync_worktree_to_remote_branch`).
   - A HEAD-didn't-advance guard that snapshots pre/post agent run and
     reports a no-op session honestly instead of silently pushing nothing.

   Together these turn "stale context" from a correctness risk into "more
   context than the current state, occasionally" — the desired property.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Derived the deterministic session id from the live trunk SHA: `session_name(repo, issue, agent, githash)` and `session_uuid(repo, issue, agent, githash)`, both reading `current_trunk_githash(self.repo_root)` at call time. | Every `_drive_issue` call on a freshly-bumped main produced a new UUID. `invoke_claude_with_session` could not `--resume` an id it had never minted, so it fell back to `--session-id` (create) and started a fresh transcript every iteration. Transcripts fragmented into a family of unrelated sessions on the same PR; agents acted amnesiac across main-bumps. | Scope the session id to the lifetime of the **artifact** (issue + PR), not to the live trunk commit. The artifact persists across many main-bumps — the session should too. Drop `githash` from the tuple, drop the matching kwarg from the wrapper, and update **every** caller in the same PR so the session family is not forked at the update boundary. |
| 2 | Pinned the regression with the obvious test — `session_uuid("R", 1, AGENT_PLANNER, githash="abc1234")` inside a `pytest.raises(TypeError)` block, with a `# type: ignore[call-arg]` for mypy. | github-code-quality's static analyzer correctly resolved the name back to the now-githash-free signature and reported "Wrong name for an argument in a call". The intent ("test asserts the kwarg is bad") and the static signal ("test uses a bad kwarg") are indistinguishable to a name-resolver, so the bot kept reporting it on every PR that touched the file. | Use `**kwargs`-unpacking to make the intentional bad kwarg invisible to static analysis: `bad_kwargs = {"githash": "abc1234"}; session_uuid("R", 1, AGENT_PLANNER, **bad_kwargs)`. Runtime behavior is identical (still raises `TypeError`), but the static analyzer has no fixed name to resolve. This is a general pattern for any intentional-bad-arg regression test. |

## Results & Parameters

### Diff shape — what changes in one PR

```text
hephaestus/automation/<session_helpers>.py
  - def session_name(repo, issue, agent, githash) -> str
  + def session_name(repo, issue, agent) -> str
  - def session_uuid(repo, issue, agent, githash) -> str
  + def session_uuid(repo, issue, agent) -> str

hephaestus/automation/<wrapper>.py
  - def invoke_claude_with_session(..., githash, ...)
  + def invoke_claude_with_session(...)  # githash kwarg removed

hephaestus/automation/planner.py
hephaestus/automation/plan_reviewer.py
hephaestus/automation/implementer.py
hephaestus/automation/address_review.py
hephaestus/automation/pr_reviewer.py
hephaestus/automation/ci_driver.py
  # 8 call sites total. At each one:
  -   githash = current_trunk_githash(self.repo_root)
  -   invoke_claude_with_session(..., githash=githash, ...)
  +   invoke_claude_with_session(...)

tests/unit/automation/test_session_naming.py
  + bad_kwargs = {"githash": "abc1234"}
  + with pytest.raises(TypeError):
  +     session_uuid("R", 1, AGENT_PLANNER, **bad_kwargs)
  + with pytest.raises(TypeError):
  +     session_name("R", 1, AGENT_PLANNER, **bad_kwargs)
  + def test_session_uuid_is_stable_across_trunk_bumps(monkeypatch):
  +     ...
```

`current_trunk_githash` itself is **not** deleted — non-session callers (log
lines, state files, audit trails) still legitimately use it. Only session-id
derivation drops it.

### Why partial removal is wrong

If you update some callers but not others, the session family forks at the
update boundary:

| Caller | Reads `githash`? | Resulting session id | Effect |
| -------- | ----------------- | --------------------- | ------- |
| planner (updated) | No | `uuid5(<repo>_<issue>_planner)` | Stable across main-bumps. |
| implementer (NOT updated) | Yes | `uuid5(<repo>_<issue>_implementer_<sha>)` | New id every main-bump. |
| pr_reviewer (updated) | No | `uuid5(<repo>_<issue>_pr_reviewer)` | Stable. |

The pipeline now has two coexisting scoping rules. Resume works for some
agents and fails for others, on the same artifact, on the same iteration.
Any partial-update PR has to be rejected or completed in the same PR.

### Why `**kwargs` unpacking silences the analyzer (without weakening the assertion)

The static analyzer's job is **name resolution**: given a call `f(x=1)`, can
the parameter `x` be matched to a known argument of `f`? When the call site is
`f(**bad_kwargs)`, the keys of `bad_kwargs` are not statically knowable
without flow analysis, so the analyzer cannot prove "this kwarg name does
not exist" and stays silent. At runtime, however, Python still resolves
`**bad_kwargs` to `githash="abc1234"` and the wrong-kwarg `TypeError`
fires exactly as intended.

This pattern generalizes to any intentional-bad-arg regression test against
any name-resolving static analyzer (github-code-quality, ruff, mypy,
pyright, pylance).

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #845 closes #841 (rebased successor of conflict-closed PR #843) — automation loop session-naming fix | `session_name` and `session_uuid` lost `githash`; `invoke_claude_with_session` lost the matching kwarg; 8 callers updated in lockstep (planner, plan_reviewer, implementer, address_review, pr_reviewer, ci_driver). Regression test uses `**bad_kwargs` unpacking so github-code-quality cannot statically resolve the intentional bad kwarg. PR merged via CI. Three prior fixes (session_jsonl dot-encoding, worktree pre-sync, HEAD-didn't-advance guard) keep the staleness risk of longer-lived sessions bounded. |
