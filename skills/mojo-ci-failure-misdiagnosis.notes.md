# Session Notes: Mojo CI Failure Misdiagnosis

## Date: 2026-03-15

## Context

- Branch: `fix-mojo-jit-crash-targeted-imports`
- Original plan: Investigate JIT crashes by creating controlled experiments (heavy vs light imports)
- Hypothesis: `from shared.core import` forces JIT to compile 37K lines, causing intermittent buffer overflow

## Timeline

1. Created two synthetic test files: `test_jit_crash_heavy_import.mojo` (package-level import) and `test_jit_crash_light_import.mojo` (targeted import)
2. First attempt used `mojo test` — doesn't exist in this Mojo version. Tests run via `mojo run` with explicit `fn main()`
3. Ran 30 iterations locally (GLIBC 2.39): 0 crashes for both heavy and light
4. Ran 100 iterations of `test_edge_cases_part1.mojo` (package-level imports): 0 crashes
5. Checked ADR-009 original test (25 tests in one file): 50 iterations, 0 crashes
6. Spun up Docker (GLIBC 2.35 matching CI): all tests still 0 crashes
7. Docker `pixi install` corrupted host `.pixi/` env (bind mount issue)
8. Finally checked actual CI logs: ALL failures were `--Werror` compile errors from `alias` deprecation
9. Fix: `alias` → `comptime` on 2 lines in `extensor.mojo`

## CI Log Analysis

```
gh run view 23099501918 --log-failed 2>&1 | grep -E "error:|FAILED"
```

Showed:
- `'alias' is deprecated, use 'comptime' instead` (with --Werror → compile error)
- `invalid call to 'full': value passed to 'fill_value' cannot be converted from 'UInt8' to 'Float64'`
- Retry logic labeled all as "likely Mojo JIT crash — ADR-009"

Zero instances of `execution crashed` in any recent CI run.

## Experiment Results

| Test | Env | Iterations | Pass | Fail |
|------|-----|-----------|------|------|
| Heavy import (no --Werror) | Local GLIBC 2.39 | 30 | 30 | 0 |
| Light import (no --Werror) | Local GLIBC 2.39 | 30 | 30 | 0 |
| edge_cases_part1 (no --Werror) | Local GLIBC 2.39 | 100 | 100 | 0 |
| ADR-009 monolithic (no --Werror) | Local GLIBC 2.39 | 50 | 50 | 0 |
| Heavy import (no --Werror) | Docker GLIBC 2.35 | 30 | 30 | 0 |
| Light import (no --Werror) | Docker GLIBC 2.35 | 30 | 30 | 0 |
| edge_cases_part1 (no --Werror) | Docker GLIBC 2.35 | 100 | 100 | 0 |
| ADR-009 monolithic (no --Werror) | Docker GLIBC 2.35 | 50 | 50 | 0 |
| Any file (--Werror) | Either | any | 0 | all |

## Docker Pitfall

Running `pixi install` inside a Docker container that bind-mounts the host `.pixi/` directory will overwrite the host's Mojo installation with container-pathed binaries. The Mojo binary embeds absolute paths to `libKGENCompilerRTShared.so` at install time, so the host `mojo` command fails with "unable to locate compiler_rt" after Docker corrupts it. Fix: `rm -rf .pixi && pixi install` on host.