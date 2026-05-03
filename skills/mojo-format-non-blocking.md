---
name: mojo-format-non-blocking
description: "Use when: (1) mojo-format pre-commit hook crashes on files using new Mojo
  syntax (comptime_assert, etc.) and CI is blocked; (2) pre-commit CI fails because
  mojo-format reformatted a .mojo file due to a line exceeding the line length limit;
  (3) multiple PRs need parallel formatter fixes; (4) a pre-commit hook needs to be
  made advisory (non-blocking) without removal."
category: ci-cd
date: 2026-03-13
version: 2.0.0
user-invocable: false
tags:
- mojo-format
- pre-commit
- ci-cd
- formatter-crash
- line-length
- workaround
- parallel-pr-fixes
- glibc
---
# Skill: mojo-format-non-blocking

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-03-13 |
| Project | ProjectOdyssey |
| Objective | Fix 3 failing PRs blocked by mojo-format crashes and make formatter non-blocking in CI |
| Outcome | All 3 PRs fixed, mojo-format made advisory in CI via `continue-on-error`; merged with mojo-format-line-length-fix on 2026-05-03 |
| PR | HomericIntelligence/ProjectOdyssey#4499 (CI fix), #4059, #4053, #3836 (PR fixes) |
| Absorbed | mojo-format-line-length-fix on 2026-05-03 |

## When to Use

Use this skill when:

- `mojo format` crashes with `'_python_symbols' object has no attribute 'comptime_assert_stmt'`
- Pre-commit CI fails because mojo-format modifies files or crashes
- CI pre-commit job fails showing `mojo-format` modified a `.mojo` file
- `print("...long string...")` exceeds line length in a `.mojo` file
- Any single-line statement in Mojo that mojo-format would rewrite
- Multiple PRs are blocked by formatter issues and need parallel fixes
- A pre-commit hook needs to be made advisory (non-blocking) without removal
- `mojo format` cannot run locally due to GLIBC version mismatch

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

### Fixing line-length failures (mojo-format modifies a file in CI)

1. **Identify the offending line** from the CI failure log — look for which file `mojo-format` modified.

2. **Read the file** at the reported line number to see the long line.

3. **Apply the multi-line form** that mojo-format produces for `print()`:

   ```mojo
   # Before (too long):
   print("some very long message that exceeds the line length limit and causes mojo-format to reformat it")

   # After (mojo-format style):
   print(
       "some very long message that exceeds the line"
       " length limit and causes mojo-format to reformat it"
   )
   ```

   Key rules:
   - Opening `print(` on its own line
   - String split at a natural word boundary, continuation starts with a space: `" continuation"`
   - Closing `)` on its own line, indented to match the `print`

4. **Commit** — pre-commit hooks will run `mojo-format` again and it should pass with no modifications.

5. **Cannot run mojo-format locally?** (e.g., GLIBC version mismatch on older Linux)
   - Apply the multi-line form manually as above
   - mojo-format is deterministic: matching its output style is sufficient for the hook to pass
   - The pre-commit hook in CI will confirm correctness

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
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked | N/A | Solution was straightforward (non-blocking CI split) |
| Run `pixi run mojo format` locally | Ran the formatter on the local machine to verify formatting | GLIBC version too old (`GLIBC_2.32`/`2.33`/`2.34` not found) — mojo binary requires newer glibc | Mojo requires a modern Linux (Ubuntu 22.04+). On older systems, apply multi-line form manually using the known mojo-format output style. mojo-format is deterministic so manual matching works. |
## Results & Parameters

| Parameter | Value |
| ----------- | ------- |
| Mojo version | 0.26.1 |
| Crash trigger | `comptime_assert` in formatted files |
| Wrapper script | `scripts/mojo-format-compat.sh` |
| Pre-commit skip env | `SKIP=mojo-format` |
| CI pattern | `continue-on-error: true` on separate step |
| PRs fixed in parallel | 3 (using worktree agents) |
| Line length limit | ~88 chars (Mojo default) |

**Working multi-line print pattern** (copy-paste template):

```mojo
print(
    "first part of the message up to ~80 chars"
    " continuation of the message"
)
```

**String continuation rule**: adjacent string literals in Mojo are concatenated — no `+` operator needed. The continuation string must start with a space if the split point is mid-word-boundary.

**Verification command** (when mojo is available):

```bash
pixi run mojo format <file> && git diff
# Expected: no output from git diff (file already correctly formatted)
```

**Commit message pattern used**:

```
fix: Address review feedback for PR #<number>

Wrap long print() call in <file> to pass mojo-format
line length check (pre-commit CI failure).

Closes #<issue>
```

## Related

- Mojo formatter GLIBC compat: `docs/dev/mojo-glibc-compatibility.md`
- Mojo JIT crash workaround: `docs/dev/mojo-jit-crash-workaround.md`
- Pre-commit config: `.pre-commit-config.yaml`
