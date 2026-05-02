# Session Notes: fix-security-scan-gaps

## Context

- **Repo**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3143 — [P0-3] Fix security scanning to actually enforce on PRs
- **PR**: #3315
- **Branch**: 3143-auto-impl
- **Date**: 2026-03-05

## Problem Statement

Three gaps made security scanning ineffective as a PR gate:

1. `security-scan.yml` only had `push: branches: [main]` trigger — SAST and dependency
   scans ran only after merge, not before
2. Semgrep step had `continue-on-error: true` — any SAST finding would be silently ignored
   and the job would show green
3. Gitleaks in `security-pr-scan.yml` used `--no-git` — only scanned working directory files,
   missing any secrets in git history

## Files Modified

- `.github/workflows/security-scan.yml`: Added `pull_request:` trigger; removed
  `continue-on-error` from Semgrep step (lines 8 and 100)
- `.github/workflows/security-pr-scan.yml`: Removed `--no-git` from both Gitleaks
  invocations (lines 46 and 49 in original)

## Diff Summary

```diff
# security-scan.yml
+  pull_request:
+
   push:
     branches:
       - main

# security-scan.yml (Semgrep step)
-      continue-on-error: true   # removed from scan step

# security-pr-scan.yml (both branches of if/else)
-    ./gitleaks detect --source=. --config=.gitleaks.toml --verbose --no-git --exit-code=1
+    ./gitleaks detect --source=. --config=.gitleaks.toml --verbose --exit-code=1
-    ./gitleaks detect --source=. --verbose --no-git --exit-code=1
+    ./gitleaks detect --source=. --verbose --exit-code=1
```

## Tricky Part

`continue-on-error: true` appeared on 4 lines in `security-scan.yml`:
- Line 100: Semgrep scan step — **REMOVED** (this was the bug)
- Line 109: SARIF upload step — **KEPT** (legitimate, upload failure shouldn't block scan)
- Line 136: Dependency Review action — **KEPT** (supply-chain-scan job, already gated by `if: github.event_name == 'pull_request'`)
- Line 149: Checkout in security-report job — **KEPT** (report aggregation, not blocking)

The key insight: only the scan step itself needs to fail hard. Reporting/upload steps
can legitimately use `continue-on-error`.

## Validation

```bash
python3 -c "
import yaml
for f in ['.github/workflows/security-scan.yml', '.github/workflows/security-pr-scan.yml']:
    yaml.safe_load(open(f))
    print(f'OK: {f}')
"
# Output: OK for both files
```
