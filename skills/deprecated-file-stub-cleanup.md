---
name: deprecated-file-stub-cleanup
description: "Safely delete deprecated files and stubs. Use when: (1) removing deprecated .mojo stub files, (2) cleaning up dead code after refactor, (3) deleting deprecated skills from the registry."
category: tooling
date: 2026-03-28
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---
## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-28 |
| **Objective** | Safely delete deprecated files/stubs with zero breakage |
| **Outcome** | File deleted, cross-references updated, PR created and auto-merged |

Consolidated workflow for removing deprecated files, stubs, re-export shims, and skill directories
from any codebase. Covers Mojo directory-vs-file resolution, cross-reference sweeps across all
file types, and the GLIBC/mojo-format pre-commit workaround.

## When to Use

- A file is annotated `DEPRECATED`, `# legacy`, or `# compatibility shim`
- A cleanup GitHub issue requests deleting a specific file or directory
- Consolidation left a re-export stub that duplicates a canonical location
- Post-reorganization: a `.mojo` stub remains alongside a newly created directory
- Deprecated skill directories reference a removed system (e.g. planning directories)
- `CLAUDE.md` Available Skills list contains skills that no longer exist

## Verified Workflow

### Quick Reference

```bash
# 1. Read the file to confirm it is a stub
cat <path/to/deprecated/file>

# 2. Grep ALL file types for references (not just source)
grep -r "<module_name>" . --include="*.mojo" --include="*.py" \
  --include="*.md" --include="*.yaml" --include="*.yml" -l

# 3. Delete (use git rm to stage atomically)
git rm <path/to/deprecated/file>

# 4. Update cross-references in docs, agent configs, scripts
grep -r "<module_name>" . -l   # verify nothing left

# 5. Run pre-commit (skip mojo-format if GLIBC incompatible)
SKIP=mojo-format pixi run pre-commit run --all-files

# 6. Commit, push, PR
git commit -m "cleanup(<scope>): delete deprecated <name>"
git push -u origin <branch>
gh pr create --title "..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

### Step 1: Confirm the file is truly a stub

Read the file. A safe-to-delete stub contains only:
- Docstrings or comments
- Redirect text (`"Use X for all new code"`)
- Zero executable code, zero exports

If it has real logic or exports, stop and escalate — do not delete.

### Step 2: Check branch/PR state first

```bash
git status
gh pr list --head <branch>
```

Prior automation may have already completed the work. Verify before proceeding.

### Step 3: Search for references across ALL file types

```bash
# Cast wide net — source code AND docs AND configs AND scripts
grep -r "<module_name>" . \
  --include="*.mojo" --include="*.py" \
  --include="*.md" --include="*.yaml" --include="*.yml" \
  -l
```

Key files to inspect:
- `__init__.mojo` / `__init__.py` in the **same directory** — may have backward-compat comments
- `CLAUDE.md` — Available Skills list
- `.claude/agents/*.md` — Skills tables and Delegation Patterns sections
- `docs/dev/*.md` — Architecture and pattern docs
- `scripts/*.py` — Code generators that emit references

Acceptable matches: the issue/prompt file itself, historical migration docs.
Blocking matches: any `import` or `from` statement in `.mojo`/`.py` files.

### Step 4: Mojo directory vs file resolution (Mojo-specific)

When both `schedulers.mojo` and `schedulers/` directory exist, Mojo resolves
`from shared.training.schedulers import X` to the **directory's `__init__.mojo`**.
The `.mojo` stub is shadowed and unused. Safe to delete once you confirm:

1. The directory and its `__init__.mojo` exist
2. No code uses file-extension-style imports (`schedulers.mojo` — these don't exist in Mojo)

### Step 5: Delete the file

```bash
git rm <path>          # stages atomically
# or for directories:
rm -rf .claude/skills/<name>/
git add -u
```

### Step 6: Update all cross-references

After deletion, re-run the grep sweep. For each remaining hit:

- `CLAUDE.md`: remove from Available Skills bullet list
- `.claude/agents/*.md`: remove rows from Skills tables and Delegation Patterns lists
- `docs/dev/*.md`: remove entire subsections for the deleted skill
- `scripts/*.py`: remove lines that emit deprecated references

### Step 7: Run pre-commit hooks

```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

`mojo-format` fails with GLIBC version mismatch in local environments — this is a pre-existing
infrastructure constraint, not caused by the deletion. All markdown, Python, and YAML hooks must pass.
CI will validate Mojo format.

### Step 8: Commit, push, create PR

```bash
git add <specific changed files>
git commit -m "$(cat <<'EOF'
cleanup(<scope>): delete deprecated <name>

<file> was a stub/re-export left after consolidation into <canonical-path>.
No active imports reference this file.

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin <branch>
gh pr create --title "cleanup(<scope>): delete deprecated <name>" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `pixi run mojo build` as validation | Executed build after deletion to confirm no breakage | GLIBC version mismatch prevented mojo from running (pre-existing env issue, not deletion-related) | Use pre-commit hooks as validation signal, not raw mojo build; GLIBC mismatch is a Docker-only env constraint |
| Searching only `.mojo` files for references | Grepped only source code for imports | Missed references in `__init__.mojo` comments and `.md` doc files | Always grep across ALL file types after deletion |
| Searching only `.md` files | Ran grep with `--include="*.md"` only | Missed `scripts/update_agents_claude4.py` which generates agent configs | Include `--include="*.py"` and all config types in grep sweep |
| Assuming only `CLAUDE.md` needed updates | Checked only CLAUDE.md initially | Missed 7 other files with references (agents, docs, scripts) | Always grep the entire repo before and after deleting to find all references |
| Not reading `__init__` in same directory | Deleted file without reading sibling `__init__.mojo` | It had a backward-compat comment referencing the deleted file | Always read the `__init__` file in the same directory before deleting |
| Not checking branch state first | Started deletion workflow from scratch | The deletion and PR were already pre-done by automation (`213f7566`) | Run `git status` and `gh pr list` before starting; work may already be done |
| Grepping the file itself for self-references | Searched deleted file for its own module name | Produced false positives (e.g., `from benchmarks import stats` inside `benchmarks/__init__.mojo`) | Grep the target file last; exclude it or mentally filter self-references |
| Using Glob to find skill dirs | `Glob("**/.claude/skills/plan-*")` | Returned no results despite dirs existing | Glob has path restrictions; use `ls` via Bash to confirm directory existence |

## Results & Parameters

**Safe-to-delete criteria checklist:**
- [ ] File contains only docstring/comments (zero executable code, zero exports)
- [ ] `git status` confirms no prior automation completed the work already
- [ ] Zero grep matches for the module name in `.mojo`/`.py` import statements
- [ ] For Mojo stubs: directory with `__init__.mojo` exists at the same level
- [ ] All cross-reference files updated (CLAUDE.md, agents, docs, scripts)

**Commit message template:**
```
cleanup(<scope>): delete deprecated <name>

Remove deprecated stub `<path>` left after consolidation into `<canonical-path>`.
No active imports reference this file. Update <doc-files> to reflect current state.

Closes #<issue>
```

**Pre-commit skip pattern:**
```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3062 - delete `tests/shared/fixtures/mock_models.mojo` | PR #3254 |
| ProjectOdyssey | Issue #3063 - delete plan-* skill directories (3 dirs, 8 files updated) | Merged |
| ProjectOdyssey | Issue #3066 - delete deprecated `benchmarks/__init__.mojo` | Merged |
| ProjectOdyssey | Cleanup of `shared/training/schedulers.mojo` stub (Mojo dir resolution) | Merged |
