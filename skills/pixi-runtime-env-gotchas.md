---
name: pixi-runtime-env-gotchas
description: "Use when: (1) pixi silently re-solves the shared .pixi/envs/default and wipes the pip install -e . editable install mid-run after a worktree edit to pyproject.toml, (2) CI logs show 'Saved cache with ID -1' or cache hits are inconsistent despite cache: true in setup-pixi, (3) adding a second actions/cache over .pixi poisons a locked pixi env (downgrades packages, fails pip-audit), (4) a pre-commit hook invoking 'pixi run <command>' resolves to the system-installed binary instead of the project's pixi env binary because dev-install was not run, (5) GLIBC_PRIVATE linker errors appear when using system OpenSSL with a pixi conda-forge compiler toolchain."
category: debugging
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: pixi-runtime-env-gotchas.history
tags:
  - pixi
  - editable-install
  - pip-install-e
  - dev-install
  - env-resolve
  - module-not-found
  - swarm-worktree
  - actions-cache
  - setup-pixi
  - cache-poisoning
  - pip-audit
  - pre-commit
  - binary-resolution
  - openssl
  - glibc
  - linker
  - conda-forge
  - sysroot
---

# Pixi Runtime Environment Gotchas

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-07 |
| **Objective** | Diagnose and recover from pixi runtime environment bugs that manifest AFTER install: env re-solve wiping the editable install in swarm worktrees, unreliable GHA caching (`Saved cache with ID -1`) and locked-env cache poisoning, pre-commit hooks resolving to the wrong pixi env binary, and GLIBC_PRIVATE linker errors mixing system OpenSSL with a conda-forge toolchain |
| **Outcome** | Each failure mode has a confirmed root cause and a copy-paste recovery: `pixi run dev-install` restores a wiped editable install; explicit `actions/cache` (non-locked) or built-in-only caching (locked) fixes GHA caching; `pixi run dev-install` populates the correct pre-commit binary; `openssl >= 3` from conda-forge resolves the linker errors |
| **Verification** | verified-ci |
| **History** | [changelog](./pixi-runtime-env-gotchas.history) |

## When to Use

Use this skill for pixi bugs that appear **after** a successful install — the env exists, but something at runtime is wrong. Specifically:

- A long-running driver (ecosystem driver, automation loop, watcher) that worked at startup begins emitting `ModuleNotFoundError: No module named '<pkg>'` mid-run, with a sharp before/after cliff at one UTC timestamp.
- A myrmidon / parallel-agent swarm is editing `pyproject.toml` inside worktrees that share `.pixi/envs/default` with the driver's parent checkout.
- `stat -c '%Y' .pixi/envs/default/conda-meta` shows a timestamp newer than the last `pixi run dev-install`.
- CI logs show `Saved cache with ID -1` or HTTP 400 after a `prefix-dev/setup-pixi` step with `cache: true`; cache hits are inconsistent or never occur.
- `security` / `dependency-scan` (pip-audit) fails on EVERY PR even though `pixi.lock` is already patched, and the version setup-pixi installs differs from the version pip-audit audits.
- A pre-commit hook invoking `pixi run <command>` fails locally with an error that refers to `pyproject.toml`/`pixi.toml` content that also exists on `origin/main` (which CI passes).
- `which <command>` inside `pixi run` returns `~/.local/bin/...` instead of `.pixi/envs/default/bin/...`.
- Linker errors contain `GLIBC_PRIVATE` symbols (`__libc_siglongjmp`, `_dl_sym`, `__libc_thread_freeres`, `__libc_pthread_init`, `_dl_make_stack_executable`) when linking a C library that depends on OpenSSL in a pixi conda-forge environment.

Do NOT use this skill for:

- pixi.toml authoring / dependency version constraints / lockfile churn — those are separate concerns.
- Stale console-script entry points after `git pull` (a Python packaging issue, not a pixi env runtime bug).
- The package was never installed editable in the first place (run `pixi run dev-install` once; no env-resolve happened).

## Verified Workflow

### Quick Reference

```bash
# (A) EDITABLE INSTALL WIPED BY ENV RE-SOLVE — restore from the PARENT worktree:
stat -c '%Y %n' .pixi/envs/default/conda-meta            # newer than last dev-install? re-solved.
pixi run python -c "import <pkg>; print(<pkg>.__version__)"   # ModuleNotFoundError = wiped
pixi run dev-install                                      # idempotent, O(seconds)
pixi run python -c "import <pkg>; print(<pkg>.__version__)"   # now prints <base>.devN+g<sha>

# (B) GHA CACHE 'Saved cache with ID -1' (NON-locked) — drop cache: true, add explicit cache:
#   actions/cache@v5 over BOTH .pixi and ~/.cache/rattler/cache, keyed on hashFiles('pixi.lock')

# (C) LOCKED-ENV CACHE POISONING — remove ANY second actions/cache over .pixi; rely on built-in:
gh run view <run-id> --log | grep -iE "pixi install .*--locked|Cache restored from key|vulnerab"

# (D) PRE-COMMIT WRONG BINARY — populate the project's console scripts into the pixi env:
pixi run dev-install
pixi run --environment default which <command>   # must be .pixi/envs/default/bin/<command>

# (E) GLIBC_PRIVATE LINKER ERRORS — provide OpenSSL from conda-forge, then clean-rebuild:
#   pixi.toml: [dependencies] openssl = ">=3"
pixi install && rm -rf build/debug && cmake --preset debug && cmake --build --preset debug
```

### Detailed Steps

#### (A) Env re-solve in a swarm worktree silently drops the editable install

**Why it happens.** Projects that keep the package OUT of `[pypi-dependencies]` and instead run a `pixi run dev-install` task (`pip install -e . --no-deps`) drop `.pth` / `.egg-link` files into `.pixi/envs/default/lib/python3.X/site-packages/`. This editable install is invisible to pixi's solver. The moment pixi decides it must re-create `.pixi/envs/default` (because `pyproject.toml` was touched in a way it deems significant), it nukes the env and rebuilds from `pixi.lock` — and the editable install is gone, because it was never in the lockfile. There is **no** explicit "Uninstalled" log line; the fingerprint is the `conda-meta` mtime.

`pixi run` re-solves when any of these change in `pyproject.toml`: `[project.scripts]` (add/remove/rename), `[project.dependencies]`, `[project.optional-dependencies]`, `[build-system]`, `[tool.hatch.version]`. Worktrees inherit the parent checkout's `.pixi/envs/default`, so one worktree mutating `pyproject.toml` and then invoking `pixi run` re-solves the env that ALL worktrees (and the parent) share.

1. **Detect the cliff.** Grep the driver log for the boundary — the last `Successfully installed <Pkg>-` line marks the last good install; every later run that imports the package fails:

   ```bash
   grep -E "ModuleNotFoundError: No module named '<pkg>'|Successfully installed <Pkg>-" driver.log | head
   ```

2. **Confirm the re-solve.** The `conda-meta` mtime is the fingerprint of the last env-resolve:

   ```bash
   stat -c '%Y %n' .pixi/envs/default/conda-meta
   date -u -d @"$(stat -c '%Y' .pixi/envs/default/conda-meta)"
   ```

   If that timestamp lies between the last successful run and the first `ModuleNotFoundError`, the env was re-solved mid-session.

3. **Identify the trigger.** The most-recently-modified `pyproject.toml` across worktrees is the cause:

   ```bash
   for wt in $(git worktree list --porcelain | awk '/^worktree /{print $2}'); do
     echo "=== $wt ==="; stat -c '%y %n' "$wt/pyproject.toml" 2>/dev/null
   done
   ```

4. **Restore from the PARENT worktree** (not from a swarm worktree, whose `pyproject.toml` may re-trigger the re-solve):

   ```bash
   pixi run dev-install
   pixi run python -c "import <pkg>; print(<pkg>.__version__)"   # <base>.devN+g<sha>
   ```

   For hatch-vcs projects the version is `<base>.devN+g<sha>`; if the SHA matches `git rev-parse --short HEAD`, the install is current.

5. **Restart any long-running drivers** started before the re-solve — they cached a now-stale `sys.path`.

6. **Preventive pre-flight check** at the top of each driver loop, turning a silent mid-run failure into one loud, actionable message:

   ```python
   import importlib

   def _assert_editable_install_present():
       try:
           importlib.import_module("<pkg>")
       except ModuleNotFoundError as exc:
           raise SystemExit(
               "FATAL: <pkg> is not importable. The pixi env was likely re-solved "
               "by a worktree edit. Run `pixi run dev-install` from the parent "
               "worktree and restart the driver."
           ) from exc

   _assert_editable_install_present()
   ```

#### (B) `cache: true` in setup-pixi is unreliable (non-locked workflows)

`prefix-dev/setup-pixi@v0.9.x` with `cache: true` uses an internal caching mechanism that can silently fail, logging `Saved cache with ID -1` — the cache is never saved and every CI run rebuilds from scratch. The fix is to drop `cache: true` and add an explicit `actions/cache@v5` over BOTH paths pixi uses, keyed on the lockfile:

```yaml
# .github/actions/setup-pixi/action.yml  (NON-locked case)
- name: Set up Pixi
  uses: prefix-dev/setup-pixi@v0.9.4
  with:
    pixi-version: ${{ inputs.pixi-version }}
- name: Cache Pixi environments
  uses: actions/cache@v5
  with:
    path: |
      .pixi
      ~/.cache/rattler/cache
    key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
    restore-keys: |
      pixi-${{ runner.os }}-
```

Key decisions: omit `cache: true`; hash `pixi.lock` (encodes exact resolved versions) not `pixi.toml`; cache both `.pixi` (env) AND `~/.cache/rattler/cache` (downloads); match the `actions/cache@` version the repo already uses.

#### (C) Locked mode: do NOT add a second `.pixi` cache (it poisons the env)

When a workflow uses `setup-pixi` with `locked: true` (`pixi install -e <env> --locked`), setup-pixi ALREADY caches `.pixi` keyed exactly on the `pixi.lock` hash and installs the correct locked env. Adding a SECOND `actions/cache` over the same `.pixi` poisons it:

1. setup-pixi installs the CORRECT locked versions (e.g. urllib3 `2.7.0`).
2. A later `actions/cache` restore extracts a STALE `.pixi` archive on top — whichever cache restores LAST wins — silently downgrading packages (urllib3 `2.7.0` → `2.6.3`).
3. `pip-audit` audits the DOWNGRADED env and reports vulnerabilities (e.g. `PYSEC-2026-141`), failing `dependency-scan` on every PR even though `pixi.lock` is patched.

**Both poisoning variants are dangerous** — loose `restore-keys:` falls back to any prior lock's cache, and an exact-key-only cache exact-hits a cache a PREVIOUS poisoned run saved under the same lock hash. "No `restore-keys` = safe" is WRONG. ANY second `actions/cache` over `.pixi` after a `--locked` setup-pixi is unsafe.

Diagnosis (a version mismatch between install and audit is the signature):

```bash
gh run view <run-id> --log | grep -iE "pixi install .*--locked|Cache restored from key|vulnerab|urllib3"
```

Fix: remove the redundant second `actions/cache` over `.pixi` across ALL workflows (composite actions, `release.yml`, `pre-commit.yml`, `security.yml`) and rely solely on setup-pixi's built-in lock-keyed cache.

```bash
grep -rn -A8 "actions/cache" .github/workflows/ .github/actions/ | grep -n "\.pixi"   # confirm none remain
```

Decision tree:

```text
Does the workflow use setup-pixi with locked: true (or pixi install --locked)?
├─ YES → DO NOT add a second actions/cache over .pixi. Rely on built-in lock-keyed cache. Remove any existing one.
└─ NO  → cache: true is unreliable → use ONE explicit actions/cache over .pixi + ~/.cache/rattler/cache keyed on pixi.lock.
```

#### (D) Pre-commit hook resolves to the system binary instead of the pixi env binary

When `pixi run <command>` is invoked (directly or via a pre-commit hook), pixi resolves the binary as: (1) pixi env bin `.pixi/envs/default/bin/` — only populated AFTER `pixi run dev-install`; (2) system PATH fallback — picks up `~/.local/bin/<command>` if (1) is empty. Without `dev-install`, `pixi run` falls through to a globally-installed binary that may be a different (often newer, stricter) version, producing false-positive failures that CI doesn't reproduce (because the CI pre-commit job runs `pixi run dev-install` first).

```bash
pixi run dev-install
pixi run --environment default which <command>
# Expected: <repo-root>/.pixi/envs/default/bin/<command>
# NOT:      /home/<user>/.local/bin/<command>
pre-commit run --all-files
```

Always verify the failing check passes on `origin/main` before "fixing" `pyproject.toml` — if it does, the failure is a local environment issue, not a real one.

#### (E) GLIBC_PRIVATE linker errors: system OpenSSL vs conda-forge toolchain

The pixi conda-forge `cxx-compiler` uses its own sysroot (`~/.pixi/envs/default/x86_64-conda-linux-gnu/sysroot/`). When `find_package(OpenSSL)` resolves to the SYSTEM OpenSSL (`/usr/lib/x86_64-linux-gnu/libssl.so`), those system libs reference GLIBC symbols from the system libc — but the conda-forge linker expects its sysroot's libc, which doesn't export the `@GLIBC_PRIVATE` symbols. Provide OpenSSL through conda-forge so it's built against the same sysroot:

```toml
# pixi.toml
[dependencies]
cxx-compiler = ">=1.7"
openssl = ">=3"           # CRITICAL: must come from conda-forge
```

```bash
pixi install
rm -rf build/debug        # MUST clean — CMakeCache caches the stale system OpenSSL path
cmake --preset debug
cmake --build --preset debug
```

Also match the Conan profile GCC version to what pixi ships (a mismatch causes Conan package-hash errors):

```bash
pixi run g++ --version    # e.g. g++ (conda-forge gcc 14.3.0-18) 14.3.0
```

```ini
# conan/profiles/debug
[settings]
compiler=gcc
compiler.version=14       # match pixi, NOT 13
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Continue the swarm run after the first `ModuleNotFoundError` | Assumed a flaky import | Every repo started after the env-resolve timestamp failed identically; the loss compounded | A sharp before/after cliff at one timestamp is structural, not flaky — stop and investigate env state |
| Re-run `pixi install` alone to fix the wiped editable install | `pixi install` builds the env from `pixi.lock` | It does NOT run the `dev-install` task; the editable install stays missing | `pixi install` and `pixi run dev-install` are different operations; you need the latter after any env-resolve |
| Run `pixi run dev-install` from inside a swarm worktree | Recovery attempted from the worktree that triggered the re-solve | The worktree's `pyproject.toml` re-triggers another re-solve | Always run `pixi run dev-install` from the parent / clean worktree |
| Keep `cache: true` in setup-pixi | Used `prefix-dev/setup-pixi@v0.9.4` with `cache: true` | Fails silently; logs "Saved cache with ID -1"; no cache ever saved | Never use `cache: true` — use an explicit `actions/cache` (non-locked case) |
| Cache only `.pixi` | Cached `.pixi`, skipped `~/.cache/rattler/cache` | Pixi re-downloads packages on every run even on a `.pixi` hit | Must cache BOTH paths or the cache is incomplete |
| Hash `pixi.toml` as the cache key | Used `hashFiles('pixi.toml')` | `pixi.toml` doesn't encode resolved versions; false-positive cache hits | Use `pixi.lock` for precise invalidation |
| Second `actions/cache` over `.pixi` under `locked: true` | Kept built-in cache AND added an explicit `actions/cache@v5` over the same `.pixi` | The second restore extracts a STALE `.pixi` over the fresh `--locked` install (last restore wins), downgrading urllib3 2.7.0 → 2.6.3; pip-audit then fails `dependency-scan` | With `locked: true`, never layer a second cache over `.pixi` — rely solely on setup-pixi's built-in lock-keyed cache |
| "No `restore-keys` = safe" assumption | Fixed only workflows with loose `restore-keys`, left an exact-key-only `.pixi` cache in place | The exact key hit a `.pixi` cache a PREVIOUS poisoned run saved under the same lock hash — restored the poison | An exact-key-only `.pixi` cache is NOT safe; ANY second cache over `.pixi` after `--locked` is unsafe |
| Bump `pixi.lock` to the patched version alone | Updated `pixi.lock` so the locked env had urllib3 2.7.0 | The poisoning cache still restored 2.6.3 over the patched install | Patching the lock is necessary but not sufficient — also remove the redundant `.pixi` cache |
| Remove `[project.optional-dependencies]` to satisfy a pre-commit hook | The hook flagged the section as forbidden | The section is legitimately needed for PyPI packaging; the hook was using a stale system binary | Never remove `pyproject.toml` sections to satisfy a hook without first verifying the hook's binary version (run `dev-install`) |
| System OpenSSL with the pixi conda linker | `find_package(OpenSSL)` resolved to `/usr/lib/x86_64-linux-gnu/libssl.so` | The conda linker uses a different sysroot — GLIBC_PRIVATE symbols undefined | Add `openssl >= 3` to `pixi.toml` so OpenSSL comes from conda-forge |
| Rebuild without cleaning CMakeCache | Added OpenSSL to `pixi.toml` and re-ran cmake | `CMakeCache.txt` cached the system OpenSSL path | Always delete the build directory when changing how OpenSSL is provided |

## Results & Parameters

### Editable-install recovery (verified)

```bash
# From the PARENT worktree, NOT a swarm worktree:
pixi run dev-install
pixi run python -c "import <pkg>; print(<pkg>.__version__)"
```

Recovery is O(seconds) — pip re-uses cached wheel data and only writes the `.pth` / `.egg-link`.

| Signal | Means |
|--------|-------|
| `ModuleNotFoundError: No module named '<pkg>'` mid-run | Editable install lost — investigate env-resolve |
| Sharp before/after cliff at ONE timestamp | Structural, not flaky |
| `stat -c '%Y' .pixi/envs/default/conda-meta` > last `dev-install` time | Env was re-solved |
| Any worktree's `pyproject.toml` mtime > last `dev-install` | Likely trigger |
| `pixi run pip show <pkg>` returns `Package(s) not found` | Editable install gone — re-run `pixi run dev-install` |

### GHA caching parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `actions/cache` version | `@v5` | Match what other workflows use |
| Cache path 1 | `.pixi` | Project environment directory |
| Cache path 2 | `~/.cache/rattler/cache` | Package download cache — must include both |
| Cache key hash source | `pixi.lock` | More precise than `pixi.toml` |
| Restore key prefix | `pixi-${{ runner.os }}-` | Only when NOT using `locked: true` |
| `cache: true` | **omit** | Unreliable — causes "Saved cache with ID -1" |
| Second `actions/cache` over `.pixi` under `locked: true` | **remove** | Poisons the locked install; fails pip-audit |
| Locked-mode caching | built-in setup-pixi cache only | Exact-keys `.pixi` on `pixi.lock`; never clobbers the install |

### Pre-commit binary resolution

```bash
pixi run dev-install
pixi run --environment default which <command>   # must be .pixi/envs/default/bin/<command>
```

CI reference pattern (always runs `dev-install` before hooks):

```yaml
- name: Run pre-commit
  run: |
    pixi install --environment lint
    pixi install --environment default
    pixi run dev-install            # CRITICAL: populates .pixi/envs/default/bin
    pixi run --environment lint pre-commit run --all-files
```

### OpenSSL / GLIBC_PRIVATE

```yaml
error_patterns:
  - "undefined reference to `__libc_siglongjmp@GLIBC_PRIVATE'"
  - "undefined reference to `_dl_sym@GLIBC_PRIVATE'"
  - "undefined reference to `__libc_thread_freeres@GLIBC_PRIVATE'"
  - "undefined reference to `__libc_pthread_init@GLIBC_PRIVATE'"
pixi_dep: "openssl >= 3"
clean_required: true     # delete build/ after adding
cmake_additions:
  - "find_package(OpenSSL REQUIRED)"
  - "target_link_libraries(... OpenSSL::SSL OpenSSL::Crypto)"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-31 — 10-PR myrmidon swarm run | Driver started 23:04:26Z (`Successfully installed ...-0.9.4.dev14+g3fcc2f0fb`); at 23:59:47Z `.pixi/envs/default/conda-meta` mtime jumped (re-solve); from 23:59:48Z, 6 repo runs of `scripts/drive_prs_green.py` died with `ModuleNotFoundError`. Trigger: a swarm worktree added a `[project.scripts]` entry then ran `pixi run pytest`. `pixi run dev-install` from the parent restored importability. |
| ProjectHephaestus | PR #633 rebase — `check-dep-sync` pre-commit false positive | Local binary was v0.9.5 system install; project was v0.9.3; after `dev-install` the correct `.pixi/envs/default/bin` binary was used |
| ProjectHephaestus | `.pixi` cache poisoning under `locked: true` — PR #1021 fixed setup-pixi-env composite + release.yml + pre-commit.yml; PR #1026 fixed security.yml (exact-key-only cache) | verified-ci: dependency-scan green on rebased PRs after the fix (e.g. PR #1011 passed) |
| ProjectOdyssey | Consolidate 14+ Pixi setup blocks into a composite action (issue #3155 / PR #4464) | Eliminated `Saved cache with ID -1`; explicit `actions/cache` over `.pixi` + `~/.cache/rattler/cache` keyed on `pixi.lock` |
| ProjectNestor | nats.c static link failed with GLIBC_PRIVATE errors | Fixed by adding `openssl >= 3` to `pixi.toml` + cleaning the build dir |
| ProjectAgamemnon | Same nats.c + OpenSSL pattern | Same fix applied preventatively |

## References

- [Pixi `[pypi-dependencies]` docs](https://pixi.sh/latest/reference/project_configuration/#the-pypi-dependencies-table)
- [pip editable install reference](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs)
- [prefix-dev/setup-pixi](https://github.com/prefix-dev/setup-pixi)
