---
name: document-magic-number-constants
description: 'Extract inline magic-number NOTE comments into named module-level constants
  with full rationale. Use when: (1) a value is used with a NOTE comment referencing
  an issue, (2) the same magic number appears in multiple locations, (3) a cleanup
  issue asks to convert inline NOTEs to docstrings.'
category: documentation
date: 2026-03-04
version: 1.0.0
user-invocable: false
---
# Document Magic Number Constants

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Date** | 2026-03-04 |
| **Objective** | Replace inline `NOTE:` magic-number comments with named module-level constants that carry the full rationale |
| **Outcome** | Three `NOTE:` comments in `shared/testing/layer_testers.mojo` replaced with `GRADIENT_CHECK_EPSILON_FLOAT32` / `GRADIENT_CHECK_EPSILON_OTHER` aliases; PR #3201 created |
| **Related Issues** | ProjectOdyssey #3090 (cleanup), #2704 (precision analysis) |

## When to Use This Skill

Use this skill when:

- A file has inline `NOTE: value=X for <reason> (see #NNNN)` comments that are hard to discover
- The same magic number appears in 2+ locations with the same comment copy-pasted
- A cleanup issue explicitly asks to "convert NOTEs to docstrings" or "add constants for epsilon values"
- A number was chosen after careful analysis (documented in a linked issue) and that context should be preserved

**Triggers:**

- Issue title contains "document epsilon", "document tolerance", "convert NOTE comments", "extract constants"
- File has `# NOTE: epsilon=` or `# NOTE: tolerance=` inline comments
- Multiple lines share an identical `# NOTE:` comment
- The NOTE references a GitHub issue number for context

## Verified Workflow

### Phase 1: Read the Issue and Identify All Affected Sites

```bash
gh issue view <number> --comments
```

Note the exact file paths and line numbers listed in the issue.
Read each site to understand the context around the NOTE.

### Phase 2: Verify the Value Is Still Appropriate

Before creating constants, confirm the value is correct:

- Check that the referenced issue (e.g., `#2704`) documents why the value was chosen
- Look at the epsilon assignment to confirm no drift since the NOTE was written
- If multiple sites share the value, confirm they use it identically

### Phase 3: Add Named Constants

Add module-level constants **before** the first struct definition (Mojo) or at module scope (Python):

**Mojo pattern:**

```mojo
# ============================================================================
# Gradient Checking Constants
# ============================================================================

# Epsilon for float32 gradient checking in matmul-heavy layers (conv2d, linear).
# Using 1e-5 causes ~56% precision loss; 1e-4 gives 3.3% error (above tolerance).
# 3e-4 gives 1.2% error, within the 1.5% tolerance threshold.
# See issue #NNNN (<description>) for full analysis.
alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4

# Epsilon for non-float32 dtypes (BF16, FP16) in gradient checking.
alias GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3
```

**Python pattern:**

```python
# Epsilon for float32 gradient checking in matmul-heavy operations.
# See issue #NNNN for precision analysis; 3e-4 gives 1.2% error (within tolerance).
GRADIENT_CHECK_EPSILON_FLOAT32: float = 3e-4
GRADIENT_CHECK_EPSILON_OTHER: float = 1e-3
```

Rules:
- Put ALL rationale in the constant definition comment, not at usage sites
- Include concrete alternatives that were tried and rejected (quantified)
- Reference the issue number where the analysis lives

### Phase 4: Replace the NOTE Comments at Each Usage Site

Replace the inline `NOTE:` comments with a single-line reference to the constant:

```mojo
# Before
# NOTE: epsilon=3e-4 for float32 prevents precision loss in matmul (see #2704)
var epsilon = 3e-4 if dtype == DType.float32 else 1e-3

# After
# Epsilon for gradient checking: float32 uses GRADIENT_CHECK_EPSILON_FLOAT32 (3e-4)
# to avoid precision loss in matmul operations. See issue #2704 for full analysis.
var epsilon = GRADIENT_CHECK_EPSILON_FLOAT32 if dtype == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER
```

Key principle: the usage-site comment says "why this constant exists and where to look", not "what the value is and why". The constant definition carries the full context.

### Phase 5: Update Module Docstring (if applicable)

If the module-level docstring mentions tolerances, update it to reference the constant:

```mojo
# Before
# - Tolerances adjusted per dtype (1e-2 for float32)

# After
# - Tolerances adjusted per dtype (1e-2 for float32)
# - Epsilon for float32 gradient checking: GRADIENT_CHECK_EPSILON_FLOAT32 (3e-4),
#   chosen to avoid precision loss in matmul operations (see issue #NNNN)
```

### Phase 6: Commit and PR

```bash
git add <changed-file>
git commit -m "$(cat <<'EOF'
docs(<scope>): document epsilon values in gradient checking

Add GRADIENT_CHECK_EPSILON_FLOAT32 and GRADIENT_CHECK_EPSILON_OTHER
module-level constants. Replace inline NOTE comments with proper
documented references to the constants and issue #NNNN.

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin <branch>
gh pr create \
  --title "docs(<scope>): document epsilon values in gradient checking" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Adding `alias` inside the struct body | Tried to put the constants as struct-level aliases | Mojo `alias` inside a struct is scoped to the struct; usage sites inside methods can still reference them, but they become struct members rather than module-level names | Place aliases at module scope before the struct for clearest discoverability |
| Keeping long rationale at usage sites | Left the detailed "Using 1e-5 causes 56% loss..." comment at each usage | Creates duplication — if the constant's value ever changes, all three sites need updating | Move all rationale to the constant definition; keep usage-site comments brief |
| Using `/commit-commands:commit-push-pr` skill | Attempted to invoke the skill tool | Skill tool may not be available in all execution modes | Fall back to direct `git add/commit/push` + `gh pr create` |

## Results & Parameters

| Parameter | Value | Notes |
| ----------- | ------- | ------- |
| Constant name | `GRADIENT_CHECK_EPSILON_FLOAT32` | Descriptive: includes dtype and use case |
| Constant value | `3e-4` | Unchanged from original magic number |
| Alias type | `Float64` | Match the type expected by `compute_numerical_gradient` |
| Companion constant | `GRADIENT_CHECK_EPSILON_OTHER = 1e-3` | For non-float32 dtypes |
| Usage sites updated | 3 | All in `shared/testing/layer_testers.mojo` |
| Commit type | `docs(testing):` | No functional change — only documentation |

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3090, PR #3201 | Branch `3090-auto-impl`; pre-commit passed |
