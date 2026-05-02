---
name: ci-workflow-hardening-checklist
description: 'Harden GitHub Actions workflows with concurrency controls, least-privilege
  permissions, timeouts, and gitleaks allowlist for test fixtures. Use when: (1) workflows
  lack concurrency/cancel-in-progress controls, (2) gitleaks finds false positives
  in test fixtures or example data, (3) workflows missing permissions blocks or timeouts,
  (4) adding Trivy scanning to Docker build jobs.'
category: ci-cd
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
# CI Workflow Hardening Checklist

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-03-15 |
| Objective | Harden 6 GitHub Actions workflows with security and robustness improvements |
| Outcome | Operational — applied in ProjectScylla PR #1499 |

Covers the five most commonly missing hardening measures in mature CI setups that have grown organically: concurrency controls, least-privilege token permissions, job timeouts, gitleaks false positive suppression, and Trivy scanning for non-CI Docker images.

## When to Use

- Auditing existing CI workflows for the D-grade hardening gaps
- `gitleaks detect` finds hundreds of false positives in `tests/fixtures/` or example data dirs
- A workflow has no `timeout-minutes:` and runs up to GitHub's 6-hour default
- Workflows are missing `permissions:` blocks (default token has excessive write access)
- Multiple pushes to a PR branch queue up redundant CI runs
- Adding Trivy vulnerability scanning to a Docker build job that already builds the image
- Upgrading pytest reliability with `pytest-timeout` + `pytest-rerunfailures` plugins

## Verified Workflow

### Quick Reference

| Hardening Measure | Files | Impact |
| ------------------- | ------- | -------- |
| Concurrency + cancel | All workflows | Saves runner minutes on push chains |
| `permissions: contents: read` | 5 of 6 workflows | Limits blast radius of `GITHUB_TOKEN` |
| `timeout-minutes: 30` | `pre-commit.yml` only | Prevents 6-hour zombie jobs |
| `.gitleaks.toml` allowlist | New file + `security.yml` | Eliminates test fixture false positives |
| Trivy on build image | `docker-test.yml` | Catches vulns in experiment runner |
| `chmod 600` credentials | `docker_common.sh` | Fixes world-readable credential copy |
| `pytest-timeout` + `pytest-rerunfailures` | `pixi.toml`, `pyproject.toml` | Kills hung tests, retries flaky ones |

### Step 1: Add concurrency controls to ALL workflows

Every workflow gets this block between `on:` and `jobs:`:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.sha }}
  cancel-in-progress: true
```

**Why `head_ref || sha`**: `github.head_ref` is only set on `pull_request` events. For `push` events it's empty. The fallback to `sha` ensures push runs don't cancel each other (each SHA is unique), while PR runs do cancel stale runs on the same branch.

### Step 2: Add permissions to each workflow

Minimum viable: `contents: read`. Add `packages: write` only if the job pushes to a registry.

```yaml
# Standard (read-only — most workflows):
permissions:
  contents: read

# Registry push (ci-image.yml only):
permissions:
  contents: read
  packages: write
```

**Note**: Workflow-level `permissions:` applies to ALL jobs. If one job needs `packages: write` but others don't, move `permissions:` to the job level.

### Step 3: Add timeout to uncapped workflows

Pre-commit is the classic offender — pixi + pre-commit environment setup can stall:

```yaml
jobs:
  pre-commit:
    runs-on: ubuntu-latest
    timeout-minutes: 30  # Was uncapped (6hr default)
```

Rule of thumb: `timeout-minutes` ≤ 2× observed p99 runtime. For pre-commit: 30min. For test matrix: 30min. For Docker build: 20-30min.

### Step 4: Fix gitleaks false positives with .gitleaks.toml

**Problem**: `gitleaks detect --source . --verbose` finds 333 false positives in:
- `tests/fixtures/` — dummy API keys like `msk_test_123456789`, `msk_live_1234567890`
- `docs/paper-dryrun-data/` — experiment outputs containing example security scan skills

**Solution**: Create `.gitleaks.toml` at the repo root:

```toml
[allowlist]
  description = "Allowlist for test fixtures and dryrun data containing example API keys"
  paths = [
    '''tests/fixtures/''',
    '''docs/paper-dryrun-data/''',
  ]
```

Update the gitleaks command in `security.yml`:

```yaml
- name: Run gitleaks
  run: gitleaks detect --source . --config .gitleaks.toml --verbose
```

**Verify locally** before pushing:
```bash
gitleaks detect --source . --config .gitleaks.toml --verbose
# Should output: 0 leaks found
```

### Step 5: Add Trivy to an existing Docker build job

If the job already builds the image with `docker build`, tag it and scan in the same job:

```yaml
- name: Build cold (no cache)
  id: cold_build
  run: |
    docker build -f docker/Dockerfile -t scylla-experiment:trivy-scan . \
      --progress=plain --no-cache \
      2>&1 | tee /tmp/build_cold.log

- name: Scan experiment image for vulnerabilities (Trivy)
  uses: aquasecurity/trivy-action@0.30.0
  with:
    image-ref: scylla-experiment:trivy-scan
    format: table
    exit-code: 1
    ignore-unfixed: true
    severity: HIGH,CRITICAL
```

**Key**: Use a pinned version tag (`@0.30.0`), not `@latest` or `@main`. Use `ignore-unfixed: true` to avoid noise from vulnerabilities with no available fix.

### Step 6: Fix credential file permissions

In any shell script that copies credentials for container mounting:

```bash
# BEFORE (world-readable — any local user can read):
chmod 644 "${TEMP_CREDS_DIR}/.credentials.json"

# AFTER (owner-only):
chmod 600 "${TEMP_CREDS_DIR}/.credentials.json"
```

The container mount `:ro` flag prevents the container from writing, but the host-side `chmod` controls who can read the original copy.

### Step 7: Add pytest-timeout + pytest-rerunfailures

**pixi.toml**:
```toml
[dependencies]
pytest-timeout = ">=2.0,<3"
pytest-rerunfailures = ">=14.0,<15"
```

**pyproject.toml** (`[tool.pytest.ini_options]`):
```toml
timeout = 120  # 2 minutes per test — kills hung tests
```

**Integration tests only** — add reruns in the CI command, not in `addopts` (to avoid retrying fast unit tests):
```bash
pixi run pytest tests/integration -v \
  --reruns 2 --reruns-delay 5 \
  --junitxml="junit-integration.xml"
```

**Do NOT** add `--reruns` to `addopts` in `pyproject.toml` — it would apply to unit tests too, hiding bugs by retrying deterministic failures.

### Step 8: Add JUnit XML artifacts

```yaml
- name: Run tests
  env:
    TEST_PATH: ${{ matrix.test-group.path }}
  run: |
    JUNITXML="junit-${{ matrix.test-group.name }}.xml"
    pixi run pytest "$TEST_PATH" --junitxml="$JUNITXML" ...

- name: Upload test artifacts on failure
  if: failure()
  uses: actions/upload-artifact@v7
  with:
    name: test-results-${{ matrix.test-group.name }}
    path: |
      coverage.xml
      junit-${{ matrix.test-group.name }}.xml
    retention-days: 7
```

**Note**: `matrix.test-group.name` is safe to use directly in a shell variable — it's a static literal defined in the workflow matrix, not user-controlled input.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gitleaks/gitleaks-action@v2` | Used the official GitHub Action for gitleaks | Requires a paid Gitleaks license for org repos — produces auth errors in CI | Use gitleaks CLI directly: `curl ... \| tar xz gitleaks` then `gitleaks detect` |
| gitleaks without `--config` | Ran `gitleaks detect --source . --verbose` on a repo with test fixtures | Found 333 false positives in `tests/fixtures/` and `docs/paper-dryrun-data/` | Always create `.gitleaks.toml` allowlist before running gitleaks on repos with test data |
| `node:20-slim` pinned by SHA256 | Pinned base image by SHA256 digest in Containerfile | SHA256 digests for `node:20-slim` expired/rotated within 24 hours, breaking builds | Pin by version tag not SHA256 for actively maintained images; SHA256 only works for immutable registries |
| `docker --check` for Containerfile validation | Used `docker build --check` to validate Containerfile syntax | `--check` flag not available in Podman — command fails silently or errors | Use `hadolint` for Containerfile linting instead; `docker --check` is Docker-specific |
| concurrency group without `head_ref \|\| sha` fallback | Used only `github.head_ref` in concurrency group | Empty string on `push` events — all push runs share the same empty-string group and cancel each other | Always use `${{ github.head_ref \|\| github.sha }}` to handle both PR and push events |
| PR #1497 rebase (conflict) | Rebased `ci-container-workflows` branch onto main | Single conflict in `test.yml` on artifact `path:` format — one used scalar `coverage.xml`, other used YAML literal block scalar form | Both formats are valid YAML; resolve by keeping either; no functional difference |

## Results & Parameters

### Complete Hardening Audit Score (Before/After)

| Workflow | Concurrency | Permissions | Timeout | Grade |
| ---------- | ------------- | ------------- | --------- | ------- |
| `test.yml` | ✅ Added | ✅ Added | ✅ Existing 30m | A |
| `pre-commit.yml` | ✅ Added | ✅ Added | ✅ Added 30m | A |
| `shell-test.yml` | ✅ Added | ✅ Added | ✅ Existing 10m | A |
| `docker-test.yml` | ✅ Added | ✅ Added | ✅ Existing 10/20m | A |
| `security.yml` | ✅ Added | ✅ Added | ✅ Existing 15m | A |
| `ci-image.yml` | ✅ Added | ✅ Existing | ✅ Existing 30m | A |

### gitleaks CLI Install (Pinned Version)

```bash
GITLEAKS_VERSION="8.21.2"
curl -sSfL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
  | tar xz -C /usr/local/bin gitleaks
```

### pytest Plugins Version Constraints

```toml
# pixi.toml
pytest-timeout = ">=2.0,<3"        # 2.4.0 resolves
pytest-rerunfailures = ">=14.0,<15"  # 14.0 resolves
```

```toml
# pyproject.toml [tool.pytest.ini_options]
timeout = 120  # 2 minutes per test
```
