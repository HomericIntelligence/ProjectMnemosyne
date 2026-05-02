---
name: mojo-api-name-reconciliation
description: 'Reconcile planned API names in Mojo test placeholders and documentation
  comments with actual implemented names after an import audit. Use when: placeholder
  tests use old planned names, __init__.mojo docs are stale, or following up on import
  audit issues.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mojo-api-name-reconciliation |
| **Category** | documentation |
| **Complexity** | Low |
| **Risk** | Minimal — comment/documentation only changes |
| **Trigger** | Follow-up issue after import audit (e.g., issue #3222 following audit #3093) |

## When to Use

- Placeholder tests (e.g., `test_packaging.mojo`) were written against originally planned API names that changed during implementation
- `shared/__init__.mojo` docstring or commented-out imports use stale planned names (e.g., `Conv2D` instead of `Conv2dLayer`)
- A GitHub issue specifically calls out a list of old names to replace with actual names
- After an import audit reveals name divergence between plan and implementation

## Verified Workflow

### 1. Read the issue and understand the mapping

```bash
gh issue view <number> --comments
```

Key mappings discovered in this session:

| Old (planned) | New (actual) | Location |
| --- | --- | --- |
| `Conv2D` | `Conv2dLayer` | `shared/core/layers/conv2d.mojo` |
| `ReLU` | `ReLULayer` | `shared/core/layers/relu.mojo` |
| `Tensor` | `ExTensor` | `shared/core/extensor.mojo` |
| `Accuracy` | `AccuracyMetric` | `shared/training/metrics/__init__.mojo` |
| `DataLoader` | `BatchLoader` | `shared/data/__init__.mojo` |
| `TensorDataset` | `ExTensorDataset` | `shared/data/` |

### 2. Verify actual names by searching the implementation

```bash
# Check struct names in layers
grep -rn "struct.*Layer\|struct Conv\|struct ReLU" shared/core/layers/

# Check metric names
grep -n "AccuracyMetric" shared/training/metrics/__init__.mojo

# Check data loader names
grep -n "BatchLoader\|DataLoader" shared/data/__init__.mojo
```

### 3. Identify all files containing old names

```bash
# Find test files with old names
grep -n "Conv2D\b\|\"ReLU\"\|\"Tensor\"\|\"Accuracy\"\|\"DataLoader\"" tests/shared/integration/test_packaging.mojo

# Find __init__.mojo docs with old names
grep -n "Conv2D\b\|\bTensor\b\|\bAccuracy\b\|\bDataLoader\b" shared/__init__.mojo
```

### 4. Apply targeted edits

Use the `Edit` tool with exact string replacement. Changes are **comments only** — no functional code.

Key locations in `test_packaging.mojo`:
- Commented-out `test_public_api_exports` body (lines ~277-283): update the `expected_exports` list

Key locations in `shared/__init__.mojo`:
- Module docstring Usage/Example sections (top of file)
- Commented-out import lines (~line 54-82)
- Public API documentation block (~lines 104-115)

### 5. Verify no old names remain

```bash
grep -n "Conv2D\b\|\"ReLU\"\|\"Tensor\"\|\"Accuracy\"\|\"DataLoader\"\|TensorDataset\b" \
  shared/__init__.mojo tests/shared/integration/test_packaging.mojo
```

### 6. Run pre-commit and commit

```bash
pixi run pre-commit run --all-files
git add shared/__init__.mojo tests/shared/integration/test_packaging.mojo
git commit -m "fix(tests): update test_packaging.mojo placeholders to actual API names"
git push -u origin <branch>
gh pr create --title "fix(tests): ..." --body "Closes #<number>"
gh pr merge --auto --rebase
```

## Results & Parameters

- **Files changed**: 2 (`tests/shared/integration/test_packaging.mojo`, `shared/__init__.mojo`)
- **Nature of changes**: Comments and documentation strings only — zero functional risk
- **Pre-commit hooks**: All pass (mojo format, markdown lint, trailing whitespace, etc.)
- **CI note**: `mojo test` cannot run locally due to GLIBC version mismatch on this host; tests run in Docker CI
- **PR**: Created and auto-merge enabled immediately after push

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Running `mojo test` locally | Tried `pixi run mojo test tests/shared/integration/test_packaging.mojo` | GLIBC version mismatch (`GLIBC_2.32/2.33/2.34` not found) — Mojo binary incompatible with host libc | For this project, Mojo tests must run in Docker CI; pre-commit hooks are sufficient local verification |
| Searching for `Linear` as old name | Grepped for `\bLinear\b` to update | `Linear` struct actually exists in `shared/core/layers/linear.mojo` — it's a valid current name, not a stale planned name | Always verify against the implementation before replacing; not all "old" names are actually stale |
