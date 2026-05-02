---
name: ci-cd-codeql-missing-workflow-permissions-fix
description: "Fix CodeQL security alert actions/missing-workflow-permissions by adding an explicit permissions block to GitHub Actions workflows. Use when: (1) a CodeQL code scanning alert flags a workflow for lacking a permissions block, (2) a validate/lint/check workflow only reads code and needs least-privilege access, (3) auditing sibling workflows to determine the correct permission level to assign."
category: ci-cd
date: 2026-03-27
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-actions
  - codeql
  - security
  - permissions
  - least-privilege
---

# CI/CD: Fix CodeQL Missing Workflow Permissions Alert

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-27 |
| **Objective** | Resolve GitHub CodeQL alert #2 (`actions/missing-workflow-permissions`) on `validate-plugins.yml` |
| **Outcome** | Successful — 2-line addition resolved the alert |
| **Verification** | verified-local (YAML syntax validated; CI will confirm after PR merge) |

## When to Use

- A GitHub CodeQL code scanning alert fires `actions/missing-workflow-permissions` on a workflow file
- A workflow lacks an explicit `permissions:` block (leaving the default `GITHUB_TOKEN` with broad write access)
- A workflow only checks out code and runs read-only scripts — it qualifies for `permissions: contents: read`
- You need to determine the minimal permission set for a workflow by cross-checking its sibling workflows

## Verified Workflow

### Quick Reference

```yaml
# Add this block between the `on:` section and `jobs:` section:
permissions:
  contents: read
```

For workflows that push to a registry or write PR comments, check sibling workflows for the required set:

```yaml
# Example: workflow that writes PR comments needs more:
permissions:
  contents: write
  pull-requests: write
```

### Detailed Steps

1. **Fetch the alert details** to get the exact file and line numbers:
   ```bash
   gh api repos/<OWNER>/<REPO>/code-scanning/alerts/<ALERT_NUMBER>
   ```
   Look for `location.path` and `location.start_line` in the response.

2. **Read the flagged workflow** to understand what it does:
   - Does it only check out code and run scripts? → `permissions: contents: read`
   - Does it push artifacts, create releases, or write to packages? → add those scopes too

3. **Cross-check sibling workflows** for reference:
   ```bash
   grep -A5 "permissions:" .github/workflows/*.yml
   ```
   Sibling workflows with similar jobs reveal the expected permission pattern.

4. **Add the permissions block** between `on:` and `jobs:`:
   ```yaml
   on:
     push:
       branches: [main]
     pull_request:
       branches: [main]

   permissions:        # <-- Add here
     contents: read

   jobs:
     validate:
       ...
   ```

5. **Validate the YAML syntax** locally before committing:
   ```bash
   python3 -c "import yaml; yaml.safe_load(open('.github/workflows/<filename>.yml'))" && echo "YAML OK"
   ```

6. **Submit via PR**: Create a branch, commit, push, and open a PR against main.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| N/A | Direct approach worked on first try | N/A | The fix is always a 2-line YAML block; no complex debugging needed |

## Results & Parameters

**Before fix** (flagged by CodeQL `actions/missing-workflow-permissions`):
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    ...
```

**After fix**:
```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    ...
```

**Permission level guide**:

| Workflow Type | Recommended Permissions |
| --------------- | ------------------------ |
| Validate / lint / check (read-only) | `contents: read` |
| Test matrix (read-only) | `contents: read` |
| Release / publish to package registry | `contents: write`, `packages: write` |
| Auto-merge / update PR | `contents: write`, `pull-requests: write` |
| Security scan with SARIF upload | `contents: read`, `security-events: write` |

**Locating the CodeQL alert**:
```bash
# List all code scanning alerts for a repo
gh api repos/<OWNER>/<REPO>/code-scanning/alerts

# Fetch a specific alert (includes file path and line numbers)
gh api repos/<OWNER>/<REPO>/code-scanning/alerts/<N>
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | CodeQL alert #2 on `validate-plugins.yml` | Added `permissions: contents: read` between `on:` and `jobs:` blocks |
