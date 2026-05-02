---
name: markdown-linting-bulk-table-format-fix
description: "Use when: (1) markdownlint CI fails with 20,000+ errors across hundreds of files due to missing .markdownlint.yaml config, (2) MD060 table style errors flood CI output after a linter config is added or upgraded, (3) you need to bulk-normalize markdown table formatting to compact style across an entire repository"
category: ci-cd
date: 2026-05-01
version: 1.0.0
user-invocable: false
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
| **Date** | 2026-05-01 |
| **Objective** | Fix 20,131 markdownlint errors across 1,189 files in ProjectMnemosyne after CI began enforcing a missing `.markdownlint.yaml` config |
| **Outcome** | Fixed: markdownlint CI passes with 0 errors after adding config + running bulk table normalizer script |
| **Status** | Completed — CI verified passing |

## When to Use

Apply this pattern when:

1. **CI references `.markdownlint.yaml` but the file is missing** from the repo — causes sudden mass failures on all files
2. **MD060 table style errors** flood across hundreds of files (tables using non-compact `| cell |` vs. compact `|cell|` style inconsistently)
3. **MD024 "duplicate heading" errors** in changelogs or version files where repeated headings (Added/Fixed/Changed) are legitimate under different version headers
4. **MD003 setext heading style errors** caused by orphaned YAML-like `---...---` blocks embedded in markdown content (not real frontmatter)
5. **MD056 column count mismatch** in tables containing literal pipe characters in cell content

**Do NOT use** when:

- Only a handful of markdownlint errors exist (fix manually instead)
- The config file already exists and CI was passing before

## Verified Workflow

### Quick Reference

```bash
# 1. Add .markdownlint.yaml with correct options
cat .markdownlint.yaml

# 2. Run bulk table normalizer
python3 scripts/fix_md_tables.py --all

# 3. Fix ruff import sorting in the new script
ruff check --fix scripts/fix_md_tables.py

# 4. Fix trailing whitespace + missing EOF newlines (pre-commit catches these)
pre-commit run --all-files

# 5. Stage and verify
pre-commit run markdownlint --all-files
```

### Detailed Steps

#### Step 1 — Create `.markdownlint.yaml`

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

#### Step 2 — Write and Run the Bulk Table Normalizer

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

#### Step 3 — Fix MD056 (column count mismatch)

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

#### Step 4 — Fix MD003 (setext heading style)

Some markdown files embed YAML-like blocks after the real frontmatter, which markdownlint misdetects as headings with setext style (underline `---`). Remove orphaned `---...---` blocks from content sections — they are not valid frontmatter.

```bash
# Find files where markdownlint reports MD003
pre-commit run markdownlint --all-files 2>&1 | grep MD003
# Inspect each: look for stray --- blocks in content (not at file top)
```

#### Step 5 — Run Pre-commit to Catch Remaining Issues

After the bulk table fix, pre-commit will catch trailing whitespace and missing end-of-file newlines on 600+ files. Let it auto-fix:

```bash
pre-commit run --all-files
# Will modify files and exit 1 on first pass
# Re-run until all hooks pass
pre-commit run --all-files
```

#### Step 6 — Fix Ruff Import Sorting in New Scripts

If you wrote a new Python script, `ruff` will flag unsorted imports (I001):

```bash
ruff check --fix scripts/fix_md_tables.py
```

#### Step 7 — Verify and Commit

```bash
# Confirm markdownlint passes
pre-commit run markdownlint --all-files
# Expected: Passed (no file modifications)

# Stage specific files — never git add -A
git add .markdownlint.yaml scripts/fix_md_tables.py
git add $(git diff --name-only)   # all modified skills/docs files
git commit -m "fix(lint): fix 20k markdownlint errors — add config + bulk table normalizer"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Wrong MD024 option | Used `allow_different_nesting: true` in `.markdownlint.yaml` | Not a valid MD024 option — markdownlint ignored it silently, errors persisted | The correct option is `siblings_only: true` |
| Suppress MD060 entirely | Set `MD060: false` to disable the rule | CI still required real fixes; disabling hid the errors but did not normalize the files | Use `style: consistent` to accept existing style rather than disabling the rule |
| Ruff clean script | Added `fix_md_tables.py` without running ruff | I001 import order violation caused pre-commit to fail on the new script | Always run `ruff check --fix` on any new Python file before committing |
| Manual table edits | Attempted to fix a sample of tables by hand | 1,189 files × multiple tables each = impractical; introduced inconsistencies | Automate bulk fixes with a script that handles edge cases (frontmatter, code blocks) |

## Results & Parameters

### `.markdownlint.yaml` Configuration

```yaml
default: true

MD024:
  siblings_only: true

MD046:
  style: fenced

MD060:
  style: consistent
```

### Script Invocation

```bash
# Fix all markdown files in the repo
python3 scripts/fix_md_tables.py --all

# Fix a single file
python3 scripts/fix_md_tables.py skills/some-skill.md
```

### Expected Output

- Bulk normalizer: `Fixed N files` (ProjectMnemosyne: 1,176 files)
- Pre-commit markdownlint: `Passed` with no file modifications
- Total errors eliminated: 20,131 across 1,189 files

### Scale Metrics (ProjectMnemosyne)

| Metric | Value |
| ------- | ------- |
| Total markdownlint errors before | 20,131 |
| Files affected | 1,189 |
| Files fixed by script | 1,176 |
| Files fixed manually (MD003/MD056) | ~13 |
| Pre-commit trailing-whitespace/EOF fixes | 600+ |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | 2026-05-01 — mass fix of missing .markdownlint.yaml | CI markdownlint job passes with 0 errors after fix |

## References

- [markdownlint Rules Reference](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md)
- [MD060 — Table style](https://github.com/DavidAnson/markdownlint/blob/main/doc/md060.md)
- [MD024 — siblings_only option](https://github.com/DavidAnson/markdownlint/blob/main/doc/md024.md)
- [markdownlint-troubleshooting.md](markdownlint-troubleshooting.md) — related skill for hook auto-fix failures blocking multiple PRs
