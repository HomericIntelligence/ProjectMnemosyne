# Session Notes: pin-install-script-tag

## Context

- **Date**: 2026-03-07
- **Project**: ProjectOdyssey
- **Issue**: #3349 — "Pin just version in Dockerfile pre-built binary install"
- **PR**: #3982
- **Branch**: 3349-auto-impl

## Background

Issue #3349 was a follow-up to PR #3343 (issue #3152: replace `cargo install just` with
pre-built binary). In that migration, the `--version 1.14.0` pin from `cargo install just
--version 1.14.0` was NOT carried forward to the new curl installer command. The resulting
Dockerfile line always installed the latest `just` release:

```dockerfile
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin
```

## Fix Applied

Added `--tag 1.14.0` to pin the version:

```dockerfile
RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin --tag 1.14.0
```

## Implementation Steps

1. Read `.claude-prompt-3349.md` to understand the task
2. Searched for `just.systems/install.sh` in the codebase — found in `Dockerfile:38`
3. Read `Dockerfile` to confirm the unpinned line
4. Used `Edit` tool to add `--tag 1.14.0`
5. Verified diff with `git diff Dockerfile`
6. Committed with pre-commit hooks passing
7. Pushed to `origin/3349-auto-impl`
8. Created PR #3982

## Key Observation

When migrating from `cargo install <tool> --version X.Y.Z` to a pre-built binary installer,
the version pin should be carried forward **in the same PR**. Doing it as a follow-up creates
an extra PR and temporary reproducibility gap.

The `dockerfile-cargo-to-prebuilt-binary` skill even notes this in its Results section:
> "No version pin in this form (installs latest) — pin with `--tag v1.x.y` if needed"

This was a known gap that was deferred and became its own issue.

## Commit

```
fix(docker): pin just version to 1.14.0 for reproducible builds

Use --tag 1.14.0 flag in just.systems install script instead of
always fetching latest, matching previous cargo install pinning.

Closes #3349
```
