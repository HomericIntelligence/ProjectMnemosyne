# Checkpoint Recovery for Batch Processes

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-12 |
| **Objective** | Add resume/checkpoint and rate limit handling to batch runner for E2E tests |
| **Outcome** | ✅ Success - PR #526 created with full implementation |
| **Files Modified** | `scripts/run_e2e_batch.py` (new file, 928 lines) |
| **Key Innovation** | Incremental checkpoint saves with atomic writes + pre-flight rate limit checks |

## When to Use This Skill

Use this skill when you need to add checkpoint/resume functionality to any batch processing system, especially when:

- ✅ Long-running batch jobs (hours/days) that can be interrupted
- ✅ External API calls that may hit rate limits or fail transiently
- ✅ Multi-threaded or parallel execution that processes independent units
- ✅ Need to preserve progress across restarts (infrastructure failures, Ctrl+C, crashes)
- ✅ Want to selectively retry failed items without re-running successful ones

**Common Scenarios**:
- Batch E2E test runners
- Data migration scripts with API calls
- Multi-file processing pipelines
- Long-running evaluation/benchmarking jobs
- ETL processes with external dependencies

## Verified Workflow

### 1. Design the Checkpoint Data Structure

**Decision**: Use JSON for human-readable, self-describing checkpoints.

```python
# Checkpoint structure
{
    "started_at": "2026-02-12T10:00:00Z",
    "completed_at": "2026-02-12T11:30:00Z",
    "config": {...},  # Immutable config snapshot
    "results": [      # Incremental results list
        {"item_id": "test-001", "status": "pass", ...},
        {"item_id": "test-002", "status": "error", ...}
    ]
}
```

**Key Principles**:
- Append-only results list (never modify existing entries)
- Include timestamp metadata for debugging
- Snapshot config to detect incompatible restarts

### 2. Implement Incremental Checkpoint Saves

**Pattern**: Save after each item completes (not just at the end).

```python
def save_incremental_result(checkpoint_path: Path, result: dict, config: dict) -> None:
    """Save single result incrementally with atomic write."""
    tmp_path = checkpoint_path.with_suffix(".json.tmp")

    # Load existing or create fresh
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
    else:
        checkpoint = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "config": config,
            "results": []
        }

    # Append new result
    checkpoint["results"].append(result)
    checkpoint["completed_at"] = datetime.now(timezone.utc).isoformat()

    # Atomic write (tmp + rename)
    with open(tmp_path, "w") as f:
        json.dump(checkpoint, f, indent=2)
    tmp_path.rename(checkpoint_path)
```

**Why Atomic Writes Matter**:
- `tmp + rename` prevents corrupt JSON if process is killed during write
- Filesystem rename is atomic on POSIX systems
- Ensures checkpoint is always valid or non-existent (never half-written)

### 3. Load and Filter on Startup

**Pattern**: Load existing results and skip completed items.

```python
def load_existing_results(checkpoint_path: Path) -> list[dict]:
    """Load existing results from checkpoint."""
    if not checkpoint_path.exists():
        return []

    try:
        with open(checkpoint_path) as f:
            data = json.load(f)
        return data.get("results", [])
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return []  # Fail gracefully

# On startup
existing_results = load_existing_results(checkpoint_path)
completed_ids = {r["item_id"] for r in existing_results}

# Filter out completed items
items_to_process = [item for item in all_items if item["id"] not in completed_ids]
```

**Decision**: Treat ALL existing results as "completed" (pass, fail, error).
- Prevents re-running tests that legitimately failed
- User can inspect failures in checkpoint and logs
- Add `--retry-errors` flag for selective re-run

### 4. Add Pre-Flight Checks for Transient Failures

**Pattern**: Check for known failure conditions before launching expensive work.

```python
def check_rate_limit() -> tuple[bool, str]:
    """Pre-flight check for API rate limits."""
    rate_info = check_api_rate_limit_status()  # Lightweight API ping
    if rate_info:
        reset_time = calculate_reset_time(rate_info)
        message = f"Rate limited until {reset_time}"
        return True, message
    return False, ""

# In main()
is_rate_limited, rate_msg = check_rate_limit()
if is_rate_limited:
    print(f"⏸️  {rate_msg}")
    print("Re-run this script later. It will auto-resume from checkpoint.")
    return 2  # Distinct exit code for automation
```

**Why Distinct Exit Codes**:
- `0` = Success (all items completed)
- `1` = Error (permanent failure, investigate)
- `2` = Transient failure (rate limit, retry later)
- Enables automation: `if exit_code == 2: sleep_and_retry()`

### 5. Handle Logs in Append Mode

**Decision**: Append to log files on restart (don't truncate).

```python
# BEFORE (truncates on restart)
with open(log_file, "w") as f:
    process_items(items, log_file=f)

# AFTER (appends on restart)
with open(log_file, "a") as f:
    process_items(items, log_file=f)
```

**Rationale**:
- Preserves debugging context from previous attempts
- Shows full history of retries and rate limit waits
- Slightly larger logs acceptable (can add rotation later)

### 6. Add Selective Retry Flags

**Pattern**: Allow users to re-run specific failure categories.

```python
# CLI argument
parser.add_argument("--retry-errors", action="store_true",
    help="Re-run items with status='error'")

# Filter logic
completed_ids = set()
for result in existing_results:
    # Skip non-errors, or errors if --retry-errors not set
    if result["status"] != "error" or not args.retry_errors:
        completed_ids.add(result["item_id"])

# Clean up stale error entries when retrying
if args.retry_errors:
    existing_results = [r for r in existing_results if r["status"] != "error"]
```

### 7. Add Fresh/Reset Flag

**Pattern**: Allow users to start from scratch.

```python
parser.add_argument("--fresh", action="store_true",
    help="Clear checkpoint and restart from scratch")

# On startup
if args.fresh:
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        logger.info("Cleared checkpoint (--fresh mode)")
```

## Failed Attempts & Lessons Learned

### ❌ FAILED: Conditional String in Command List

**What We Tried**:
```python
cmd = [
    "python", "script.py",
    "--fresh" if args.fresh else "",  # BUG!
]
```

**Why It Failed**:
- When `args.fresh` is False, appends empty string `""` to command
- Subprocess interprets `""` as a literal argument
- Causes cryptic errors or unexpected behavior

**Solution**:
```python
cmd = ["python", "script.py"]
if args.fresh:
    cmd.append("--fresh")
```

**Lesson**: Build command lists conditionally, never use ternary with empty string.

### ❌ FAILED: Writing Checkpoint Only at End

**What We Tried** (initial design):
- Save checkpoint once when all items complete
- Fast (single write), simple implementation

**Why It Failed**:
- Ctrl+C or crash loses ALL progress
- Long-running jobs (hours) have to restart from scratch
- Defeats the purpose of checkpointing

**Solution**:
- Save checkpoint after EACH item completes
- Atomic writes ensure integrity even if killed mid-save
- Small performance cost (~1 write/item) vs huge UX win

**Lesson**: Incremental saves are worth the overhead for long-running processes.

### ❌ FAILED: Treating Errors as Incomplete

**What We Tried**:
- Only mark "pass" and "fail" as completed
- Always re-run "error" status items on restart

**Why It Failed**:
- Some errors are permanent (bad test fixture, missing deps)
- Re-running them wastes time and resources
- Hard to distinguish transient (rate limit) from permanent (bug)

**Solution**:
- Treat ALL results (pass, fail, error) as "completed" by default
- Add `--retry-errors` flag for selective re-run
- User inspects logs to decide what to retry

**Lesson**: Default to conservative (skip completed), provide escape hatch (retry flag).

### ⚠️ GOTCHA: Checkpoint Format Changes

**Problem**: What if checkpoint structure changes between versions?

**Current Approach**:
- Graceful fallback: If load fails, return `[]` and start fresh
- Log warning so user knows checkpoint was ignored

**Better Future Approach**:
- Add `"version": 1` field to checkpoint
- Check version on load, reject incompatible formats
- Provide migration script for major changes

**Lesson**: Plan for schema evolution from day 1 (we punted this to future work).

### ⚠️ GOTCHA: Concurrent Writes

**Problem**: What if two processes write checkpoint simultaneously?

**Current Mitigation**:
- Atomic rename prevents corrupt JSON
- Last write wins (one process's results may be lost)

**Not Addressed**:
- No file locking (acceptable for single-user scripts)
- No merge conflict detection

**When This Matters**:
- Multi-machine batch jobs (distributed systems)
- Shared filesystem with multiple writers

**Lesson**: For single-threaded, single-machine scripts, atomic writes are sufficient. For distributed systems, need proper locking/coordination.

## Results & Parameters

### Implementation Stats

| Metric | Value |
|--------|-------|
| **Lines of code** | 928 lines (new file) |
| **Functions added** | 3 new (`load_existing_results`, `save_incremental_result`, `check_rate_limit`) |
| **Functions modified** | 3 (`run_single_test`, `run_thread`, `main`) |
| **CLI flags added** | 2 (`--fresh`, `--retry-errors`) |
| **Exit codes** | 3 (0=success, 1=error, 2=rate-limited) |

### Usage Examples

```bash
# Fresh run (start from scratch)
python scripts/run_e2e_batch.py --tests test-001 test-002 --fresh

# Resume (auto-skip completed)
python scripts/run_e2e_batch.py --tests test-001 test-002

# Retry only errors
python scripts/run_e2e_batch.py --retry-errors

# Check rate limit and exit immediately
python scripts/run_e2e_batch.py
# Output: "⏸️  Rate limited until 2026-02-19T06:00:00Z"
# Exit code: 2
```

### Verification Checklist

- ✅ Fresh run creates checkpoint with 1 result
- ✅ Second run (without `--fresh`) skips completed tests
- ✅ Ctrl+C mid-run, restart resumes from checkpoint
- ✅ `--retry-errors` re-runs error cases only
- ✅ Pre-flight rate limit check exits with code 2
- ✅ Thread logs append (not truncate) on restart
- ✅ No empty string `""` in subprocess command

## Key Design Decisions

### 1. Completed = Attempted (Not Just Passed)

**Decision**: A test is "completed" if it has ANY result (pass, fail, error, unknown).

**Rationale**:
- Prevents re-running tests that failed due to legitimate issues
- User can inspect failures in checkpoint and decide what to retry
- `--retry-errors` provides selective re-run for transient failures

**Trade-off**: User must manually review failures (not auto-retried).

### 2. Incremental Saves Use Atomic Writes

**Decision**: Write to `.tmp`, then rename (atomic operation).

**Rationale**:
- Prevents corrupt JSON if killed during write
- Ensures checkpoint is always valid or non-existent
- Standard pattern for atomic file updates

**Cost**: One extra filesystem operation per save (negligible).

### 3. Append Logs Instead of Truncate

**Decision**: Use `open(log_file, "a")` instead of `"w"`.

**Rationale**:
- Preserves debugging context from previous attempts
- Shows full history of retries, rate limit waits, and failures
- Correlation between checkpoint state and execution logs

**Trade-off**: Logs grow larger on repeated restarts (acceptable for batch scripts).

### 4. Exit Code 2 for Transient Failures

**Decision**: Use distinct exit code for rate limits (not generic error code 1).

**Rationale**:
- Enables automation to distinguish transient from permanent failures
- Scripts can `if exit_code == 2: sleep_and_retry()`
- Clear signal to user: "wait and re-run, don't debug"

**Standard**:
- 0 = Success
- 1 = Permanent error
- 2 = Transient failure (retry later)
- 130 = SIGINT (Ctrl+C)

## Related Files & Context

| File | Purpose |
|------|---------|
| `scripts/run_e2e_batch.py` | Batch runner with checkpoint/resume (all changes) |
| `scylla/e2e/rate_limit.py` | Rate limit detection module (imported by batch runner) |
| `scylla/e2e/runner.py` | Single-test runner with per-test checkpoint (orthogonal system) |

## When NOT to Use This Pattern

- ❌ **Fast jobs (<5 min)**: Checkpoint overhead not worth it
- ❌ **Strictly ordered processing**: Items depend on previous results (can't skip)
- ❌ **Distributed systems**: Need proper locking, not atomic writes
- ❌ **Real-time systems**: Latency of disk I/O per item unacceptable
- ❌ **Stateful transformations**: Can't re-run same item twice (idempotency required)

## Future Enhancements

1. **Checkpoint versioning** - Add `"version"` field, validate on load
2. **Progress bar** - Live progress across threads (e.g., `tqdm`)
3. **Thread affinity** - Resume same tests on same threads (reduces log fragmentation)
4. **Partial item resume** - If single item interrupted mid-processing, resume that item
5. **Automatic backoff** - Instead of exiting on rate limit, wait automatically
6. **Checkpoint metadata** - Track `pause_count`, `resume_count`, `total_wait_time`
7. **Cleanup command** - `--cleanup` to remove checkpoint and logs

## Tags

`#checkpoint` `#resume` `#batch-processing` `#rate-limits` `#interruption-recovery` `#atomic-writes` `#resilience`
