---
name: e2e-compose-python-stub-to-cpp-server
description: "Migrate E2E compose services from Python stub servers to real C++ multi-stage Dockerfiles. Use when: (1) replacing Python FastAPI stubs with compiled C++ servers in compose, (2) healthcheck fails because C++ container lacks Python, (3) compose build context points to missing stub directory."
category: ci-cd
date: 2026-03-31
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - podman
  - compose
  - e2e
  - cpp
  - dockerfile
  - healthcheck
---

# Migrate E2E Compose from Python Stubs to C++ Servers

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-31 |
| **Objective** | Replace Python FastAPI stub containers with real C++20 multi-stage build containers in an E2E compose stack |
| **Outcome** | Successful — compose services point to real C++ Dockerfiles, healthchecks use wget instead of python3 |
| **Verification** | verified-local |

## When to Use

- E2E compose file references a `stub/` directory that doesn't exist or contains a Python stub that violates architecture rules
- Healthchecks in compose use `python3 -c "import urllib..."` but the C++ runtime image doesn't have Python
- Migrating from prototype Python stubs to production C++ services in a compose stack

## Verified Workflow

### Quick Reference

```yaml
# BEFORE (Python stub)
agamemnon:
  build:
    context: control/ProjectAgamemnon/stub/   # Python FastAPI
  healthcheck:
    test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8080/v1/health')\""]

# AFTER (real C++ server)
agamemnon:
  build:
    context: control/ProjectAgamemnon/        # Multi-stage C++ Dockerfile
  healthcheck:
    test: ["CMD-SHELL", "wget -qO- http://localhost:8080/v1/health 2>/dev/null || exit 1"]
```

### Detailed Steps

1. Change compose `build.context` from `stub/` subdirectory to repo root (where the real `Dockerfile` lives)
2. Replace all `python3 urllib` healthchecks with `wget -qO-` (the C++ runtime image has `wget` but not Python)
3. Ensure the C++ Dockerfile's runtime image installs `wget` (`apt-get install wget`)
4. Verify environment variables match between stub and real server (e.g., `NATS_URL`, `PORT`)
5. Delete the stub directory if it violates architecture rules
6. Run the E2E test suite to verify the full pipeline still works

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| python3 urllib healthcheck | `python3 -c "import urllib.request; urllib.request.urlopen(...)"` | C++ runtime images (ubuntu:24.04 slim + wget) don't have Python installed | Use `wget -qO-` for healthchecks in containers running compiled binaries |
| Keeping Python stubs alongside C++ servers | Maintaining both stub/ and real Dockerfile | Stubs drift from real API, cause confusion, violate architecture rules | Delete stubs once real servers exist — single source of truth |

## Results & Parameters

```yaml
# Healthcheck pattern for C++ containers
healthcheck_pattern: "wget -qO- http://localhost:${PORT}/v1/health 2>/dev/null || exit 1"
requires_in_runtime: wget  # apt-get install --no-install-recommends wget

# Files changed
compose_file: docker-compose.e2e.yml
deleted: control/ProjectNestor/stub/  # Python FastAPI stub

# Environment variables to verify match between stub and C++ server
env_vars:
  - NATS_URL     # Both stub and C++ read this
  - PORT         # Agamemnon default 8080
  - NESTOR_PORT  # Nestor default 8081
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | E2E compose migration | Agamemnon and Nestor services migrated from Python stubs to C++ Dockerfiles |
