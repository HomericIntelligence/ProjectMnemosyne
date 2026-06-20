---
name: ci-cd-pixi-macos-runner-integration-test-gotcha
description: "Adding a macOS (osx-arm64) runner to a pixi-based GitHub Actions CI job, and the gotcha that the aggregate test recipe pulls in Docker/NATS integration tests that cannot run on macOS GitHub runners. Use when: (1) adding macos-latest / osx-arm64 to a pixi CI matrix or job, (2) a new macOS pixi job goes permanently red at test collection because integration fixtures connect to a service unconditionally, (3) deciding what test subset a macOS pixi job should run, (4) `pixi install --locked` fails with 'The workspace does not support <platform>', (5) reasoning about whether setup-python / a version matrix controls pixi's interpreter."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags: []
---

# Adding a macOS Runner to a Pixi CI Job: The Integration-Test Gotcha

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-19 |
| **Objective** | Add a macOS (osx-arm64) runner to a pixi-based CI job without producing a permanently-red job, and capture why the literal "run the test recipe on macOS" instruction is wrong |
| **Source context** | ProjectHermes #574 — planning session only; no CI ran and no macOS host executed the commands |
| **Outcome** | Hypothesis: run the unit subset (`-m "not integration"`) on the macOS runner; full validation deferred to CI |
| **Verification** | unverified — planning learning only; nothing was executed |

## When to Use

- Before adding `runs-on: macos-latest` (or `osx-arm64`) to a pixi-based GitHub Actions matrix or standalone job.
- When a freshly-added macOS pixi job is permanently red at pytest collection / fixture setup rather than on an assertion.
- When deciding which test subset a macOS pixi job should run versus the existing Linux job.
- When `pixi install --locked` fails fast with "The workspace does not support '\<platform>'" or a missing-platform lock error.
- When reasoning about whether `setup-python` or a version-matrix axis controls the interpreter a pixi job uses (it does not).

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has NOT been validated end-to-end. Treat it as a hypothesis until CI confirms. Verification level: `unverified` — sourced from a planning session for ProjectHermes #574; no CI ran, no macOS host executed the commands.

### Quick Reference

```bash
# 1. Confirm the platform is BOTH declared in pixi.toml and SOLVED into the lock.
grep -n "osx-arm64" pixi.toml          # must appear under [workspace] platforms
grep -c "osx-arm64" pixi.lock          # must be non-zero (the resolved graph exists)

# 2. On the macOS runner, install the locked env (exercises the new platform solve)
#    and run ONLY the unit subset — never the aggregate `just test` recipe.
pixi install --locked
pixi run pytest -m "not integration"   # matches the existing Linux unit job
```

### Detailed Steps

1. **Do NOT run the aggregate test recipe on macOS.** Recipes like `just test` typically expand to `pixi run pytest` over the FULL suite, including `-m integration` tests. Those integration tests depend on a live service (NATS, a database) that a Linux-only job starts via `docker run`. GitHub-hosted macOS runners have **no Docker daemon**, and integration fixtures that connect unconditionally (no skip-if-unavailable guard) will deterministically error at collection/fixture setup — a permanently-red macOS job.
2. **Run the unit subset instead:** `pixi run pytest -m "not integration"`, matching whatever the existing Linux unit job runs. This still satisfies the usual intent of a new-platform job, because (a) `pixi install --locked` exercises the new platform's dependency solve, and (b) importing the package during unit collection catches platform-specific import errors.
3. **Verify the platform is solved, not merely declared.** The target platform (`osx-arm64`/`osx-64`) must be present in `pixi.toml` `[workspace] platforms` AND solved into `pixi.lock`. Declaration alone is not enough: `pixi install --locked` fails fast with "The workspace does not support '\<platform>'" / a missing-platform lock error if the resolved graph is absent. Check with `grep -c osx-arm64 pixi.lock` (non-zero) before relying on `--locked`; regenerate the lock if it is zero.
4. **Pick the runner OS as the lever — not `setup-python` or a version matrix.** pixi installs its own conda-forge toolchain (including the Python interpreter) and ignores external `setup-python` / version-matrix axes. The thing that actually exercises a platform solve is the runner OS (`runs-on: macos-latest`), so declare the platform in `pixi.toml` rather than expecting an interpreter axis to do anything.
5. **Know the coverage gap.** `runs-on: macos-latest` is currently Apple-silicon (arm64), so it exercises `osx-arm64` only; `osx-64` remains solved-but-unexercised. Note this gap explicitly.
6. **Caching and fail-fast.** `setup-pixi`'s `cache: true` keys on `runner.os`, so a new OS automatically gets an isolated cache — no cache-key changes needed. If the job is expressed as a matrix, set `fail-fast: false` so a macOS-only failure does not cancel the Linux job. Pin actions to SHAs and pass an explicit `pixi-version`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Run `pixi run just test` on macOS as-written in the issue | Aggregate recipe pulls in `-m integration` tests | macOS GitHub runners have no Docker daemon to start NATS; fixtures connect unconditionally → collection/fixture error, permanently red | Filter to `-m "not integration"`; the literal issue command is wrong for macOS |
| Expect a `setup-python` / version matrix axis to control pixi's interpreter | pixi installs its own conda-forge toolchain | The axis is ignored | The runner OS is the lever; declare the platform in pixi.toml |
| Assume `--locked` works once `pixi.toml` declares the platform | Declaration ≠ solved lock | `--locked` fails fast if `pixi.lock` lacks the platform's resolved graph | Verify `pixi.lock` carries the platform solve (grep) or regenerate |

## Results & Parameters

Proposed copy-paste job block for the macOS pixi runner (replace `<sha>` with pinned action SHAs):

```yaml
  macos-tests:
    name: macos-tests
    runs-on: macos-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<sha>
      - uses: prefix-dev/setup-pixi@<sha>
        with:
          pixi-version: v0.68.0
          cache: true
      - name: Install locked environment (exercises osx-arm64 solve)
        run: pixi install --locked
      - name: Unit tests (no NATS/Docker on macOS runners)
        run: pixi run pytest -m "not integration"
```

**Notes:**

- `timeout-minutes: 15` — macOS runners are slower than Linux; budget extra time.
- `runs-on: macos-latest` exercises `osx-arm64` (Apple silicon) only; `osx-64` stays solved-but-unexercised — a known coverage gap.
- `setup-pixi` `cache: true` keys on `runner.os`, so the macOS job gets an isolated cache automatically; no cache-key edits required.
- If expressed as a matrix, add `strategy.fail-fast: false` so a macOS-only failure does not cancel the Linux job.
- `pixi install --locked` requires `osx-arm64` already declared in `pixi.toml` `[workspace] platforms` and solved into `pixi.lock`.
