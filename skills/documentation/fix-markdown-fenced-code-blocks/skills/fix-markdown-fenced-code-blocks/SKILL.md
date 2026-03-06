---
name: fix-markdown-fenced-code-blocks
description: "Fix malformed fenced code block closings and markdownlint violations in markdown files. Use when: closing fences have language tags, line-length violations in docs, or lists lack surrounding blank lines."
category: documentation
date: 2026-03-06
user-invocable: false
---

## Overview

| Property | Value |
|----------|-------|
| **Trigger** | markdownlint CI failure or PR review feedback citing MD013/MD032/MD040 |
| **Primary Fix** | Edit closing fences from ` ```lang ` to ` ``` ` |
| **Secondary Fixes** | Wrap long lines, add blank lines around lists |
| **Verification** | `pixi run pre-commit run markdownlint-cli2 --all-files` |

## When to Use

- markdownlint reports MD040 (missing language on fenced code block) or MD031 on a closing fence line
- A closing fence has a language tag, e.g. ` ```text ` used as a closing ` ``` `
- MD013 line-length violations on descriptive bullet points in agent/hierarchy docs
- MD032 (blanks-around-lists) violations after a bold heading line

## Verified Workflow

1. **Identify violations** — run pre-commit or read CI output to get file:line references
2. **Read context** — `Read` the file around each flagged line to confirm the pattern
3. **Fix closing fences** — use `Edit` to change ` ```text ` → ` ``` ` on closing fence lines only
4. **Fix line-length** — wrap long bullet lines by inserting a newline+indent continuation:
   ```markdown
   - **Key**: Short intro text that fits,
     continuation on next line at 2-space indent
   ```
5. **Fix MD032** — add a blank line after the preceding paragraph/heading before the list
6. **Verify** — run `pixi run pre-commit run markdownlint-cli2 --all-files` and confirm Passed
7. **Commit** — stage only the markdown file, commit with conventional message

## Results & Parameters

### Environment

```bash
# Verify markdown linting (no npx needed — pixi wraps it)
pixi run pre-commit run markdownlint-cli2 --all-files

# Check a single file
pixi run pre-commit run markdownlint-cli2 --files agents/hierarchy.md
```

### markdownlint Rule Reference

| Rule | Name | Fix |
|------|------|-----|
| MD013 | line-length (max 120) | Wrap at natural clause boundary, indent continuation 2 spaces |
| MD031 | blanks-around-fences | Ensure blank line before and after fenced block |
| MD032 | blanks-around-lists | Add blank line before first list item after paragraph/heading |
| MD040 | fenced-code-language | Opening fences need language; closing fences must be plain ` ``` ` |

### Key Pattern: Malformed Closing Fence

Wrong (closing fence with language tag — triggers MD040/MD031):

```text
    └──────────────────────────────────────┘
```text
```

Correct:

```text
    └──────────────────────────────────────┘
```
```

### Key Pattern: Line Wrap for MD013

Wrong (>120 chars):

```markdown
- **Language Context**: Designs Mojo module structures, leverages Mojo features (SIMD, traits, structs); coordinates review across all code dimensions
```

Correct:

```markdown
- **Language Context**: Designs Mojo module structures, leverages Mojo features (SIMD, traits, structs);
  coordinates review across all code dimensions
```

### Key Pattern: MD032 Blank Line Before List

Wrong:

```markdown
**Level 3 Breakdown:**
- Item one with detail
- Item two with detail
```

Correct:

```markdown
**Level 3 Breakdown:**

- Item one with detail
- Item two with detail
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `pixi run npx markdownlint-cli2` | Called npx directly through pixi | `npx: command not found` — npx not in pixi env | Use `pixi run pre-commit run markdownlint-cli2` instead |
| `pixi run markdownlint-cli2` | Called markdownlint-cli2 as a direct pixi task | `markdownlint-cli2: command not found` | markdownlint is invoked via pre-commit hook, not as standalone pixi task |
| `just pre-commit-all` | Used just command runner | `just: command not found` in this environment | Use `pixi run pre-commit run ...` directly |
| Fix only the 3 fence closings | Assumed fix plan was complete | Linting also caught MD013/MD032 violations not listed in the review plan | Always re-run linting after initial fixes to catch secondary violations |
