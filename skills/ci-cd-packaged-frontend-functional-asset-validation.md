---
name: ci-cd-packaged-frontend-functional-asset-validation
description: "Validate packaged frontend outputs functionally instead of diffing generated bundle names. Use when: (1) CI checks packaged web assets after a rebuild, (2) hashed bundle filenames make git diff gates brittle."
category: ci-cd
date: 2026-04-22
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [ci-cd, github-actions, frontend, packaging, validation]
---

# Packaged Frontend Functional Asset Validation

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-22 |
| **Objective** | Replace brittle packaged-asset drift checks with runtime validation of the shipped frontend surface. |
| **Outcome** | Successful locally. Rebuild the packaged frontend, serve it from the packaged directory, and verify all discovered local assets return `200`. |
| **Verification** | verified-local |

Verified locally only — CI validation was pending during capture.

## When to Use

- A workflow rebuilds packaged frontend assets and currently fails on `git diff --exit-code` because hashed bundle filenames change.
- You need to prove the packaged web app is actually servable instead of proving generated files stayed byte-for-byte stable.
- A repo vendors a built frontend into a Python or server package and wants CI to validate the shipped output surface.

## Verified Workflow

### Quick Reference

```bash
# 1. Rebuild packaged assets from the UI source tree
cd vendor/model_explorer/src/ui
npm ci
npm run deploy

# 2. Validate the packaged frontend runtime surface
cd /path/to/repo
python3 scripts/checks/validate_packaged_frontend.py
```

### Detailed Steps

1. Rebuild the packaged frontend exactly the way the repository ships it, not just the development bundle.
2. Serve the packaged `web_app` directory over a local loopback HTTP server inside the validator.
3. Fetch `index.html` and parse local `script`, `stylesheet`, `icon`, and preload URLs dynamically instead of hardcoding hashed filenames.
4. Fetch each discovered local asset and fail if any request is non-`200` or returns an empty body.
5. Parse CSS asset bodies for `url(...)` references and verify those local assets as well.
6. Run the validator from CI immediately after `npm run deploy` so the workflow proves the shipped package is internally consistent.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Hardcoded drift gate | Used `git diff --exit-code` after `npm run deploy` | Rebuilds legitimately changed hashed bundle names like `main-*.js`, which made CI fail even when the packaged app still worked | Generated filename drift is not a functional failure; validate runtime reachability instead |
| Narrow `index.html` diff inspection | Looked only at `index.html` script-tag rewrites | That explains why CI failed, but it does not prove the packaged frontend is healthy or complete | Turn diagnosis into an executable validator that checks all discovered local assets |
| Generic `urllib.request.urlopen` in validator | Used `urlopen()` for convenience in the functional validator | Bandit flagged it as `B310` because it accepts broader URL schemes than necessary | Keep the validator on an explicit trust boundary and fetch only loopback `http://127.0.0.1:<port>` assets |

## Results & Parameters

Recommended validator behavior:

```text
Input root: vendor/model_explorer/src/server/package/src/model_explorer/web_app
Server bind: 127.0.0.1 on ephemeral port
Accepted URLs: only http://127.0.0.1:<ephemeral>/...
Validation surface:
- index.html
- local script assets
- local stylesheet assets
- local icon/preload assets
- local CSS url(...) assets
Failure conditions:
- non-200 response
- empty response body
- no local assets discovered in index.html
```

Observed useful command sequence:

```bash
npm run deploy
python3 scripts/checks/validate_packaged_frontend.py
bandit -q -r radiance scripts --severity-level medium --confidence-level medium
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Radiance | PR #110 CI remediation | Replaced the packaged frontend `git diff` gate with a runtime asset validator and confirmed it locally before pushing |
