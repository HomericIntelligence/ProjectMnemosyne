---
name: wave-based-bulk-issue-triage
description: Fix 5+ independent GitHub issues in parallel waves using Task isolation:worktree. No manual worktree setup — Claude Code auto-manages isolation.
category: architecture
date: 2026-02-22
user-invocable: false
---

# Skill: Wave-Based Bulk Issue Triage

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Fix 8 GitHub issues (2 waves × 4 PRs) — simple fixes + test additions |
| **Outcome** | ✅ Success — 8 PRs created in parallel, auto-merge enabled |
| **Key Innovation** | `Task(isolation="worktree")` — zero manual worktree management |

## When to Use

Use this skill when:

1. **Backlog of 5+ independent issues** to clear in one session
2. **Issues fall into categories** — e.g., simple doc/config fixes vs. test additions
3. **Issues modify different files** — no shared file conflicts
4. **Want maximum parallelism** with minimal orchestration overhead

**Don't use when:**
- Issues depend on each other (use sequential PRs)
- Any issue touches 20+ files (exclude from wave, file separately)
- Issues share modified files (risk of merge conflicts)

## Verified Workflow

### Phase 1: Triage & Wave Planning

Group issues by **complexity and type** before running anything:

```
Wave A — Simple fixes (no new files, minimal change):
  - Doc/config changes
  - Single-line .gitignore tweaks
  - Adding one test method to existing class

Wave B — Test additions (new classes, more lines):
  - New test classes for untested methods
  - Integration test roundtrips
  - Multi-method test coverage

Excluded — Too complex for bulk:
  - 20+ file changes
  - Cross-repo changes
  - Architectural refactors
```

**Key decision:** Run Wave A first (faster, unblocks Wave B if needed), then Wave B.

### Phase 2: Launch Parallel Agents (One Wave at a Time)

Use `Task` tool with `isolation: "worktree"` — **no manual worktree setup needed**:

```python
# Launch all Wave A agents in parallel (single message, multiple Task calls)
Task(
    subagent_type="Bash",
    isolation="worktree",     # ← Claude Code auto-creates isolated worktree
    description="Fix #NNN brief-description",
    prompt="""
    You are fixing GitHub issue #NNN.

    ## Steps
    1. Read target file(s) before editing
    2. Make minimal change
    3. pre-commit run --files <changed-files>
    4. pixi run python -m pytest <specific-test-file> -q --no-cov
    5. git checkout -b NNN-slug
    6. git add <specific-files>  # Never git add -A
    7. git commit -m "type(scope): description (Closes #NNN)"
    8. git push -u origin NNN-slug
    9. gh pr create --title "..." --body "Closes #NNN"
    10. gh pr merge --auto --rebase

    ## Rules
    - Read files before editing
    - Never git add -A or git add .
    - Never --no-verify
    - Tests must pass before pushing
    """
)
```

Wait for Wave A to complete, then launch Wave B agents the same way.

### Phase 3: Verify

After all agents return:

```bash
gh pr list --author "@me" --state open
```

Check each PR has:
- ✅ Auto-merge enabled
- ✅ CI queued or passing

### Prompt Template for Bash Agent

```
You are fixing GitHub issue #NNN in the ProjectScylla repository.

## Task
[One-sentence description of the fix]

## Steps
1. Read the relevant file(s): cat path/to/file
2. [Specific fix instructions]
3. Run pre-commit: pre-commit run --files <changed-files>
4. Run tests: pixi run python -m pytest tests/path/to/test.py -q --no-cov
5. Create branch: git checkout -b NNN-slug
6. Stage only changed files: git add path/to/changed/file
7. Commit: git commit -m "type(scope): description (Closes #NNN)"
8. Push: git push -u origin NNN-slug
9. Create PR: gh pr create --title "type(scope): description" --body "Closes #NNN"
10. Auto-merge: gh pr merge --auto --rebase

## Important Rules
- Read files before editing them
- Never use git add -A or git add .
- Never use --no-verify
- Pre-commit must pass before committing
- Tests must pass before pushing
```

## Failed Attempts

| Attempt | What We Tried | Why It Failed | Solution |
|---------|--------------|---------------|----------|
| Include complex issue in wave | Issue #908 (SKILL.md relative paths, 20+ files across 2 repos) added to Wave 6 | Too many files, cross-repo scope, not a 15-min fix | Excluded with note "not a simple fix, skip for now" |
| No explicit read-before-edit reminder | Agent prompt omitted "read files before editing" instruction | Agent sometimes tries to Edit without prior Read, causing tool error | Always include explicit read reminder in every agent prompt |
| Manual worktree setup | Previous sessions required `git worktree add` per agent | Extra orchestration overhead, path management complexity | Use `isolation: "worktree"` — zero overhead |

## Results & Parameters

### Session Results (2026-02-22)

| Wave | Issue | Fix Type | PR | Tests Added |
|------|-------|----------|----|-------------|
| 6a | #930 | Add test method to existing class | #1051 | 1 |
| 6b | #959 | Update 3 phantom doc paths | #1052 | 0 |
| 6c | #920 | 1-char .gitignore fix | #1053 | 0 |
| 6d | #1042 | New filter_audit.py script + pixi.toml update | #1055 | 0 |
| 7a | #985 | 8 tests for _move_to_failed + _commit_test_config | #1056 | 8 |
| 7b | #986 | 5 tests for _run_subtest_in_process_safe | #1057 | 5 |
| 7c | #987 | 6 tests for CursesUI._refresh_display | #1058 | 6 |
| 7d | #898 | 3 integration tests for --update roundtrip | #1059 | 3 |

**Total**: 8 PRs, 23 new tests, ~2 minutes wall clock per wave

### Wave Sizing Guidelines

| Wave Size | Agents | Expected Duration |
|-----------|--------|-------------------|
| 2-3 issues | 2-3 parallel | ~1-2 min |
| 4-5 issues | 4-5 parallel | ~2-5 min |
| 6+ issues | Split into sub-waves | Varies |

### Issue Complexity Thresholds

| Category | Fits in Wave? | Notes |
|----------|--------------|-------|
| 1-char config fix | ✅ Yes | Simplest possible |
| Add 1 test method | ✅ Yes | 15-30 lines |
| Add new test class (5-8 tests) | ✅ Yes | Wave B material |
| Update 2-3 doc files | ✅ Yes | Quick |
| New script + config update | ✅ Yes | borderline, but ok |
| 20+ file changes | ❌ No | Exclude, file separate issue |
| Cross-repo changes | ❌ No | Exclude, handle manually |

### Exclusion Criteria (Skip for Now)

Add a comment in the plan when excluding:
```
### Excluded from Wave N
- **#NNN** (brief reason) — [specific reason]. Skip for now.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Wave 6+7, PRs #1051-#1059 | [notes.md](references/notes.md) |
