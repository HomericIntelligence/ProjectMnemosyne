---
name: fix-mojo-format-line-length
description: "Fix mojo format CI failures caused by print() strings exceeding 88-char line limit when mojo cannot run locally. Use when: pre-commit mojo-format hook fails in CI reformatting print() calls, mojo binary unavailable due to GLIBC incompatibility."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

# Fix Mojo Format Line Length Skill

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Fix pre-commit `mojo-format` CI failures when mojo cannot run locally due to GLIBC version incompatibility |
| Outcome | Success — manually applied formatter changes match CI diff exactly |
| Project | ProjectOdyssey (Mojo ML framework) |

## When to Use

- `pre-commit` CI check fails with `mojo-format` hook reformatting files
- `mojo` binary unavailable locally (GLIBC version mismatch: requires GLIBC_2.32/2.33/2.34)
- `print()` statements with string literals exceed 88-character line limit
- CI diff shows formatter splitting long `print("...")` into multi-line `print(\n    "..."\n    "..."\n)`

## Verified Workflow

1. **Get the exact CI diff** from the failed pre-commit run:

   ```bash
   gh run view <run-id> --log-failed 2>&1 | grep -A 50 "All changes made by hooks"
   ```

2. **Identify reformatted lines** — mojo format splits long print strings at ~88 chars using
   implicit string concatenation:

   ```mojo
   # Before (>88 chars — fails mojo format):
   print("STATUS: Backward pass is a documented placeholder (full implementation tracked in GitHub issue #3181)")

   # After (mojo format output):
   print(
       "STATUS: Backward pass is a documented placeholder (full"
       " implementation tracked in GitHub issue #3181)"
   )
   ```

3. **Apply changes manually using Edit tool** — match the CI diff exactly:
   - Wrap `print("...")` → `print(\n    "part1"\n    " part2"\n)`
   - Note the leading space on continuation strings (mojo formatter convention)
   - Indentation matches surrounding code (4 spaces for top-level fn body)

4. **Commit and push** the formatting fix

5. **Verify CI re-runs** cleanly:

   ```bash
   gh pr checks <pr-number>
   ```

## Mojo Format Line-Wrapping Rules

| Rule | Detail |
|------|--------|
| Line limit | 88 characters |
| String splitting | Implicit concatenation with leading space on continuation |
| Wrap style | `print(\n    "first part"\n    " continuation"\n)` |
| Long args | Same rule applies to any function call argument, not just print |
| Indentation | Continuation strings indented 4 extra spaces from `print(` call |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `pixi run mojo format` locally | Execute mojo formatter to auto-fix files | GLIBC_2.32/2.33/2.34 not found on host OS (Debian Buster, glibc 2.31) | Mojo requires newer GLIBC than some CI/dev hosts have |
| Run `just pre-commit-all` locally | Apply all pre-commit hooks including mojo-format | Same GLIBC incompatibility blocks mojo binary | Pre-commit hooks using mojo also fail on incompatible hosts |
| Skip and rely on CI to auto-fix | Let CI apply the format and commit back | CI does not commit back — it just fails | Must apply formatting fixes manually when mojo unavailable |

## Results & Parameters

**Key insight**: The CI pre-commit failure log includes the complete diff of what `mojo format`
would apply. Extract it with:

```bash
gh run view <run-id> --log-failed 2>&1 | grep -A 100 "All changes made by hooks:"
```

This gives you the exact changes to make manually via `Edit` tool.

**GLIBC check** — verify if mojo can run locally before attempting:

```bash
pixi run mojo --version 2>&1 | grep -i glibc
# If you see "version GLIBC_2.3x not found" — use manual Edit approach
```

**Mojo format column limit**: 88 characters (not 79 like Black, not 120 like some configs).
Strings are split using implicit concatenation (adjacent string literals):

```mojo
print(
    "First 88 chars or less"
    " rest of string starting with a space"
)
```
