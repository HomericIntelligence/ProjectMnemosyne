---
name: mojo-format-non-blocking
description: 'Make mojo-format pre-commit hook non-blocking in CI when the Mojo formatter
  crashes on files using new syntax (comptime_assert, etc.). Includes manual formatting
  fix patterns and parallel PR fix workflow.

  '
category: ci-cd
date: 2026-03-13
version: 1.0.0
user-invocable: false
tags:
- mojo-format
- pre-commit
- ci-cd
- formatter-crash
- workaround
- parallel-pr-fixes
---
# Skill: mojo-format-non-blocking

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-13 |
| Project | ProjectOdyssey |
| Objective | Fix 3 failing PRs blocked by mojo-format crashes and make formatter non-blocking in CI |
| Outcome | All 3 PRs fixed, mojo-format made advisory in CI via `continue-on-error` |
| PR | HomericIntelligence/ProjectOdyssey#4499 (CI fix), #4059, #4053, #3836 (PR fixes) |

## When to Use

Use this skill when:

- `mojo format` crashes with `'_python_symbols' object has no attribute 'comptime_assert_stmt'`
- Pre-commit CI fails because mojo-format modifies files or crashes
- Multiple PRs are blocked by formatter issues and need parallel fixes
- A pre-commit hook needs to be made advisory (non-blocking) without removal

**Trigger symptoms**:

```text
error: cannot format tests/foo.mojo: '_python_symbols' object has no attribute 'comptime_assert_stmt'
Oh no! 💥 💔 💥
1 file failed to reformat.
```

## Verified Workflow

### Making mojo-format non-blocking in CI

Split the pre-commit step into two parts in `.github/workflows/pre-commit.yml`:

```yaml
- name: Run pre-commit hooks (excluding mojo-format)
  run: |
    SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure

- name: Run mojo format (advisory - non-blocking)
  continue-on-error: true
  run: |
    pixi run pre-commit run mojo-format --all-files --show-diff-on-failure || \
      echo "::warning::mojo format check failed (non-blocking)"
```

**Key insight**: `SKIP=mojo-format` is a pre-commit built-in env var that skips specific hooks by ID.

### Manual formatting fixes when formatter crashes

When `mojo format` crashes but CI shows the expected diff:

1. Read the CI failure log to get the exact diff (`gh run view <id> --job <job-id> --log-failed`)
2. Apply the formatting changes manually with the Edit tool
3. Common patterns:
   - Add blank line between functions (Mojo requires 2 blank lines between top-level `fn` definitions)
   - Re-wrap long strings at ~88 chars (Mojo's default line length)

### Parallel PR fixes with worktree agents

Fix multiple PRs simultaneously using isolated worktree agents:

```text
Agent(isolation="worktree", run_in_background=true) per PR branch
```

Each agent: checkout branch -> apply fix -> commit -> push. No branch conflicts.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Mojo version | 0.26.1 |
| Crash trigger | `comptime_assert` in formatted files |
| Wrapper script | `scripts/mojo-format-compat.sh` |
| Pre-commit skip env | `SKIP=mojo-format` |
| CI pattern | `continue-on-error: true` on separate step |
| PRs fixed in parallel | 3 (using worktree agents) |

## Related

- Mojo formatter GLIBC compat: `docs/dev/mojo-glibc-compatibility.md`
- Mojo JIT crash workaround: `docs/dev/mojo-jit-crash-workaround.md`
- Pre-commit config: `.pre-commit-config.yaml`
