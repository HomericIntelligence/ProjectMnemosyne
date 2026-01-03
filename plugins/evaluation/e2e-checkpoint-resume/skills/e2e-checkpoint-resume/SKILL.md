# E2E Checkpoint/Resume with Rate Limit Handling

| Field | Value |
|-------|-------|
| **Date** | 2026-01-03 |
| **Project** | ProjectScylla |
| **Objective** | Enable E2E testing to automatically pause when rate limits are hit, wait for retry time, and resume from exact run that was interrupted |
| **Outcome** | ✅ Success - Auto-resume working, rate limit coordination implemented |
| **Impact** | High - Enables overnight E2E test runs without manual intervention |

## When to Use This Skill

Use this skill when:

1. **Implementing long-running evaluation experiments** that may hit API rate limits
2. **Adding checkpoint/resume capability** to any multi-step execution framework
3. **Coordinating parallel workers** that need to pause/resume together
4. **Handling rate limits** from multiple API sources (agent, judge, etc.)
5. **Preserving experiment state** for crash recovery or interruption

**Triggers**:
- User requests "pause/resume on rate limits"
- Need to run experiments overnight without monitoring
- Implementing checkpoint systems for any long-running process
- Coordinating state across parallel worker processes

## Verified Workflow

### 1. Planning Phase: Interview for Requirements

**Critical**: Before implementation, clarify ALL design decisions through user interview:

```markdown
Interview Questions (use AskUserQuestion):

1. Resume Granularity
   - Options: Tier-level, Subtest-level, Run-level
   - Decision: Run-level (most comprehensive)

2. Wait Strategy
   - Options: Fixed delay, Exponential backoff, Honor Retry-After
   - Decision: Honor Retry-After + 10% buffer

3. Detection Scope
   - Options: Agent only, Judge only, Both
   - Decision: Both agent AND judge

4. Checkpoint Location
   - Options: Separate dir, Experiment dir, Temp dir
   - Decision: Experiment directory (results/{exp}/checkpoint.json)

5. Detection Method
   - Options: Exit code only, Stderr patterns, JSON parsing
   - Decision: JSON `is_error` + stderr patterns (429, "rate limit", "overloaded")

6. Parallel Behavior
   - Options: Pause individual worker, Pause all workers
   - Decision: Pause ALL workers when any hits rate limit

7. Resume Invocation
   - Options: Manual flag, Auto-resume, User choice
   - Decision: Auto-resume by default, --fresh to override

8. Config Validation
   - Options: Allow changes, Strict match, Warn only
   - Decision: Strict match required (prevent config drift)
```

**Key Insight**: This interview prevented multiple rounds of rework by establishing all requirements upfront.

### 2. Architecture: Four-Layer System

**Layer 1: Checkpoint State (`checkpoint.py`)**

```python
@dataclass
class E2ECheckpoint:
    version: str = "1.0"
    experiment_id: str
    experiment_dir: str
    config_hash: str  # SHA256 for strict validation

    # Progress: tier_id -> subtest_id -> list[completed_run_numbers]
    completed_runs: dict[str, dict[str, list[int]]]

    # Status tracking
    status: str  # "running", "paused_rate_limit", "completed", "failed"
    rate_limit_source: str | None  # "agent" or "judge"
    rate_limit_until: str | None  # ISO timestamp
    pause_count: int
    pid: int | None
```

**Key Functions**:
- `save_checkpoint()` - **Atomic write** via temp file + rename
- `compute_config_hash()` - Hash **excluding** parallel_subtests, max_subtests (non-critical)
- `validate_checkpoint_config()` - Strict validation on resume

**Layer 2: Rate Limit Detection (`rate_limit.py`)**

```python
@dataclass
class RateLimitInfo:
    source: str  # "agent" or "judge"
    retry_after_seconds: float | None
    error_message: str
    detected_at: str

def detect_rate_limit(stdout: str, stderr: str, source: str) -> RateLimitInfo | None:
    # Priority 1: Parse JSON output (primary method)
    try:
        data = json.loads(stdout.strip())
        if data.get("is_error"):
            # Check for rate limit keywords
            if any(keyword in error_str for keyword in ["rate limit", "overloaded", "429"]):
                return RateLimitInfo(...)
    except json.JSONDecodeError:
        pass

    # Priority 2: Scan stderr for patterns (fallback)
    if "429" in stderr or "rate limit" in stderr.lower():
        return RateLimitInfo(...)
```

**Wait Strategy**:
```python
def wait_for_rate_limit(retry_after, checkpoint, checkpoint_path):
    wait_time = retry_after * 1.1  # 10% buffer

    # Update checkpoint status
    checkpoint.status = "paused_rate_limit"
    checkpoint.rate_limit_until = (now + wait_time).isoformat()
    save_checkpoint(checkpoint, checkpoint_path)

    # Wait with periodic logging (every 30s)
    while remaining > 0:
        time.sleep(min(30, remaining))
        logger.info(f"Waiting for rate limit... {remaining:.0f}s remaining")
```

**Layer 3: Parallel Worker Coordination (`RateLimitCoordinator`)**

```python
class RateLimitCoordinator:
    """Pause ALL workers when ANY hits rate limit."""

    def __init__(self, manager: Manager):
        self._pause_event = manager.Event()
        self._resume_event = manager.Event()
        self._rate_limit_info = manager.dict()

    def signal_rate_limit(self, info: RateLimitInfo):
        """Called by any worker - pauses ALL workers."""
        self._rate_limit_info.update(info.__dict__)
        self._pause_event.set()

    def check_if_paused(self) -> bool:
        """Workers call before each operation. Blocks if paused."""
        if self._pause_event.is_set():
            self._resume_event.wait()  # Block until resume
            self._resume_event.clear()
            return True
        return False
```

**Usage Pattern**:
```python
# Main thread
coordinator = RateLimitCoordinator(Manager())

# Worker processes
try:
    coordinator.check_if_paused()  # Blocks if paused
    run_result = execute_run(...)
except RateLimitError as e:
    coordinator.signal_rate_limit(e.info)  # Pause all workers
    raise

# Main thread handles wait
if rate_limit_detected:
    wait_for_rate_limit(retry_after, checkpoint, checkpoint_path)
    coordinator.resume_all_workers()  # Unblock workers
```

**Layer 4: Auto-Resume Logic (`runner.py`)**

```python
def run(self) -> ExperimentResult:
    # Check for existing checkpoint
    checkpoint_path = self._find_existing_checkpoint()

    if checkpoint_path and not self._fresh:
        # Resume from checkpoint
        self.checkpoint = load_checkpoint(checkpoint_path)

        # Validate config match (strict validation)
        if not validate_checkpoint_config(self.checkpoint, self.config):
            raise ValueError("Config changed. Use --fresh to start over.")

        self.experiment_dir = Path(self.checkpoint.experiment_dir)
        logger.info(f"📂 Resuming from checkpoint: {checkpoint_path}")

    if not self.experiment_dir:
        # Fresh start - create checkpoint
        self.checkpoint = E2ECheckpoint(...)
        save_checkpoint(self.checkpoint, checkpoint_path)
```

### 3. Integration Points

**Adapter Integration** (claude_code.py, llm_judge.py):
```python
# After subprocess execution
rate_limit_info = detect_rate_limit(result.stdout, result.stderr, source="agent")
if rate_limit_info:
    self.write_logs(config.output_dir, result.stdout, result.stderr)
    raise RateLimitError(rate_limit_info)
```

**Checkpoint-Aware Execution** (subtest_executor.py):
```python
# Skip completed runs
if checkpoint and checkpoint.is_run_completed(tier_id, subtest_id, run_num):
    logger.info(f"Skipping completed run: {tier_id}/{subtest_id}/run_{run_num:02d}")
    # Load from disk
    run_result = load_from_run_result_json(run_dir / "run_result.json")
    runs.append(run_result)
    continue

# Execute run
run_result = execute_run(...)

# Save checkpoint after each successful run
checkpoint.mark_run_completed(tier_id, subtest_id, run_num)
save_checkpoint(checkpoint, checkpoint_path)
```

**Workspace Optimization**:
```python
# Check if ALL runs are already completed
all_completed = True
if checkpoint:
    for run_num in range(1, runs_per_subtest + 1):
        if not checkpoint.is_run_completed(tier_id, subtest_id, run_num):
            all_completed = False
            break

# Only setup workspace if there are runs to execute
if not all_completed:
    workspace.mkdir(parents=True, exist_ok=True)
    setup_workspace(workspace, logger)
else:
    # All runs completed, just use existing workspace path
    workspace = results_dir / "workspace"
```

### 4. Data Persistence Strategy

**Problem**: The existing `report.json` had simplified structure, not full `RunResult` data.

**Solution**: Save **two files** per run:
1. `report.json` - Human-readable summary (existing)
2. `run_result.json` - Full `RunResult.to_dict()` for checkpoint resume (NEW)

```python
# After creating RunResult
run_result = RunResult(...)

# Save full RunResult for checkpoint resume
with open(run_dir / "run_result.json", "w") as f:
    json.dump(run_result.to_dict(), f, indent=2)

# Generate human-readable report (existing)
save_run_report(output_path=run_dir / "report.md", ...)
```

**Deserialization**:
```python
with open(run_result_file) as f:
    report_data = json.load(f)

run_result = RunResult(
    run_number=report_data["run_number"],
    exit_code=report_data["exit_code"],
    token_stats=TokenStats.from_dict(report_data["token_stats"]),
    cost_usd=report_data["cost_usd"],
    duration_seconds=report_data["duration_seconds"],
    judge_score=report_data["judge_score"],
    judge_passed=report_data["judge_passed"],
    judge_grade=report_data["judge_grade"],
    judge_reasoning=report_data["judge_reasoning"],
    workspace_path=Path(report_data["workspace_path"]),
    logs_path=Path(report_data["logs_path"]),
    command_log_path=Path(report_data["command_log_path"]) if report_data.get("command_log_path") else None,
    criteria_scores=report_data.get("criteria_scores", {}),
)
```

## Failed Attempts & Lessons Learned

### ❌ Attempt 1: Load from `report.json`

**What we tried**: Load completed runs from existing `report.json` file

**Why it failed**:
```python
# This failed with KeyError: 'exit_code'
with open(run_dir / "report.json") as f:
    report_data = json.load(f)
run_result = RunResult.from_dict(report_data)  # No from_dict() method!
```

**Root cause**:
- `report.json` has simplified structure (`score`, `grade`, `passed`)
- `RunResult` needs full data (`exit_code`, `token_stats`, `workspace_path`, etc.)
- No `from_dict()` classmethod exists on `RunResult`

**Fix**: Create separate `run_result.json` with full `RunResult.to_dict()` output

**Lesson**: Don't assume existing report formats match internal data structures. Check serialization format before implementing deserialization.

### ❌ Attempt 2: Setup workspace on resume with existing directory

**What we tried**: Always setup workspace at start of `run_subtest()`

**Why it failed**:
```
RuntimeError: Failed to create worktree:
fatal: '/path/to/workspace' already exists
```

**Root cause**: When resuming, workspace already exists from previous run. Git worktree creation fails if directory exists.

**Fix**: Check if all runs are completed before setting up workspace
```python
# Only setup workspace if there are runs to execute
if not all_completed:
    workspace.mkdir(parents=True, exist_ok=True)
    self._setup_workspace(workspace, logger)
else:
    workspace = results_dir / "workspace"  # Just use path
```

**Lesson**: Idempotency is critical for resume logic. Always check if work is already done before executing expensive operations.

### ❌ Attempt 3: Missing `RunResult.from_dict()` method

**What we tried**: Call non-existent classmethod `RunResult.from_dict()`

**Why it failed**: AttributeError - method doesn't exist

**Root cause**: `RunResult` has `to_dict()` but no corresponding `from_dict()` classmethod

**Fix**: Manual reconstruction in checkpoint resume code
```python
run_result = RunResult(
    run_number=report_data["run_number"],
    exit_code=report_data["exit_code"],
    token_stats=TokenStats.from_dict(report_data["token_stats"]),
    # ... all other fields
)
```

**Lesson**: Don't assume symmetric serialization methods exist. Check class definitions before implementing deserialization.

## Results & Parameters

### Test Results

**Fresh run** (with checkpoint creation):
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 --max-subtests 1 --fresh -v

# Output:
Duration: 67.6s
Total Cost: $0.1111
✅ Checkpoint saved: results/2026-01-03T22-37-33-test-001/checkpoint.json
```

**Auto-resume** (loading from checkpoint):
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 --runs 1 --max-subtests 1 -v

# Output:
📂 Resuming from checkpoint: results/2026-01-03T22-37-33-test-001/checkpoint.json
   Previously completed: 1 runs
Skipping completed run: T0/00/run_01
Duration: 0.2s (67.4s saved!)
Total Cost: $0.1111 (no new cost)
```

### Checkpoint File Structure

```json
{
  "version": "1.0",
  "experiment_id": "test-001",
  "experiment_dir": "results/2026-01-03T22-37-33-test-001",
  "config_hash": "ab31f10de894ec31",
  "completed_runs": {
    "T0": {
      "00": [1, 2, 3],
      "01": [1, 2]
    }
  },
  "started_at": "2026-01-03T22:33:09.296219+00:00",
  "last_updated_at": "2026-01-03T22:34:18.292176+00:00",
  "status": "completed",
  "rate_limit_source": null,
  "rate_limit_until": null,
  "pause_count": 0,
  "pid": 1115392
}
```

### Files Modified

| File | Lines Added | Purpose |
|------|-------------|---------|
| `src/scylla/e2e/checkpoint.py` | 330 | NEW - Checkpoint state management |
| `src/scylla/e2e/rate_limit.py` | 190 | NEW - Rate limit detection and wait |
| `src/scylla/e2e/subtest_executor.py` | +200 | RateLimitCoordinator, checkpoint support |
| `src/scylla/e2e/runner.py` | +150 | Auto-resume logic, PID file |
| `src/scylla/adapters/claude_code.py` | +10 | Rate limit detection in agent |
| `src/scylla/e2e/llm_judge.py` | +7 | Rate limit detection in judge |
| `scripts/run_e2e_experiment.py` | +8 | --fresh flag |

### Configuration Patterns

**Config Hash Calculation** (excludes non-critical fields):
```python
def compute_config_hash(config: ExperimentConfig) -> str:
    """Compute SHA256 hash of config for strict validation.

    Excludes parallel_subtests and max_subtests (testing params).
    """
    hash_input = {
        "experiment_id": config.experiment_id,
        "task_repo": config.task_repo,
        "task_commit": config.task_commit,
        "models": config.models,
        "runs_per_subtest": config.runs_per_subtest,
        "tiers_to_run": [t.value for t in config.tiers_to_run],
        "judge_model": config.judge_model,
        "timeout_seconds": config.timeout_seconds,
    }
    return hashlib.sha256(json.dumps(hash_input, sort_keys=True).encode()).hexdigest()[:16]
```

**Checkpoint Validation**:
```python
def validate_checkpoint_config(checkpoint: E2ECheckpoint, config: ExperimentConfig) -> bool:
    """Validate that config hasn't changed since checkpoint."""
    current_hash = compute_config_hash(config)
    return checkpoint.config_hash == current_hash
```

## Best Practices

1. **Interview before implementation** - Clarify all design decisions upfront
2. **Atomic checkpoint writes** - Use temp file + rename pattern
3. **Strict config validation** - Prevent silent config drift on resume
4. **Workspace idempotency** - Check if work is done before executing
5. **Dual persistence** - Save both human-readable and machine-readable formats
6. **Pause-all-workers** - Coordinate parallel processes on rate limits
7. **PID file monitoring** - Enable external status checks
8. **Config hash exclusions** - Exclude non-critical testing parameters

## Usage Examples

**Running overnight experiments**:
```bash
# Start experiment (will auto-resume on rate limits)
python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-002 \
    --tiers T0 T1 T2 T3 \
    --runs 10

# Check status
cat results/*/checkpoint.json | jq '.status, .rate_limit_until'

# Resume manually after interruption
# (same command - auto-detects checkpoint)
python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-002 \
    --tiers T0 T1 T2 T3 \
    --runs 10

# Force fresh start
python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-002 \
    --tiers T0 T1 T2 T3 \
    --runs 10 \
    --fresh
```

## Related Skills

- `multiprocessing-coordination` - Process coordination patterns
- `api-rate-limiting` - Rate limit detection strategies
- `checkpoint-systems` - State persistence patterns
- `idempotent-operations` - Resumable execution design

## References

- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/126
- Checkpoint implementation: `src/scylla/e2e/checkpoint.py`
- Rate limit detection: `src/scylla/e2e/rate_limit.py`
- Coordinator pattern: `src/scylla/e2e/subtest_executor.py:RateLimitCoordinator`
