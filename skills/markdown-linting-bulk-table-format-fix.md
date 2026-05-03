---
name: markdown-linting-bulk-table-format-fix
description: "Use when: (1) markdownlint CI fails with 20,000+ errors across hundreds of files due
  to missing .markdownlint.yaml config, (2) MD060 table style errors flood CI output after a linter
  config is added or upgraded, (3) markdownlint-cli2 is upgraded to v0.40.0+ and adds MD060 with
  ~1000 violations that --fix silently ignores (requires two-pass Python script + style: compact),
  (4) you need to bulk-normalize markdown table formatting to compact style across an entire
  repository"
category: ci-cd
date: 2026-05-03
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: markdown-linting-bulk-table-format-fix.history
tags:
  - markdownlint
  - MD060
  - tables
  - pre-commit
  - bulk-fix
  - ci-unblocking
---

# Markdown Linting Bulk Table Format Fix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-03 |
| **Objective** | Fix markdownlint CI failures — either mass failures from missing config, or MD060 violations from v0.40.0 upgrade that `--fix` silently ignores |
| **Outcome** | Fixed: markdownlint CI passes with 0 errors after adding config + running bulk table normalizer script |
| **Verification** | verified-ci |
| **History** | [changelog](./markdown-linting-bulk-table-format-fix.history) |

## When to Use

Apply this pattern when:

1. **CI references `.markdownlint.yaml` but the file is missing** from the repo — causes sudden mass failures on all files
2. **MD060 table style errors** flood across hundreds of files (tables using non-compact `| cell |` vs. compact `|cell|` style inconsistently)
3. **markdownlint-cli2 upgraded to v0.40.0+** — MD060 is a new rule in this version; running
   `markdownlint-cli2 --fix "**/*.md"` silently produces **0 file modifications** for MD060
   violations. The auto-fixer does not implement MD060. ~1079 violations across 165 files remain
   after `--fix`.
4. **MD024 "duplicate heading" errors** in changelogs or version files where repeated headings (Added/Fixed/Changed) are legitimate under different version headers
5. **MD003 setext heading style errors** caused by orphaned YAML-like `---...---` blocks embedded in markdown content (not real frontmatter)
6. **MD056 column count mismatch** in tables containing literal pipe characters in cell content

**Do NOT use** when:

- Only a handful of markdownlint errors exist (fix manually instead)
- The config file already exists and CI was passing before

## Verified Workflow

### Quick Reference

```bash
# Scenario A: Missing .markdownlint.yaml (mass failures)
# 1. Add .markdownlint.yaml with MD060: { style: consistent }
# 2. Run bulk table normalizer
python3 scripts/fix_md_tables.py --all
# 3. Fix ruff import sorting
ruff check --fix scripts/fix_md_tables.py
# 4. Fix trailing whitespace + missing EOF newlines
pre-commit run --all-files
# 5. Verify
pre-commit run markdownlint --all-files

# Scenario B: markdownlint v0.40.0 upgrade — MD060 added, --fix is silent no-op
# 1. Add MD060: { style: compact } to .markdownlint.yaml
# 2. Run two-pass Python script (separator rows first, then cell padding)
python3 scripts/fix_md_tables.py --all   # Pass 1: normalize separator rows
# Pass 2 (if needed): strip wide padding from header/data cells
# 3. Verify
pre-commit run markdownlint --all-files
```

### Detailed Steps

#### Scenario A — Missing `.markdownlint.yaml` (20k+ errors)

##### Step A1 — Create `.markdownlint.yaml`

The root cause is almost always a missing or incomplete `.markdownlint.yaml`. CI references it, but it was never committed.

```yaml
# .markdownlint.yaml
default: true

MD024:
  siblings_only: true   # allow repeated headings under DIFFERENT parent headings (changelogs)

MD046:
  style: fenced         # enforce fenced code blocks

MD060:
  style: consistent     # accept whatever style a table already uses, as long as it's internally consistent
```

Key config decisions:

- `MD060: style: consistent` — tells markdownlint to accept whatever style a table already uses, rather than enforcing a single global style. This resolves the bulk of errors without changing table content.
- `MD024: siblings_only: true` — changelogs legitimately repeat "Added"/"Fixed" headings under different version headers; `siblings_only` allows this.

##### Step A2 — Write and Run the Bulk Table Normalizer

For repos with thousands of tables in non-compact format, write a Python normalizer script. The key correctness requirements:

- Skip YAML frontmatter (lines between leading `---` delimiters)
- Skip fenced code blocks (``` ` ``` or `~` fences)
- Normalize each table row to compact style: `| cell |` → `|cell|` (strip internal padding but keep pipes)

```python
# scripts/fix_md_tables.py — compact table normalizer
# Run with: python3 scripts/fix_md_tables.py --all
# Or single file: python3 scripts/fix_md_tables.py path/to/file.md
```

Run it:

```bash
python3 scripts/fix_md_tables.py --all
# Expected: "Fixed 1,176 files" (or similar count)
```

##### Step A3 — Fix MD056 (column count mismatch)

MD056 fires when a table cell contains a literal `|`. Escape it:

```markdown
<!-- Before (breaks column count) -->
| Rule | Description | Format |
| MD060 | Table style | `| cell |` or `|cell|` |

<!-- After -->
| Rule | Description | Format |
| MD060 | Table style | `\| cell \|` or `\|cell\|` |
```

Alternatively use the HTML entity `&#124;` instead of `\|`.

##### Step A4 — Fix MD003 (setext heading style)

Some markdown files embed YAML-like blocks after the real frontmatter, which markdownlint misdetects as headings with setext style (underline `---`). Remove orphaned `---...---` blocks from content sections — they are not valid frontmatter.

```bash
# Find files where markdownlint reports MD003
pre-commit run markdownlint --all-files 2>&1 | grep MD003
# Inspect each: look for stray --- blocks in content (not at file top)
```

##### Step A5 — Run Pre-commit to Catch Remaining Issues

After the bulk table fix, pre-commit will catch trailing whitespace and missing end-of-file newlines on 600+ files. Let it auto-fix:

```bash
pre-commit run --all-files
# Will modify files and exit 1 on first pass
# Re-run until all hooks pass
pre-commit run --all-files
```

##### Step A6 — Fix Ruff Import Sorting in New Scripts

If you wrote a new Python script, `ruff` will flag unsorted imports (I001):

```bash
ruff check --fix scripts/fix_md_tables.py
```

##### Step A7 — Verify and Commit

```bash
# Confirm markdownlint passes
pre-commit run markdownlint --all-files
# Expected: Passed (no file modifications)

# Stage specific files — never git add -A
git add .markdownlint.yaml scripts/fix_md_tables.py
git add $(git diff --name-only)   # all modified skills/docs files
git commit -m "fix(lint): fix 20k markdownlint errors — add config + bulk table normalizer"
```

#### Scenario B — markdownlint v0.40.0 Upgrade Adds MD060 (--fix is silent no-op)

This is the case where the config file exists and CI was passing, then markdownlint-cli2 is
upgraded to v0.40.0 which introduced MD060. Running `--fix` produces **zero file changes**
despite ~1000+ violations — MD060 is not implemented in the auto-fixer.

##### Step B1 — Add `MD060: { style: compact }` to `.markdownlint.yaml`

```yaml
# Add to .markdownlint.yaml:
MD060:
  style: compact    # All table columns must use compact separator: | --- |
```

Use `style: compact` (not `style: consistent`) when you want to enforce a single canonical
style across all tables. After adding this, markdownlint will report all violations against
a single standard, which the two-pass script can reliably fix.

##### Step B2 — Run the Two-Pass Fix Script

MD060 violations fall into two categories that require separate passes:

**Pass 1: Normalize separator rows**

Find lines matching `^\|[-: |]+\|$` and replace with compact separators:
`| --- | --- | ...` (one `---` per column, based on column count of the header row).

```python
import re

def fix_separator_row(line: str, col_count: int) -> str:
    """Replace any separator row with compact | --- | --- | ... form."""
    if re.match(r'^\|[-: |]+\|$', line.strip()):
        return '| ' + ' | '.join(['---'] * col_count) + ' |'
    return line
```

**Pass 2: Strip wide padding from header and data cells**

After Pass 1, tables that used "aligned" style (padded to column width) still fail because
the header/data cells have wide padding that doesn't match the new compact separators.
Strip extra spaces from inside cells:

```python
def compact_table_row(line: str) -> str:
    """Convert | wide cell | to | compact cell | (single space padding)."""
    if not line.strip().startswith('|'):
        return line
    cells = line.split('|')
    cells = [''] + [c.strip() for c in cells[1:-1]] + ['']
    return '| ' + ' | '.join(c for c in cells[1:-1]) + ' |'
```

**Why two passes**: After Pass 1, separator rows are compact but header/data cells retain
their wide padding (e.g., `|  Command  |  Description  |`). MD060 considers the full table
style — mismatched padding between separator and content rows still triggers violations.

##### Step B3 — Verify

```bash
# Run markdownlint on all files
pre-commit run markdownlint --all-files
# Expected: Passed (0 violations)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Wrong MD024 option | Used `allow_different_nesting: true` in `.markdownlint.yaml` | Not a valid MD024 option — markdownlint ignored it silently, errors persisted | The correct option is `siblings_only: true` |
| Suppress MD060 entirely | Set `MD060: false` to disable the rule | CI still required real fixes; disabling hid the errors but did not normalize the files | Use `style: consistent` to accept existing style rather than disabling the rule |
| Ruff clean script | Added `fix_md_tables.py` without running ruff | I001 import order violation caused pre-commit to fail on the new script | Always run `ruff check --fix` on any new Python file before committing |
| Manual table edits | Attempted to fix a sample of tables by hand | 1,189 files × multiple tables each = impractical; introduced inconsistencies | Automate bulk fixes with a script that handles edge cases (frontmatter, code blocks) |
| `markdownlint-cli2 --fix "**/*.md"` for MD060 | Ran auto-fixer expecting it to fix MD060 violations after v0.40.0 upgrade | Silent no-op — produced 0 file modifications despite ~1079 violations across 165 files. MD060 is not implemented in the markdownlint-cli2 auto-fixer. | When `--fix` produces no changes but violations remain, the rule lacks an auto-fix implementation. Write a custom Python script instead. |
| Single-pass separator normalization | Ran only Pass 1 (normalize separator rows) expecting all MD060 violations to be fixed | ~1079 violations remained — header and data cells with wide padding (`|  wide content  |`) still violated MD060 compact style after separator rows were normalized | Two passes required: Pass 1 normalizes separators, Pass 2 strips wide cell padding |

## Results & Parameters

### `.markdownlint.yaml` Configuration — Scenario A (missing config)

```yaml
default: true

MD024:
  siblings_only: true

MD046:
  style: fenced

MD060:
  style: consistent
```

### `.markdownlint.yaml` Configuration — Scenario B (v0.40.0 upgrade, enforce compact)

```yaml
default: true

MD024:
  siblings_only: true

MD046:
  style: fenced

MD060:
  style: compact    # Enforce compact separators; requires two-pass script to fix existing tables
```

### Script Invocation

```bash
# Fix all markdown files in the repo (Scenario A)
python3 scripts/fix_md_tables.py --all

# Fix a single file
python3 scripts/fix_md_tables.py skills/some-skill.md
```

### Expected Output

- Bulk normalizer: `Fixed N files` (ProjectMnemosyne: 1,176 files)
- Pre-commit markdownlint: `Passed` with no file modifications
- Total errors eliminated: 20,131 across 1,189 files (Scenario A)
- Total errors eliminated: ~1,079 across 165 files (Scenario B — ProjectOdyssey v0.40.0 upgrade)

### Scale Metrics

| Project | Scenario | Errors Before | Files Affected | Fix Method |
| ------- | -------- | ------------- | -------------- | ---------- |
| ProjectMnemosyne | A (missing config) | 20,131 | 1,189 | `fix_md_tables.py --all` + `style: consistent` |
| ProjectOdyssey | B (v0.40.0 upgrade) | ~1,079 | ~165 | Two-pass Python script + `style: compact` |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | 2026-05-01 — mass fix of missing .markdownlint.yaml | CI markdownlint job passes with 0 errors after fix |
| ProjectOdyssey | 2026-05-03 — PR #5347/#5348, markdownlint-cli2 v0.40.0 upgrade added MD060 | Two-pass Python script + `style: compact`; CI markdownlint job passed with 0 violations |

## References

- [markdownlint Rules Reference](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)
- [MD060 — Table style](https://github.com/DavidAnson/markdownlint/blob/main/doc/md060.md)
- [MD024 — siblings_only option](https://github.com/DavidAnson/markdownlint/blob/main/doc/md024.md)
- [markdownlint-troubleshooting.md](markdownlint-troubleshooting.md) — related skill for hook auto-fix failures blocking multiple PRs
