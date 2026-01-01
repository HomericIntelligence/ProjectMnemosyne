---
name: e2e-judge-rubric-design
description: "Design LLM-as-Judge evaluation rubrics for E2E agent testing"
category: evaluation
source: ProjectScylla
date: 2026-01-01
---

# E2E Judge Rubric Design

Design comprehensive evaluation rubrics for LLM-as-Judge systems in agent testing frameworks.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-01-01 | Fix false positives in E2E judge and expand evaluation criteria | 10-criteria weighted rubric, validity tracking, PR #104 merged |

## When to Use

- (1) Building agent evaluation systems that use LLM-as-Judge
- (2) Designing weighted scoring criteria for code generation tasks
- (3) Need to distinguish "invalid evaluation" from "evaluated and failed"
- (4) Standardizing judge prompts across multiple test runs
- (5) Handling rate limits and API errors in evaluation pipelines

## Verified Workflow

### 1. Design Weighted Criteria Categories

Organize criteria into weighted categories for balanced evaluation:

```yaml
criteria_weights:
  functional: 0.50      # Core functionality
  code_quality: 0.30    # Structure, docs, style
  security: 0.20        # Safety and error handling
```

### 2. Define Specific Criteria Per Category

**Functional (50%)**:
- `correctness` - Does the code work as intended?
- `completeness` - Were all requirements satisfied?
- `edge_case_handling` - Are boundary conditions handled?
- `following_instructions` - Did agent follow specific instructions?

**Code Quality (30%)**:
- `code_structure` - Well-organized? (CC < 15, LOC < 50, nesting < 4)
- `documentation` - Docstrings, comments present and accurate?
- `linting_compliance` - Follows language style guidelines?
- `testability` - Clear inputs/outputs, mockable dependencies?

**Security & Safety (20%)**:
- `security` - No secrets, injection vulnerabilities, unsafe patterns?
- `error_handling` - Graceful failures, meaningful messages?

### 3. Set Explicit Pass Thresholds

```yaml
pass_threshold:
  score: 0.7           # Weighted average must be >= 0.7
  correctness: 0.8     # AND correctness must be >= 0.8

score_bands:
  excellent: [0.9, 1.0]    # Production ready
  good: [0.8, 0.89]        # Minor improvements
  acceptable: [0.7, 0.79]  # Some issues but functional
  marginal: [0.6, 0.69]    # Significant issues
  failing: [0.0, 0.59]     # Does not meet requirements
```

### 4. Add Validity Tracking

Distinguish "couldn't evaluate" from "evaluated and failed":

```python
@dataclass
class JudgeResult:
    score: float
    passed: bool
    grade: str
    reasoning: str
    is_valid: bool = True  # False if evaluation couldn't complete
    criteria_scores: dict[str, float] | None = None
```

### 5. Handle API Errors First

**Critical**: Check `is_error` BEFORE `subtype` in fallback logic:

```python
def _fallback_judge(agent_output: str) -> JudgeResult:
    data = json.loads(agent_output)

    # Check is_error FIRST - rate limits have BOTH
    # "subtype": "success" AND "is_error": true
    if data.get("is_error"):
        return JudgeResult(
            score=0.0, passed=False, grade="N/A",
            reasoning=f"Invalid: {data.get('result')}",
            is_valid=False  # Mark as invalid, not failed
        )

    # Only check success if no error
    if data.get("subtype") == "success":
        return JudgeResult(score=0.7, passed=True, ...)
```

### 6. Use Checked-In System Prompt

Store judge prompt in version control for consistency:

```python
JUDGE_SYSTEM_PROMPT_FILE = Path("config/judge/system_prompt.md")

cmd = [
    "claude",
    "--model", "claude-opus-4-5-20251101",
    "--system-prompt-file", str(JUDGE_SYSTEM_PROMPT_FILE),
    "--max-turns", "1",
    evaluation_context,
]
```

## Results & Parameters

### Complete Judge Configuration

```yaml
# Judge model settings
judge:
  model: claude-opus-4-5-20251101  # REQUIRED: Opus for accuracy
  timeout: 1200                     # 20 minutes for complex evals
  system_prompt_file: config/judge/system_prompt.md

# Evaluation rubric
rubric:
  categories:
    functional:
      weight: 0.50
      criteria:
        - correctness
        - completeness
        - edge_case_handling
        - following_instructions
    code_quality:
      weight: 0.30
      criteria:
        - code_structure
        - documentation
        - linting_compliance
        - testability
    security:
      weight: 0.20
      criteria:
        - security
        - error_handling

# Pass/fail thresholds
thresholds:
  pass_score: 0.7
  min_correctness: 0.8

# Code quality benchmarks
quality_limits:
  cyclomatic_complexity: 15
  function_loc: 50
  nesting_depth: 4
```

### System Prompt Template

```markdown
# LLM Judge System Prompt

You are an expert evaluator for AI agent task completion.

## Evaluation Criteria

### Functional Criteria (Weight: 50%)
1. **Correctness**: Does the code work as intended?
2. **Completeness**: Were all requirements satisfied?
3. **Edge Case Handling**: Are boundary conditions handled?
4. **Following Instructions**: Did agent follow specific instructions?

### Code Quality Criteria (Weight: 30%)
5. **Code Structure**: Well-organized? (CC < 15, LOC < 50)
6. **Documentation**: Docstrings present and accurate?
7. **Linting Compliance**: Follows style guidelines?
8. **Testability**: Clear inputs/outputs, mockable?

### Security & Safety Criteria (Weight: 20%)
9. **Security**: No secrets, injection vulnerabilities?
10. **Error Handling**: Graceful failures?

## Response Format
{
  "score": 0.78,
  "passed": true,
  "reasoning": "...",
  "criteria_scores": { ... }
}
```

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|------------|--------|
| Check `subtype` before `is_error` | Rate-limited runs have BOTH `"subtype": "success"` AND `"is_error": true` - marked as passing | Always check error conditions FIRST |
| 120s timeout for judge | Opus model needs more time for thorough evaluation | Use 20 minutes (1200s) for Opus |
| Pass prompt as CLI argument | Shell argument length limits; hard to maintain | Use `--system-prompt-file` with checked-in file |
| 4 generic criteria | Missing security, testability, edge cases - incomplete evaluation | Expand to 10 criteria across weighted categories |
| Single pass threshold (score only) | Low correctness could still pass with high style scores | Require BOTH score >= 0.7 AND correctness >= 0.8 |
| No validity tracking | Couldn't distinguish "rate limited" from "failed evaluation" | Add `is_valid` field to JudgeResult |

## Error Handling

| Problem | Solution |
|---------|----------|
| Rate limit hit during judging | Return `is_valid=False` with reason, don't mark as pass/fail |
| Judge timeout | Increase to 20 minutes; Opus needs time for thorough analysis |
| Malformed JSON response | Parse with fallback; extract pass/fail from text if needed |
| Missing criteria scores | Use partial scores; mark evaluation as degraded |

## References

- [G-Eval Framework](https://www.confident-ai.com/blog/g-eval-the-definitive-guide) - LLM-as-Judge with CoT
- [ICER 2025: Rubric Is All You Need](https://dl.acm.org/doi/10.1145/3702652.3744220) - Question-specific rubrics
- [LLM-as-Judge Guide](https://labelyourdata.com/articles/llm-as-a-judge) - Bias handling
- ProjectScylla PR #104 - Implementation of this pattern
