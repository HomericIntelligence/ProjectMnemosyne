---
name: composite-action-expr-in-description
description: "GitHub Actions evaluates `${{ ... }}` expressions inside composite-action input `description` fields even though that field is documentation-only. Including `${{ runner.os }}` (or any non-`inputs.*` context name) inside an input description — even backtick-quoted as documentation — makes the action fail to load with `Unrecognized named-value: 'runner'`. Use plain placeholder text or escape the expression. Use when: (1) writing a composite action that documents the cache-key shape or other runner-context-using value in its input description, (2) seeing `TemplateValidationException` at action-load time with `runner.os` / `github.X` / other context names."
category: ci-cd
date: 2026-05-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [github-actions, composite-action, template-expression]
---

# Composite-Action Input Descriptions: Expressions Get Evaluated

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-27 |
| **Objective** | Document that GitHub Actions' template parser evaluates `${{ ... }}` inside composite-action input `description` fields, restricting which context names can appear in documentation |
| **Outcome** | Diagnosed and fixed a `TemplateValidationException` blocking three CI jobs on ProjectHephaestus PR #608 |
| **Verification** | verified-ci (CI flipped from FAILURE to passing on the fix commit `229591e`) |

## When to Use

- A composite action you authored fails to load with `Unrecognized named-value: 'runner'` (or `'github'`, `'env'`, etc.) and the line number points into an `inputs.<name>.description` block
- Writing a composite action and you want to document the cache key shape, runner-OS-specific paths, or any value that uses GitHub-Actions context names in its docstring
- Reviewing a composite-action PR that has any `${{ ... }}` inside an input description field — flag it before CI does

## Verified Workflow

### Quick Reference

```yaml
# BAD — fails to load with "Unrecognized named-value: 'runner'"
inputs:
  cache-key-prefix:
    description: >-
      Prefix for the cache key. The full key becomes
      `<prefix>-${{ runner.os }}-${{ hashFiles('pixi.lock') }}`.
    required: true

# GOOD — plain text placeholders
inputs:
  cache-key-prefix:
    description: >-
      Prefix for the cache key. The full key is composed as
      <prefix>-<runner.os>-<hashFiles(pixi.lock)>.
    required: true
```

### Detailed Steps

**The mechanism.** GitHub Actions parses every `description` field (even on input/output declarations in a composite action's `action.yml`) through the same template parser that handles `run:` blocks and `if:` conditions. The parser doesn't have a "documentation context" mode — it just sees `${{ ... }}` and tries to resolve the expression at template-load time.

In a composite action's `action.yml`, the resolution context for input descriptions is empty: `runner`, `github`, `env`, `steps`, `secrets`, and `matrix` are all undefined because the action hasn't been called yet. The only valid context name at that stage is `inputs.<name>` (referring to the action's own inputs).

So writing `${{ runner.os }}` inside an input description triggers:

```
Unrecognized named-value: 'runner'. Located at position 1 within
expression: runner.os
##[error]Failed to load /path/to/action.yml
```

…and every job that uses the action fails immediately with `Failed to load`, not at the step that actually needs `runner.os`.

**The fix** is to remove the `${{ ... }}` syntax from the docstring entirely. Two options:

1. **Plain placeholders** (recommended for cache-key shapes, file-path templates, etc.):

```yaml
description: >-
  The full key is composed as
  <prefix>-<runner.os>-<hashFiles(pixi.lock)>.
```

2. **Backtick-escape via fenced code** — does NOT work. The parser scans the entire description string for `${{` regardless of markdown/yaml context. Backticks are not an escape.

3. **YAML block escape** — does NOT work either. Single quotes, `>-`, `|-` all still pass the literal `${{` to the template parser.

The only reliable approach is to NOT use `${{ ... }}` syntax in descriptions. If you must reference a context name, use angle-bracket pseudo-syntax (`<runner.os>`) or just spell it out in prose.

**Where this matters** in composite actions:

- `inputs.<name>.description` — confirmed broken (this skill's source incident)
- `outputs.<name>.description` — same parser, same bug expected
- `runs.steps[].name` — interpolation here is INTENDED, will work
- `runs.steps[].run` — interpolation here is INTENDED, will work
- `branding.*` — text-only, unlikely to contain `${{`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Backtick-quoting the expression: `` `${{ runner.os }}` `` | Hope GitHub treats backticks as literal markdown | The template parser scans the raw string for `${{` regardless of surrounding characters. Backticks aren't an escape mechanism for expressions. | Markdown formatting doesn't escape template syntax |
| Single-quote YAML escape: `description: 'foo ${{ runner.os }} bar'` | Use YAML's single-quote-disables-interpolation rule | YAML single-quote disables YAML's own interpolation, but the value still gets handed to GitHub's template parser, which evaluates `${{ ... }}` regardless | YAML escapes operate on YAML; GHA expressions are a separate parsing pass |
| YAML block scalar with strip indicator: `description: >- foo ${{ runner.os }} bar` | Use block scalar to embed multi-line text | Same as above — block scalars escape YAML, not GHA expressions | |
| Move the description to a YAML comment above the input | Sidestep the parser by using YAML comments instead of the description field | Comments are not surfaced in the action's published metadata (`gh api repos/owner/repo/contents/.github/actions/foo/action.yml` consumers, the GitHub Marketplace listing, IDE tooltips) | Comments lose discoverability. Use plain text in the description, not comments. |
| Reading the `runner.os` value at action-call time and passing it as an input | Make the cache-key-prefix input take a fully-resolved value | Pushes the caller to embed `${{ runner.os }}` at the usage site, which works (caller context HAS `runner`), but loses the encapsulation benefit | Workable but undermines the whole point of the composite action; only do this if you genuinely want each caller to compute their own cache key |

## Results & Parameters

**Specific incident (ProjectHephaestus 2026-05-27):**

- Composite action at `.github/actions/setup-pixi-env/action.yml` with `cache-key-prefix.description` containing the literal cache shape: `` `<prefix>-${{ runner.os }}-${{ hashFiles('pixi.lock') }}` ``
- Three CI jobs failed at the `uses: ./.github/actions/setup-pixi-env` step before reaching the body of the action: `lint`, `shell-tests`, `security/dependency-scan`.
- Error message (verbatim, useful for grep when diagnosing the same issue elsewhere):

```
##[error]/home/runner/work/<repo>/<repo>/./.github/actions/setup-pixi-env/action.yml (Line: 35, Col: 18): Unrecognized named-value: 'runner'. Located at position 1 within expression: runner.os
##[error]GitHub.DistributedTask.ObjectTemplating.TemplateValidationException: The template is not valid.
##[error]Failed to load /home/runner/work/<repo>/<repo>/./.github/actions/setup-pixi-env/action.yml
```

- Fix: 2-line edit replacing `` `<prefix>-${{ runner.os }}-${{ hashFiles('pixi.lock') }}` `` with `<prefix>-<runner.os>-<hashFiles(pixi.lock)>` in the description.
- Fix commit: `229591e` on ProjectHephaestus PR #608.
- CI result post-fix: the three failing jobs were re-run and reached the body of the action (then hit unrelated coverage/lint issues, eventually all green).

**Detection one-liner** for any composite action you author or review:

```bash
# Flag any ${{ ... }} expression inside an input/output description block.
# Run from repo root.
yq '.inputs[]? | .description' .github/actions/*/action.yml 2>/dev/null | grep -nE '\$\{\{'
yq '.outputs[]? | .description' .github/actions/*/action.yml 2>/dev/null | grep -nE '\$\{\{'
```

If those greps return anything, that's a candidate for this bug.

**Allowed expression contexts in composite action descriptions:**

Per the GitHub Actions docs (https://docs.github.com/en/actions/learn-github-actions/expressions and https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions), the documented context for composite actions covers `inputs`, `github`, `runner`, `env`, `vars`, `secrets`, `steps`, `jobs`, `needs`, `strategy`, `matrix`, `hashFiles`, `format`, plus a few others. But ONLY `inputs.<name>` is resolvable at the action-metadata-load time when descriptions are parsed. All other context names raise `Unrecognized named-value`. So even if you have a legitimate reason to interpolate something into a description, only `${{ inputs.<other-name> }}` will work — and that's rarely useful for documentation.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #608 — extracted `setup-pixi-env` composite action from `_required.yml` | Three jobs (lint, shell-tests, security/dependency-scan) failed at the `uses:` step with `TemplateValidationException: Unrecognized named-value: 'runner'`. Fix commit `229591e` flipped them green. Description originally embedded `` `<prefix>-${{ runner.os }}-${{ hashFiles('pixi.lock') }}` `` as a backtick-quoted documentation example; rewriting as plain `<prefix>-<runner.os>-<hashFiles(pixi.lock)>` made the parser stop trying to evaluate it. |
