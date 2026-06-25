---
name: python-sca-pip-audit-update-transitive-lock
description: "Resolve GitHub Actions Python SCA pip-audit failures caused by vulnerable transitive dev dependencies in a uv.lock file. Use when: (1) python-sca or pip-audit fails with only a summary in the job log, (2) the failing package is transitive through a dev tool, (3) uv --locked reproduction needs cache paths redirected in a restricted sandbox."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - github-actions
  - python-sca
  - pip-audit
  - uv
  - uv-lock
  - lockfile
  - dependency-scanning
  - transitive-dependency
  - cachecontrol
  - msgpack
---

# Python SCA Pip-Audit Transitive Lockfile Remediation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Resolve GitHub Actions Python SCA failures from a vulnerable transitive dev dependency in a locked uv environment without weakening or bypassing pip-audit. |
| **Outcome** | Downloaded the pip-audit artifact, identified the exact advisory and fixed version, traced the vulnerable package through dev dependency metadata, refreshed only the affected package in `uv.lock`, reran the CI-equivalent audit with redirected caches, and confirmed GitHub checks passed. |
| **Verification** | verified-ci |

## When to Use

- A GitHub Actions `python-sca` or pip-audit job fails with a terse log such as `Found 1 known vulnerability in 1 package`.
- The workflow uploads a `pip-audit-report` artifact and the job log does not print the full JSON details.
- The vulnerable package is not declared directly in `pyproject.toml`, but comes from a dev tool such as `pip-audit`.
- A uv-managed project uses `uv run --locked --extra dev ...` in CI and needs a minimal lockfile remediation.
- Local reproduction fails in a restricted sandbox because pip-audit or uv tries to write caches under a read-only home directory.

## Verified Workflow

### Quick Reference

```bash
# 1. Pull the failing job log.
gh run view <run-id> --job <job-id> --log

# 2. Download the pip-audit artifact; the log may contain only the summary.
gh run download <run-id> -n pip-audit-report -D /tmp/<audit-dir>
python3 -m json.tool /tmp/<audit-dir>/pip-audit.json

# 3. Reproduce with the exact CI command, redirecting caches if home is restricted.
env UV_CACHE_DIR=/tmp/<case>-uv-cache XDG_CACHE_HOME=/tmp/<case>-xdg-cache \
  uv run --locked --extra dev python -m pip_audit \
  --local --format=json --output=/tmp/<case>-pip-audit-before.json

# 4. Trace whether the vulnerable package is transitive.
env UV_CACHE_DIR=/tmp/<case>-uv-cache XDG_CACHE_HOME=/tmp/<case>-xdg-cache \
  uv run --locked --extra dev python -m pip show <vulnerable-package> <parent-package> pip-audit

# 5. Refresh only the vulnerable package in uv.lock.
env UV_CACHE_DIR=/tmp/<case>-uv-cache XDG_CACHE_HOME=/tmp/<case>-xdg-cache \
  uv lock --upgrade-package <vulnerable-package>

# 6. Re-run the CI-equivalent audit and confirm it is clean.
env UV_CACHE_DIR=/tmp/<case>-uv-cache XDG_CACHE_HOME=/tmp/<case>-xdg-cache \
  uv run --locked --extra dev python -m pip_audit \
  --local --format=json --output=/tmp/<case>-pip-audit-fixed.json

git diff -- uv.lock
```

### Detailed Steps

1. **Inspect the failing SCA job log first.** Use `gh run view <run-id> --job <job-id> --log`. If the workflow is still running, wait until the log and artifacts are available before editing. The log may only show the pip-audit summary, not the vulnerable package details.

2. **Download and inspect the uploaded audit artifact.** Use `gh run download <run-id> -n pip-audit-report -D /tmp/<audit-dir>` and read `pip-audit.json`. The artifact is the source of truth for package name, installed version, advisory ID, and fixed version.

3. **Reproduce locally with the exact CI command.** Match the workflow invocation instead of improvising flags. For uv projects, that may be `uv run --locked --extra dev python -m pip_audit --local --format=json --output=...`. In restricted environments, redirect both `UV_CACHE_DIR` and `XDG_CACHE_HOME` to `/tmp` so pip-audit does not fail writing to a read-only home cache.

4. **Trace the transitive source before changing dependencies.** If the package is not direct, inspect installed metadata with `pip show`. The important fields are `Required-by` on the vulnerable package and on its parent package. This distinguishes a project runtime dependency from a dev-tool dependency.

5. **Prefer a targeted lock refresh when a fixed release exists.** Use `uv lock --upgrade-package <vulnerable-package>` rather than broad resolver churn. Review `git diff -- uv.lock` and confirm only the intended package/version changed.

6. **Re-run the CI-equivalent pip-audit command.** The expected terminal result is `No known vulnerabilities found`. Inspect the output JSON as well; the fixed package should show the remediated version and no vulnerabilities.

7. **Run affected tests or static checks, commit only the lockfile if that is the only change, push, and confirm GitHub SCA passes.** Do not merge based on local output alone if the required CI job is the gate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Weaken or bypass SCA | Considered treating the pip-audit failure as noise | The vulnerable package had a fixed release, so suppression would hide a real remediable advisory | Keep the SCA job fail-closed when a fixed version exists; update the lockfile instead |
| Rely on job log summary only | Read the log line `Found 1 known vulnerability in 1 package` | The log did not print the package, advisory, or fixed version details | Download the `pip-audit-report` artifact and inspect `pip-audit.json` |
| Assume the package is direct | Looked for the vulnerable package in project dependency declarations | The package was transitive through a dev tool and not declared by the project | Use `pip show` metadata to trace `Required-by` before changing manifests |
| Run pip-audit with default cache paths | Ran the CI-equivalent command in a restricted sandbox | pip-audit attempted to write under a read-only home cache and raised `OSError: [Errno 30] Read-only file system` | Redirect both `UV_CACHE_DIR` and `XDG_CACHE_HOME` to writable `/tmp` paths |
| Broad dependency refresh | Could have run a full uv lock update | Full resolver churn increases review risk and can change unrelated packages | Use `uv lock --upgrade-package <package>` for a minimal lockfile change |

## Results & Parameters

In the verified case, GitHub Actions `python-sca` ran:

```bash
uv run --locked --extra dev python -m pip_audit \
  --local --format=json --output=pip-audit.json
```

The artifact identified:

| Field | Value |
|-------|-------|
| Package | `msgpack` |
| Vulnerable version | `1.1.2` |
| Advisory | `GHSA-6v7p-g79w-8964` |
| Fixed version | `>=1.2.1` |
| Transitive source | `msgpack` required by `CacheControl`; `CacheControl` required by `pip-audit` |
| Minimal fix | `uv lock --upgrade-package msgpack` |
| Lockfile result | `msgpack` updated from `1.1.2` to `1.2.1` in `uv.lock` |

Restricted-sandbox reproduction and fix commands:

```bash
env UV_CACHE_DIR=/tmp/pr254-uv-cache XDG_CACHE_HOME=/tmp/pr254-xdg-cache \
  uv run --locked --extra dev python -m pip_audit \
  --local --format=json --output=/tmp/pr254-pip-audit-fixed.json

env UV_CACHE_DIR=/tmp/pr254-uv-cache XDG_CACHE_HOME=/tmp/pr254-xdg-cache \
  uv lock --upgrade-package msgpack
```

Expected post-fix audit result:

```text
No known vulnerabilities found
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Inference360 | PR #254, head `4086627`, 2026-06-19 | `python-sca`, `validate`, `sast`, `secrets`, and CodeQL passed after the targeted `uv.lock` update |
