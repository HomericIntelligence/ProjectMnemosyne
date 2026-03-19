---
name: adr-index-entry
description: 'Add a missing ADR entry to the ADR index table in docs/adr/README.md.
  Use when: an ADR file exists but is not listed in the index table.'
category: documentation
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
# Skill: adr-index-entry

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-05 |
| Objective | Add ADR-009 to the ADR index table in `docs/adr/README.md` |
| Outcome | Success — one-line table row added, pre-commit passed, PR #3338 created |
| Category | documentation |

## When to Use

Use this skill when:

- An ADR file exists under `docs/adr/` but its row is absent from the `## ADR Index` table in `docs/adr/README.md`
- A quality audit or GitHub issue flags a missing ADR index entry (complexity: S)
- A new ADR was merged without the author updating the index table

## Verified Workflow

### 1. Read the ADR file to get the canonical title, status, and date

```bash
head -10 docs/adr/ADR-NNN-<slug>.md
```

Extract:
- `**Status**:` line → status value (e.g., `Accepted`)
- `**Date**:` line → date value (e.g., `2025-12-30`)
- First `# ADR-NNN: ...` heading → title after the colon

### 2. Read the current README index to find the insertion point

```bash
cat docs/adr/README.md
```

Identify the last row in the `## ADR Index` table. The new row goes immediately after it,
maintaining ascending ADR number order.

### 3. Edit README.md to add the row

Use the Edit tool with the exact last row as `old_string` and append the new row:

```markdown
| [ADR-NNN](ADR-NNN-<slug>.md) | <Title> | <Status> | <Date> |
```

The row format is: `| [ADR-NNN](filename.md) | Title | Status | YYYY-MM-DD |`

### 4. Run pre-commit to verify

```bash
pixi run pre-commit run --all-files
```

Confirm `Markdown Lint` passes. GLIBC-related mojo errors in stderr are non-blocking —
they appear because the mojo binary requires a newer GLIBC than the host system provides,
but the relevant hooks (markdownlint, ruff, yaml, etc.) still run and pass.

### 5. Commit, push, create PR

```bash
git add docs/adr/README.md
git commit -m "docs(adr): add ADR-NNN to README index

ADR-NNN-<slug>.md existed but was missing from the ADR index table.

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "docs(adr): add ADR-NNN to README index" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Task completed on first attempt | N/A | Read the ADR file first to get exact title/status/date — do not guess from the filename |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| File changed | `docs/adr/README.md` |
| Lines changed | 1 inserted |
| Pre-commit hooks | All passed (Markdown Lint, ruff, yaml, trailing-whitespace) |
| PR | https://github.com/HomericIntelligence/ProjectOdyssey/pull/3338 |
| Issue | #3150 |
| Branch | `3150-auto-impl` |
| Time to complete | ~2 minutes |

## Key Insights

1. **Verify title/status/date from the ADR file itself**: The issue description says "(Verify the actual title and date from the ADR file itself)" — always read the ADR rather than trusting the issue body or filename.

2. **GLIBC errors are non-blocking**: On older Debian hosts, mojo format hooks emit GLIBC version errors to stderr but pre-commit still reports `Passed` for all relevant hooks. Do not treat these as failures.

3. **Single-line edit is sufficient**: These index updates are always exactly one table row — no surrounding context changes needed. Use the Edit tool with the previous last row as `old_string` and append the new row.
