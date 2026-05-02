---
name: ci-benchmark-host-container-path-mismatch
description: "Fix GitHub Actions benchmark workflow failures where mkdir runs on host but
  benchmark output is written inside a container. Use when: (1) benchmark CI step fails
  to write output files, (2) workflow uses 'podman compose exec' or 'docker exec' for the
  benchmark run but creates output dirs on the host, (3) directory exists on host but is
  not accessible inside the container due to volume/UID mismatch."
category: ci-cd
date: 2026-03-27
version: "1.0.0"
user-invocable: false
tags:
  - ci
  - benchmark
  - podman
  - docker
  - container
  - volume-mount
  - filesystem-mismatch
---

# CI Benchmark Host/Container Path Mismatch

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-03-27 |
| **Objective** | Fix benchmark workflow where output directory created on host is not accessible inside container |
| **Outcome** | Successful — create output directory inside the container exec command |

## When to Use

- Benchmark CI step fails with permission denied or file-not-found writing output
- Workflow creates output directory with `mkdir -p benchmark-results` on the host runner
- The actual benchmark runs via `podman compose exec -T dev bash -c "..."` or `docker exec`
- The container mounts the workspace via a volume with different UID mapping
- Output directory convention mismatch: host has `benchmark-results/` but container expects
  `builds/benchmarks/`

## Root Cause

`mkdir -p benchmark-results` on the **GitHub Actions host runner** creates a directory owned
by the runner UID. The `podman compose exec` command runs inside the **container** where
`/workspace` is a volume-mounted directory. The container process (running as a different UID
due to rootless Podman's UID remapping) cannot write to a directory created by the host.

Additionally, the output path convention may differ between host and container.

## Verified Workflow

### Quick Reference

```yaml
# BROKEN: mkdir on host, benchmark runs inside container
- name: Run benchmarks
  run: |
    mkdir -p benchmark-results
    podman compose exec -T dev bash -c "pixi run python run.py --output benchmark-results/out.json"

# FIXED: create output dir inside container exec, also create on host for fallback
- name: Run benchmarks
  run: |
    mkdir -p builds/benchmarks
    podman compose exec -T dev bash -c "mkdir -p builds/benchmarks && pixi run python run.py --output builds/benchmarks/out.json"
```

### Detailed Steps

1. **Identify the failure** — look for permission denied or missing file errors in the
   benchmark step output.

2. **Determine where the command runs** — any step using `podman compose exec`, `docker exec`,
   or `podman run` runs inside the container; `mkdir` or `run:` steps without these run on
   the host.

3. **Check volume mount UID mapping** — rootless Podman maps container UIDs to a sub-UID
   range; files created by the host runner UID are not writable by the container UID.

4. **Fix**: move `mkdir` inside the `exec` call:

   ```yaml
   podman compose exec -T dev bash -c "mkdir -p builds/benchmarks && pixi run python run.py --output builds/benchmarks/out.json"
   ```

5. **Also create on host** (for artifact upload steps that run on host):

   ```yaml
   mkdir -p builds/benchmarks
   podman compose exec -T dev bash -c "mkdir -p builds/benchmarks && ..."
   ```

6. **Verify output path convention** — ProjectOdyssey uses `builds/benchmarks/` (not
   `benchmark-results/`, not `build/`).

### ProjectOdyssey Output Directory Convention

| Purpose | Directory | Notes |
| --------- | ----------- | ------- |
| Benchmark results | `builds/benchmarks/` | JSON output files |
| Build artifacts | `builds/` | Compiled binaries |
| Test results | `test-results/` | JUnit XML, coverage |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `mkdir -p benchmark-results` on host | Created output dir before exec call | Host dir not accessible by container process due to UID remapping | Create the dir inside the container exec, not on the host |
| Using `benchmark-results/` path | Used non-standard output dir name | Project convention is `builds/benchmarks/` | Check project output dir conventions before hardcoding paths |

## Results & Parameters

### UID Remapping in Rootless Podman

```bash
# Host runner UID (typically 1001 in GitHub Actions)
id  # uid=1001(runner) gid=1001(runner)

# Container UID (mapped to subuid range)
podman compose exec dev id  # uid=1000(dev) -- different from host

# Directory created on host by UID 1001 is owned by different UID than container's 1000
# -> permission denied when container tries to write
```

### Workflow Pattern (Copy-Paste)

```yaml
- name: Run benchmarks
  run: |
    mkdir -p builds/benchmarks
    podman compose exec -T dev bash -c \
      "mkdir -p builds/benchmarks && \
       pixi run python scripts/run_benchmark.py \
         --output builds/benchmarks/results.json"

- name: Upload benchmark results
  uses: actions/upload-artifact@v4
  with:
    name: benchmark-results
    path: builds/benchmarks/
    if-no-files-found: warn
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | CI benchmark workflow | PR #5177 (unverified) |
