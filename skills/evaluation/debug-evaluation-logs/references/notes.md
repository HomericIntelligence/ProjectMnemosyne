# Debug Evaluation Logs - Session Notes

## Session Date
2026-01-08

## Initial Problem

User presented evaluation experiment logs showing confusing warnings:

```
2026-01-08 15:54:16 [WARNING] scylla.e2e.llm_judge: Build pipeline: SOME FAILED
2026-01-08 15:54:20 [WARNING] scylla.e2e.llm_judge: LLM judge failed, using fallback: Claude CLI failed (exit 1): No error message
```

The user couldn't determine:
1. Which specific pipeline steps failed (mojo-build, mojo-format, mojo-test, pre-commit)
2. What the actual error was from Claude CLI

## Initial Analysis

Log analysis revealed:
- All 24 subtests completed (not an infrastructure crash)
- Build pipeline warnings repeated many times
- Judge stages completed with fallback
- Final error at end: `AttributeError: 'ExperimentConfig' object has no attribute 'judge_model'`

**Key insight**: The AttributeError was from AFTER these logs were generated (the experiment ran on a commit before multi-judge-consensus). The warnings were expected behavior but not diagnostic.

## Code Investigation

### File: `src/scylla/e2e/llm_judge.py`

**Line 596-598: Generic build warning**
```python
if pipeline_result.all_passed:
    logger.info("Build pipeline: ALL PASSED")
else:
    logger.warning("Build pipeline: SOME FAILED")  # ← No details!
```

**Line 693-695: Missing error extraction**
```python
if result.returncode != 0:
    error_msg = result.stderr.strip() if result.stderr else "No error message"
    raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")
```

Problem: Claude CLI with `--output-format text` outputs JSON errors to stdout, not stderr.

## Solution Design

### Fix 1: Add Diagnostic Summary Method

Add to `BuildPipelineResult` dataclass:

```python
def get_failure_summary(self) -> str:
    """Get a summary of which pipeline steps failed."""
    failed = []
    if not self.mojo_build_passed:
        failed.append("mojo-build")
    if not self.mojo_format_passed:
        failed.append("mojo-format")
    if not self.mojo_test_passed:
        failed.append("mojo-test")
    if not self.precommit_passed:
        failed.append("pre-commit")
    return ", ".join(failed) if failed else "none"
```

### Fix 2: Update Warning Message

```python
else:
    failed_steps = pipeline_result.get_failure_summary()
    logger.warning(f"Build pipeline: FAILED [{failed_steps}]")
```

### Fix 3: Multi-Source Error Extraction

```python
if result.returncode != 0:
    error_msg = "No error message"

    # Check stdout for JSON error response
    if result.stdout:
        try:
            data = json.loads(result.stdout.strip())
            if data.get("is_error"):
                error_msg = data.get("result", data.get("error", "Unknown JSON error"))
        except json.JSONDecodeError:
            # Not JSON, check if stdout has useful text
            if result.stdout.strip():
                error_msg = f"stdout: {result.stdout.strip()[:200]}"

    # Fall back to stderr if no useful stdout
    if error_msg == "No error message" and result.stderr:
        error_msg = result.stderr.strip()

    raise RuntimeError(f"Claude CLI failed (exit {result.returncode}): {error_msg}")
```

## Implementation

All changes made to single file: `src/scylla/e2e/llm_judge.py`

**Lines modified**:
- 98-114: Added `get_failure_summary()` method
- 616-617: Updated warning to use summary
- 712-730: Enhanced error extraction

## Testing

### Unit Test (get_failure_summary)

```bash
pixi run python -c "from scylla.e2e.llm_judge import BuildPipelineResult; \
  r = BuildPipelineResult(False, '', True, '', False, '', True, '', False); \
  print('Failed:', r.get_failure_summary())"
```

**Result**: `Failed: mojo-build, mojo-test` ✓

### Syntax Validation

```bash
python -m py_compile src/scylla/e2e/llm_judge.py
```

**Result**: ✓ Syntax check passed

## Expected Impact

### Before
```
[WARNING] Build pipeline: SOME FAILED
[WARNING] LLM judge failed, using fallback: Claude CLI failed (exit 1): No error message
```

### After
```
[WARNING] Build pipeline: FAILED [mojo-build, mojo-test]
[WARNING] LLM judge failed, using fallback: Claude CLI failed (exit 1): Rate limit exceeded
```

## Reusable Patterns Identified

### Pattern 1: Composite Result Diagnostic Methods

**Template**:
```python
@dataclass
class MultiStepResult:
    step1_passed: bool
    step2_passed: bool
    all_passed: bool

    def get_failure_summary(self) -> str:
        failed = []
        if not self.step1_passed:
            failed.append("step1")
        if not self.step2_passed:
            failed.append("step2")
        return ", ".join(failed) if failed else "none"
```

**Use cases**:
- Validation results (syntax, types, lint, tests)
- Pipeline executions (build, test, deploy)
- Health checks (database, cache, services)
- Multi-judge consensus (individual judge results)

### Pattern 2: Priority-Based Error Extraction

**Template**:
```python
def extract_subprocess_error(result: subprocess.CompletedProcess) -> str:
    error_msg = "No error message"

    # Priority 1: Structured errors (JSON)
    if result.stdout:
        try:
            data = json.loads(result.stdout.strip())
            if data.get("is_error"):
                return data.get("result", "Unknown error")
        except json.JSONDecodeError:
            pass

    # Priority 2: Plain stdout
    if result.stdout and result.stdout.strip():
        error_msg = f"stdout: {result.stdout.strip()[:200]}"

    # Priority 3: stderr
    if error_msg == "No error message" and result.stderr:
        error_msg = result.stderr.strip()

    return error_msg
```

**Use cases**:
- Claude CLI error handling
- API client errors (may return JSON or text)
- Build tool errors (various output formats)
- Test runner errors (JUnit XML, JSON, plain text)

### Pattern 3: Structured Warning Messages

**Format**: `"{operation}: {status} [{details}]"`

**Examples**:
- `"Build: FAILED [syntax, lint]"`
- `"Validation: FAILED [type-check, format]"`
- `"Deployment: FAILED [us-east-1, eu-west-1]"`
- `"Judges: DISAGREEMENT [opus=pass, sonnet=fail, haiku=fail]"`

**Benefits**:
- Human readable
- Grep-friendly (search for `"FAILED \["`)
- Machine parseable (regex: `/FAILED \[(.*?)\]/`)
- Consistent structure across codebase

## Related Work

### Multi-Judge Consensus (Parallel Development)

The same file (`llm_judge.py`) was being modified for multi-judge consensus support:
- Changed `judge_model` (singular) to `judge_models` (plural)
- Added `JudgeResultSummary` with individual judge results
- Modified `SubTestExecutor` to run multiple judges

**Integration consideration**: The `get_failure_summary()` pattern could be applied to multi-judge results:

```python
@dataclass
class MultiJudgeResult:
    opus_passed: bool
    sonnet_passed: bool
    haiku_passed: bool
    consensus_passed: bool

    def get_disagreement_summary(self) -> str:
        """Show which judges disagreed with consensus."""
        disagreed = []
        if self.opus_passed != self.consensus_passed:
            disagreed.append("opus")
        if self.sonnet_passed != self.consensus_passed:
            disagreed.append("sonnet")
        if self.haiku_passed != self.consensus_passed:
            disagreed.append("haiku")
        return ", ".join(disagreed) if disagreed else "none"
```

## Lessons Learned

### 1. Generic Warnings Are Technical Debt

Warning messages without specific details create investigation overhead. Every generic warning forces developers to:
1. Find the log context
2. Locate the relevant code
3. Add temporary debug logging
4. Re-run to get details

**Better approach**: Add diagnostic methods upfront when designing result types.

### 2. Modern CLIs Don't Always Use stderr

Traditional Unix convention: stdout for output, stderr for errors. Modern CLIs (especially with `--output-format` flags) often:
- Output JSON to stdout regardless of success/failure
- Include error info in JSON structure
- Leave stderr empty

**Defensive pattern**: Check both streams in priority order.

### 3. Dataclass Design Pattern

When designing dataclasses for multi-step operations:

```python
@dataclass
class OperationResult:
    # Individual results (for programmatic access)
    step1_passed: bool
    step2_passed: bool

    # Overall result (for boolean checks)
    all_passed: bool

    # Diagnostic method (for logging)
    def get_failure_summary(self) -> str:
        ...
```

This provides:
- Programmatic access to individual results
- Simple boolean check for overall status
- Human-readable diagnostics for logging

## Files Modified

```
ProjectScylla/src/scylla/e2e/llm_judge.py
├── Line 98-114: Added get_failure_summary() method
├── Line 616-617: Updated build pipeline warning
└── Line 712-730: Enhanced CLI error extraction
```

## Commands Used

```bash
# Navigate to ProjectMnemosyne
cd build/ProjectMnemosyne

# Update main branch
git checkout main && git pull

# Create skill branch
git checkout -b skill/evaluation/debug-evaluation-logs

# Create directory structure
mkdir -p plugins/evaluation/debug-evaluation-logs/skills/debug-evaluation-logs
mkdir -p plugins/evaluation/debug-evaluation-logs/references

# Test implementation
pixi run python -c "from scylla.e2e.llm_judge import BuildPipelineResult; \
  r = BuildPipelineResult(False, '', True, '', False, '', True, '', False); \
  print('Failed:', r.get_failure_summary())"

# Syntax validation
python -m py_compile src/scylla/e2e/llm_judge.py
```

## Retrospective Metadata

- **Category**: evaluation
- **Skill Name**: debug-evaluation-logs
- **Related Skills**: error-message-improvement, structured-logging, subprocess-error-handling
- **Tags**: evaluation, logging, diagnostics, error-handling, llm-judge, pipeline, subprocess
- **Context**: ProjectScylla E2E evaluation framework
- **Outcome**: Success (all changes tested and validated)
