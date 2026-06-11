---
name: ci-coverage-path-remapping
description: "Remap container paths to host paths for coverage reports in CI. Use when: (1) coverage XML export fails with 'No source for code' after running inside a container, (2) .coverage file has /workspace/ paths that don't exist on the host."
category: ci-cd
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [coverage, ci, container, pyproject, pytest]
---

# CI Coverage Path Remapping

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Fix coverage XML export in CI when tests run inside a container with different paths |
| **Outcome** | Successful — coverage combine remaps container paths to host paths |
| **Verification** | verified-ci |

## When to Use

- CI runs tests inside a container (repo mounted at `/workspace/`) but coverage XML export runs on the host
- `coverage xml` fails with `No source for code: '/workspace/...'`
- The `.coverage` file contains absolute container paths that don't exist on the host

## Verified Workflow

### Quick Reference

```toml
# pyproject.toml
[tool.coverage.run]
source = ["scripts", "inference360"]

[tool.coverage.paths]
source = [
    "",              # canonical: host paths (relative)
    "/workspace/",   # alternate: container paths → remapped to ""
]
```

```yaml
# .github/workflows/validate.yml
- name: Export coverage XML
  if: always()
  run: |
    if [ -f .coverage ]; then
      cp .coverage .coverage.0
      .venv/bin/python -m coverage combine
      .venv/bin/python -m coverage xml -o coverage.xml
    fi
```

### Detailed Steps

1. **Add `[tool.coverage.paths]`** to `pyproject.toml`. The first entry is the canonical (target) path. Subsequent entries are alternates that get rewritten to the canonical. Use `""` (empty string = relative/cwd) as canonical and `"/workspace/"` as alternate.
2. **Rename `.coverage` to `.coverage.0`** before running `coverage combine`. The `combine` command looks for `.coverage.*` suffixed files, not a bare `.coverage`.
3. **Use `cp` not `mv`** to preserve the raw `.coverage` data for debugging if `combine` or `xml` fails.
4. **Run `coverage combine`** to apply path remapping from pyproject.toml, then `coverage xml`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `coverage xml` directly on container .coverage | `coverage xml -o coverage.xml` | Container paths `/workspace/...` don't exist on host | Must remap paths via `coverage combine` first |
| Swapped canonical/alternate order | `source = ["/workspace/", ""]` | First entry is canonical (target), not alternate — this remaps host paths TO /workspace/ | Read the docs: first value is canonical, others are alternates |
| `mv .coverage .coverage.0` | Moved file before combine | If combine/xml fails, raw data is lost for debugging | Use `cp` instead of `mv` |
| Single `.coverage` with combine | `coverage combine` without rename | `combine` expects `.coverage.*` files, ignores bare `.coverage` | Must rename to `.coverage.0` first |

## Results & Parameters

- **coverage.py version**: 7.x (reads pyproject.toml automatically)
- **Container mount point**: `/workspace`
- **Host working directory**: `$GITHUB_WORKSPACE` (repo root)
- **Path remapping**: `/workspace/inference360/__init__.py` → `inference360/__init__.py`

## Verified On

| Project | Context | Details |
|---------|---------|-------|
| LLM360/Inference360 | PR #82 — Move inference360 module to package path | CI validate job coverage XML export succeeds |
