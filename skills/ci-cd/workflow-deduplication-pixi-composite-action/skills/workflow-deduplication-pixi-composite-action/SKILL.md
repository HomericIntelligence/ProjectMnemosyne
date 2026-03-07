---
name: workflow-deduplication-pixi-composite-action
description: "Deduplicate repeated Pixi setup blocks across GitHub Actions workflows using a composite action. Use when: consolidating CI workflows, replacing inline prefix-dev/setup-pixi with a shared composite action, or merging security/audit workflows."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| Issue | Replace repeated `prefix-dev/setup-pixi@v0.9.4` blocks in 9+ workflows |
| Solution | Composite action at `.github/actions/setup-pixi/action.yml` |
| Result | Eliminated all inline Pixi setup; merged 2 workflows into 1 |
| Pre-commit | All hooks passed after changes |

## When to Use

- Multiple GitHub Actions workflows contain identical `prefix-dev/setup-pixi@v0.9.4` blocks
- CI workflow count is high (>20) and maintenance burden is growing
- Separate security scan + dependency audit workflows can be merged with event guards
- A `setup-pixi` composite action already exists but not all workflows use it

## Verified Workflow

### 1. Audit existing workflows for inline Pixi setup

```bash
grep -rl "prefix-dev/setup-pixi" .github/workflows/
```

### 2. Check if composite action already exists

```bash
ls .github/actions/setup-pixi/action.yml
```

### 3. Replace inline blocks with composite action (bulk Python script)

The replacement pattern is exact — match all 5 lines together:

```python
OLD = "      - name: Set up Pixi\n        uses: prefix-dev/setup-pixi@v0.9.4\n        with:\n          pixi-version: latest\n          cache: true"
NEW = "      - name: Set up Pixi\n        uses: ./.github/actions/setup-pixi"

for f in workflow_files:
    content = open(f).read()
    count = content.count(OLD)
    if count > 0:
        content = content.replace(OLD, new)
        open(f, 'w').write(content)
```

### 4. Merge scheduled audit workflow into security workflow

Add `if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'` guards to
audit jobs and append them to `security.yml`. Update triggers:

```yaml
on:
  pull_request:
  push:
    branches: [main]
    paths:
      - 'pixi.toml'
      - 'requirements.txt'
  schedule:
    - cron: '0 8 * * 1'
  workflow_dispatch:

permissions:
  issues: write  # add for audit issue creation
```

Then delete the standalone `dependency-audit.yml`.

### 5. Verify no inline setups remain

```bash
grep -rl "prefix-dev/setup-pixi" .github/workflows/
# Must return empty
```

### 6. Run pre-commit to validate YAML

```bash
pixi run pre-commit run --all-files
# Check YAML hook will catch malformed workflow files
```

### 7. Stage and commit only the workflow files

```bash
git add .github/workflows/ .github/actions/
git commit -m "ci(workflows): replace inline pixi setup with composite action"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Parallel Edit tool calls | Used Edit tool on 6 files simultaneously | 3 files failed with "File has not been read yet" error despite being read earlier in session | Edit tool requires each file to be read in the current tool-use response, not earlier in the conversation |
| `rm` with multiple args in single Bash call | Ran `rm file1 && echo msg && rm file2 && ls` | Shell parsed the echo arguments as filenames and deleted all .yml files in the directory | Never mix `rm` with unquoted multiline strings in Bash tool — use separate commands |
| `git restore .github/workflows/` after accidental deletion | Tried to recover deleted files | `git restore` restored original (unmodified) files from HEAD, wiping all in-session edits | `git restore` is destructive to uncommitted changes; use a Python script to re-apply all edits at once |
| Multiple parallel Edit calls without prior reads | Attempted batch edits on files read in previous turn | Fails with "File has not been read yet" — Edit tool tracks reads per-response | Read files and edit them in the same response, or use Bash/Python scripts for bulk edits |

## Results & Parameters

### Composite action structure

`.github/actions/setup-pixi/action.yml`:

```yaml
name: Set Up Pixi Environment
description: Install Pixi and restore the cached environment.

inputs:
  pixi-version:
    description: Pixi version to install
    required: false
    default: latest
  cache:
    description: Whether to enable Pixi built-in caching
    required: false
    default: 'true'

runs:
  using: composite
  steps:
    - name: Set up Pixi
      uses: prefix-dev/setup-pixi@v0.9.4
      with:
        pixi-version: ${{ inputs.pixi-version }}
        cache: ${{ inputs.cache }}
```

### Workflow reference

```yaml
- name: Set up Pixi
  uses: ./.github/actions/setup-pixi
```

### Outcome

- 9 workflows updated from inline to composite action
- 1 workflow deleted (`dependency-audit.yml`) merged into `security.yml`
- Workflow count: 23 -> 22 yml files
- All pre-commit hooks passed
