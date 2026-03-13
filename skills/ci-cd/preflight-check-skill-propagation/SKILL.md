# Preflight Check Skill Propagation

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-21 |
| Issue | #803 |
| Objective | Add preflight check to `worktree-create` skill so developers bypassing `gh-implement-issue` still run the 6-check safety gate |
| Outcome | Success — PR #917 created, auto-merge enabled |
| Files Changed | `tests/claude-code/shared/skills/worktree/worktree-create/SKILL.md` |

## When to Use

Use this pattern when:

- A safety/quality gate exists in one entry-point skill but not all entry points
- A follow-up issue asks to propagate a check to a sibling or parallel skill
- The fix is documentation-only (no script duplication needed — reference by path)
- You need to keep two sibling skills' error-handling tables in sync

## Verified Workflow

1. **Read the source skill** (`gh-implement-issue/SKILL.md`) to understand the exact language used for the preflight step — copy it verbatim for consistency
2. **Verify the script path** — confirm `preflight_check.sh` exists at the referenced path before writing the path into the target skill
3. **Update Quick Reference** — add Step 0 preflight command above the create command
4. **Update Workflow list** — insert Step 1 "Run pre-flight check", renumber remaining steps
5. **Sync Error Handling table** — copy the four preflight rows from the source skill exactly
6. **Add References entry** — link to `issue-preflight-check` skill for full documentation
7. **Stage and commit** — pre-commit markdown lint, trim-whitespace, fix-end-of-files all pass with no code changes needed

### Key Commands

```bash
# Verify the script exists before referencing it
find . -name "preflight_check.sh"

# The correct path to reference in the skill doc
bash tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh <issue-number>

# Commit (pre-commit runs automatically)
git add tests/claude-code/shared/skills/worktree/worktree-create/SKILL.md
git commit -m "docs(skills): Add preflight check to worktree-create skill"
```

## Failed Attempts

### git add was blocked by .gitignore

**Symptom**: `git add tests/claude-code/shared/skills/worktree/worktree-create/SKILL.md` printed:

```
The following paths are ignored by one of your .gitignore files:
tests/claude-code/shared/skills/worktree
```

**Root cause**: The `worktree` directory name appears in `.gitignore`. However, the file was **already staged** in the index from a prior interactive operation, so the error was non-fatal.

**Resolution**: Run `git status <file>` to confirm the file is already staged ("Changes to be committed"), then proceed directly to `git commit`. Do **not** use `-f` to force-add ignored files unless you have verified intent.

**Lesson**: When `git add` is blocked by `.gitignore` for a skill file that is tracked in the repo, verify staged status first — the error message can be misleading.

## Results & Parameters

### Diff Summary

```diff
--- a/tests/claude-code/shared/skills/worktree/worktree-create/SKILL.md
+++ b/tests/claude-code/shared/skills/worktree/worktree-create/SKILL.md

 ## Quick Reference

+# 0. Pre-flight check (REQUIRED - runs all 6 checks automatically)
+bash tests/claude-code/shared/skills/github/gh-implement-issue/scripts/preflight_check.sh <issue-number>
+
+# 1. Create worktree (only after pre-flight passes)
 ./scripts/create_worktree.sh <issue-number> <description>

 ## Workflow

+1. **Run pre-flight check** - `bash ... preflight_check.sh <issue-number>` — stops on critical failures
 2. **Create worktree** - Run create script ...
-1. → 2., 2. → 3., etc.

 ## Error Handling

+| Pre-flight: issue CLOSED | Stop work; issue already resolved |
+| Pre-flight: merged PR found | Stop work; check PR for implementation |
+| Pre-flight: worktree conflict | Navigate to existing worktree or remove it |
+| Pre-flight: warns existing branch | Review branch before creating new one |

 ## References
+- See `issue-preflight-check` skill for full pre-flight check documentation
```

### Pre-commit Results

All hooks passed on first attempt:

- Markdown Lint: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- (Python/YAML/Shell checks: Skipped — no code changes)

## References

- `gh-implement-issue/SKILL.md` — source of preflight pattern
- `issue-preflight-check` skill — full preflight documentation
- Issue #803 — original request (follow-up from #735)
- PR #917 — implementation
