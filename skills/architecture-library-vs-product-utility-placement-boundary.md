---
name: architecture-library-vs-product-utility-placement-boundary
description: "Decide WHERE a new shared utility lives when an enforced automation→library import boundary plus a stdlib-only base-import-surface guard constrain the choice, and classify 'N similar' caches/duplicates before blind-merging them into one abstraction. Use when: (1) an issue offers two homes (library module vs product module) for a new shared helper and a dependency-arrow ADR + import-surface test constrain the pick, (2) you are scoping a refactor that claims several module-level caches/dicts are 'the same' and should collapse into one TTL/locking abstraction, (3) you are wrapping an ad-hoc success-only cache and must preserve exception/fallback/clear-fixture behavior."
category: architecture
date: 2026-06-30
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [architecture, library-boundary, import-surface, cache, ttl, thread-safety, toctou, planning, dry, placement]
---

# Library-vs-Product Utility Placement Under an Enforced Boundary

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Objective** | Plan placement of a new `ThreadSafeCache` utility (TTL + locking) replacing ad-hoc module-level dict caches, under ProjectHephaestus's automation→library boundary + stdlib-only base-import-surface guard |
| **Outcome** | Plan produced: place in the **library** (`hephaestus/utils/cache.py`), migrate the **two** key→value dict caches, deliberately **NOT** migrate the set-shaped `_label_cache` |
| **Verification** | unverified — planning-only session; no code written, no tests run, no CI |

## When to Use

- An issue gives you **two candidate homes** for a new shared utility (a *library* module vs a *product*/automation module) and the repo enforces a one-way dependency arrow (e.g. `docs/adr/0001-automation-library-boundary.md`: automation may import library, never the reverse).
- The repo has a **base-import-surface guard** (e.g. `tests/unit/test_import_surface.py`) asserting `import pkg` pulls no heavy deps (`curses`/`fcntl`/`pydantic`/product modules).
- An issue frames **N "similar" module-level caches/dicts** as uniformly migratable into one abstraction — before you scope, you must diff their actual SHAPES.
- You are wrapping an **ad-hoc success-only cache** in a TTL/locking abstraction and must preserve exception-propagation, fallback-caching, and the existing `clear_*()` fixture contract.

## Verified Workflow

> **Warning:** This workflow has NOT been validated end-to-end (despite the section heading, which is a fixed schema requirement). It is a **proposed**, planning-only hypothesis. No code was written, no tests were run, no CI confirmed it. Treat every placement and behavior claim below as something the implementer/reviewer MUST verify against live source and the test suite before relying on it.

### Quick Reference

```bash
# 1. Determine the dependency-arrow direction — read the ADR, do not trust the summary
cat docs/adr/0001-automation-library-boundary.md

# 2. Find every consumer of the utility-to-be. If a LIBRARY module consumes it,
#    the utility MUST live in the library (product cannot be imported by library).
grep -rn "_repo_info_cache\|_repo_slug_cache\|get_repo_slug\|clear_repo_caches" hephaestus/

# 3. Confirm the candidate library module is stdlib-only (no curses/fcntl/pydantic/automation)
grep -nE "^(import|from) " hephaestus/utils/git_utils.py | head
python -m pytest tests/unit/test_import_surface.py tests/unit/test_automation_boundary.py

# 4. COUNT and DIFF each claimed-duplicate cache — do not assume they share a shape
grep -n "_repo_info_cache\|_repo_slug_cache\|_label_cache" hephaestus/**/*.py
grep -rn "_label_cache" tests/   # tests reveal the real contract (assignment shape)
```

### Detailed Steps

1. **Placement is forced by the dependency arrow, not preference.** A utility consumed by a *library* module must live in the *library*, because the boundary forbids library→product imports. Here the choice was `hephaestus/utils/cache.py` (library) vs `hephaestus/automation/_review_utils.py` (product); because `git_utils.py` (a library module) is a consumer, only the library home is legal. Read the ADR itself — do not infer the arrow from a CLAUDE.md summary.
2. **Placement is also gated by the base-import-surface guard.** A library utility must be **stdlib-only** (`threading`, `time`, typing — no `curses`/`fcntl`/`pydantic`/automation imports), or `tests/unit/test_import_surface.py` goes red the moment any library module imports it. Verify the new module imports nothing heavy, and that adding `from hephaestus.utils.cache import ThreadSafeCache` to a consumer introduces **no import cycle**. (UNVERIFIED in this session: that `git_utils.py` imports only from `hephaestus.utils.*` and is cycle-free with the new import — planner read `git_utils.py:21-22` but did NOT run the import-surface/boundary tests.)
3. **Classify the "N similar" caches — count and DIFF, never blind-merge.** The issue framed three module-level caches as uniformly migratable. Reading the real code/tests showed only two share a shape:
   - `_repo_info_cache` and `_repo_slug_cache` are `key → value` **dict** caches → migrate to `ThreadSafeCache[K, V]`.
   - `_label_cache` is a `set[str] | None` (a whole-repo label SET plus a refresh flag), assigned directly by tests (`_github_api_module._label_cache = {"bug"}` / `= None`) and mutated in place by `gh_create_label` (`.add(name)`) — a fundamentally different SHAPE. Forcing it into `ThreadSafeCache[K, V]` would break the helpers plus ~10 tests. **Document this as an intentional non-migrated variant with a follow-up-issue note** rather than silently dropping it or jamming it into the abstraction. (Mirrors the dry-refactoring "stale N-identical claim" lesson: diff every claimed duplicate before scoping.)
4. **Preserve ad-hoc cache behavior exactly when wrapping it.**
   - **Success-only memoization:** the original caches only successes, so `get_or_compute` must NOT memoize exceptions — a raising `compute` propagates and stores nothing. Reviewer confirms the new contract matches.
   - **Fallback caching:** `get_repo_slug`'s `"repo"` fallback is currently *cached*. Fold the fallback INSIDE the compute closure so the fallback value is what gets memoized, preserving the exact current behavior (computed once, reused).
   - **Clear fixture contract:** keep `clear_repo_caches()`'s signature intact so the autouse test fixture (`test_git_utils.py:29-34`) keeps working unchanged.
   - **Double-checked locking tradeoff:** call `compute()` OUTSIDE the lock so a slow `git remote` for one key does not block other keys — accepting that a cold cache may run a duplicate concurrent compute for the SAME key (idempotent read, deliberate tradeoff vs. holding the lock across I/O).
5. **Re-verify external references before editing.** Line numbers drift; cited files may not have been opened. Re-grep `git_utils.py` / `github_api.py` and the test files, and actually read `docs/adr/0001-automation-library-boundary.md`, `tests/unit/test_import_surface.py`, and `tests/unit/test_automation_boundary.py` rather than trusting their assumed behavior.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed (or would have) | Lesson Learned |
|---------|----------------|-------------------------------|----------------|
| Place in product module | Considered `hephaestus/automation/_review_utils.py` as the home for the shared cache | A *library* module (`git_utils.py`) consumes it; library→product imports are forbidden by the boundary ADR | Placement is forced by the dependency arrow — a utility consumed by a library MUST live in the library |
| Migrate all three caches uniformly | Issue framed `_repo_info_cache`, `_repo_slug_cache`, `_label_cache` as one migration into `ThreadSafeCache[K,V]` | `_label_cache` is `set[str] \| None` (whole-repo set + refresh flag), directly assigned by tests and mutated via `.add()` — wrong SHAPE; would break helpers + ~10 tests | Count and DIFF every claimed-duplicate before scoping; document intentional non-migrated variants |
| Memoize the compute result unconditionally | Naive `get_or_compute` would cache whatever `compute` returns, including on the exception path | Original cached only SUCCESSES; caching exceptions changes behavior | Preserve success-only semantics — a raising compute propagates and stores nothing |
| Drop the fallback from the cache | Considered computing `"repo"` fallback outside the cached path | Original *caches* the `"repo"` fallback; moving it out changes which value is memoized | Fold the fallback inside the compute closure to preserve exact current behavior |
| Trust cited line numbers / ADR summary | Relied on `git_utils.py:70/73-122/...`, `github_api.py:114-115`, ADR text from CLAUDE.md | Line numbers drift after edits; the ADR and import-surface tests were never re-opened | Re-grep and re-read the actual files before editing |

## Results & Parameters

**Proposed final plan for ProjectHephaestus issue #1440 (UNVERIFIED):**
- New file `hephaestus/utils/cache.py` — `ThreadSafeCache[K, V]` with TTL (default `300s`) + `threading.Lock`, double-checked `get_or_compute(key, compute)` calling `compute` outside the lock, success-only memoization, and a `clear()` method. `time.monotonic()` for TTL (immune to wall-clock jumps).
- Migrate the two dict caches in `git_utils.py`: `_repo_info_cache`, `_repo_slug_cache` → `ThreadSafeCache` instances; fold `get_repo_slug`'s `"repo"` fallback inside the compute closure; keep `clear_repo_caches()` signature unchanged (autouse fixture `test_git_utils.py:29-34`).
- **Do NOT migrate** `github_api.py`'s `_label_cache` (`set[str] | None`, direct test assignment, in-place `.add()`); record as intentional variant + follow-up issue.

**Risks the reviewer MUST focus on:**
- **Library placement hinges on no-import-cycle + stdlib-only** — not test-verified in this session. Run `test_import_surface.py` and `test_automation_boundary.py`.
- **`_label_cache` non-migration** — confirm the issue's acceptance criteria don't REQUIRE migrating all three caches. If they do, the scope-narrowing is a deviation needing explicit justification.
- **Caching the `get_repo_slug` fallback** — a transient `git remote` failure caches `"repo"` for the whole TTL window. Flag as a conscious tradeoff (preserves current behavior) that a reviewer might consider undesirable.
- **TTL default 300s is a behavior change** — original cache was infinite (process-life). The issue explicitly asks for TTL, so the change is intended, but it alters semantics from "cache forever" to "expire after 5min" and should be called out.

**External references relied on but NOT directly verified (flag for reviewer):**
- `docs/adr/0001-automation-library-boundary.md` — cited from CLAUDE.md summary, not re-read.
- `tests/unit/test_import_surface.py`, `tests/unit/test_automation_boundary.py` — existence/behavior assumed from CLAUDE.md, not opened.
- Exact line numbers (`git_utils.py:70/73-122/129/132-156/159-162`, `github_api.py:114-115`, test lines 1095/1147) — read once, may drift; re-grep before editing.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1440 — Create ThreadSafeCache utility to replace ad-hoc module-level dict caches with TTL + locking | Planning-only session; plan produced but NOT executed (no code, no tests, no CI). Verification: **unverified**. |
