---
name: radiance-headless-graph-existing-pipeline-json-validation
description: "Build a headless Radiance graph export CLI by reusing the existing run/artifact pipeline. Use when: (1) validating model graph output without the web UI, (2) adding CLI coverage to a browser-first analysis app, (3) exporting Model Explorer graphCollections or raw source graph JSON for tests."
category: tooling
date: 2026-04-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - radiance
  - cli
  - headless
  - graph-export
  - testing
---

# Radiance Headless Graph Export CLI Using Existing Pipeline

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-29 |
| **Objective** | Add a non-browser validation path that can download or resolve a model, run Radiance analysis, and emit graph JSON. |
| **Outcome** | Successful local implementation: `radiance-graph` console script, reusable `radiance.headless` helper, tests for local/Hugging Face/stdout flows, and README usage. |
| **Verification** | verified-local — focused tests, Ruff, CLI help, and `make check` passed locally; CI validation pending. |

## When to Use

- A browser-first analysis tool needs a CLI path for automated validation.
- You need to test model graph generation without Model Explorer or a Flask server.
- You want JSON outputs that can be diffed in tests, CI, or fixture generation.
- The application already has a run service that persists graph artifacts, metrics, and run manifests.
- A known runtime execution gap exists, so the safe CLI default should be structural analysis until runtime mode is fixed.

## Verified Workflow

### Quick Reference

```bash
# Add the console script
# pyproject.toml
[project.scripts]
radiance-appliance = "radiance.server.app:main"
radiance-graph = "radiance.cli:main"

# Typical user commands
radiance-graph sshleifer/tiny-gpt2 --source-kind hugging-face > graphCollections.json
radiance-graph ./models/my-checkpoint --source-kind local --output graphCollections.json
radiance-graph sshleifer/tiny-gpt2 --source-kind hugging-face \
  --output-format source-graph -o graph.json

# Local verification
.venv/bin/ruff check radiance/headless.py radiance/cli.py tests/backend/test_headless_cli.py
.venv/bin/pytest -q tests/backend/test_headless_cli.py
make check
```

### Detailed Steps

1. Start with tests for the CLI behavior, not the implementation. Cover:
   - local path source resolution
   - Hugging Face source setup with the snapshot downloader faked
   - missing local path errors
   - CLI stdout JSON shape

2. Build a reusable headless module instead of putting all logic in `argparse`.
   In Radiance this became `radiance/headless.py` with:
   - `HeadlessGraphOptions`
   - `HeadlessGraphResult`
   - `HeadlessSourceKind`
   - `GraphOutputFormat`
   - `run_headless_graph(...)`

3. Reuse the existing artifact pipeline. The key implementation was:
   - create a `SourceRegistry` in the configured runtime cache
   - register the model source as a normal `SourceRegistryEntry`
   - instantiate `TheoreticalRunService(..., max_workers=1)`
   - call `start_run(...)`
   - poll `get_run(run_id)` until terminal state
   - read outputs from the persisted run root or service helpers

4. For local paths outside the configured models root, do not copy files. Instead, set a run-local `RuntimePaths.models_dir` to the source parent and use the basename as `mounted_subpath`. This preserves the same mounted-path contract while letting the CLI accept arbitrary local checkpoint paths.

5. For Hugging Face sources, create the source through the same helper as the UI:
   `create_huggingface_model_source(...)`. Only call full snapshot download with `allow_patterns=None` when the user passes `--download-weights`; otherwise metadata-only behavior should remain the default.

6. Default the CLI to `structural_only` analysis. In Radiance, runtime mode was known to be misleading until the runtime orchestration gap was fixed, so the CLI default avoided locking tests to a broken runtime claim.

7. Offer output formats that map to persisted artifacts:
   - `graph-collections`: `service.get_graph_collections(run_id)`
   - `source-graph`: `graphs/operators/source_graph.json`
   - `run-summary`: the run status payload

8. Register a small `argparse` entrypoint in `radiance/cli.py`. Keep JSON writing centralized so `stdout` and `--output <path>` use the same payload.

9. After adding a new console script, refresh a local editable install before manually testing `.venv/bin/<script>`:

   ```bash
   .venv/bin/python -m pip install -e . --no-deps
   .venv/bin/radiance-graph --help
   ```

10. Document the command in the README with examples for local paths, Hugging Face repos, full weight download, and raw source graph output.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Build a parallel analyzer | Considered adding a CLI that directly calls graph extraction and serializes the result | That would bypass run manifests, graphCollections translation, metrics, and persisted artifact behavior used by the UI | Reuse `TheoreticalRunService` so CLI validation exercises the same pipeline as the browser |
| Assume raw graph JSON is camelCase | Test expected `nodes[0]["opName"]` in `source-graph` output | The raw dataclass artifact is persisted as snake_case (`op_name`); camelCase labels exist in graphCollections | Distinguish raw internal artifacts from Model Explorer graphCollections payloads |
| Manually test new console script before reinstall | Ran `.venv/bin/radiance-graph --help` after editing `pyproject.toml` | Existing editable install did not yet expose the new console entrypoint | Run `pip install -e . --no-deps` after adding a script entry |
| Default to runtime mode | Letting the CLI default to `runtime_with_weights` looked attractive for coverage | Radiance had an open runtime orchestration blocker, so runtime mode could imply execution that did not happen | Default to `structural_only`; expose runtime mode only as an explicit flag |

## Results & Parameters

### Files Added Or Changed In Radiance

```text
radiance/headless.py
radiance/cli.py
tests/backend/test_headless_cli.py
pyproject.toml
README.md
```

### Command Surface

```bash
radiance-graph [-h]
  [--source-kind {auto,local,hugging-face}]
  [--revision REVISION]
  [--trust-remote-code]
  [--download-weights]
  [--analysis-mode {structural_only,runtime_with_weights}]
  [--output-format {graph-collections,source-graph,run-summary}]
  [--output OUTPUT]
  [--hardware-id HARDWARE_ID]
  [--timeout-seconds TIMEOUT_SECONDS]
  [--models-dir MODELS_DIR]
  [--runs-dir RUNS_DIR]
  [--cache-dir CACHE_DIR]
  [--uploads-dir UPLOADS_DIR]
  [--access-token-env ACCESS_TOKEN_ENV]
  source
```

### Observed Local Verification

```text
.venv/bin/pytest -q tests/backend/test_headless_cli.py
4 passed in 0.21s

.venv/bin/pytest -q tests/backend/test_headless_cli.py tests/backend/test_app_entrypoint.py tests/backend/test_theoretical_runs.py
9 passed in 0.41s

make check
218 passed, 4 skipped in 4.74s
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Radiance | Added `radiance-graph` after strict audit identified the need to validate graph output without a browser | Verified locally with focused tests, Ruff, CLI help, editable install refresh, and full `make check` |
