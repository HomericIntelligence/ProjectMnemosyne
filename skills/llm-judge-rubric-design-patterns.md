---
name: llm-judge-rubric-design-patterns
description: "Use when: (1) designing or extending LLM-as-Judge rubrics for agent evaluation, (2) reducing judge score variance beyond 10%, (3) implementing multi-judge consensus or hybrid scoring, (4) adding fair-baseline regression detection, (5) consolidating grading-scale definitions, (6) hardening judge worker pools against API rate limits, (7) improving diagnostic clarity of judge pipeline logs"
category: evaluation
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: llm-judge-rubric-design-patterns.history
tags:
  - llm-judge
  - rubric
  - evaluation
  - grading
  - consensus
  - rate-limit
  - baseline
  - variance
  - hybrid-scoring
  - processpool
---

# LLM Judge Rubric Design Patterns

Comprehensive guide to designing, implementing, and operating LLM-as-Judge evaluation systems:
rubric criteria, hybrid scoring, multi-judge consensus, baseline regression detection,
grading-scale standardisation, and resilient judge worker pools.

## Overview

| Date | Objective | Outcome |
| ---------- | --------- | ------- |
| 2026-01-01 | Weighted 10-criteria rubric with validity tracking | PR #104 merged |
| 2026-01-04 | Proportionality criteria + invalid-result detection | PR #145 merged |
| 2025-12-31 | Consensus-retry, cleanup evaluation, container orchestration | 4 PRs, 89 tests |
| 2026-01-08 | Multi-judge consensus, per-judge reporting, clean shutdown | PR #160 merged |
| 2026-01-10 | Hybrid 80/20 scoring: variance 14% → 6% | Operational |
| 2025-02-15 | Baseline pipeline regression detection | 367 lines, 100% tests |
| 2026-01-19 | Grading deduplication, single source of truth | 241 lines removed |
| 2026-01-02 | Industry-aligned S/A/B/C/D/F scale | Centralised |
| 2026-01-08 | Actionable build-pipeline and CLI error messages | Operational |
| 2026-01-10 | 3-layer ProcessPoolExecutor rate-limit defence | PR #168 merged |

## When to Use

1. Building a new LLM-as-Judge evaluation system from scratch
2. Adding criteria (proportionality, scope discipline, test quality) to an existing rubric
3. Score variance for identical outputs exceeds 10% — apply hybrid 80/20 split
4. Need multiple judges with consensus voting and majority-vote pass/fail
5. Evaluation unfairly penalises agents for pre-existing pipeline failures
6. Duplicate `GradeScale` classes / inconsistent S-grade threshold across modules
7. Replacing academic A=95% grading with production-readiness semantics
8. Build-pipeline warnings are generic; CLI error messages say "No error message"
9. Parallel judge workers crash entire ProcessPoolExecutor under API rate-limit pressure
10. Extending a judge system with new modules (cleanup evaluator, cross-tier analysis)

## Verified Workflow

### Quick Reference

```bash
# Run multi-judge evaluation (3 judges, 3 runs, check variance)
pixi run python scripts/run_e2e_experiment.py \
  --tiers-dir tests/fixtures/tests/test-001 \
  --tiers T0 --runs 3 --parallel 3 \
  --add-judge sonnet-4-5 --add-judge haiku-4-5

# Check variance and grade distribution
jq '.summary | {mean: .mean_score, std_dev, distribution: .grade_distribution}' \
  results/latest/T0/*/report.json

# Verify grading is single-source
grep -r "def.*grade\|assign.*grade\|GradeScale" src/

# Run baseline regression unit tests
pixi run pytest tests/unit/e2e/test_baseline_regression.py -v

# Test rate-limit safe wrapper
pixi run pytest tests/unit/e2e/test_rate_limit_recovery.py::TestRunSubtestInProcessSafe -v
```

### Phase 1 — Design the Rubric

Organise criteria into weighted categories with a hybrid 80/20 split to balance
objectivity with engineering judgment:

```yaml
# tests/fixtures/tests/<task>/expected/rubric.yaml
categories:
  functional:
    weight: 0.35
    scoring_type: "checklist"   # Objective, measurable
    items:
      - id: F1
        check: "File exists in workspace root"
        points: 1.0
      - id: F2
        check: "Code executes without errors"
        points: 1.0

  code_quality:
    weight: 0.20
    scoring_type: "checklist"
    items:
      - id: Q1
        check: "Python syntax is valid"
        points: 1.0

  proportionality:
    weight: 0.15
    scoring_type: "checklist"
    items:
      - id: P1
        check: "Files are proportionate to task complexity"
        points: 1.0

  build_pipeline:
    weight: 0.10
    scoring_type: "checklist"
    items:
      - id: B1
        check: "Build passes (or was already failing in baseline)"
        points: 1.0
        na_condition: "Build already failed in baseline"

  overall_quality:
    weight: 0.20          # Subjective component (20%)
    scoring_type: "subjective"
    items:
      - id: OQ1
        check: "Overall engineering judgment: appropriateness, maintainability, clarity"
        points: 2.0       # Larger scale for granularity

grading:
  pass_threshold: 0.60
  grade_scale:
    S: 1.00   # Amazing — above and beyond
    A: 0.80   # Excellent — production ready
    B: 0.60   # Good — minor improvements possible
    C: 0.40   # Acceptable — functional with issues
    D: 0.20   # Marginal — significant issues
    F: 0.00   # Failing — does not meet requirements
```

**Key Principles**:
- Checklist categories: binary/near-binary scoring (sum ≥ 80% of total weight)
- Subjective category: continuous 0–2.0 scale with anchored examples (≤ 20% weight)
- S grade is ONLY for exactly 1.0; `>= 1.0` threshold is wrong
- Proportionality criteria penalise BOTH over-engineering AND under-engineering

#### Extended Criteria (add when needed)

```python
# Proportionality & Scope additions (weight 1.0 each, total weight 12.5 → 15.5)
EvaluationCategory.WORKSPACE_CLEANLINESS  # Files proportionate to task complexity
EvaluationCategory.TEST_QUALITY           # Tests appropriate and valuable
EvaluationCategory.SCOPE_DISCIPLINE       # Solution appropriately scoped
```

### Phase 2 — Configure the Judge System Prompt

Store judge prompt in version control (`config/judge/system_prompt.md`):

```markdown
## Evaluation Methodology

### Two Scoring Types

1. **Checklist Categories** (`scoring_type: "checklist"`)
   - Award ANY value between 0 and max (not limited to 0, 0.5, 1.0)
   - Proportional: 0.3, 0.7, 0.85, etc.

2. **Subjective Categories** (`scoring_type: "subjective"`)
   - Continuous scale (0.0 to 2.0)
   - Anchored examples: 2.0=Exceptional, 1.7=Excellent, 1.4=Good,
     1.0=Acceptable, 0.6=Marginal, 0.3=Poor, 0.0=Unacceptable

### Baseline Regression Handling

<baseline_regression>
Baseline pipeline results (before agent) and post-agent results are provided.

- **Regressions** (passed → failed): Penalise heavily — agent broke working functionality.
- **Pre-existing failures** (failed → failed): Mark rubric item N/A, do not penalise.
- **Improvements** (failed → passed): Recognise positively.
</baseline_regression>

### Deduction Explanations

For notes below 1.0, you MUST clearly explain what is missing or incorrect and
why points were deducted. Be specific.
```

### Phase 3 — Add Baseline Regression Detection

Capture pipeline state once before the first run, persist for checkpoint resume:

```python
# scylla/e2e/subtest_executor.py
pipeline_baseline: "BuildPipelineResult | None" = None

for run_num in range(1, config.runs_per_subtest + 1):
    if pipeline_baseline is None:
        pipeline_baseline = _load_pipeline_baseline(results_dir)
        if pipeline_baseline is None:
            pipeline_baseline = _run_build_pipeline(workspace, language)
            _save_pipeline_baseline(results_dir, pipeline_baseline)

    run_result = self._execute_single_run(..., pipeline_baseline=pipeline_baseline)
```

```python
def _save_pipeline_baseline(results_dir: Path, result: "BuildPipelineResult") -> None:
    (results_dir / "pipeline_baseline.json").write_text(
        json.dumps(result.model_dump(), indent=2)
    )

def _load_pipeline_baseline(results_dir: Path) -> "BuildPipelineResult | None":
    from scylla.e2e.llm_judge import BuildPipelineResult
    p = results_dir / "pipeline_baseline.json"
    if not p.exists():
        return None
    try:
        return BuildPipelineResult(**json.loads(p.read_text()))
    except Exception as e:
        logger.warning(f"Failed to load baseline: {e}")
        return None
```

Use `TYPE_CHECKING` for forward declarations to avoid circular imports.

### Phase 4 — Implement Multi-Judge Consensus

```python
# CLI: --add-judge flag with model shortcuts
parser.add_argument(
    "--add-judge", action="append", nargs="?",
    const="claude-opus-4-5-20251101", metavar="MODEL",
)

SHORTCUTS = {
    "opus-4-5": "claude-opus-4-5-20251101",
    "sonnet-4-5": "claude-sonnet-4-5-20250929",
    "haiku-4-5": "claude-haiku-4-0-20250514",
}

# Consensus: simple average + majority vote
def _compute_judge_consensus(judges):
    valid = [j for j in judges if j.score is not None]
    consensus_score = sum(j.score for j in valid) / len(valid)
    passed = sum(1 for j in valid if j.passed) > len(valid) / 2
    return consensus_score, passed, score_to_grade(consensus_score)
```

Each judge writes to a separate directory (`judge_01/`, `judge_02/`, …).
Always add backward compatibility in `load()` when renaming persisted fields.

### Phase 5 — Harden Worker Pool Against Rate Limits

Three-layer defence:

```python
# Layer 1: Pre-flight check before each tier
rate_limit_info = check_api_rate_limit_status()
if rate_limit_info:
    wait_for_rate_limit(rate_limit_info.retry_after_seconds, checkpoint, path)

# Layer 2: Safe wrapper — worker NEVER crashes the pool
def _run_subtest_in_process_safe(*args, **kwargs) -> SubTestResult:
    try:
        return _run_subtest_in_process(*args, **kwargs)
    except RateLimitError as e:
        return SubTestResult(..., rate_limit_info=e.info)
    except Exception as e:
        return SubTestResult(..., selection_reason=f"WorkerError: {e}")

# Layer 3: BrokenProcessPool recovery with retry
except BrokenProcessPool:
    rate_info = _detect_rate_limit_from_results(results, results_dir)
    if rate_info:
        wait_for_rate_limit(rate_info.retry_after_seconds, ...)
        remaining = [s for s in subtests
                     if s.id not in results
                     or results[s.id].selection_reason.startswith("RateLimitError:")]
        results.update(_retry_with_new_pool(remaining, max_retries=3))
```

Multi-source rate-limit detection: check `SubTestResult.rate_limit_info`, then
`selection_reason`, then `.failed/` directory logs.

### Phase 6 — Improve Diagnostic Log Messages

```python
# Add summary method to composite result objects
@dataclass
class BuildPipelineResult:
    def get_failure_summary(self) -> str:
        failed = [name for name, ok in [
            ("build", self.build_passed),
            ("format", self.format_passed),
            ("test", self.test_passed),
        ] if not ok]
        return ", ".join(failed) if failed else "none"

# Usage
logger.warning(f"Build pipeline: FAILED [{pipeline_result.get_failure_summary()}]")

# Multi-source error extraction for subprocesses
def extract_subprocess_error(result) -> str:
    if result.stdout:
        try:
            data = json.loads(result.stdout.strip())
            if data.get("is_error"):
                return data.get("result", "Unknown JSON error")
        except json.JSONDecodeError:
            if result.stdout.strip():
                return f"stdout: {result.stdout.strip()[:200]}"
    return result.stderr.strip() if result.stderr else "No error message"
```

### Phase 7 — Consolidate Grading to Single Source of Truth

```python
# scylla/metrics/grading.py — single canonical implementation
DEFAULT_PASS_THRESHOLD = 0.60

def assign_letter_grade(score: float) -> str:
    assert 0.0 <= score <= 1.0, f"Score must be in [0,1], got {score}"
    if score == 1.0:  return "S"  # EXACT 1.0 only
    if score >= 0.80: return "A"
    if score >= 0.60: return "B"
    if score >= 0.40: return "C"
    if score >= 0.20: return "D"
    return "F"
```

Delete all other `GradeScale` classes and `assign_letter_grade()` methods.
Export `DEFAULT_PASS_THRESHOLD` from `metrics/__init__.py`.

### Phase 8 — Extend the System with New Modules

Pattern for adding capabilities (consensus-retry, cleanup evaluator, container orchestration):

1. Read existing module to understand integration points and data structures
2. Create new module file with Pydantic `BaseModel` for config validation
3. Add comprehensive docstrings
4. Export from `__init__.py` (both import and `__all__`)
5. Create dedicated test file; mock external deps (Docker, adapters)

```python
class ConsensusConfig(BaseModel):
    initial_runs: int = Field(default=3, ge=1)
    max_additional_runs: int = Field(default=5, ge=0)
    variance_threshold: float = Field(default=0.15, ge=0.0, le=1.0)

class JudgeContainerConfig:
    agent_workspace: Path   # mount READ-ONLY
    output_dir: Path        # mount read-write
    timeout_seconds: int = 600
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Pure checklist rubric (100%) | All criteria discrete 0/0.5/1 | Too rigid; environmental noise penalised agents; no engineering judgment | Need 20% subjective component for holistic quality assessment |
| Pure subjective grading | Vague criteria "code quality 0-1" | 14% variance for identical outputs; no reference points | Objective anchors are required to reduce variance |
| Discrete-only scoring (0, 0.5, 1) | Limited judges to three values | Lost granularity; "good but not perfect" collapsed to 0.5 | Continuous scoring with anchored examples is essential |
| 50/50 checklist/subjective split | Equal objective/subjective weight | Too much subjective increased variance | 80/20 split is optimal; majority must be objective |
| S grade threshold >= 1.0 | Used `>= 1.0` for S grade | Score 0.97 incorrectly graded S | S grade requires exactly `== 1.0` |
| RateLimitError exception-only handling | `except RateLimitError: wait_and_retry()` | Worker crashes before clean exception; pool throws `BrokenProcessPool` | Need safe wrapper that catches exceptions before worker process exits |
| Detecting rate limits only from exceptions | Catch `RateLimitError` in execution path | Errors manifest as generic subprocess crashes; error buried in stderr | Multi-source detection required: exceptions + structured results + .failed/ dirs |
| Single retry attempt on BrokenProcessPool | Create new pool, retry once | Rate limit can persist; no wait between retries | Retry loop with max_retries=3 and proper wait |
| Checking only `is_error` fallback logic | `if data.get("is_error")` without checking first | Rate-limited responses have both `"subtype": "success"` AND `"is_error": true` | Check `is_error` BEFORE `subtype` in fallback |
| Importing BuildPipelineResult at module top | Direct module-level import | Circular import between `subtest_executor` and `llm_judge` | Use `TYPE_CHECKING` guard + runtime import inside functions |

## Results & Parameters

### Canonical Grading Scale (Industry-Aligned)

| Grade | Threshold | Label | Production Action |
| ----- | --------- | ----- | ----------------- |
| S | == 1.00 | Amazing | Ship immediately |
| A | >= 0.80 | Excellent | Ship with confidence |
| B | >= 0.60 | Good | Ship after minor fixes |
| C | >= 0.40 | Acceptable | Rework required |
| D | >= 0.20 | Marginal | Significant rework |
| F | >= 0.00 | Failing | Start over |

```python
DEFAULT_PASS_THRESHOLD = 0.60   # B = passing
```

### Variance Reduction Results

| Metric | Before | After | Target |
| ------ | ------ | ----- | ------ |
| Variance (identical outputs) | 14% | 6% | <10% |
| Score range | 0.74–0.88 | 0.81–0.87 | ±0.05 |
| Scoring resolution | 3 values | Continuous | >10 distinct |

### Rate-Limit Recovery Configuration

```python
max_retries: int = 3
default_wait_seconds: int = 60
buffer_multiplier: float = 1.1  # Add 10% to Retry-After header
preflight_test_command = ["claude", "--print", "ping"]
preflight_timeout = 30
```

### Judge Model Shortcuts

```python
SHORTCUTS = {
    "opus-4-5":   "claude-opus-4-5-20251101",
    "sonnet-4-5": "claude-sonnet-4-5-20250929",
    "haiku-4-5":  "claude-haiku-4-0-20250514",
}
```

### Baseline Pipeline Summary Structure

```python
{
    "all_passed": bool,
    "build_passed": bool,
    "format_passed": bool,
    "test_passed": bool,
}
# File: {results_dir}/pipeline_baseline.json
```

### Consensus Defaults

```python
ConsensusConfig(
    initial_runs=3,
    max_additional_runs=5,
    variance_threshold=0.15,
    min_confidence=0.6,
    score_range_threshold=0.3,
)
```

### Cleanup Evaluator Scores

```python
SCORE_FULL_CLEANUP    = 1.0
SCORE_PARTIAL_CLEANUP = 0.7
SCORE_SCRIPT_FAILED   = 0.4
SCORE_NO_SCRIPT       = 0.0
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectScylla | PR #104 — initial rubric design | e2e-judge-rubric-design |
| ProjectScylla | PR #145 — proportionality criteria | judge-criteria-enhancement |
| ProjectScylla | PRs ×4 — system extensions | judge-system-extension |
| ProjectScylla | PR #160 — multi-judge consensus | multi-judge-consensus |
| ProjectScylla | Variance 14%→6% | skill-hybrid-llm-judge-with-granular-scoring |
| ProjectScylla | PR #705 — baseline regression | fair-evaluation-baseline |
| ProjectScylla | Grading dedup — 241 lines removed | grading-consolidation |
| ProjectScylla | Industry grading scale | industry-grading-scale |
| ProjectScylla | Diagnostic log improvements | debug-evaluation-logs |
| ProjectScylla | PR #168 — rate-limit recovery | processpoolexecutor-rate-limit-recovery |

## References

- [G-Eval Framework](https://www.confident-ai.com/blog/g-eval-the-definitive-guide)
- [ICER 2025: Rubric Is All You Need](https://dl.acm.org/doi/10.1145/3702652.3744220)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [LLM-as-Judge Guide](https://labelyourdata.com/articles/llm-as-a-judge)
- Python docs: `concurrent.futures.process.BrokenProcessPool`
