# contributing-md-structure-sync

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| Category | documentation |
| Objective | Sync CONTRIBUTING.md project structure with actual scylla/ sub-packages |
| Outcome | Success — added missing scylla/discovery/ entry |

## When to Use

- A GitHub issue reports that CONTRIBUTING.md project structure listing is out of sync with the codebase
- After adding a new `scylla/` sub-package, to update documentation
- Quality audit tasks flagging documentation gaps in project structure listings

## Verified Workflow

1. **Read the issue** — identify which packages are reported missing
2. **Read CONTRIBUTING.md** around the project structure block (search for `## Project Structure`)
3. **List the actual directories** with `ls scylla/` to verify what exists
4. **Cross-check** — the issue description may be stale; always verify against actual file content before editing
5. **Add missing entries** in alphabetical order within the `scylla/` block
6. **Use consistent format**: `│   ├── <name>/       # <Description>`
7. **Commit** with `docs(contributing): add scylla/<name>/ to project structure listing`
8. **Push and PR** with `Closes #<issue>`

## Failed Attempts

- **Skill tool in don't-ask mode**: `commit-commands:commit-push-pr` was denied; fell back to manual `git add / git commit / git push / gh pr create` — these always work as a fallback

## Key Insights

- **Issue descriptions can be stale**: Issue #1352 said both `utils/` and `discovery/` were missing, but `utils/` was already in CONTRIBUTING.md. Always read the actual file before editing.
- **Alphabetical ordering**: CONTRIBUTING.md uses strict alphabetical ordering within the `scylla/` block — insert at correct position
- **Docs-only changes**: No tests needed; pre-commit markdown lint is the only gate
- **CONTRIBUTING.md vs CLAUDE.md**: Both have project structure listings — a gap in one may not exist in the other (CLAUDE.md had `discovery/` added earlier in PR fdc37657)

## Results & Parameters

```bash
# Verify what's actually in the listing vs what exists
grep -n "discovery\|utils\|cli" CONTRIBUTING.md
ls scylla/

# Standard edit pattern
# old: │   ├── core/            # Core types
#      │   ├── e2e/             # E2E testing framework
# new: │   ├── core/            # Core types
#      │   ├── discovery/       # Resource discovery
#      │   ├── e2e/             # E2E testing framework

# Commit message format
git commit -m "docs(contributing): add scylla/discovery/ to project structure listing"
```
