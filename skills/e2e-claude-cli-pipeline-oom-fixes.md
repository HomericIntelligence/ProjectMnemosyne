---
name: e2e-claude-cli-pipeline-oom-fixes
description: "Fix OOM crashes in multi-stage Claude CLI pipelines orchestrated via NATS JetStream. Use when: (1) claude-myrmidon or similar NATS pipeline OOM-kills a WSL2/Linux host, (2) spawning multiple `claude -p` processes exhausts memory, (3) NATS JetStream messages grow unbounded across pipeline stages, (4) adding dry-run validation mode to a Claude CLI pipeline."
category: optimization
date: 2026-04-05
version: "1.0.0"
user-invocable: false
tags:
  - oom
  - nats
  - jetstream
  - claude-cli
  - myrmidon
  - pipeline
  - memory
  - dry-run
  - wsl2
  - docker-compose
---

# E2E Claude CLI Pipeline OOM Fixes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-05 |
| **Objective** | Fix OOM crash in claude-myrmidon NATS pipeline and add dry-run validation mode |
| **Outcome** | Pipeline stabilized with session reuse, payload pruning, NATS retention, and DRY_RUN mode. Dry-run completes in ~2s at flat 26.9 MB. |

## When to Use

- `claude-myrmidon.py` (or similar multi-stage NATS pipeline) OOM-kills a 16GB WSL2 system
- Each `claude -p` invocation consumes ~500MB-1GB RAM and the pipeline spawns many sessions per task
- NATS JetStream messages accumulate indefinitely, growing payload size across stages
- You need a dry-run mode to validate pipeline mechanics without invoking Claude CLI
- `subprocess.run()` calls to Claude CLI block on stdin (see also: `batch-subprocess-signal-hang` skill)

## Verified Workflow

### Quick Reference

```python
# 1. Session reuse: first invocation creates session, subsequent ones resume it
import uuid
session_id = str(uuid.uuid4())

# Iteration 0: create session
cmd_first = ["claude", "-p", prompt, "--session-id", session_id, "--output-format", "json"]
result = subprocess.run(cmd_first, capture_output=True, text=True, stdin=subprocess.DEVNULL)

# Iterations 1+: resume existing session (massive memory savings)
cmd_resume = ["claude", "-p", prompt, "--resume", session_id, "--output-format", "json"]
result = subprocess.run(cmd_resume, capture_output=True, text=True, stdin=subprocess.DEVNULL)

# 2. Always pass stdin=subprocess.DEVNULL to prevent blocking
subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)

# 3. Payload pruning between stages
def prune_task_data(task_data: dict, next_stage: str) -> dict:
    """Strip accumulated stage outputs, carry only core keys + what next stage needs."""
    core_keys = {"task_id", "repo", "issue", "branch"}
    stage_input_key = f"{next_stage}_input"
    pruned = {k: v for k, v in task_data.items() if k in core_keys}
    if stage_input_key in task_data:
        pruned[stage_input_key] = task_data[stage_input_key]
    return pruned

# 4. NATS stream retention policies
stream_config = {
    "name": "MYRMIDON",
    "subjects": ["myrmidon.>"],
    "max_age": 3600_000_000_000,  # 1 hour in nanoseconds
    "max_bytes": 50 * 1024 * 1024,  # 50 MB
    "retention": "limits",
}

# 5. Memory logging at each stage
import resource
def log_memory(stage: str):
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss_mb = usage.ru_maxrss / 1024  # Linux reports in KB
    print(f"[{stage}] RSS: {rss_mb:.1f} MB")

# 6. DRY_RUN mode
import os
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
if DRY_RUN:
    result = '{"mock": true, "stage": "plan", "output": "dry-run mock response"}'
else:
    result = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
```

### Step 1: Enable Session Reuse

Each `claude -p` process consumes ~500MB-1GB RAM. The pipeline spawns up to 16 sessions per task (1 plan + 5x test + 5x implement + 5x review + 1 ship). Session reuse via `--session-id` (first call) and `--resume` (subsequent calls) avoids spawning entirely new processes for each loop iteration.

### Step 2: Prevent Stdin Blocking

Always pass `stdin=subprocess.DEVNULL` on all `subprocess.run()` calls to Claude CLI. Without this, `capture_output=True` alone causes the subprocess to block waiting for stdin. This is a known pattern documented in the `batch-subprocess-signal-hang` skill.

### Step 3: Prune Payloads Between Stages

When passing task data through NATS between pipeline stages, do NOT use `{**task_data, "feedback": result}` dict unpacking. This carries ALL previous stage outputs, causing payload size to grow exponentially across iterations. Instead, use a `prune_task_data()` function that strips accumulated outputs and only carries core keys plus what the next stage actually needs.

### Step 4: Configure NATS Stream Retention

Set `max_age` (e.g., 3600s / 1 hour) and `max_bytes` (e.g., 50MB) on the JetStream stream. Without retention policies, messages accumulate indefinitely and compound the memory issue.

### Step 5: Fix NATS Connection Parameters

Set `max_reconnect_attempts` to a finite number (e.g., 3-5) instead of `-1`. The value `-1` in nats-py means unlimited retries during initial `connect()`, which hangs forever instead of failing fast when NATS is unreachable.

### Step 6: Add DRY_RUN Mode

Implement `DRY_RUN=1` environment variable that substitutes mock responses for all Claude CLI invocations. This validates the full pipeline mechanics (NATS publish/subscribe, stage transitions, payload handling) without consuming any memory for Claude processes. Use `resource.getrusage()` to confirm flat memory profile (~26.9 MB) in dry-run.

### Step 7: Set Container Memory Limits

In `docker-compose.yml`, set `mem_limit` per service (128-256M for lightweight services). This prevents any single container from consuming unbounded host memory.

```yaml
services:
  myrmidon-worker:
    mem_limit: 256m
  nats:
    mem_limit: 128m
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `--no-input` flag on Claude CLI | Passed `--no-input` to prevent interactive prompts | Flag does not exist on Claude CLI; caused all stages to produce empty output | Check `claude --help` for valid flags; use `stdin=subprocess.DEVNULL` instead |
| `capture_output=True` without `stdin=subprocess.DEVNULL` | Captured stdout/stderr but did not redirect stdin | Subprocess blocks waiting for stdin input indefinitely | Always pair `capture_output=True` with `stdin=subprocess.DEVNULL` for non-interactive CLI tools |
| `{**task_data, "feedback": result}` dict unpacking | Merged all previous stage data when publishing to next NATS subject | Carries ALL previous stage outputs; payload grows exponentially across 5 stages x 5 iterations | Always prune payloads between stages; only carry core keys + what the next stage needs |
| No NATS retention policies | Used default JetStream stream config without max_age or max_bytes | Messages accumulate indefinitely in JetStream, compounding memory pressure | Always set retention policies: max_age + max_bytes on every JetStream stream |
| `max_reconnect_attempts=-1` in nats-py | Set unlimited reconnect attempts for resilience | `-1` means unlimited retries during initial `connect()`, hangs forever when NATS is down | Use finite retry count (3-5) for initial connect; unlimited retries are only safe for established connections |

## Results & Parameters

### Resource Profile

```yaml
# Per-process memory footprint
claude_cli_per_process: "500MB - 1GB"
pipeline_stages_per_task: 16  # 1 plan + 5 test + 5 implement + 5 review + 1 ship
system_ram: 16GB  # WSL2

# With session reuse: only 1 process per stage type (not per iteration)
effective_processes: 5  # plan, test, implement, review, ship

# NATS stream retention
stream_max_age: 3600s  # 1 hour
stream_max_bytes: 50MB

# Container memory limits (docker-compose)
myrmidon_worker_mem: 256M
nats_mem: 128M

# Dry-run validation
dry_run_duration: ~2 seconds
dry_run_memory: 26.9 MB (flat)
```

### Key Files

| File | Role |
| ------ | ------ |
| `e2e/claude-myrmidon.py` | Multi-stage NATS pipeline orchestrator |
| `e2e/docker-compose.yml` | Container definitions with memory limits |

### Diagnostic Commands

```bash
# Check RSS of running claude processes
ps aux | grep '[c]laude' | awk '{print $6/1024 " MB", $0}'

# Monitor NATS stream state
nats stream info MYRMIDON

# Run pipeline in dry-run mode
DRY_RUN=1 python3 e2e/claude-myrmidon.py

# Check system memory pressure
free -h && cat /proc/meminfo | grep -E 'MemAvail|SwapFree'

# Check OOM kills in dmesg (note: WSL2 VM may be killed silently by Windows host)
dmesg | grep -i oom
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Odysseus | E2E NATS pipeline OOM on 2026-04-04 | Dry-run validated end-to-end locally; memory confirmed flat at 26.9 MB |

## References

- [batch-subprocess-signal-hang](batch-subprocess-signal-hang.md) -- stdin blocking and signal isolation patterns
- [e2e-resource-exhaustion](e2e-resource-exhaustion.md) -- related OOM from parallel Scylla experiment workspaces
- [architecture-crosshost-nats-compose-deployment](architecture-crosshost-nats-compose-deployment.md) -- NATS deployment patterns
