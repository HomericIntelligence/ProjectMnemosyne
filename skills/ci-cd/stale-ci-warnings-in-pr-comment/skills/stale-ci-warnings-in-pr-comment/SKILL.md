---
name: stale-ci-warnings-in-pr-comment
description: "Surface stale CI pattern warnings in PR comment body rather than stderr only. Use when: (1) stale pattern detection exists but output is stderr-only, (2) reviewers need to see stale warnings without inspecting raw CI logs, (3) post_to_pr() should fire even when no uncovered files exist."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `check_stale_patterns()` results were printed to stderr only; `post_to_pr()` was guarded by `if uncovered:`, so stale-only situations never appeared in the PR comment |
| **Solution** | Add `stale_patterns` param to `generate_report()`, append `### Stale CI Patterns` section when non-empty, change guard to `if uncovered or stale_patterns:` |
| **Follow-up from** | Issue #3358 (stale pattern detection) → Issue #4010 (surface in PR comment) |
| **Key change** | `generate_report()` gains `stale_patterns: Optional[List[str]] = None` |
| **Backward compatible** | Yes — parameter defaults to `None`, existing callers unaffected |
| **Language** | Python 3.7+ |
| **New tests** | 5 pytest cases in `TestGenerateReportStalePatterns` |

## When to Use

- You have stale CI pattern detection (e.g. `check_stale_patterns()`) that only prints to stderr
- Reviewers are missing stale warnings because they don't look at raw CI logs
- `post_to_pr()` is only called when `uncovered` is non-empty, so stale-only runs produce no PR comment
- You need to wire detection output into the report body without breaking the existing forward-check

## Verified Workflow

### Quick Reference

| Step | What to do |
|------|-----------|
| 1 | Add `Optional` to imports |
| 2 | Add `stale_patterns: Optional[List[str]] = None` to `generate_report()` |
| 3 | Append `### Stale CI Patterns` section inside `generate_report()` when non-empty |
| 4 | Call `check_stale_patterns()` in `main()` and pass result to `generate_report()` |
| 5 | Change `if post_pr and uncovered:` guard to `if post_pr and (uncovered or stale_patterns):` |
| 6 | Add 5 pytest cases for the new parameter |

### Step 1 — Add `Optional` to imports

```python
from typing import Any, Dict, List, Optional, Set, Tuple
```

### Step 2 — Update `generate_report()` signature

```python
def generate_report(
    uncovered: Set[Path],
    test_files: List[Path],
    coverage_by_group: Dict[str, Set[Path]],
    stale_patterns: Optional[List[str]] = None,
) -> str:
    """Generate a detailed validation report.

    Args:
        uncovered: Set of test file paths not covered by any CI group.
        test_files: All discovered test file paths.
        coverage_by_group: Mapping of group name to the files it covers.
        stale_patterns: Optional list of CI group names that match zero files.
            When non-empty, a '### Stale CI Patterns' section is appended.

    Returns:
        Formatted markdown report string.
    """
```

### Step 3 — Append stale section at end of `generate_report()`

Add this block immediately before the `return "\n".join(report_lines)` line:

```python
if stale_patterns:
    report_lines.append("")
    report_lines.append("### Stale CI Patterns")
    report_lines.append("")
    report_lines.append(
        "The following CI groups matched zero test files and may be stale:"
    )
    report_lines.append("")
    for name in stale_patterns:
        report_lines.append(f"- {name}")
```

### Step 4 — Wire `check_stale_patterns()` into `main()`

After the existing `check_coverage(...)` call:

```python
# Check for stale CI patterns (groups that match zero test files)
stale_patterns = check_stale_patterns(ci_groups, repo_root)
if stale_patterns:
    print("⚠️  Stale CI patterns detected (match zero test files):", file=sys.stderr)
    for name in stale_patterns:
        print(f"   • {name}", file=sys.stderr)
```

Pass the result to `generate_report()` in both the `uncovered` branch and the stale-only branch:

```python
# Inside "if uncovered:" block:
report = generate_report(uncovered, test_files, coverage_by_group, stale_patterns)

# After the uncovered block (stale-only case):
if post_pr and stale_patterns:
    report = generate_report(uncovered, test_files, coverage_by_group, stale_patterns)
    post_to_pr(report)
```

### Step 5 — Tests for the new parameter

```python
class TestGenerateReportStalePatterns:
    """Tests for the stale_patterns argument of generate_report()."""

    def _make_coverage(self) -> dict:
        return {"Unit Tests": {Path("tests/unit/test_foo.mojo")}}

    def test_no_stale_section_when_none_passed(self) -> None:
        report = generate_report(set(), [], self._make_coverage(), stale_patterns=None)
        assert "### Stale CI Patterns" not in report

    def test_no_stale_section_when_empty_list(self) -> None:
        report = generate_report(set(), [], self._make_coverage(), stale_patterns=[])
        assert "### Stale CI Patterns" not in report

    def test_stale_section_appended_when_patterns_exist(self) -> None:
        report = generate_report(
            set(), [], self._make_coverage(), stale_patterns=["Alpha Tests", "Zebra Tests"]
        )
        assert "### Stale CI Patterns" in report
        assert "- Alpha Tests" in report
        assert "- Zebra Tests" in report

    def test_stale_section_with_uncovered_files(self) -> None:
        uncovered = {Path("tests/unit/test_missing.mojo")}
        report = generate_report(
            uncovered,
            [Path("tests/unit/test_missing.mojo")],
            {},
            stale_patterns=["Ghost Group"],
        )
        assert "### Uncovered Tests" in report
        assert "### Stale CI Patterns" in report
        assert "- Ghost Group" in report

    def test_stale_only_no_uncovered(self) -> None:
        report = generate_report(
            set(), [], self._make_coverage(), stale_patterns=["Deleted Group"]
        )
        assert "### Stale CI Patterns" in report
        assert "- Deleted Group" in report
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Combined guard `if post_pr and uncovered or stale_patterns:` | Operator precedence: `and` binds tighter than `or`, so the `stale_patterns` arm ran unconditionally | Python operator precedence — always parenthesize mixed `and`/`or` | Use `if post_pr and (uncovered or stale_patterns):` or separate the two cases |
| Adding stale section inside the `if not uncovered:` branch | Stale section only appeared in the "all covered" path, not when uncovered files also existed | The section must be appended after both branches, unconditionally | Place stale section append after both `if/else` blocks, before `return` |

## Results & Parameters

All 18 tests pass (13 existing + 5 new):

```text
tests/scripts/test_validate_test_coverage.py::TestCheckStalePatterns::* (9 tests) PASSED
tests/scripts/test_validate_test_coverage.py::TestGenerateReportStalePatterns::* (5 tests) PASSED
tests/scripts/test_validate_test_coverage.py::TestExpandPattern::* (4 tests) PASSED
```

Key design decisions:

- `stale_patterns` defaults to `None` (not `[]`) for explicit backward compatibility signal
- Both `None` and `[]` suppress the section — only truthy lists render it
- Stale section is always appended **after** the uncovered/covered branches so it appears in both cases
- `post_to_pr()` fires when `uncovered or stale_patterns` — the stale-only path calls `generate_report()` separately to avoid duplicating the report variable in the uncovered path
