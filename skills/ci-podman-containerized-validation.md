---
name: ci-podman-containerized-validation
description: "Install rootless Podman in GitHub Actions CI to run containerized validation. Use when: (1) CI needs to build/run dev containers, (2) set -u causes unbound variable errors with empty bash arrays, (3) shasum is missing on Ubuntu CI runners."
category: ci-cd
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [podman, ci, github-actions, container, bash]
---

# CI Podman Containerized Validation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Run containerized validation (`just validate`) in GitHub Actions CI using rootless Podman |
| **Outcome** | Successful — CI builds and runs dev container on ubuntu-latest |
| **Verification** | verified-ci |

## When to Use

- CI workflow needs to build and run a Podman/Docker container for validation
- `set -u` (nounset) causes `unbound variable` errors with empty bash arrays in CI
- `shasum` command is not available on Ubuntu CI runners (only `sha256sum`)
- TTY allocation (`-t` flag) fails in headless CI environments

## Verified Workflow

### Quick Reference

```yaml
# .github/workflows/validate.yml
- name: Install Podman
  run: |
    sudo apt-get update -qq
    sudo apt-get install -y -qq podman
    podman info --format '{{.Host.Security.Rootless}}'

- name: Run validation gate
  run: just validate
```

```bash
# run_dev_container.sh — conditional TTY (string, not array)
tty_flag=""
if [ -t 1 ]; then
  tty_flag="-t"
fi
podman run --rm ${tty_flag} -v "${source_root}:/workspace:Z" ...
```

```bash
# setup.sh — sha256sum fallback for Linux CI
if command -v sha256sum >/dev/null 2>&1; then
  actual_sha="$(sha256sum "$installer" | awk '{print $1}')"
elif command -v shasum >/dev/null 2>&1; then
  actual_sha="$(shasum -a 256 "$installer" | awk '{print $1}')"
else
  echo "error: sha256sum or shasum is required" >&2
  exit 1
fi
```

### Detailed Steps

1. **Install Podman in CI**: Add `apt-get install podman` step before the containerized validation step. Verify rootless mode with `podman info`.
2. **Fix TTY flag**: Use a string variable (`""` or `"-t"`) instead of a bash array for the TTY flag. Empty arrays + `set -u` cause `unbound variable` errors on some bash versions.
3. **Add sha256sum fallback**: Ubuntu CI runners have `sha256sum` (coreutils) but not `shasum` (Perl). Use direct conditional calls — avoid `eval` with stored command strings.
4. **Update test assertions**: Tests that check podman command output should not assert `-t` since it's conditional on TTY availability.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Array-based tty_flag | `tty_flag=(); if [ -t 1 ]; then tty_flag=(-t); fi; "${tty_flag[@]}"` | `set -u` treats empty array as unbound variable | Use string variable instead of array for simple flag values |
| eval-based sha command | `sha_cmd="shasum -a 256"; eval "$sha_cmd" "$installer"` | eval with file paths is fragile and breaks on special characters | Use direct conditional calls with separate code paths |
| shasum-only check | `command -v shasum` | Ubuntu CI has `sha256sum` but not `shasum` | Try `sha256sum` first, fall back to `shasum` |

## Results & Parameters

- **CI runner**: `ubuntu-latest`
- **Podman version**: Whatever `apt-get` provides (4.x on Ubuntu 22.04+)
- **Bash**: 5.x on ubuntu-latest (supports string tty_flag pattern)
- **Containerfile**: `containers/dev/Containerfile`

## Verified On

| Project | Context | Details |
|---------|---------|-------|
| LLM360/Inference360 | PR #82 — Move inference360 module to package path | CI validate job passes with Podman on ubuntu-latest. Container image tag: inference360-dev:uv-0.11.18 |
