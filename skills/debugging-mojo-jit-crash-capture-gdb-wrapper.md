---
name: debugging-mojo-jit-crash-capture-gdb-wrapper
description: "Use when: (1) Mojo 1.0 runtime crashes (modular/modular#6413 family) but kernel `core_pattern` + `ulimit -c unlimited` produce no core because `libKGENCompilerRTShared.so` installs an in-process SIGABRT/SIGILL handler that swallows the signal before the kernel can dump, (2) you need real ELF cores from the JIT-emitted fault site (not Crashpad's 3-frame published trace), (3) you've already tried kernel `core_pattern` and confirmed empty cores directory, (4) you need a wrapper that runs `mojo` under `gdb` from inside `pixi run` so `MODULAR_HOME`/stdlib paths remain activated, (5) you're on gdb 15.1 where `hook-stop` and `--return-child-result` misbehave in `-batch` mode, (6) you want to handle SIGILL (Mojo's `os.abort()` lowers to `llvm.trap` → SIGILL on Linux, not SIGABRT) in addition to SIGSEGV/SIGABRT/SIGBUS/SIGFPE, and (7) the wrapper must exit `128 + signo` on crash and the inferior's real exit code on clean exit."
category: debugging
date: 2026-05-10
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - mojo
  - jit
  - crash
  - gdb
  - coredump
  - libKGEN
  - SIGILL
  - signal-handler
  - pixi
  - modular-6413
---

# Capture Mojo JIT Crash Cores via a `gdb` Wrapper that Defeats libKGEN's In-Process Signal Handler

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-05-10 |
| **Objective** | Capture real ELF coredumps from Mojo 1.0 JIT runtime crashes (modular/modular#6413 family) when bare `ulimit -c unlimited` + kernel `core_pattern` produce nothing. Root cause: `libKGENCompilerRTShared.so` registers its own in-process SIGABRT/SIGILL handler that beats the kernel to the signal — the process handles the crash itself so the kernel never dumps. The fix is to run `mojo` under `gdb` (which intercepts signals **before** the user-space handler) and use Python events to drive `generate-core-file`. |
| **Outcome** | A reusable wrapper `scripts/mojo-under-gdb.sh` in ProjectOdyssey. CI run `25649843238` (Mojo `1.0.0b2.dev2026050805`) captured 7 real ELF cores using this wrapper across two jobs. |
| **Verification** | verified-ci |
| **Companion skill** | `gha-mojo-coredump-capture` — the GHA host-side infrastructure (core_pattern, systemd-coredump stop, artifact bundling). **This** skill is the missing piece: the wrapper that actually produces the core when libKGEN is in the picture. |

## When to Use

- You have the GHA host config from `gha-mojo-coredump-capture` set up (kernel
  `core_pattern` points to a workspace path, systemd-coredump stopped,
  `ulimit -c unlimited` set in the container), but the cores directory is **still
  empty** after a crash
- You see Crashpad/`libKGENCompilerRTShared.so` frames in the published trace,
  confirming an in-process signal handler is running before the kernel can dump
- You are reproducing locally inside the dev container and `kill -ABRT $$` from a
  bare shell writes a core, but `mojo run <crashing-test>` writes nothing — proving
  the issue is mojo-specific signal interception, not the kernel config
- You need cores from Mojo `os.abort()` calls (which lower to `llvm.trap` → SIGILL
  on Linux), where a SIGABRT-only handler would miss them
- You're on `gdb` 15.1 (Ubuntu 24.04 default) and previous attempts with
  `hook-stop` errored with "You can't do that without a process to debug." on
  clean-exit tests

## Verified Workflow

### Architecture

```text
Without wrapper                         With wrapper
───────────────────────────────         ─────────────────────────────────────
mojo run test.mojo                      pixi run -- gdb -batch \
  → libKGEN installs SIGILL handler        --eval-command "py-events install" \
  → JIT crash → SIGILL                     --eval-command "run …" mojo
  → user-space handler runs first         → gdb intercepts SIGILL FIRST (ptrace)
  → handler prints Crashpad trace         → Python SignalEvent fires
  → calls _exit() — no kernel dump        → generate-core-file core.<pid>
  → kernel core_pattern never invoked     → write 128+signo to exit-code file
  → cores/ stays empty                    → kernel core_pattern path filled
```

The wrapper has to satisfy five non-obvious constraints simultaneously; missing any
one of them silently degrades to "no core" or "broken exit codes". See
**Failed Attempts** for the discovery sequence.

### Quick Reference

```bash
# Inside the dev container (or any host with gdb installed):
ulimit -c unlimited
bash scripts/mojo-under-gdb.sh /tmp/cores \
  --Werror -debug-level=line-tables -I /workspace -I . path/to/test.mojo

# Wrapper exit codes:
#   0 / N         → inferior exited cleanly with that code
#   128 + signo   → inferior died on a signal (e.g. 132 = SIGILL, 134 = SIGABRT,
#                   139 = SIGSEGV)
# On signal, /tmp/cores/core.<pid> is a real ELF dump usable with:
#   gdb -ex "core-file /tmp/cores/core.<pid>" $(pixi run which mojo)
```

### The five constraints (each is load-bearing)

1. **Run gdb under `pixi run`, not bare gdb.** `pixi run -- gdb …` is required so
   the inferior inherits `MODULAR_HOME`, `PATH`, and the stdlib search paths from
   the pixi env. Bare `gdb $(which mojo) …` strips that activation and mojo dies
   with `error: unable to locate module 'std'` **before it can crash** — the
   wrapper appears broken when really it just can't reach the bug.
2. **Resolve `mojo` via `pixi run which mojo`** (not host `which mojo`). The mojo
   binary lives inside the pixi env; the host PATH usually doesn't have it.
3. **Use gdb Python events, NOT `hook-stop`.** In gdb 15.1, `hook-stop` fires on
   **every** stop — including the synthetic "Inferior exited normally" stop after
   a clean exit. `generate-core-file` inside `hook-stop` then errors:
   `You can't do that without a process to debug.` Subscribe to
   `gdb.events.stop` and filter to `isinstance(event, gdb.SignalEvent)`; the
   exit-stop is an `ExitedEvent` and harmlessly ignored.
4. **Write the exit code to a file, not via `--return-child-result`.** In gdb
   15.1 `-batch` mode, `--return-child-result` returns `0` even when the inferior
   died on a handled signal. Pattern: on `SignalEvent` write `128 + event.stop_signal_number`
   (after mapping name → number) and set `signaled = True`; on `ExitedEvent`
   write `event.exit_code` **unless** `signaled` is already true (the
   post-signal teardown also fires `ExitedEvent` with code 0 and would overwrite).
5. **Wrap the gdb invocation in `set +e` / `set -e`.** gdb itself exits non-zero
   when the inferior dies on a signal; without bracketing, the wrapper aborts
   under `set -e` before it can read the exit-code file.

### Handle all five fatal signals (not just SIGABRT)

```text
SIGABRT  (6)  — explicit abort() calls, glibc assertion failures
SIGSEGV (11)  — null deref, OOB, use-after-free
SIGBUS   (7)  — misaligned access, mmap fault
SIGILL   (4)  — Mojo `os.abort()` lowers to `llvm.trap` → SIGILL on Linux,
                NOT SIGABRT. Observed JIT crashes in modular#6413 also
                surface as SIGILL.
SIGFPE   (8)  — integer divide by zero
```

Wrappers that watch only SIGABRT will miss every Mojo `os.abort()` crash and most
JIT faults.

### Wrapper skeleton

```bash
#!/usr/bin/env bash
# scripts/mojo-under-gdb.sh <cores-dir> <mojo args...>
set -euo pipefail

CORES_DIR="${1:?usage: $0 <cores-dir> <mojo args...>}"
shift
mkdir -p "$CORES_DIR"

MOJO_BIN="$(pixi run -- bash -c 'command -v mojo')"
EXIT_FILE="$(mktemp)"
trap 'rm -f "$EXIT_FILE"' EXIT

# Python script driving gdb events — filter to SignalEvent only.
GDB_PY=$(cat <<PYEOF
import gdb, os
signaled = False
NAME_TO_NUM = {"SIGHUP":1,"SIGINT":2,"SIGILL":4,"SIGABRT":6,"SIGBUS":7,
               "SIGFPE":8,"SIGKILL":9,"SIGSEGV":11,"SIGTERM":15}
def on_stop(ev):
    global signaled
    if isinstance(ev, gdb.SignalEvent):
        signo = NAME_TO_NUM.get(ev.stop_signal, 6)
        gdb.execute(f"generate-core-file {os.environ['CORES_DIR']}/core.{gdb.selected_inferior().pid}")
        with open(os.environ["EXIT_FILE"], "w") as f: f.write(str(128 + signo))
        signaled = True
def on_exit(ev):
    if not signaled:
        code = ev.exit_code if ev.exit_code is not None else 0
        with open(os.environ["EXIT_FILE"], "w") as f: f.write(str(code))
gdb.events.stop.connect(on_stop)
gdb.events.exited.connect(on_exit)
PYEOF
)

export CORES_DIR EXIT_FILE

set +e
pixi run -- gdb -batch -nx \
  -ex "python\n$GDB_PY" \
  -ex "set pagination off" \
  -ex "handle SIGILL SIGSEGV SIGABRT SIGBUS SIGFPE stop nopass" \
  -ex "run $*" \
  "$MOJO_BIN"
set -e

cat "$EXIT_FILE" 2>/dev/null | { read -r rc; exit "${rc:-1}"; }
```

The real wrapper at
[scripts/mojo-under-gdb.sh](https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/scripts/mojo-under-gdb.sh)
adds quoting safety, stderr tee, and core-name templating; the skeleton above is
the minimum that reproduces the behaviour.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| 1. Bare `ulimit -c unlimited` + kernel `core_pattern` | The standard recipe from `gha-mojo-coredump-capture` | `libKGENCompilerRTShared.so` installs an in-process SIGABRT/SIGILL handler at mojo startup. Its handler runs **before** the kernel's `core_pattern` rule fires (user-space signal handlers beat the kernel). The handler prints Crashpad's 3-frame trace and calls `_exit()` — the kernel never sees an uncaught signal, never writes a core. Cores directory stays empty. | Need a debugger that intercepts signals via `ptrace` **before** delivery to the inferior's handlers — gdb does this naturally. |
| 2. `gdb $(which mojo) …` outside `pixi run` | Bare gdb invocation, expecting `mojo` to behave the same as in the pixi shell | Mojo can't find `std`: `error: unable to locate module 'std'`. Without `pixi run` activation, `MODULAR_HOME` and stdlib search paths are unset, so mojo errors out at compile time before it can crash. The wrapper looked broken; the bug was upstream of the bug. | Always launch gdb **through** `pixi run -- gdb …` so the inferior inherits the activated env. The same applies to any tool that depends on conda/pixi env vars. |
| 3. `hook-stop` + `if $_siginfo` to detect signals | Standard gdb idiom for "do X only on signal stop" | `if $_siginfo` errors with `No stack.` on a clean exit (no siginfo struct exists), and the error propagates as gdb's batch exit code. Previously-passing tests now exit non-zero from the wrapper. | `$_siginfo` is unreliable in `-batch` mode; use Python events that explicitly type-check `gdb.SignalEvent` instead. |
| 4. `hook-stop` + unconditional `generate-core-file` | Skip the `$_siginfo` check, just dump on every stop | In gdb 15.1, `hook-stop` fires on the synthetic "Inferior exited normally" stop emitted after a clean exit. `generate-core-file` then errors `You can't do that without a process to debug.` because the inferior is gone. The error fails the wrapper on every successful test run. | `hook-stop` is too coarse in modern gdb; use Python `gdb.events.stop` and filter to `SignalEvent` to ignore exit-stops. |
| 5. `--return-child-result` for exit propagation | Documented gdb flag that propagates inferior's exit code | In gdb 15.1 `-batch` mode, `--return-child-result` often returns `0` even when the inferior died on a handled signal. Wrapper would report success on crashes. | Drive the exit code from the Python event handlers via a file: write `128 + signo` on `SignalEvent`, write `event.exit_code` on `ExitedEvent` **only if not already signaled** (post-signal teardown also fires `ExitedEvent` with code 0 and would clobber the real signal exit code). |
| 6. Wrap only SIGABRT and SIGSEGV | Initial signal handler list | Missed every Mojo `os.abort()` crash because Mojo's `os.abort()` lowers to `llvm.trap` which raises **SIGILL** on Linux, not SIGABRT. Observed modular#6413 crashes also surface as SIGILL. | Always include SIGILL in the handled-signal set for any tool that runs Mojo, plus SIGBUS and SIGFPE for completeness. |

## Results & Parameters

### Local validation (Podman dev container, `/usr/bin/gdb` 15.1)

| Test case | Wrapper exit | Core file |
| --- | --- | --- |
| `kill -ABRT $$` in bash inferior | 134 (128+6) | 2.1 MB |
| `kill -SEGV $$` in bash inferior | 139 (128+11) | 2.1 MB |
| Clean `exit 0` | 0 | none |
| Clean `exit 7` | 7 | none |
| Mojo `os.abort()` test | 132 (SIGILL) | 2.8 GB; `info shared` shows `libKGENCompilerRTShared.so` |
| Mojo `print("ok")` clean exit | 0 | none |

### CI evidence — ProjectOdyssey run `25649843238`

Mojo `1.0.0b2.dev2026050805`, Ubuntu 24.04, gdb 15.1. Captured 7 real ELF cores
that the bare-`ulimit` approach would have missed:

| Job | Cores | Crash site |
| --- | --- | --- |
| Configs | 6 (842 MB each) | 4 in `KGEN_CompilerRT_GetOrCreateGlobalIndexed` → `python.import_module`; 2 in `dict.mojo:1460::_insert` |
| Data Utilities | 1 (662 MB) | `assert_almost_equal` at `shared/testing/assertions.mojo:170` |

### Where to install in a repo

| File | Purpose |
| --- | --- |
| `scripts/mojo-under-gdb.sh` | The wrapper itself; check in with `+x` |
| `justfile` (or test recipe) | Swap `pixi run mojo run …` for `bash scripts/mojo-under-gdb.sh "$CORES_DIR" …` |
| `docs/dev/mojo-jit-crash-capture-core.md` | The 5-constraint explainer for human readers (link from CONTRIBUTING) |
| `.github/workflows/<test>.yml` | Already covered by `gha-mojo-coredump-capture` (host config + bundling); **this** wrapper goes between those two |

### Companion skills (read together)

- `gha-mojo-coredump-capture` — host-side core_pattern, systemd-coredump stop,
  artifact bundling. **This skill is the missing middle layer** between that
  GHA infra and the actual mojo invocation.
- `mojo-jit-crash-retry` — the dynsym/objdump procedure for analysing the
  captured core
- `mojo-binary-closed-source-debugging` — why the captured core's libKGEN
  frames don't resolve to source lines

### Reference links

- Real wrapper: <https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/scripts/mojo-under-gdb.sh>
- Full design doc: <https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/docs/dev/mojo-jit-crash-capture-core.md>
- Upstream Mojo issue: <https://github.com/modular/modular/issues/6413>

### What this DOES NOT do

- Does not symbolicate JIT-emitted code inside `libKGEN*` (no DWARF — see
  `mojo-binary-closed-source-debugging`); it captures the core so Modular can
  open it on their side.
- Does not work for `SIGKILL` (uncatchable by design — process is killed by
  the kernel without notification).
- Does not replace `gha-mojo-coredump-capture` — you still need the host config
  to write cores anywhere usable, and the bundling step to ship them out of CI.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | CI run `25649843238`, Mojo `1.0.0b2.dev2026050805` | 7 real ELF cores captured (6 Configs job, 1 Data Utilities job); previously these crashes produced zero cores with the bare `ulimit` recipe. Wrapper handles SIGABRT/SIGSEGV/SIGBUS/SIGILL/SIGFPE; uses Python `gdb.events` (not `hook-stop`); resolves mojo via `pixi run which mojo`; runs gdb under `pixi run` to inherit `MODULAR_HOME` and stdlib paths. |
