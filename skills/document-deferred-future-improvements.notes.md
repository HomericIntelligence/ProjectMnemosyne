# Raw Notes — document-deferred-future-improvements (issue-881)

## Session Context

- **Date**: 2026-02-22
- **Branch**: `881-auto-impl` in ProjectScylla
- **Working directory**: `/home/mvillmow/ProjectScylla/.worktrees/issue-881`

## What Was Done

1. Read `.claude-prompt-881.md` — issue asked to add deferral notes to four Future Improvements items in `docs/design/container-architecture.md`
2. Read `docs/design/container-architecture.md` — confirmed four bare bullet items at end of file
3. Read `docker/Dockerfile` — confirmed:
   - `FROM` uses SHA256 digest pinned to x86_64 (ARM64 not supported)
   - Source + deps copied together before `pip install` (layer caching blocked)
   - No resource limit flags present
   - HEALTHCHECK **is** implemented at lines 116–117
4. Read `scripts/run_experiment_in_container.sh` — confirmed:
   - No `--memory`, `--cpus`, `--memory-swap` flags in `docker run` command
   - Bind mounts used (not named volumes)
5. Edited the Future Improvements section with structured entries
6. Committed, pushed, created PR #990 with auto-merge

## Key Implementation Details

### Structure used for each item

```markdown
N. **Name**: Short description.

   - **Status**: Deferred (not implemented)
   - **Why deferred**: [concrete reason referencing actual code]
   - **Acceptance criteria**: [measurable conditions]
```

### Evidence found in Dockerfile

```dockerfile
# Line 14 — architecture-specific digest
FROM python:3.14.2-slim@sha256:1a3c6dbfd2173971abba880c3cc2ec4643690901f6ad6742d0827bae6cefc925 AS builder

# Lines 33-37 — source + deps copied together (layer caching problem)
COPY pyproject.toml /opt/scylla/
COPY README.md /opt/scylla/
COPY scylla/ /opt/scylla/scylla/
RUN pip install --user --no-cache-dir /opt/scylla/

# Lines 116-117 — HEALTHCHECK implemented
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c 'import scylla; print("OK")' || exit 1
```

### Evidence found in wrapper script

```bash
# No --memory, --cpus flags
DOCKER_CMD=(
    docker run
    --rm
    --workdir /workspace
    "${VOLUMES[@]}"    # bind mounts, not named volumes
    "${ENV_VARS[@]}"
    "${IMAGE_NAME}"
    python scripts/run_e2e_experiment.py
    "$@"
)
```

## Pre-commit Hook Results

All hooks passed without issues:
- Markdown Lint: Passed
- Trim Trailing Whitespace: Passed
- Fix End of Files: Passed
- Check for Large Files: Passed
- Fix Mixed Line Endings: Passed

(Python hooks were skipped — no Python files changed)
