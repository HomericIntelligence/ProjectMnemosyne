# Session Notes: Bulk Skill Migration (Issue #3140)

## Context

- **Date**: 2026-03-04
- **Issue**: ProjectOdyssey2 #3140 — Port all skills to ProjectMnemosyne
- **Result**: 4 new skills ported; 81 already present from prior migrations

## Discovery Phase

Ran `comm -23` on sorted directory listings to find which of 85 Odyssey2 skills
were missing from Mnemosyne's `skills/` directory (flattened across all categories).

Finding: Only `worktree-cleanup`, `worktree-create`, `worktree-switch`, `worktree-sync` were absent.
All tier-1, tier-2, and most top-level skills had been previously migrated.

## Migration Script Design

Key design decisions:

1. **Idempotency**: `skill_already_exists()` scans all category subdirs in Mnemosyne,
   not just a flat top-level check. This handles skills stored under any category.

2. **Category mapping**: Two-level resolution — skill-name override map first,
   then frontmatter `category` field, then default `tooling`.

3. **Section reconstruction**: Rather than simple string replace, parse sections
   into named buckets then rebuild in canonical order:
   When to Use → other sections → Verified Workflow → Failed Attempts → Results

4. **Path generalization**: Pattern list ordered longest-match first to avoid
   partial substitutions (e.g. `pixi run mojo` before `pixi run`).

## Shell Pitfall

`ls dir/ | sort > file.txt` as a single compound expression in Bash subprocess
caused sort to try to read `ls` as a filename. Fix: use Python's `os.listdir()`
or `Path.iterdir()` directly instead of shelling out.

## PRs Created

- ProjectMnemosyne PR #326: 4 worktree skills + marketplace regeneration
- ProjectOdyssey2 PR #3224: migration script added to `scripts/`