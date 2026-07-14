# Prompt String Syntax — Implementation Notes

## Session Context

**Issue**: #1082 (token reduction in automation pipeline)
**Branch**: `1082-auto-impl` in ProjectHephaestus
**Date**: 2026-06-07

## Problems Encountered

### 1. Raw String Syntax Error

When initially composing the `_TERSE_OUTPUT_DIRECTIVE`, the implementation attempted:

```python
directive = r"""
Output only terse JSON without explanation.
Omit markdown, code blocks, and verbose text.  # noqa: E501
"""
```

This failed with `SyntaxError: EOL while scanning string literal` because:
- The `r` prefix (raw string) disables backslash escape processing
- Backslash-newline line continuation requires escape processing
- Raw strings cannot use backslash continuation across lines

**Solution**: Changed to plain string (no `r` prefix), which allows backslash
processing:

```python
TERSE_OUTPUT_DIRECTIVE = """Output only terse JSON without explanation.
Omit markdown, code blocks, and verbose text."""  # noqa: E501
```

### 2. Comment Contamination in Prompts

The initial attempt kept the `# noqa: E501` comment inside the string:

```python
TERSE_OUTPUT_DIRECTIVE = """Output only terse JSON without explanation.
Omit markdown, code blocks, and verbose text.  # noqa: E501"""
```

This caused the `# noqa: E501` text to appear verbatim in rendered agent prompts, e.g.:

```
System Prompt:
"Output only terse JSON without explanation.
Omit markdown, code blocks, and verbose text.  # noqa: E501

Plan the following issue: ..."
```

Agents would see the comment as part of the instruction, potentially causing confusion.

**Solution**: Moved the comment outside the string literal:

```python
TERSE_OUTPUT_DIRECTIVE = """Output only terse JSON without explanation.
Omit markdown, code blocks, and verbose text."""  # noqa: E501
```

### 3. Bare Assertions in Test Suites

Initial test code used bare `assert` for validation:

```python
def test_planning_prompt_includes_directive():
    prompt = get_planning_prompt(issue=123)
    assert "Output only terse JSON" in prompt
```

**Problem**: Under Python's `-O` (optimize) flag, the Python interpreter strips
all `assert` statements at parse time. This means:
- Local test runs pass (assert runs)
- CI with `-O` flag silently skips assertions
- Tests give false passing status

This is particularly problematic for automation tests that validate agent behavior,
since missing validations could allow token bloat to creep back in undetected.

**Solution**: Changed to `pytest.fail()` which always runs:

```python
def test_planning_prompt_includes_directive():
    prompt = get_planning_prompt(issue=123)
    if "Output only terse JSON" not in prompt:
        pytest.fail("Terse directive missing from planning prompt")
```

Or used `pytest.raises()` for exception testing:

```python
def test_tool_scoping_enforced():
    with pytest.raises(ValueError, match="allowed_tools required"):
        call_anthropic_agent(...)
```

### 4. Silent Test Gaps for Unimplemented Features

The implementation plan referenced a feature `get_comment_difficulty_prompt()` that
was never implemented in this iteration. The test suite initially had:

```python
def test_directive_in_implementation_prompt():
    # TODO: when get_comment_difficulty_prompt is implemented
    pass
```

Without explanation, this looks like an oversight or incomplete work, making it
unclear whether the gap is intentional (deferred) or accidental (forgotten).

**Solution**: Added clarifying docstring explaining the deferral:

```python
def test_directive_in_implementation_prompt():
    """Validate terse directive in implementation agent prompt.

    Note: Requires get_comment_difficulty_prompt() helper, planned for future
    refinement. Currently implementation prompt does not use comment difficulty
    scoring, so this test is deferred.
    """
    # TODO: implement when get_comment_difficulty_prompt is available
    pass
```

## PR Review Feedback (Round 2)

After the initial PR submission (#1087 review round 1), the following refinements
were made:

1. **Directive naming**: Ensured `_TERSE_OUTPUT_DIRECTIVE` follows Python
   convention (underscore prefix indicates module-private)
2. **Tool scoping audit**: Reviewed all agent call sites to identify unscoped
   invocations, then added `allowed_tools` parameter to the 3 most critical sites
   (planning, implementation, pr_review)
3. **Test isolation**: Ensured test fixtures properly isolate prompt generation
   from agent calls
4. **Comment clarity**: Added detailed docstrings to tests that validate prompt content

## Verification Details

**Local verification** (2026-06-07):

```bash
$ pixi run pytest tests/unit/automation -v
tests/unit/automation/prompts/test_shared_directive.py \
  ::test_terse_directive_is_defined PASSED
tests/unit/automation/prompts/test_shared_directive.py \
  ::test_terse_directive_is_non_empty PASSED
tests/unit/automation/prompts/test_composed_prompts.py \
  ::test_planning_prompt_includes_terse_directive PASSED
tests/unit/automation/prompts/test_composed_prompts.py \
  ::test_implementation_prompt_includes_terse_directive PASSED
... (21 tests total)

======================== 21 passed in 1.23s ========================
```

**CI verification**: Awaiting GitHub Actions CI completion (PR #1087)

## Related Learning

This skill should be cross-referenced with:

- Existing skill: `fix-s101-assert-to-runtimeerror` (but that's about production
  code; this is about test code)
- CLAUDE.md section on assertions: "use `pytest.fail()` instead of bare `assert`"
  (not yet formalized in CLAUDE.md; this skill documents the pattern)

## Key Takeaways for Future Work

1. **String literal syntax matters**: Raw strings (`r"""..."""`) are for regex
   patterns and Windows paths; use plain strings for prompt text
2. **Comments outside strings**: Keep `# noqa` and lint directives outside string
   literals; they belong in code, not in rendered output
3. **Test robustness**: Never rely on bare `assert` in tests; use `pytest.fail()`
   or `pytest.raises()` for validation that must run in all Python modes
4. **Intentional deferrals**: Document why tests are incomplete or TODOs are
   deferred; single-line comments invite confusion
