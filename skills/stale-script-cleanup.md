---
name: stale-script-cleanup
description: 'Remove stale one-time fix/migration scripts safely. Use when: scripts/
  directory has accumulated one-time scripts no longer needed, cleaning up before
  releases, or reducing contributor confusion.'
category: tooling
date: 2026-03-05
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Name** | stale-script-cleanup |
| **Category** | tooling |
| **Complexity** | S (Simple) |
| **Risk** | Low — deletions are reversible via git |

Safely identifies and removes one-time fix/migration scripts from a `scripts/` directory
that have accumulated during development. Ensures nothing is broken before deletion by
verifying no workflows or build recipes reference the scripts.

## When to Use

- GitHub issue requests removal of ~N stale fix/migration scripts
- `scripts/` directory has grown cluttered with one-time-use files
- New contributors are confused by scripts that are no longer relevant
- Pre-release cleanup to reduce maintenance surface area

## Verified Workflow

### Step 1: Confirm files exist

```bash
ls scripts/ | sort
```

### Step 2: Check for references in CI/workflows and build system

Run these checks in parallel — they are independent:

```bash
# Check GitHub Actions workflows and Justfile
grep -r "<script-name>" --include="*.yml" --include="*.yaml" --include="justfile" --include="Justfile" -l

# Check broader file types (Python, shell, markdown)
grep -r "<script-name>" --include="*.py" --include="*.sh" --include="*.md" -l
```

Key insight: References found only inside the scripts themselves (self-references),
blog posts, or notes are safe to ignore. Only references in CI workflows, Justfile
recipes, or active tooling scripts require keeping the file.

### Step 3: Delete confirmed stale scripts

```bash
rm scripts/fix_foo.py scripts/migrate_bar.sh scripts/create_baz.py
```

### Step 4: Update documentation

If `scripts/README.md` documents any deleted scripts, remove those sections.
Look for both the directory listing entry AND any full documentation sections.

```bash
grep -n "<deleted-script-name>" scripts/README.md
```

### Step 5: Validate with pre-commit

```bash
pixi run pre-commit run --all-files
# OR
just pre-commit-all
```

All hooks must pass before committing.

### Step 6: Commit, push, create PR

```bash
git add scripts/
git commit -m "cleanup(scripts): remove N stale one-time fix/migration scripts

Closes #<issue-number>"

git push -u origin <branch-name>
gh pr create --title "cleanup(scripts): remove stale scripts" \
  --body "Closes #<issue-number>" \
  --label "cleanup"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `just pre-commit-all` | Used `just` command runner | `just` was not in PATH on this system | Fall back to `pixi run pre-commit run --all-files` when `just` is unavailable |
| Using shell PID expansion for clone location | `MNEMOSYNE_DIR="build/$$/..."` pattern | `$$` expands unpredictably across different contexts; doesn't work across separate tool invocations | Use a fixed standardized path like `$HOME/.agent-brain/ProjectMnemosyne` instead |

## Results & Parameters

### Pre-commit hooks that run

- `mojo format` (Mojo files only — skipped for pure script cleanup)
- `markdownlint-cli2` — validates README.md edits
- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`
- `ruff-format`, `ruff-check` — for Python files
- `validate-test-coverage` — ensures no test files are orphaned

### Grep patterns for bulk reference check

```bash
# Build one grep pattern for all scripts at once
grep -r "fix_arithmetic_backward\|fix_code_fences\|fix_markdown" \
  --include="*.yml" --include="*.yaml" --include="justfile" -l
```

### Commit message format

```text
cleanup(scripts): remove N stale one-time fix/migration scripts

Brief description of what was deleted and verification done.

Closes #<issue-number>
```
