---
name: note-variant-canonical-audit
description: 'Audit Mojo production files for non-canonical # NOTE variants: wrong
  issue/version order, missing version tag, or TODO-style notes masquerading as limitation
  notes. Use when: follow-up cleanup after a prior audit, grep shows mixed ordering,
  or limitation NOTEs lack version tags.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Skill** | note-variant-canonical-audit |
| **Category** | documentation |
| **Language** | Mojo |
| **Trigger** | Follow-up cleanup issue auditing production `shared/` files for `# NOTE` canonical format |
| **Outcome** | All `# NOTE` markers use canonical format; TODO-style notes converted to `# TODO:` |

## When to Use

- A follow-up GitHub issue (e.g., "Audit remaining # NOTE variants in shared/ production files")
  targets production files explicitly excluded from a prior cleanup issue
- Grep reveals mixed ordering: some notes use `# NOTE (Mojo v0.26.1, #3076):` (version-first)
  while the canonical standard is `# NOTE(#NNNN, Mojo v0.26.1):` (issue-first)
- Limitation NOTEs in `trainer_interface.mojo` or similar files have `# NOTE(#NNNN):` but no version tag
- A NOTE comment describes future work ("could be added here if needed") rather than an actual
  language/compiler limitation

## Canonical Format Reference

```mojo
# Plain limitation note (no issue ref):
# NOTE (Mojo v0.26.1): <description of limitation>

# Limitation note with issue reference (issue number FIRST):
# NOTE(#NNNN, Mojo v0.26.1): <description of limitation>

# Wrong — version before issue:
# NOTE (Mojo v0.26.1, #3076): ...   ← swap to # NOTE(#3076, Mojo v0.26.1):

# Wrong — issue but no version:
# NOTE(#3076): ...                  ← add , Mojo v0.26.1

# Wrong — TODO-style disguised as limitation note:
# NOTE (Mojo v0.26.1): X could be added if needed  ← convert to # TODO: Add X if needed
```

## Verified Workflow

### Quick Reference

| Change Type | Detection Pattern | Action |
|-------------|------------------|--------|
| Inverted order | `# NOTE (Mojo v0.26.1, #` | Swap to `# NOTE(#NNNN, Mojo v0.26.1):` |
| Missing version | `# NOTE(#\d+):` without `, Mojo` | Add `, Mojo v0.26.1` after issue ref |
| TODO-style | `# NOTE.*could be added\|if needed\|will be implemented` (future tense prose) | Convert to `# TODO:` |
| Already canonical | `# NOTE(#\d+, Mojo v` or `# NOTE (Mojo v` | No change |

### 1. Read the issue plan

```bash
gh issue view <number> --comments
```

The plan comment typically contains a disposition table per file — use it as the
authoritative checklist rather than re-deriving dispositions from scratch.

### 2. Full discovery grep

```bash
grep -r "# NOTE" shared/ --include="*.mojo" -n
```

Count occurrences per file. Cross-check against the plan's disposition table.

### 3. Read each affected file before editing

The Edit tool requires a prior Read in the same conversation. Batch reads in parallel:

```
Read shared/training/__init__.mojo (lines around target)
Read shared/training/trainer_interface.mojo (lines around target)
Read shared/utils/toml_loader.mojo (lines around target)
```

Use `offset` and `limit` to read only the relevant lines (e.g., `offset: 440, limit: 6`).

### 4. Apply targeted edits

For each non-canonical marker, use Edit with `replace_all: false`:

**Inverted order fix:**

```
old: # NOTE (Mojo v0.26.1, #3076): Batch iteration blocked...
new: # NOTE(#3076, Mojo v0.26.1): Batch iteration blocked...
```

**Missing version tag fix:**

```
old: # NOTE(#3076): Python data loader integration blocked...
new: # NOTE(#3076, Mojo v0.26.1): Python data loader integration blocked...
```

**TODO-style NOTE conversion:**

```
old: # NOTE (Mojo v0.26.1): List handling could be added here if needed
new: # TODO: Add list handling if needed
```

### 5. Post-edit verification grep

```bash
grep -r "# NOTE" shared/ --include="*.mojo" -n
```

Confirm the count is stable (no new variants introduced) and all remaining
markers match a canonical pattern.

### 6. Run pre-commit

```bash
SKIP=mojo-format pixi run pre-commit run --all-files
```

These are comment-only changes — no compilation impact. Skip `mojo-format` only
if the local GLIBC version is incompatible (Mojo requires >= 2.32).

### 7. Commit and push

```bash
git add shared/training/__init__.mojo shared/training/trainer_interface.mojo shared/utils/toml_loader.mojo
git commit -m "cleanup(shared): normalize # NOTE format in production files

Closes #<issue>"
git push -u origin <branch>
```

### 8. Create PR with auto-merge

```bash
gh pr create --title "cleanup(shared): normalize # NOTE format in production files" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Deriving dispositions from grep alone | Ran grep and tried to classify all 23 occurrences from scratch | Slow and error-prone — many occurrences look similar without file context | Read the issue plan comment first; it contains a pre-computed disposition table per file |
| Using the Skill tool for commit | Called `commit-commands:commit` skill | Denied in don't-ask permission mode | Fall back to direct `git commit` with HEREDOC message format |

## Results & Parameters

**Session stats (ProjectOdyssey issue #3883):**

- Total `# NOTE` occurrences audited: 23 across 14 files
- Changes required: **3** (the other 20 were already canonical)
- Pre-commit result: All hooks PASS (`SKIP=mojo-format`)
- Compilation impact: None (comment-only changes)

**The 3 actual changes:**

| File | Line | Change Type | Detail |
|------|------|-------------|--------|
| `shared/training/__init__.mojo` | 443 | Inverted order | `(Mojo v0.26.1, #3076)` → `(#3076, Mojo v0.26.1)` |
| `shared/training/trainer_interface.mojo` | 385 | Missing version | `# NOTE(#3076):` → `# NOTE(#3076, Mojo v0.26.1):` |
| `shared/utils/toml_loader.mojo` | 115 | TODO-style | `# NOTE (Mojo v0.26.1): List handling could be added` → `# TODO: Add list handling if needed` |

**Files confirmed already canonical (no changes needed):**

- `shared/data/_datasets_core.mojo` (5 occurrences)
- `shared/training/callbacks.mojo`, `shared/training/checkpoint.mojo`
- `shared/core/__init__.mojo`, `shared/core/broadcasting.mojo`, `shared/core/activation_simd.mojo`
- `shared/data/__init__.mojo`, `shared/__init__.mojo`
- `shared/utils/training_args.mojo`, `shared/utils/file_io.mojo`, `shared/utils/profiling.mojo`
- `shared/utils/__init__.mojo`, `shared/utils/toml_loader.mojo` (line 96)
- `shared/testing/layer_testers.mojo` (2 occurrences)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3883, PR #4821 | [notes.md](../references/notes.md) |
