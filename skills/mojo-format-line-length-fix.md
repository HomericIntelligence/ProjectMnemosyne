---
name: mojo-format-line-length-fix
description: 'Fix mojo-format pre-commit CI failures caused by lines exceeding the
  line length limit. Use when: pre-commit CI fails because mojo-format reformatted
  a file, a print() or string literal in .mojo exceeds the line length limit.'
category: ci-cd
date: 2026-03-06
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Trigger** | pre-commit CI fails with `mojo-format` modifying a .mojo file |
| **Root cause** | A line (often a `print()` call with a long string) exceeds mojo-format's line length limit |
| **Fix** | Wrap the long line into multi-line form that mojo-format accepts |
| **Verification** | Run `pixi run mojo format <file> && git diff` — no diff means correctly formatted |

## When to Use

- CI pre-commit job fails showing `mojo-format` modified a file
- `print("...long string...")` exceeds line length in a `.mojo` file
- Any single-line statement in Mojo that mojo-format would rewrite

## Verified Workflow

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
   - The pre-commit hook in CI will confirm correctness

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `pixi run mojo format` locally | Ran the formatter on the local machine to verify formatting | GLIBC version too old (`GLIBC_2.32`/`2.33`/`2.34` not found) — mojo binary requires newer glibc | Mojo requires a modern Linux (Ubuntu 22.04+). On older systems, apply multi-line form manually using the known mojo-format output style |

## Results & Parameters

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
