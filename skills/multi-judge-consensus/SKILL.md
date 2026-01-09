# Skill: Multi-Judge Consensus in E2E Evaluation

| Aspect | Details |
|--------|---------|
| **Date** | 2026-01-08 |
| **Objective** | Add support for multiple LLM judges with consensus voting to E2E evaluation framework |
| **Outcome** | ✅ Successfully implemented multi-judge support with consensus scoring, per-judge reporting, and clean shutdown handling |
| **Category** | Evaluation Infrastructure |
| **Repository** | ProjectScylla |
| **PR** | https://github.com/HomericIntelligence/ProjectScylla/pull/160 |

## When to Use This Skill

Use this skill when you need to:

1. **Add multi-judge support** to any evaluation system that currently uses a single judge
2. **Implement consensus voting** across multiple LLM evaluators
3. **Design per-judge reporting** with individual results and aggregate consensus
4. **Fix multiprocessing shutdown issues** with clean Ctrl+C handling
5. **Extend CLI tools** to support optional repeated arguments (e.g., `--add-judge`)

Trigger conditions:
- User wants multiple judges to evaluate the same output for consensus
- User needs to see individual judge reasoning alongside aggregate scores
- User wants clean exit from multiprocessing workers (no stack traces)
- User wants flexible CLI options with shortcuts (e.g., `--add-judge sonnet-4-5`)

## Verified Workflow

### Phase 1: CLI Argument Design

**Goal:** Add flexible `--add-judge` argument that supports shortcuts and defaults

**Steps:**
1. Add argument with `action="append"` and `nargs="?"` for optional values
   ```python
   parser.add_argument(
       "--add-judge",
       action="append",
       nargs="?",  # Optional value
       const="claude-opus-4-5-20251101",  # Default if flag given without value
       metavar="MODEL",
       help="Add additional judge model. Examples: --add-judge, --add-judge sonnet-4-5"
   )
   ```

2. Create model name resolver for shortcuts:
   ```python
   def resolve_judge_model(model_shorthand: str) -> str:
       shortcuts = {
           "opus-4-5": "claude-opus-4-5-20251101",
           "sonnet-4-5": "claude-sonnet-4-5-20250929",
           "haiku-4-5": "claude-haiku-4-0-20250514",
       }
       return shortcuts.get(model_shorthand, model_shorthand)
   ```

3. Build judge list in config:
   ```python
   judge_models = [args.judge_model]  # Primary judge
   if args.add_judge:
       for model in args.add_judge:
           judge_models.append(resolve_judge_model(model))
   ```

**Result:** Users can run `--add-judge`, `--add-judge sonnet-4-5`, or multiple `--add-judge` flags

### Phase 2: Data Model Updates

**Goal:** Store multiple judge results and consensus scores

**Steps:**
1. Change config from single `judge_model: str` to `judge_models: list[str]`
   ```python
   judge_models: list[str] = field(
       default_factory=lambda: ["claude-opus-4-5-20251101"]
   )
   ```

2. Create `JudgeResultSummary` dataclass:
   ```python
   @dataclass
   class JudgeResultSummary:
       model: str
       score: float | None = None
       passed: bool | None = None
       grade: str | None = None
       reasoning: str | None = None
       judge_number: int = 1
   ```

3. Update `RunResult` to store both consensus and individual judges:
   ```python
   judge_score: float  # Consensus score
   judge_passed: bool  # Majority vote
   judge_grade: str    # Grade from consensus
   judges: list[JudgeResultSummary] = field(default_factory=list)
   ```

4. **CRITICAL:** Add backward compatibility in `load()` method:
   ```python
   # Backward compatibility: convert old judge_model to judge_models
   if "judge_model" in data and "judge_models" not in data:
       judge_models = [data["judge_model"]]
   else:
       judge_models = data.get("judge_models", ["claude-opus-4-5-20251101"])
   ```

**Critical:** Optional fields with `field(default_factory=...)` must come AFTER required fields in dataclasses

### Phase 3: Judge Execution with Consensus

**Goal:** Run multiple judges and compute consensus scores

**Steps:**
1. Implement consensus calculation (simple average + majority vote):
   ```python
   def _compute_judge_consensus(
       self, judges: list[JudgeResultSummary]
   ) -> tuple[float | None, bool | None, str | None]:
       if not judges:
           return (None, None, None)

       valid = [j for j in judges if j.score is not None]
       if not valid:
           return (None, None, None)

       # Simple average for scores
       consensus_score = sum(j.score for j in valid) / len(valid)

       # Majority vote for passed
       passed_votes = sum(1 for j in valid if j.passed)
       passed = passed_votes > len(valid) / 2

       # Convert score to grade
       grade = score_to_grade(consensus_score)

       return (consensus_score, passed, grade)
   ```

2. Loop through judges with separate directories:
   ```python
   def _run_judge(self, ...) -> tuple[dict, list[JudgeResultSummary]]:
       judges = []
       for judge_num, model in enumerate(self.config.judge_models, start=1):
           judge_result = run_llm_judge(
               workspace=workspace,
               task_prompt=task_prompt,
               agent_output=stdout,
               model=model,
               judge_dir=judge_dir,
               judge_run_number=judge_num,  # Creates judge_01/, judge_02/, etc.
           )
           judge_summary = JudgeResultSummary(
               model=model,
               score=judge_result.score,
               passed=judge_result.passed,
               grade=judge_result.grade,
               reasoning=judge_result.reasoning,
               judge_number=judge_num,
           )
           judges.append(judge_summary)

       consensus_score, consensus_passed, consensus_grade = self._compute_judge_consensus(judges)
       consensus_dict = {
           "score": consensus_score,
           "passed": consensus_passed,
           "grade": consensus_grade,
           "reasoning": judges[0].reasoning if judges else "",
       }
       return consensus_dict, judges
   ```

**Result:** Each judge writes to separate subdirectories, consensus computed from all results

### Phase 4: Report Generation

**Goal:** Show consensus summary and individual judge tables

**Steps:**
1. Detect multi-judge vs single-judge:
   ```python
   if judges and len(judges) > 1:
       # Multi-judge report
   else:
       # Single-judge report (backward compatible)
   ```

2. Generate consensus summary:
   ```markdown
   ## Judge Evaluation (Consensus)

   | Metric | Value |
   |--------|-------|
   | Score | {score:.3f} |
   | Grade | {grade} |
   | Passed | ✅/❌ |
   ```

3. Generate per-judge tables with links:
   ```markdown
   ### Individual Judges

   #### Judge 1: claude-opus-4-5-20251101

   | Metric | Value |
   |--------|-------|
   | Score | {judge.score:.3f} |
   | Passed | ✅/❌ |
   | Grade | {judge.grade} |

   **Reasoning:** {judge.reasoning}

   - [View judgment](./judge/judge_01/judgment.json)
   - [View result JSON](./judge/judge_01/result.json)
   ```

**Result:** Reports show both aggregate consensus and individual judge details

### Phase 5: Clean Shutdown Handling

**Goal:** Fix Ctrl+C to exit cleanly without stack traces from child processes

**Steps:**
1. Import `BrokenProcessPool` from correct module:
   ```python
   from concurrent.futures.process import BrokenProcessPool  # NOT from concurrent.futures
   ```

2. Wrap `ProcessPoolExecutor` in try/except:
   ```python
   try:
       with ProcessPoolExecutor(max_workers=...) as executor:
           # Execute subtests
           for future in as_completed(futures):
               # Process results
   except (KeyboardInterrupt, BrokenProcessPool):
       # Clean exit on Ctrl+C or process pool failure
       logger.warning("Experiment interrupted, cleaning up...")
       # Cancel pending futures
       for future in futures:
           if not future.done():
               future.cancel()
   ```

3. Add exception handling in runner:
   ```python
   except (KeyboardInterrupt, BrokenProcessPool) as e:
       if isinstance(e, KeyboardInterrupt):
           logger.warning("Shutdown requested (Ctrl+C), cleaning up...")
       else:
           logger.warning("Process pool interrupted, cleaning up...")
   ```

**Result:** Ctrl+C shows single "Shutdown requested" message, no stack traces

### Phase 6: Judge Prompt Enhancement

**Goal:** Require judges to explain why points are deducted

**Steps:**
1. Update Phase 3 instructions:
   ```markdown
   - notes: **REQUIRED** - Explain your score. For scores below 1.0, you MUST clearly
     explain what is missing or incorrect and why points were deducted. Be specific
     about what needs to be fixed or improved.
   ```

2. Update JSON schema examples to emphasize explanation requirement

**Result:** Judges now explicitly state what's missing and why scores are reduced

## Failed Attempts

### ❌ Attempt 1: Import BrokenProcessPool from concurrent.futures

**What we tried:**
```python
from concurrent.futures import BrokenProcessPool
```

**Why it failed:**
`ImportError: cannot import name 'BrokenProcessPool' from 'concurrent.futures'`

**Root cause:**
`BrokenProcessPool` is defined in `concurrent.futures.process`, not the top-level `concurrent.futures` module. Python's import system doesn't automatically expose all submodule exceptions.

**Correct approach:**
```python
from concurrent.futures.process import BrokenProcessPool
```

**Lesson:** Always check the actual module hierarchy for exception classes in standard library

### ❌ Attempt 2: Place judges field before required fields

**What we tried:**
```python
@dataclass
class RunResult:
    judge_reasoning: str
    judges: list[JudgeResultSummary] = field(default_factory=list)  # Optional field
    workspace_path: Path  # Required field
```

**Why it failed:**
```
TypeError: non-default argument 'workspace_path' follows default argument 'judges'
```

**Root cause:**
Dataclass fields with defaults (including `field(default_factory=...)`) must come AFTER fields without defaults. Python processes field definitions sequentially and can't have required positional arguments after optional ones.

**Correct approach:**
```python
@dataclass
class RunResult:
    judge_reasoning: str
    workspace_path: Path  # Required fields first
    judges: list[JudgeResultSummary] = field(default_factory=list)  # Optional fields last
```

**Lesson:** Always place optional dataclass fields (with defaults or `field()`) after all required fields

### ❌ Attempt 3: Forgetting backward compatibility in load()

**What we initially did:**
Changed `judge_model` to `judge_models` without updating the `load()` method

**Why it failed:**
Existing saved configs and tests still used the old `judge_model` field, causing:
```
TypeError: ExperimentConfig.__init__() got an unexpected keyword argument 'judge_model'
```

**Root cause:**
The `load()` method was still trying to pass `judge_model` to the constructor, but the parameter had been renamed to `judge_models`.

**Correct approach:**
```python
# Backward compatibility: convert old judge_model to judge_models
if "judge_model" in data and "judge_models" not in data:
    judge_models = [data["judge_model"]]
else:
    judge_models = data.get("judge_models", ["claude-opus-4-5-20251101"])
```

**Lesson:** When renaming fields in dataclasses that are persisted, always add backward compatibility in the `load()` method

## Results & Parameters

### Successful Multi-Judge Execution

**Command:**
```bash
pixi run python scripts/run_e2e_experiment.py \
    --tiers-dir tests/fixtures/tests/test-001 \
    --tiers T0 \
    --runs 1 \
    --add-judge sonnet-4-5 \
    --add-judge haiku-4-5
```

**Result:**
- 3 judges executed: opus-4-5 (primary), sonnet-4-5, haiku-4-5
- Directory structure: `judge_01/`, `judge_02/`, `judge_03/`
- Consensus score: simple average of all judge scores
- Consensus passed: majority vote (2 out of 3 = passed)
- Report shows both consensus summary and individual judge tables

### Clean Ctrl+C Behavior

**Before fix:**
```
^C[multiple stack traces from ProcessPoolExecutor workers]
Exception in thread Thread-1:
Traceback (most recent call last):
  [50+ lines of stack traces from child processes]
```

**After fix:**
```
^C2026-01-08 15:43:35 [WARNING] scylla.e2e.runner: Shutdown requested (Ctrl+C), cleaning up...
```

### Consensus Calculation Parameters

**Algorithm:**
- **Score:** Simple average of all valid judge scores
- **Passed:** Majority vote (>50% of judges must pass)
- **Grade:** Computed from consensus score using standard grading scale

**Grading Scale:**
- S: 1.00
- A: 0.80 - 0.99
- B: 0.60 - 0.79
- C: 0.40 - 0.59
- D: 0.20 - 0.39
- F: 0.00 - 0.19

**Example:**
- Judge 1 (Opus): 0.90 (A), passed ✅
- Judge 2 (Sonnet): 0.80 (A), passed ✅
- Judge 3 (Haiku): 0.70 (B), passed ✅
- **Consensus:** 0.80 (A), passed ✅ (3/3 judges passed)

## Files Modified

| File | Changes |
|------|---------|
| `scripts/run_e2e_experiment.py` | Added `--add-judge` argument, model resolver, config assembly |
| `src/scylla/e2e/models.py` | `judge_model` → `judge_models`, added `JudgeResultSummary`, updated `RunResult`, added backward compatibility |
| `src/scylla/e2e/subtest_executor.py` | Multi-judge loop, consensus calculation, clean shutdown handling |
| `src/scylla/e2e/runner.py` | Exception handling for clean Ctrl+C |
| `src/scylla/e2e/run_report.py` | Per-judge tables with links, consensus summary |
| `src/scylla/judge/prompts.py` | Updated prompt to require deduction explanations |
| `tests/unit/e2e/test_resume.py` | Updated fixture to use `judge_models` |

## Key Insights

1. **Consensus is simpler than you think:** Simple average + majority vote works well for LLM judges. Don't over-engineer.

2. **Directory structure matters:** Using `judge_run_number` parameter to create separate directories (judge_01/, judge_02/) makes multi-judge support clean and backward compatible.

3. **Dataclass field ordering is strict:** Optional fields must always come after required fields, regardless of whether they use `field(default_factory=...)` or simple defaults.

4. **Import hierarchy is important:** Exception classes in Python stdlib may not be at the top-level module. Always check submodules.

5. **CLI flexibility improves UX:** `nargs="?"` with `const=` allows both `--add-judge` (default) and `--add-judge model-name` (explicit), making the tool more user-friendly.

6. **Clean shutdown requires multiple layers:** You need exception handling in both the executor (where futures are managed) and the runner (where the executor is called).

7. **Backward compatibility is free:** By checking `if judges and len(judges) > 1`, single-judge behavior remains unchanged, making this a zero-risk addition.

8. **Backward compatibility in load() is critical:** When renaming fields that are persisted, always add migration logic in the `load()` method to handle old data formats.

## Testing Checklist

- [x] Single judge still works (backward compatibility)
- [x] `--add-judge` adds default opus-4-5
- [x] `--add-judge sonnet-4-5` resolves shortcut correctly
- [x] Multiple `--add-judge` flags stack correctly
- [x] Consensus score is simple average of all judges
- [x] Consensus passed uses majority vote
- [x] Report shows consensus summary for multi-judge
- [x] Report shows individual judge tables with links
- [x] Ctrl+C exits cleanly without stack traces
- [x] Judge directories created correctly (judge_01/, judge_02/)
- [x] Judge prompt includes deduction explanations
- [x] Unit tests pass with backward compatibility

## Related Skills

- `judge-protocol` - Base judge evaluation protocol
- `e2e-evaluation-framework` - E2E testing infrastructure
- `consensus-algorithms` - Voting and aggregation methods
- `clean-multiprocessing-shutdown` - Handling process pool interruptions

## References

- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/160
- Python docs: `argparse.nargs="?"` behavior
- Python docs: `concurrent.futures.process.BrokenProcessPool`
- Python docs: dataclass field ordering
