# Session Notes: CI/CD Phase 6 Optimization

**Date**: 2026-03-15
**Repository**: HomericIntelligence/ProjectOdyssey
**Branch**: main (changes not yet committed — working tree modifications)

## Context

Implementing CI/CD Phase 6 out of a multi-phase CI optimization plan:
- Phases 1-5 already complete (path filters, concurrency groups, test tiering, setup-pixi
  composite action, Mojo pkg cache, pip cache, podman abstraction, just test-timing recipe,
  validate_test_coverage.py bug fix, collect-test-timing.yml workflow)
- Phase 6 targets: slow test migration, pre-commit optimization, container CI, runner pinning,
  validation

## What Was Done

### Workstream 3: Pre-commit Changed Files Only
**File**: `.github/workflows/pre-commit.yml`

Changed `--all-files` to `--from-ref origin/$BASE_REF --to-ref HEAD` for PR events.
Used `env:` block to capture `github.event_name` and `github.base_ref` safely.

Key issue: Security hook blocked inline `${{ github.event_name }}` in shell — required
using env variables. Hook message: "GitHub Actions workflow injection risk".

Also added git fetch step since `actions/checkout` with default `fetch-depth: 1` doesn't
fetch the base branch ref.

### Workstream 4: Pin All Runners
**Files**: All 27 `*.yml` workflow files

Used single sed command:
```bash
for f in .github/workflows/*.yml; do
  sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"
done
```

Result: 63 replacements across 27 files. 2 remaining `ubuntu-latest` refs are in
`README.md` documentation examples (not actual workflow YAML) — intentionally left.

### Workstream 5: Dockerfile.ci Fix
**File**: `Dockerfile.ci`

Runtime stage (Stage 2) previously re-ran:
1. `curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash`
2. `COPY pixi.toml pixi.lock ./`
3. `RUN pixi install --frozen`

Replaced with:
```dockerfile
COPY --from=builder /root/.pixi /root/.pixi
COPY --from=builder /build/.pixi /app/.pixi
COPY pixi.toml pixi.lock ./
```

Also removed `curl` from `apt-get install` in runtime stage (no longer needed).
`pixi install` count: 2 → 1.

### Workstream 7: Speedup Report Script
**File**: `scripts/ci_speedup_report.py` (new)

Python script using `gh run list --json createdAt,updatedAt,conclusion,name,databaseId`.
Splits runs into:
- Recent: last 3 days
- Baseline: 7-14 days ago

Outputs markdown table with avg/min/max per window and speedup %.

## Workstreams NOT Implemented (blocked)

- **Workstream 1** (trigger timing workflow): Requires pushing to main first
- **Workstream 2** (migrate slow tests): Blocked on timing data from collect-test-timing.yml
- **Workstream 6** (Podman): No changes needed — already supported via `CONTAINER_ENGINE` abstraction

## Tool Issues Encountered

1. **Glob doesn't traverse hidden dirs**: `.github/workflows/*.yml` pattern returned "No files found".
   Solution: Use `ls` via Bash or direct path reads.

2. **Edit after Bash sed fails**: After `sed -i` modified a file, the Edit tool refused with
   "File has been modified since read". Must re-read after any Bash modification.

3. **Pre-commit security hook on workflow edits**: Hook blocked inline `${{ }}` expressions
   in `run:` commands. Must use `env:` block pattern.

## Verification Commands Used

```bash
# Runner pinning verification
grep -c "ubuntu-latest" .github/workflows/*.yml  # All show :0

# pre-commit
grep "from-ref" .github/workflows/pre-commit.yml  # Shows 2 lines

# Dockerfile
grep -c "pixi install" Dockerfile.ci  # Shows 1

# Test coverage
python scripts/validate_test_coverage.py  # Exit 0
```
