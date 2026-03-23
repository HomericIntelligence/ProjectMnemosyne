---
name: pr-review-pii-fix-gradebook-leak
description: "How to review a privacy feature branch for PII leaks and fix gradebook identity re-hydration in a FastAPI/ARQ pipeline. Use when: (1) reviewing a branch that introduces tokenization/anonymization for student data, (2) tracing PII through multi-step async job pipelines, (3) fixing output artifacts (xlsx/docx) that bypass an identity lookup."
category: architecture
date: 2026-03-23
version: "1.0.0"
user-invocable: false
tags: [privacy, pii, fastapi, arq, gradebook, identity-map]
---

# PR Review: PII Leak in Gradebook via Missing Identity Lookup

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-23 |
| **Objective** | Review `privacy-safeguard-sprint` branch for correctness before merging to main; fix any blocking issues |
| **Outcome** | Found and fixed one critical bug (gradebook PII leak); merged to main successfully |

## When to Use

- Reviewing a branch that adds tokenization / anonymization to a data pipeline
- Tracing how student (or user) display names flow through async job workers into output files
- Fixing cases where an identity lookup was added to some output paths but not all
- Merging a feature branch through an intermediate branch before landing on main

## Verified Workflow

### Quick Reference

```bash
# Review the branch diff via GitHub web (no gh CLI needed)
# https://github.com/<owner>/<repo>/compare/main...<branch>

# Fix: add identity_lookup param through the call chain
# spreadsheet.py: _cell_value_for_col → _write_data_row → _write_batch_sheet → generate_gradebook
# post_batch.py: build cross-batch identity lookup, pass to generate_gradebook

# Run tests
python3 -m pytest tests/ -q

# Merge flow when fix is a single commit on top of feature branch:
# Option A (simplest): open PR from fix branch directly to main — contains both commits
# Option B: fast-forward feature branch then PR feature branch → main
```

### Detailed Steps

1. **Fetch and diff the branch** against main to enumerate all changed files
2. **Trace each output artifact** (`.docx`, `.xlsx`, checklist) and verify the identity re-hydration lookup is passed all the way through to the final write
3. **Identify the gap**: `generate_gradebook` in `spreadsheet.py` read `result.student_name` directly — the LLM-extracted real name — instead of consulting `identity_lookup`
4. **Fix the call chain**: add `identity_lookup: Optional[dict[str, str]] = None` as a parameter to `_cell_value_for_col`, `_write_data_row`, `_write_batch_sheet`, and `generate_gradebook`; in `_cell_value_for_col` prefer `identity_lookup[result.identity_map_id]` when available
5. **Expand the lookup in `post_batch_job`**: the existing `identity_lookup` only covered the current batch's `completed_results`; the gradebook queries all batches, so build a separate `gradebook_identity_lookup` from `all_student_results` before calling `generate_gradebook`
6. **Run tests** — all 43 pass
7. **Commit, push fix branch, open PR to main** (fix branch contains both the sprint commit and the fix commit — clean merge)
8. **Clean up branches** after merge: delete remote branches, fast-forward local main, prune worktrees

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `/advise` before review | Tried to clone ProjectMnemosyne via `gh repo clone` | `gh` CLI not on PATH in Claude Code's non-interactive shell | Add `/opt/homebrew/bin` to `env.PATH` in `~/.claude/settings.json` |
| Targeting `privacy-safeguard-sprint` as PR base | Fix commit pushed to `claude/epic-kepler`; PR opened targeting sprint branch | Sprint branch was already merged to main separately (PR #2), leaving the fix branch orphaned | When fix is on top of a feature branch and feature branch is already on main, open the fix PR directly to main |
| Using `gh pr create` for the fix PR | `gh` not installed | `gh` is a Homebrew package not present on this machine | Install with `brew install gh && gh auth login`; PATH fix alone is not sufficient if package is missing |

## Results & Parameters

**The critical bug pattern:**

```python
# ❌ WRONG — reads LLM-extracted real name, bypasses tokenisation
if col_key == "student_name":
    return _safe(result.student_name)

# ✅ FIXED — prefers display_name from identity map
if col_key == "student_name":
    if identity_lookup and result.identity_map_id:
        display_name = identity_lookup.get(result.identity_map_id)
        if display_name:
            return display_name
    return _safe(result.student_name)
```

**Cross-batch lookup pattern (post_batch_job, step 7):**

```python
all_identity_map_ids = [
    r.identity_map_id for r in all_student_results if r.identity_map_id
]
if all_identity_map_ids:
    all_im_result = await db.execute(
        select(StudentIdentityMap).where(
            StudentIdentityMap.id.in_(all_identity_map_ids)
        )
    )
    gradebook_identity_lookup: dict[str, str] = {
        im.id: im.display_name for im in all_im_result.scalars()
    }
else:
    gradebook_identity_lookup = {}

spreadsheet.generate_gradebook(
    ...,
    identity_lookup=gradebook_identity_lookup,
)
```

**`~/.claude/settings.json` env fix:**

```json
{
  "env": {
    "PATH": "/opt/homebrew/bin:/Users/jpw/bin:/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  }
}
```

**To install `gh` after PATH is set:**

```bash
brew install gh
gh auth login
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| teachwithcolin | Privacy safeguard sprint — student PII protection | FastAPI + ARQ workers + openpyxl gradebook |
