# Session Notes — bare-mojo-call-lint-guard

## Context

Issue #3956 in ProjectOdyssey. Follow-up to #3329 (which applied retry logic to all
bare `pixi run mojo` calls). The ask: add a lint guardrail so new workflow files can't
introduce the same problem again.

## Files Changed

- `scripts/check_bare_mojo_calls.py` — new detector script
- `tests/scripts/test_check_bare_mojo_calls.py` — 23 unit tests
- `.pre-commit-config.yaml` — new `no-bare-pixi-mojo-calls` hook
- `.github/workflows/validate-workflows.yml` — new lint step + expanded path triggers
- `.github/workflows/docker.yml` — suppression comment on smoke test call
- `.github/workflows/paper-validation.yml` — suppression comment
- `.github/workflows/release.yml` — suppression comments (2 calls)
- `.github/workflows/simd-benchmarks-weekly.yml` — suppression comment

## Violations Found Before Fix

```
paper-validation.yml:257  — inside retry loop
docker.yml:153            — smoke test with || echo (non-fatal)
release.yml:273           — inside retry loop (unit tests)
release.yml:305           — inside retry loop (integration tests)
simd-benchmarks-weekly.yml:49 — inside retry loop
```

`benchmark.yml` and `paper-validation.yml:324` were NOT flagged because they use
`pixi run mojo -I .` (no `test` or `run` subcommand directly after `mojo`).

## Key Design Insight

A pygrep pre-commit hook would have been simpler but has no suppression mechanism.
`language: system` with a Python script was necessary to support per-line suppression
comments so existing retry-wrapped calls don't need to be restructured.

## Gotcha

The CI step's own echo message triggered the linter when it contained the literal string
`pixi run mojo test|run`. Fixed by rephrasing the echo to avoid the exact match.
