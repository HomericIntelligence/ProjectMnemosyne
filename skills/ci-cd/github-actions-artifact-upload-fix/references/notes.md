# Session Notes: GitHub Actions Artifact Upload Fix

## Date

2026-03-15

## Issue

ProjectOdyssey #4006 — Add test-results artifact upload to comprehensive-tests workflow

## Root Cause Analysis

Three separate problems caused artifact upload failures:

1. **Matrix artifact names with spaces/&**: GitHub Actions artifact names cannot contain
   spaces or `&`. Names like `"Core Activations & Types"` produce unreliable behavior
   in the UI and `download-artifact` pattern matching.

2. **Non-matrix jobs with empty upload directories**: `test-configs`, `test-benchmarks`,
   and `test-core-layers` had `upload-artifact` steps pointing to `test-results/` but
   their run steps called `just test-group ...` directly without ever creating `test-results/`
   or writing any files into it. The upload step would succeed (no error) but upload
   an empty directory, so the `test-report` job would find zero JSON files for these groups.

3. **`date +%s` timing**: Minor portability issue — `$SECONDS` is a bash built-in that
   avoids a subprocess call.

## Fix Applied

- Added `sanitized-name` field to all 14 matrix entries
- Changed upload step from `matrix.test-group.name` to `matrix.test-group.sanitized-name`
- Rewrote run steps for 3 non-matrix jobs to: mkdir, capture pass/fail, write JSON, exit
- Changed `date +%s` to `$SECONDS`

## Key Observation

The `actions/upload-artifact` step does NOT fail when the `path:` directory doesn't exist
or is empty — it silently uploads nothing. This makes the bug invisible in CI logs unless
you specifically check that artifacts were downloaded with actual content.
