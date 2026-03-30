---
name: natsc-fetchcontent-cpp20-integration
description: "Integrate nats.c v3.9.1 into C++20 projects via CMake FetchContent. Use when: (1) adding NATS JetStream pub/sub to a C++20 service, (2) creating JetStream streams/consumers from C++, (3) debugging nats.c API signature mismatches in C++."
category: tooling
date: 2026-03-30
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - nats
  - cmake
  - fetchcontent
  - cpp20
  - jetstream
---

# nats.c FetchContent C++20 Integration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Add NATS JetStream support to C++20 services (ProjectAgamemnon, ProjectNestor, hello-myrmidon) via nats.c |
| **Outcome** | Successful — all 3 binaries compile and link with nats.c v3.9.1, JetStream streams created, pub/sub working |
| **Verification** | verified-local |

## When to Use

- Adding NATS JetStream messaging to any C++20 project in the HomericIntelligence ecosystem
- Creating JetStream streams and durable pull consumers from C++
- Publishing JSON events to NATS subjects from a cpp-httplib REST server
- Debugging nats.c API compilation errors in C++20 code

## Verified Workflow

### Quick Reference

```cmake
# In CMakeLists.txt — add BEFORE your executable target
FetchContent_Declare(
  nats_c
  GIT_REPOSITORY https://github.com/nats-io/nats.c.git
  GIT_TAG v3.9.1
  GIT_SHALLOW TRUE
)
set(NATS_BUILD_STREAMING OFF CACHE BOOL "" FORCE)
set(NATS_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING_SAVED "${BUILD_TESTING}")
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(nats_c)
set(BUILD_TESTING "${BUILD_TESTING_SAVED}" CACHE BOOL "" FORCE)

# Link to your target
target_link_libraries(my_server PRIVATE nats_static)
```

```cpp
// Include — NOT <nats/nats.h>, just:
#include "nats.h"
```

### Detailed Steps

1. Add FetchContent block to CMakeLists.txt (see Quick Reference)
2. Use `nats_static` target (static link avoids runtime dep)
3. Disable streaming/examples/testing to speed up build
4. Save and restore BUILD_TESTING to avoid breaking your own tests
5. Include `"nats.h"` (not `<nats/nats.h>`) — the target sets include dirs automatically
6. Requires `libssl-dev` at build time (nats.c uses OpenSSL for TLS)

### JetStream Stream Creation (C++)

```cpp
jsCtx* js = nullptr;
natsConnection_JetStream(&js, conn, nullptr);

jsStreamConfig cfg;
jsStreamConfig_Init(&cfg);
cfg.Name = "homeric-myrmidon";
const char* subjects[] = {"hi.myrmidon.>"};
cfg.Subjects = subjects;
cfg.SubjectsLen = 1;

jsStreamInfo* si = nullptr;
jsErrCode jerr = static_cast<jsErrCode>(0);  // CRITICAL: C enum needs cast in C++
natsStatus s = js_AddStream(&si, js, &cfg, nullptr, &jerr);
// Ignore "already exists" errors — idempotent
if (s == NATS_OK && si) jsStreamInfo_Destroy(si);
```

### JetStream Publish (C++)

```cpp
jsPubAck* pa = nullptr;
jsErrCode jerr = static_cast<jsErrCode>(0);
natsStatus s = js_Publish(&pa, js, subject.c_str(),
                          payload.c_str(), payload.size(),
                          nullptr, &jerr);
if (s == NATS_OK && pa) jsPubAck_Destroy(pa);
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `#include <nats/nats.h>` | Standard angle-bracket include | nats.c installs headers flat, not in nats/ subdirectory | Use `#include "nats.h"` — the CMake target sets include dirs |
| `js_AddStream(&si, js, &cfg, nullptr, nullptr)` | Passing nullptr for jsErrCode | v3.9.1 requires `jsErrCode*` parameter, nullptr causes segfault in some builds | Always pass `&jerr` with `jsErrCode jerr = static_cast<jsErrCode>(0)` |
| `jsErrCode jerr = 0` | Direct int initialization | `jsErrCode` is a C enum — C++ doesn't allow implicit int→enum conversion | Use `static_cast<jsErrCode>(0)` in C++20 |
| nats.c v3.12.0 | Tried latest version | v3.12.0 not found on GitHub (latest tag is v3.9.1) | Pin to `v3.9.1` which is the actual latest release |
| `NATS_BUILD_STREAMING ON` | Default streaming support | Adds unnecessary STAN dependency, increases build time | Set `NATS_BUILD_STREAMING OFF` — JetStream is built-in, STAN is separate |

## Results & Parameters

```yaml
# Verified configuration
nats_c_version: v3.9.1
cmake_target: nats_static
build_time: ~60s (89 C objects)
binary_size_overhead: ~500KB (static link)
requires: libssl-dev (build), libssl3 (runtime)
openssl_version_tested: 3.0.13

# JetStream streams created successfully:
streams:
  - name: homeric-agents
    subjects: ["hi.agents.>"]
  - name: homeric-tasks
    subjects: ["hi.tasks.>"]
  - name: homeric-myrmidon
    subjects: ["hi.myrmidon.>"]
  - name: homeric-research
    subjects: ["hi.research.>"]
  - name: homeric-pipeline
    subjects: ["hi.pipeline.>"]
  - name: homeric-logs
    subjects: ["hi.logs.>"]
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectAgamemnon | E2E pipeline implementation | C++20 REST server with 20+ routes + NATS event publishing |
| ProjectNestor | E2E pipeline implementation | C++20 research stats server with NATS research event publishing |
| hello-myrmidon | E2E pipeline implementation | Standalone C++20 NATS pull consumer worker |
