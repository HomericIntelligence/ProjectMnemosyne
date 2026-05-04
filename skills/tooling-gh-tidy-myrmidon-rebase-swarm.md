---
name: tooling-gh-tidy-myrmidon-rebase-swarm
description: "Use when wrapping the gh-tidy CLI extension to add Myrmidon swarm rebase-conflict resolution. Triggers: (1) developer wants single-repo branch tidy with interactive delete prompts preserved, (2) gh-tidy aborts rebases due to conflicts and you want agents to fix them autonomously, (3) you need a branch-tidying CLI that dispatches per-branch swarm agents without ever deleting branches, (4) hephaestus-tidy swarm crashes immediately with 'Unknown message type: rate_limit_event' and all branches remain failing."
category: tooling
date: 2026-05-03
version: "1.1.0"
user-invocable: false
verification: verified-local
history: tooling-gh-tidy-myrmidon-rebase-swarm.history
tags: [gh-tidy, myrmidon, rebase, swarm, git, worktree, branch, asyncio, claude-code-sdk, rate-limit-event]
---

# Skill: gh-tidy + Myrmidon Rebase Swarm

**History:** [changelog](./tooling-gh-tidy-myrmidon-rebase-swarm.history)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Wrap `gh tidy --rebase-all` with a Myrmidon swarm that semantically resolves rebase conflicts gh-tidy aborted, without ever deleting branches |
| **Outcome** | hephaestus-tidy CLI + /hephaestus:tidy skill built; swarm crashes on `rate_limit_event`; workaround via parallel Agent() calls resolves conflicts |
| **Verification** | verified-local — workaround (parallel Agent() calls) executed and confirmed; swarm bug directly observed on ProjectMnemosyne |
| **History** | [changelog](./tooling-gh-tidy-myrmidon-rebase-swarm.history) |

## When to Use

- A developer sits in a single repo and wants all local branches rebased onto trunk in one command
- `gh tidy --rebase-all` works for most branches but aborts some due to conflicts; you want Claude to fix the failures
- You need to preserve gh-tidy's interactive y/N branch-delete prompts (the tool, not the swarm, deletes branches)
- You're adding a per-repo rebase-fix CLI to a shared tooling package (e.g., ProjectHephaestus)
- Conflicts in the failed branches need semantic resolution (not blind `--ours`/`--theirs`)
- **`hephaestus-tidy` swarm immediately crashes all agents (~4 seconds each) with `Unknown message type: rate_limit_event`** — use the parallel Agent() workaround below

## Verified Workflow

> **Verification level:** verified-local — the parallel Agent() workaround was executed end-to-end on ProjectMnemosyne and resolved all 5 real conflicts. The hephaestus-tidy swarm itself is verified-precommit only (CI pending on ProjectHephaestus PR #306).

### Quick Reference

```bash
# Run: tidy current repo interactively, then swarm-fix failed rebases
hephaestus-tidy

# Preview without executing
hephaestus-tidy --dry-run

# Run gh-tidy only, no swarm
hephaestus-tidy --no-swarm

# Limit swarm concurrency
hephaestus-tidy --max-concurrent 3

# --- WORKAROUND if swarm crashes with rate_limit_event ---
# Bypass the swarm and use direct parallel Agent() calls per branch
# (see "Workaround: Direct Parallel Agent() Calls" section below)
```

### gh-tidy Problem Branch Parser

gh-tidy emits ANSI-coloured output. Strip ANSI before parsing:

```python
import re
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_PROBLEM_HEADER = re.compile(r"WARNING:\s*Unable to auto-rebase the following branches")
_PROBLEM_BULLET = re.compile(r"^\s*\*\s+(\S+)")

def parse_problem_branches(output: str) -> list[str]:
    clean = _ANSI.sub("", output)
    branches: list[str] = []
    in_block = False
    for line in clean.splitlines():
        if _PROBLEM_HEADER.search(line):
            in_block = True
            continue
        if in_block:
            m = _PROBLEM_BULLET.match(line)
            if m:
                branches.append(m.group(1))
            elif line.strip() and not line.strip().startswith("*"):
                in_block = False
    return branches
```

gh-tidy source confirms format (lines 297–301):
```
WARNING: Unable to auto-rebase the following branches:
    * branch-a
    * branch-b
```

### Interactive TTY Passthrough

Keep `stdin` connected to user TTY while teeing output to a buffer:

```python
with subprocess.Popen(
    ["gh", "tidy", "--rebase-all", "--trunk", trunk, "--skip-gc"],
    stdin=sys.stdin,          # passthrough — user answers y/N prompts
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
) as proc:
    assert proc.stdout is not None  # noqa: S101
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        buf.append(line)
    proc.wait()
```

**Critical:** `stdin=sys.stdin` (not `subprocess.PIPE`) is what keeps the TTY interactive.

### Swarm Dispatch (asyncio + claude_code_sdk)

```python
async def _dispatch_swarm(branches, trunk, repo_path, repo_slug, max_concurrent, dry_run):
    from claude_code_sdk import ClaudeCodeOptions, query
    results: dict[str, str] = {}
    sem = asyncio.Semaphore(max_concurrent)

    async def _run_one(branch: str) -> None:
        async with sem:
            prompt = _make_agent_prompt(branch, trunk, repo_path, repo_slug)
            options = ClaudeCodeOptions(
                max_turns=40, cwd=str(repo_path), model="claude-sonnet-4-6"
            )
            status = "failed"
            for message in query(prompt=prompt, options=options):
                text = getattr(message, "text", None) or str(message)
                if "STATUS:" in text:
                    m = re.search(r"STATUS:\s*(\S+)", text)
                    if m:
                        status = m.group(1)
            results[branch] = status

    await asyncio.gather(*(_run_one(b) for b in branches))
    return results
```

**Cap at 5 concurrent agents** (Mnemosyne batch-pr-rebase-workflow v2.8.0 verified-ci).

### Per-Agent Worktree Pattern

```bash
# Agent creates its own isolated worktree
git worktree add .git/worktrees/tidy-<branch> <branch>
git -C .git/worktrees/tidy-<branch> fetch origin <trunk>
git -C .git/worktrees/tidy-<branch> rebase origin/<trunk>

# After success:
git push --force-with-lease --force-if-includes origin <branch>

# Re-arm auto-merge (GitHub silently clears it after force-push):
PR=$(gh pr list --head <branch> --json number --jq '.[0].number // empty')
[ -n "$PR" ] && gh pr merge --auto --merge "$PR"

# Clean up (no --force):
git worktree remove .git/worktrees/tidy-<branch>
```

### Empty-Commit Detection (Subsumption)

After rebase, always verify commits weren't silently dropped:

```bash
git log origin/<trunk>..HEAD --oneline
# Empty output = all commits already on trunk (subsumed)
# If empty: report "subsumed" and STOP — do NOT push, do NOT delete
```

### Safety Net Workarounds

| Blocked command | Safe alternative |
| ----------------- | ----------------- |
| `git checkout <ref> -- <path>` | `git show <ref>:<path> > <path>` |
| `git checkout <branch>` | `git switch <branch>` |
| `git reset --hard` | `git reset --keep` (only if clean) |
| `git worktree remove --force` | Leave in place; report to parent |

### Agent Prompt Structure

Include a **verbatim FORBIDDEN ACTIONS block** in every agent prompt:

```text
## FORBIDDEN ACTIONS — do not perform any of these, ever:
- `git branch -d <branch>`
- `git branch -D <branch>`
- `git push origin --delete <branch>`
- `git worktree remove --force <path>`
- Removing or deleting any worktree that existed before this agent started
- Deleting any local or remote branch
```

Include `git worktree prune` (safe — removes only already-gone worktree directories)
as an explicitly allowed pre-flight step.

### Agent Status Reporting

Instruct agents to end their response with:
```
STATUS: <rebased | subsumed | conflict-too-complex | failed>
BRANCH: <branch-name>
NOTE: <one sentence summary>
```

Parse with: `re.search(r"STATUS:\s*(\S+)", text)`

### Workaround: Direct Parallel Agent() Calls (when swarm crashes with rate_limit_event)

If `hephaestus-tidy` swarm crashes with `Unknown message type: rate_limit_event`, bypass
the swarm entirely and dispatch one `Agent()` call per branch with explicit conflict
resolution instructions:

```python
# Example: resolve rebase conflicts on a list of branches via parallel agents
# (pseudocode — adapt to your agent framework)
branches_to_fix = ["branch-a", "branch-b", "branch-c"]

for branch in branches_to_fix:
    Agent(
        description=f"Resolve rebase conflict on {branch}",
        prompt=f"""
        Resolve the rebase conflict on branch {branch} against origin/main.

        Steps:
        1. git fetch origin
        2. git switch {branch}
        3. git rebase origin/main
        4. For each conflict: examine both sides, apply correct resolution
        5. git add <resolved-files>
        6. GIT_EDITOR=true git rebase --continue
        7. git push --force-with-lease --force-if-includes origin {branch}

        FORBIDDEN: Do not delete any branch or worktree.
        """
    )
```

**Why this works:** Direct `Agent()` calls do not go through the `claude-code-sdk` event
loop in `tidy.py` that fails to handle `rate_limit_event`. The agent framework handles
rate limiting internally without crashing.

### Suggested Fix for hephaestus-tidy (ProjectHephaestus)

In `hephaestus/github/tidy.py`, the agent event loop needs to handle `rate_limit_event`
message type explicitly instead of raising on unknown types:

```python
# Proposed fix in _run_one() / the query event loop:
async for message in query(prompt=prompt, options=options):
    # Handle rate_limit_event — do NOT raise, just wait and continue
    msg_type = getattr(message, "type", None)
    if msg_type == "rate_limit_event":
        await asyncio.sleep(60)  # or use message.retry_after_ms if available
        continue

    text = getattr(message, "text", None) or str(message)
    if "STATUS:" in text:
        m = re.search(r"STATUS:\s*(\S+)", text)
        if m:
            status = m.group(1)
```

**File to fix:** `hephaestus/github/tidy.py` in ProjectHephaestus.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `stdin=subprocess.PIPE` with auto-answers | Piped `n\nn\n` to stdin to auto-decline gh-tidy's delete prompts | User loses ability to delete branches via gh-tidy's own prompts; design requirement changed | Use `stdin=sys.stdin` to pass TTY through; user answers their own prompts |
| `{k: v for k in list}` dict comprehension | Used comprehension with constant value | ruff C420: use `dict.fromkeys(list, v)` for constant-value comprehensions | Replace with `dict.fromkeys(iterable, constant)` |
| Single large `main()` function | All logic in one function | ruff C901: complexity > 10 | Extract `_build_arg_parser()`, `_validate_environment()`, `_print_summary()` helpers |
| Long strings in f-strings | Multi-part message in single f-string line | E501 line-too-long even after breaking Python line — f-string content counted | Break the string content itself, not just the Python syntax |
| `type: ignore[import]` on claude_code_sdk | Added ignore comment for missing stubs | mypy had stubs for claude_code_sdk; comment triggered `unused-ignore` error | Remove the comment; if stubs are missing use `import-untyped` not `import` |
| `assert proc.stdout is not None` without noqa | Asserting Popen's stdout is set after `stdout=PIPE` | ruff S101 flags assert in production code | Add `# noqa: S101` — this assert is justified (Popen with PIPE always sets stdout) |
| Running `hephaestus-tidy` swarm (cap=5) with 10 conflicting branches | Dispatched full Myrmidon swarm via hephaestus-tidy on ProjectMnemosyne — 10 branches, cap=5 | All 10 agents failed in ~4 seconds each with `ERROR - [<branch>] agent exception: Unknown message type: rate_limit_event`; zero branches resolved | `claude-code-sdk` emits `rate_limit_event` during rate limiting; `tidy.py` event loop treats unrecognized message types as fatal exceptions rather than skipping or waiting |
| Retrying `hephaestus-tidy` after `rate_limit_event` crash | Assumed crash was transient; re-ran hephaestus-tidy swarm | Same crash on every retry — identical failure mode, not transient | The bug is structural in `tidy.py`: unhandled message types always raise; retrying without a code fix always reproduces |

## Results & Parameters

### CLI Interface

```
hephaestus-tidy [--dry-run] [--trunk BRANCH] [--no-swarm] [--max-concurrent N] [-v]
```

| Flag | Default | Purpose |
| ------ | --------- | --------- |
| `--dry-run` | false | Print actions without executing |
| `--trunk` | auto-detected | Override default branch |
| `--no-swarm` | false | Run gh-tidy only; print failures, skip agents |
| `--max-concurrent` | 5 | Agent pool size |

### Agent Status Values

| Status | Meaning | Action |
| -------- | --------- | -------- |
| `rebased` | Branch pushed to remote, auto-merge re-armed | Done |
| `subsumed` | All commits already on trunk after rebase | Branch still exists; user can delete manually |
| `conflict-too-complex` | Agent could not confidently resolve | Manual intervention needed |
| `failed` | Exception or push failure | Manual intervention needed |

### Known Bug: `rate_limit_event` Crash in Swarm

| Property | Value |
| --------- | ----- |
| **Symptom** | All swarm agents fail in ~4 seconds with `Unknown message type: rate_limit_event` |
| **Affected file** | `hephaestus/github/tidy.py` in ProjectHephaestus |
| **Root cause** | `claude-code-sdk` emits `rate_limit_event` message type; tidy.py event loop does not handle it and raises a fatal exception |
| **Workaround** | Use direct parallel `Agent()` calls with explicit rebase instructions (see Verified Workflow) |
| **Suggested fix** | Catch `rate_limit_event` in the `async for message in query(...)` loop; sleep and continue instead of raising |

### Key Design Decisions

- `git push --force-with-lease --force-if-includes origin <branch>` (not bare `--force`)
- After every force-push: `gh pr merge --auto --merge <pr>` to re-arm auto-merge
  (GitHub silently clears it on force-push)
- `GIT_EDITOR=true git rebase --continue` to avoid editor prompts in non-interactive shells
- `git worktree prune` is safe to run as a pre-flight step (only removes
  worktrees whose directories are already gone)

### Unit Test Coverage

The `parse_problem_branches()` function should have tests for:
- Clean output (no WARNING block) → empty list
- Single problem branch
- Multiple problem branches
- ANSI escape codes in output (must be stripped before parsing)
- Empty problem block (header present, no bullets)
- Non-bullet text after header terminates the block
- Various branch name formats (`main`, `feature/foo-bar`, `release/v2.0.0`)

### pyproject.toml Entry Point

```toml
[project.scripts]
hephaestus-tidy = "hephaestus.github.tidy:main"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | PR #306 feat/hephaestus-tidy — ruff + mypy + 12 unit tests pass | verified-precommit; CI pending |
| ProjectMnemosyne | /hephaestus:tidy run — 10 conflict branches, swarm crashed; parallel Agent() workaround resolved 5 real conflicts | verified-local; rate_limit_event bug directly observed |
