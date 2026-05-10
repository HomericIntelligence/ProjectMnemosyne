---
name: ci-cd-remove-upstream-fixed-workaround-fan-out-matrix
description: "Pattern for safely removing a CI matrix workaround once an upstream bug is fixed: convert sequential single-runner steps back to a multi-entry matrix. Each `just test-group` (or equivalent) invocation must remain its OWN step gated by `if: matrix.group == 'X'` so coverage-validation parsers (which scan `run:` blocks for literal command invocations) keep working. Use when: (1) a memory/concurrency limit was lifted upstream, (2) you have a sequential job to fan out into a parallel matrix, (3) a coverage-checking script complains about missing test files after collapsing steps into a case statement."
category: ci-cd
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - github-actions
  - matrix
  - fan-out
  - sequential
  - validate_test_coverage
  - mojo
  - modular
  - workaround-removal
---

# Removing an Upstream-Fixed CI Workaround: Fan-Out a Sequential Job into a Matrix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-10 |
| **Objective** | modular/modular#6433 (Mojo compiler unconditionally reserves ~3.6 GB virtual address space, OOM-crashing GHA free-tier 7 GB runners with parallel matrix jobs) was fixed upstream and shipped in the pinned nightly. Two surface workarounds had to be removed: 24-step sequential test-mojo-comprehensive job + single-element placeholder matrix on test-configs. |
| **Outcome** | Workflow fanned out into 6-entry matrix (core-tensors-loss, core-gradient-utils, data, autograd-tensor-base, models-misc, integration-bench). Each `just test-group` invocation kept as its OWN step with `if: matrix.group == 'X'` so `scripts/validate_test_coverage.py` (regex over `run:` blocks) still sees every (path, pattern) pair. test-configs returned to a plain non-matrix job. |
| **Verification** | verified-precommit (YAML valid, validate_test_coverage.py exit 0; CI run pending) |

## When to Use

- An upstream bug that forced a CI workaround has been fixed (confirm via the upstream issue's "fixed" comment + your pinned dependency version postdating the fix's commit)
- You're considering converting a long sequential job back to a matrix to recover wall-clock time
- You collapsed a sequential job into a single step using `case "$VAR" in ... esac`, and a coverage-checking script that scans `run:` blocks now reports "uncovered test files" in its hundreds — the parser only saw the first command per `run:` block
- You need to keep `matrix:` and `fail-fast: false` literals in the workflow file to satisfy grep-based smoke-tests

## Verified Workflow

### Quick Reference

```yaml
# AFTER (good): each test invocation is its own step, gated by matrix.group
strategy:
  fail-fast: false
  matrix:
    group:
      - group-a
      - group-b
      # ...
steps:
  - name: "Group A test 1"
    if: matrix.group == 'group-a'
    run: just test-group "tests/path1" "test_*.mojo"
  - name: "Group A test 2"
    if: matrix.group == 'group-a'
    run: just test-group "tests/path2" "test_*.mojo"
  - name: "Group B test 1"
    if: matrix.group == 'group-b'
    run: just test-group "tests/path3" "test_*.mojo"
```

### Detailed Steps

1. **Confirm the upstream fix is in your pinned dep.** `gh issue view <N> --repo modular/modular --comments` → look for "fixed in nightly X" and confirm your pin postdates X.
2. **Inventory the workaround surface.** `grep -rn "<upstream-issue-number>" .github/workflows/ docs/ scripts/`. Both surface comments AND structural artefacts (single-element matrices, `max-parallel: 1`) count.
3. **Plan the fan-out.** Group the sequential steps into 4-6 matrix entries that roughly balance per-runner wall-clock. Don't go to 1-step-per-entry unless the steps are truly independent and CI minutes are cheap.
4. **Each test invocation stays its own `- name:` step, gated by `if: matrix.group == 'X'`.** This is the critical anti-pattern fix below — scripts like `validate_test_coverage.py` parse `run:` blocks with a regex like `just\s+test-group\s+"?([^\s"]+)"?\s+"?(.+?)(?:"?\s*$|$)` which captures only the FIRST `just test-group` per block. Multi-command steps look like one giant pattern blob to the parser.
5. **Verify required-check name impact.** `gh api repos/<org>/<repo>/branches/<branch>/protection --jq '.required_status_checks.contexts'` — make sure the original job name isn't in the required-checks list. When matrixed, GHA renames the job to `<name> (<matrix-value>)` which won't match.
6. **Verify smoke-test literals still appear.** Tools like `Other Workflow Property Checks` grep for `matrix:` + `fail-fast: false` literals. The new fan-out's matrix supplies these organically — placeholder single-element matrices elsewhere can be removed.
7. **Run the local validator before committing.** `python3 scripts/validate_test_coverage.py` (or your equivalent) MUST pass.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Collapsed all 24 sequential steps into ONE step using `case "$GROUP" in ... esac` containing every `just test-group` invocation | `scripts/validate_test_coverage.py` reported 185 uncovered test files. Its regex over each step's `run:` body captured only the first `just test-group` per block; everything after was mashed into a single pattern string the parser couldn't decode. | Coverage parsers see steps, not commands. Keep one command per step even when the case-block looks cleaner. |
| 2 | Removed the `test-configs` placeholder matrix as part of the same change without first re-adding `matrix:` literals elsewhere | `Other Workflow Property Checks` and `Security Workflow Property Checks` grep for the literal strings `matrix:` and `fail-fast: false` somewhere in the workflow file. If neither exists, both checks fail. | If you remove a matrix used as a placeholder, ensure another matrix in the same file supplies the required literals. The new test-mojo-comprehensive matrix did. |
| 3 | Naïvely changed the sequential job to use a matrix without checking branch-protection required checks | Required check name `Comprehensive Mojo Tests` would have changed to `Comprehensive Mojo Tests (group-name)`, breaking the protection rule and blocking all merges. (Caught in pre-flight `gh api` check; would have been a self-DoS otherwise.) | Always `gh api ... protection --jq '.required_status_checks.contexts'` BEFORE adding a matrix to a job whose name might be a required check. |
| 4 | Pre-commit hook reformatted the workflow file mid-commit; the original `git commit` silently failed because the file was modified after staging | A subsequent `git commit -m "..."` showed "Everything up-to-date" on push — confusing because the `git status` still showed staged changes. | After pre-commit reformats your file, the commit DID NOT happen. Re-run `git commit` to pick up the reformatted staged content. |

## Results & Parameters

```yaml
# Recipe template — replace <test-group> with your project's actual test runner

strategy:
  fail-fast: false  # required literal for many smoke-tests
  matrix:
    group:           # required literal for many smoke-tests
      - group-a
      - group-b

steps:
  - name: "Group A: subset 1"
    if: matrix.group == 'group-a'
    run: <test-group> "<path1>" "<pattern>"

  - name: "Group A: subset 2"
    if: matrix.group == 'group-a'
    run: <test-group> "<path2>" "<pattern>"

  - name: "Group B: subset 1"
    if: matrix.group == 'group-b'
    run: <test-group> "<path3>" "<pattern>"
```

Pre-flight checks before merging:

```bash
# 1. YAML valid
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/<file>.yml'))"

# 2. Coverage parser still sees all paths
python3 scripts/validate_test_coverage.py

# 3. Required-check names not impacted
gh api repos/<org>/<repo>/branches/<branch>/protection --jq '.required_status_checks.contexts' \
  | grep -F "<original-job-name>" || echo "OK — not a required check"

# 4. Smoke-test literals still present
grep -E "matrix:|fail-fast: false" .github/workflows/<file>.yml
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5381 — removing modular/modular#6433 workaround once Mojo nightly 1.0.0b2.dev2026050805 (postdating modular@99c4bfc9d6) was pinned | Sequential 24-step test-mojo-comprehensive job → 6-entry matrix; placeholder test-configs matrix removed |
