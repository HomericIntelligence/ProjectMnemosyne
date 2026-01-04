---
name: e2e-agent-judge-timing
description: Add separate agent and judge timing fields to E2E test results for tiebreaker ranking
category: evaluation
date: 2026-01-04
tags: [e2e, timing, metrics, tiebreaker, agent, judge, evaluation]
---

# E2E Agent/Judge Timing Separation

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Add separate timing fields for agent and judge execution to enable tiebreaker ranking |
| **Outcome** | ✅ Success - Timing breakdown implemented with report visualization |
| **Project** | ProjectScylla |
| **PR** | [#143](https://github.com/HomericIntelligence/ProjectScylla/pull/143) |

## When to Use

Use this pattern when:
- Implementing tiebreaker metrics for ranking equivalent evaluation results
- Need to track performance of multi-stage pipelines (agent + judge)
- Want to analyze where time is spent in evaluation workflows
- Building E2E test frameworks with separate execution and evaluation phases
- Need timing data for cost/performance optimization decisions

## Problem

**Original State**: Only total `duration_seconds` tracked for entire run
- Cannot determine if agent or judge is the bottleneck
- No timing-based tiebreaker when multiple results have identical scores
- Cached/reused results have unclear timing semantics

**User Request**: "I want the time it takes to run agents/judges added to the reports/logs so that it is possible to rank equivalently produced results by time taken as a tiebreaker"

## Verified Workflow

### 1. Add Timing Fields to Data Model

**File**: `src/scylla/e2e/models.py`

```python
@dataclass
class RunResult:
    """Result from a single run of a sub-test."""

    # Existing fields...
    cost_usd: float
    duration_seconds: float              # Total (agent + judge)
    agent_duration_seconds: float        # NEW: Agent execution time
    judge_duration_seconds: float        # NEW: Judge evaluation time
    judge_score: float
    # ... other fields
```

**Key Points**:
- `duration_seconds` = total time (agent + judge)
- Separate fields enable timing-based tiebreaking
- Both fields required (not optional) for consistency

### 2. Update Serialization

**File**: `src/scylla/e2e/models.py:RunResult.to_dict()`

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "duration_seconds": self.duration_seconds,
        "agent_duration_seconds": self.agent_duration_seconds,
        "judge_duration_seconds": self.judge_duration_seconds,
        # ... other fields
    }
```

### 3. Track Timing During Execution

**File**: `src/scylla/e2e/subtest_executor.py`

```python
# Agent execution
agent_start = datetime.now(UTC)
result = self.adapter.run(config=adapter_config, ...)
duration = (datetime.now(UTC) - agent_start).total_seconds()

# Judge evaluation
if not agent_ran and _has_valid_judge_result(run_dir):
    # Reused judge result
    judgment = _load_judge_result(judge_dir)
    judge_duration = 0.0  # Duration not tracked for reused results
else:
    # Fresh judge run
    judge_start = datetime.now(UTC)
    judgment = self._run_judge(...)
    judge_duration = (datetime.now(UTC) - judge_start).total_seconds()

# Create RunResult with both durations
run_result = RunResult(
    duration_seconds=duration + judge_duration,  # Total
    agent_duration_seconds=duration,
    judge_duration_seconds=judge_duration,
    # ... other fields
)
```

**Critical Decision**: Set `judge_duration = 0.0` when reusing cached results
- Consistent with `agent_duration = 0.0` for cached agent results
- Prevents misleading timing data in reports

### 4. Update Checkpoint Resume

**File**: `src/scylla/e2e/subtest_executor.py`

```python
# Load from saved run_result.json
with open(run_result_file) as f:
    report_data = json.load(f)

run_result = RunResult(
    duration_seconds=report_data["duration_seconds"],
    agent_duration_seconds=report_data["agent_duration_seconds"],
    judge_duration_seconds=report_data["judge_duration_seconds"],
    # ... other fields
)
```

### 5. Update Report Generation

**File**: `src/scylla/e2e/run_report.py`

```python
def generate_run_report(
    # ... existing params
    duration_seconds: float,
    agent_duration_seconds: float | None = None,
    judge_duration_seconds: float | None = None,
) -> str:
    lines = [
        "| Duration (Total) | {duration_seconds:.2f}s |",
    ]

    # Add breakdown if available
    if agent_duration_seconds is not None and judge_duration_seconds is not None:
        lines.extend([
            "| - Agent | {agent_duration_seconds:.2f}s |",
            "| - Judge | {judge_duration_seconds:.2f}s |",
        ])
```

**Report Output**:
```markdown
| Metric | Value |
|--------|-------|
| Duration (Total) | 23.45s |
| - Agent          | 18.20s |
| - Judge          | 5.25s  |
```

### 6. Update Tests

**File**: `tests/unit/e2e/test_models.py`

```python
def test_to_dict(self) -> None:
    result = RunResult(
        duration_seconds=15.5,
        agent_duration_seconds=12.0,
        judge_duration_seconds=3.5,
        # ... other fields
    )

    d = result.to_dict()
    assert d["duration_seconds"] == 15.5
    assert d["agent_duration_seconds"] == 12.0
    assert d["judge_duration_seconds"] == 3.5
```

## Failed Attempts

| Approach | Why It Failed | Lesson Learned |
|----------|---------------|----------------|
| **Make timing fields optional** | Initial consideration to make `agent_duration_seconds` and `judge_duration_seconds` optional for backward compatibility | User explicitly requested "ignore old formats, just focus on new format, don't need to worry about compatibility" - clean breaks are acceptable when explicitly requested |
| **Only track total duration** | Original implementation only had `duration_seconds` | Cannot support tiebreaker use case or identify performance bottlenecks without component-level timing |

## Results & Parameters

### Data Model Changes

**RunResult fields** (all required):
```python
duration_seconds: float              # Total time (agent + judge)
agent_duration_seconds: float        # Agent execution time
judge_duration_seconds: float        # Judge evaluation time
```

### Timing Semantics

| Scenario | agent_duration | judge_duration | duration_seconds |
|----------|----------------|----------------|------------------|
| Fresh run | Actual time | Actual time | Sum of both |
| Cached agent | 0.0 | 0.0 or actual | Sum |
| Cached judge | Actual | 0.0 | Sum |
| Both cached | 0.0 | 0.0 | 0.0 |

### Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `src/scylla/e2e/models.py` | +4 | Add timing fields to RunResult |
| `src/scylla/e2e/subtest_executor.py` | +8 | Track and pass timing data |
| `src/scylla/e2e/run_report.py` | +15 | Display timing breakdown in reports |
| `tests/unit/e2e/test_models.py` | +6 | Verify timing serialization |

### Test Results

```bash
✅ All 97 E2E unit tests passing
```

## Key Learnings

1. **User-Driven Design**: When user explicitly states no backward compatibility needed, implement clean solution without migration complexity
2. **Consistent Semantics**: Set timing to 0.0 for cached results across both agent and judge for consistency
3. **Breakdown Visibility**: Showing timing breakdown in reports (Total + Agent + Judge) helps identify bottlenecks
4. **Required vs Optional**: Making new fields required prevents null-handling complexity in analysis code

## Use Cases

1. **Tiebreaker Ranking**: When multiple results have identical scores, use `duration_seconds` to prefer faster executions
2. **Performance Analysis**: Compare `agent_duration_seconds` across tiers to identify which configurations are fastest
3. **Bottleneck Identification**: High `judge_duration_seconds` indicates judging is slow, may need caching or optimization
4. **Cost Optimization**: Correlate timing with cost to find cost-per-second metrics

## Related Skills

- `execution-stage-logging` - Stage-by-stage logging with timing (more granular)
- `e2e-checkpoint-resume` - Checkpoint system that stores timing data
- `e2e-resume-refactor` - Directory structure for agent/judge separation

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | PR #143 - Separate agent/judge timing for tiebreaker ranking | [notes.md](../../references/notes.md) |
