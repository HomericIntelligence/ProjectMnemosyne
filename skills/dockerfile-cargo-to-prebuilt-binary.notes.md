# Session Notes: dockerfile-cargo-to-prebuilt-binary

## Session Context

- **Date**: 2026-03-05
- **Project**: ProjectOdyssey
- **Issue**: #3152 — [P2-2] Fix Dockerfile issues (double Pixi install, slow cargo install just)
- **PR**: #3343
- **Branch**: `3152-auto-impl`

## Problem Statement

Two Dockerfile issues slowed down builds:

1. `Dockerfile`: `cargo install just --version 1.14.0` at line 80 compiles Just from source
   via Rust — this is very slow (5-15 minutes).
2. `Dockerfile.ci`: Pixi install appears twice across build stages (lines 23 and 54) using
   unpinned `curl -fsSL https://pixi.sh/install.sh | bash`.

The issue also noted potential duplicate Pixi install in `Dockerfile`, but after reading
the file carefully, the Pixi install at line 68 was the ONLY install (not a duplicate) —
the PATH at line 50 was just pre-emptively setting up the expected location.

## Changes Made

### Dockerfile

```diff
-    cargo \
     && rm -rf /var/lib/apt/lists/*
```

```diff
+# Install just tool (pre-built binary, much faster than cargo install)
+RUN curl -fsSL https://just.systems/install.sh | bash -s -- --to /usr/local/bin
+
 # ---------------------------
 # Stage 1.5: Create dev user
```

```diff
-ENV PATH="$HOME/.local/bin:$HOME/.pixi/bin:$PATH:$HOME/.cargo/bin"
+ENV PATH="$HOME/.local/bin:$HOME/.pixi/bin:$PATH"
```

```diff
-# Install just tool
-RUN cargo install just --version 1.14.0
-
 # Install project dependencies
```

### Dockerfile.ci

```diff
+ENV PIXI_VERSION=0.65.0
 # ...
-RUN curl -fsSL https://pixi.sh/install.sh | bash
+RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash
```

Applied to both `builder` (line ~23) and `runtime` (line ~54) stages.

## Key Decision: Where to install just

Initial attempt placed the `just` install in the `development` stage after `USER ${USER_NAME}`.
This failed conceptually because `/usr/local/bin` requires root. The fix was to move the
install to the `base` stage where it runs as root, making `just` available to all derived
stages.

## Pre-commit Results

All hooks passed when skipping mojo-format (GLIBC environment constraint):

```
SKIP=mojo-format pixi run pre-commit run --all-files
Mojo Format.............................................................Skipped
Check for deprecated List[Type](args) syntax.............................Passed
Check for shell=True (Security)..........................................Passed
Ruff Format Python.......................................................Passed
Ruff Check Python........................................................Passed
Validate Test Coverage...................................................Passed
Markdown Lint............................................................Passed
...all others Passed
```

The mojo-format failure is a pre-existing environment issue (system GLIBC too old for
the installed Mojo binary) — unrelated to these changes.

## Pixi Version Used

Checked with `pixi --version` → `pixi 0.65.0`. This was used as the pinned version.

## just Installer URL

`https://just.systems/install.sh` — official installer that accepts `--to <dir>` flag.
Can also accept `--tag <version>` for pinning to a specific version.