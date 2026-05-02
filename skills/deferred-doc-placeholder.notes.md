# Session Notes: deferred-doc-placeholder

## Session Details

- **Date**: 2026-03-07
- **Repository**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3312-auto-impl
- **Issue**: #3312 — "docs/index.md lacks Core Documentation section after stub deletion"
- **PR**: #3932

## Problem

After 17 placeholder stub files were deleted in PR/issue #3142 (under YAGNI), the
`docs/index.md` Core Documentation section was removed entirely. The section included 8 topics:

- project-structure
- shared-library
- paper-implementation
- testing-strategy
- mojo-patterns
- agent-system
- workflow
- configuration

Also removed from Advanced Topics: performance, custom-layers, distributed-training,
visualization, debugging, integration.

Also removed from Development Guides: architecture, api-reference, ci-cd.

The issue asked for a reminder that the navigation hub is now sparse and these topics
should be re-added when real docs are written.

## Approach Taken

Single file edit: inserted an HTML comment block into `docs/index.md` between the
Getting Started section (line 18) and Advanced Topics section (line 19 post-edit).

The comment lists all 17 deferred topics with:
- Status (Deferred — doc not yet written)
- Why (Stub deleted in #3142, YAGNI)
- Acceptance criteria (Write <file>; re-add link here)

Plus a `Tracking issue: #3312` footer.

## Execution

```bash
# Read current state
cat docs/index.md

# Edit (used Edit tool to insert comment block at line 19)
# Verified: grep -c "DEFERRED: Core Documentation" docs/index.md → 1
# Verified: grep -n "\[.*\](core/" docs/index.md → no matches (no broken links)
# Verified: awk 'length > 120' docs/index.md → 2 pre-existing long lines, not from edit

# Commit
git add docs/index.md
git commit -m "docs(index): add deferred placeholder for Core Documentation section"
# All pre-commit hooks passed

# Push + PR
git push -u origin 3312-auto-impl
gh pr create --title "docs(index): add deferred placeholder for Core Documentation section"
gh pr merge --auto --rebase 3932
```

## Key Observations

1. HTML comments in Markdown pass `markdownlint-cli2` even with MD033 (allowed_elements list)
   because comments are not HTML *elements*
2. The pre-existing long lines (106, 112 chars) in the Community/License sections were
   pre-existing — confirmed via `git diff HEAD`
3. The task was trivial but important: making stub-deletion follow-ups explicit so future
   contributors don't wonder why the nav hub is sparse

## Commit Hash

`d5d70c2f` (post-edit) — superseded by the new commit in this session
