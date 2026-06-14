---
name: ci-ruff-format-collapses-handwrapped-comprehensions
description: "Deleting a filter clause from a hand-wrapped comprehension makes ruff format collapse it onto one line, failing both the lint and pre-commit CI gates with one root cause. Use when: (1) the required `lint` check AND the `pre-commit` check both fail red with the same ruff-format root cause; (2) after hand-deleting a filter/condition clause from a multi-line list/generator comprehension (or a call), the committed layout disagrees with `ruff format`; (3) `ruff format --check` reports only `Would reformat: <file>` with no diff and you need to see the actual change."
category: ci-cd
date: 2026-06-11
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: []
---

# Ruff Format Collapses Hand-Wrapped Comprehensions After Clause Deletion

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-11 |
| **Objective** | Drive ProjectHephaestus PR #1058 (issue #814) to green CI after both the `lint` and `pre-commit` checks failed red |
| **Outcome** | Successful — one `ruff format` run fixed both checks; pure whitespace/line-wrap change, zero logic change |
| **Verification** | verified-local |

## When to Use

- The required `lint` check AND the `pre-commit` check both fail red and the underlying log message points at `ruff format` on the **same** files — these are the same gate surfaced twice, not two separate problems.
- A prior commit hand-deleted a filter/condition clause (e.g. an `if not ...` guard) from a multi-line list/generator comprehension or a multi-line call, and left it hand-wrapped without re-running the formatter.
- The `lint` job log shows `ruff format --check` printing `Would reformat: <file>` while the `pre-commit` job log shows `Ruff Format Python ... Failed - files were modified by this hook / N files reformatted`.
- `ruff format --check` reports only `Would reformat: <file>` with no `+`/`-` diff and you need to see the actual change before committing.
- Any time you hand-edit a comprehension or call in a way that changes its rendered length — shortening a multi-line expression past the line-length budget triggers a collapse the author will not anticipate.

## Verified Workflow

### Quick Reference

```bash
# Reproduce exactly what CI's lint job runs:
pixi run --environment lint ruff format --check hephaestus scripts tests
pixi run --environment lint ruff check hephaestus scripts tests

# Fix (run on the reported files, or the whole tree):
pixi run --environment lint ruff format <files>

# Confirm pre-commit agrees and SEE the actual +/- diff:
pre-commit run --all-files
```

### Detailed Steps

1. **Recognize the single-root-cause signature.** Two red checks — `lint` and `pre-commit` — whose logs both blame `ruff format` on the *same* file list are ONE problem. Do not open two investigations.
   - `lint` log: `ruff format --check` prints `Would reformat: hephaestus/automation/ensure_state_labels.py` and `...loop_runner.py`.
   - `pre-commit` log: `Ruff Format Python ... Failed - files were modified by this hook / 2 files reformatted, 312 files left unchanged`.

2. **Find the offending edit.** Look for a recent commit that deleted a clause from a comprehension/call (here: a commit titled "Remove hardcoded Odysseus skip list" that deleted a name-based filter from an org-repo enumeration comprehension). The author left it hand-wrapped across four lines:

   ```python
   return [
       e["name"]
       for e in entries
       if not e.get("isArchived", False)
       and not e.get("isFork", False)
   ]
   ```

   Once short enough to fit the line-length budget, `ruff format` collapses it onto one line:

   ```python
   return [e["name"] for e in entries if not e.get("isArchived", False) and not e.get("isFork", False)]
   ```

3. **See the actual change.** `ruff format --check` only tells you *which* files would change, not *how*. Run `pre-commit run --all-files` locally to surface the real `+`/`-` diff.

4. **Apply the fix.** Run `pixi run --environment lint ruff format <the two files>` (or on the whole tree). This is pure whitespace/line-wrap with zero logic change.

5. **Commit signed and re-verify.** Confirm both gates are green: re-run `ruff format --check` (no output / clean) and `pre-commit run --all-files` (passes).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Treat lint and pre-commit as two different problems | Chasing the `lint` red check and the `pre-commit` red check as separate failures | Both stem from the identical `ruff format` disagreement on the same 2 files | One root cause — fix `ruff format` once and both checks go green |
| Trust the committed hand-wrapped layout because it "looks formatted" | Leaving the 4-line hand-wrapped comprehension as-is | ruff collapses it onto one line once the deleted clause makes it short enough | Re-run `ruff format` after editing comprehension length; never hand-format |

## Results & Parameters

**Context:** ProjectHephaestus PR #1058, issue #814, branch `814-auto-impl`. Issue #814 removed a hardcoded "Odysseus" repo skip-list from org-repo enumeration in two modules.

**Affected files:**

- `hephaestus/automation/ensure_state_labels.py`
- `hephaestus/automation/loop_runner.py`

**The whole fix:**

```bash
pixi run --environment lint ruff format hephaestus/automation/ensure_state_labels.py hephaestus/automation/loop_runner.py
```

**Resulting diff** — pure whitespace/line-wrap, zero logic change:

```text
2 files changed, 2 insertions(+), 8 deletions(-)
```

(Each 4-line hand-wrapped comprehension `+ ... ]` collapsed to a single line: 5 source lines become 1, i.e. `1 insertion(+)` and `4 deletions(-)` per file.)

**Expected `lint`-job output before the fix:**

```text
Would reformat: hephaestus/automation/ensure_state_labels.py
Would reformat: hephaestus/automation/loop_runner.py
```

**Expected `pre-commit`-job output before the fix:**

```text
Ruff Format Python ... Failed - files were modified by this hook
2 files reformatted, 312 files left unchanged
```

**After `ruff format` + commit:** both `ruff format --check` and `pre-commit run --all-files` pass; the required `lint` check and the `pre-commit` check both go green.
