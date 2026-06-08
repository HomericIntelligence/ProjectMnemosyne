---
name: mojo-ci-runtime-crash-diagnosis-and-mitigation
description: "Use when: (1) CI fails non-deterministically with 'JIT session error: Cannot allocate memory' or SIGSEGV in libKGENCompilerRTShared.so on GHA free-tier runners (VMA exhaustion from ~3.6 GB per mojo invocation), (2) auditing GHA workflows for unprotected bare 'pixi run mojo' calls and applying retry logic for JIT crash resilience, (3) validating that an upstream Mojo fix (runtime crash, codegen flag, compiler-driver bug) actually landed in a bumped nightly before removing downstream workarounds, (4) diagnosing a 'SIGILL on this host but works on others' crash using 4-layer CPU feature detection (kernel /proc/cpuinfo, raw cpuid, compiler-rt __builtin_cpu_supports, compiler driver target resolution), (5) fixing a deterministic Mojo runtime crash (exit 134) when container image UID differs from host runner UID causing Permission denied on ~/.modular, (6) understanding historically documented JIT retry patterns that are now obsolete after modular/modular#6413."
category: ci-cd
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: mojo-ci-runtime-crash-diagnosis-and-mitigation.history
tags:
  - mojo
  - jit
  - crash
  - ci
  - gha
  - vma
  - libkgen
  - sigill
  - sigsegv
  - cpu-feature-detection
  - cpuid
  - print-effective-target
  - uid-mismatch
  - container
  - upstream-validation
  - retry
  - avx512
  - modular-6413
---

# Mojo CI Runtime Crash Diagnosis and Mitigation

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-06-07 |
| **Objective** | One canonical reference for diagnosing and mitigating Mojo JIT/runtime crashes in CI: VMA (virtual address space) exhaustion on GHA free-tier runners, workflow retry auditing, upstream-fix validation before removing workarounds, multi-layer CPU feature-detection (SIGILL) probing, and container UID-mismatch crashes. |
| **Outcome** | Consolidated from 6 overlapping skills. Live root-cause and mitigation patterns retained; obsolete retry posture is documented as historical context only (see modular/modular#6413). |
| **Verification** | verified-ci |

## When to Use

1. CI fails non-deterministically with `JIT session error: Cannot allocate memory` or `SIGSEGV` in `libKGENCompilerRTShared.so` on GHA free-tier runners (7 GB RAM, ~3.6 GB VmPeak per mojo invocation).
2. Auditing GHA workflows for unprotected bare `pixi run mojo` calls and applying retry logic for JIT crash resilience.
3. Validating that an upstream Mojo fix (runtime crash, codegen flag, compiler-driver bug) actually landed in a bumped nightly before removing downstream workarounds.
4. Diagnosing a "SIGILL on this host but works on others" crash using 4-layer CPU feature detection.
5. Fixing a deterministic Mojo runtime crash (exit 134) when container image UID differs from host runner UID, causing `Permission denied [/home/.../.modular]`.
6. Understanding historically documented JIT retry patterns that are now obsolete after modular/modular#6413.

### Crash Classification — Start Here

Misidentifying the crash type wastes investigation time. Check the stack offsets and timing first.

| Symptom | Crash Type | Fix |
| --- | --- | --- |
| `JIT session error: Cannot allocate memory` / SIGSEGV, non-deterministic on 7 GB GHA runners | VMA exhaustion (modular#6433) | Sequential single-job workflow (one mojo process at a time) |
| `execution crashed` + `filesystem error: Permission denied [.../.modular]`, exit 134, 100% reproducible at CI UID | UID mismatch (modular#6412) | Dockerfile `chmod 755 $HOME` + cache key UID + entrypoint HOME-fixup |
| SIGILL at JIT execution on some CPUs but not others; driver emits AVX-512 on masked-AVX-512 host | CPU feature mismatch (modular#6413) | Upstream-fixed; validate via 4-layer probe + `--print-effective-target` |
| `execution crashed` before output, variable offsets | JIT volume / VMA — see above | Sequential job; import audit is a red herring for pure VMA |

## Verified Workflow

### Quick Reference

```bash
# --- VMA exhaustion: deterministic local reproducer ---
ulimit -v 3500000 && pixi run mojo --Werror -I . tests/any_test.mojo   # → crash below ~3.6 GB
ulimit -v 4000000 && pixi run mojo --Werror -I . tests/any_test.mojo   # → PASS at 4.0 GB+

# --- Workflow audit: find unprotected mojo calls ---
grep -rn "pixi run mojo" .github/workflows/ --include="*.yml" | grep -v "mojo --version" | grep -v "mojo format"

# --- UID mismatch: reproduce at the CI UID ---
podman compose down -v
USER_ID=1001 GROUP_ID=1001 podman compose up -d
podman compose exec -T myservice bash -c "mojo run test.mojo"; echo "Exit: $?"   # → 134 if broken

# --- CPU feature mismatch: driver-resolved target ---
pixi run mojo build --print-effective-target some.mojo   # compare against /proc/cpuinfo & cpuid

# --- Upstream fix validation: Gate 0 (verify the premise) ---
grep '^mojo' pixi.toml && git log --oneline -- pixi.toml | head -5
```

### Detailed Steps

#### A. VMA Exhaustion on GHA Free-Tier Runners (modular/modular#6433)

Mojo's JIT unconditionally reserves ~3.6 GB of virtual address space on startup, regardless
of source size. GHA free-tier `ubuntu-latest` runners have ~7 GB RAM, so two overlapping
`mojo` processes (2 × 3.6 = 7.2 GB) exceed available memory → OOM → SIGSEGV in the JIT.

```bash
# Step 1: Confirm root cause is VMA, not JIT volume or UID
ulimit -v 3500000 && pixi run mojo --Werror -I . tests/any_test.mojo   # fails → confirmed
ulimit -v 4000000 && pixi run mojo --Werror -I . tests/any_test.mojo   # passes → ~3.6 GB threshold
# max-parallel:1 does NOT fix it — separate GHA jobs overlap during setup/teardown.
```

Fix: replace the GHA **matrix** strategy with a **single sequential job** where each test
group is a named step, guaranteeing only one `mojo` process runs at a time.

```yaml
# AFTER (fix): single job, all groups as named steps, NO continue-on-error
test-mojo-comprehensive:
  runs-on: ubuntu-latest
  timeout-minutes: 120
  steps:
    - uses: actions/checkout@v4
    # ... setup steps (pixi install, container start) ...
    - name: "Memory snapshot"
      run: free -h && ulimit -v
    - name: "Core Tensors"
      run: just test-group "tests/shared/core" "test_tensors*.mojo test_any_tensor*.mojo"
    - name: "Core Activations & Types"
      run: just test-group "tests/shared/core" "test_activation*.mojo test_dtype*.mojo"
    # ... all remaining groups as steps
```

Add `-debug-level=line-tables` to mojo invocations (symbolicated traces) and validate YAML:

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/comprehensive-tests.yml'))" && echo "YAML valid"
```

#### B. Workflow Retry Auditing for JIT-Crash Resilience

> **Posture note:** Retry is the WRONG long-term answer for a real bug — it masks
> reproducibility and blocks upstream filing (see Failed Attempts and the historical context
> in the history file). The audit below remains useful for finding *unprotected* calls; for the
> dominant pre-#6413 crash class, the correct fix is the upstream bump, not retry.

Find every bare call, then classify it:

```bash
grep -rn "pixi run mojo" .github/workflows/ --include="*.yml"
```

| Call type | Best handling |
| --- | --- |
| Test file (`*.mojo`) | Route through `just test-group` (add `Install Just` step) |
| Package build (`mojo package`) | Inline retry loop |
| Benchmark / build / run | Inline retry loop |
| Version check (`mojo --version`) | No retry — does not invoke the JIT |

Inline 3-attempt exponential-backoff loop (preserve `|| true` for soft-fail workflows):

```bash
attempt=0; delay=1
while [ $attempt -lt 3 ]; do
  attempt=$((attempt + 1))
  if pixi run mojo <args>; then break; fi
  if [ $attempt -lt 3 ]; then
    echo "Attempt $attempt failed, retrying in ${delay}s..."
    sleep $delay; delay=$((delay * 2))
  else
    echo "Failed after 3 attempts"; exit 1
  fi
done
```

Audit script to detect bare (unwrapped) compiling subcommands:

```python
# scripts/validate_mojo_retry_pattern.py
COMPILING_SUBCOMMANDS = {"test", "run", "build", "package"}
RETRY_MARKERS = ("while [", "attempt=")

def _has_retry_protection(block: str) -> bool:
    return any(marker in block for marker in RETRY_MARKERS)
```

#### C. Validating an Upstream Mojo Fix Before Removing Workarounds (4-Gate Protocol)

Before peeling any downstream workaround (Dockerfile chmod, entrypoint mkdir, `--target-cpu`
pin, sudoers `_ensure_writable`), confirm the upstream fix actually landed in your bumped pin.

```bash
# === GATE 0 (mandatory) — verify the version premise ===
grep '^mojo' pixi.toml
git log --oneline -- pixi.toml | head -5
# If the pinned version predates the upstream fix-shipped date, STOP. The rest is theater.

# === GATE 1 — cheapest local signal for the bug class ===
# (B1) Codegen / target-resolution bugs (e.g. #6413 AVX-512 mis-emission):
cat > /tmp/repro.mojo <<'EOF'
def main():
    print("ok")
EOF
pixi run mojo build --print-effective-target /tmp/repro.mojo
# Pre-fix on masked-AVX-512 host: --target-cpu znver4 + +avx512*. Post-fix: host's real ISA, NO avx512.
# Then run the real reproducer 5×50 = 250 iterations: pre-fix ~100% crash, post-fix 0.

# (A1) Filesystem-error class (e.g. #6412): hostile-$HOME matrix — build once, exec under N HOME shapes.
pixi run mojo build /tmp/hello.mojo -o /tmp/hello   # def main(): print("ok")
mkdir -p /tmp/fake-home && chmod 000 /tmp/fake-home
HOME=/tmp/fake-home /tmp/hello; echo "exit=$?"   # 0 = fixed, 134 = still broken (do NOT peel)
HOME=/tmp/does-not-exist-$$ /tmp/hello; echo "exit=$?"
env -u HOME /tmp/hello; echo "exit=$?"
HOME=/dev/null /tmp/hello; echo "exit=$?"
chmod 755 /tmp/fake-home; rm -rf /tmp/fake-home /tmp/hello

# === GATE 2 — dispatch the existing repro-<issue#> workflow ≥10× on the bump branch ===
for i in $(seq 1 10); do gh workflow run repro-<issue#>.yml --ref <bump-branch>; sleep 2; done
# CAVEAT: pre-fix coredump/gdb infra often bitrots and reports "failure" while the Mojo step
# actually succeeded. Inspect the Mojo invocation logs, NOT the workflow badge. Do not fix
# pre-fix infra slated for demolition.

# === GATE 4 — ≥8 consecutive green required-check runs on the bump branch ===
gh pr checks <bump-pr> --watch
# Gate 4 frequently catches stdlib API regressions that ride along with the bump
# (removed constructors, renamed traits). Fix them on the bump branch BEFORE any demolition.
```

Keep the validation PR OPEN as a historical canary spanning the demolition wave; close only
after the first demolition merges.

#### D. Multi-Layer CPU Feature-Detection Mismatch Probe (SIGILL triage)

For "SIGILL on this host but works on others" / "wrong instruction emitted", probe four
orthogonal layers on the same host, then diff. The disagreement pattern names the culprit.

| Layer | What it queries | API |
| --- | --- | --- |
| 1. Kernel-mediated | `/proc/cpuinfo flags`, `AT_HWCAP` (includes hypervisor masking) | shell, `getauxval` |
| 2. Silicon-direct | raw `cpuid` + `xgetbv(0)` (XCR0 mask) | `<cpuid.h>` in C |
| 3. Compiler-rt | `__builtin_cpu_supports("name")` | gcc/clang builtin |
| 4. Driver-resolved | what the compiler chose for codegen | Mojo `--print-effective-target`; `rustc --print=target-features`; `clang -march=native -E -dM`; `llc --print-supported-cpus` |

```bash
# Layer 1
grep -m1 ^flags /proc/cpuinfo | tr ' ' '\n' | grep -E '^(avx512[a-z0-9_]*|avx2|avx|fma)$' | sort -u
# Layer 2 (compile and run)
cat > /tmp/probe.c <<'EOF'
#include <stdio.h>
#include <cpuid.h>
int main(void){unsigned a,b,c,d;__cpuid_count(7,0,a,b,c,d);
 printf("AVX512F=%d AVX512VL=%d\n",!!(b&(1u<<16)),!!(b&(1u<<31)));return 0;}
EOF
gcc -O2 -o /tmp/probe /tmp/probe.c && /tmp/probe
# Layer 3
cat > /tmp/builtin.c <<'EOF'
#include <stdio.h>
int main(void){__builtin_cpu_init();printf("avx512f=%d\n",__builtin_cpu_supports("avx512f"));return 0;}
EOF
gcc -O2 -o /tmp/builtin /tmp/builtin.c && /tmp/builtin
# Layer 4
pixi run mojo build --print-effective-target some.mojo
```

Interpretation:

| L1 kernel | L2 cpuid | L3 builtin | L4 compiler | Diagnosis |
| --- | --- | --- | --- | --- |
| no | no | no | **AVX-512** | **Bug in compiler driver** — emits codegen the silicon can't run (modular#6413) |
| no | AVX-512 | no | varies | Hypervisor masking — compiler-rt correctly stops at kernel/XCR0 view |
| AVX-512 | AVX-512 | AVX-512 | no | Compiler honoring an explicit `--target-features=-avx512f` override (intentional) |
| AVX-512 | AVX-512 | no | varies | Host gcc/clang too old to know the feature name; upgrade the toolchain |

Always probe a known-good baseline host AND inside vs outside the container.

#### E. Container UID-Mismatch Crash (exit 134, modular/modular#6412)

`libAsyncRTMojoBindings.so` calls `std::filesystem::status("$HOME/.modular")` (throwing
overload) at startup. When the container UID ≠ home-dir owner UID, `filesystem_error:
Permission denied` propagates to `std::terminate` → `abort()` → exit 134. 100% reproducible.

```text
mojo run → dlopen libAsyncRTMojoBindings.so → getAcceleratorArchOrEmpty()
  → std::filesystem::status("$HOME/.modular")  → filesystem_error: Permission denied
    → std::terminate() → abort() → SIGABRT (exit 134)
```

```dockerfile
# Fix 1: make home dir traversable by other UIDs (useradd -m defaults to mode 750)
RUN useradd -m -u ${USER_ID} -g ${GROUP_ID} -s /bin/bash ${USER_NAME} && \
    chmod 755 /home/${USER_NAME}
# Fix 2: do NOT chmod -R 700 pixi dirs (use 755 if explicit control needed)
# Fix 6: grant passwordless sudo for mkdir/chown/chmod (bind-mount subdir reclaim)
RUN printf 'dev ALL=(root) NOPASSWD: /bin/mkdir\ndev ALL=(root) NOPASSWD: /bin/chown\ndev ALL=(root) NOPASSWD: /bin/chmod\n' \
    > /etc/sudoers.d/dev-workspace && chmod 440 /etc/sudoers.d/dev-workspace
```

```bash
# Fix 3: entrypoint.sh — pre-create .modular or redirect HOME to /tmp
if [ ! -d "${HOME}/.modular" ]; then
    mkdir -p "${HOME}/.modular" 2>/dev/null || {
        export HOME="/tmp/mojo-home-$(id -u)"; mkdir -p "${HOME}/.modular"
        export PIXI_HOME="${HOME}/.pixi"
    }
fi
# Fix 6: entrypoint _ensure_writable — non-interactive sudo + recursive chown
_ensure_writable() {
    for dir in "$@"; do
        mkdir -p "$dir" 2>/dev/null || sudo -n mkdir -p "$dir" 2>/dev/null || true
        [ -w "$dir" ] && continue
        chmod u+w "$dir" 2>/dev/null || sudo -n chown -R "$(id -u):$(id -g)" "$dir" 2>/dev/null || true
    done
}
_ensure_writable build .pixi datasets lenet5_weights tests/configs/fixtures /tmp/mojo-tests
```

```yaml
# Fix 4: CI cache key must include runner UID (UID-1000 image must not run as UID-1001)
- name: Get runner UID
  id: uid
  run: echo "user_id=$(id -u)" >> "$GITHUB_OUTPUT"
- uses: actions/cache@v4
  with:
    key: container-image-uid${{ steps.uid.outputs.user_id }}-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}
# Use ${{ steps.uid.outputs.user_id }}, NOT ${{ env.USER_ID }} (env from earlier step is unreliable).
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| `max-parallel: 1` on the matrix to serialize Mojo jobs | Set matrix `max-parallel: 1` | GHA jobs are separate processes; setup/teardown of adjacent jobs overlap on the same physical machine, so two `mojo` processes co-exist transiently and exceed 7 GB | `max-parallel` controls scheduling concurrency, not machine exclusivity. Use a single sequential job (steps, not matrix) to guarantee one mojo process at a time |
| `ulimit -v unlimited` in the test recipe | Added `ulimit -v unlimited` to raise the VMA cap | Shell `ulimit` cannot override cgroup memory limits enforced by the GHA VM/hypervisor | Hard cgroup limits are infra-set and not overridable from inside the job |
| Convert package imports to targeted submodule imports (assumed JIT volume) | Changed `from shared.core import X` to submodule imports | 40/40 local runs passed but root cause was per-process VmPeak, not compilation footprint — import volume was a red herring | The `ulimit -v` reproducer reveals the true root cause; don't chase import-volume theories for pure VMA crashes |
| Treat the crash as JIT flakiness and retry / `continue-on-error` | Added retry loops or `continue-on-error: true` to swallow crashes | Masks the bug; a crash that is retried away cannot be filed upstream and recurs after the next Mojo bump | Fail fast, reproduce, and fix (or bump past the upstream fix). Retry/`continue-on-error` is the wrong direction |
| Removed downstream workaround on a "fixed" version without checking the pin | Trusted the claim the Mojo version was bumped and removed workarounds | The version had not actually been bumped; validation was meaningless | Always run Gate 0 (`grep '^mojo' pixi.toml && git log -- pixi.toml`) before validating any upstream-fix claim |
| Dismissed a Gate 2 "failed" workflow as the fix not landing | Spent cycles on the repro workflow's failing badge | Failure was in the bitrotted coredump-capture composite action; the actual Mojo step succeeded | Inspect the Mojo invocation logs, not the workflow badge. Don't fix pre-fix infra slated for demolition |
| Dismissed a Gate 4 required-check failure as a flake | "Looks like a flake, rerun" | It was a real stdlib API regression (`UnsafePointer._unsafe_null=()` removed) riding along in the same nightly bump | Gate 4 failures on a Mojo-bump branch are almost never flakes; the bump drags in API churn that must be fixed on the same branch first |
| Skip layer 2 (raw cpuid) and trust `/proc/cpuinfo` + `__builtin_cpu_supports` | Probed only kernel + compiler-rt views | Cannot distinguish "no AVX-512 silicon" from "AVX-512 silicon under hypervisor mask" — both look identical without raw cpuid | Always include the silicon-direct layer; it is the only ground-truth view of the hardware |
| Classified the UID crash as non-deterministic JIT flakiness | Closed it as unfixable JIT noise; local tests at UID 1000 passed | Crash was 100% deterministic at the CI UID; warm-cache local UID-1000 runs masked it | Always reproduce at the exact CI runner UID before calling a crash flaky |
| `MODULAR_HOME=/tmp/.modular` to redirect the startup check | Set the env var to move `.modular` | `libAsyncRTMojoBindings.so` reads `$HOME/.modular` directly via native C++ before any env handling | Fix permissions or pre-create the dir / redirect `$HOME`; env-var redirect does not affect the native call |
| Non-recursive `chown` in `_ensure_writable` | `sudo chown $(id -u):$(id -g) "$dir"` without `-R` | Existing root-owned subdirs (`build/release/`) stayed root:root; linker still failed | Use `chown -R` when reclaiming a tree that may contain root-owned children; use `sudo -n` (plain sudo blocks on `exec -T`) and include `/bin/mkdir` in the NOPASSWD grant |

## Results & Parameters

### GHA Runner Memory Profile (VMA exhaustion)

| Resource | Value |
| --- | --- |
| Total RAM (GHA free-tier `ubuntu-latest`) | ~7 GB |
| Mojo VmPeak per process | ~3.6 GB (modular/modular#6433) |
| Max concurrent `mojo` processes before OOM | 1 |
| `max-parallel: 1` prevents overlap? | NO (job lifecycle overlap) |
| Single job, sequential steps prevents overlap? | YES |

### Standard Retry Parameters

- Max attempts: 3 · Base delay: 1s · Backoff: 2× (1s, 2s)
- Exit behavior: `exit 1` on hard-fail workflows; preserve `|| true` on soft-fail workflows
- Only JIT-compiling subcommands need retry: `test`, `run`, `build`, `package` (not `--version`/`format`)

### 4-Gate Pass Criteria (upstream-fix validation)

| Gate | Pass Criteria | Confidence |
| --- | --- | --- |
| 0 | Pinned Mojo version in `pixi.toml` is at/past the fix-shipped date | Mandatory pre-check |
| 1 | Local micro-repro clean for the bug class; `--print-effective-target` matches host ISA | Low (fix in binary) |
| 2 | `repro-<issue#>` workflow ≥10× with zero signature-library frames | Medium |
| 4 | ≥8 consecutive green runs across ALL required checks | High |

### CPU Feature Mismatch — modular/modular#6413 root cause

LLVM `getHostCPUName()` returns `"znver4"` from family/model (which Hyper-V does not mask),
then `X86TargetParser.cpp::Processors[]` applies a static AVX-512 feature list without
intersecting against the masked CPUID leaves → SIGILL at JIT execution. Confirmed on GHA
Azure AMD EPYC 9V74 (Zen 4) under Hyper-V, CI runs 25778579617 + 25778580407. Fixed upstream.

### UID Crash Signature (modular/modular#6412)

```text
terminate called after throwing an instance of 'std::filesystem::__cxx11::filesystem_error'
  what():  filesystem error: status: Permission denied [/home/dev/.modular]
Aborted (core dumped)          # exit code 134
libKGENCompilerRTShared.so+0x6d4ab / +0x6a686 / +0x6e157 ; libc.so.6+0x45330 (__fortify_fail_abort)
```

### Upstream References

- VMA / VmPeak reservation: [modular/modular#6433](https://github.com/modular/modular/issues/6433)
- Filesystem-error startup crash: [modular/modular#6412](https://github.com/modular/modular/issues/6412)
- AVX-512 mis-emission / SIGILL: [modular/modular#6413](https://github.com/modular/modular/issues/6413)

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | PR #5351 — VMA exhaustion sequential-job fix | Matrix → single sequential job; modular#6433; verified-precommit/CI |
| ProjectOdyssey | Issue #3329, PR #3950 — workflow retry audit | 8 workflows protected; route tests via `just test-group`, inline retry elsewhere |
| ProjectOdyssey | modular/modular#6412 + #6413 validation | 4-gate protocol; Gate 1 hostile-`$HOME` matrix + `--print-effective-target`; Gate 4 caught coincident stdlib API regression |
| ProjectOdyssey | modular/modular#6413 root-cause | 4-layer CPU feature probe on GHA EPYC 9V74; CI runs 25778579617 + 25778580407 |
| ProjectOdyssey | PRs #5217, #5252, #5351 — UID mismatch crash | Dockerfile `chmod 755 $HOME`, UID cache key, entrypoint `_ensure_writable` (recursive, `sudo -n`) |
| ProjectOdyssey | Historical retry/forensics context (modular#6413 demolition PRs #5458–#5460) | Retry/coredump/gdb infra removed after upstream fix landed; see history file |
