---
name: deferred-doc-placeholder
description: 'Pattern for adding an HTML comment placeholder to a docs navigation
  index when an entire section is removed due to stub deletion. Use when: a docs/index.md
  section disappears after placeholder stubs are deleted and a follow-up issue tracks
  restoring it.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Deferred Doc Placeholder

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-07 |
| **Issue** | #3312 (ProjectOdyssey) |
| **PR** | #3932 (ProjectOdyssey) |
| **Objective** | Restore navigation awareness in `docs/index.md` after Core Documentation section was removed when 17 placeholder stubs were deleted in #3142 |
| **Outcome** | HTML comment block added listing all 17 deferred topics with status, reason, and acceptance criteria; no broken links introduced |
| **Status** | Completed and merged |

## When to Use This Skill

Apply this pattern when:

1. A docs navigation index (`docs/index.md` or similar hub) had a **section removed** because the linked files were placeholder stubs deleted under YAGNI
2. A follow-up issue explicitly tracks **restoring the navigation hub** when real docs are written
3. You want to make the **absence visible** to future contributors without introducing broken links
4. Multiple topics are deferred and each needs **acceptance criteria** for restoration

**Do NOT use** when:

- Only one or two links are missing (just add a TODO comment inline)
- The section was intentionally removed permanently (no planned restoration)
- The doc files actually exist — link them directly instead

## Verified Workflow

### 1. Read the issue and the current index file

```bash
gh issue view <number> --comments
# Then read docs/index.md to see its current state
```

Confirm: which section is missing, which topics belong to it.

### 2. Insert an HTML comment block at the section's former location

Place the comment between the last real section above and the next real section below.
Each deferred topic gets three sub-fields:

```markdown
<!-- DEFERRED: <Section Name> section
  The following topics were linked in docs/index.md but their source files
  were placeholder stubs deleted in #<stub-deletion-issue>. Re-add each entry
  once the corresponding doc is written.

  - <topic-slug> (<path/to/file.md>)
    Status: Deferred — doc not yet written
    Why: Stub deleted in #<issue> (YAGNI)
    Acceptance criteria: Write <path/to/file.md>; re-add link here

  ...

  Tracking issue: #<follow-up-issue>
-->
```

Key rules:

- Use an **HTML comment** (`<!-- ... -->`), not a Markdown heading — the section should
  not render in the output, only in source
- List **every** topic that was in the removed section
- Include **all related sections** that also lost entries (e.g., Advanced Topics, Dev Guides)
- Add `Tracking issue: #<number>` at the bottom so the comment is self-referencing

### 3. Verify no broken links were introduced

```bash
grep -n "\[.*\](<missing-path>" docs/index.md   # should return nothing
```

### 4. Check line length compliance (markdownlint MD013)

```bash
awk 'length > 120 {print NR": "length" chars"}' docs/index.md
```

Lines inside HTML comments are exempt from markdownlint rendering rules, but confirm
any pre-existing long lines are not from your edit.

### 5. Commit, push, PR

Pure documentation change — no tests needed:

```bash
git add docs/index.md
git commit -m "docs(index): add deferred placeholder for <Section> section

<Brief explanation of what was removed and why the comment was added.>

Closes #<issue-number>"

git push -u origin <branch>
gh pr create --title "docs(index): add deferred placeholder for <Section> section" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Single-pass implementation | — | Task was well-scoped: one file edit, HTML comment, no broken links |

## Results & Parameters

### Files Modified

| File | Change |
|------|--------|
| `docs/index.md` | +55 lines: HTML comment block between Getting Started and Advanced Topics sections |

### Comment Block Template (copy-paste)

```markdown
<!-- DEFERRED: Core Documentation section
  The following topics were linked in docs/index.md but their source files
  were placeholder stubs deleted in #3142. Re-add each entry once the
  corresponding doc is written.

  - project-structure (core/project-structure.md)
    Status: Deferred — doc not yet written
    Why: Stub deleted in #3142 (YAGNI)
    Acceptance criteria: Write core/project-structure.md; re-add link here

  - shared-library (core/shared-library.md)
    Status: Deferred — doc not yet written
    Why: Stub deleted in #3142
    Acceptance criteria: Write core/shared-library.md; re-add link here

  Tracking issue: #3312
-->
```

### Pre-commit Results

All hooks passed with a pure HTML comment addition:

- `Markdown Lint` — Passed (HTML comments are not HTML elements; MD033 allows-list not triggered)
- `Trim Trailing Whitespace` — Passed
- `Fix End of Files` — Passed
- `Check for Large Files` — Passed

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3312, PR #3932 | 17-topic Core Documentation section restored as deferred comment after stubs deleted in #3142 |

## Related Skills

- **document-deferred-future-improvements** — Annotates *existing* Future Improvements items inside design docs with Status/Why/Acceptance Criteria; this skill is for a *missing navigation section* in an index file
- **delete-placeholder-docs** — The upstream skill that removes stubs; this skill documents the follow-up pattern
- **placeholder-note-to-status-tracking** — Similar pattern for converting bare placeholder notes to structured status entries
