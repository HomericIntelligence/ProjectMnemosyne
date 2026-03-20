---
name: sync-stale-future-improvements
description: Sync stale Future Improvements sections with actual implementation. Use
  when a TODO or Future Improvements doc section lists a feature that has already
  been shipped.
category: documentation
date: 2026-02-20
version: 1.0.0
user-invocable: false
---
# Skill: Sync Stale "Future Improvements" With Implementation

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #759 |
| PR | #877 |
| Category | documentation |
| Objective | Remove stale "Future Improvements" entries from docs for features that have already been implemented |
| Outcome | Success — documentation now matches implementation, PR created with auto-merge |

## When to Use

Trigger this skill when:

- A "Future Improvements" or "TODO" section in docs lists a feature that has already been shipped
- Code review / issue triage finds a doc that calls something "planned" but a quick `grep` shows it exists in source
- A Dockerfile, config, or script gains a new capability but only the code is updated, not the narrative docs
- CI or contributors are confused because docs say "not yet implemented" but the feature works

## Verified Workflow

### 1. Confirm the feature is implemented

```bash
# Grep for the actual implementation
grep -rn "<feature-keyword>" <source-dir>/

# Read the relevant lines to confirm it's real, not just a comment
```

### 2. Read the stale documentation

```bash
# Identify the Future Improvements section
grep -n -i "<feature-keyword>\|future" <docs-file>
```

Confirm the stale entry exists.

### 3. Add a proper documented section to the main body

Insert a subsection **near the component it belongs to**.
Document all relevant parameters in a table:

```markdown
### <Feature Name>

Brief description of what it does.

\`\`\`<language>
<code block showing actual implementation>
\`\`\`

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--param` | value | What it does |
```

### 4. Remove the stale "Future Improvements" entry

Edit the numbered list, removing only the item that was just implemented. Renumber if needed.

### 5. Scan remaining Future Improvements for other stale entries

When the issue asks to check whether other Future Improvements are stale, do it systematically — grep for each item in the actual source files before concluding they are still future work.

### 6. Commit, push, and PR

```bash
git add <docs-file>
git commit -m "fix(docs): Mark <feature> as implemented in <doc-file>

- Add <Feature> subsection documenting the existing implementation
- Remove stale '<feature>' item from Future Improvements section

Closes #<issue>"

git push -u origin <branch>
gh pr create --title "fix(docs): Mark <feature> as implemented" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

| Parameter | Value |
|-----------|-------|
| Commit type | `fix(docs):` |
| Files typically changed | 1 markdown doc file |
| Pre-commit hooks | Markdown lint, trim whitespace — Python linters skip if no .py files changed |

## Key Insight

When the issue asks to check whether other Future Improvements are stale, do it systematically — grep for each item in the actual source files before concluding they are still future work. Don't assume only the reported item is stale.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Issue #759, PR #877 | [notes.md](../../references/notes.md) |
