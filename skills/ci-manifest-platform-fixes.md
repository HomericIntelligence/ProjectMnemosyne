---
name: ci-manifest-platform-fixes
description: "Fix CI/CD failures in manifest-driven platforms. Use when: (1) Python binary path differs between local and CI, (2) git-dependent tests fail in CI, (3) docs routing tests fail for new files."
category: ci-cd
date: 2026-06-15
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ci-cd, python, testing, manifests, slurm]
---

# Fixing CI Failures in Manifest-Driven Platforms

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-15 |
| **Objective** | Fix CI/CD failures in the Inference360 manifest-driven H200 Slurm inference platform |
| **Outcome** | All 580 tests passing, 85.57% coverage, all 12 validation steps pass |
| **Verification** | verified-local |

## When to Use

- A Python CLI tool uses a hardcoded .venv/bin/python path that fails in CI
- Tests depend on git being available but CI environment may not have it
- New documentation files cause docs routing coverage tests to fail
- Debugging which validation step in a multi-step CI script is failing

## Verified Workflow

### Quick Reference

```python
# Fix 1: Use sys.executable instead of hardcoded .venv/bin/python
import sys
parser.add_argument("--python-bin", default=sys.executable)

# Fix 2: Mock git-dependent functions with monkeypatch
def test_dry_run(monkeypatch):
    lock = load_inferencex_lock()
    monkeypatch.setattr(
        "scripts.inferencex.validate_inferencex_pin",
        lambda **kwargs: dict(lock),
    )
    result = main(["dry-run", ...])

# Fix 3: Add docs routing to AGENTS.md
# In AGENTS.md Conditional Documentation Routing section:
# - If a request is assessment related, read docs/assessments/README.md,
#   docs/assessments/2026-05-20.md, and docs/assessments/new-file.md
```

### Detailed Steps

1. **Use sys.executable for Python binary defaults** - Any argparse default for a Python binary path should use `sys.executable` instead of `.venv/bin/python`. This works in CI, on Mac, and in virtual environments.

2. **Mock git-dependent functions in tests** - If a test calls code that imports git-dependent functions (like reading git commit hashes), mock those functions with monkeypatch. The mock should return valid data from the lock/config file.

3. **Route new docs files in AGENTS.md** - When adding new markdown files to the docs/ directory, add a routing entry in the Conditional Documentation Routing section of AGENTS.md. The test_agents_doc_routes_every_docs_markdown_file test checks that every docs/*.md file is referenced.

4. **Debug CI validation step failures** - Run each step from validate.sh individually to identify the exact failure. Print the step name and exit code before moving to the next step.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded .venv/bin/python | Used default=".venv/bin/python" in argparse | CI uses /opt/inference360-venv/bin/python; Mac uses different path | Always use sys.executable for Python binary defaults |
| Skip git mock | Ran tests without mocking validate_inferencex_pin | CI environment may not have git on PATH | Always mock git-dependent functions in tests |
| Ignore docs routing | Added docs/ files without updating AGENTS.md | test_agents_doc_routes_every_docs_markdown_file checks all docs are routed | Add routing entry when adding any docs/*.md file |
| Run full CI script only | Ran validate.sh as a single command | Could not identify which of the 12 steps failed | Run each validation step individually to find the exact failure |

## Results & Parameters

**Environment:** Python 3.12, Slurm H200 clusters, rootless Podman containers

**CI steps:** ruff format, ruff check, mypy, validate-manifest, check-isolation, promotion-ready, validate-software-versions, validate-inferencex-pin, evaluation_harness, compileall, pytest

**Coverage:** 85.57% (up from 80%)

**All 12 validation steps pass locally**

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | PR 116 CI fixes on fix/issue-82-rebase branch | 580 tests passing, all 12 validation steps pass |
