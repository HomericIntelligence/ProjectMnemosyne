---
name: mojo-build-compilation-and-linker-error-patterns
description: "Use when: (1) adding --Werror to a Mojo build system and auditing all files for hidden warnings, (2) CI fails with Mojo import errors after module renames, mojo-format pre-commit hook line-length failures, or stable vs nightly version mismatch, (3) mojo build fails with 'undefined reference to fmaxf/sincos/libm' symbols from AOT compilation of example or benchmark files, (4) enabling ASAN/TSAN for Mojo CI and diagnosing tcmalloc/sanitizer incompatibility or AVX-512 codegen asymmetry, (5) resolving git rebase conflicts in Mojo test files by converting invalid Python syntax to valid Mojo Bool flag patterns, (6) fixing out-of-bounds List access from DynamicVector→List migration where index assignment was not converted to append."
category: ci-cd
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: mojo-build-compilation-and-linker-error-patterns.history
tags: [mojo, build, compilation, linker, werror, mojo-format, sanitizer, asan, tsan, avx512, libm, rebase, dynamicvector, ci-cd]
---

# Mojo Build, Compilation, and Linker Error Patterns

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | One canonical reference for Mojo build-system, compilation, and linker error patterns: `--Werror` audits, import/format/version errors, AOT linker (libm) exclusions, sanitizer build-flag matrices, rebase syntax conflicts, and DynamicVector→List OOB crashes |
| **Outcome** | Merged from 6 skills covering the full compile/link/build-flag surface; specific cases preserved as concrete examples below |
| **Verification** | verified-ci |

## When to Use

1. Adding `--Werror` to a justfile / CI build system and auditing hundreds of Mojo files for hidden warnings, or running a periodic warning sweep after a version upgrade.
2. CI fails with Mojo import errors after module renames (`activation_ops`→`activation`), `mojo-format` pre-commit hook fails on lines exceeding 88 chars, stable vs nightly version mismatch breaks compilation, or `mypy` rejects `X | Y` union syntax.
3. `mojo build` fails with `undefined reference to fmaxf/sincos@@GLIBC` / `libm.so.6: DSO missing` from AOT compilation of `examples/` or `benchmarks/` files that should run via `mojo run` (JIT).
4. Enabling ASAN/TSAN for Mojo CI and diagnosing which sanitizers the compiler accepts, tcmalloc/sanitizer shadow-memory aborts, OOM during sanitizer sweeps, or AVX-512 driver-vs-sanitizer codegen asymmetry.
5. Resolving git rebase conflicts in `.mojo` test files where the incoming commit introduced invalid Python syntax (dicts, sets, `in`, f-strings) that must become valid Mojo Bool-flag patterns.
6. Fixing out-of-bounds `List` access from a `DynamicVector`→`List` migration where index assignment (`vec[i] = val`) was not converted to `append`.

## Verified Workflow

### Quick Reference

```bash
# --Werror single-file compile (test runner vs binary)
timeout 60 pixi run mojo --Werror -I "$(pwd)" -I . "$FILE" 2>&1 | grep -E "error:|warning:"
timeout 60 pixi run mojo build --Werror -I "$(pwd)" -I . "$FILE" -o /tmp/audit_out 2>&1

# Get exact CI diff for mojo-format failures
gh run view <run-id> --log-failed 2>&1 | grep -A 100 "All changes made by hooks:"

# GLIBC workaround: skip mojo-format on old hosts, CI enforces it
SKIP=mojo-format git commit -m "message"

# Sanitizer support (Mojo 1.0.0b2): ASAN works; TSAN/MSAN/UBSAN do not
pixi run mojo build --sanitize=address -g -I "$(pwd)" -I . -o /tmp/repro <file.mojo>
ASAN_OPTIONS=halt_on_error=0:abort_on_error=0:detect_leaks=1:symbolize=1 /tmp/repro

# Find List() + index-assignment OOB candidates
grep -B2 -A2 'List\[Int\]()' **/*.mojo | grep -A2 '\[0\] ='

# Find conflict markers in a rebased .mojo file
grep -n "<<<<<<<\|=======\|>>>>>>>" tests/shared/test_serialization.mojo
```

### Detailed Steps

#### 1. `--Werror` Compilation Audit (parallel sweep + triage)

For large codebases (400+ files), split into ~6 parallel Haiku agents (~80 files each, divided by
directory). Each agent greps for `^fn main` first (SKIP library files), then runs the `--Werror`
compile and emits a `FILE/STATUS/MESSAGE` block. Use `mojo --Werror` for test files (they use
`raises`/assertions), `mojo build --Werror` only for examples/scripts with `main()`. Use 90s
timeouts for model e2e tests, 60s for unit/shared.

Triage warnings into **simple** (fix immediately) vs **complex** (file an issue):

| Pattern | Fix |
| --------- | ----- |
| `assignment to 'x' was never used` | `_ = expr` or remove |
| `for i in range(...)` with `i` unused | `for _ in range(...)` |
| docstring missing trailing `.` / lowercase start | add period / capitalize (bulk via Python `re.sub(r'(?<=\"\"\")([a-z])', ...)`) |
| `'alias' is deprecated, use 'comptime'` | replace `alias` with `comptime` (top-level only) |
| `transfer from an owned value has no effect` | remove `^` from return |
| `'TypeName' value is unused` | `_ = expr` |
| `except e:` with `e` unused | bare `except:` (NOT `except _:` — unsupported) |
| `if statement with constant condition` (`if True:`) | unwrap block; release scope with explicit `_ = view^` |
| `undefined reference to 'fmaxf@@GLIBC'` | known linker-libm issue — skip; see step 3 |
| type mismatch / missing arg / non-copyable fieldwise init | file a GitHub issue (`--label implementation`) |

Always skip `*.templates/*.mojo` (Jinja `{{}}`), `**/__init__.mojo`, library files without `main()`,
and previously-filed known-broken files. Commit in logical batches by fix type; verify with the
justfile recipe (`just test-mojo`) which uses `--Werror` internally.

#### 2. CI Import / Format / Version Errors

- **Import not found after rename**: check leaf-module path in `shared/` `__init__.mojo` re-exports (`activation_ops`→`activation`, `batch_norm`→`normalization`). Test files lag refactors.
- **mypy `X | Y` unsupported**: bump `python_version` in `mypy.ini` to match runtime (e.g., `3.12`).
- **`assert_equal` won't compile for DType**: use `assert_true(dtype == DType.float32, "msg")`.
- **mojo-format line-length (88-char) failure** with mojo binary unavailable locally: get the exact CI diff (`gh run view <id> --log-failed | grep -A50 "All changes made by hooks"`) and apply it manually. The formatter splits long `print("...")` into implicit-concat strings with a leading space on each continuation, indented 4 extra spaces:

  ```mojo
  # After mojo format:
  print(
      "STATUS: Backward pass is a documented placeholder (full"
      " implementation tracked in GitHub issue #3181)"
  )
  ```

- **Nightly breaking changes**: `path[byte=i]` → `chr(Int(path.as_bytes()[i]))`; `value[byte=i]` write → `value.as_bytes()[i]`; `ptr.offset(n)` → `ptr + n`; `owned` param → `var`. The stable `mojo format` crashes (exit 123) on docstring+`comptime` files (modular/modular#6144) — treat exit 123 as a warning in the format wrapper.

#### 3. Linker / AOT Exclusions (libm)

Symptom: `undefined reference to symbol 'fmaxf@@GLIBC_2.2.5'` / `libm.so.6: DSO missing from
command line`. Root cause: Mojo v0.26.1 cannot pass `-lm`, and `find`-based build recipes try to
AOT-compile `examples/`/`benchmarks/` files that transitively import libm via `shared/`. Those files
are JIT entry points (`mojo run`), not AOT binaries.

Fix the justfile `build` recipe — add the exclusion and restore real error handling:

```diff
-    # CI mode should continue despite linker errors (Mojo limitation: cannot pass -lm flag)
-    FAIL_ON_ERROR=0
+    FAIL_ON_ERROR=1

     find . -name "*.mojo" \
         -not -path "./.pixi/*" \
         -not -path "./shared/*" \
+        -not -path "./examples/*" \
         -not -path "./benchmarks/*" \
```

Architectural rule: library code (`shared/`, `src/`) is AOT-compiled (`mojo build`); entry points
(`examples/`, `benchmarks/`) are JIT-executed (`mojo run`). Never silence with `FAIL_ON_ERROR=0` —
it hides future real failures.

#### 4. Sanitizer Flag Matrix (Mojo 1.0.0b2)

| Flag | Accepts? | Links? | Runs? | Notes |
| ---- | ----- | ---- | ---- | ----- |
| `--sanitize=address` | YES | YES | YES | Instruments user code only; NOT pre-built `libKGEN*`/`libAsync*`/`libMSupport*` |
| `--sanitize=thread` | YES | NO | — | `duplicate symbol: DW.ref.__gcc_personality_v0` (modular/modular#6512); needs `-j1` to compile |
| `--sanitize=memory` | NO | — | — | `invalid sanitizer 'memory'` |
| `--sanitize=undefined` | NO | — | — | `invalid sanitizer 'undefined'` |

Two-phase build scope (prevents OOM from 46 parallel AOT builds on ≤16 GiB hosts): Phase A always
packages the shared library; sanitizer modes **stop after Phase A** and defer per-binary
instrumentation to test time (one process at a time).

```just
asan)    FLAGS="-g1 --sanitize address $STRICT" ;;
tsan)    FLAGS="-g1 --sanitize thread  $STRICT" ; JOBS="-j1" ;;
# After packaging shared.mojopkg, sanitizer modes: echo + exit 0 (no per-binary AOT)
```

TSAN binaries abort at startup (`FATAL: ThreadSanitizer: unexpected memory mapping` from tcmalloc
shadow-memory overlap) — a Modular-side fix is required; `-j1` fixes the compile crash, not the
runtime abort. If user code is ASAN-clean but a `libKGEN` crash persists, the bug is in the Mojo
runtime — escalate upstream, stop editing user code.

**AVX-512 driver-vs-sanitizer asymmetry**: the modular/modular#6413 driver fix (xgetbv-gated
AVX-512 emission, Mojo 1.0.0b2.dev2026052306+) does NOT propagate through sanitizer codegen. Strip
`--target-features -avx512*` from non-sanitizer paths only; **retain it on ASAN/TSAN composites** or
sanitized tests SIGILL (`Illegal instruction (core dumped)` / `killed by signal 4`) on
AVX-512-masked runners.

```make
MOJO_TARGET_CPU := "--target-features -avx512bf16,-avx512bitalg,-avx512bw,-avx512cd,-avx512dq,-avx512f,-avx512ifma,-avx512vbmi,-avx512vbmi2,-avx512vl,-avx512vnni,-avx512vpopcntdq"
MOJO_ASAN := "--sanitize address " + MOJO_TARGET_CPU   # KEEP
MOJO_TSAN := "--sanitize thread "  + MOJO_TARGET_CPU   # KEEP
# Non-sanitizer flags MUST NOT concatenate MOJO_TARGET_CPU.
```

#### 5. Rebase Conflicts: Python Syntax → Valid Mojo

When an incoming rebase commit introduces Python-only constructs in a `.mojo` test, replace the
whole conflicted block (markers included) in one Edit, preserving intent with Bool flags + index
loops. Mojo has no `set`, `dict`, or `in` operator for collections.

```mojo
var found_weights = False
var found_bias = False
for i in range(len(loaded)):
    var name = loaded[i].name
    if name == "weights":
        found_weights = True
        assert_equal(loaded[i].tensor.numel(), 6, "Wrong size for weights")
    elif name == "bias":
        found_bias = True
        assert_equal(loaded[i].tensor.numel(), 3, "Wrong size for bias")
assert_true(found_weights, "Missing weights tensor")
assert_true(found_bias, "Missing bias tensor")
```

| Python (invalid in Mojo) | Mojo equivalent |
| -------------------------- | ----------------- |
| `expected = {"a": 1}` | `var found_a = False` (Bool flag) |
| `found = set()` | multiple `var found_x = False` flags |
| `for item in collection:` | `for i in range(len(collection)):` |
| `name in expected` | `name == "a" or name == "b"` |
| `raise AssertionError(f"...")` | `assert_true(cond, "message")` |

Then `git add <file>; GIT_EDITOR=true git rebase --continue` and verify with a targeted
`just test-group tests/shared "test_serialization.mojo"`.

#### 6. DynamicVector→List OOB Crashes

`DynamicVector[Int](N)` pre-allocates N index slots; `List[Int]()` is empty, so a migration that
kept `vec[i] = val` is an out-of-bounds write that "execution crashed". Convert index assignment to
`append`:

```mojo
# BEFORE (OOB on empty list):
var shape = List[Int]()
shape[0] = size
shape[1] = size
# AFTER:
var shape = List[Int]()
shape.append(size)
shape.append(size)
```

Find candidates with `grep -B2 -A2 'List\[Int\]()' **/*.mojo | grep -A2 '\[0\] ='`. Note: the correct
migration of `DynamicVector[Int](N)` is `List[Int]()` + N `append()` calls, NOT `List[Int](N)`
(different semantics in Mojo). Always investigate "execution crashed" as a source bug first.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Single sequential `--Werror` compile of all 498 files | One bash loop | >8 hours (30-60s/file) | Split into ~6 parallel Haiku agents of ~80 files each |
| `alias x = val` to silence unused var | Changed `var`→`alias` in function body | `alias` deprecated in fn bodies (0.26.1) | Use `_ = val` directly |
| `except e:` → `except _:` | Bind exception to `_` | Mojo has no `except _:` syntax | Use bare `except:` (no binding) |
| Run `pixi run mojo format` / `just pre-commit-all` locally | Auto-fix format on old host | GLIBC_2.32/33/34 not found (host glibc 2.31) | `SKIP=mojo-format` and let CI (GLIBC 2.35) enforce |
| Rely on CI to auto-fix mojo-format | Expect CI to commit back | CI fails, never commits back | Apply the CI diff manually when mojo unavailable |
| Pass `-lm` to `mojo build` | Add `-lm` linker flag | v0.26.1 rejects arbitrary linker flags | Compiler limitation; exclude JIT-only dirs instead |
| Silence linker errors with `FAIL_ON_ERROR=0` | Disable failure globally + in `ci` | Hides all future real linker failures | Exclude `examples/`/`benchmarks/` and keep `FAIL_ON_ERROR=1` |
| Full `--sanitize=address` AOT of all 46 examples/benchmarks | `just build asan` over every binary | 3-6 GB/binary; container OOM-killed after ~4 on 15 GiB host | Sanitize the shared package only; per-binary at test time |
| `-j1` to "fix" TSAN runtime abort | Added `JOBS="-j1"` | Fixed compile crash but every binary still aborts (tcmalloc shadow-memory) | `-j1` required for compile; runtime abort needs Modular fix |
| `--sanitize=memory` / `=undefined` | Tried MSAN/UBSAN | Compiler rejects: `invalid sanitizer` | Only `address`/`thread` accepted in 1.0.0b2 |
| Strip `MOJO_TARGET_CPU` from ALL flags after #6413 fix | Dropped strip from `MOJO_ASAN` too | ASAN test SIGILL (signal 4) — driver fix doesn't reach sanitizer codegen | Keep strip on sanitizer composites only |
| Assume "execution crashed" is a JIT bug | Dismissed bench_simd crash | Real OOB write on empty `List` | Investigate execution crashes as source bugs first |
| Assume a prior docstring/format fix was complete | Trusted earlier PR | Partial fixes leave residual artifacts passing casual review | Always read current file state before assuming |

## Results & Parameters

### Compile / Format Constants

```text
mojo --Werror -I "<repo-root>" -I . <test_file>       # test runner
mojo build --Werror ... -o /tmp/out <example_file>    # binary (has main())
mojo format column limit: 88 chars, implicit string concat, leading-space continuation
GLIBC: host (Debian 10) 2.28 / required 2.32+ / CI Docker (Ubuntu 22.04+) 2.35
```

### Sanitizer Escalation Matrix

| Sanitizer | Status | Use it? |
| --------- | ------ | ------- |
| ASAN | Works (user code only) | YES |
| TSAN | Linker error / runtime abort | NO (until modular/modular#6512) |
| MSAN / UBSAN | Compiler rejects | NO |

### Sanitizer Env / Build Flags

| Setting | Effect | Recommendation |
| ------- | ------ | -------------- |
| `ASAN_OPTIONS=halt_on_error=0:abort_on_error=0:detect_leaks=1` | Collect all reports | Use for `test-mojo-asan` |
| `JOBS="-j1"` for TSAN | Fixes #6413 parallel-JIT compile crash | Required for compile; not for runtime |
| `ODYSSEY_MEM_LIMIT` > physical RAM | cgroups still caps at RAM | Set ≤ physical RAM; reduce demand instead |

### Linker-libm justfile diff (summary)

Add `-not -path "./examples/*"` to the `find` command; remove every `FAIL_ON_ERROR=0` and set
`FAIL_ON_ERROR=1`. Typical change: 2 files / 2 insertions / 4 deletions.

### DynamicVector→List Fix Record

```yaml
pattern: "List[Int]() then shape[N] = val"
fix: "List[Int]() then shape.append(val)"
root_cause: "DynamicVector→List migration regression"
original_code: "DynamicVector[Int](2); shape[0] = size"
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | PR #4512 — `--Werror` audit Round 2 | 538 files swept via 6 parallel agents; 462 PASS, 35 fixed, 8 issues filed (#4519–#4526). |
| ProjectOdyssey | Issue #4514, PR #4887 — libm linker exclusion | Excluded `examples/` from AOT `find`; restored `FAIL_ON_ERROR=1`; 2 files / +2 -4 in justfile. |
| ProjectOdyssey | PR #5389 — Mojo 1.0 sanitizer build system | ASAN: 298/298 tests, 46 real leaks. TSAN: 298/298 compiled with `-j1`, all aborted at startup (tcmalloc). |
| ProjectOdyssey | PR #5364 — KGEN crash sanitizer escalation | ASAN works; TSAN linker error; MSAN/UBSAN rejected. Filed modular/modular#6512. |
| ProjectOdyssey | Mojo 1.0.0b2.dev2026052506 — AVX-512 workaround demolition | Non-sanitizer paths green across 6 Comprehensive Mojo Tests shards; stripping `MOJO_TARGET_CPU` from `MOJO_ASAN` produced SIGILL; retained on sanitizer composites only. |
| ProjectOdyssey | Commit `0b6f52a4` — rebase conflict in test_serialization.mojo | Python set/dict/f-string converted to Bool-flag pattern; rebase completed; test passes. |
| ProjectOdyssey | PR #5175 — bench_simd.mojo OOB | 2 `shape[N] = size` → `shape.append(size)` fixes after DynamicVector→List migration. |

## See Also

- `mojo-jit-crash-retry` — `-j1` context and modular/modular#6413
- `mojo-module-docstring-limitation` — documenting a known re-export limitation
