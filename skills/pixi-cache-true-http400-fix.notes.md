# Session Notes: pixi-cache-true-http400-fix

## Session Context

- **Date**: 2026-03-07
- **Issue**: #3341 — Extend setup-pixi composite to remaining 10 pixi-using workflows
- **Branch**: `3341-auto-impl`
- **PR**: #3966

## What Was Found

When starting the session, the implementation plan (from issue comments) indicated:

1. The composite action `.github/actions/setup-pixi/action.yml` already existed
2. All 10 target workflows already used `./.github/actions/setup-pixi` (the migration was done)
3. BUT the composite action itself still used `cache: ${{ inputs.cache }}` which defaulted to `true`
4. `prefix-dev/setup-pixi@v0.9.4` with `cache: true` fails with HTTP 400 from the GitHub cache service

## State Before Fix

```yaml
# .github/actions/setup-pixi/action.yml (broken)
name: Set Up Pixi Environment
description: Install Pixi and restore the cached environment.

inputs:
  pixi-version:
    description: Pixi version to install
    required: false
    default: latest
  cache:
    description: Whether to enable Pixi built-in caching
    required: false
    default: 'true'

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: ${{ inputs.pixi-version }}
        cache: ${{ inputs.cache }}    # HTTP 400!
```

## State After Fix

```yaml
# .github/actions/setup-pixi/action.yml (fixed)
name: Set Up Pixi Environment
description: Install Pixi with explicit ~/.pixi cache (avoids broken cache:true HTTP 400).

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: latest
      # DO NOT use cache: true — broken, fails with HTTP 400 from GitHub cache service

    - name: Cache pixi environments
      uses: actions/cache@v4
      with:
        path: |
          .pixi
          ~/.cache/rattler/cache
        key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
        restore-keys: |
          pixi-${{ runner.os }}-
```

## Key Discovery: Check Callers Before Removing Inputs

Before removing the `inputs:` block, ran:
```bash
grep -rn -A3 "uses: ./.github/actions/setup-pixi" .github/workflows/ | grep -E "pixi-version|cache:"
```
Result: no output — confirmed no callers pass `with:` blocks, so inputs could be safely removed.

## Workflows Already Converted (by Prior Work)

All 10 originally listed workflows were already using the composite action:
- `mojo-version-check.yml`, `paper-validation.yml`, `pre-commit.yml`, `release.yml`
- `script-validation.yml`, `test-data-utilities.yml`, `test-gradients.yml`, `type-check.yml`
- Note: `dependency-audit.yml` was merged into `security.yml` in issue #3149
- Note: `validate-configs.yml` has no pixi steps at all

## Related Skills

- `fix-composite-action-migration` — covers the case where workflows weren't yet using the composite action
- `github-actions-pytest-pixi` — general pixi + GitHub Actions pattern
- `github-actions-ci-speedup` — source of the broken `cache: true` HTTP 400 knowledge