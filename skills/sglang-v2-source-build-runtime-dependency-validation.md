---
name: sglang-v2-source-build-runtime-dependency-validation
description: "Construct and validate a pinned-source SGLang v2 runtime image with CUDA build dependencies that match the PyTorch wheel, no obsolete Mooncake pin, and image-level validation independent of Warden HAProxy. Use when: (1) a SGLang source image fails to compile CUDA extensions, (2) a manifest-derived builder needs to forward source-build packages and a PyTorch CUDA version, (3) a serving image is incorrectly checked for a control-plane binary, (4) publishing a digest-verified SGLang artifact into a manifest-driven runtime catalog."
category: ci-cd
date: 2026-07-24
version: "1.0.0"
verification: verified-local
user-invocable: false
tags: [sglang, source-build, cuda, pytorch, container, manifest, mooncake, haproxy, runtime-validation]
---

# SGLang V2 Source-Build Runtime Dependency Validation

## Overview

| Field | Value |
| ----- | ----- |
| Objective | Build and publish a reproducible SGLang v2 source runtime without confusing build-time CUDA requirements, serving-image dependencies, and Warden control-plane dependencies. |
| Outcome | A manifest-derived image build forwards an explicit PyTorch CUDA version and required compiler/development packages, removes an obsolete Mooncake pin, and validates only what the serving image owns. |
| Verification | verified-local: the pinned-source image built, imported SGLang, and reported CUDA availability; focused manifest and builder tests passed. A full service-lifecycle smoke still requires a healthy control plane. |

## When to Use

Use this when:

1. A pinned SGLang source build must compile CUDA extensions in a container image.
2. The PyTorch wheel targets a specific CUDA release and build tooling must match that release.
3. A manifest-to-shell builder needs to propagate repeatable operating-system package requirements.
4. A legacy Mooncake version pin survives in a SGLang production build without a demonstrated current dependency requirement.
5. An image validation contract requires HAProxy even though HAProxy is launched and owned by Warden rather than shipped in the model-serving image.
6. A verified image digest is ready to be promoted from draft to ready in a manifest-driven runtime catalog.

## Verified Workflow

### 1. Keep build facts in the manifest

Declare the source revision, PyTorch version, explicit `torch_cuda` version, and every required
operating-system build package in the container-requirements manifest. The manifest is the one
source of truth; the builder only renders its values into explicit command-line arguments.

For CUDA extension builds, include a compiler plus the CUDA development packages required by the
extension build. Do not infer the CUDA release from the host driver or rely on a preinstalled
toolchain. The compiler and development packages must align with the CUDA release expected by the
selected PyTorch wheel.

### 2. Make the shell builder consume the complete contract

The builder must reject an absent PyTorch CUDA version or empty build-package list before it starts
a source build. It must:

1. install each manifest-declared package before invoking the build;
2. locate the CUDA compiler and expose its home directory and binary directory to the build;
3. install the PyTorch wheel compatible with the manifest CUDA version; and
4. record the source revision, package set, PyTorch version, and CUDA version in runtime metadata.

Pass repeatable packages as separate shell arguments rather than encoding an unparsed package list
inside an environment variable. This keeps the manifest-to-builder boundary reviewable and avoids
silently changing package selection.

### 3. Separate serving-image validation from Warden validation

The SGLang serving image owns the SGLang executable, Python runtime, CUDA support, and explicitly
declared serving utilities. Warden owns the gateway lifecycle and invokes HAProxy from its own
runtime. Therefore, a SGLang image validation list must not require the HAProxy binary.

Validate the image with an import/version probe and CUDA-availability probe. Validate Warden and
gateway behavior separately through their lifecycle checks. Requiring a Warden-owned binary in the
serving image creates a false failure and expands the image's responsibility without a runtime
need.

### 4. Remove stale optional dependency pins deliberately

Remove an old Mooncake version pin only when the selected SGLang source revision and launch
contract do not require it. Also remove its builder argument and generated metadata field so the
deprecated value cannot remain an implicit dependency. Do not replace it with a new speculative
pin; add a dependency only when a current source-build or serving contract demonstrates it.

### 5. Promote only a verified artifact

Keep the runtime artifact in `draft` state until the source image has been built and its observed
digest has been independently recorded. Once the digest and image-level probe agree with the
manifest contract, mark the cluster-specific artifact `ready`. Validate the runtime release and
the full cluster manifest set after the state transition.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Build CUDA extensions with only a runtime CUDA environment | Relied on the base image and host driver without a matching compiler/development package set | Native extension compilation needs the compiler and development headers/libraries for the PyTorch wheel's CUDA release | Declare and install the matching toolchain packages before the source build |
| Keep a legacy Mooncake pin by default | Forwarded a historical version through manifests, shell arguments, and metadata | The current source-build contract did not consume it, so it created unsupported configuration drift | Remove obsolete pins end-to-end rather than leaving a no-op compatibility argument |
| Require HAProxy in the serving image | Included the gateway binary in the SGLang runtime validation tool list | HAProxy is Warden-owned control-plane software, not a SGLang serving-image dependency | Test image and gateway responsibilities independently |
| Promote a manifest artifact from source metadata alone | Treated a declared digest as proof that usable image bytes existed | Manifest text does not prove the image built or imported successfully | Record an observed digest only after a real image build and image-level probe |

## Results & Parameters

| Parameter | Required behavior |
| --------- | ----------------- |
| `torch_cuda` | Explicit CUDA release compatible with the selected PyTorch wheel |
| `packages` | Non-empty, repeatable list of compiler and CUDA development packages needed by the source build |
| SGLang source revision | Pinned and recorded in generated runtime metadata |
| Mooncake | Absent unless the selected source revision has a demonstrated requirement |
| Image validation tools | Limited to serving-image-owned executables and probes; excludes Warden HAProxy |
| Artifact state | `ready` only after an observed digest and successful image-level probe |

## Evidence

The verified local evidence for this pattern was a pinned SGLang source image that completed its
build, imported SGLang successfully, and reported CUDA availability. The accompanying focused
builder and manifest tests passed, as did both affected cluster manifest validations. The image
probe's later allocation teardown exceeded its scheduler window, so this knowledge does not claim
a completed end-to-end lifecycle run. Run a fresh, isolated lifecycle smoke after the control plane
is healthy before claiming serving readiness.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| Inference360 | Manifest-derived SGLang v2 runtime | Source-build image completed; import and CUDA probes succeeded; focused contract tests and affected cluster manifest validations passed. |

## References

- [Machine-Local Container-Artifact Validation Lane](machine-local-container-artifact-validation-lane.md) for digest-verified artifact materialization and the local-container versus host-CI validation split.
