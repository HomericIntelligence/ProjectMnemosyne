---
name: debugging-radiance-graph-load-capture-browser-api-artifacts
description: "Debug Radiance graph-load hangs by correlating the browser console, `/api/v1/radiance/runs*` endpoints, and persisted run artifacts. Use when: (1) the UI spinner hangs after Analyze/Open, (2) a run reaches `succeeded` but the graph does not render, (3) you need to separate backend graph generation failures from frontend Model Explorer rendering failures."
category: debugging
date: 2026-04-13
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - radiance
  - model-explorer
  - graph-debugging
  - flask
  - podman
---

# Debug Radiance Graph Load Hangs via Browser, API, and Artifacts

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-13 |
| **Objective** | Isolate where a Radiance graph-load hang occurs: browser rendering, API transport, or persisted run artifact generation |
| **Outcome** | Success — identified the minimum debug bundle needed to localize hangs without guessing |
| **Verification** | verified-local |
| **Project** | Radiance local appliance on `http://127.0.0.1:8080` |

## When to Use

- The Radiance UI hangs after `Analyze` or `Open`
- A run is marked `succeeded` but no graph appears in Model Explorer
- You need to distinguish a bad `graphCollections.json` payload from a frontend rendering problem
- You are debugging a local Podman appliance and need the exact persisted graph artifacts for a run

## Verified Workflow

### Quick Reference

```bash
# 1. Confirm the backend sees runs
curl -i http://127.0.0.1:8080/api/v1/radiance/runs

# 2. Resolve the latest run id and inspect status
RUN_ID=$(curl -sS http://127.0.0.1:8080/api/v1/radiance/runs \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["runs"][0]["runId"])')
curl -i "http://127.0.0.1:8080/api/v1/radiance/runs/$RUN_ID"

# 3. Check whether the graph endpoint returns data or errors
curl -i "http://127.0.0.1:8080/api/v1/radiance/runs/$RUN_ID/graph"

# 4. If running in Podman, inspect the persisted graph artifacts in the container
CID=$(podman ps -q | head -n1)
podman exec "$CID" sh -lc "ls -lh /radiance/runs/$RUN_ID/graphs"
podman exec "$CID" sh -lc "wc -c /radiance/runs/$RUN_ID/graphs/graphCollections.json"
podman exec "$CID" sh -lc "head -n 40 /radiance/runs/$RUN_ID/run_manifest.json"
```

### Detailed Steps

1. **Capture the browser failure point first**. In DevTools for `http://127.0.0.1:8080`, reproduce the hang and collect:
   - the first red `Console` error or stack trace
   - the `Network` entry for `GET /api/v1/radiance/runs/<run_id>/graph`
   - the response status, timing, and body if it is not `200`

2. **Check run discovery before looking at graph payloads**. Use `GET /api/v1/radiance/runs` to confirm the backend has a run entry at all. If the run is missing here, the problem is earlier than rendering.

3. **Inspect the specific run status**. Use `GET /api/v1/radiance/runs/<run_id>` and look at:
   - `status`
   - `graphReady`
   - `statusMessage`
   If `status != succeeded` or `graphReady != true`, the hang is not a frontend-only problem.

4. **Inspect the graph endpoint directly**. Use `GET /api/v1/radiance/runs/<run_id>/graph`. This separates:
   - backend graph-serialization failures
   - oversized or malformed JSON payloads
   - frontend-only rendering issues where the endpoint still returns `200`

5. **Inspect persisted artifacts, not just HTTP state**. For containerized runs, inspect `/radiance/runs/<run_id>/graphs` from inside the running container. Minimum files to verify:
   - `graphCollections.json`
   - `graph_manifest.json`
   - `nodes.jsonl`
   - `edges.jsonl`
   - `values.jsonl`
   Also inspect `run_manifest.json` in the run root.

6. **Use artifact size as a fast signal**. A non-trivial `graphCollections.json` confirms translation happened. If the file is missing, empty, or far smaller than expected, debug backend graph translation before investigating the frontend.

7. **Always correlate all three layers**:
   - browser console/network
   - Flask API responses
   - persisted run files
   Looking at only one of them leaves too much ambiguity.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Generic log request | Asking for “the logs” without specifying browser/API/artifacts | Mixed together frontend, backend, and container signals with no way to localize the fault | Ask for a structured debug bundle, not generic logs |
| Server stdout only | Looking only at the terminal running the webserver | A clean server log does not prove that `graphCollections.json` exists or that the browser consumed it correctly | Always pair stdout with direct API and artifact checks |
| Runs list only | Checking `GET /api/v1/radiance/runs` and stopping there | Confirms run discovery, but does not prove graph payload generation or renderability | `runs` must be followed by `runs/<run_id>` and `runs/<run_id>/graph` |

## Results & Parameters

### Verified Local Signals

The workflow was validated against a live local Radiance server on `http://127.0.0.1:8080`:

- `GET /api/v1/radiance/runs` returned `200 OK` with succeeded runs
- `GET /api/v1/radiance/jobs` returned `200 OK`
- `GET /api/v1/radiance/runs/<run_id>` returned `200 OK` with `graphReady: true`
- `GET /api/v1/radiance/runs/<run_id>/graph` returned `200 OK`
- The persisted run directory contained:
  - `graphs/graphCollections.json`
  - `graphs/graph_manifest.json`
  - `graphs/nodes.jsonl`
  - `graphs/edges.jsonl`
  - `graphs/values.jsonl`
  - `graphs/source_graph.json`

### Expected Artifact Paths

For a run id `run-<id>`:

```text
/radiance/runs/run-<id>/run_manifest.json
/radiance/runs/run-<id>/graphs/graphCollections.json
/radiance/runs/run-<id>/graphs/graph_manifest.json
/radiance/runs/run-<id>/graphs/nodes.jsonl
/radiance/runs/run-<id>/graphs/edges.jsonl
/radiance/runs/run-<id>/graphs/values.jsonl
/radiance/runs/run-<id>/graphs/source_graph.json
```

### Minimum Debug Bundle To Request

When someone reports a graph hang, ask for exactly this:

1. Browser `Console` error and `Network` details for `GET /api/v1/radiance/runs/<run_id>/graph`
2. Server stdout/stderr from the moment they click `Analyze` or `Open`
3. `curl -i` output for:
   - `/api/v1/radiance/runs`
   - `/api/v1/radiance/runs/<run_id>`
   - `/api/v1/radiance/runs/<run_id>/graph`
4. `ls -lh` and file size for `/radiance/runs/<run_id>/graphs/graphCollections.json`

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Radiance | Local appliance debugging on 2026-04-13 | Verified live `runs`, `jobs`, `run`, and `run graph` endpoints plus persisted graph artifact layout inside the running Podman container |
