---
name: fix-docker-image-case
description: Fix Docker SBOM and workflow failures caused by mixed-case image names in GitHub Actions
---

# Fix Docker Image Case Sensitivity in CI/CD

## Overview

| Property | Value |
|----------|-------|
| **Date** | 2025-12-29 |
| **Objective** | Fix Docker SBOM generation failures caused by mixed-case image names |
| **Outcome** | Successfully fixed by hardcoding lowercase image name |
| **Context** | GitHub Actions workflow using `anchore/sbom-action` |

## When to Use

Invoke this skill when:

1. **SBOM generation fails** with errors like:
   - `could not parse reference: ghcr.io/Owner/RepoName:tag`
   - `unable to parse registry reference`
   - Docker image reference parsing errors in CI

2. **GitHub Actions Docker workflows fail** with case-related errors

3. **Using `github.repository` variable** in Docker image references

4. **After repository renames** that change capitalization

## Problem Overview

### Root Cause

Docker image names **must be lowercase**, but GitHub's `github.repository` variable preserves the original repository name case (e.g., `mvillmow/ProjectOdyssey`). This causes failures in tools that manually construct Docker image references (like `anchore/sbom-action`).

### Why `docker/metadata-action` Works

The `docker/metadata-action` automatically lowercases image names in its outputs, so build/push steps work fine. However, when **manually constructing image references** using `${{ env.IMAGE_NAME }}`, the original case is preserved, causing failures.

## Verified Workflow

### Step 1: Identify the Failure

Check CI logs for image parsing errors:

```bash
gh run list --branch main --limit 5
gh run view <run-id> --log-failed
```

Look for errors like:
```
could not parse reference: ghcr.io/mvillmow/ProjectOdyssey:main
```

### Step 2: Locate Mixed-Case References

Search the workflow file for uses of `github.repository`:

```bash
grep -n "github.repository" .github/workflows/docker.yml
```

### Step 3: Fix Environment Variable

Replace dynamic repository reference with hardcoded lowercase:

```yaml
# BEFORE (preserves case)
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

# AFTER (hardcoded lowercase)
env:
  REGISTRY: ghcr.io
  # Docker image names must be lowercase - github.repository preserves case
  IMAGE_NAME: owner/reponame
```

### Step 4: Verify All Image References

Check all places where `env.IMAGE_NAME` is used:
- SBOM generation steps
- Image scanning steps
- Manual docker pull/push commands
- Summary generation

### Step 5: Test the Fix

```bash
git checkout -b fix-docker-image-case
git add .github/workflows/docker.yml
git commit -m "fix(ci): use lowercase image name for Docker operations"
git push -u origin fix-docker-image-case
gh pr create --title "fix(ci): use lowercase image name" --body "Fixes Docker SBOM generation"
```

## Failed Attempts

| Attempt | What I Tried | Why It Failed |
|---------|--------------|---------------|
| Use `github.repository_owner` | `${{ github.repository_owner }}/repo` | `github.repository_owner` also preserves case |
| Rely on `docker/metadata-action` | Expected it to lowercase everywhere | Only lowercases its own outputs, not env variables |

## Results & Parameters

### Successful Fix

**File:** `.github/workflows/docker.yml`

**Change:**
```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: mvillmow/projectodyssey  # Hardcoded lowercase
```

### Error Before Fix

```
[0000] ERROR could not determine source: errors occurred attempting to resolve 'ghcr.io/mvillmow/ProjectOdyssey:main':
  - docker: could not parse reference: ghcr.io/mvillmow/ProjectOdyssey:main
  - oci-registry: unable to parse registry reference="ghcr.io/mvillmow/ProjectOdyssey:main"
```

### Success After Fix

- SBOM generation completes successfully
- Image scanning works
- All Docker operations use consistent lowercase names

## Prevention

### For New Workflows

1. **Always hardcode lowercase** image names in `env.IMAGE_NAME`
2. **Never use** `github.repository` directly in Docker contexts
3. **Test SBOM generation** in PR workflow (not just main)

### For Existing Workflows

1. **Audit all Docker workflows** for `github.repository` usage
2. **Search for image references**: `grep -r "IMAGE_NAME" .github/workflows/`
3. **Add validation**: Test lowercase conversion in workflow
