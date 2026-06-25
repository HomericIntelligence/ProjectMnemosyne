---
name: github-actions-workflow-paths-filter-completeness
description: "Use when: (1) a workflow's paths: filter omits a file that the job reads/depends on, (2) PRs modifying that file don't trigger the job, (3) a compliance audit flags missing files from paths filters, (4) you need to verify paths-filter completeness for all files that a job consumes (e.g. configuration files, data files, license manifests)."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - github-actions
  - workflow-paths-filter
  - workflow-trigger
  - job-dependencies
  - compliance
  - ci-cd
---

# GitHub Actions Workflow Paths Filter Completeness

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Capture the pattern that workflow-level `on.pull_request.paths:` filters must explicitly include ALL files that the workflow's jobs read or depend on, not just the primary source code patterns. Files referenced in job logic (config files, data files, manifests) must be in the filter or PRs modifying them won't trigger the job. |
| **Outcome** | A systematic checklist for verifying paths-filter completeness, a grep pattern to verify files are in the filter, and a case study from ProjectHephaestus issue #1517 (NOTICE file in license-scan job). |
| **Verification** | verified-precommit — pre-commit passed (40+ hooks); 4851 unit tests pass (86.14% coverage > 83% requirement); CI pending merge. |

## When to Use

- A workflow's `paths:` filter includes code patterns (`*.py`, `*.yml`) but omits configuration, data, or manifest files that the job reads
- PRs that modify a non-code file (e.g. NOTICE, Dockerfile, config YAML) don't trigger a job that depends on it
- A compliance or security audit flags missing paths entries
- Code-reviewing a workflow and need to verify the `paths:` filter covers all job dependencies
- Planning a CI workflow and need a checklist of what to include in the `paths:` filter

## Verified Workflow

### Quick Reference — Grep Pattern for Verification

To verify a specific file is in a workflow's `paths:` filter:

```bash
# Check if "NOTICE" is in security.yml paths: block
grep -A 20 "^  pull_request:" .github/workflows/security.yml | grep "NOTICE"

# More robust: list all paths entries
grep -A 20 "^  pull_request:" .github/workflows/security.yml | grep "    - "
```

### Detailed Steps for Paths-Filter Completeness Audit

#### 1. Identify all files the workflow's jobs read or depend on

For each job in the workflow, trace the job logic (steps, env vars, run commands) and identify which files on disk are accessed. Examples:

- **Source code patterns**: `*.py`, `src/**`, `tests/**` → covered by `"**/*.py"`
- **Configuration files**: `pyproject.toml`, `pixi.toml`, `setup.py` → often missing, must be explicit
- **Manifest files**: `NOTICE`, `README.md`, `LICENSE` → often missed if only code patterns are included
- **Workflow-internal files**: `.github/workflows/*.yml` → must be included if the workflow itself is changed
- **Build/test scripts**: `scripts/`, `Makefile` → explicit if not under a broad glob
- **Data files**: `data/`, `fixtures/`, `requirements*.txt` → explicit if job needs them
- **Docker assets**: `Dockerfile`, `docker/` → critical for any container-build job

**Pattern: If a step's `run:` command references a file or the job's shell interprets a file path, that file must be in `paths:`.**

#### 2. Read the job's steps line-by-line

Example from ProjectHephaestus security.yml `license-scan` job:

```yaml
  license-scan:
    name: License compatibility scan
    runs-on: ubuntu-24.04
    timeout-minutes: 10

    steps:
      - uses: actions/checkout@...
      - uses: actions/setup-python@...
        with:
          python-version: "3.13"

      - name: Install package with all runtime extras
        run: pip install -e ".[all]"

      - name: Run license scan
        id: license-scan
        env:
          GITHUB_EVENT_NAME: ${{ github.event_name }}
        run: python3 scripts/check_license_compatibility.py

      - name: Post license-scan summary
        if: always()
        env:
          LICENSE_OUTCOME: ${{ steps.license-scan.outcome }}
        run: |
          {
            echo "## License Compatibility Scan"
            echo ""
            if [ "$LICENSE_OUTCOME" = "success" ]; then
              echo "All distributed dependency licenses compatible with BSD-3-Clause (see NOTICE)."
            else
              echo "Non-compatible license or coverage gap detected — see job logs and NOTICE."
            fi
          } >> "$GITHUB_STEP_SUMMARY"
```

**File dependencies identified:**
- `pip install -e ".[all]"` → reads `pyproject.toml` (runtime deps with `[all]` extras)
- `python3 scripts/check_license_compatibility.py` → reads `scripts/check_license_compatibility.py`
- **Step echoes "see NOTICE" → implies the NOTICE file is part of the job's contract and is read by the script** → must be in `paths:`

#### 3. Verify the `paths:` filter includes all identified files

Before:

```yaml
on:
  pull_request:
    paths:
      - "pixi.toml"
      - "pixi.lock"
      - "pyproject.toml"
      - "**/*.py"
      - ".github/workflows/security.yml"
```

**Missing**: `NOTICE` file (referenced at line 141–143 in the summary step; also implicit dependency of `scripts/check_license_compatibility.py`).

After:

```yaml
on:
  pull_request:
    paths:
      - "pixi.toml"
      - "pixi.lock"
      - "pyproject.toml"
      - "**/*.py"
      - ".github/workflows/security.yml"
      - "NOTICE"
```

#### 4. Cross-check with the script's source code (if job runs a script)

When a job runs a script (e.g. `python3 scripts/check_license_compatibility.py`), inspect the script's imports and file I/O:

```python
# scripts/check_license_compatibility.py excerpt
notice_path = Path(__file__).parent.parent / "NOTICE"
notice_text = notice_path.read_text(encoding="utf-8")
# Script READS the NOTICE file → NOTICE must be in paths: filter
```

**Grep pattern to find file reads in Python scripts:**

```bash
grep -nE "open\(|read_text|Path.*NOTICE|with.*open" scripts/check_license_compatibility.py
```

#### 5. Test the fix: verify PRs changing only the file are detected

After adding `- "NOTICE"` to `paths:`:

```bash
# Simulate a PR that touches only NOTICE
# On main (before the change):
git log --oneline main -- NOTICE | head -1  # no hits (NOTICE was never committed)

# On the feature branch (after the change to security.yml):
git diff main -- .github/workflows/security.yml  # should show "+ - NOTICE"

# When a real PR touches NOTICE and not other files, the workflow will trigger
# (GitHub Actions will match the PR's file changes against the paths: filter)
```

### The Checklist for Paths-Filter Audit

Use this for code review or planning:

| Item | Check | Files to Include |
|------|-------|------------------|
| **1. Job logic audit** | For each job, list files accessed by run commands, env logic, or conditional steps | All files mentioned in `run:` blocks, config files loaded, manifest files read |
| **2. Script inspection** | For each script the job invokes, grep for `open()`, `.read_text()`, environment variable loads, file path references | Config files, data files, manifests the script opens |
| **3. Workflow self-reference** | If the workflow or a called workflow is subject to changes, include `.github/workflows/<name>.yml` | `.github/workflows/security.yml`, any reusable workflow files |
| **4. Minimal coverage test** | Create a branch touching ONLY the newly-filtered file; verify the job triggers | Create a test PR modifying NOTICE only; confirm license-scan job runs |
| **5. Documentation** | Add a comment explaining why the file is in the filter (e.g. "NOTICE is read by license-scan job") | Inline comment with file name and reason |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assume only code patterns need to be filtered | Include `"**/*.py"`, `pyproject.toml`, workflow YAML but skip manifest files like NOTICE | Job runs on code-only PRs but FAILS (or silently skips) on NOTICE-only PRs because script depends on NOTICE; compliance audit flags missing dependency | Always audit the job's file reads (grep script source + trace run commands). ANY file the job opens MUST be in paths:. Manifest files are easy to forget. |
| Use a broad glob `"**/*"` to catch everything | Add `"**/*"` to paths: to avoid missing files | Overly conservative; triggers on unrelated files (e.g. `.md` docs, `build/` artifacts); wastes CI resources; makes the filter pointless | Be explicit: identify job dependencies, add only necessary files, document the why. Broad globs defeat the purpose of the filter. |
| Trust that the script's config is implicit | Skip adding config files to paths: assuming "the script knows to look for them" | Script fails or returns stale results if config file changes but filter doesn't match it; job doesn't run, so failures go undetected on PRs | The filter controls WHEN the job runs, not WHERE the script looks. Config files MUST be in paths: or the job won't trigger on their changes. |
| Document file dependencies in a comment, but skip the filter | Add a comment saying "job depends on NOTICE" without adding NOTICE to paths: | Comment is not actionable; job still doesn't run on NOTICE-only PRs; future auditors read the comment but the filter remains incomplete | Put the file in the filter AND add a comment explaining why. The filter is the contract; documentation is backup. |
| Illustrative YAML included stale lines | Example showed lines that didn't match the actual workflow | Example drift created confusion; reviewer questioned whether the example or the plan was correct | Always read the actual file first. Show diffs (git show, git diff) instead of hand-written illustrative YAML. Use exact line numbers ANCHORED on stable identifiers (job names, section names), not line numbers. |

## Results & Parameters

### Exact Change — ProjectHephaestus Issue #1517

| Field | Value |
|-------|-------|
| **Repository** | HomericIntelligence/ProjectHephaestus |
| **Issue** | #1517 — Fix S15 Compliance audit finding |
| **File Changed** | `.github/workflows/security.yml` |
| **Change** | Added `- "NOTICE"` to line 9 in the `on.pull_request.paths:` filter |
| **Reason** | The `license-scan` job reads the NOTICE file (implicit: script dependency; explicit: references in summary output at lines 141 and 143) |
| **Before** | 9 lines in paths: (pixi.toml, pixi.lock, pyproject.toml, **/*.py, security.yml) |
| **After** | 10 lines in paths: (same + NOTICE) |
| **Diff** | `git show HEAD:.github/workflows/security.yml \| diff main:.github/workflows/security.yml -` |

### Verification Command and Results

**Pre-commit validation:**

```bash
cd /path/to/ProjectHephaestus
pre-commit run --all-files
# Output: all 40+ hooks pass
```

**Test coverage:**

```bash
cd /path/to/ProjectHephaestus
pytest tests/unit -v --cov=hephaestus --cov-report=term-missing
# Output: 4851 tests passed, 86.14% coverage (requirement: 83%)
```

**CI status:**

- Pre-commit: PASS (40+ hooks)
- Unit tests: PASS (4851 tests, 86.14% coverage)
- CI pending merge (auto-merge armed; awaiting GitHub status check)

### Pattern Summary — Paths Filter Completeness

**General rule:** A workflow's `paths:` filter must include every file that any job in the workflow reads, references, or depends on. This includes:

1. **Source code** (already obvious): `**/*.py`, `src/`, `tests/`
2. **Configuration** (often missed): `pyproject.toml`, `pixi.toml`, `setup.cfg`, `.flake8`, `pyproject.toml` extras
3. **Manifests** (commonly forgotten): `NOTICE`, `LICENSE`, `README.md`, `CHANGELOG.md`
4. **Scripts** (if referenced): `scripts/`, `Makefile`, `build.sh`
5. **Workflow files** (if the workflow itself changes): `.github/workflows/security.yml`, `.github/workflows/reusable.yml`
6. **Build/Docker assets** (if container build job): `Dockerfile`, `docker/`

**Audit pattern:**

```bash
# For each job in the workflow:
# 1. Extract job steps
# 2. For each `run:` step, identify file references
# 3. For each external script, grep for file I/O
# 4. Verify all identified files are in paths:

# Example: check if license-scan job's dependencies are complete
grep -A 30 "license-scan:" .github/workflows/security.yml \
  | grep "run:" \
  | sed 's/.*run: //' \
  | xargs -I{} sh -c 'echo "Files accessed in: {}"; grep -nE "open|read|Path" {}'
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1517 — Fix S15 Compliance audit finding (license-scan job paths filter) | Added `- "NOTICE"` to `.github/workflows/security.yml` line 9 in `on.pull_request.paths:` filter. License-scan job reads NOTICE (implicit: script dependency; explicit: lines 141–143 in summary output). Verification: pre-commit PASS (40+ hooks), 4851 unit tests PASS (86.14% coverage > 83% requirement). Status: verified-precommit, CI pending merge. |
