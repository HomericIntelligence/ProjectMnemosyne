---
name: inline-comment-and-note-cleanup
description: >-
  Systematically audit and clean up inline NOTE/TODO/FIXME/placeholder comments
  in source code. Use when: (1) a cleanup issue targets NOTE/TODO/FIXME markers
  for normalization, removal, or tracing, (2) runtime print statements carry NOTE
  prefixes that confuse users, (3) magic-number comments need extracting into named
  constants, (4) generator-script TODOs need reclassifying as TEMPLATE markers,
  (5) shipped-feature placeholders or no-op placeholder tests need removal.
category: documentation
date: 2026-05-19
version: 1.0.0
user-invocable: false
history: inline-comment-and-note-cleanup.history
tags:
  - note-cleanup
  - comment-normalization
  - placeholder
  - todo
  - mojo
  - python
---

## Overview

| Field | Value |
| ----- | ----- |
| **Category** | documentation |
| **Theme** | Lifecycle management of inline NOTE/TODO/FIXME/placeholder comments in source code |
| **Languages** | Mojo, Python (patterns apply broadly) |
| **Trigger** | Cleanup issue targeting NOTE/TODO/FIXME markers, runtime print confusion, or stale placeholders |
| **Outcome** | Zero untracked or non-canonical markers; all pre-commit hooks pass |

## When to Use

- A GitHub cleanup issue asks to audit or normalize `# NOTE:`, `# Note:`, `# TODO:`, or `# FIXME:` markers
- Runtime `print("NOTE: ...")` statements appear during execution and confuse users into thinking something is broken
- Magic-number comments (`# NOTE: epsilon=3e-4`) should be elevated to named module-level constants
- Generator scripts contain `# TODO:` inside template strings that should be `# TEMPLATE:`
- Source code has `# NOTE: X aliases to Y until Z ships` stale comments after the feature lands
- No-op placeholder test functions (body is only `pass` + comments) need removal
- Bare `# NOTE:` workaround comments lack GitHub issue tracking references
- Mixed casing (`# Note:` vs `# NOTE:`) or wrong canonical order (version before issue ref) needs normalizing

## Verified Workflow

### Quick Reference

| Scenario | Detection Pattern | Action |
| -------- | ----------------- | ------ |
| Runtime NOTE print | `print.*NOTE\|print.*Note:` in examples/ | Reword to plain STATUS message or factual text; remove prefix |
| Mixed casing | `# Note:` in Mojo shared/ files | Normalize to `# NOTE:` |
| Unlinked workaround NOTE | `# NOTE:` without `#[0-9]{4,}` | Add `(#NNNN)` to marker |
| Inverted canonical order | `# NOTE (Mojo vX.Y, #NNNN):` | Swap to `# NOTE(#NNNN, Mojo vX.Y):` |
| Missing version tag | `# NOTE(#NNNN):` without `, Mojo` | Append `, Mojo vX.Y` |
| TODO-style NOTE | future-tense prose: "could be added", "will be" | Convert to `# TODO:` |
| Magic-number NOTE | `# NOTE: epsilon=` or `# NOTE: tolerance=` | Extract to named module-level constant |
| Shipped-feature placeholder | `aliases to.*until.*supports` or `Will use.*when available` | Verify feature shipped, then remove stale comment |
| No-op placeholder test | `pass  # Placeholder` with zero assertions | Remove function and its call from main() |
| Generator TODO in template string | `# TODO:` inside Python string literal | Replace with `# TEMPLATE:` |
| Docstring NOTE prefix | `NOTE:` inside a docstring | Strip prefix, convert to plain prose |
| Stale "X removed" marker | references to deleted code or closed issues | Remove entirely |

### Phase 1: Discovery

Always grep before editing — issue plans are frequently stale:

```bash
# All NOTE variants (catches bare, versioned, issue-linked forms)
grep -rn "# NOTE" <scope>/ --include="*.mojo"

# Case-insensitive for runtime prints
grep -rn 'print.*NOTE\|print.*TODO\|print.*FIXME\|print.*Note:' examples/ --include="*.mojo" -i

# Magic-number inline comments
grep -rn "# NOTE:.*epsilon\|# NOTE:.*tolerance" . --include="*.mojo"

# Shipped-feature stale markers
grep -rn "aliases to.*until\|Will use.*when available\|not natively supported" . --include="*.mojo"

# Untracked workaround NOTEs (no issue reference)
grep -rn "# NOTE:" --include="*.mojo" . | grep -v "#[0-9]\{4,\}"

# Generator TODO in template strings
grep -rn "# TODO:" scripts/generators/ --include="*.py"
```

Compare grep results against the issue plan. Skip files with zero hits — they may already be clean.

### Phase 2: Categorize Each Marker

Read each NOTE in context before applying a disposition. Use the decision tree:

```
Is this a runtime print("NOTE: ...")?
  YES → Replace with STATUS: message or plain factual text

Is this a # NOTE: magic-number comment used in 2+ places?
  YES → Extract to named module-level constant; replace inline with reference

Is this a # NOTE: inside a docstring?
  YES → Strip NOTE: prefix, convert to plain prose

Is this # NOTE: describing a shipped feature's placeholder?
  YES → Confirm feature landed (grep for comptime alias or native support), then remove

Is this a no-op placeholder test (pass + comments, zero assertions)?
  YES → Remove function definition and its call from main()

Is this a # TODO: inside a generator template string?
  YES → Replace with # TEMPLATE:

Is this a bare # NOTE: workaround lacking an issue ref?
  YES → Find or create tracking issue; add (#NNNN) to marker

Is this a non-canonical format (wrong order, missing version)?
  YES → Normalize to # NOTE(#NNNN, Mojo vX.Y): format
```

**Always keep**: FP16/SIMD compiler limitation notes, epsilon/tolerance justifications with issue refs,
active Track/Phase blocker notes, Mojo language limitation notes (`no __all__`, missing stdlib APIs).

### Phase 3: Apply Edits

Use the `Edit` tool with `replace_all: false` for unique strings. For exact duplicates across
a file, use `replace_all: true`. Always Read a file before editing it.

**Normalize casing:**

```
old: # Note: This comment explains the workaround.
new: # NOTE: This comment explains the workaround.
```

**Link workaround NOTE to tracking issue:**

```
old: # NOTE: Batch iteration blocked by Track 4 (Python-Mojo interop).
new: # NOTE(#3092): Batch iteration blocked by Track 4 (Python-Mojo interop).
     # Track resolution via #3076. Implement when Python-Mojo interop is available.
```

**Fix canonical order (issue ref first):**

```
old: # NOTE (Mojo v0.26.1, #3076): Batch iteration blocked...
new: # NOTE(#3076, Mojo v0.26.1): Batch iteration blocked...
```

**Convert runtime NOTE print to STATUS:**

```mojo
# Before
print("Note: Training requires batch_norm2d_backward implementation.")
print("See GAP_ANALYSIS.md for details.")

# After
print("Training requires batch_norm2d_backward (see GAP_ANALYSIS.md).")
```

**Remove shipped-feature placeholder:**

```mojo
# Before
# NOTE: bfloat16_dtype aliases to float16_dtype until Mojo supports BF16
return PrecisionConfig(...)

# After
return PrecisionConfig(...)
```

**Extract magic-number NOTE to named constant (Mojo):**

```mojo
# Before (at usage site)
# NOTE: epsilon=3e-4 for float32 prevents precision loss in matmul (see #2704)
var epsilon = 3e-4 if dtype == DType.float32 else 1e-3

# After (module-level constant)
# Epsilon for float32 gradient checking in matmul-heavy layers.
# 3e-4 gives 1.2% error, within tolerance. See issue #2704 for full analysis.
alias GRADIENT_CHECK_EPSILON_FLOAT32: Float64 = 3e-4
alias GRADIENT_CHECK_EPSILON_OTHER: Float64 = 1e-3

# At usage site (brief reference only)
var epsilon = GRADIENT_CHECK_EPSILON_FLOAT32 if dtype == DType.float32 else GRADIENT_CHECK_EPSILON_OTHER
```

**Replace generator TODO with TEMPLATE:**

```python
# Before (inside Python string literal / generated output)
# TODO: Add forward pass implementation

# After
# TEMPLATE: Add forward pass implementation
```

### Phase 4: Verify

```bash
# Zero unlinked workaround NOTEs
grep -rn "# NOTE:" --include="*.mojo" . | grep -v "#[0-9]\{4,\}"

# Zero mixed-casing
grep -rn "# Note:" --include="*.mojo" <scope>/

# Zero stale runtime NOTE prints
grep -rn 'print.*NOTE\|print.*Note:' examples/ --include="*.mojo" -i

# Zero generator TODOs in template strings
grep -r "# TODO:" scripts/generators/

# Zero remaining shipped-feature markers
grep -rn "aliases to.*until\|Will use.*when available" . --include="*.mojo"
```

### Phase 5: Pre-commit

```bash
pixi run pre-commit run --all-files
# If mojo-format fails with GLIBC errors (pre-existing env issue, not caused by comment changes):
SKIP=mojo-format pixi run pre-commit run --all-files
```

All non-mojo hooks (ruff, markdownlint, trailing-whitespace, end-of-file-fixer, check-yaml) must pass.
`mojo-format` passes in CI Docker (GLIBC >= 2.34) even when skipped locally.

### Phase 6: Commit and PR

```bash
git add <changed-files>
git commit -m "$(cat <<'EOF'
cleanup(<scope>): normalize inline NOTE/TODO/placeholder comments

<Summary of changes: markers linked, casing normalized, stale removed, etc.>

Closes #<issue>
Part of #<parent-epic>
EOF
)"
git push -u origin <branch>
gh pr create --title "cleanup(<scope>): ..." --body "Closes #<issue>"
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusting issue plan line numbers | Used plan's line numbers directly to edit files | Files were partially fixed already; line numbers had shifted | Always grep to discover actual state — issue plans go stale |
| Case-sensitive grep only | Used `print.*NOTE` without `-i` flag | Missed `Note:` (mixed case) variants in inference.mojo files | Use case-insensitive grep (`-i`) or include all case variants |
| Linking all NOTEs | Tried to add issue refs to all `# NOTE:` lines including informational ones | Created unnecessary issue noise | Only link NOTEs that describe temporary workarounds or blocked features |
| Creating new issues without searching first | Created new tracking issues for each group immediately | Would have created duplicates of existing cleanup issues | Always `gh issue list --search` before creating |
| Modifying multi-line NOTE body unnecessarily | Added `(tracked in #NNNN)` to body lines that already had `#NNNN` | No change needed — body reference is sufficient | If `#NNNN` appears anywhere in the NOTE block, it is already linked |
| Adding `alias` inside a struct body | Put constants as struct-level aliases instead of module scope | Module-level names are cleaner and more discoverable | Place aliases at module scope before the struct definition |
| Keeping long rationale at usage sites | Left detailed comment at each usage site instead of at the constant definition | Creates duplication; all three sites need updating if value changes | Move all rationale to the constant definition; keep usage-site comments brief |
| Looking for pooling backward tester | Searched for methods not in the audit scope | Method did not exist | Confirm scope first before attempting to audit non-existent targets |
| Assuming BatchNorm tolerance matches activation | Chose `1e-2` activation pattern for BatchNorm | BatchNorm accumulates division errors across N x H x W, matching conv2d not elementwise | Match tolerance to the accumulation regime, not to the layer category |
| Searching only the issue-cited file | Grepped only the one file mentioned in the issue body | Missed 3 other files with stale comments | Always grep the entire repo with multiple patterns |
| Editing main repo file from worktree session | Edited `/repo/shared/__init__.mojo` instead of worktree copy | File is tracked by `main`, not the feature branch | Always edit the worktree path, not the main repo path |
| Running `just pre-commit-all` | Called `just` command runner | `just` not on PATH in this environment | Use `pixi run pre-commit run --all-files` directly |
| Batch-replacing all TODOs at once in generator | Used `replace_all=True` for a single Edit call per file | TODOs had slightly different surrounding context | Use individual targeted Edit calls per TODO for precision |
| Deriving dispositions from grep alone | Classified all occurrences from scratch without reading issue plan | Slow and error-prone when many occurrences look similar | Read the issue plan comment first — it often contains a pre-computed disposition table |

## Results & Parameters

### Canonical NOTE Format Reference (Mojo)

```mojo
# Plain limitation note (no issue ref):
# NOTE (Mojo v0.26.1): <description of limitation>

# Limitation note with issue reference (issue number FIRST):
# NOTE(#NNNN, Mojo v0.26.1): <description of limitation>
# Track resolution via #<parent>. Implement when <condition>.

# Wrong — version before issue (fix by swapping):
# NOTE (Mojo v0.26.1, #3076): ...

# Wrong — issue but no version (fix by appending version):
# NOTE(#3076): ...

# Wrong — TODO-style disguised as limitation (convert):
# NOTE (Mojo v0.26.1): X could be added if needed
# → # TODO: Add X if needed
```

### Gradient Checking Constant Pattern

| Constant | Value | Use Case |
| -------- | ----- | -------- |
| `GRADIENT_CHECK_EPSILON_FLOAT32` | `3e-4` | float32 matmul-heavy layers (conv2d, linear) |
| `GRADIENT_CHECK_EPSILON_OTHER` | `1e-3` | Non-float32 dtypes (BF16, FP16) |

### Tolerance Values by Layer Type

| Layer | Tolerance | Rationale |
| ----- | --------- | --------- |
| Conv2d backward | `1e-1` (10%) | Accumulated matmul errors |
| Linear backward | `0.10` wide + `0.01` abs | Matrix op accumulated errors (see #2704) |
| Activation backward | `1e-2` float32, `1e-1` other | Elementwise, less accumulation |
| BatchNorm backward | `1e-1` (10%) all dtypes | Normalization divides across N x H x W, same as conv2d |

### NOTEs to Always Keep (Do Not Remove)

- FP16 SIMD vectorization blocked by compiler limitation
- `epsilon=3e-4` precision justifications referencing issue #2704
- Track 4 (Python-Mojo interop) blocker references while Track 4 is active
- Mojo language limitation notes (`no __all__`, `no os.remove()`, BF16 alias)
- Open issue/tracker references that are still actionable

### Pre-commit Command Reference

```bash
# Standard
pixi run pre-commit run --all-files

# Skip mojo-format when GLIBC < 2.32 on host (passes in CI Docker)
SKIP=mojo-format pixi run pre-commit run --all-files

# Check git status after pre-commit (ruff-format may auto-reformat Python files)
git status
git add <ruff-reformatted-file>
```

### Grep Patterns by Scenario

```bash
# All NOTE variants
grep -rn "# NOTE" <scope>/ --include="*.mojo"

# Runtime NOTE prints (case-insensitive)
grep -rn 'print.*NOTE\|print.*TODO\|print.*FIXME\|print.*Note:' examples/ --include="*.mojo" -i

# Untracked NOTEs
grep -rn "# NOTE:" --include="*.mojo" . | grep -v "#[0-9]\{4,\}"

# Stale shipped-feature markers
grep -rn "aliases to.*until\|Will use.*when available\|not natively supported\|Uncomment when" . --include="*.mojo"

# Generator template TODOs
grep -rn "# TODO:" scripts/generators/ --include="*.py"
```
