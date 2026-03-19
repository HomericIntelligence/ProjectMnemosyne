---
name: workflow-binary-sha256-verification
description: 'Add SHA256 checksum verification for binary downloads in GitHub Actions
  workflows to prevent supply chain attacks. Use when: a workflow downloads a binary
  via wget/curl without integrity verification before execution.'
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Goal** | Add SHA256 checksum verification for binary downloads in GitHub Actions workflows |
| **Context** | Security hardening — supply chain attack prevention |
| **Trigger** | Workflow downloads a binary (wget/curl) and executes it without integrity check |
| **Output** | Modified workflow YAML with `sha256sum --check` step + regression tests |

## When to Use

1. A GitHub Actions workflow downloads a binary via `wget` or `curl` with no hash check
2. A tool is pinned to a version in the URL but the downloaded tarball is not checksummed
3. Security audit identifies unverified binary execution before `tar`/`chmod`/execution
4. Reviewing a follow-up issue requiring supply chain hardening for a specific CI tool

## Verified Workflow

### Step 1: Identify the download step

Read the workflow YAML and find the `wget`/`curl` line downloading the binary. Note the exact
filename and version.

### Step 2: Fetch the official checksum

Fetch from the tool's GitHub Releases page — most projects publish a `_checksums.txt` file:

```bash
curl -L -s https://github.com/<org>/<tool>/releases/download/<version>/<tool>_<version>_checksums.txt
```

Extract the SHA256 for the exact tarball used in the workflow (match OS/arch).

### Step 3: Add the sha256sum check in the workflow

Insert immediately after the `wget` line, before `tar`:

```yaml
- name: Run Gitleaks
  run: |
    # Pinned to v8.18.0 — update hash when upgrading version (see #3316)
    wget -q https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
    # Verify integrity before execution — SHA256 from https://github.com/.../gitleaks_8.18.0_checksums.txt
    echo "6e19050a3ee0688265ed3be4c46a0362487d20456ecd547e8c7328eaed3980cb  gitleaks_8.18.0_linux_x64.tar.gz" | sha256sum --check
    tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
    chmod +x gitleaks
```

Key formatting: `echo "<sha256>  <filename>"` — note **two spaces** between hash and filename
(sha256sum standard format).

### Step 4: Update any comments to document fetch-depth requirements

If the binary is a git-scanning tool (like Gitleaks), ensure `fetch-depth: 0` is documented:

```yaml
with:
  fetch-depth: 0  # Required: full history needed for gitleaks git-log mode (do not remove, see #NNNN)
```

### Step 5: Write regression tests

Create `tests/workflows/test_<workflow>_security.py` asserting:

1. SHA256 check line is present in the workflow file
2. The SHA256 value is a real 64-char hex digest (not a placeholder)
3. The actual hash matches the expected value from the official checksums
4. `fetch-depth: 0` is present (if applicable)
5. The version string is pinned in the download URL

```python
EXPECTED_SHA256 = "6e19050a3ee0688265ed3be4c46a0362487d20456ecd547e8c7328eaed3980cb"
GITLEAKS_TARBALL = "gitleaks_8.18.0_linux_x64.tar.gz"

def test_sha256_value_matches_expected(workflow_content: str) -> None:
    match = re.search(r"([0-9a-f]{64})\s+" + re.escape(GITLEAKS_TARBALL), workflow_content)
    assert match is not None
    assert match.group(1) == EXPECTED_SHA256
```

### Step 6: Run tests, commit, and create PR

```bash
pixi run python -m pytest tests/workflows/ -v
git add .github/workflows/<workflow>.yml tests/workflows/
git commit -m "security(workflow): add SHA256 verification for <tool> binary download"
gh pr create --title "..." --body "Closes #NNNN"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `curl` to checksums URL returned empty | Used `curl -s` without `-L` flag | GitHub releases redirect; without `-L`, curl follows no redirect and returns empty | Always use `curl -L -s` for GitHub Releases URLs, or use `wget -q -O -` |
| Searching for `security-pr-scan.yml` | Issue description mentioned this filename | The actual file is `security.yml` — the issue description used an informal name | Always `ls .github/workflows/` to find actual filenames before assuming |

## Results & Parameters

**Gitleaks v8.18.0 SHA256 (linux_x64)**:
```
6e19050a3ee0688265ed3be4c46a0362487d20456ecd547e8c7328eaed3980cb
```

**Official checksums URL pattern**:
```
https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_checksums.txt
```

**sha256sum check format** (two spaces required):
```bash
echo "<hash>  <filename>" | sha256sum --check
```

**Test pattern** — regex to extract and verify SHA256 from workflow YAML:
```python
import re
match = re.search(r"([0-9a-f]{64})\s+" + re.escape(TARBALL_FILENAME), workflow_content)
```

**CI outcome**: 6/6 tests passed, pre-commit auto-fixed ruff formatting on first commit attempt.
