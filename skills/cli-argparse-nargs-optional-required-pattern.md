---
name: cli-argparse-nargs-optional-required-pattern
description: "argparse pattern for optional flag that requires >=1 value when present. Use when: (1) designing a CLI flag that is optional to omit but must have at least one value if given, (2) debugging silent nargs='*' acceptance of empty flag."
category: tooling
date: 2026-06-14
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: []
---

# argparse nargs Optional Flag With Required Values Pattern

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-14 |
| **Objective** | Implement a CLI flag that is optional to omit but requires ≥1 value when present |
| **Outcome** | Successful — `nargs="+"` + `default=[]` is the correct pattern |
| **Verification** | verified-ci |

## When to Use

- Designing a CLI argument that enables a mode when absent and scopes when present
- The flag should be valid to omit entirely, but invalid to write with no values
- Debugging argparse behavior where `--flag` with no values should exit 2
- After deleting a CLI flag, auditing tests that construct `argv` lists

## Verified Workflow

### Quick Reference

```python
# CORRECT: optional flag, but requires >=1 value when present
parser.add_argument(
    "--issues",
    type=int,
    nargs="+",       # "+" = at least one value required when flag is present
    default=[],      # absent flag returns [] (discovery/default mode)
    help="Scope to these issue numbers. Omit to run in discovery mode.",
)
# Behavior:
# argv=[]                       → args.issues == []    (discovery mode)
# argv=["--issues", "814"]      → args.issues == [814] (scoped mode)
# argv=["--issues"]             → SystemExit(2)        (user error)
```

### Detailed Steps

1. Use `nargs="+"` (not `nargs="*"`) for "optional flag but at least one value when given"
2. Set `default=[]` so absent flag enters the desired default mode
3. Write tests for all three cases: absent flag, present with values, present without values
4. After deleting any CLI flag, grep all test files for the flag string in argv lists

```bash
# After deleting --some-flag, find stale references in tests:
grep -rn '"--some-flag"' tests/
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `nargs="*"` + `default=[]` | Both absent `--issues` and `--issues` with no values returned `[]` silently | The two modes (absent flag = discovery, empty flag = error) became indistinguishable; AC5 was inverted | `nargs="*"` cannot distinguish absent-flag from empty-flag — use `nargs="+"` |
| Test asserting success for empty-flag case | `test_parse_args_issues_flag_without_values` checked `args.issues == []` | The test was green with the wrong `nargs="*"` implementation, masking the bug until CI | Name tests for the expected behavior (`_exits_2` suffix); assert the exit code, not success |
| Stale `--force-run` in test argv | After removing `--force-run` from argparse, a test still passed `["--force-run"]` in its constructed argv | argparse exits 2 for unknown flags; the test's setup phase crashed | After any CLI flag deletion, grep tests for the flag name and update all argv constructions |

## Results & Parameters

```python
# Verify the three-case behavior contract in tests:

def test_absent_flag_enters_discovery_mode(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog"])
    args = mymodule._parse_args()
    assert args.issues == []  # discovery mode


def test_flag_with_values_scopes(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--issues", "814"])
    args = mymodule._parse_args()
    assert args.issues == [814]


def test_flag_without_values_exits_2(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["prog", "--issues"])
    with pytest.raises(SystemExit) as exc:
        mymodule._parse_args()
    assert exc.value.code == 2  # argparse user error
```

Expected argparse behavior confirmed:

- `nargs="+"` with no values → `error: argument --issues: expected at least one argument` → exit 2
- `nargs="+"` absent → returns `default` value (`[]`)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1061 / issue #820 — make `--issues` optional in `drive_prs_green.py` | CI gate fully green after switching `nargs="*"` → `nargs="+"` |
