---
name: tooling-make-wrapper-skips-image-rebuild
description: "A high-level build wrapper (e.g. a Makefile `build` target, `just`, or a shell script around `docker build`) short-circuits when the target image already exists, prints something like 'image already built', and does nothing — so a Dockerfile edit never lands. Use when: (1) you edited a Dockerfile (added a dependency, bumped a pin, added a package) then ran a `make`/`just`/script build target and the change is not in the running image; (2) a build wrapper prints 'already built'/'up to date' and exits without compiling; (3) you need to confirm a build-input edit actually baked into the output artifact."
category: tooling
date: 2026-06-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - docker
  - dockerfile
  - make
  - build
  - rebuild
  - verification
---

# Tooling: Build Wrapper Skips Image Rebuild on Existing Image

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-06-22 |
| Objective | Make a Dockerfile edit actually take effect when the project's build wrapper short-circuits on an already-built image. |
| Root cause | A high-level build wrapper target (a Makefile `build` target, or any `make`/`just`/script wrapper around `docker build`) is existence-gated: it checks whether the target image tag already exists and, if so, prints something like `Docker image already built` and exits without invoking `docker build`. After you edit the Dockerfile, re-running the wrapper does NOT pick up the change — the stale image keeps running and you are fooled into thinking the edit is live. |
| Outcome | Force a real rebuild with the underlying engine and verify the change is present INSIDE the built image, not just in the Dockerfile source. |
| Verification | verified-local |

## When to Use

- You edited a Dockerfile (added an `ansible-galaxy collection install` entry, changed a pinned dependency, added a package) and then ran the project's `make build` / `just build` / build script, but the new thing is absent from the running container.
- A build wrapper completes near-instantly and prints `image already built`, `up to date`, or similar, without any `docker build` output.
- You want to confirm a build-input edit actually landed before concluding the change is live.

## Verified Workflow

The wrapper only no-ops because it sees the old image tag still present. Bypass the wrapper (call the engine directly) so the rebuild is unconditional, then prove the result by inspecting the OUTPUT artifact rather than the source.

1. After editing a Dockerfile, do NOT trust a wrapper `build` target that may be existence-gated. Force a real rebuild with the underlying engine: `docker build -t <image-tag> .` (add `--no-cache` if a cached layer is the stale part).
2. ALWAYS verify the change actually landed by inspecting the BUILT IMAGE, not the source. Run a command INSIDE the freshly built image that proves the new dependency/package/version is present. Treat "the Dockerfile says X" as NOT proof; "the running image contains X" is the proof.
3. Generic principle: any "build" wrapper that can no-op on an already-built artifact must be paired with an artifact-level verification step. Never conclude a build-input edit is live until you have inspected the output.

### Quick Reference

```sh
# 1. Force an unconditional rebuild (bypass the existence-gated wrapper)
docker build -t <image-tag> .
# add --no-cache if a cached layer holds the stale dependency:
# docker build --no-cache -t <image-tag> .

# 2. Verify the change is present INSIDE the image (not just in the Dockerfile)
docker run --rm <image-tag> <list-or-version-command> | grep -i <expected-token>
# e.g. ansible-galaxy collection list | grep -i <namespace.collection>
#      pip show <package>  |  <tool> --version  |  cat <installed-file>
```

If the wrapper has a force/no-cache flag, prefer it; otherwise call `docker build` directly. Removing the old tag first (`docker rmi -f <image-tag>`) also defeats an existence gate.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Edited the Dockerfile dependency line, then ran the project's `make build` wrapper to bake it in | The wrapper detected an existing image and printed `image already built`, performing NO rebuild; the new dependency was absent from the running image | A wrapper build target may be existence-gated; force `docker build -t <image-tag> .` and verify the dependency exists INSIDE the image, not just in the Dockerfile |
| 2 | Confirmed the change by re-reading the Dockerfile and seeing the new line staged | Source presence proves nothing about the built artifact — the stale image was still running | Verify at the artifact level: run a command inside the freshly built image that prints/lists the expected token |

## Results & Parameters

- **Force rebuild + verify in one pass** (the generic verification one-liner):
  ```sh
  docker build -t <image-tag> .
  docker run --rm <image-tag> <list-or-version-command> | grep -i <expected-token>
  ```
- **If a cached layer is the stale part:**
  ```sh
  docker build --no-cache -t <image-tag> .
  ```
- **Defeat an existence gate without `--no-cache`:**
  ```sh
  docker rmi -f <image-tag> && docker build -t <image-tag> .
  ```
- **Note:** "the Dockerfile says X" is not evidence; "`docker run --rm <image-tag> ...` prints X" is the evidence. Pair every no-op-capable build wrapper with an artifact-level check.

## Related Skills

- [[justfile-and-local-build-verification]] — also a silent build no-op, but a DIFFERENT root cause: a `justfile` `find`-exclusion glob silently skips newly added source directories so the build compiles almost nothing. THIS skill is about an image-existence short-circuit in a `docker build` wrapper (the wrapper sees the tag already exists and skips the rebuild entirely). Read both when a build "succeeds" but your change is missing.
