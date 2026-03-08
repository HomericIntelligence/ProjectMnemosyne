---
name: pre-commit-version-alignment
description: "Align pre-commit hook versions with pixi/conda resolved package versions to eliminate local vs CI behavior drift. Use when: pre-commit rev differs from pixi.toml version, or linter behavior differs between pre-commit and pixi run."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Skill** | pre-commit-version-alignment |
| **Category** | ci-cd |
| **Complexity** | Low |
| **Time** | ~5 minutes |
| **Risk** | Low — single-line config change |

Align the `rev:` field in `.pre-commit-config.yaml` for tools like `mirrors-mypy` with the
version that pixi actually resolves. This prevents silent behavioral differences where
`pixi run mypy` and the pre-commit hook run different mypy versions and may disagree on
type errors.

## When to Use

- Pre-commit hook `rev:` is pinned to an old version while `pixi.toml` has been upgraded
- `pixi run mypy` reports different errors than `git commit` triggers
- A follow-up issue flags a version mismatch after a pixi dependency upgrade
- Dependency audit discovers `mirrors-mypy` rev lags behind pixi-resolved version

## Verified Workflow

1. **Identify the mismatch** — compare `rev:` in `.pre-commit-config.yaml` with the
   `mypy =` constraint in `pixi.toml`:

   ```bash
   grep -A1 "mirrors-mypy" .pre-commit-config.yaml
   grep "mypy" pixi.toml
   ```

2. **Find the resolved version** — run the installed binary:

   ```bash
   pixi run mypy --version
   # Output: mypy 1.19.1 (compiled: yes)
   ```

3. **Update the `rev:` field** — change `v1.8.0` → `v{resolved-version}`:

   ```yaml
   # .pre-commit-config.yaml
   - repo: https://github.com/pre-commit/mirrors-mypy
     rev: v1.19.1   # was v1.8.0
   ```

4. **Verify pre-commit installs and runs cleanly**:

   ```bash
   just pre-commit-all
   # or: pixi run pre-commit run --all-files
   ```

5. **Commit and open PR**:

   ```bash
   git add .pre-commit-config.yaml
   git commit -m "fix(pre-commit): upgrade mirrors-mypy rev from v1.8.0 to v1.19.1

   Closes #<issue-number>"
   git push -u origin <branch>
   gh pr create --title "fix(pre-commit): upgrade mirrors-mypy rev" \
     --body "Closes #<issue-number>"
   gh pr merge --auto --rebase
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Pinning to `>=1.19.1` | Tried using a semver range in the `rev:` field | `rev:` only accepts exact git tags, not semver ranges | Always use an exact tag (e.g. `v1.19.1`) matching the installed binary |
| Guessing the tag | Assumed v1.19.0 from pixi constraint `>=1.19.1` | pixi resolves to the latest satisfying version; `mypy --version` gives the actual installed version | Always run `pixi run mypy --version` rather than inferring from the constraint |

## Results & Parameters

### Canonical Update Pattern

```yaml
# Before
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0

# After — matches `pixi run mypy --version`
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.19.1
```

### Commit Message Template

```text
fix(pre-commit): upgrade mirrors-mypy rev from vOLD to vNEW

Align the mirrors-mypy pre-commit hook revision with the mypy version
resolved by pixi (>=1.19.1,<2), eliminating the version mismatch where
`pixi run mypy` and the pre-commit hook could behave differently.

Closes #<issue>
```

### General Pattern (any mirrored pre-commit hook)

```bash
# 1. Find current rev
grep -A1 "<hook-name>" .pre-commit-config.yaml

# 2. Find pixi-resolved version
pixi run <tool> --version

# 3. Update rev to match exactly
# 4. Commit + PR
```
