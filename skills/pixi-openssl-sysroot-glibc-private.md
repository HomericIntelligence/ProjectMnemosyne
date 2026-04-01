---
name: pixi-openssl-sysroot-glibc-private
description: "Fix GLIBC_PRIVATE linker errors when using system OpenSSL with pixi conda-forge compiler. Use when: (1) seeing __libc_siglongjmp@GLIBC_PRIVATE or _dl_sym@GLIBC_PRIVATE errors, (2) linking a C library that depends on OpenSSL in a pixi environment, (3) Conan profile GCC version mismatch with pixi."
category: debugging
date: 2026-03-31
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - pixi
  - openssl
  - glibc
  - linker
  - conda-forge
  - sysroot
---

# Fix pixi + System OpenSSL GLIBC_PRIVATE Linker Errors

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-31 |
| **Objective** | Fix undefined reference to GLIBC_PRIVATE symbols when linking OpenSSL in a pixi/conda-forge C++ environment |
| **Outcome** | Solved — adding `openssl >= 3` to pixi.toml provides conda-forge-compatible OpenSSL |
| **Verification** | verified-local |

## When to Use

- Linker errors containing `GLIBC_PRIVATE` symbols: `__libc_siglongjmp`, `_dl_sym`, `__libc_thread_freeres`, `__libc_pthread_init`, `_dl_make_stack_executable`
- Using pixi with `cxx-compiler` from conda-forge and linking against system OpenSSL (`/usr/lib/x86_64-linux-gnu/libssl.so`)
- A C library fetched via FetchContent (e.g., nats.c) depends on OpenSSL and fails to link
- Conan profile says `compiler.version=13` but pixi ships GCC 14

## Verified Workflow

### Quick Reference

```toml
# pixi.toml — add openssl from conda-forge
[dependencies]
cxx-compiler = ">=1.7"
openssl = ">=3"           # CRITICAL: must come from conda-forge
```

```bash
# After adding openssl to pixi.toml
pixi install              # Pulls conda-forge OpenSSL
rm -rf build/debug        # MUST clean — stale cache has system OpenSSL paths
cmake --preset debug      # Now finds conda-forge OpenSSL
cmake --build --preset debug
```

### Root Cause

The pixi conda-forge `cxx-compiler` uses its own sysroot (`~/.pixi/envs/default/x86_64-conda-linux-gnu/sysroot/`). When `find_package(OpenSSL)` resolves to the **system** OpenSSL at `/usr/lib/x86_64-linux-gnu/libssl.so`, the system libraries reference GLIBC symbols from `/lib/x86_64-linux-gnu/libc.so.6` — but the conda-forge linker expects its sysroot's libc, which doesn't export the `@GLIBC_PRIVATE` symbols.

**Fix:** Provide OpenSSL through conda-forge (`pixi.toml` dependency) so it's built against the same sysroot as the compiler.

### Also: Match Conan Profile GCC Version

```bash
# Check actual pixi GCC version
pixi run g++ --version
# Output: g++ (conda-forge gcc 14.3.0-18) 14.3.0
```

```ini
# conan/profiles/debug — must match!
[settings]
compiler=gcc
compiler.version=14    # NOT 13
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| System OpenSSL with pixi linker | `find_package(OpenSSL)` found `/usr/lib/x86_64-linux-gnu/libssl.so` | pixi's conda linker uses different sysroot — GLIBC_PRIVATE symbols undefined | Add `openssl >= 3` to pixi.toml so OpenSSL comes from conda-forge |
| Conan profile `compiler.version=13` | Assumed GCC 13 was standard | pixi conda-forge ships GCC 14.3.0 — version mismatch causes Conan package hash errors | Always run `pixi run g++ --version` and match the Conan profile |
| Rebuild without cleaning CMakeCache | Added OpenSSL to pixi.toml and re-ran cmake | CMakeCache.txt cached the system OpenSSL path from the previous configure | Always delete build directory when changing how OpenSSL is provided |

## Results & Parameters

```yaml
# Error signature (look for these in linker output)
error_patterns:
  - "undefined reference to `__libc_siglongjmp@GLIBC_PRIVATE'"
  - "undefined reference to `_dl_sym@GLIBC_PRIVATE'"
  - "undefined reference to `__libc_thread_freeres@GLIBC_PRIVATE'"
  - "undefined reference to `__libc_pthread_init@GLIBC_PRIVATE'"

# Fix
pixi_dep: "openssl >= 3"
clean_required: true  # Must delete build/ after adding

# Also needed in CMakeLists.txt when statically linking nats.c
cmake_additions:
  - "find_package(OpenSSL REQUIRED)"
  - "target_link_libraries(... OpenSSL::SSL OpenSSL::Crypto)"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectNestor | nats.c static link failed with GLIBC_PRIVATE errors | Fixed by adding `openssl >= 3` to pixi.toml + cleaning build dir |
| ProjectAgamemnon | Same nats.c + OpenSSL pattern | Same fix applied preventatively |
