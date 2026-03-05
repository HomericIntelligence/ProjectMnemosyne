---
name: deprecated-file-cleanup-workflow
description: "Workflow for safely deleting deprecated files from a Mojo/Python codebase. Use when: (1) a file is marked DEPRECATED and consolidated elsewhere, (2) cleaning up legacy modules after migration, (3) removing files as part of a cleanup GitHub issue."
category: tooling
date: 2026-03-05
user-invocable: false
---

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Safely delete a deprecated file by verifying no active imports reference it before deletion |
| Outcome | File deleted, pre-commit passes, PR created and auto-merged |

Workflow for removing deprecated Mojo (or other) files that have been consolidated into a
shared module. Emphasizes verifying no imports reference the file before deletion to avoid
breaking builds.

## When to Use

- A file is marked `DEPRECATED` and has a comment like "Use X for all new code"
- Cleaning up a module that was migrated to `shared.*` or another package
- Implementing a `[Cleanup]`-labeled GitHub issue asking to delete a specific file
- After verifying the migration is complete and no code still depends on the old module

## Verified Workflow

1. **Read the issue**: `gh issue view <issue> --comments` — understand the file, context, and deliverables
2. **Find the file**: Confirm it exists and read it to understand what it contained
3. **Grep for imports** — search all `.mojo`, `.py`, and `.md` files for references:
   ```bash
   # Search for any import of the module
   grep -rn "from benchmarks import\|import benchmarks" . --include="*.mojo" --include="*.py"
   # Also grep for the filename pattern
   grep -rn "benchmarks/__init__" . --include="*.mojo" --include="*.md"
   ```
4. **If no active imports found**: Delete the file with `git rm <file>`
5. **Run pre-commit hooks**: `pixi run pre-commit run --all-files` — verify all hooks pass
6. **Commit**: `git commit -m "chore(scope): delete deprecated <file>\n\nCloses #<issue>"`
7. **Push and PR**: `git push -u origin <branch>` then `gh pr create`
8. **Enable auto-merge**: `gh pr merge --auto --rebase`

## Key Observations

- `__init__.mojo` files for deprecated packages often only contain docstrings with migration
  guidance — no actual functionality. Safe to delete without behavior changes.
- GLIBC version mismatches (`version 'GLIBC_2.32' not found`) in `pixi run mojo build` are
  a pre-existing environment issue, not caused by file deletion. Pre-commit hooks still
  pass because the `mojo format` hook gracefully skips when mojo binary fails.
- Grep the file itself last — it may self-reference in examples (`from benchmarks import stats`
  inside `benchmarks/__init__.mojo`) and produce false positives.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `pixi run mojo build` as verification | Ran build to confirm nothing broke | GLIBC version mismatch caused mojo binary to fail — pre-existing environment issue, unrelated to changes | Use pre-commit hooks as the verification signal, not raw mojo build in this environment |

## Results & Parameters

```bash
# Full workflow (from worktree)
gh issue view 3066 --comments          # Read full context

# Verify no imports (adjust patterns for your module)
grep -rn "from benchmarks import\|import benchmarks" . \
  --include="*.mojo" --include="*.py" | grep -v "__init__.mojo"

# Delete and commit
git rm benchmarks/__init__.mojo
git commit -m "$(cat <<'EOF'
chore(benchmarks): delete deprecated benchmarks/__init__.mojo

Remove deprecated file redirecting to shared.benchmarking.
No Mojo files import this module.

Closes #3066

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# Push and PR
git push -u origin <branch>
gh pr create --title "chore(scope): delete deprecated <file>" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3066 - cleanup benchmarks/__init__.mojo | [notes.md](../../references/notes.md) |
