# Session Notes: CLAUDE.md Token Trimming (Issue #3158)

## Session Context

- **Date**: 2026-03-05
- **Issue**: #3158 — [P3-4] Trim CLAUDE.md length to reduce token consumption
- **Branch**: `3158-auto-impl`
- **PR**: #3363
- **Repo**: HomericIntelligence/ProjectOdyssey

## Objective

Reduce CLAUDE.md from 1,786 lines to ≤1,400 lines (target was ≤1,200 lines success criterion)
without losing critical information.

## Approach

1. Read all section headings with line numbers via `grep -n "^##\|^###"``
2. Classified each section: keep-full / trim-examples / move-and-link
3. Created two new `.claude/shared/` files for moved content
4. Edited CLAUDE.md with targeted `Edit` tool calls (no full rewrites)
5. Ran pre-commit to verify markdown linting

## Files Changed

- **Modified**: `CLAUDE.md` (1786 → 1199 lines, -587 lines)
- **Created**: `.claude/shared/output-style-guidelines.md`
- **Created**: `.claude/shared/tool-use-optimization.md`

## Environment Gotchas

### Working Directory Confusion

The task ran with cwd at `.worktrees/issue-3158/` but the shell cwd reset on each Bash call.
Initial edits went to `/home/mvillmow/Odyssey2/CLAUDE.md` (main repo) rather than the worktree.
Had to copy files manually after noticing `git status` showed no changes in the worktree.

**Fix**: Always check `git status` after edits to confirm you're editing the right copy.

### pre-commit not in PATH

`just` and `just pre-commit-all` were not available. Resolution:
- Found pre-commit at `/home/mvillmow/Odyssey2/.pixi/envs/default/bin/pre-commit`
- Called directly: `SKIP=mojo-format /path/to/pre-commit run --all-files`

### mojo-format GLIBC Failure

The `mojo-format` pre-commit hook fails with GLIBC version errors on this host.
This is a pre-existing infrastructure issue — not caused by documentation changes.
Use `SKIP=mojo-format` when running pre-commit for markdown-only changes.

## What Worked Well

- Targeted `Edit` tool calls to replace specific sections without reading/writing the full file
- Parallel section reads to plan all changes before executing
- Creating `.claude/shared/` files first, then editing CLAUDE.md to replace sections with links
- Preserving decision trees and tables (high information density) while removing example code blocks

## Sections to Always Preserve

These sections should never be trimmed from CLAUDE.md:

1. `## ⚠️ CRITICAL RULES` — Contains PR workflow enforcement
2. `## Git Workflow / ### Development Workflow` — Has concrete `gh pr create` command patterns
3. `### Pre-Commit Hook Policy - STRICT ENFORCEMENT` — Has enforcement language
4. `### Mojo Development Guidelines / Critical Patterns` — Compact constructor/mutation table
5. `### Common Commands / Justfile Build System` — Command reference needed in every session

## Sections Safe to Move to .claude/shared/

These are pure reference/example content not needed inline:

1. Output Style Guidelines (code-block examples)
2. Tool Use Optimization (parallel calls, bash patterns)
3. Agentic Loop Patterns (exploration→planning→execution)
4. Testing Strategy (comprehensive detail in docs/dev/)
5. Extended Thinking examples (illustrative only)
6. Hooks YAML examples (illustrative only)