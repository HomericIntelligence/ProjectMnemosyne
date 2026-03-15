---
name: mojo-extensor-view-contract
description: "Documents the ExTensor view/owner contract for Mojo ML frameworks. Use when: (1) documenting shared-ownership tensor semantics, (2) fixing MD060 table-column-style errors, (3) expanding view contract docs with refcount lifecycle details."
category: documentation
date: 2026-03-15
user-invocable: false
---

## Overview

| Attribute   | Value                                                |
|-------------|------------------------------------------------------|
| Name        | mojo-extensor-view-contract                          |
| Category    | documentation                                        |
| Complexity  | Low                                                  |
| Typical PR  | Documentation-only, ~100 line addition               |

Documents the view/owner contract for `ExTensor` in a Mojo-based ML research platform.
The contract covers: refcount mechanics (`__copyinit__`/`__del__`), which operations
return views vs copies, the `as_contiguous()` guard pattern, and `is_view()` vs
`is_contiguous()` anti-patterns.

## When to Use

- A tensor struct uses reference counting for shared-ownership views
- Developers need to understand when mutations propagate to original tensors
- `view_with_strides()` or similar APIs are referenced but not implemented
- A doc file needs a "Refcount Mechanics" or "When to Call `as_contiguous()`" section
- `markdownlint-cli2` MD060 table-column-style errors need fixing

## Verified Workflow

### Quick Reference

```bash
# Lint the markdown after editing
pixi run npx markdownlint-cli2 docs/dev/<file>.md

# Stage and commit (docs only — no tests required)
git add docs/dev/<file>.md
git commit -m "docs(<scope>): <description>\n\nCloses #<issue>"

git push -u origin <branch>
gh pr create --title "docs(...): ..." --body "..." --label "documentation"
```

### Step 1 — Read the existing doc and source

Read the existing doc file (in `docs/dev/`) and grep the source for the relevant
patterns:

```bash
grep -n "_is_view\|_refcount\|as_contiguous\|__copyinit__\|__del__" shared/core/extensor.mojo
```

Key things to extract:

- Where `_refcount[]` is incremented (in `__copyinit__`)
- Where it is decremented and freed (in `__del__`)
- Which operations set `_is_view = True` vs `False`
- The "guard pattern" for `as_contiguous()` (often already in a matmul helper)

### Step 2 — Add three sections

**Refcount Mechanics** — explain `__copyinit__`/`__del__` lifecycle. Critical subtlety:
`_is_view` is a semantic tag only; both views and value-copies participate equally in
reference counting. Buffer freed when last reference is destroyed, regardless of
`_is_view`.

**`view_with_strides()` — Not Available** (or equivalent "proposed but not implemented"
section) — document what was proposed, why it was dropped, and redirect callers to the
existing view-returning operations using a lookup table.

**When to Call `as_contiguous()`** — the guard pattern, copy semantics (`_is_view =
False`), and anti-patterns:

```mojo
# CORRECT guard pattern
if a.is_contiguous():
    a_cont = a               # zero-copy shared-ownership
else:
    a_cont = as_contiguous(a)  # allocates C-order copy

# ANTI-PATTERN: wrong guard
if a.is_view():              # Wrong — a view can be contiguous
    a_cont = as_contiguous(a)
```

### Step 3 — Fix MD060 table-column-style linting

`markdownlint-cli2` with MD060 enforces "aligned" table style: every row's pipe
characters must align column-for-column with the header row.

**Two root causes**:

1. A cell value is wider than its header column (e.g. `` `transpose(dim0, dim1)` ``
   wider than `Operation` header)
2. Different rows have different column widths

**Fix**: Pad all columns to the width of the widest cell in each column:

```markdown
# Before (fails MD060)
| Operation | Location | View? |
|-----------|----------|-------|
| `transpose(dim0, dim1)` | `extensor.mojo` | Yes |

# After (passes MD060)
| Operation               | Location         | View? |
|-------------------------|------------------|-------|
| `transpose(dim0, dim1)` | `extensor.mojo`  | Yes   |
```

Also watch for `#<issue-number>` at line start — markdownlint parses it as an ATX
heading (MD018). Replace with `issue-<number>` or rephrase.

### Step 4 — Lint, commit, PR

```bash
pixi run npx markdownlint-cli2 docs/dev/<file>.md   # Must show "0 error(s)"

git add docs/dev/<file>.md
git commit -m "docs(<scope>): <description>\n\nCloses #<issue>\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push -u origin <branch>
gh pr create --title "docs(...): ..." --body "$(cat <<'EOF'
## Summary
- **Refcount Mechanics** — `__copyinit__`/`__del__` lifecycle
- **Not Available section** — explains unimplemented API
- **`as_contiguous()` guidance** — guard pattern, copy semantics, anti-patterns

## Verification
- markdownlint-cli2 passes with 0 errors

Closes #<issue>
EOF
)" --label "documentation"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Committed `#3236` at line start in prose | Wrote "during the #3236 development cycle" | MD018: markdownlint treats `#3236` at line start as a malformed ATX heading | Replace `#<N>` at line start with `issue-<N>` or rephrase to put the hash mid-sentence |
| Compact table style (pipes touching text) | `\|Op\|Loc\|` without padding spaces | MD060: linter requires "aligned" style — pipes must align with header row | Pad every column to the width of its widest cell, including header separator row |
| Inconsistent column widths across rows | One row had a wider cell than header | MD060: "Table pipe does not align with header for style aligned" | Count chars in every cell per column; set all to max width |

## Results & Parameters

**Skill parameters**:

```yaml
scope: docs/dev/extensor-view-contract.md
sections_added: 3  # Refcount Mechanics, view_with_strides Not Available, as_contiguous guidance
linting_tool: "pixi run npx markdownlint-cli2"
linting_errors_before: 19
linting_errors_after: 0
commit_type: docs
label: documentation
```

**Commit message template**:

```text
docs(extensor): document view contract, refcount mechanics, and as_contiguous() guidance

Expands docs/dev/extensor-view-contract.md with three sections:
- Refcount Mechanics: __copyinit__/__del__ lifecycle, _is_view as semantic tag only
- view_with_strides() Not Available: redirects to reshape/transpose/slice/broadcast_to
- When to Call as_contiguous(): guard pattern, copy semantics, anti-patterns

Closes #<issue>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```
