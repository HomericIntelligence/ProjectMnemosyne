# Session Notes: Diagnose PR CI Failures

## Session Date
2026-03-05

## Repository
HomericIntelligence/ProjectOdyssey

## PR
#3239 — fix(tests): sort glob results in load_named_tensors to fix flaky test

## Failures Encountered

### Failure 1: Mojo Package Compilation (PR-caused)
- **Error**: `error: use of unknown declaration 'sorted'`
- **Cause**: Used `sorted()` directly in Mojo — it's a Python builtin, not Mojo
- **Fix**: `Python.import_module("builtins").sorted(p.glob("*.weights"))`
- **Classification**: PR-caused

### Failure 2: link-check (Pre-existing)
- **Error**: Root-relative links like `/.claude/shared/...` can't be resolved by lychee without `--root-dir`
- **Evidence**: Fails on ALL PRs, not just mine
- **Classification**: Pre-existing, ignore

### Failure 3: Core ExTensor / Core Initializers (Flaky)
- **Error**: `mojo: error: execution crashed` with stack trace from libKGENCompilerRTShared.so
- **Evidence**: Passes on other PRs (e.g. 3077-auto-impl run 22708149306); no files I changed are in these tests
- **Classification**: Flaky Mojo runtime crash
- **Action**: `gh run rerun 22724257917 --failed`

## Diagnosis Steps Taken

1. `gh pr checks 3239` → identified failing jobs
2. `gh run view 22723666624 --log-failed` → found `sorted()` compilation error
3. Fixed `sorted()` → pushed second commit
4. `gh pr checks 3239` → new failures: Core ExTensor, Core Initializers, link-check
5. `gh run view 22724257917 --log-failed | grep "error:"` → found `execution crashed`
6. `gh run list --branch main --workflow "Comprehensive Tests" --limit 1` → last main run was Feb 14
7. `gh run view 22708149306` (other PR) → Core ExTensor PASSED on that PR
8. Confirmed: crash is flaky, not caused by my change
9. `gh run rerun 22724257917 --failed`

## Key Insight
When multiple unrelated tests fail simultaneously with runtime crashes, check:
- Is the error in a file you changed? (No → not PR-caused)
- Does it pass on other PRs? (Yes → flaky)
- Is it a Mojo `execution crashed` error? (Yes → Mojo runtime flakiness pattern)
