# Skill: Deduplicate LLM JSON Extraction

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-02-12 |
| **Objective** | Fix LLM judge parsing bug with Haiku model + deduplicate 3 identical JSON extraction implementations |
| **Outcome** | ✅ SUCCESS - Bug fixed, code deduplicated, 16 tests added, all quality checks passed |
| **Issue** | #503 |
| **PR** | #505 |
| **Category** | Refactoring |

## When to Use This Skill

Apply this pattern when you encounter:

1. **Identical or near-identical code** in multiple modules (3+ occurrences)
2. **Bug exists in one implementation** but not others with same logic
3. **Copy-paste propagation risk** - when fixing one, others get missed
4. **Maintenance burden** - need to update logic in multiple places
5. **Missing test coverage** - implementations lack comprehensive tests

**Trigger signals**:
- Finding same regex patterns in multiple files
- Same algorithm (e.g., brace-matching) duplicated across modules
- Bug report affects one consumer but identical code exists elsewhere
- Code review comments about "we have this same logic in X, Y, Z"

## Problem Context

When running e2e experiments with `--judge-model haiku`, the LLM judge returned JSON wrapped in `<json_evaluation>` XML tags with preamble text. The parser in `scylla/e2e/llm_judge.py` only handled markdown code blocks, causing failures.

**Root cause discovered**: The codebase had **3 separate implementations** of JSON extraction from LLM responses:

| Location | Strategy | Handles XML? | Bug? |
|----------|----------|--------------|------|
| `scylla/e2e/llm_judge.py:1038-1084` | Markdown code blocks only | ❌ | **YES** |
| `scylla/judge/parser.py:267-308` | Code blocks + brace-matching | ✅ | No |
| `scylla/judge/evaluator.py:474-519` | Code blocks + brace-matching | ✅ | No |

Two implementations had the robust solution, one didn't. Classic deduplication opportunity.

## Verified Workflow

### Step 1: Identify Duplicate Implementations

**Tools**: `grep`, `Grep` tool

```bash
# Search for similar patterns
grep -r "json.loads" scylla/
grep -r "```json" scylla/
grep -r "re.search.*json" scylla/
```

**What to look for**:
- Same regex patterns (e.g., `` r"```(?:json)?\s*(\{[\s\S]*?\})\s*```" ``)
- Same algorithmic structure (find opening brace, match depth, extract substring)
- Same error handling patterns
- Comments describing same functionality

### Step 2: Choose the Best Implementation as Source

**Selection criteria** (in order):
1. ✅ **Most robust** - handles the most edge cases
2. ✅ **Best tested** - has existing test coverage
3. ✅ **Most recent** - likely to have latest fixes
4. ✅ **Clearest code** - easiest to understand and maintain

In this case: `parser.py:267-308` was chosen (identical to `evaluator.py`, both more robust than `llm_judge.py`)

### Step 3: Extract to Shared Utility Module

**File naming pattern**: `<module>/utils.py` for module-level utilities

**Created**: `scylla/judge/utils.py`

**Key decisions**:
- ✅ Use descriptive name: `extract_json_from_llm_response()`
- ✅ Add comprehensive docstring with examples
- ✅ Include all edge cases in docstring
- ✅ Keep same signature as original functions

**Template**:
```python
"""Shared utilities for <module>-related operations."""

import <required-imports>


def extract_json_from_llm_response(output: str) -> dict[str, Any] | None:
    r"""Extract a JSON object from LLM output text.

    Handles multiple common LLM response formats:
    - Raw JSON objects
    - JSON in markdown code blocks (```json or ```)
    - JSON wrapped in XML tags with preamble text
    - JSON with leading/trailing text

    This function uses a robust brace-matching algorithm to extract JSON
    objects even when surrounded by explanatory text or XML tags.

    Args:
        output: Raw LLM output text that may contain JSON.

    Returns:
        Parsed JSON dictionary, or None if no valid JSON object found.

    Examples:
        >>> extract_json_from_llm_response('{"score": 5}')
        {'score': 5}

        >>> extract_json_from_llm_response('```json\n{"score": 5}\n```')
        {'score': 5}

    """
    # [Paste the most robust implementation here]
```

**Critical**: Use `r"""` for docstrings with backslashes (ruff will complain otherwise)

### Step 4: Update Module Exports

**Edit**: `<module>/__init__.py`

```python
from <module>.utils import extract_json_from_llm_response

__all__ = [
    # ... existing exports ...
    # Utils
    "extract_json_from_llm_response",
]
```

### Step 5: Update All Consumers

**Pattern for each consumer**:

**Before** (full implementation):
```python
def _extract_json(self, output: str) -> dict[str, Any] | None:
    """Extract JSON object from output text."""
    # 40+ lines of duplicate logic
    json_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", output)
    # ... brace matching ...
    # ... error handling ...
    return json.loads(output[start:end])
```

**After** (delegation):
```python
from <module>.utils import extract_json_from_llm_response

def _extract_json(self, output: str) -> dict[str, Any] | None:
    """Extract JSON object from output text."""
    return extract_json_from_llm_response(output)
```

**For standalone functions** (like `_parse_judge_response`):
```python
# Before: 40+ lines of extraction + validation
# After:
data = extract_json_from_llm_response(response)
if data is None:
    raise ValueError("Judge response does not contain valid JSON...")
# ... keep existing validation logic ...
```

### Step 6: Write Comprehensive Tests

**Create**: `tests/unit/<module>/test_utils.py`

**Test coverage checklist**:
- ✅ Raw JSON (happy path)
- ✅ JSON in markdown code blocks (`` ```json `` and `` ``` ``)
- ✅ JSON wrapped in XML tags with preamble
- ✅ JSON with preamble text (no tags)
- ✅ JSON with trailing text
- ✅ No JSON in output (returns None)
- ✅ Malformed JSON (returns None)
- ✅ Unbalanced braces (returns None)
- ✅ Nested JSON objects
- ✅ JSON with arrays
- ✅ Complex real-world LLM responses
- ✅ Empty string
- ✅ Whitespace only
- ✅ Escaped quotes in strings
- ✅ Multiple JSON objects (extracts first)

**Template**:
```python
"""Tests for <module> utility functions."""

import pytest
from <module>.utils import extract_json_from_llm_response


class TestExtractJsonFromLlmResponse:
    """Tests for extract_json_from_llm_response utility."""

    def test_raw_json_happy_path(self):
        """Test extraction of raw JSON object."""
        output = '{"score": 5, "passed": true}'
        result = extract_json_from_llm_response(output)
        assert result == {"score": 5, "passed": True}

    def test_json_wrapped_in_xml_tags_with_preamble(self):
        """Test extraction from XML-wrapped JSON with preamble text."""
        output = """Here is the evaluation result:
<json_evaluation>
{"score": 0.8, "passed": true, "reasoning": "Good work"}
</json_evaluation>
"""
        result = extract_json_from_llm_response(output)
        assert result == {
            "score": 0.8,
            "passed": True,
            "reasoning": "Good work",
        }
```

### Step 7: Add Integration Tests

**Update**: `tests/unit/<module>/test_<consumer>.py`

Add tests for the **originally failing case**:

```python
def test_parse_judge_response_handles_xml_wrapped_json(self) -> None:
    """Test _parse_judge_response handles XML-wrapped JSON with preamble text."""
    response = """Here is the evaluation result:
<json_evaluation>
{"score": 0.8, "passed": true, "reasoning": "Good work"}
</json_evaluation>
"""
    result = _parse_judge_response(response)
    assert result.score == 0.8
    assert result.passed is True
    assert result.reasoning == "Good work"
```

### Step 8: Verification Checklist

Run in this exact order:

```bash
# 1. New utility tests
pixi run python -m pytest tests/unit/<module>/test_utils.py -v

# 2. Integration tests (updated consumer tests)
pixi run python -m pytest tests/unit/<module>/test_<consumer>.py::<TestClass> -v

# 3. Full test suite (ensure no regressions)
pixi run python -m pytest tests/ -q

# 4. Pre-commit hooks (code quality)
pre-commit run --files <changed-files>
```

**Expected results**:
- ✅ All new tests pass
- ✅ All integration tests pass (including new cases)
- ✅ Full test suite passes (or pre-existing failures documented)
- ✅ Pre-commit hooks pass (ruff, black, mypy)

### Step 9: Commit and PR

**Commit message format**:
```
refactor(<module>): deduplicate <functionality> & fix <bug>

## Problem
[Description of bug + duplication discovery]

## Solution
Created shared `<utility_function>()` utility in `<module>/utils.py` that:
- [Feature 1]
- [Feature 2]
- [Feature 3]

Updated all N consumers to use the shared utility:
- `<file1>` - fixes the original bug
- `<file2>` - removes duplicate code
- `<file3>` - removes duplicate code

## Changes
- NEW: <new files>
- EDIT: <modified files>

## Verification
✓ New utility tests pass (X/X)
✓ Integration tests pass (Y/Y)
✓ Full test suite passes (Z/total)
✓ Pre-commit hooks pass

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**PR workflow**:
```bash
git checkout -b fix-<description>
git add <files>
git commit -m "..."
git push -u origin fix-<description>
gh pr create --title "..." --body "..." --label "bug,refactor"
gh pr merge --auto --rebase
```

## Failed Attempts & Lessons Learned

### ❌ Attempt 1: Fix Only the Broken Implementation

**What we tried**: Initially considered just fixing the bug in `llm_judge.py` by copying the brace-matching logic.

**Why it failed**: Would have created a **4th** duplicate implementation. Future bugs would require fixing 4 places instead of 1.

**Lesson**: When you find duplicate code during bug fixing, **always deduplicate first** rather than propagating the fix.

### ⚠️ Pitfall: Updating Error Messages Without Checking Tests

**What happened**: Changed error message from `"Judge response is not valid JSON"` to `"Judge response does not contain valid JSON"`.

**Impact**: Broke existing test that expected the old message.

**Fix**: Updated test expectations in `test_subtest_executor.py:220` to match new message.

**Lesson**: When changing error messages, always grep for tests that assert on those messages:
```bash
grep -r "Judge response is not valid JSON" tests/
```

### ⚠️ Pitfall: Docstring Backslashes Without Raw String

**What happened**: Linter (ruff) failed with `D301 Use r""" if any backslashes in a docstring`.

**Why**: Docstring had `` `\n` `` in examples without using raw string prefix.

**Fix**: Changed `"""` to `r"""` for the docstring.

**Lesson**: Always use `r"""` for docstrings containing backslashes, even in examples.

### ✅ Success: Identifying Pre-existing Test Failures

**What happened**: Full test suite showed 2 failures in `executor/test_agent_container.py`.

**Investigation**: Stashed changes, ran tests on main branch → same failures.

**Conclusion**: Pre-existing failures unrelated to our changes.

**Lesson**: Always verify test failures by checking if they exist on main branch:
```bash
git stash
pixi run python -m pytest <failing-test> -q
git stash pop
```

## Results & Parameters

### Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `scylla/judge/utils.py` | 68 | Shared JSON extraction utility |
| `tests/unit/judge/test_utils.py` | 149 | Comprehensive test suite |

### Files Modified

| File | Lines Changed | Purpose |
|------|---------------|---------|
| `scylla/judge/__init__.py` | +2 | Export new utility |
| `scylla/e2e/llm_judge.py` | -24, +11 | Use shared utility (fixes bug) |
| `scylla/judge/parser.py` | -41, +1 | Delegate to shared utility |
| `scylla/judge/evaluator.py` | -46, +1 | Delegate to shared utility |
| `tests/unit/e2e/test_subtest_executor.py` | +22 | Add integration tests |

**Net change**: +273 additions, -113 deletions (160 net lines)

### Test Results

```
✅ New utility tests: 16/16 passed
✅ Integration tests: 5/5 passed
✅ Full test suite: 1775/1777 passed
   ⚠️  2 pre-existing failures in executor (unrelated)
✅ Pre-commit hooks: All passed
```

### Deduplication Metrics

| Metric | Value |
|--------|-------|
| **Duplicate implementations removed** | 2 |
| **Lines of duplicate code removed** | ~87 lines |
| **New shared utility** | 1 function |
| **Test coverage added** | 16 tests |
| **Consumers updated** | 3 |

## Key Takeaways

1. **Bug in one → Check for duplicates**: When fixing a bug, always search for duplicate implementations that may have the same issue (or the fix).

2. **Deduplicate during bug fix**: Don't just fix the bug in one place — consolidate the logic to prevent future drift.

3. **Choose the most robust implementation**: When deduplicating, pick the version that handles the most edge cases.

4. **Write tests for the bug**: The originally failing case (XML-wrapped JSON) became a test case to prevent regression.

5. **Document what each format handles**: The docstring explicitly lists all supported formats (raw JSON, markdown, XML, preamble).

6. **Verify pre-existing failures**: Don't assume test failures are your fault — check if they exist on main.

7. **Use raw strings for backslashes**: Always use `r"""` for docstrings containing backslash examples.

## Related Skills

- `find-duplicate-code` - Techniques for identifying code duplication
- `extract-utility-functions` - Creating shared utilities
- `comprehensive-test-coverage` - Writing thorough test suites
- `pre-commit-hook-workflow` - Running and fixing pre-commit checks

## References

- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/503
- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/505
- Commit: `cfa6869`
