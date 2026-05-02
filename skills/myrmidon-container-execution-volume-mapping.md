---
name: myrmidon-container-execution-volume-mapping
description: "Replace bare subprocess.run(['claude', ...]) with containerized execution
  via achaean-claude image. Use when: (1) claude-myrmidon NATS pipeline invokes claude
  CLI directly on host, (2) agent processes need container isolation with proper volume
  mappings, (3) migrating host-based CLI invocations to ephemeral Docker/Podman containers
  with network access to NATS, (4) debugging why Claude CLI loops retrying inside a
  container, (5) NATS connection drops after a long container subprocess invocation,
  (6) --resume fails with 'No conversation found' across ephemeral containers."
category: architecture
date: "2026-04-05"
version: "2.0.0"
user-invocable: false
verification: verified-local
tags:
  - myrmidon
  - container
  - podman
  - docker
  - claude-cli
  - achaean-fleet
  - volume-mapping
  - pipeline
  - asyncio
  - nats
  - session-resume
  - ephemeral-container
---
# Myrmidon Container Execution & Volume Mapping

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-05 |
| **Objective** | Replace bare `subprocess.run(["claude", ...])` in the claude-myrmidon NATS pipeline with containerized execution using the `achaean-claude` image from AchaeanFleet |
| **Outcome** | SUCCESS — agents run inside ephemeral `achaean-claude:latest` containers with proper volume mappings, network access to NATS, and configurable container runtime |
| **Verification** | verified-local (pipeline progressed past planner stage with Docker + all fixes applied) |

## When to Use

- The claude-myrmidon NATS pipeline worker calls `subprocess.run(["claude", "-p", ...])` directly on the host
- Any agent invocation that runs `claude` CLI without container isolation
- Need to ensure agents run inside the `achaean-claude` container (built from `infrastructure/AchaeanFleet/vessels/claude/Dockerfile`)
- Migrating from host-based CLI execution to ephemeral Docker/Podman containers with `--rm`
- Agent process needs access to NATS running on the default bridge network (not a named compose network)
- Claude CLI loops retrying indefinitely inside the container and you suspect a missing config file
- NATS connection drops mid-pipeline with `TimeoutError` after a long container run
- `--resume <session_id>` returns empty output on every iteration > 0 of a test/implement/review loop

## Verified Workflow

### Quick Reference

```bash
# BEFORE (wrong — runs claude directly on host, no isolation):
subprocess.run(["claude", "-p", prompt], cwd=working_dir, ...)

# AFTER (correct — runs inside ephemeral achaean-claude container, async-safe):
# NOTE: Use asyncio.to_thread() so the NATS event loop keeps processing pings
async def invoke_claude(prompt: str, working_dir: str) -> str:
    def _sync() -> str:
        return _invoke_claude_sync(prompt, working_dir)
    return await asyncio.to_thread(_sync)

def _invoke_claude_sync(prompt: str, working_dir: str) -> str:
    runtime = os.environ.get("CONTAINER_RUNTIME", "docker")
    home = os.path.expanduser("~")
    api_key = os.environ["ANTHROPIC_API_KEY"]
    network = os.environ.get("CONTAINER_NETWORK", "host")

    cmd = [
        runtime, "run", "--rm",
        # Volume mappings — BOTH paths required
        "-v", f"{working_dir}:/workspace",
        "-v", f"{home}/.claude.json:{home}/.claude.json",  # config file (separate from dir!)
        "-v", f"{home}/.claude:{home}/.claude",            # session directory
        "-w", "/workspace",
        "-e", f"ANTHROPIC_API_KEY={api_key}",
        "-e", f"HOME={home}",
        "--network", network,
        "achaean-claude:latest",
        "claude", "-p", prompt,
        # NEVER use --resume with ephemeral containers (see Failed Attempts)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return result.stdout
```

### Step-by-Step Migration

1. **Identify the bare subprocess call** in the myrmidon pipeline worker:

   ```python
   # Look for this pattern:
   result = subprocess.run(
       ["claude", "-p", prompt],
       cwd=working_dir,
       capture_output=True,
       text=True,
   )
   ```

2. **Determine the container runtime** — default to `docker` when podman rootless is unavailable (e.g., WSL2 without runc):

   ```python
   import os
   runtime = os.environ.get("CONTAINER_RUNTIME", "docker")
   network = os.environ.get("CONTAINER_NETWORK", "host")
   ```

3. **Build the container command** with all required flags, including BOTH config paths:

   ```python
   home = os.path.expanduser("~")
   api_key = os.environ["ANTHROPIC_API_KEY"]

   cmd = [
       runtime, "run", "--rm",
       # Volume mappings
       "-v", f"{working_dir}:/workspace",             # Host working dir -> container /workspace
       "-v", f"{home}/.claude.json:{home}/.claude.json",  # Claude config FILE (critical!)
       "-v", f"{home}/.claude:{home}/.claude",        # Claude session directory
       # Working directory inside container
       "-w", "/workspace",
       # Environment variables
       "-e", f"ANTHROPIC_API_KEY={api_key}",
       "-e", f"HOME={home}",
       # Network — use "host" when NATS is on default bridge, not a named compose network
       "--network", network,
       # Image
       "achaean-claude:latest",
       # Command — no --resume (see Failed Attempts)
       "claude", "-p", prompt,
   ]
   ```

4. **Wrap in asyncio.to_thread()** so the NATS event loop keeps processing pings during the long-running subprocess:

   ```python
   import asyncio

   async def invoke_claude_async(prompt: str, working_dir: str) -> str:
       """Run blocking container subprocess without starving the NATS event loop."""
       def _sync():
           result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
           return result.stdout
       return await asyncio.to_thread(_sync)
   ```

5. **Replace the subprocess call** — remove `cwd` since `-w /workspace` handles it:

   ```python
   output = await invoke_claude_async(prompt, working_dir)
   ```

6. **Verify** — run a dry-run test to confirm both config paths are accessible and NATS is reachable:

   ```bash
   docker run --rm \
     -v "$(pwd):/workspace" \
     -v "$HOME/.claude.json:$HOME/.claude.json" \
     -v "$HOME/.claude:$HOME/.claude" \
     -w /workspace \
     -e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" \
     -e "HOME=$HOME" \
     --network host \
     achaean-claude:latest \
     claude --version
   ```

### Volume Mapping Reference

| Flag | Host Path | Container Path | Purpose |
| ------ | ----------- | ---------------- | --------- |
| `-v WORKING_DIR:/workspace` | Host working directory | `/workspace` | Maps project files into container |
| `-v ~/.claude.json:~/.claude.json` | `$HOME/.claude.json` | `$HOME/.claude.json` (same path) | **Claude config FILE** — missing this causes infinite retry loop |
| `-v ~/.claude:~/.claude` | `$HOME/.claude` | `$HOME/.claude` (same path) | Claude session directory |
| `-w /workspace` | n/a | `/workspace` | Sets container working directory |

**Critical**: `~/.claude.json` and `~/.claude/` are two separate paths. Mounting only the directory is insufficient — the CLI will not find its config and will loop retrying until the timeout (600s).

### Environment Variable Reference

| Variable | Required | Purpose |
| ---------- | ---------- | --------- |
| `ANTHROPIC_API_KEY` | Yes | API authentication for claude CLI |
| `HOME` | Yes | So claude finds its config at `~/.claude` inside the container |
| `CONTAINER_RUNTIME` | No (default: `docker`) | Override container runtime (`podman` or `docker`); podman rootless may fail on WSL2 without runc |
| `CONTAINER_NETWORK` | No (default: `host`) | Override network; use `homeric-mesh` only if NATS is on that named compose network |

### Network Configuration

Use `--network host` when NATS is started with plain `docker run` (default bridge network). Use `--network homeric-mesh` only when NATS was launched via Docker Compose on that named network.

Hardcoding `--network homeric-mesh` when NATS is on the default bridge causes immediate `nats.errors.NoServersError`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `claude` directly on host | `subprocess.run(["claude", "-p", prompt], cwd=working_dir)` | Breaks container isolation — agents run on bare host with no network segmentation, no resource limits, and direct filesystem access | Agents must always run inside the `achaean-claude` container from AchaeanFleet |
| Using `docker exec` on a running container | Attempted to exec into a long-lived container for each invocation | Wrong pattern — the myrmidon pipeline creates ephemeral containers per invocation with `--rm`, not a persistent container | Use `docker run --rm` for ephemeral per-invocation containers, not `docker exec` on a running instance |
| Missing `~/.claude.json` mount | Only mounted `~/.claude/` directory but not `~/.claude.json` config file | Claude CLI couldn't find its config and looped retrying until the 600s timeout expired — produced no output, pipeline stalled | Always mount BOTH `-v "$HOME/.claude.json:$HOME/.claude.json"` AND `-v "$HOME/.claude:$HOME/.claude"`. They are separate paths. |
| Using `--resume` across ephemeral containers | Used `--resume <session_id>` for iteration > 0 in the test/implement/review loop | Each `docker run --rm` creates a fresh container — session state is not persistent even with `~/.claude/` volume-mounted. Every `--resume` call failed with "No conversation found with session ID", causing every iteration after the first to return empty output | Never use `--resume` with ephemeral containers. Start fresh sessions with full context embedded in the prompt for each invocation. |
| Blocking `subprocess.run()` in async NATS handler | Called `subprocess.run(cmd, ...)` directly inside an `async def` message handler | `subprocess.run()` blocks the Python thread for 5-10 minutes. The asyncio event loop cannot process NATS pings during this time. When the subprocess finishes and tries to publish results, NATS throws `TimeoutError` (connection dropped due to missed pings). | Wrap blocking subprocess calls in `await asyncio.to_thread(_invoke_claude_sync, cmd)` so the async NATS event loop keeps running. |
| Hardcoded `--network homeric-mesh` | Container started with `--network homeric-mesh` but NATS was on the default `bridge` network | NATS was started with plain `docker run`, not via compose, so it was not on `homeric-mesh`. Container could not reach NATS at all. | Default to `--network host` or make it configurable via `CONTAINER_NETWORK` env var. Use `homeric-mesh` only when NATS was started via Docker Compose on that explicit network. |
| Podman rootless on WSL2 | Used `CONTAINER_RUNTIME=podman` on a WSL2 host without runc installed | Podman rootless failed immediately: `Error: rootless netns: mount /proc/self/exe ... runc not found`. runc is not pre-installed in many WSL2 distributions. | Default `CONTAINER_RUNTIME` to `docker` on WSL2 hosts. Fall back to podman only when explicitly configured and runc is confirmed available. |

## Results & Parameters

### Container Image

| Parameter | Value |
| ----------- | ------- |
| Image name | `achaean-claude:latest` |
| Dockerfile | `infrastructure/AchaeanFleet/vessels/claude/Dockerfile` |
| Lifecycle | Ephemeral (`--rm`) — created per invocation, destroyed after completion |
| Network | `host` (default) or configurable via `CONTAINER_NETWORK` env var |
| Runtime | Configurable via `CONTAINER_RUNTIME` env var (default: `docker`; podman requires runc) |
| Claude CLI version | 2.1.92 (verified) |

### Complete Command Template

```python
import asyncio
import os
import subprocess

def _invoke_claude_sync(prompt: str, working_dir: str) -> str:
    """Synchronous claude container invocation — call via asyncio.to_thread()."""
    runtime = os.environ.get("CONTAINER_RUNTIME", "docker")
    network = os.environ.get("CONTAINER_NETWORK", "host")
    home = os.path.expanduser("~")
    api_key = os.environ["ANTHROPIC_API_KEY"]

    cmd = [
        runtime, "run", "--rm",
        # Volume mappings — mount BOTH config file and session directory
        "-v", f"{working_dir}:/workspace",
        "-v", f"{home}/.claude.json:{home}/.claude.json",
        "-v", f"{home}/.claude:{home}/.claude",
        # Working directory
        "-w", "/workspace",
        # Environment
        "-e", f"ANTHROPIC_API_KEY={api_key}",
        "-e", f"HOME={home}",
        # Network
        "--network", network,
        # Image and command
        "achaean-claude:latest",
        "claude", "-p", prompt,
        # NOTE: no --resume; ephemeral containers don't preserve session state
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"claude container failed: {result.stderr[:500]}")
    return result.stdout


async def invoke_claude(prompt: str, working_dir: str) -> str:
    """
    Async wrapper — runs blocking container subprocess in thread pool
    so the NATS event loop keeps processing pings/keepalives.
    """
    return await asyncio.to_thread(_invoke_claude_sync, prompt, working_dir)
```

### NATS Connection Parameters for Long-Running Pipelines

When the pipeline runs Claude inside containers (5-10 minutes per invocation), increase NATS ping tolerance:

```python
nc = await nats.connect(
    nats_url,
    max_outstanding_pings=10,  # allow 10 missed pings before disconnect
    ping_interval=30,           # ping every 30s (default is 120s)
)
```

This, combined with `asyncio.to_thread()`, prevents the NATS connection from dropping during long container runs.

### Key Differences from Host Execution

| Aspect | Host Execution (wrong) | Container Execution (correct) |
| -------- | ---------------------- | ------------------------------- |
| Isolation | None — full host access | Container namespace isolation |
| Network | Host network | Configurable via `CONTAINER_NETWORK` |
| Filesystem | Full host filesystem | Only mounted volumes |
| Lifecycle | Persistent process | Ephemeral `--rm` per invocation |
| `cwd` parameter | `subprocess.run(cwd=...)` | Removed — `-w /workspace` handles it |
| Claude config | Direct `~/.claude` access | Both `~/.claude.json` AND `~/.claude/` volume-mapped |
| Session resume | `--resume <id>` works | Never use `--resume` — embed full context in prompt |
| Async safety | Blocks event loop | Must use `asyncio.to_thread()` |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| claude-myrmidon | NATS pipeline worker (initial) | Replaced bare `subprocess.run(["claude", ...])` with containerized execution; syntax checked, dry-run tested |
| claude-myrmidon-multi.py | NATS multi-repo pipeline (full e2e) | All 4 pitfalls discovered and fixed; pipeline progressed past planner stage with Docker runtime on WSL2 |
