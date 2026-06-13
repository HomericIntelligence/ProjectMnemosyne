---
name: architecture-god-function-decomposition-planning-risks
description: >-
  Use when: planning an extraction pass on over-long functions (god functions)
  in hephaestus/automation/ or similar large Python codebases, especially when
  working from an issue that cites specific line numbers, function sizes, or
  file locations — before finalizing an extraction plan that waives work on a
  function, verify on disk that the cited size matches reality; apply the
  sentinel return pattern for extracted poll loops; verify test file existence
  before writing stubs; and audit plan documents for helper-defined-but-never-called
  inconsistencies.
category: architecture
date: 2026-06-13
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - python
  - refactoring
  - god-function
  - planning
  - extraction
  - risk-management
  - line-number-validation
  - poll-loop
  - sentinel-pattern
  - test-stubs
  - planning-risks
---

# Architecture: God-Function Decomposition — Planning Risks

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-13 |
| **Source issue** | ProjectHephaestus #1180 — decompose 5 god-functions in `hephaestus/automation/` |
| **Verification** | unverified (planning-phase learnings; no code ran) |
| **Objective** | Document recurring planning-phase failure modes when working from issue-cited metadata rather than disk reality |

These risks surface whenever an engineer or agent plans god-function extractions from
an issue description that cites line numbers, function sizes, or file paths. The
issue body may be weeks or months old; the code on disk is authoritative.

---

## Risk 1: Issue-Cited Line Numbers May Be Stale — Always Re-read Before Planning

**What happened**: Issue #1180 cited `_implement_issue` as 354 lines (at line 255).
Direct `Read` of `implementer_phase_runner.py` showed the function spans lines 180–307:
127 lines, not 354. The plan correctly waived extraction for this function — but only
because the planner read the file first.

**The failure mode**: If the planner trusts the issue's cited size and plans extraction
for a 354-line function, it designs helpers that don't exist, splits non-existent blocks,
and writes a plan that is wrong from line 1.

**Rule**: Before deciding to extract *or* waive extraction for any named function, run:

```python
python3 -c "
import ast, sys
src = open('path/to/file.py').read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name == '_target_function':
            print(f'Lines {node.lineno}–{node.end_lineno}: {node.end_lineno - node.lineno + 1} lines')
"
```

Or use the Read tool and count from the `def` line to the last line of the body.
**Never trust the issue's line count as the decision input.**

**Corollary**: If the plan says "waive extraction — function is only 127 lines", cite
the disk evidence (`file.py:180-307, 127 lines`) so the reviewer can verify without
re-reading the whole file.

---

## Risk 2: Cited File/Line Reference May Point to a Refactored Location

**What happened**: Issue #1180 cited `_run_impl_review_loop` at line 1513 of
`ci_driver.py`. After a prior refactor the function was moved to `_review_phase.py`
at lines 374–503. The plan found it only because a subagent searched by name
rather than by file+line.

**The failure mode**: An agent that opens `ci_driver.py:1513` sees a completely
different function or a blank line and either (a) extracts the wrong function, or
(b) panics with a "function not found" error.

**Rule**: When an issue cites `file.py:N`, grep for the function name across the
package first:

```bash
grep -rn "def _run_impl_review_loop" hephaestus/automation/
```

Accept the grep result as the authoritative location; treat the issue's file+line
citation as a hint, not a fact.

---

## Risk 3: The Helper-Defined-But-Not-Called Inconsistency

**What happened**: The decomposition plan for `_address_issue` defined a
`_finalize_address_state` helper in the "New helpers" section, but the replacement
code block shown for lines 561–635 inlined the state finalization directly rather
than calling the helper. The helper was defined but its call site was never shown.

**The failure mode**: An implementer writes both the helper and the inlined version,
leaving dead code. Or the reviewer approves a plan that has an unreachable function.
Either path wastes review cycles or introduces a dead-code lint failure.

**Rule**: Before finalizing a decomposition plan, audit every helper defined in the
plan document:

```text
For each helper H defined in "New helpers" / "Extracted functions":
  - grep the replacement code blocks for `H(`
  - if zero matches: either (a) delete H from the plan, or (b) add the call site
  - NEVER ship a plan where a defined helper has no shown call site
```

**Detection heuristic**: After writing the plan, search the plan document itself for
each helper name. If it appears only in its own definition section and nowhere else,
flag it as inconsistent.

---

## Risk 4: Sentinel Return Pattern for Extracted Poll Loops

**What happened**: The plan extracted a `_poll_ci_until_concluded` helper from
`_drive_issue`. The helper's return contract was:
- `None` — timeout; CI still pending after deadline
- `[]` (empty list) — no CI checks found at all
- `list[CheckResult]` (non-empty) — CI concluded with results

The caller must handle both `None` and `[]` as "treat as success=True / proceed".

**The failure mode**: If the caller treats `[]` as "no checks ran → failure" (a natural
intuition), it will abort the issue drive unnecessarily on repos with no required CI checks.
If the caller treats `None` as "timed out → hard failure", it will never retry a
transiently-slow CI.

**Rule**: When extracting any polling loop into a helper, document the full sentinel
contract in a docstring before merging:

```python
def _poll_ci_until_concluded(
    pr_number: int,
    deadline: float,
    gh_fn: Callable,
) -> list[CheckResult] | None:
    """Poll CI checks until all conclude or deadline is reached.

    Returns:
        list[CheckResult]: All checks concluded (may be empty if no checks exist).
            An empty list means no CI checks are configured — treat as success.
        None: Deadline reached before checks concluded — caller should
            treat as "still pending" (not a hard failure).
    """
```

And add a unit test asserting the `[]` vs `None` distinction explicitly:

```python
def test_poll_returns_empty_list_when_no_checks(mock_gh):
    mock_gh.return_value = []
    result = _poll_ci_until_concluded(pr=42, deadline=time.time() + 60, gh_fn=mock_gh)
    assert result == []           # not None
    assert result is not None     # caller must not treat as timeout
```

---

## Risk 5: Verify Test File Existence Before Writing Test Stubs

**What happened**: The plan added tests to `tests/unit/automation/test_ci_driver.py`
and `tests/unit/automation/test_address_review.py`. Neither file was verified to exist
or inspected for fixture patterns before the plan was finalized.

**The failure mode**: The implementer discovers the file does not exist and must invent
a fixture structure from scratch, or the file exists but uses a project-wide fixture
(`autouse` conftest, class-based test structure, `@pytest.fixture(scope="module")`) that
the new tests must follow to avoid import errors or fixture-collision failures.

**Rule**: Before writing any test stubs in a plan, run:

```bash
# Verify file exists
ls tests/unit/automation/test_ci_driver.py 2>/dev/null || echo "FILE DOES NOT EXIST"

# If it exists, read the first 60 lines to identify fixture patterns
head -60 tests/unit/automation/test_ci_driver.py
```

If the file does not exist, the plan must include a "Create test file" step that
describes the required imports and any fixture scaffolding to match the conftest.

If the file exists, the plan must note the dominant fixture pattern (e.g.,
`class TestCIDriver: ...` vs module-level functions, `@pytest.fixture(autouse=True)` vs
per-test setup) so the new tests are consistent.

---

## Risk 6: The Empty-Replies-Dict Edge Case in Extracted State Helpers

**What happened**: The plan's `_finalize_address_state` helper passed `replies={}`
(empty dict) to `_resolve_addressed_threads`. This is correct when the replies are
already handled by the caller before the helper is invoked — but the plan did not
verify whether `_resolve_addressed_threads` accepts an empty dict or requires a
non-empty one.

**The failure mode**: If `_resolve_addressed_threads` has a guard like
`if not replies: raise ValueError(...)` or iterates `replies` with an assumption that
at least one entry exists, passing `{}` silently skips the resolution logic and leaves
threads unresolved.

**Rule**: When an extracted helper passes a sentinel/empty value to a downstream
function, read the downstream function's signature and body before finalizing the call:

```bash
grep -n "def _resolve_addressed_threads" hephaestus/automation/*.py
# then read the first 20 lines of that function to check for empty-input guards
```

Document the expected behavior explicitly in the plan:

> `_resolve_addressed_threads(addressed, replies={}, thread_ids)` — passing `replies={}`
> is safe because the function iterates `thread_ids` (not `replies`) as the primary
> driver. Verified at `address_review.py:312-335`.

---

## Planning Checklist for God-Function Decomposition

Before submitting or approving a god-function decomposition plan:

```text
[ ] For each function named in the issue:
    [ ] Re-read the function on disk — cite file:start-end and actual LOC
    [ ] If waiving extraction: cite the disk evidence in the plan
    [ ] If the issue's file+line doesn't match disk: note the discrepancy

[ ] For each new helper defined in the plan:
    [ ] Confirm at least one call site appears in the plan's replacement blocks
    [ ] If no call site shown: delete the helper or add the call

[ ] For each extracted poll/retry loop:
    [ ] Document the full sentinel return contract (what each return value means)
    [ ] Add a unit test distinguishing the empty-list vs None sentinels

[ ] For each test stub added by the plan:
    [ ] Verify the target test file exists (ls command)
    [ ] If it exists, read its fixture pattern (first 60 lines)
    [ ] If it doesn't exist, include a "Create test file" step in the plan

[ ] For each helper that passes an empty/sentinel value downstream:
    [ ] Read the downstream function's first 20 lines
    [ ] Confirm it handles the empty value correctly
    [ ] Cite the verification in the plan (file:line range)
```

---

## Verified On

| Project | Context |
| --------- | --------- |
| ProjectHephaestus | Planning session for issue #1180 — decompose 5 god-functions in `hephaestus/automation/`; `_implement_issue` cited as 354 lines in issue, found as 127 lines on disk; `_run_impl_review_loop` cited at `ci_driver.py:1513`, found at `_review_phase.py:374-503`; `_finalize_address_state` defined in plan but not called in replacement block; test file existence unverified; `_poll_ci_until_concluded` sentinel contract risk identified |
