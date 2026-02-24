# Session Notes: Deduplicate LLM JSON Extraction

## Session Context

**Date**: 2026-02-12
**Session ID**: 95550d04-f8cc-43b3-abac-40cd64149abd
**Issue**: #503
**PR**: #505

## Problem Discovery

Initial bug report: LLM judge failing with Haiku model when JSON wrapped in XML tags.

Error was in `scylla/e2e/llm_judge.py:_parse_judge_response()` which only handled:
- Markdown code blocks (`` ```json `` or `` ``` ``)
- Raw JSON via `json.loads()`

**Did NOT handle**:
- XML-wrapped JSON: `<json_evaluation>{"score": 0.8}</json_evaluation>`
- Preamble text before JSON: `Here is the result: {"score": 0.8}`

## Code Search Findings

Searched for similar JSON extraction logic:

```bash
grep -r "json.loads" scylla/
grep -r '```json' scylla/
grep -r 're.search.*json' scylla/
```

**Found 3 implementations**:

1. **scylla/e2e/llm_judge.py:1038-1084** (BROKEN)
   - String manipulation for markdown blocks
   - No brace matching
   - Fails on XML/preamble

2. **scylla/judge/parser.py:267-308** (WORKING)
   - Markdown code blocks regex
   - Brace-matching algorithm
   - Handles XML/preamble

3. **scylla/judge/evaluator.py:474-519** (WORKING)
   - **IDENTICAL** to parser.py
   - Same regex, same algorithm
   - Copy-paste from parser.py

## Implementation Strategy

Chose to:
1. Extract proven implementation to shared utility
2. Update all 3 consumers
3. Add comprehensive tests

**Why this approach**:
- Fixes the bug in llm_judge.py
- Removes duplicate code (113 lines removed)
- Prevents future drift
- Single source of truth for testing

## Key Code Snippets

### Original Broken Implementation (llm_judge.py)

```python
# Handle markdown code blocks
if "```json" in response:
    start = response.find("```json") + 7
    end = response.find("```", start)
    response = response[start:end].strip()
elif "```" in response:
    start = response.find("```") + 3
    end = response.find("```", start)
    response = response[start:end].strip()

try:
    data = json.loads(response)  # Fails on XML/preamble
except json.JSONDecodeError as e:
    raise ValueError(...)
```

### Working Implementation (parser.py)

```python
# Try to find JSON in code blocks first
json_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", output)
if json_block:
    try:
        return json.loads(json_block.group(1))
    except json.JSONDecodeError:
        pass

# Try to find raw JSON object (brace matching)
start = output.find("{")
if start == -1:
    return None

# Find matching closing brace
depth = 0
end = start
for i, char in enumerate(output[start:], start):
    if char == "{":
        depth += 1
    elif char == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

if depth != 0:
    return None

try:
    return json.loads(output[start:end])
except json.JSONDecodeError:
    return None
```

### New Shared Utility (judge/utils.py)

Exact copy of working implementation, now in `extract_json_from_llm_response()`.

## Test Strategy

### Unit Tests (test_utils.py)

16 test cases covering:
- Happy paths (raw JSON, code blocks)
- Edge cases (XML tags, preamble, trailing text)
- Error cases (no JSON, malformed, unbalanced braces)
- Real-world examples (complex nested JSON with XML wrapper)

### Integration Tests (test_subtest_executor.py)

Added 3 tests for `_parse_judge_response()`:
1. XML-wrapped JSON (the original bug)
2. Preamble text
3. Markdown code block

**Important**: Had to update error message expectation from `"Judge response is not valid JSON"` to `"Judge response does not contain valid JSON"`.

## Pitfalls Encountered

### 1. Test Grade Expectations

Initial tests expected:
- 0.8 → "B" grade
- 0.7 → "C" grade

Actual grading scale:
- 0.8 → "A" grade
- 0.7 → "B" grade

**Fix**: Checked actual `_score_to_grade()` function and updated test assertions.

### 2. Docstring Backslashes

Ruff error: `D301 Use r""" if any backslashes in a docstring`

**Why**: Examples had `\n` in docstring without raw string prefix.

**Fix**: Changed `"""` to `r"""` and actual `\n` in examples (not escaped).

### 3. Pre-existing Test Failures

Full test suite showed 2 failures in `tests/unit/executor/test_agent_container.py`.

**Investigation**:
```bash
git stash
pixi run python -m pytest tests/unit/executor/test_agent_container.py::test_build_volumes_without_claude_md -q
# Still fails on main branch
git stash pop
```

**Conclusion**: Unrelated to our changes, pre-existing failures.

## Verification Commands

```bash
# Unit tests
pixi run python -m pytest tests/unit/judge/test_utils.py -v

# Integration tests
pixi run python -m pytest tests/unit/e2e/test_subtest_executor.py::TestParseJudgeResponse -v

# Full suite
pixi run python -m pytest tests/ -q

# Pre-commit
pre-commit run --files scylla/judge/utils.py scylla/judge/__init__.py scylla/judge/parser.py scylla/judge/evaluator.py scylla/e2e/llm_judge.py tests/unit/judge/test_utils.py tests/unit/e2e/test_subtest_executor.py
```

## Git Workflow

```bash
# Create branch
git checkout -b fix-llm-judge-json-parsing

# Create issue
gh issue create --title "..." --body "..." --label "bug,refactor"
# → Issue #503

# Make changes
# ...

# Stage files
git add scylla/judge/utils.py scylla/judge/__init__.py scylla/judge/parser.py scylla/judge/evaluator.py scylla/e2e/llm_judge.py tests/unit/judge/test_utils.py tests/unit/e2e/test_subtest_executor.py

# Commit
git commit -m "refactor(judge): deduplicate JSON extraction & fix LLM judge parsing

[Full commit message with problem, solution, changes, verification]

Closes #503

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# Push
git push -u origin fix-llm-judge-json-parsing

# Create PR
gh pr create --title "..." --body "..." --label "bug,refactor"
# → PR #505

# Enable auto-merge
gh pr merge --auto --rebase 505

# Comment on issue
gh issue comment 503 --body "Implementation Complete ✅..."
```

## Metrics

### Code Changes

- **Files created**: 2 (utils.py, test_utils.py)
- **Files modified**: 5
- **Lines added**: 273
- **Lines deleted**: 113
- **Net change**: +160 lines

### Deduplication Impact

- **Duplicate implementations**: 3 → 1
- **Lines of duplicate code removed**: ~87
- **Consumers updated**: 3
- **Tests added**: 16 unit + 3 integration

### Test Results

- **New utility tests**: 16/16 ✅
- **Integration tests**: 5/5 ✅
- **Full test suite**: 1775/1777 ✅ (2 pre-existing failures)
- **Pre-commit hooks**: All passed ✅

## Links

- **Issue**: https://github.com/HomericIntelligence/ProjectScylla/issues/503
- **PR**: https://github.com/HomericIntelligence/ProjectScylla/pull/505
- **Commit**: cfa6869
- **Branch**: fix-llm-judge-json-parsing
