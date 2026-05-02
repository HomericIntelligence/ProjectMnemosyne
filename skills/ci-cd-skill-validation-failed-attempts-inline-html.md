---
name: ci-cd-skill-validation-failed-attempts-inline-html
description: "Fix CI failures in skill PRs caused by wrong Failed Attempts table column
  names or inline HTML from angle-bracket placeholders. Use when: (1) a skill PR fails
  validate/unit-tests with 'Failed Attempts table missing required columns', (2) a skill
  PR fails markdownlint MD033 no-inline-html on a <placeholder> pattern in prose, (3)
  writing a new skill and wanting to avoid these common validation failures."
category: ci-cd
date: 2026-05-02
version: "1.0.0"
user-invocable: false
tags: [markdownlint, md033, inline-html, failed-attempts, skill-format, validate, unit-tests]
---

# Fix Skill PR CI Failures — Failed Attempts Table + Inline HTML

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-02 |
| **Objective** | Fix CI failures in PRs #1498 and #1516 in ProjectMnemosyne caused by wrong Failed Attempts column names and an MD033 inline-HTML false positive |
| **Outcome** | Both issues resolved; pre-commit hooks passed after fixes |

## When to Use

- A skill PR fails `validate` or `unit-tests` with message "Failed Attempts table missing required columns"
- A skill PR fails `markdownlint` with `MD033/no-inline-html` on a `<word>` placeholder in prose
- You are writing a new skill file and want to avoid these two common authoring mistakes
- The same skill file exists on multiple PR branches and both need the same fix applied independently

## Verified Workflow

### Quick Reference

```bash
# Validate a skill file locally before pushing
python3 scripts/validate_plugins.py

# Check markdownlint for MD033 issues
pixi run npx markdownlint-cli2 skills/<skill-name>.md
```

**Failed Attempts table — exact required column names:**

```markdown
| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Description | Reason | Takeaway |
```

**Inline HTML fix — wrap angle-bracket placeholders in backticks:**

```markdown
<!-- WRONG — triggers MD033 -->
here's the actual CI config, addresses #<existing-issue-number>.

<!-- CORRECT — backticks escape the angle brackets -->
here's the actual CI config, addresses `#<existing-issue-number>`.
```

### Detailed Steps

#### Fix 1: Failed Attempts Table Column Names

The `scripts/validate_plugins.py` validator enforces exact column header names. The
check (`validate_failed_attempts_table`) requires all four of these strings to appear
in the header row:

- `Attempt`
- `What Was Tried`
- `Why It Failed`
- `Lesson Learned`

**Any other column naming will fail validation.** Common wrong variants:

| Wrong column name | Correct column name |
|---|---|
| `Approach` | `Attempt` |
| `Description` | `What Was Tried` |
| `Correct Approach` | `Lesson Learned` |
| 3-column table (any names) | Must be 4 columns with exact names |

**Fix procedure:**

1. Open the skill `.md` file
2. Locate the `## Failed Attempts` section
3. Replace the header row with the exact required header:
   `| Attempt | What Was Tried | Why It Failed | Lesson Learned |`
4. Adjust the separator row column count to match (4 columns)
5. Reformat data rows to fit 4 columns
6. Run `python3 scripts/validate_plugins.py` — must report zero errors for the file

#### Fix 2: MD033 Inline HTML from Angle-bracket Placeholders

Markdownlint rule MD033 (`no-inline-html`) treats any `<word>` pattern as an HTML
element tag — including documentation placeholders like `<existing-issue-number>`,
`<branch-name>`, or `<run-id>`.

**Fix**: wrap every angle-bracket placeholder in backticks so markdownlint sees it as
inline code, not HTML:

```markdown
<!-- Before (triggers MD033) -->
Addresses #<existing-issue-number>.

<!-- After (clean) -->
Addresses `#<existing-issue-number>`.
```

This applies anywhere in prose, including list items, table cells, and inline text.
The fix does not affect readability — readers still understand the placeholder meaning.

#### Fix 3: Same File on Multiple Branches

When the same skill file exists on multiple PR branches (e.g., two concurrent PRs both
touched `skills/oss-contribution-issue-filing-pattern.md`), each branch must be fixed
independently:

1. Check out branch A, apply both fixes, commit, push
2. Check out branch B, apply both fixes, commit, push
3. Verify CI on each PR separately

There is no shortcut — a fix committed to branch A does not appear on branch B unless
cherry-picked or rebased.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 3-column Failed Attempts table | Used `\| Approach \| Why It Failed \| Correct Approach \|` (3 columns, non-standard names) | `validate_plugins.py` checks for all 4 exact header strings; missing `Attempt`, `What Was Tried`, `Lesson Learned` caused rejection | Always use the exact 4-column header: `Attempt \| What Was Tried \| Why It Failed \| Lesson Learned` |
| Bare angle-bracket placeholder in prose | Left `#<existing-issue-number>` as unescaped text in a sentence | Markdownlint MD033 parses `<existing-issue-number>` as an HTML element tag and flags it | Wrap every `<placeholder>` in backticks when it appears in prose |

## Results & Parameters

### Validator Column Check (from `scripts/validate_plugins.py`)

```python
# The exact check — all four must be present in the header row
if not all(col in header for col in ["Attempt", "What Was Tried", "Why It Failed", "Lesson Learned"]):
    errors.append("Failed Attempts table missing required columns")
```

### Expected Output After Fix

```text
$ python3 scripts/validate_plugins.py
Validating skills...
✓ skills/your-skill.md
All skills valid.
```

```text
$ pixi run npx markdownlint-cli2 skills/your-skill.md
skills/your-skill.md: 0 error(s), 0 warning(s)
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | PR #1498 and PR #1516 — `oss-contribution-issue-filing-pattern.md` | Two branches, same file, both fixes applied independently |

## References

- [markdownlint MD033 rule](https://github.com/DavidAnson/markdownlint/blob/main/doc/md033.md)
- [Skill template](../templates/skill-template.md)
- [ci-cd-pre-commit-ci-hook-failures](ci-cd-pre-commit-ci-hook-failures.md)
- [markdownlint-troubleshooting](markdownlint-troubleshooting.md)
