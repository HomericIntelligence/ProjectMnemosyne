# Docker Image Case Sensitivity Fix - Raw Notes

## Session Details

**Date:** 2025-12-29
**Actual Issue:** Docker SBOM generation failing on main branch

## Discovery Process

1. Checked CI runs on main branch: `gh run list --branch main --limit 5`
2. Found failing run: 20563226174 (Docker Build and Publish)
3. Retrieved failed logs: `gh run view 20563226174 --log-failed`

## Key Error

```
[0000] ERROR could not determine source: errors occurred attempting to resolve 'ghcr.io/mvillmow/ProjectOdyssey:main':
  - snap: snap file "ghcr.io/mvillmow/ProjectOdyssey:main" does not exist
  - docker: could not parse reference: ghcr.io/mvillmow/ProjectOdyssey:main
  - podman: podman not available: no host address
  - containerd: containerd not available: failed to dial "/run/containerd/containerd.sock"
  - oci-registry: unable to parse registry reference="ghcr.io/mvillmow/ProjectOdyssey:main"
```

## Root Cause Analysis

Docker image names MUST be lowercase, but the workflow was using:
```yaml
env:
  IMAGE_NAME: ${{ github.repository }}
```

Which evaluates to: `mvillmow/ProjectOdyssey` (mixed case)

## Why Other Steps Worked

The `docker/build-push-action` and `docker/metadata-action` automatically lowercase image names in their outputs. But the `anchore/sbom-action` step manually constructs the image reference:

```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    image: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.ref_name }}
```

This creates: `ghcr.io/mvillmow/ProjectOdyssey:main` (wrong!)

## Solution

Hardcode lowercase in env:
```yaml
env:
  REGISTRY: ghcr.io
  # Docker image names must be lowercase - github.repository preserves case
  IMAGE_NAME: mvillmow/projectodyssey
```

## Lessons Learned

1. **Docker is strict about lowercase** - no exceptions
2. **GitHub variables preserve case** - `github.repository`, `github.repository_owner`, etc.
3. **Actions handle lowercasing differently** - some do it automatically, others don't
4. **Manual image references are risky** - prefer using action outputs when possible

## Source

- PR #3001 on mvillmow/ProjectOdyssey (created on wrong repo)
- Original fix PR: #2982
