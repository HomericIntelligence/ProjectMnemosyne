---
name: docker-mojo-uid-mismatch-crash-fix
description: "Fix deterministic Mojo runtime crash (exit 134) when container image UID
  differs from host runner UID. Use when: (1) mojo run crashes before executing any
  user code with 'filesystem error: status: Permission denied [/home/.../.modular]',
  (2) CI passes locally (UID 1000) but fails in CI runner (UID 1001+), (3) crash is
  100% reproducible — not a flaky JIT issue, (4) cached CI image was built at a
  different UID than the current runner's uid, (5) execution crashed with
  __fortify_fail_abort in libKGENCompilerRTShared.so before any test output."
category: ci-cd
date: 2026-04-14
version: "1.1.0"
user-invocable: false
verification: verified-precommit
history: docker-mojo-uid-mismatch-crash-fix.history
tags:
  - docker
  - mojo
  - uid
  - permissions
  - container
  - crash
  - modular
  - cache-key
  - github-actions
---

# Docker Mojo UID Mismatch Crash Fix

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-14 |
| **Objective** | Fix deterministic CI failures where `mojo run` crashes before executing any user code |
| **Outcome** | Successful — crash reproduced and fixed; CI cache key fix added to prevent recurrence |
| **Verification** | verified-precommit (PR #5252 open, CI validation pending) |
| **Root Cause** | `libAsyncRTMojoBindings.so` calls `std::filesystem::status("$HOME/.modular")` at startup. When container UID ≠ home dir owner UID, `filesystem_error: Permission denied` propagates to `std::terminate` → `abort()`. Also triggered when CI image cache is keyed without runner UID, causing a UID-1000 cached image to run as UID-1001. |
| **Exit Code** | 134 (SIGABRT) |
| **History** | [changelog](./docker-mojo-uid-mismatch-crash-fix.history) |

## When to Use

- `mojo run` or `mojo test` crashes with exit code 134 before printing any user output
- Error message contains: `terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'`
- Error message contains: `filesystem error: status: Permission denied [/home/dev/.modular]`
- Stack trace shows `libKGENCompilerRTShared.so+0x6d4ab` / `+0x6a686` / `+0x6e157` + `libc.so.6+0x45330` (`__fortify_fail_abort`)
- CI fails deterministically but local tests pass (local UID 1000 matches image build UID)
- Image was built with `useradd -m` on Ubuntu (creates home dir with mode 750 by default)
- Container is run with a different UID than the one used during `docker build`
- CI image cache key does not include runner UID — a prior run cached at UID-1000, current run uses UID-1001

## Verified Workflow

> **Note:** Fixes 1-3 are verified-local (PR #5217). Fixes 4-5 are verified-precommit only (PR #5252, CI pending). Treat Fixes 4-5 as proposed until CI confirms.

### Quick Reference

```bash
# Fix 1: Dockerfile — make home dir traversable by other UIDs
RUN chmod 755 /home/${USER_NAME}

# Fix 2: Dockerfile — remove overly restrictive pixi permissions
# REMOVE: RUN chmod -R 700 $PIXI_HOME $PIXI_CACHE_DIR

# Fix 3: entrypoint.sh — pre-create .modular or redirect HOME
if [ ! -d "${HOME}/.modular" ]; then
    mkdir -p "${HOME}/.modular" 2>/dev/null || {
        export HOME="/tmp/mojo-home-$(id -u)"
        mkdir -p "${HOME}/.modular"
        export PIXI_HOME="${HOME}/.pixi"
    }
fi

# Fix 4: GitHub Actions cache key — include runner UID
- name: Get runner UID
  id: uid
  run: echo "user_id=$(id -u)" >> "$GITHUB_OUTPUT"
- uses: actions/cache@v4
  with:
    key: container-image-uid${{ steps.uid.outputs.user_id }}-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}

# Fix 5: justfile HOME-fixup for podman compose exec
HOME_FIXUP := "if [ ! -w \"$$HOME\" ]; then export HOME=\"/tmp/mojo-home-$$(id -u)\"; mkdir -p \"$$HOME/.modular\" \"$$HOME/.pixi\"; fi;"
_run CMD:
    podman compose exec -T myservice bash -c "{{ HOME_FIXUP }} {{ CMD }}"
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

6. **Apply Fix 4 — CI image cache key includes runner UID** — prevents stale UID-1000 image
   being reused on a UID-1001 runner:

   ```yaml
   # In GitHub Actions workflow or composite action:
   - name: Get runner UID
     id: uid
     run: echo "user_id=$(id -u)" >> "$GITHUB_OUTPUT"

   - name: Cache container image
     uses: actions/cache@v4
     with:
       path: /tmp/container-image.tar
       # Include UID in key so UID-1000 and UID-1001 images are cached separately
       key: container-image-uid${{ steps.uid.outputs.user_id }}-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
   ```

   **Important**: Use `${{ steps.uid.outputs.user_id }}` (step output), NOT `${{ env.USER_ID }}`.
   Environment variables set in an earlier step of the same action may not be evaluated correctly
   depending on runner version. Step outputs are always safe.

7. **Apply Fix 5 — justfile HOME-fixup for every `podman compose exec`** — belt-and-suspenders
   for any execution path that bypasses the entrypoint:

   ```makefile
   # In justfile, define a HOME fixup fragment
   HOME_FIXUP := "if [ ! -w \"$$HOME\" ]; then export HOME=\"/tmp/mojo-home-$$(id -u)\"; mkdir -p \"$$HOME/.modular\" \"$$HOME/.pixi\"; fi;"

   # Prepend to every podman compose exec invocation:
   _run CMD:
       podman compose exec -T myservice bash -c "{{ HOME_FIXUP }} {{ CMD }}"
   ```

8. **Rebuild and verify**:

   ```bash
   podman compose build --no-cache
   podman compose down -v
   USER_ID=1001 GROUP_ID=1001 podman compose up -d
   podman compose exec -T myservice bash -c "mojo run test.mojo"
   # -> Should print test output and exit 0
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Assumed JIT flakiness | Classified crash as non-deterministic `__fortify_fail_abort` JIT issue | Crash was 100% deterministic at UID mismatch; warm-cache local tests at UID 1000 always passed, masking the real bug | Never close a crash as "unfixable JIT flakiness" without first reproducing at the exact CI UID |
| Local parallel test run | Ran 10 parallel `mojo test` locally without replicating CI UID | Local UID = 1000 matched image owner, so home dir was accessible and all tests passed | Always replicate the exact runtime UID of the CI runner when diagnosing "CI-only" crashes |
| Setting `MODULAR_HOME` env var | Tried redirecting via `MODULAR_HOME=/tmp/.modular` | `libAsyncRTMojoBindings.so` reads `$HOME/.modular` directly via `std::filesystem::status`; env var redirect does not affect this call | The crash happens in native C++ before any Mojo env var handling; must fix permissions or pre-create the directory |
| Cache key without UID | CI image cache key used only `hashFiles(Dockerfile, pixi.toml, pixi.lock)` | A prior CI run at UID-1000 cached the image; current run at UID-1001 reused the stale image with wrong home dir owner | Include `$(id -u)` in the cache key so UID-1000 and UID-1001 images are always cached separately |
| `${{ env.VAR }}` for UID in cache key | Tried setting UID via `${{ env.USER_ID }}` in the same composite action | `${{ env.VAR }}` may not be evaluated when the env var is set in an earlier step of the same action (runner version dependent) | Use `${{ steps.<id>.outputs.<name> }}` for values computed in earlier steps — step outputs are always safe |

## Results & Parameters

### Crash Signature

```text
terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'
  what():  filesystem error: status: Permission denied [/home/dev/.modular]
Aborted (core dumped)
```

Exit code: **134** (SIGABRT from `std::terminate` → `abort()`)

Stack trace identifiers (Mojo 0.26.x):

```text
libKGENCompilerRTShared.so+0x6d4ab
libKGENCompilerRTShared.so+0x6a686
libKGENCompilerRTShared.so+0x6e157
libc.so.6+0x45330  (= __fortify_fail_abort)
```

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

### GitHub Actions Cache Key Template

```yaml
- name: Get runner UID
  id: uid
  run: echo "user_id=$(id -u)" >> "$GITHUB_OUTPUT"

- name: Cache container image
  uses: actions/cache@v4
  with:
    path: /tmp/container-image.tar
    key: container-image-uid${{ steps.uid.outputs.user_id }}-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
    restore-keys: |
      container-image-uid${{ steps.uid.outputs.user_id }}-
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
| --------- | --------- | --------- |
| ProjectOdyssey | CI deterministic crash reproduced and fixed locally, PR #5217 | UID 1001 CI runner vs UID 1000 image owner; `docker-compose.yml` with `USER_ID` ARG |
| ProjectOdyssey | CI cache key UID isolation added, PR #5252 | `setup-container/action.yml` amended to include `uid` step output in cache key; justfile `_run` recipe amended with HOME_FIXUP |
