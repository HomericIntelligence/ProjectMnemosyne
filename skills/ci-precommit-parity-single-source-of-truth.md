---
name: ci-precommit-parity-single-source-of-truth
description: "Architecture pattern: make .pre-commit-config.yaml the single source of truth for all linting; CI runs `pre-commit run --all-files` instead of duplicating lint steps. Use when: (1) CI and pre-commit run different linters or different file scopes causing silent divergence, (2) a new linter exists in CI but not locally (or vice versa), (3) shellcheck in CI covers .sh but not .bats while pre-commit covers both, (4) yamllint in CI covers agents/ but pre-commit covers all .yaml, (5) consolidating N separate CI lint jobs into one pre-commit parity job."
category: ci-cd
date: 2026-04-28
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [pre-commit, shellcheck, yamllint, actionlint, gitleaks, parity, lint, ci-cd]
---

# CI ↔ Pre-commit Parity Architecture

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Eliminate silent divergence between what CI linters catch and what pre-commit catches locally; make coverage identical |
| **Outcome** | Successful — all CI lint jobs collapsed to one `pre-commit run --all-files` job; gitleaks, actionlint, yamllint (all .yaml), shellcheck (.sh + .bats) all running identically in CI and locally |
| **Verification** | verified-local — pre-commit run --all-files passes; CI run pending |
| **History** | none |

## When to Use

- CI runs shellcheck on `*.sh` but pre-commit also runs it on `*.bats` — or vice versa
- A linter added to CI was never added to `.pre-commit-config.yaml`
- You discover CI and pre-commit diverge: one catches a violation the other misses
- You want to collapse N separate CI lint steps into one maintainable job
- Adding a new linter to the project and need to wire it up correctly
- yamllint in CI only covers `agents/` but all `.yaml` files should be linted

## Verified Workflow

### Quick Reference

```bash
# 1. Add new linter ONLY to .pre-commit-config.yaml
# 2. CI job runs this exact command:
pixi run --environment lint pre-commit run --all-files --show-diff-on-failure

# 3. Test locally:
pre-commit run --all-files

# 4. Test a single hook:
pre-commit run shellcheck --all-files
pre-commit run actionlint --all-files
pre-commit run yamllint --all-files
```

### Detailed Steps

1. **Declare `.pre-commit-config.yaml` as single source of truth** — add comment header:
   ```yaml
   # Source of truth for all linting.
   # CI runs `pre-commit run --all-files` via validate.yml.
   # Do not add CI-only linters here.
   ```

2. **Collapse CI lint steps** — replace all standalone lint steps with one job:
   ```yaml
   jobs:
     pre-commit:
       name: Pre-commit (parity)
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0  # gitleaks needs history
         - uses: ./.github/actions/setup-pixi
           with:
             environment: lint
         - run: pixi run --environment lint pre-commit run --all-files --show-diff-on-failure
   ```

3. **Ensure shellcheck covers `*.bats`** — in `.pre-commit-config.yaml`:
   ```yaml
   - repo: https://github.com/shellcheck-py/shellcheck-py
     rev: a23f6b85d0fdd5bb9d564e2579e678033debbdff  # v0.10.0.1
     hooks:
       - id: shellcheck
         args: [--severity=warning]
         files: '\.(sh|bats)$|(^|/)pre-commit$'
   ```
   Mirror the same pattern in `scripts/lint-shell.sh` and the `pixi.toml` `lint-shell` task:
   ```bash
   find scripts tests hooks \( -name '*.sh' -o -name '*.bats' -o -name 'pre-commit' \) \
     | xargs shellcheck --severity=warning
   ```

4. **Broaden yamllint to all YAML** — replace `files: '^(agents|fleets)/.*\.yaml$'` with:
   ```yaml
   - repo: https://github.com/adrienverge/yamllint
     rev: 81e9f98ffd059efe8aa9c1b1a42e5cce61b640c6  # v1.35.1
     hooks:
       - id: yamllint
         args: [-d, relaxed]
         files: '\.ya?ml$'
   ```
   This catches long lines in `.github/workflows/*.yml`, `agents/`, `fleets/`, `schemas/`, etc.

5. **Add actionlint** (catches workflow YAML shellcheck issues locally):
   ```yaml
   - repo: https://github.com/rhysd/actionlint
     rev: v1.7.7   # MUST be a git tag, not a commit SHA — see Failed Attempts
     hooks:
       - id: actionlint
   ```

6. **Add gitleaks** (binary mode, no license required):
   ```yaml
   - repo: https://github.com/gitleaks/gitleaks
     rev: v8.24.3
     hooks:
       - id: gitleaks
   ```

7. **Rule for future additions**: Any new linter goes into `.pre-commit-config.yaml` first. CI picks it up automatically. Never add a CI-only linter step outside `.pre-commit-config.yaml`.

8. **Rule for fixing long lines** (yamllint 80-char relaxed default): use YAML folded scalars (`>-`) rather than relaxing the rule:
   ```yaml
   taskDescription: >-
     Long description that wraps
     across multiple lines — folded scalar collapses newlines to spaces.
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Divergent CI lint steps | Running shellcheck only on `*.sh` in CI while pre-commit also covered `*.bats` | SC2034/SC2120 violations in `.bats` files passed CI but blocked pre-commit | Always make CI and pre-commit use identical file patterns |
| yamllint scoped to agents/ | CI ran `yamllint agents/` but `.github/workflows/*.yml` had long lines | Workflow files with >80 char lines passed CI yamllint but failed pre-commit | Broaden yamllint to all `\.ya?ml$`; fix lines rather than narrowing scope |
| CI-only actionlint step | `actionlint -shellcheck shellcheck` ran in validate.yml but not in pre-commit | SC2015 violations in `_required.yml` caught by CI but not locally before push | Add actionlint to pre-commit so violations are caught at commit time |
| Separate CI jobs for each linter | Individual lint, shellcheck, yamllint, actionlint jobs in separate YAML blocks | Any new linter required editing 2 files (workflow + pre-commit); drift inevitable | Single `pre-commit run --all-files` CI job; `.pre-commit-config.yaml` is authoritative |

## Results & Parameters

**Pre-commit hooks that must be present for full parity** (Myrmidons pattern):

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: cef0300fd0fc4d2a87a85fa2093c6b283ea36f4b  # v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        args: [--allow-multiple-documents]

  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: a23f6b85d0fdd5bb9d564e2579e678033debbdff  # v0.10.0.1
    hooks:
      - id: shellcheck
        args: [--severity=warning]
        files: '\.(sh|bats)$|(^|/)pre-commit$'

  - repo: https://github.com/rhysd/actionlint
    rev: v1.7.7
    hooks:
      - id: actionlint

  - repo: https://github.com/adrienverge/yamllint
    rev: 81e9f98ffd059efe8aa9c1b1a42e5cce61b640c6  # v1.35.1
    hooks:
      - id: yamllint
        args: [-d, relaxed]
        files: '\.ya?ml$'

  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.3
    hooks:
      - id: gitleaks
```

**CI job template** (replaces all standalone lint jobs):

```yaml
pre-commit:
  name: Pre-commit (parity)
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: ./.github/actions/setup-pixi
      with:
        environment: lint
    - run: >-
        pixi run --environment lint
        pre-commit run --all-files --show-diff-on-failure
```

**CLAUDE.md invariant to document**:
> `.pre-commit-config.yaml` is the single source of truth for all linting.
> CI's `Pre-commit (parity)` job runs `pre-commit run --all-files`.
> Adding a linter? Add it to `.pre-commit-config.yaml`. It runs in CI automatically.
> Never add CI-only linters.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Myrmidons | fix/ci-precommit-parity PR — closed CI divergence across shellcheck/yamllint/actionlint/gitleaks | 2026-04-28 |
