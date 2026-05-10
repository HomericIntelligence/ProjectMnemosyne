---
name: mojo-binary-closed-source-debugging
description: "Use when: (1) trying to build Mojo from source to debug a libKGEN* crash and looking for the compiler in the modular/modular repo, (2) trying to resolve a Mojo binary version hash (e.g. ed7c8f0a) to a public commit, (3) deciding whether self-building Mojo is a viable debugging path for a runtime crash, (4) writing an upstream issue and need to know what level of source-level investigation is possible, (5) considering forking modular/modular to add instrumentation, (6) confused why grep/git-blame across modular/modular doesn't find KGEN/Async/MSupport runtime code."
category: debugging
date: 2026-05-09
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - mojo
  - upstream
  - modular
  - closed-source
  - debugging
  - libKGEN
  - escalation
---

# Mojo Binary Is Closed-Source — Cannot Self-Build for Crash Debugging

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-05-09 |
| **Objective** | Document the boundary of what source-level Mojo debugging is possible: the public `modular/modular` repo only ships the standard library, not the compiler/runtime. Self-building Mojo is not a viable path for debugging `libKGEN*` / `libAsync*` / `libMSupport*` crashes. |
| **Outcome** | Confirmed during ProjectOdyssey PR #5363/#5364 investigation of Mojo 1.0.0b2 KGEN crash. The only viable path for compiler-internal bugs is upstream issue + reproducer + waiting. |
| **Verification** | verified-local |

## When to Use

- You're investigating a Mojo runtime crash (frames in `libKGENCompilerRTShared.so`,
  `libAsyncRTMojoBindings.so`, `libMSupport.so`, etc.) and considering building Mojo
  from source to add instrumentation or step through with a debugger
- You're trying to resolve the Mojo binary's internal version hash (e.g. `ed7c8f0a` in
  `1.0.0b2.dev2026...`) to a public git commit so you can read the source
- You're writing an upstream issue against `modular/modular` and need to set realistic
  expectations about your level of access
- An agent or teammate proposes "let's just patch Mojo locally" or "let's grep the
  Mojo repo for this function" — both are blocked by closed-source

## Verified Workflow

### Quick Reference

```bash
# Confirm what is actually in the public modular/modular repo
gh repo clone modular/modular /tmp/modular-public
ls /tmp/modular-public/                    # mojo/, max/, examples/, ...
ls /tmp/modular-public/mojo/               # stdlib/, docs/, ...
# Note the absence of: compiler/, kgen/, runtime/, async-runtime/

# Confirm the runtime libs are NOT in the repo
find /tmp/modular-public -name 'libKGEN*' -o -name 'libAsync*' -o -name 'libMSupport*'
# (no output)

# Confirm the version hash in your installed Mojo is not in the public repo
pixi run mojo --version
# mojo 1.0.0b2.dev2026... (ed7c8f0a)
git -C /tmp/modular-public log --all --grep='ed7c8f0a' --oneline
git -C /tmp/modular-public rev-parse ed7c8f0a 2>&1
# fatal: ambiguous argument 'ed7c8f0a': unknown revision
```

### What is and is not in `modular/modular`

| Component | In public repo? | Implication |
| --- | --- | --- |
| `mojo/stdlib/` (Tensor, List, Dict, String, etc.) | YES | You CAN build, modify, and submit PRs against the standard library |
| Mojo compiler frontend (parser, type checker, MLIR pipeline) | NO | Not buildable from public source |
| `libKGENCompilerRTShared.so` (JIT runtime) | NO | Not buildable from public source |
| `libAsyncRTMojoBindings.so`, `libAsyncRTRuntimeGlobals.so` | NO | Not buildable from public source |
| `libMSupport.so`, `libMojoJupyter*.so` | NO | Not buildable from public source |
| The `mojo` binary itself | NO | Distributed only as a pre-built binary via `pip`/`conda`/`pixi` |

### Why the version hash is unresolvable

The hash printed by `mojo --version` (e.g. `ed7c8f0a` inside `1.0.0b2.dev2026XXXX`) is
from Modular's **private build system**. It corresponds to a commit in their internal
monorepo, not in the public `modular/modular` repo. There is no public tag,
branch, or commit named `1.0.0b2.dev2026XXXX` — these dev builds are produced from
private source and shipped as binaries only.

### What you CAN do for stdlib bugs

If a crash reproduces against stdlib code (e.g. `Tensor.__copyinit__`, `List.append`,
`String.__add__`):

1. Clone `modular/modular`
2. Edit the stdlib file
3. Build a local stdlib package and override the installed one
4. Test the fix
5. Submit a PR upstream

### What you can ONLY do via upstream issue

For runtime/JIT crashes (any `libKGEN*` / `libAsync*` / `libMSupport*` frame):

1. **Capture a coredump** (see `gha-mojo-coredump-capture` skill)
2. **Decode the published trace as far as possible** using dynsym + objdump (see
   `mojo-jit-crash-retry` skill v4.1.0+)
3. **File an upstream issue** at `https://github.com/modular/modular/issues` with:
   - Mojo version (full string including the dev hash)
   - Stack offsets and dynsym buckets
   - Sanitizer reports if any (see `mojo-sanitizer-support-matrix` skill)
   - Minimal repro
   - Coredump artifact link if you have one
4. **Wait for Modular** to investigate against their private source

There is no shortcut. Forking `modular/modular` and patching does not help — the
compiler/runtime is not in the fork.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Clone modular/modular and grep for libKGEN function | `gh repo clone modular/modular && grep -r KGEN .` | KGEN runtime source is not in the public repo (only stdlib is); grep returns hits in test names and docstrings, never in implementation | The compiler and runtime are closed-source; only `mojo/stdlib/` is public |
| Resolve Mojo binary version hash to a public commit | `git -C modular-public rev-parse <hash>` from `mojo --version` output | Hash is from Modular's private monorepo, not public `modular/modular` | Dev-build hashes (`1.0.0b2.dev*`) cannot be resolved publicly; do not use them as a basis for source navigation |
| Self-build Mojo with debug symbols to step through libKGEN crash | Considered cloning `modular/modular` and running its build to produce a debug `mojo` binary | The repo only builds stdlib packages, not the compiler/runtime; there is no `make mojo` or `bazel build //mojo/compiler:mojo` target available publicly | Stop pursuing source-level Mojo runtime debugging; escalate to upstream with the best fingerprint you can produce (dynsym buckets + sanitizer reports + coredump) |
| Fork modular/modular to patch around a libKGEN crash | Proposed forking and patching the JIT runtime locally | The JIT runtime source is not in the fork; only stdlib is | Forking does not help for runtime bugs; only for stdlib bugs |
| `nm -D` libKGEN to find the function name to grep upstream for | Ran `nm -D libKGENCompilerRTShared.so | grep <suspected-feature>` | The binary is stripped; most internal functions fold into the giant `_ZNSt24uniform_int_distributionImEclISt13random_deviceEEmRT_RKNS0_10param_typeE@@Base` anchor symbol; you can identify a 60+KB region but not the function | Use the dynsym map to bucket crash offsets (see `mojo-jit-crash-retry` v4.1.0), then file upstream — Modular has the symbols privately |

## Results & Parameters

### Decision tree for "should I try to build Mojo from source?"

```text
Is the crash in stdlib (Tensor, List, String, Dict, ...)?
├─ YES → Clone modular/modular, edit stdlib, build, override, test, PR upstream
└─ NO → Is the frame in libKGEN* / libAsync* / libMSupport* / libMojo* ?
    ├─ YES → STOP. Self-build is impossible. File upstream issue with:
    │         - dynsym buckets (mojo-jit-crash-retry v4.1.0)
    │         - sanitizer reports (mojo-sanitizer-support-matrix)
    │         - coredump artifact (gha-mojo-coredump-capture)
    └─ NO  → Re-examine the trace; if frame 4 is `<unmapped>`, the real fault may
              still be in JIT-emitted code; capture a coredump first
```

### Companion skills

- `mojo-jit-crash-retry` (v4.1.0+): dynsym + objdump forensic procedure, frame-pattern
  recognition (Crashpad signal-handler chain vs real fault)
- `mojo-sanitizer-support-matrix`: which `--sanitize=` flags actually work in 1.0.0b2
  (only ASAN; TSAN broken; MSAN/UBSAN rejected)
- `gha-mojo-coredump-capture`: how to capture a real coredump from CI when frame 4
  is `<unmapped>` and you need to recover the JIT-emitted fault site

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| ProjectOdyssey | PR #5363 / #5364 — Mojo 1.0.0b2 KGEN +0x6ef7b/+0x6c156/+0x6fc27 crash investigation | Confirmed `modular/modular` ships only stdlib; binary version hash `ed7c8f0a` not resolvable publicly; self-build attempt abandoned in favor of upstream issue |
