---
name: multi-pattern-stale-detection
description: "Detect stale CI matrix patterns at the sub-pattern level when space-separated multi-pattern strings are used. Use when: extending CI coverage validators, a group has multiple patterns where a subset may silently go stale, or implementing check_stale_patterns() style functions."
category: testing
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | CI matrix pattern groups use space-separated multi-pattern strings. A group with `pattern: "test_foo.mojo test_gone.mojo"` would not be flagged as stale if `test_gone.mojo` was deleted but `test_foo.mojo` still existed — the surviving sibling silently masked the stale pattern. |
| **Solution** | Per-sub-pattern breakdown in `check_stale_patterns()`: split on whitespace, expand each sub-pattern independently, distinguish fully-stale groups (all sub-patterns dead) from partially-stale groups (some dead). |
| **Language** | Python 3.7+ |
| **Test framework** | pytest |
| **Scope** | `scripts/validate_test_coverage.py` + `tests/scripts/test_validate_test_coverage.py` |

## When to Use

- You have a CI matrix validator that calls `pattern.split()` to expand multiple patterns
- A CI group references multiple test files via a space-separated pattern string
- You want granular staleness reporting (which specific sub-pattern is dead, not just which group)
- Existing `check_stale_patterns()` only checks combined expansion (all-or-nothing)

## Verified Workflow

### Quick Reference

```python
# Before: all-or-nothing group-level check
def check_stale_patterns(ci_groups, root_dir):
    stale = []
    for name, info in ci_groups.items():
        matched = expand_pattern(info["path"], info["pattern"], root_dir)
        if not matched:
            stale.append(name)
    return sorted(stale)

# After: per-sub-pattern breakdown
def check_stale_patterns(ci_groups, root_dir):
    stale = []
    for group_name, info in ci_groups.items():
        sub_patterns = info["pattern"].split()
        stale_subs = []
        live_subs = []
        for sub_pat in sub_patterns:
            matched = expand_pattern(info["path"], sub_pat, root_dir)
            if not matched:
                stale_subs.append(sub_pat)
            else:
                live_subs.append(sub_pat)
        if len(stale_subs) == len(sub_patterns):
            # All dead — original group-level report (backward compatible)
            stale.append(group_name)
        else:
            # Partial: report each dead sub-pattern individually
            for sub_pat in stale_subs:
                stale.append(f"{group_name} (sub-pattern: {sub_pat})")
    return sorted(stale)
```

### Step 1 — Understand the existing `expand_pattern` contract

`expand_pattern(base_path, pattern, root_dir)` already handles space-separated patterns by splitting internally and returning a combined `Set[Path]`. This means a single call to `expand_pattern` with a multi-pattern string can return non-empty results even if some sub-patterns are dead.

**Key insight**: call `expand_pattern` once per sub-pattern (not once per group) to see individual match counts.

### Step 2 — Implement the per-sub-pattern loop

```python
sub_patterns = group_info["pattern"].split()
stale_subs: List[str] = []
live_subs: List[str] = []

for sub_pat in sub_patterns:
    matched = expand_pattern(group_info["path"], sub_pat, root_dir)
    if not matched:
        stale_subs.append(sub_pat)
    else:
        live_subs.append(sub_pat)
```

### Step 3 — Apply the two-branch reporting logic

```python
if len(stale_subs) == len(sub_patterns):
    # Entire group matches nothing — backward-compatible group-level name
    stale.append(group_name)
else:
    # Partial staleness — report each dead sub-pattern with context
    for sub_pat in stale_subs:
        stale.append(f"{group_name} (sub-pattern: {sub_pat})")
```

This preserves backward compatibility: callers already checking for `"Group Name"` in the list still work correctly for fully-stale groups.

### Step 4 — Write tests covering all four cases

```python
class TestCheckStalePatternsMultiPattern:
    def test_one_stale_sub_pattern_reports_sub_pattern_not_group(self, tmp_repo):
        ci_groups = {
            "Mixed Group": {
                "path": "tests/unit",
                "pattern": "test_foo.mojo test_gone.mojo",
            },
        }
        stale = check_stale_patterns(ci_groups, tmp_repo)
        assert stale == ["Mixed Group (sub-pattern: test_gone.mojo)"]

    def test_all_sub_patterns_stale_reports_group_name(self, tmp_repo):
        ci_groups = {
            "Dead Group": {
                "path": "tests/unit",
                "pattern": "test_missing1.mojo test_missing2.mojo",
            },
        }
        stale = check_stale_patterns(ci_groups, tmp_repo)
        assert stale == ["Dead Group"]

    def test_both_sub_patterns_live_not_reported(self, tmp_repo):
        ci_groups = {
            "Healthy Group": {
                "path": "tests/unit",
                "pattern": "test_foo.mojo test_bar.mojo",
            },
        }
        stale = check_stale_patterns(ci_groups, tmp_repo)
        assert stale == []

    def test_multiple_stale_sub_patterns_all_reported(self, tmp_repo):
        ci_groups = {
            "Partial Group": {
                "path": "tests/unit",
                "pattern": "test_bar.mojo test_gone1.mojo test_gone2.mojo",
            },
        }
        stale = check_stale_patterns(ci_groups, tmp_repo)
        assert stale == [
            "Partial Group (sub-pattern: test_gone1.mojo)",
            "Partial Group (sub-pattern: test_gone2.mojo)",
        ]

    def test_mixed_and_fully_stale_groups_sorted_together(self, tmp_repo):
        ci_groups = {
            "Zebra Group": {
                "path": "tests/unit",
                "pattern": "test_foo.mojo test_gone.mojo",
            },
            "Alpha Group": {"path": "tests/nowhere", "pattern": "test_*.mojo"},
        }
        stale = check_stale_patterns(ci_groups, tmp_repo)
        assert stale == [
            "Alpha Group",
            "Zebra Group (sub-pattern: test_gone.mojo)",
        ]
```

### Step 5 — Verify all tests pass

```bash
pixi run python -m pytest tests/scripts/test_validate_test_coverage.py -v
# 18 passed in 0.11s
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Single `expand_pattern` call per group | Called `expand_pattern(path, full_pattern, root)` where `full_pattern` is the entire space-separated string | `expand_pattern` splits internally and unions results — a live sibling masks the dead sub-pattern, returning non-empty set | Must call `expand_pattern` once per individual sub-pattern to detect partial staleness |
| Reporting all stale sub-patterns as group-level | Returning `group_name` for both fully-stale and partially-stale groups | Caller cannot distinguish "group is entirely gone" from "one pattern in a healthy group was deleted" | Use `"GroupName (sub-pattern: pat)"` format for partial staleness, preserve plain group name for full staleness |

## Results & Parameters

### Output format contract

```text
# Fully stale group (all sub-patterns dead):
"Alpha Group"

# Partially stale group (one dead sub-pattern):
"Zebra Group (sub-pattern: test_gone.mojo)"

# Multiple dead sub-patterns in one partially-live group:
"Partial Group (sub-pattern: test_gone1.mojo)"
"Partial Group (sub-pattern: test_gone2.mojo)"
```

### Return type

`List[str]` — always sorted, always `str` elements. Empty list when nothing is stale.

### Backward compatibility

Pre-existing callers that check `"Group Name" in stale` for fully-stale groups continue to work unchanged. The `(sub-pattern: …)` suffix only appears for the partial-staleness case.
