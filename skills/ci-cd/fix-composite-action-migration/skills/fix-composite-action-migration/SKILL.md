---
name: fix-composite-action-migration
description: "Fix incomplete GitHub Actions composite action migration and redundant double-caching. Use when: jobs still call a third-party action directly instead of using a composite wrapper, or a composite action duplicates caching the wrapped action already handles."
category: ci-cd
date: 2026-03-05
user-invocable: false
---

# Fix Composite Action Migration

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-05 |
| Objective | Fix two common issues when introducing GitHub Actions composite actions: incomplete job migration and redundant double-caching |
| Outcome | All jobs use composite action; no cache key conflicts |

## When to Use

- A new composite action wrapper was created (e.g. `.github/actions/setup-pixi`) but some jobs in a workflow still call the underlying third-party action directly (e.g. `prefix-dev/setup-pixi@v0.9.4`)
- A composite action adds an `actions/cache` step on top of a wrapped action that already has `cache: true` built in — causing duplicate cache keys and unnecessary overhead
- PR review feedback identifies incomplete migration or redundant caching in GitHub Actions workflows

## Verified Workflow

1. **Read the composite action file** — identify all steps, especially any `actions/cache` steps layered on top of a wrapped action that handles caching itself

2. **Check if the wrapped action already caches** — e.g. `prefix-dev/setup-pixi@v0.9.4` with `cache: true` already caches `~/.pixi` internally; adding another `actions/cache` for the same path creates conflicts

3. **Remove the redundant cache step** — delete the entire `actions/cache` step from the composite action; let the inner action handle it

4. **Find all remaining direct calls** in workflow files:

   ```bash
   grep -rn "prefix-dev/setup-pixi" .github/workflows/
   ```

5. **Replace each direct call** with the composite action reference:

   ```yaml
   # Before
   - name: Set up Pixi
     uses: prefix-dev/setup-pixi@v0.9.4
     with:
       pixi-version: latest
       cache: true

   # After
   - name: Set up Pixi
     uses: ./.github/actions/setup-pixi
   ```

6. **Verify no direct calls remain**:

   ```bash
   grep -n "prefix-dev/setup-pixi" .github/workflows/comprehensive-tests.yml
   # Expected: no output
   grep -n "actions/cache" .github/actions/setup-pixi/action.yml
   # Expected: no output
   ```

7. **Commit** — pre-commit hooks may auto-fix end-of-file newlines after editing YAML; re-stage the auto-fixed file and commit again

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #3340, issue #3149 | [notes.md](../references/notes.md) |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| First commit after removing cache step | Committed immediately after edit | `end-of-file-fixer` pre-commit hook modified the YAML file (missing trailing newline) and blocked commit | After editing YAML files, re-stage all auto-modified files before committing |
| Committing both files in one shot with original edits | Staged both workflow files without re-staging after hook ran | Hook fixed `action.yml` but it wasn't re-staged, so commit still failed | Always check which files were modified by hooks and re-stage them |

## Results & Parameters

**Pattern: Remove redundant `actions/cache` from composite action**

Before (`setup-pixi/action.yml`):

```yaml
runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: ${{ inputs.pixi-version }}
        cache: ${{ inputs.cache }}

    - name: Cache Pixi environments
      uses: actions/cache@v5
      with:
        path: ~/.pixi
        key: pixi-${{ runner.os }}-${{ hashFiles('pixi.toml') }}
        restore-keys: |
          pixi-${{ runner.os }}-
```

After (remove the `Cache Pixi environments` step entirely):

```yaml
runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: ${{ inputs.pixi-version }}
        cache: ${{ inputs.cache }}
```

**Commit workflow for YAML edits with pre-commit hooks:**

```bash
git add .github/actions/setup-pixi/action.yml .github/workflows/comprehensive-tests.yml
git commit -m "fix: migrate jobs to composite action and remove redundant caching"
# If end-of-file-fixer runs and modifies files:
git add .github/actions/setup-pixi/action.yml   # re-stage the fixed file
git commit -m "fix: migrate jobs to composite action and remove redundant caching"
```
