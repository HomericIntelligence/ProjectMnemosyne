---
name: docker-mojo-uid-mismatch-crash-fix
description: "Fix deterministic Mojo runtime crash (exit 134) when container image UID
  differs from host runner UID. Use when: (1) mojo run crashes before executing any
  user code with 'filesystem error: status: Permission denied [/home/.../.modular]',
  (2) CI passes locally (UID 1000) but fails in CI runner (UID 1001+), (3) crash is
  100% reproducible — not a flaky JIT issue."
category: ci-cd
date: 2026-04-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - docker
  - mojo
  - uid
  - permissions
  - container
  - crash
  - modular
---

# Docker Mojo UID Mismatch Crash Fix

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-11 |
| **Objective** | Fix deterministic CI failures where `mojo run` crashes before executing any user code |
| **Outcome** | Successful — crash reproduced and fixed locally; CI PR #5217 filed with auto-merge |
| **Verification** | verified-local (crash reproduced and fixed locally; CI validation pending) |
| **Root Cause** | `libAsyncRTMojoBindings.so` calls throwing `std::filesystem::status("$HOME/.modular")` at startup. When container UID ≠ home dir owner UID, `filesystem_error: Permission denied` propagates to `std::terminate` → `abort()` |
| **Exit Code** | 134 (SIGABRT) |

## When to Use

- `mojo run` or `mojo test` crashes with exit code 134 before printing any user output
- Error message contains: `terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'`
- Error message contains: `filesystem error: status: Permission denied [/home/dev/.modular]`
- CI fails deterministically but local tests pass (local UID 1000 matches image build UID)
- Image was built with `useradd -m` on Ubuntu (creates home dir with mode 750 by default)
- Container is run with a different UID than the one used during `docker build`

## Verified Workflow

### Quick Reference

```bash
# Fix 1: Dockerfile — make home dir traversable by other UIDs
# After useradd, add:
RUN chmod 755 /home/${USER_NAME}

# Fix 2: Dockerfile — remove overly restrictive pixi permissions
# REMOVE this line:
# RUN chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR

# Fix 3: entrypoint.sh — pre-create .modular or redirect HOME
if [ ! -d "${HOME}/.modular" ]; then
    mkdir -p "${HOME}/.modular" 2>/dev/null || {
        export HOME="/tmp/mojo-home-$(id -u)"
        mkdir -p "${HOME}/.modular"
        export PIXI_HOME="${HOME}/.pixi"
    }
fi
```

### Detailed Steps

1. **Identify the crash** — confirm exit code 134 and the `filesystem_error` message:

   ```bash
   podman compose exec -T myservice bash -c "mojo run test.mojo"; echo "Exit: $?"
   # Expected crash output:
   # terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'
   #   what():  filesystem error: status: Permission denied [/home/dev/.modular]
   # Exit: 134
   ```

2. **Reproduce the UID mismatch** (confirm root cause, not a coincidence):

   ```bash
   podman compose down -v             # delete ALL volumes (cold cache)
   USER_ID=1001 GROUP_ID=1001 podman compose up -d
   podman compose exec -T myservice bash -c "mojo run test.mojo"
   # -> crash: filesystem error: status: Permission denied [/home/dev/.modular]
   ```

3. **Apply Fix 1 — Dockerfile home dir permissions** — after your `useradd` line, add:

   ```dockerfile
   RUN useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USER_NAME} && \
       chmod 755 /home/${USER_NAME}
   ```

   Ubuntu's `useradd -m` creates home directories with mode 750 (`drwxr-x---`),
   which blocks `execute` (traverse) permission for other UIDs. Mode 755 allows
   traversal without granting write access.

4. **Apply Fix 2 — Remove restrictive pixi permissions** — remove or relax:

   ```dockerfile
   # REMOVE this if present:
   RUN chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR

   # Replace with no chmod (pixi creates files with reasonable defaults)
   # OR use 755 if explicit control is needed:
   RUN chmod -R 755 $PIXI_HOME $PIXI_CACHE_DIR
   ```

5. **Apply Fix 3 — entrypoint.sh pre-create `.modular`** — add before invoking mojo:

   ```bash
   #!/bin/bash
   # Pre-create .modular so libAsyncRTMojoBindings.so startup check doesn't throw
   if [ ! -d "${HOME}/.modular" ]; then
       mkdir -p "${HOME}/.modular" 2>/dev/null || {
           # HOME is not writable by current UID — redirect to /tmp
           export HOME="/tmp/mojo-home-$(id -u)"
           mkdir -p "${HOME}/.modular"
           export PIXI_HOME="${HOME}/.pixi"
       }
   fi

   exec "$@"
   ```

6. **Rebuild and verify**:

   ```bash
   podman compose build --no-cache
   podman compose down -v
   USER_ID=1001 GROUP_ID=1001 podman compose up -d
   podman compose exec -T myservice bash -c "mojo run test.mojo"
   # -> Should print test output and exit 0
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Assumed JIT flakiness | Classified crash as non-deterministic `__fortify_fail_abort` JIT issue | Crash was 100% deterministic at UID mismatch; warm-cache local tests at UID 1000 always passed, masking the real bug | Never close a crash as "unfixable JIT flakiness" without first reproducing at the exact CI UID |
| Local parallel test run | Ran 10 parallel `mojo test` locally without replicating CI UID | Local UID = 1000 matched image owner, so home dir was accessible and all tests passed | Always replicate the exact runtime UID of the CI runner when diagnosing "CI-only" crashes |
| Setting `MODULAR_HOME` env var | Tried redirecting via `MODULAR_HOME=/tmp/.modular` | `libAsyncRTMojoBindings.so` reads `$HOME/.modular` directly via `std::filesystem::status`; env var redirect does not affect this call | The crash happens in native C++ before any Mojo env var handling; must fix permissions or pre-create the directory |

## Results & Parameters

### Crash Signature

```text
terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'
  what():  filesystem error: status: Permission denied [/home/dev/.modular]
Aborted (core dumped)
```

Exit code: **134** (SIGABRT from `std::terminate` → `abort()`)

### Root Cause Chain

```text
mojo run → dlopen libAsyncRTMojoBindings.so
  → getAcceleratorArchOrEmpty()
    → std::filesystem::status("$HOME/.modular")   ← throwing overload
      → filesystem_error: Permission denied        ← home dir is mode 750, UID mismatch
        → std::terminate() → abort() → SIGABRT
```

### Dockerfile Fix Template

```dockerfile
ARG USER_NAME=dev
ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g ${GROUP_ID} ${USER_NAME} && \
    useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USER_NAME} && \
    chmod 755 /home/${USER_NAME}          # <-- CRITICAL: allow other UIDs to traverse

# If you set pixi cache/home permissions, use 755 not 700:
ENV PIXI_HOME=/home/${USER_NAME}/.pixi
ENV PIXI_CACHE_DIR=/home/${USER_NAME}/.cache/rattler
# Do NOT: RUN chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR
```

### Upstream Bug

Filed as **modular/modular#6412**. The fix in Mojo's C++ runtime should replace:

```cpp
std::filesystem::status(path)          // throwing overload — NEVER throws safely
```

with:

```cpp
std::error_code ec;
std::filesystem::status(path, ec)      // error_code overload — never throws
if (ec) return "";
```

### Verification Commands

```bash
# Verify home dir permissions are correct (should show drwxr-xr-x = 755)
podman compose exec -T myservice stat /home/dev | grep Access

# Verify mojo runs as different UID without crash
USER_ID=1001 GROUP_ID=1001 podman compose up -d
podman compose exec -T myservice bash -c "id && mojo run -e 'print(42)'"
# Expected: uid=1001 ... \n 42
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | CI deterministic crash reproduced and fixed locally, PR #5217 | UID 1001 CI runner vs UID 1000 image owner; `docker-compose.yml` with `USER_ID` ARG |
