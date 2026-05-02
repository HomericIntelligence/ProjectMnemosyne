---
name: test-driven-bug-discovery
description: "Writing unit tests that expose latent parsing bugs in text-processing\
  \ functions \u2014 particularly functions that process subprocess/external tool\
  \ output where single-line vs. multi-line input shapes behave differently."
category: testing
date: 2026-03-07
version: 1.0.0
user-invocable: false
tags:
- pytest
- unit-testing
- bug-discovery
- string-parsing
- git
- porcelain
- subprocess
---
## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Objective | Add unit tests for git-quoted filename handling in `commit_changes()` |
| Outcome | Tests exposed a real bug; both bug fix and tests merged in PR #1467 |
| Issue | HomericIntelligence/ProjectScylla#1447 |

## When to Use

- Adding tests for functions that parse subprocess stdout (git, shell commands)
- Testing string manipulation with `strip()`, `split()`, or slicing on multi-line text
- Any function where correctness depends on whether input is single-line or multi-line
- Verifying special-character or whitespace handling (quoted filenames, unicode, etc.)

## The Core Bug Pattern

`str.strip().split("\n")` is subtly wrong when processing line-oriented text that may
have significant leading whitespace on individual lines.

**Problem**: `stdout.strip()` strips leading whitespace from the *entire string*, which
also removes the leading space from the first line if the string starts with a space.

```python
# BUG: strip() eats the leading space that belongs to the first line
line = ' M "path with spaces/file.py"\n'
lines = line.strip().split("\n")
# → ['M "path with spaces/file.py"']   ← leading space gone!
# line[3:] = 'path with spaces/file.py"'  ← no leading quote, unquoting skips

# FIX: splitlines() preserves per-line leading whitespace
lines = line.splitlines()
# → [' M "path with spaces/file.py"']  ← leading space preserved
# line[3:] = '"path with spaces/file.py"'  ← quote detected, unquoting fires
```

**Why this matters for `git status --porcelain`**:
- `M file` = space at position 0 means "unmodified in index, modified in worktree"
- The space is *semantically significant* — it encodes the index status
- `line[3:]` relies on the space being at position 0 to correctly locate the filename

## Verified Workflow

### 1. Read the implementation before writing tests

Always read the actual parsing logic, not just the docstring. Understand:
- What positions are used for field extraction (e.g., `line[3:]`)
- What string operations are applied to `stdout` before splitting into lines
- What guard conditions control special-case handling

### 2. Write parametrized tests covering shape variants

```python
@pytest.mark.parametrize(
    "porcelain_line, expected_path",
    [
        # Single-line stdout where strip() would corrupt the leading space
        (' M "path with spaces/file.py"', "path with spaces/file.py"),
        # Unicode
        (' M "répertoire/fichier.py"', "répertoire/fichier.py"),
        # Untracked file with spaces
        ('?? "dir with spaces/new file.py"', "dir with spaces/new file.py"),
    ],
)
def test_quoted_filename_is_unquoted(
    self, tmp_path: Path, porcelain_line: str, expected_path: str
) -> None:
    status_result = MagicMock()
    status_result.stdout = porcelain_line + "\n"  # single-line stdout

    with (
        patch("<module>.run", side_effect=[status_result, MagicMock(), MagicMock()]) as mock_run,
        patch("<module>.fetch_issue_info", return_value=mock_issue),
    ):
        commit_changes(42, tmp_path)

    staged_files = mock_run.call_args_list[1][0][0]
    assert expected_path in staged_files
    assert f'"{expected_path}"' not in staged_files  # no surrounding quotes
```

### 3. Assert both positive and negative

Always assert:
- The unquoted path **is** in the staged files list
- The *quoted* form (with surrounding `"`) is **not** in the staged files list

This catches the case where the code partially works (e.g., strips leading quote but not
trailing, or passes the raw quoted string alongside an unquoted one).

### 4. Debug assertion failures by inspecting the actual list

When a test fails with `assert 'x' in ['git', 'add', 'x"']`, the list is the actual
`git add` argument list. Compare character by character against expected to pinpoint
exactly where the parsing goes wrong.

### 5. Fix: replace `strip().split("\n")` with `splitlines()`

```python
# Before (buggy)
for line in result.stdout.strip().split("\n"):

# After (correct)
for line in result.stdout.splitlines():
```

`splitlines()` splits on all line boundary sequences (`\n`, `\r\n`, `\r`) and does NOT
strip leading/trailing whitespace from individual lines.

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Key Insight

The existing tests (multi-line stdout like `"M  file1\nA  file2\n"`) passed because
`.strip()` only removed the trailing newline — the first line didn't start with a space
in those cases. The bug only surfaced when a single-line stdout started with a significant
space (`M ...`).

**Always test your parsing functions with both single-line and multi-line inputs.**

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #1467, issue #1447 | `scylla/automation/pr_manager.py::commit_changes` |
