# Session Notes: ADR-009 Audit & Issue Creation

## Context

Repository: HomericIntelligence/ProjectOdyssey
Date: 2026-03-06
Branch: 3013-auto-impl

CI on `main` was failing 13/20 runs due to Mojo v0.26.1 heap corruption
(`libKGENCompilerRTShared.so` JIT fault). ADR-009 mandated ≤10 `fn test_` per file.
Audit found 131 files exceeding the limit (worst: `test_matrix.mojo` with 64 tests).

## Files Audited

Used: `grep -c "^fn test_" <file>` for each `test_*.mojo`

Top violators:
- test_matrix.mojo: 64
- test_assertions.mojo: 61
- test_arithmetic.mojo: 58
- test_elementwise_dispatch.mojo: 47
- test_activations.mojo: 45
- (... 126 more files down to 11 tests)

## CI Group Mapping

Sourced from `.github/workflows/comprehensive-tests.yml`:
- Core Tensors: explicit file list (20 files)
- Core Elementwise: test_elementwise.mojo, test_elementwise_dispatch.mojo, etc.
- Testing Fixtures: wildcard `test_*.mojo` in tests/shared/testing/
- Shared Infra: wildcard + training/test_*.mojo (overlap issue)
- Models: test_*_layers.mojo

## Issue Creation Approach

Wrote `/tmp/create_adr009_issues.py` with:
- VIOLATING_FILES list (114 entries ordered by test count desc)
- compute_split(n) = ceil(n/8)
- make_issue_body() generating structured markdown
- create_issue() calling `gh issue create`
- `--start N M` CLI args for index range batches

## What Went Wrong

Batch 1 (0-9): OK, 9 issues created (#3396-#3404)
Batch 2 (9-20): OK, 11 issues created (#3405-#3415)
Batch 3 (20-55): 1 x 502 error (test_progress_bar), 34 issues created

Then ran `--start 55 115` in background (run_in_background=True).
Also ran a separate retry for test_progress_bar in background.
Both background tasks completed but the batch task had hit a 502 error
early and the task system re-executed from index 0, creating duplicate
waves totalling 105 extra issues.

Closed duplicates in 3 rounds:
- Round 1: 41 duplicates closed
- Round 2: 64 duplicates closed
- Round 3: 8 duplicates closed

## Final State

- 131 file-split issues: #3396–#3638 (with gaps where duplicates were closed)
- 1 wildcard overlap issue: #3640
- Summary posted to #3330
- All issues: labels bug, testing, ci-cd; cross-ref #2942 and ADR-009

## Key Lessons

1. NEVER background a sequential `gh issue create` loop
2. Check `gh issue list` authoritatively after any failure — don't parse stdout
3. Break into batches of ≤20 and run each synchronously
4. Same-named files at different paths (test_validation.mojo x2, test_integration.mojo x2)
   are legitimate — don't close them as duplicates
5. GitHub 502 errors are transient — just retry the specific failed item