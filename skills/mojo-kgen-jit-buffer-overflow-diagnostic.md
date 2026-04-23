---
name: mojo-kgen-jit-buffer-overflow-diagnostic
description: "Use when: (1) CI test group crashes with Aborted (core dumped) at libKGENCompilerRTShared.so+0x6d4ab (__fortify_fail_abort) BEFORE any test output, (2) the crash is 100% deterministic on every CI run (same crash address), (3) the crashing file combines std.python import + List[String] struct field + 6+ overloaded constructors + Dict[String, <that struct>], (4) ulimit and max-parallel changes have no effect, (5) you need to write a minimal reproducer to file upstream against modular/modular. Distinct from the UID-mismatch fortify_fail crash (Crash 2 in mojo-jit-crash-retry skill) and from JIT volume overflow (Crash 3)."
category: debugging
date: 2026-04-22
version: "1.0.0"
user-invocable: false
verification: verified-precommit
tags:
  - mojo
  - kgen
  - jit
  - buffer-overflow
  - fortify
  - libKGENCompilerRTShared
  - upstream
  - crash
  - python-interop
  - deterministic
---

# Mojo KGEN JIT Buffer Overflow Diagnostic

> **Warning — verified-precommit**: Reproducer committed and upstream issue filed
> (modular/modular#6445). CI fix confirmation pending Modular response. Treat workflow
> steps as **Proposed** until confirmed fixed in a Mojo release.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-22 |
| **Objective** | Identify and reproduce a KGEN internal buffer overflow that causes a deterministic `Aborted (core dumped)` crash before any test output, distinguish it from other `__fortify_fail_abort` crash patterns, and file an upstream issue. |
| **Outcome** | Upstream issue filed (modular/modular#6445). Workaround: requires removing the triggering code pattern. No fix yet from Modular. |
| **Verification** | verified-precommit — repro file committed, upstream issue filed, CI not yet confirmed fixed |
| **Source** | ProjectOdyssey CI failures; branch `fix-ci-hephaestus-install` |

## When to Use

- CI produces `Aborted (core dumped)` with `libKGENCompilerRTShared.so+0x6d4ab (__fortify_fail_abort)`
  **before any test output appears** — not after
- The crash happens on **every single CI run** (100% deterministic), not intermittently
- The crash address is the **same offset every run** (not ASLR-variable like JIT volume overflow)
- `ulimit -v unlimited` has no effect (rules out virtual memory limit)
- `max-parallel: 1` does not prevent the crash in a single file
- The crashing file or module uses **all four** of these together:
  1. `from std.python import Python, PythonObject` at module level
  2. A struct with a `List[String]` field
  3. Six or more overloaded `__init__` constructors on that struct
  4. `Dict[String, <that struct>]` usage

## How to Distinguish From Other `__fortify_fail_abort` Patterns

There are three different crashes that all appear as `__fortify_fail_abort` in `libKGENCompilerRTShared.so`.
Getting the crash type wrong wastes investigation time.

| Indicator | KGEN Buffer Overflow (this skill) | Crash 2: UID Mismatch | Crash 3: JIT Volume |
|-----------|-----------------------------------|-----------------------|---------------------|
| Crash address | Fixed: `+0x6d4ab` every run | Fixed: `+0x6d4ab` or `+0x6a686` | Variable (ASLR) |
| Determinism | 100% — fails every run | Deterministic given same UID | Non-deterministic |
| Trigger | Specific code pattern (see trigger combination) | Cold pixi volume + UID mismatch + no TTY | >20 functions OR package-level imports |
| `ulimit -v unlimited` | No effect | No effect | No effect |
| `max-parallel: 1` | No effect | May reduce (concurrent UID contention) | Reduces (but doesn't fix) |
| Reproducer | Standalone `.mojo`, zero project imports | Any Mojo program hitting HOME write | Large test file |
| Fix | Remove trigger pattern / await Modular fix | Fix UID in Docker cache key + entrypoint HOME-fixup | Targeted submodule imports |

See `mojo-jit-crash-retry` skill (Crash 2, Crash 3) for the other two patterns.

## The Trigger Combination

All four conditions must be present **in the same compilation unit**:

1. **CPython interop**: `from std.python import Python, PythonObject` at module level
2. **`List[String]` field**: A struct that has `var <name>: List[String]`
3. **6+ overloaded `__init__`**: The same struct has six or more `def __init__(out self, ...)` with
   different parameter types
4. **`Dict[String, <that struct>]`**: The struct is used as a `Dict` value type

Removing **any one** of the four stops the crash. The buffer overflow appears to occur in KGEN's
type-specialization codegen when CPython interop metadata intersects with a complex overload set
on a struct containing heap-allocated fields.

## Verified Workflow

> **Warning — Proposed Steps**: Steps below are based on repro + upstream filing
> (verified-precommit only). CI fix is not yet confirmed. Treat each step as proposed
> until modular/modular#6445 is resolved and tested in CI.

### Quick Reference

```bash
# Step 1: Confirm 100% determinism (run 3 times)
for i in 1 2 3; do
  echo "=== Run $i ==="; pixi run mojo run <crashing_file>.mojo; echo "exit: $?"
done
# If crash address varies across runs → NOT this pattern (use mojo-jit-crash-retry instead)

# Step 2: Check for the trigger combination in the crashing file
grep -n "from std.python import\|List\[String\]\|Dict\[String" <file>.mojo
grep -c "def __init__(out self" <file>.mojo   # Should be >= 6

# Step 3: Write minimal reproducer (stdlib-only, no project imports)
cat > /tmp/repro_kgen_overflow.mojo << 'MOJO'
# Reproducer for KGEN JIT buffer overflow
# Mojo 0.26.3, Ubuntu (GitHub Actions runner)
# Filed: modular/modular#6445
from std.python import Python, PythonObject
struct Value(Copyable, Movable):
    var list_val: List[String]
    def __init__(out self, v: Int): self.list_val = List[String]()
    def __init__(out self, v: Float64): self.list_val = List[String]()
    def __init__(out self, v: String): self.list_val = List[String]()
    def __init__(out self, v: Bool): self.list_val = List[String]()
    def __init__(out self, var v: List[String]): self.list_val = v^
    def __init__(out self, v: List[Int]): self.list_val = List[String]()
struct Container(Copyable, Movable):
    var data: Dict[String, Value]
    def __init__(out self): self.data = Dict[String, Value]()
def main() raises:
    print("If you see this, the KGEN crash did NOT occur.")
    var c = Container()
    print("Success")
MOJO
pixi run mojo run /tmp/repro_kgen_overflow.mojo

# Step 4: File upstream at https://github.com/modular/modular/issues/new
# Use the template in Results & Parameters section below

# Step 5: Workaround — remove the std.python import from the crashing file
# (requires restructuring code to not need Python interop in that compilation unit)
```

### Step 1: Confirm Determinism

Run the failing CI test file 3 times locally (if GLIBC 2.32+ available) or via CI reruns.

**Key diagnostic**: If `print("If you see this...")` at the start of `main()` does NOT appear
before the crash, the crash is at JIT compilation time (before `main()` executes). This is
the signature of KGEN internal buffer overflow — not a runtime error.

```bash
# Capture crash address
pixi run mojo run <file>.mojo 2>&1 | grep -E "fortify|Aborted|0x[0-9a-f]+"
```

If crash address is the same offset every run → high confidence KGEN buffer overflow (this pattern).
If crash address varies → JIT volume overflow (Crash 3 in `mojo-jit-crash-retry`).

### Step 2: Identify the Trigger Combination

```bash
# Check for all four trigger conditions
FILE=<your_file>.mojo

echo "=== Condition 1: Python import ==="
grep -n "from std.python import" "$FILE"

echo "=== Condition 2: List[String] field ==="
grep -n "List\[String\]" "$FILE"

echo "=== Condition 3: Overloaded __init__ count ==="
grep -c "def __init__(out self" "$FILE"   # needs to be >= 6

echo "=== Condition 4: Dict with struct ==="
grep -n "Dict\[String," "$FILE"
```

If all four are present → confirmed KGEN buffer overflow trigger combination.

### Step 3: Write Minimal Reproducer

The reproducer must be **stdlib-only** (no project-internal imports) to be usable for an
upstream issue against modular/modular.

Strategy: Start with the full struct. Then try removing components one at a time:

1. Remove `from std.python import` → if crash stops: confirmed CPython interop is required trigger
2. Restore Python import; reduce `__init__` overloads from 6 → 5 → 4 → find minimum that crashes
3. Remove `List[String]` field → if crash stops: confirmed heap field is required
4. Replace `Dict[String, Value]` with direct `Value` usage → if crash stops: confirmed Dict is required

```mojo
# Minimal reproducer template
# Mojo version: X.Y.Z  OS: Ubuntu  CI-only (does not reproduce locally on developer machines)
# Filed: modular/modular#NNNN
from std.python import Python, PythonObject

struct Value(Copyable, Movable):
    var list_val: List[String]
    # Include minimum number of __init__ overloads that trigger crash
    def __init__(out self, v: Int): self.list_val = List[String]()
    def __init__(out self, v: Float64): self.list_val = List[String]()
    def __init__(out self, v: String): self.list_val = List[String]()
    def __init__(out self, v: Bool): self.list_val = List[String]()
    def __init__(out self, var v: List[String]): self.list_val = v^
    def __init__(out self, v: List[Int]): self.list_val = List[String]()

struct Container(Copyable, Movable):
    var data: Dict[String, Value]
    def __init__(out self): self.data = Dict[String, Value]()

def main() raises:
    print("If you see this, the KGEN crash did NOT occur.")
    var c = Container()
    print("Success")
```

**Key diagnostic line**: If `"If you see this..."` never prints before the crash, the crash
fires at JIT compilation time (before `main()` runs). Include this observation in the upstream report.

### Step 4: File Upstream Issue (modular/modular)

Only file after the reproducer crashes 3/3 runs. Use this template structure:

```markdown
## Environment

- Mojo version: X.Y.Z (from `pixi.toml`: `mojo = "==X.Y.Z"`)
- OS: GitHub Actions ubuntu-latest (~7 GB RAM, 2-core runner)
- Hardware: CPU-only
- Reproduced locally: NO (CI-only; developer machines with more RAM do not crash)

## Description

Compilation of a module crashes with __fortify_fail_abort in
libKGENCompilerRTShared.so before main() executes. The crash fires
at JIT compilation time, not at runtime. The trigger is a specific
combination of four code patterns in one compilation unit:
(1) from std.python import Python at module level,
(2) a struct with a List[String] field,
(3) 6+ overloaded __init__ constructors on that struct,
(4) Dict[String, <that struct>] usage.

## Crash Signature

#0  libKGENCompilerRTShared.so+0x6d4ab  (__fortify_fail_abort)
[paste full crash trace]

## Minimal Reproducer

[Paste full content of the minimal reproducer file]

## Steps to Reproduce

1. Save above as `repro.mojo`
2. Run: `mojo repro.mojo` on a GitHub Actions runner (CI environment)
3. Observe: `Aborted (core dumped)` before "If you see this..." prints

## Expected Behavior

Program runs and prints "Success"

## Actual Behavior

Process aborts with __fortify_fail_abort in libKGENCompilerRTShared.so
before main() begins executing. The crash address is deterministic
(same offset every run), indicating a KGEN internal buffer overflow
(not ASLR-variable JIT volume overflow).

## Relationship to Known Issues

Related to the fortify_fail HOME permission crash (Crash 2 in our
internal docs) but with a different root cause — not a HOME write
permission issue. Removing any one of the four trigger conditions
eliminates the crash.
```

### Step 5: Workaround

No workaround is available without removing the `std.python` import (which would break
any functionality requiring Python interop, such as YAML loading).

Temporary options pending Modular fix:

1. **Move Python interop to a separate compilation unit** — keep the overloaded struct in its
   own `.mojo` file that does NOT import `std.python`; have a thin Python-facing wrapper that
   only imports Python and delegates to the struct module. Avoids the combination in one unit.
2. **Reduce overload count** — if the crash requires ≥6 overloads, reducing to 5 may stop it
   (needs bisection). Trade-off: less convenient API.
3. **Replace `List[String]` field with `String`** — if the `List[String]` field is required,
   consider encoding as a single delimited string. Ugly but avoids the crash.
4. **Accept CI-only failure and track upstream issue** — if the pattern cannot be restructured,
   mark the CI job as advisory and link to the upstream issue.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `ulimit -v unlimited` | Set virtual memory limit to unlimited in CI runner | No effect — KGEN internal buffer is not a virtual memory allocation | `ulimit` only affects process virtual address space limits, not KGEN's fixed-size internal codegen buffers |
| `max-parallel: 1` in GitHub Actions | Set `max-parallel: 1` to reduce concurrent compilation load | Reduces concurrent load but a single-file overflow still crashes the single job | The overflow is triggered by one file's complexity, not aggregate CI parallelism |
| Treat as random JIT noise and rerun | Assumed non-deterministic; re-triggered CI | Crash occurred 100% of the time, confirming it is NOT random flake | 100% determinism is the distinguishing signal — stop retrying and start bisecting |
| Diagnose as UID mismatch (Crash 2) | Checked Docker image UID, entrypoint HOME-fixup | UID fix was already applied; same crash address `+0x6d4ab` had been seen for Crash 2 as well | Same crash address can come from different root causes; check the trigger combination, not just the address |
| Diagnose as JIT volume overflow (Crash 3) | Audited imports, tried targeted submodule imports | Import audit found no package-level broad imports; crash persisted after conversion | Volume overflow crashes have ASLR-variable addresses; fixed address means different root cause |
| Remove Dict usage | Tried removing `Dict[String, Value]` from the struct | Bisection showed Dict alone was not sufficient; the combination of all four was required | Bisect one variable at a time; don't jump to conclusions after removing one component |

## Results & Parameters

### Trigger Combination — Required All Four

| Component | Trigger | Safe Alternative |
|-----------|---------|-----------------|
| `from std.python import Python, PythonObject` | Module-level CPython interop | Move to separate compilation unit |
| `var <name>: List[String]` in struct | Heap-allocated string list field | Single delimited `String` field |
| 6+ `def __init__(out self, ...)` overloads | Large overload set on struct | Reduce overload count to <6 |
| `Dict[String, <struct>]` | Dict with the struct as value | Use `List[Tuple[String, <struct>]]` instead |

### Crash Identification Commands

```bash
# Confirm determinism (all 3 must crash at same offset)
for i in 1 2 3; do
  pixi run mojo run <file>.mojo 2>&1 | grep -oE "0x[0-9a-f]+" | head -3
done

# Check trigger combination in one command
FILE=<your>.mojo
echo "Python: $(grep -c 'from std.python import' $FILE)"
echo "List[String]: $(grep -c 'List\[String\]' $FILE)"
echo "init overloads: $(grep -c 'def __init__(out self' $FILE)"
echo "Dict[String: $(grep -c 'Dict\[String,' $FILE)"
# Should show: Python:1, List[String]:1+, init overloads:6+, Dict[String:1+
```

### Upstream Issue Filed

- **Issue**: modular/modular#6445
- **Filed**: 2026-04-22
- **Status**: Open, awaiting Modular triage

### Environment Where Crash Reproduces

| Environment | Reproduces? | Notes |
|-------------|------------|-------|
| GitHub Actions `ubuntu-latest` | YES, 100% | ~7 GB RAM, 2-core runner |
| Developer machine (high RAM) | NO | Larger KGEN buffers on machine with more RAM (suspected) |

## Verified On

| Project | Context | Outcome |
|---------|---------|---------|
| ProjectOdyssey | Branch `fix-ci-hephaestus-install`; CI crash on YAML-loading module | Upstream issue filed modular/modular#6445; workaround pending |

## References

- [modular/modular#6445](https://github.com/modular/modular/issues/6445) — upstream issue filed
- [mojo-jit-crash-retry](mojo-jit-crash-retry.md) — other `__fortify_fail_abort` patterns (Crash 2: UID mismatch, Crash 3: JIT volume)
- [mojo-upstream-bug-filing-reproducibility-standard](mojo-upstream-bug-filing-reproducibility-standard.md) — reproducibility gate for upstream filing
- [docker-mojo-uid-mismatch-crash-fix](docker-mojo-uid-mismatch-crash-fix.md) — fix for Crash 2 (UID mismatch)
