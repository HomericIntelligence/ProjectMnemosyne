# E2E Judge Rubric Design - Session Notes

## Context

This skill was extracted from a debugging session in ProjectScylla where E2E test results were showing false positives due to incorrect error handling in the LLM judge fallback logic.

## Original Problem

When running E2E experiments:
```bash
pixi run python scripts/run_e2e_experiment.py \
  --repo https://github.com/octocat/Hello-World \
  --commit 7fd1a60 \
  --prompt tests/fixtures/tests/test-001/prompt.md \
  --tiers T0 T1 \
  --runs 2
```

Rate-limited runs were being marked as PASS with score 0.7 because the Claude CLI output had:
```json
{
  "type": "result",
  "subtype": "success",
  "is_error": true,
  "result": "You've hit your limit"
}
```

The fallback judge checked `subtype == "success"` before `is_error`, so it returned a passing result.

## Key Code Changes

### llm_judge.py - Fallback Logic Fix

```python
# BEFORE (buggy)
def _fallback_judge(agent_output):
    data = json.loads(agent_output)
    if data.get("subtype") == "success":  # Checked first!
        return JudgeResult(score=0.7, passed=True, ...)
    elif data.get("is_error"):
        return JudgeResult(score=0.0, passed=False, ...)

# AFTER (fixed)
def _fallback_judge(agent_output):
    data = json.loads(agent_output)
    # Check is_error FIRST
    if data.get("is_error"):
        return JudgeResult(score=0.0, passed=False, is_valid=False, ...)
    if data.get("subtype") == "success":
        return JudgeResult(score=0.7, passed=True, is_valid=True, ...)
```

### JudgeResult - Added is_valid Field

```python
@dataclass
class JudgeResult:
    score: float
    passed: bool
    grade: str
    reasoning: str
    is_valid: bool = True  # NEW: False if evaluation couldn't complete
    criteria_scores: dict[str, float] | None = None
    raw_response: str | None = None
```

### _call_claude_judge - System Prompt File

```python
JUDGE_SYSTEM_PROMPT_FILE = Path(__file__).parent.parent.parent.parent / "config" / "judge" / "system_prompt.md"

cmd = [
    "claude",
    "--model", model,
    "--print",
    "--output-format", "text",
    "--dangerously-skip-permissions",
    "--max-turns", "1",
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),  # NEW
    evaluation_context,
]

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=1200,  # 20 minutes (was 120s)
    env={**os.environ},
)
```

## Rubric Evolution

### Original (4 criteria)
1. Correctness
2. Completeness
3. Quality (generic)
4. Following Instructions

### Final (10 criteria, weighted)

**Functional (50%)**:
1. Correctness - Does code work?
2. Completeness - All requirements met?
3. Edge Case Handling - Boundaries handled?
4. Following Instructions - Specific instructions followed?

**Code Quality (30%)**:
5. Code Structure - CC < 15, LOC < 50, nesting < 4
6. Documentation - Docstrings present?
7. Linting Compliance - PEP8/style followed?
8. Testability - Mockable, clear I/O?

**Security & Safety (20%)**:
9. Security - No secrets, no injection?
10. Error Handling - Graceful failures?

## Research Sources

- G-Eval: https://www.confident-ai.com/blog/g-eval-the-definitive-guide
- ICER 2025 Paper: https://dl.acm.org/doi/10.1145/3702652.3744220
- LLM-as-Judge Biases: https://labelyourdata.com/articles/llm-as-a-judge

## Files Modified

- `src/scylla/e2e/llm_judge.py` - Bug fixes and improvements
- `config/judge/system_prompt.md` - New standardized rubric

## PR Reference

ProjectScylla PR #104: https://github.com/HomericIntelligence/ProjectScylla/pull/104
