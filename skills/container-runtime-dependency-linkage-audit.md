---
name: container-runtime-dependency-linkage-audit
description: "Audit whether a runtime dependency (e.g. libssl3) can be dropped from a container image by tracing per-binary linkage from source #defines through CMake link lists and the package manager's transitive usage interface down to ldd/nm on the built artifact. Use when: (1) planning to slim a runtime container image by removing an apparently-unused shared library, (2) a Dockerfile/compose ships a .so (libssl3, libcrypto) you suspect is dead, (3) producing an implementation plan whose conclusion rests on linkage you have NOT yet verified empirically, (4) you need a discipline for flagging uncertain/unverified assumptions in a dependency-removal plan for a reviewer."
category: ci-cd
date: 2026-06-19
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - container
  - docker
  - runtime-image
  - linkage
  - ldd
  - libssl
  - openssl
  - dependency-audit
  - planning
  - unverified-plan
---

# Container Runtime Dependency Linkage Audit

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Capture a durable PLANNING method for auditing whether a runtime shared-library dependency (libssl3) can be dropped from a container image — and, just as importantly, how to identify and flag the assumptions in such a plan that are uncertain / unverified for the reviewer. |
| **Outcome** | Plan only. The method below was used to produce an implementation plan for ProjectAgamemnon issue #279. The plan was NEVER executed: no build was run, no `ldd`/`nm` was invoked, no image was built. Captured at `unverified`. |
| **Verification** | unverified |

## When to Use

- You are planning to slim a runtime container image by removing a shared library (libssl3, libcrypto, etc.) that *looks* unused.
- A Dockerfile or compose file ships a `.so` you suspect is dead weight, and you want to prove (or disprove) it can go.
- You are writing an implementation plan whose central conclusion ("this dependency is droppable") rests on linkage you have read in source but NOT confirmed with `ldd`/`nm` on the real artifact.
- You need a repeatable discipline for separating "build-time link line present" from "runtime `.so` actually loaded", and for flagging version-skew and transitive-link assumptions to a reviewer.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. The originating plan (ProjectAgamemnon #279) was produced from static source reading only — no build, no `ldd`, no image build was ever run.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read every step below as **proposed**, per the warning above.

### Quick Reference

The reusable audit method — apply per binary shipped in the runtime image:

```text
For EACH binary in the runtime image (not just the obvious one):
  1. source  : grep for the feature #define (e.g. CPPHTTPLIB_OPENSSL_SUPPORT)
  2. cmake   : read target_link_libraries — is OpenSSL::SSL / Crypto linked?
  3. pkgmgr  : read the package's transitive/usage link interface
               (Conan conanfile.py / generated <pkg>-config.cmake;
                a usage requirement can propagate the .so even when
                the feature #define is absent and code is #ifdef'd out)
  4. artifact: ONLY ldd / nm on the BUILT binary closes the loop.
               ldd <binary> | grep -i ssl
               nm -D <binary> | grep -i 'SSL_\|EVP_\|crypto'
```

Two rules that the #279 plan violated and a reviewer must enforce:

```text
- A link line being PRESENT does NOT prove the symbol is USED at runtime.
- A #ifdef #define being ABSENT does NOT prove the .so is NOT pulled
  transitively by the package manager's link interface.
=> Neither static fact is authoritative. Only ldd/nm on the real artifact is.
```

### Proposed Detailed Steps

1. **Enumerate every binary** shipped in the runtime image — the server AND the healthcheck binary AND anything else copied into the final stage. Auditing only the obvious binary is how a dependency survives "removal".
2. **Trace each binary through the four layers** above (source `#define` → CMake `target_link_libraries` → package-manager transitive/usage interface → `ldd`/`nm`). Stop trusting the conclusion at any layer above `ldd`/`nm`.
3. **Distinguish build-time link vs runtime `.so` dependency.** A symbol resolved at static-link time, a Conan usage requirement, and an actually-`dlopen`'d/`NEEDED` shared object are three different things. The runtime image only cares about the `NEEDED` entries `ldd` reports.
4. **Re-confirm version-specific dependency claims against the exact build in THIS repo.** Do not extrapolate a coupling claim ("nats.c needs OpenSSL for JetStream TLS") made about one version to a different pinned version, and do not assume a library was compiled with a feature (TLS) it can be built without (`NATS_BUILD_NO_SSL`). Check the actual build flags.
5. **When the conclusion rests on un-run commands, mark the plan `unverified`** and enumerate the EXACT commands the implementer must run to close the loop (the `ldd`/`nm`/build commands), so the reviewer knows precisely what is still a hypothesis.
6. **Separate the lower-risk wins from the contested audit conclusion.** In #279 the plan also fixed a genuinely-broken compose healthcheck (`wget` invoked on a `wget`-less `debian:12-slim` image). That fix is correct and shippable independent of whether the libssl3-removal conclusion holds — call out such separable, lower-risk wins explicitly.

### Uncertain Assumptions To Flag Prominently (from the #279 plan)

These are the assumptions a reviewer MUST scrutinize before trusting the plan:

1. **Healthcheck = zero OpenSSL symbols (BIGGEST unverified leap).** The claim that the healthcheck binary references no OpenSSL symbols rests *entirely* on `healthcheck_main.cpp` not defining `CPPHTTPLIB_OPENSSL_SUPPORT`. It was NOT verified by compiling and running `ldd`/`nm` on the produced binary. cpp-httplib can pull OpenSSL transitively via the Conan `httplib::httplib` package's own link interface even when the SSL code paths are `#ifdef`-compiled out. If so, removing `OpenSSL::SSL`/`OpenSSL::Crypto` from the target may NOT drop the `.so`.
2. **nats.c needs OpenSSL at runtime for JetStream TLS.** Taken from team-KB skills, not confirmed against the actual `nats_static` build flags in THIS repo. nats.c can be built with `NATS_BUILD_NO_SSL` / without TLS. The plan asserts the server NEEDS libssl3 without checking whether nats.c was actually compiled with TLS enabled here.
3. **Version skew in the plan's own evidence.** The plan body says "nats.c v3.12.0" (matching the `CMakeLists.txt` `GIT_TAG` comment) but cites team skill `natsc-fetchcontent-cpp20-integration`, which describes "nats.c v3.9.1". The OpenSSL-coupling claim was made about a DIFFERENT nats.c version — relying on it for v3.12.0 is unverified extrapolation.

### External Sources Relied On Without Direct Verification

- Team-KB skills (`pixi-openssl-sysroot-glibc-private`, `natsc-fetchcontent-cpp20-integration`, `container-image-security-patching`) cited as authoritative for the OpenSSL/nats.c coupling without re-confirming against this repo's current build.
- The Conan `httplib` package's transitive link interface — never inspected (`conanfile.py` / generated `httplib-config.cmake` not read).
- `debian:12-slim` having no `wget` — asserted from general knowledge, not verified against the pinned digest.

### Risks The Reviewer Should Focus On

- **Verify the healthcheck `ldd` claim empirically BEFORE trusting the "drop the link" change** — the build may still link libssl transitively via Conan.
- **Confirm nats.c is actually built WITH TLS in this repo** before asserting libssl3 is load-bearing for the server.
- **The plan still adds value** (it fixes the genuinely-broken compose `wget` healthcheck on a `wget`-less image) even if the libssl3 audit conclusion shifts — this is a separable, lower-risk win.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 1 | Concluded a link is dead from absence of a `#define` alone (no `CPPHTTPLIB_OPENSSL_SUPPORT` ⇒ "no OpenSSL") | The package manager (Conan) may add the dependency transitively via the package's usage/link interface regardless of the `#define` | Only `ldd`/`nm` on the built artifact is authoritative; an absent `#define` does not prove the `.so` is not pulled |
| 2 | Cited team-KB OpenSSL-coupling claim that was made about nats.c v3.9.1 to justify a decision about v3.12.0 | Version-skew extrapolation — the coupling and build flags can differ between versions | Re-confirm dependency claims against the exact version and build flags in the CURRENT repo |
| 3 | Asserted "nats.c requires OpenSSL at runtime for JetStream TLS" without checking build flags | nats.c can be built with `NATS_BUILD_NO_SSL`; the assertion assumed TLS was compiled in | Confirm the feature is actually enabled in this repo's build before treating its dependency as load-bearing |
| 4 | Audited only the obvious server binary for the OpenSSL dependency | A runtime image ships multiple binaries (server + healthcheck); a dependency can survive removal via an un-audited binary | Enumerate EVERY binary in the runtime image before concluding a `.so` is droppable |
| 5 | Treated a build-time link line as equivalent to a runtime `.so` dependency | Build-time link, Conan usage requirement, and runtime `NEEDED`/`dlopen` are three distinct things | Distinguish build-time link vs runtime `.so` dependency; the image only cares about `NEEDED` entries `ldd` reports |
| 6 | Asserted `debian:12-slim` has no `wget` from general knowledge | Not verified against the pinned digest; base-image package sets vary across tags/digests | Verify package presence against the exact pinned image digest, not from memory |

## Results & Parameters

### Configuration

The exact commands an implementer MUST run to convert this plan from `unverified` to verified:

```bash
# 1. Build the runtime image / binaries (per the repo's normal build).
#    Then, for EACH binary copied into the final image stage:
ldd ./healthcheck            | grep -i 'ssl\|crypto'   # expect EMPTY if droppable
nm -D ./healthcheck          | grep -i 'SSL_\|EVP_\|crypto'

ldd ./agamemnon-server       | grep -i 'ssl\|crypto'   # is libssl3 actually NEEDED?
nm -D ./agamemnon-server     | grep -i 'SSL_\|EVP_'

# 2. Confirm whether nats.c was compiled with TLS in THIS repo:
grep -RinE 'NATS_BUILD_NO_SSL|NATS_BUILD_WITH_TLS|OpenSSL' CMakeLists.txt

# 3. Inspect the Conan httplib transitive link interface:
#    read conanfile.py and the generated httplib-config.cmake for OpenSSL usage reqs.

# 4. Verify the base image's package set against the pinned digest:
docker run --rm <pinned-digest> sh -c 'command -v wget || echo NO-WGET'
```

### Expected Output

- A definitive per-binary `ldd`/`nm` result showing whether libssl3 is actually `NEEDED`.
- A confirmed answer on whether nats.c was built with TLS in this repo.
- A confirmed answer on whether Conan's `httplib` package propagates OpenSSL transitively.
- Until all four are run, the plan's conclusion remains a hypothesis and must stay marked `unverified`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectAgamemnon | Issue #279 — "Dockerfile runtime image still has libssl3 — evaluate if needed" | Plan only, UNVERIFIED. Method produced an implementation plan from static source reading; no build, `ldd`, `nm`, or image build was ever run. The healthcheck-OpenSSL and nats.c-TLS conclusions are hypotheses pending the commands above. |

## References

- [`natsc-fetchcontent-cpp20-integration`](./natsc-fetchcontent-cpp20-integration.md) — nats.c FetchContent integration; note its OpenSSL/TLS claims are version-specific and must be re-confirmed per repo build.
- Team-KB skills cited by the #279 plan but NOT re-confirmed against this repo's build (treat as unverified inputs): `container-image-security-patching`, `pixi-openssl-sysroot-glibc-private`. These were relied on as authoritative for the OpenSSL/nats.c coupling without re-validation — exactly the kind of external-source assumption this skill warns against.
