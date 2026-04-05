---
name: myrmidon-container-execution-volume-mapping
description: "Replace bare subprocess.run(['claude', ...]) with containerized execution
  via achaean-claude image. Use when: (1) claude-myrmidon NATS pipeline invokes claude
  CLI directly on host, (2) agent processes need container isolation with proper volume
  mappings, (3) migrating host-based CLI invocations to ephemeral Podman containers
  with network access to NATS."
category: architecture
date: "2026-04-05"
version: "1.0.0"
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
---
# Myrmidon Container Execution & Volume Mapping

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Objective** | Replace bare `subprocess.run(["claude", ...])` in the claude-myrmidon NATS pipeline with containerized execution using the `achaean-claude` image from AchaeanFleet |
| **Outcome** | SUCCESS — agents run inside ephemeral `achaean-claude:latest` containers with proper volume mappings, network access to NATS, and configurable container runtime |
| **Verification** | verified-local (syntax checked, dry-run tested) |

## When to Use

- The claude-myrmidon NATS pipeline worker calls `subprocess.run(["claude", "-p", ...])` directly on the host
- Any agent invocation that runs `claude` CLI without container isolation
- Need to ensure agents run inside the `achaean-claude` container (built from `infrastructure/AchaeanFleet/vessels/claude/Dockerfile`)
- Migrating from host-based CLI execution to ephemeral Podman/Docker containers with `--rm`
- Agent process needs access to NATS via the `homeric-mesh` container network
- Claude session data at `~/.claude` must be shared between host and container for session reuse

## Verified Workflow

### Quick Reference

```bash
# BEFORE (wrong — runs claude directly on host, no isolation):
subprocess.run(["claude", "-p", prompt], cwd=working_dir, ...)

# AFTER (correct — runs inside ephemeral achaean-claude container):
subprocess.run([
    runtime,           # "podman" or "docker" (from CONTAINER_RUNTIME env var)
    "run", "--rm",
    "-v", f"{working_dir}:/workspace",
    "-v", f"{home}/.claude:{home}/.claude",
    "-w", "/workspace",
    "-e", f"ANTHROPIC_API_KEY={api_key}",
    "-e", f"HOME={home}",
    "--network", "homeric-mesh",
    "achaean-claude:latest",
    "claude", "-p", prompt
], ...)
# NOTE: cwd parameter on subprocess.run() is removed — the container's -w flag handles it
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

2. **Determine the container runtime** — default to `podman`, allow override via environment variable:

   ```python
   import os
   runtime = os.environ.get("CONTAINER_RUNTIME", "podman")
   ```

3. **Build the container command** with all required flags:

   ```python
   home = os.path.expanduser("~")
   api_key = os.environ["ANTHROPIC_API_KEY"]

   cmd = [
       runtime, "run", "--rm",
       # Volume mappings
       "-v", f"{working_dir}:/workspace",       # Host working dir -> container /workspace
       "-v", f"{home}/.claude:{home}/.claude",   # Claude config/session for reuse
       # Working directory inside container
       "-w", "/workspace",
       # Environment variables
       "-e", f"ANTHROPIC_API_KEY={api_key}",
       "-e", f"HOME={home}",
       # Network (so container can reach NATS)
       "--network", "homeric-mesh",
       # Image
       "achaean-claude:latest",
       # Command
       "claude", "-p", prompt,
   ]
   ```

4. **Replace the subprocess call** — remove `cwd` since `-w /workspace` handles it:

   ```python
   result = subprocess.run(
       cmd,
       capture_output=True,
       text=True,
   )
   ```

5. **Verify** — run a dry-run test to confirm the container starts, mounts volumes, and reaches NATS:

   ```bash
   podman run --rm \
     -v "$(pwd):/workspace" \
     -v "$HOME/.claude:$HOME/.claude" \
     -w /workspace \
     -e "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" \
     -e "HOME=$HOME" \
     --network homeric-mesh \
     achaean-claude:latest \
     claude --version
   ```

### Volume Mapping Reference

| Flag | Host Path | Container Path | Purpose |
|------|-----------|----------------|---------|
| `-v WORKING_DIR:/workspace` | Host working directory | `/workspace` | Maps project files into container |
| `-v ~/.claude:~/.claude` | `$HOME/.claude` | `$HOME/.claude` (same path) | Claude config and session data for session reuse |
| `-w /workspace` | n/a | `/workspace` | Sets container working directory |

### Environment Variable Reference

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | Yes | API authentication for claude CLI |
| `HOME` | Yes | So claude finds its config at `~/.claude` inside the container |
| `CONTAINER_RUNTIME` | No (default: `podman`) | Override container runtime (`podman` or `docker`) |

### Network Configuration

The `--network homeric-mesh` flag connects the ephemeral container to the shared Podman network so the agent can communicate with NATS and other services in the HomericIntelligence mesh. Without this flag, the container runs in an isolated network namespace and cannot reach NATS.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Running `claude` directly on host | `subprocess.run(["claude", "-p", prompt], cwd=working_dir)` | Breaks container isolation — agents run on bare host with no network segmentation, no resource limits, and direct filesystem access | Agents must always run inside the `achaean-claude` container from AchaeanFleet |
| Using `docker exec` on a running container | Attempted to exec into a long-lived container for each invocation | Wrong pattern — the myrmidon pipeline creates ephemeral containers per invocation with `--rm`, not a persistent container | Use `podman run --rm` for ephemeral per-invocation containers, not `docker exec` on a running instance |

## Results & Parameters

### Container Image

| Parameter | Value |
|-----------|-------|
| Image name | `achaean-claude:latest` |
| Dockerfile | `infrastructure/AchaeanFleet/vessels/claude/Dockerfile` |
| Lifecycle | Ephemeral (`--rm`) — created per invocation, destroyed after completion |
| Network | `homeric-mesh` (shared Podman network for NATS access) |
| Runtime | Configurable via `CONTAINER_RUNTIME` env var (default: `podman`) |

### Complete Command Template

```python
import os
import subprocess

def run_claude_in_container(
    prompt: str,
    working_dir: str,
) -> subprocess.CompletedProcess:
    """Run claude CLI inside an ephemeral achaean-claude container."""
    runtime = os.environ.get("CONTAINER_RUNTIME", "podman")
    home = os.path.expanduser("~")
    api_key = os.environ["ANTHROPIC_API_KEY"]

    cmd = [
        runtime, "run", "--rm",
        "-v", f"{working_dir}:/workspace",
        "-v", f"{home}/.claude:{home}/.claude",
        "-w", "/workspace",
        "-e", f"ANTHROPIC_API_KEY={api_key}",
        "-e", f"HOME={home}",
        "--network", "homeric-mesh",
        "achaean-claude:latest",
        "claude", "-p", prompt,
    ]

    return subprocess.run(cmd, capture_output=True, text=True)
```

### Key Differences from Host Execution

| Aspect | Host Execution (wrong) | Container Execution (correct) |
|--------|----------------------|-------------------------------|
| Isolation | None — full host access | Container namespace isolation |
| Network | Host network | `homeric-mesh` only |
| Filesystem | Full host filesystem | Only mounted volumes |
| Lifecycle | Persistent process | Ephemeral `--rm` per invocation |
| `cwd` parameter | `subprocess.run(cwd=...)` | Removed — `-w /workspace` handles it |
| Claude config | Direct `~/.claude` access | Volume-mapped `~/.claude` |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| claude-myrmidon | NATS pipeline worker | Replaced bare `subprocess.run(["claude", ...])` with containerized execution; syntax checked, dry-run tested |
