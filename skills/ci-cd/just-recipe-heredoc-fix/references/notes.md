# Session Notes: just-recipe-heredoc-fix

## Session Date
2026-03-14

## What Was Being Implemented

CI/CD speedup post-implementation fixes for ProjectOdyssey, specifically a new `just test-timing`
recipe that runs all Mojo tests with per-file wall-clock timing and writes structured JSON output.

## The Bug

While adding `just test-timing` to `ProjectOdyssey/justfile`, the recipe used a heredoc to write
JSON lines to the output file:

```just
        cat >> "$OUTPUT" <<ENTRY
  {"file": "$test_file", "duration_s": $duration, "status": "$status", "attempts": $attempts_used}
ENTRY
```

This caused `just --list` to fail with:

```text
error: Recipe line has inconsistent leading whitespace. Recipe started with `    ` but found line with `  `
   ——▶ justfile:709:1
    │
709 │   {"file": "$test_file", "duration_s": $duration, "status": "$status", "attempts": $attempts_used}
    │ ^^
```

## Root Cause Analysis

`just` requires all lines in a recipe body (for `#!/usr/bin/env bash` shebang recipes) to share
the same leading whitespace. The recipe body used 4-space indentation throughout, but:

1. The heredoc content line had 2-space indent (for aesthetic JSON formatting)
2. The heredoc terminator `ENTRY` was at column 0 (required by bash for unquoted terminators)

Both violated `just`'s whitespace consistency requirement.

## Fix Applied

Replaced the heredoc with `printf`:

```just
        printf '  {"file": "%s", "duration_s": %s, "status": "%s", "attempts": %s}\n' \
            "$test_file" "$duration" "$status" "$attempts_used" >> "$OUTPUT"
```

This keeps all lines at 4-space indent (the recipe standard) while producing identical output.

## Other Items Implemented in Same Session

1. **`validate_test_coverage.py` bug fix**: Replaced hardcoded `jobs.get("test-mojo-comprehensive", {})`
   with a scan over all jobs for any with `strategy.matrix.test-group` — fixes false positives
   when nightly workflow uses job key `test-mojo-nightly`.

2. **`precommit-benchmark.yml` concurrency group**: Added standard `concurrency:` block after
   the `on:` section to cancel in-progress runs on new pushes.

## Verification

```bash
# Coverage script passes
python scripts/validate_test_coverage.py; echo "Exit: $?"
# Exit: 0

# Concurrency block present
grep -A3 "concurrency" .github/workflows/precommit-benchmark.yml

# Recipe appears in just listing
just --list | grep test-timing
# test-timing output="test-timing.json" # Run all Mojo tests with per-file timing, output JSON report
```
