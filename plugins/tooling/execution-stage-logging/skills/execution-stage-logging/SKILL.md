---
name: execution-stage-logging
description: Add structured stage logging with timing to track worker thread progress through multi-stage pipelines
category: tooling
date: 2026-01-04
tags: [logging, observability, debugging, worker-threads, pipeline]
---

# Execution Stage Logging

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Add visibility into which stage each worker thread is executing and how long each stage takes |
| **Outcome** | ✅ Structured stage logging with timing prevents "appears hung" issues |
| **Project** | ProjectScylla |
| **PR** | [#139](https://github.com/HomericIntelligence/ProjectScylla/pull/139) |

## When to Use

Use this pattern when:
- Parallel workers execute multi-stage pipelines
- Long-running operations make it unclear if process is stuck
- Need to identify performance bottlenecks per stage
- Want structured logs for parsing/analysis
- Debugging which workers are slow/stuck

## Problem

**Unstructured Logging**:
```
[AGENT] - Running agent with model[...]
```
...27 seconds of silence...
```
Starting tier T1
```

**Issues**:
1. No indication of current stage during execution
2. Can't tell if worker is stuck or just slow
3. No timing data per stage
4. Unclear which worker is doing what
5. Appears hung to users

## Verified Workflow

### 1. Define Stage Enum

```python
from enum import Enum

class ExecutionStage(str, Enum):
    """Execution stages for worker thread reporting."""
    WORKTREE = "WORKTREE"
    AGENT = "AGENT"
    JUDGE = "JUDGE"
    CLEANUP = "CLEANUP"
    COMPLETE = "COMPLETE"
```

### 2. Create Stage Logging Helper

```python
import time
from datetime import UTC, datetime

def _stage_log(
    worker_id: str,
    stage: ExecutionStage,
    status: str,
    elapsed: float | None = None,
) -> None:
    """Log execution stage with worker context and timing.

    Args:
        worker_id: Worker identifier (e.g., "T0_00")
        stage: Execution stage
        status: Status description (e.g., "Starting", "Complete")
        elapsed: Optional elapsed time in seconds
    """
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    elapsed_str = f" ({elapsed:.1f}s)" if elapsed is not None else ""
    logger.info(f"{timestamp} [{worker_id}] Stage: {stage.value} - {status}{elapsed_str}")
```

### 3. Add Stage Markers

```python
def execute_pipeline(worker_id: str):
    """Execute multi-stage pipeline with stage logging."""
    start_time = time.time()

    # Stage 1: AGENT
    _stage_log(worker_id, ExecutionStage.AGENT, "Starting")
    agent_start = time.time()

    result = run_agent()

    agent_duration = time.time() - agent_start
    _stage_log(worker_id, ExecutionStage.AGENT, "Complete", agent_duration)

    # Stage 2: JUDGE
    _stage_log(worker_id, ExecutionStage.JUDGE, "Starting")
    judge_start = time.time()

    judgment = run_judge(result)

    judge_duration = time.time() - judge_start
    _stage_log(worker_id, ExecutionStage.JUDGE, "Complete", judge_duration)

    # Final
    total_elapsed = time.time() - start_time
    _stage_log(worker_id, ExecutionStage.COMPLETE, "All stages complete", total_elapsed)
```

### 4. Example Output

```
2026-01-04T19:30:15.234Z [T0_00] Stage: AGENT - Starting
2026-01-04T19:30:28.456Z [T0_00] Stage: AGENT - Complete (13.2s)
2026-01-04T19:30:29.123Z [T0_00] Stage: JUDGE - Starting
2026-01-04T19:30:35.789Z [T0_00] Stage: JUDGE - Complete (6.7s)
2026-01-04T19:30:35.890Z [T0_00] Stage: COMPLETE - All stages complete (20.7s)
```

### 5. Parallel Worker Output

```
2026-01-04T19:30:15.234Z [T0_00] Stage: AGENT - Starting
2026-01-04T19:30:15.245Z [T0_01] Stage: AGENT - Starting
2026-01-04T19:30:28.456Z [T0_00] Stage: AGENT - Complete (13.2s)
2026-01-04T19:30:29.123Z [T0_00] Stage: JUDGE - Starting
2026-01-04T19:30:30.678Z [T0_01] Stage: AGENT - Complete (15.4s)  # Slower!
2026-01-04T19:30:31.234Z [T0_01] Stage: JUDGE - Starting
```

## Failed Attempts

| Approach | Why It Failed |
|----------|---------------|
| Logging only start events | Can't tell when stages complete or how long they took |
| Logging only completion | Can't tell if worker is stuck during execution |
| Using progress bars | Doesn't work well with multiple parallel workers |
| Polling worker state | Race conditions, complex synchronization needed |

## Results & Parameters

### Stage Logging Pattern

```python
# Template for adding stage logging to existing code:

def existing_function(worker_id: str):
    # 1. Track overall timing
    start_time = time.time()

    # 2. For each stage:
    _stage_log(worker_id, ExecutionStage.STAGE_NAME, "Starting")
    stage_start = time.time()

    # ... existing stage logic ...

    stage_duration = time.time() - stage_start
    _stage_log(worker_id, ExecutionStage.STAGE_NAME, "Complete", stage_duration)

    # 3. Final completion
    total_elapsed = time.time() - start_time
    _stage_log(worker_id, ExecutionStage.COMPLETE, "All stages complete", total_elapsed)
```

### Benefits Achieved

1. **Visibility**: Know exactly which stage each worker is in
2. **Performance**: Timing data identifies slow stages
3. **Debugging**: Easy to spot stuck workers
4. **Structured**: Parseable format for analysis tools
5. **User Confidence**: Progress visible, not "appears hung"

### Parsing Stage Logs

```python
import re

def parse_stage_log(line: str):
    """Parse stage log line into structured data."""
    pattern = r"(\S+) \[(\w+)\] Stage: (\w+) - (\w+)(?: \((\d+\.\d+)s\))?"
    match = re.match(pattern, line)

    if match:
        return {
            "timestamp": match.group(1),
            "worker_id": match.group(2),
            "stage": match.group(3),
            "status": match.group(4),
            "duration": float(match.group(5)) if match.group(5) else None
        }
```

## Key Learnings

1. **Consistent Format**: Use `[worker_id] Stage: STAGE - status (timing)` pattern
2. **Both Start and Complete**: Log transitions, not just endpoints
3. **Timing Essential**: Elapsed time helps identify bottlenecks
4. **Worker Context**: Include worker ID in every log
5. **Enum for Stages**: Prevents typos, enables tooling

## Use Cases

1. **Parallel ML Training**: Track which GPU is in which training phase
2. **ETL Pipelines**: Monitor extract/transform/load stages per worker
3. **Batch Processing**: Track item processing stages across workers
4. **Test Runners**: Show which test stage each worker is running

## Related Skills

- `tooling/structured-logging` - General structured logging patterns
- `debugging/hung-process-detection` - Detecting stuck processes
- `optimization/performance-profiling` - Finding bottlenecks

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #139 - Worker stage reporting for E2E experiments | [notes.md](../../references/notes.md) |
