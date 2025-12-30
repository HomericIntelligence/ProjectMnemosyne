---
name: fix-docker-platform
description: Fix Docker build failures caused by platform mismatches between workflow config and pixi.toml
category: ci-cd
created: 2025-12-28
tags: [docker, ghcr, arm64, pixi, platform, ci]
---

# Fix Docker Platform Mismatch

| Field | Value |
|-------|-------|
| Date | 2025-12-28 |
| Objective | Fix Docker build failures caused by ARM64 platform not supported by pixi.toml |
| Outcome | Successfully removed ARM64 builds, all Docker CI jobs now pass |

## When to Use

Use this skill when:

- Docker builds fail with "unsupported platform" errors
- `pixi install --frozen` fails in Docker with platform mismatch
- Error message contains: "The workspace does not support 'linux-aarch64'"
- Multi-arch builds (`linux/amd64,linux/arm64`) fail but single-arch works
- Building Docker images that use pixi for dependency management

## Verified Workflow

### 1. Identify Platform Support in pixi.toml

```bash
grep -A5 "platforms" pixi.toml
```

Expected output for x86-only support:

```toml
platforms = ["linux-64"]
```

If only `linux-64` is listed, ARM64 (`linux-aarch64`) builds will fail.

### 2. Find ARM64 References in Workflows

```bash
grep -rn "arm64\|aarch64\|linux/arm" .github/workflows/
```

Common locations:

- `.github/workflows/docker.yml`
- `.github/workflows/release.yml`

### 3. Remove Unsupported Platforms

Edit the `platforms` field in `docker/build-push-action`:

```yaml
# Before (fails if pixi doesn't support ARM64)
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64,linux/arm64

# After (works with linux-64 only pixi.toml)
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    platforms: linux/amd64
```

### 4. Verify and Create PR

```bash
# Commit changes
git add .github/workflows/docker.yml .github/workflows/release.yml
git commit -m "fix(ci): remove ARM64 Docker builds"
git push -u origin <branch>

# Create PR with auto-merge
gh pr create --title "fix(ci): remove ARM64 Docker builds" \
  --body "Remove linux/arm64 platform - pixi.toml only supports linux-64"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Happened | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| Build ARM64 without pixi support | Docker workflow tried `linux/arm64` | Dockerfile runs `pixi install --frozen` which validates platform | Check pixi.toml platforms before enabling multi-arch builds |
| Ignore Docker failures | Left ARM64 in workflow, Docker failed on every PR | `build-and-push` wasn't a required check but blocked auto-merge | Non-required failing checks still cause friction |
| Fix via pixi platform add | Considered adding ARM64 to pixi.toml | Would require regenerating lock file and testing | Removal is simpler when ARM64 not actually needed |

## Results & Parameters

### Files Modified

| File | Line | Change |
|------|------|--------|
| `.github/workflows/docker.yml` | 86 | `linux/amd64,linux/arm64` → `linux/amd64` |
| `.github/workflows/release.yml` | 454 | `linux/amd64,linux/arm64` → `linux/amd64` |

### Error Message Pattern

```text
× The workspace does not support 'linux-aarch64'.
│ Add it with 'pixi workspace platform add linux-aarch64'.
help: supported platforms are linux-64
```

### Commands Reference

```bash
# Find platform config
grep -rn "platforms:" .github/workflows/

# Check pixi support
grep "platforms" pixi.toml

# Re-run failed CI jobs
gh run rerun <run-id> --failed

# Check CI status
gh pr checks <pr-number>
```

## Related

- PR #2978 in ProjectOdyssey - Implementation of this fix
- Issue #995 - Feature request to add ARM64 support properly
