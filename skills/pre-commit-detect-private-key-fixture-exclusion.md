---
name: pre-commit-detect-private-key-fixture-exclusion
description: "Suppress detect-private-key pre-commit hook false positives on test fixtures, TLS unit tests, and Kubernetes secret manifests by adding an exclude regex. Use when: (1) CI fails on detect-private-key for files that contain fake/test credentials, (2) k8s secret manifests or C++ TLS test files trigger PEM header pattern matches."
category: ci-cd
date: 2026-04-23
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pre-commit
  - detect-private-key
  - false-positive
  - tls
  - kubernetes
  - test-fixtures
  - ci
---

# Excluding Test Fixture Files from detect-private-key Pre-Commit Hook

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-23 |
| **Objective** | Stop `detect-private-key` hook from false-firing on test fixtures, TLS unit test files, and Kubernetes secret manifests that contain PEM-style headers but are not real credentials |
| **Outcome** | Success — hook passes; real private key detection remains active for non-excluded paths |
| **Verification** | verified-local |
| **History** | N/A (v1.0.0 initial) |

## When to Use

- CI shows `detect-private-key` hook failing in the `Pre-commit Checks` job
- The flagged files are any of: TLS/mTLS unit tests (`.cpp`, `.py`) containing certificate strings, Kubernetes secret manifests (`k8s/*-security.yaml`, `k8s/*-secret.yaml`), test fixtures or example directories with generated certs
- The files are intentionally in the repo — they contain **fake/test credentials**, not real ones
- You cannot remove the files (they are needed for tests or k8s manifests)
- You must NOT simply delete the `detect-private-key` hook (that would miss real leaks elsewhere)

## Verified Workflow

### Quick Reference

```yaml
# .pre-commit-config.yaml
# Under the detect-private-key hook entry, add an exclude: field:

- id: detect-private-key
  exclude: '^(k8s/metrics-security\.yaml|tests/unit/test_grpc_tls\.cpp)$'
```

For broader exclusions (test directories, example certs, k8s secret patterns):

```yaml
- id: detect-private-key
  exclude: '^(tests/|fixtures/|examples/|k8s/.*-secret.*\.yaml|k8s/.*-security.*\.yaml)$'
```

### Detailed Steps

1. **Identify the flagged files** — Read the CI log output from the `detect-private-key` hook. It lists each file path that triggered the pattern.

2. **Confirm they are test fixtures** — Check whether the file is a unit test, example cert, generated credential, or Kubernetes manifest. If the file contains real credentials that should not be in the repo, fix that instead.

3. **Locate the hook entry** in `.pre-commit-config.yaml`. Look for the `repo: https://github.com/pre-commit/pre-commit-hooks` block and find `- id: detect-private-key`.

4. **Add the `exclude:` field** directly under `- id: detect-private-key`. The value is a Python regex anchored with `^...$`.
   - For exact file paths: `'^(path/to/file\.ext)$'`
   - For multiple files: `'^(path/a\.yaml|path/b\.cpp)$'`
   - For entire directories: `'^tests/'` (no anchor needed for prefix match)

5. **Escape regex metacharacters** in paths — forward slashes `/` do not need escaping, but dots `.` in filenames should be escaped as `\.`.

6. **Verify locally**:
   ```bash
   pre-commit run detect-private-key --all-files
   ```
   The hook should now pass for excluded files while still checking all other paths.

7. **Commit and push** — the exclusion is in `.pre-commit-config.yaml` which is checked into version control, so CI will pick it up automatically.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Delete the hook entirely | Remove `detect-private-key` from `.pre-commit-config.yaml` | Would miss real credential leaks in non-test paths — eliminates security value of the hook | Use `exclude:` to scope the hook, never remove it entirely |
| Move test files to a different path | Rename `tests/unit/test_grpc_tls.cpp` to avoid detection | Disrupts test structure and doesn't scale for k8s manifests that must live in `k8s/` | Path-based `exclude:` is the correct mechanism; don't relocate files to satisfy a hook |
| Add `# noqa` or inline ignore comments | Tried embedding per-line directives in the C++ source | `detect-private-key` is a grep-based hook, not a Python linter — inline suppressions are not supported | Hook-level `exclude:` is the only supported suppression mechanism for `pre-commit-hooks` |

## Results & Parameters

### Minimal exclusion (exact files)

```yaml
- id: detect-private-key
  exclude: '^(k8s/metrics-security\.yaml|tests/unit/test_grpc_tls\.cpp)$'
```

### Broad exclusion (directories + patterns)

```yaml
- id: detect-private-key
  exclude: '^(tests/|fixtures/|examples/|k8s/.*-secret.*\.yaml|k8s/.*-security.*\.yaml)$'
```

### Regex rules for the `exclude:` field

| Pattern | Matches |
| --------- | --------- |
| `^path/to/file\.ext$` | Exact file |
| `^(file1\.yaml\|file2\.cpp)$` | Either of two exact files |
| `^tests/` | All files under `tests/` |
| `^k8s/.*-secret.*\.yaml$` | Any k8s YAML with `-secret` in the name |
| `^k8s/.*-security.*\.yaml$` | Any k8s YAML with `-security` in the name |

### Typical PEM patterns that trigger false positives in test files

```
-----BEGIN CERTIFICATE-----
-----BEGIN PRIVATE KEY-----
-----BEGIN RSA PRIVATE KEY-----
-----BEGIN EC PRIVATE KEY-----
-----BEGIN CERTIFICATE REQUEST-----
```

These patterns appear in TLS unit tests (`test_grpc_tls.cpp`, `test_tls_*.py`) and in Kubernetes secret manifests that embed cert/key material as base64 or raw PEM for local dev environments.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectKeystone | Branch `fix/main-pre-commit-mypy`, PR #384 | Fix committed and pushed; CI was running at capture time |
