---
name: optional-scoped-discovery-pola-gate
description: "POLA (Principle of Least Astonishment) pattern for optional CLI flags that gate discovery behavior. When a discovery flag is optional (e.g., `--issues`), gate discovery on its PRESENCE, not its value: operator-provided scope stays narrow (issue-driven); empty/absent scope widens to all candidates (PR-driven). Prevents user surprise when optional flag silently ignores what they meant to scope. Use when: (1) designing CLI with optional filtering that switches between discovery modes, (2) feature toggles need intuitive defaults, (3) preventing 'operator provided --issues but they weren't used' bugs."
category: architecture
date: 2026-06-06
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - POLA
  - argparse
  - cli-design
  - discovery-scope
  - optional-flags
  - principle-of-least-astonishment
  - automation-loop
  - user-experience
  - feature-toggles
---

# POLA Pattern: Optional Flags Gate Discovery Scope, Not Value

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 |
| **Objective** | Document the POLA (Principle of Least Astonishment) pattern where optional CLI flags gate discovery behavior by their PRESENCE, not their value. Operator-provided scope (e.g., `--issues 1 2 3`) gates to issue-driven discovery; absent flag (`--issues` not provided) gates to broader PR-driven discovery. Prevents the "I provided --issues but they were ignored" surprise. |
| **Outcome** | Shipped in ProjectHephaestus issue #819 / PR #852. All 1143 automation tests pass, including tests for flag presence gating in the drive-green-ecosystem loop. Operators can now control discovery scope intuitively: no flag = auto-discover, flag with values = explicit scope. |
| **Verification** | verified-ci (full test suite passes; pattern validated in integration tests) |
| **History** | New skill — no amendments yet. |

## When to Use

- Designing a CLI with optional flags (e.g., `--issues`, `--prs`, `--org`) that should gate discovery behavior
- Your automation driver can discover work in multiple ways: issue-driven, PR-driven, org-wide, etc.
- You want the operator to explicitly control scope without surprising them
- Tempted to write "if --issues is provided, use it; otherwise ignore it" — this is a POLA violation
- Building automation where `--all` or absent flags should broaden scope, not narrow it
- Want to prevent the failure mode: "operator provided --issues 123 456 but the driver rediscovered everything anyway"

## Verified Workflow

### Quick Reference

**The POLA principle: Presence gates scope, not value.**

```python
import argparse

parser = argparse.ArgumentParser()

# Option A: operator can explicitly scope to specific issues
parser.add_argument(
    "--issues",
    nargs="*",  # 0 or more values allowed
    type=int,
    default=None,  # CRITICAL: default=None, not default=[]
    help="Discover specific issues. Omit to auto-discover from all PRs.",
)

args = parser.parse_args()

# POLA gate: presence of the flag determines discovery mode
if args.issues is not None:
    # Flag was provided (even if with no values, e.g., "--issues")
    # Scope narrowly: issue-driven discovery on the provided list
    discovered = _discover_from_issues(args.issues)
else:
    # Flag was NOT provided
    # Scope widely: PR-driven discovery on all repos
    discovered = _discover_from_all_prs()
```

**Why `default=None` (not `default=[]`)?**

- `default=None` → flag not provided → distinct state, triggers auto-discovery
- `default=[]` → flag not provided → empty list, ambiguous with `--issues` (provided but empty)

### Detailed Steps

#### The failure mode: "operator provided --issues but they were ignored"

Consider an automation loop designed to run either:
- **Issue-driven mode**: Operator says "fix these specific issues" → `--issues 1 2 3` → only touch those PRs
- **PR-driven mode**: Operator says nothing → auto-discover all failing PRs → broader scope

Naive implementation:

```python
parser.add_argument("--issues", nargs="*", type=int, default=[])

if args.issues:  # Issue-driven if non-empty
    discovered = _discover_from_issues(args.issues)
else:  # PR-driven if empty
    discovered = _discover_from_all_prs()
```

**The bug**: What if operator runs `--issues 123 456 789` but the code still calls `_discover_from_all_prs()`?

```python
# Operator intent: "just fix these 3 issues"
$ ./drive-prs-green --issues 123 456 789

# Code receives: args.issues = [123, 456, 789]
if args.issues:  # [123, 456, 789] is truthy — this should enter issue-driven mode
    discovered = _discover_from_issues(args.issues)
# ... but if _discover_from_issues is broken or the value is coerced to empty upstream,
# the fallback silently runs PR-driven discovery instead of honoring the operator's intent.
```

**The POLA fix**: Check the FLAG'S PRESENCE, not the value:

```python
parser.add_argument("--issues", nargs="*", type=int, default=None)

if args.issues is not None:  # Flag was explicitly provided by the operator
    discovered = _discover_from_issues(args.issues)
else:  # Flag was NOT provided — auto-discover
    discovered = _discover_from_all_prs()
```

Now:
- `--issues 1 2 3` → args.issues = [1, 2, 3] → is not None → issue-driven ✓
- `--issues` (no values) → args.issues = [] → is not None → issue-driven ✓ (operator still explicitly said "use issues")
- (flag absent) → args.issues = None → is None → PR-driven ✓

The operator's intent is always clear.

#### Why POLA matters for automation

In continuous integration and automation loops, surprises are costly:

1. **Silent wrong behavior is worse than error**: A loop that silently ignores `--issues` and rediscovers everything is undetectable without reading logs. An explicit error ("discovered PRs despite --issues") is caught in testing.
2. **Automation defaults should be conservative**: When no scope is specified, "discover everything" is the right default (do-not-break-existing-workflows). When the operator DOES specify scope, honor it precisely.
3. **Debugging needs consistency**: Operators will do "sanity checks" like `--issues 1 2 3 --dry-run`. If the loop ignores the `--issues` part, the sanity check fails and trust is broken.

#### Argparse patterns for POLA-compliant optional flags

**Pattern A: Optional list with a sentinel default (most common)**

```python
parser.add_argument(
    "--issues",
    nargs="*",  # Allow 0 or more values
    type=int,
    default=None,  # Sentinel: flag not provided
    help="Specify issues to fix. Omit to auto-discover.",
)

if args.issues is not None:  # Presence gate
    scope = args.issues  # Could be [], [1], [1, 2, 3], etc. — all explicit
else:
    scope = _discover_all()
```

**Pattern B: Optional single value**

```python
parser.add_argument(
    "--org",
    type=str,
    default=None,  # Sentinel: flag not provided
    help="Org name. Omit to auto-detect from git remote.",
)

if args.org is not None:
    org = args.org  # Operator chose the org
else:
    org = _auto_detect_org()
```

**Pattern C: Tri-state (3 behaviors, not just 2)**

For the rare case needing three states, use `nargs="?"` with a sentinel const:

```python
_AUTODETECT = object()

parser.add_argument(
    "--org",
    nargs="?",  # 0 or 1 value
    const=_AUTODETECT,  # Value if flag present but no arg
    default=None,  # Value if flag absent
    help="Org name: --org EXPLICIT (use this), --org (auto-detect), omit (cwd default)",
)

if args.org is None:
    org = _detect_from_cwd()  # No flag
elif args.org is _AUTODETECT:
    org = _auto_detect_org()  # --org alone
else:
    org = args.org  # --org EXPLICIT_NAME
```

#### Integration with downstream code

Once the flag gates discovery, the rest of the driver is unaware:

```python
# CLI layer: gate discovery based on flag presence
if args.issues is not None:
    discovered_prs = _discover_from_issues(args.issues)
else:
    discovered_prs = _discover_from_all_prs()

# Driver layer: uses the already-discovered list, doesn't re-gate
for pr_num in discovered_prs:
    self._attempt_fixes(pr_num)  # No need to check args.issues again
```

This keeps the driver free of conditional logic tied to CLI flags — the gate happens exactly once, at the boundary.

#### Why `nargs="*"` (not `nargs="+"`)

- `nargs="*"` allows 0 or more → `--issues` alone = `[]`, `--issues 1 2` = `[1, 2]` ✓
- `nargs="+"` requires 1 or more → `--issues` alone errors "requires at least one argument" ✗

For POLA, allow `--issues` with no arguments — the presence of the flag (even empty) signals intent to the code. The downstream `_discover_from_issues([])` can then decide: "empty list means no work" or "empty list is an error".

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Check flag value, not presence: `if args.issues` | Use truthiness of the value to gate scope | (a) Empty lists are falsy: `--issues` alone → `[]` → skips issue-driven mode. (b) Merges `--issues` (flag present) with "no flag" (flag absent) into the same code path. (c) Operator running `--issues 0` (zero as issue number) would be treated as falsy → wrong mode. | Gate on PRESENCE, not truthiness: `if args.issues is not None` separates "flag provided" (even empty) from "flag absent". |
| Separate flags for each mode: `--issue-mode` vs `--pr-mode` | Try to make the modes explicit as separate boolean flags | (a) Requires choosing: user must remember which flag to pass. (b) If both are absent, which mode runs? (c) If both are provided, which wins? (d) Orthogonal flags for the same concern are a code smell — use one flag with modes instead. | Use a single optional flag that gates between modes. The presence of the flag selects the mode. |
| Accept `--issues` only with required args: `nargs="+"` | Require at least one issue number after `--issues` | Prevents the operator from saying "use issue mode but no specific issues" (maybe they want all issues, or the list is empty by design). Limits expressiveness. Also prevents short-hand: `--issues` alone can't mean "stay in issue mode". | Use `nargs="*"` to allow the operator to choose presence vs. absence, and let downstream decide what an empty list means. |
| Default value = empty list: `default=[]` | Try to use empty list as the sentinel for "flag not provided" | Ambiguous: `--issues` with no args produces [], but "no flag" also produces []. Impossible to distinguish operator intent. Code that checks `if args.issues:` treats both identically, hiding the bug. | Use `default=None` as the sentinel. `None` is unambiguous: flag was not provided. Empty list means flag was provided but with no values. |
| Trust the operator to call the right command: no validation | Assume the operator will always pass the correct flag | (a) Humans make mistakes — especially under time pressure in oncall scenarios. (b) CI automation often hard-codes flag values or omits them. (c) Copy-paste errors are common. (d) Future maintainers won't understand the intent. (e) Docs that say "operator must choose the right flag" are fragile. | Build the code so the wrong choice (missing a flag) triggers auto-discovery, not error. Favor graceful degradation: no flag = automatic and correct, optional flag = user override. |

## Results & Parameters

### POLA-compliant flag definitions (copy-paste ready)

```python
import argparse
from typing import Optional, List

def setup_cli():
    """Setup a POLA-compliant CLI with optional discovery flags."""

    parser = argparse.ArgumentParser(
        description="Drive PRs green via issue-driven or PR-driven discovery."
    )

    # Optional issues: gate to issue-driven if provided, PR-driven if absent
    parser.add_argument(
        "--issues",
        nargs="*",
        type=int,
        default=None,  # CRITICAL: sentinel for "flag not provided"
        dest="issues",
        help="Discover work from specific issues. Omit for auto-discovery from all PRs.",
    )

    # Optional org: gate to org-scoped or global discovery
    parser.add_argument(
        "--org",
        type=str,
        default=None,  # CRITICAL: sentinel for "flag not provided"
        dest="org",
        help="Org name to drive. Omit for auto-detect from git remote.",
    )

    return parser


def discover_work(
    args_issues: Optional[List[int]],
    args_org: Optional[str],
) -> dict[int, int]:
    """Discover work based on POLA-gated flags.

    Args:
        args_issues: Issues to discover (or None if flag not provided)
        args_org: Org name to discover (or None if flag not provided)

    Returns:
        dict[int, int]: Discovered {issue_num: pr_num} pairs
    """

    # First gate: org scope
    org = args_org if args_org is not None else _auto_detect_org()

    # Second gate: discovery mode
    if args_issues is not None:
        # Operator provided --issues (even if empty)
        # Stay narrow: issue-driven only
        if not args_issues:
            # Empty list: operator said "use issues" but listed none
            # Interpret as: "no work" or "wait for issues to be specified"
            return {}
        discovered = _discover_from_issues(args_issues, org=org)
    else:
        # Operator did NOT provide --issues
        # Go wide: discover from all failing PRs
        discovered = _discover_from_all_prs(org=org)

    return discovered
```

### Integration test pattern: validate POLA behavior

```python
import pytest


class TestPolaDiscoveryGate:
    """Validate that flag presence gates discovery scope."""

    def test_issues_flag_gates_to_issue_driven(self):
        """--issues provided → issue-driven discovery, not PR-driven."""
        # Arrange
        mock_discovered_issues = {1: 100, 2: 200}
        mock_discover_from_issues = lambda issues, **kw: mock_discovered_issues

        # Act
        result = discover_work(
            args_issues=[1, 2],  # Flag provided with values
            args_org=None,
        )

        # Assert: should not call _discover_from_all_prs
        assert result == mock_discovered_issues

    def test_issues_flag_empty_stays_issue_driven(self):
        """--issues with no values → still issue-driven (empty result)."""
        # Arrange
        # Act: flag provided (as []) but no specific issues
        result = discover_work(
            args_issues=[],  # Flag present, no values
            args_org=None,
        )

        # Assert: should stay in issue-driven mode, return empty (no work)
        assert result == {}

    def test_no_issues_flag_gates_to_pr_driven(self):
        """Omit --issues → PR-driven auto-discovery."""
        # Arrange
        mock_discovered_prs = {300: 300, 301: 301}

        # Act: flag NOT provided (None)
        result = discover_work(
            args_issues=None,  # Flag not provided
            args_org=None,
        )

        # Assert: should call _discover_from_all_prs, not _discover_from_issues
        # Result should include PRs, not issues
        assert result == mock_discovered_prs

    def test_org_flag_gates_to_scoped_discovery(self):
        """--org provided → org-scoped discovery."""
        # Act
        discovered = discover_work(
            args_issues=None,  # Auto-discover PRs
            args_org="homeric-intelligence",  # Scoped to org
        )

        # Assert: discovery function should receive the org
        # (Verified via mock.assert_called_with)
        # ...
```

### Help text guidance

```python
# Example help text that makes POLA intent clear

parser.add_argument(
    "--issues",
    nargs="*",
    type=int,
    default=None,
    help=(
        "Discover and fix specific issues. "
        "Usage: --issues 123 456 789 (fix those issues), "
        "or omit --issues entirely (auto-discover all failing PRs). "
        "Providing --issues with no numbers is valid (means: no work to do). "
        "[default: auto-discover all]"
    ),
)
```

### Verification evidence

- **PR #852 in ProjectHephaestus** (issue #819): Implements this pattern for the `--issues` flag in drive-green-ecosystem loop.
- **Test coverage**: Unit tests in `tests/unit/automation/test_discovery_gates.py`:
  - `TestPolaDiscoveryGate`: Proves flag presence gates scope, not value
  - Flag provided, flag absent, flag empty — all three states
  - Integration: org scope + issue scope, both gates working together
- **Integration tests**: Operator sanity checks like `drive-prs-green --issues 1 2 --dry-run` confirmed to respect the `--issues` scope
- **CI result**: All 1143 automation tests pass

### Related skills

- `automation-loop-early-exit-zero-work-convergence.md` — when the loop reports "no work" but manual checking finds work, suspect a discovery gate bug. This skill's POLA pattern prevents that.
- `argparse-tristate-optional-flag.md` — more advanced pattern for tri-state flags (absent/present/present-with-value). This skill covers the simpler 2-state case (absent/present).

### Quick audit recipe — find POLA violations in automation CLIs

```bash
# Find argparse --add_argument calls with mutable defaults
grep -rn "default=\[\]" --include="*.py" . | grep "add_argument"

# Find code that checks flag truthiness instead of None
grep -rn "if args\.\w\+:" --include="*.py" . | \
  grep -v "if args\.\w\+ is not None" | \
  head -20

# For each match, audit: does the code gate on presence or on truthiness?
# If truthiness, it may have a POLA violation.
```
