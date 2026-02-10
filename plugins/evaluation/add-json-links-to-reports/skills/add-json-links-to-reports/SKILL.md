---
name: "Adding JSON Links to Markdown Reports"
description: "Add JSON result links to markdown reports for structured data access"
category: evaluation
date: 2026-01-08
user-invocable: false
---
# Adding JSON Links to Markdown Reports

## Overview

| Item | Details |
|------|---------|
| Date | 2026-01-08 |
| Objective | | Attribute | Value | |-----------|-------| | **Date** | 2026-01-08 | | **Objective** | Add links to JSON result files in markdown reports for easy... |
| Outcome | Operational |


| Attribute | Value |
|-----------|-------|
| **Date** | 2026-01-08 |
| **Objective** | Add links to JSON result files in markdown reports for easy access to structured data |
| **Outcome** | ✅ Successfully added JSON links to run reports for both judge and agent results |
| **Files Modified** | `scylla/e2e/run_report.py` |
| **Tests Status** | ✅ All 28 tests passing |

## When to Use This Skill

Use this skill when you need to:

- **Add structured data links** to markdown reports in an evaluation framework
- **Enhance report navigation** by linking to raw JSON results alongside human-readable outputs
- **Maintain backward compatibility** while adding new links to existing report sections
- **Work with hierarchical report structures** (run → subtest → tier → experiment)

### Trigger Conditions

- User requests JSON data access from markdown reports
- Need to expose structured evaluation results (scores, tokens, costs) in machine-readable format
- Reports need both human-readable (markdown/text) and machine-readable (JSON) views
- Working with LLM evaluation frameworks that generate both detailed and simplified results

## Verified Workflow

### 1. Understand the Report Structure

First, identify the report generation code and understand the directory structure:

```bash
# Find report generation code
grep -r "generate.*report|save.*report" scylla/e2e/

# Understand the path structure
cat scylla/e2e/paths.py  # Shows agent/ and judge/ directory constants
```

**Key Discovery**: Reports use a consistent structure:
- `agent/result.json` - Simplified agent execution result
- `agent/output.txt` - Full agent output
- `judge/result.json` - Simplified judge result (score, passed, grade, reasoning)
- `judge/judgment.json` - Full detailed judgment

### 2. Locate the Markdown Generation Function

Find where markdown report sections are generated:

```python
# In scylla/e2e/run_report.py
def generate_run_report(
    tier_id: str,
    subtest_id: str,
    run_number: int,
    # ... other parameters
) -> str:
    """Generate markdown report content for a single run."""
```

**Key Sections**:
- Line ~150-165: Judge Evaluation section
- Line ~240-252: Agent Output section

### 3. Add JSON Links Using Bullet Lists

Modify the sections to use bullet lists for multiple links:

```python
# Before (single link):
lines.extend([
    "## Judge Evaluation",
    "",
    "[View full judgment](./judge/judgment.json)",
    "",
])

# After (bullet list with JSON link):
lines.extend([
    "## Judge Evaluation",
    "",
    "- [View full judgment](./judge/judgment.json)",
    "- [View judge result JSON](./judge/result.json)",
    "",
])
```

**Pattern**: Use relative paths with `./` prefix for consistency

### 4. Verify Changes with Test Generation

Create a verification script using the existing report generator:

```python
from pathlib import Path
from scylla.e2e.run_report import generate_run_report

report = generate_run_report(
    tier_id='T0',
    subtest_id='test-01',
    run_number=1,
    score=0.85,
    grade='B',
    passed=True,
    reasoning='Good implementation',
    cost_usd=0.15,
    duration_seconds=45.2,
    tokens_input=1000,
    tokens_output=500,
    exit_code=0,
    task_prompt='Test task',
    workspace_path=Path('/tmp/test'),
)

# Verify new links exist
assert '- [View judge result JSON](./judge/result.json)' in report
assert '- [View agent result JSON](./agent/result.json)' in report
```

### 5. Run Existing Tests

Ensure no regressions:

```bash
pixi run pytest tests/unit/reporting/test_markdown.py -v
```

**Expected**: All tests should pass (28/28) since we're only adding, not changing existing content.

## Failed Attempts


| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| Initial approach | See details below | Refer to notes in this section |

### ❌ Attempt 1: Using Task Tool for Exploration

**What we tried**: Using the Task tool with `subagent_type=Explore` to understand the codebase structure.

**Why it failed**: User interrupted the exploration, preferring direct file searches.

**Lesson**: For well-structured codebases with clear naming conventions, direct `Glob` and `Grep` searches are faster than agent-based exploration.

### ❌ Attempt 2: Wrong String Matching in Edit

**What we tried**: First Edit call used incorrect indentation/spacing in the `old_string` parameter.

**Error**: `String to replace not found in file`

**Root cause**: The lines had specific spacing that didn't match our string pattern.

**Solution**: Read the file at the exact line range to copy the correct indentation:
```python
# Read to get exact formatting
Read(file_path="...", offset=148, limit=30)
# Then use exact string from output
```

**Lesson**: When using Edit tool, always read the exact lines first to capture correct indentation and formatting.

## Results & Parameters

### Changes Made

**File**: `scylla/e2e/run_report.py`

**Judge Section (lines 160-164)**:
```python
lines.extend([
    "---",
    "",
    "## Judge Evaluation",
    "",
    "- [View full judgment](./judge/judgment.json)",
    "- [View judge result JSON](./judge/result.json)",
    "",
])
```

**Agent Section (lines 245-252)**:
```python
lines.extend([
    "---",
    "",
    "## Agent Output",
    "",
    "- [View agent output](./agent/output.txt)",
    "- [View agent result JSON](./agent/result.json)",
    "",
])
```

### Output Format

Generated markdown now includes:

```markdown
## Judge Evaluation

- [View full judgment](./judge/judgment.json)
- [View judge result JSON](./judge/result.json)

---

## Agent Output

- [View agent output](./agent/output.txt)
- [View agent result JSON](./agent/result.json)
```

### Test Results

```
============================= test session starts ==============================
tests/unit/reporting/test_markdown.py::TestTierMetrics::test_create PASSED
[... 26 more tests ...]
============================== 28 passed in 0.09s ==============================
```

## Key Takeaways

1. **Relative paths are key**: Use `./` prefix for relative links within report directories
2. **Bullet lists for multiple links**: More readable than inline links when showing multiple related files
3. **Backward compatibility**: Adding new links doesn't break existing tests or functionality
4. **Consistent structure**: Both judge and agent sections follow the same pattern (text + JSON)
5. **Fast verification**: Generate sample reports programmatically to verify changes

## Related Files

- `scylla/e2e/paths.py` - Path constants and helpers for agent/judge directories
- `scylla/e2e/subtest_executor.py` - Where agent and judge results are saved
- `scylla/e2e/llm_judge.py` - Creates `judgment.json` files
- `tests/unit/reporting/test_markdown.py` - Report generation tests

## Next Steps

If you need to extend this pattern:

1. **Add more result files**: Follow the same bullet list pattern
2. **Add to higher-level reports**: Apply to subtest/tier/experiment reports
3. **Add preview sections**: Consider inline JSON snippets in markdown
4. **Add validation**: Check that linked files actually exist before generating links
