---
name: planning-reuse-existing-public-env-reader
description: "When a TASK/issue says to PROMOTE or EXPORT a private helper (e.g. `make _read_int_env public`), FIRST grep the whole package for an ALREADY-PUBLIC function that does the same job and reuse THAT as the canonical source — the issue's suggested fix may be superseded by repo reality. Then collapse the private duplicate to a 1-line delegate (do NOT delete it if it has in-module callers), and prioritize any MODULE-TOP-LEVEL env coercion as the real bug (fatal-at-import beats function-body reads). Use when: (1) an issue proposes exporting/renaming a private `_helper` to public, (2) you suspect an already-public equivalent exists in a library-layer module like constants.py, (3) a base-layer module reads `int(os.environ.get(...))` at import time, (4) routing a base-layer module through another module risks pulling forbidden transitive imports into the base import surface, (5) swapping `int(os.environ.get(NAME, \"1800\"))` for a typed reader and the string default must become an int default."
category: architecture
date: 2026-06-30
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [planning, dry, env-vars, canonical-source, reuse-over-promote, import-time-coercion, delegate-shim, import-surface, library-layer, hephaestus, anchor-on-literal]
---

# Planning: Reuse an Existing Public Env Reader Instead of Promoting a Private One

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-30 |
| **Objective** | Plan ProjectHephaestus #1431: the issue proposed making the private `claude_timeouts._read_int_env` public/exported and routing two automation call sites through it. |
| **Outcome** | Plan written: do NOT promote the private helper — `hephaestus/constants.py` already has a PUBLIC, library-layer, tested `read_timeout_env(env_name, default, *, legacy_names=())` doing the same job. Reuse THAT as the canonical source, collapse `_read_int_env` to a 1-line delegate (keep it — it has 6 in-module callers), and fix the real bug: `helpers.py` reads `int(os.environ.get(...))` at MODULE TOP LEVEL (fatal-at-import). Plan was NOT executed. |
| **Verification** | unverified — planning session only; no code applied, no tests run, CI not confirmed. |

## When to Use

- An issue/task proposes "make the private `_helper` public" / "export `_read_int_env`" / "rename and expose this helper" — before doing that, look for an already-public equivalent.
- You suspect a library-layer module (e.g. `constants.py`) already exposes a public, tested function doing the same coercion/validation the private one does.
- A base-layer module performs `int(os.environ.get(...))` at MODULE TOP LEVEL, so a malformed value is fatal at IMPORT — strictly worse than a function-body read.
- You are about to add `from X import Y` to a base-layer module and need to be sure it won't drag forbidden transitive imports into the base `import <package>` surface.
- You are swapping `int(os.environ.get(NAME, "1800"))` for a typed reader and must convert the string default to the matching int default without drift.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 1. The issue says "export the private helper" — FIRST grep for an already-PUBLIC equivalent.
grep -rnE 'def read_timeout_env|def [a-z_]*read[a-z_]*env' hephaestus/   # find public readers
grep -rn  'def _read_int_env'                                  hephaestus/   # the private one the issue cites
# If a public, library-layer, tested reader exists, it — not the private helper — is the canonical source.

# 2. Re-anchor on the LITERAL expressions (line numbers below are plan-time grep, NOT pinned — they DRIFT).
grep -rn  'int(os.environ.get'        hephaestus/                          # find every eager coercion
grep -rn  '_read_int_env'             hephaestus/automation/               # the in-module callers to keep

# 3. The MODULE-TOP-LEVEL read is the real bug (fatal at import), not just the two function-body call sites.
grep -rnE '^[A-Z_]+\s*=\s*int\(os\.environ' hephaestus/                     # import-time landmines

# 4. Before adding `from hephaestus.constants import read_timeout_env` to a base-layer module, PROVE no leak.
python3 -c 'import hephaestus'                                              # must not pull curses/fcntl/pydantic/automation
pixi run pytest tests/unit/test_import_surface.py tests/unit/utils/test_no_import_cycles.py -q
```

```python
# CANONICAL public reader (already exists, library-layer, tested) — reuse THIS, don't promote the private one.
# hephaestus/constants.py
def read_timeout_env(env_name, default, *, legacy_names=()):
    ...  # logs + falls back on ValueError, never raises

# BEFORE — issue's suggestion: export the private duplicate. helpers.py top-level read is the real landmine.
# hephaestus/automation/helpers.py  (MODULE TOP LEVEL — fatal at IMPORT on a bad value)
METADATA_TIMEOUT = int(os.environ.get("HEPH_METADATA_TIMEOUT", "1800"))     # dies at import on garbage

# AFTER — reuse the public reader; never-raising, import-safe. String default "1800" -> int default 1800.
from hephaestus.constants import read_timeout_env
METADATA_TIMEOUT = read_timeout_env("HEPH_METADATA_TIMEOUT", 1800)

# AFTER — collapse the private duplicate to a thin delegate (DO NOT delete: 6 in-module callers).
# hephaestus/automation/claude_timeouts.py
def _read_int_env(name, default):
    return read_timeout_env(name, default)   # zero call-site churn, zero behavior change
```

### Detailed Steps

1. **Treat the issue's "export the private helper" as a hypothesis, not a mandate.** grep the whole package for an already-public function doing the same job FIRST. In #1431 the issue said to export `claude_timeouts._read_int_env`, but `hephaestus/constants.py` already had a PUBLIC, library-layer, tested `read_timeout_env(env_name, default, *, legacy_names=())`. The public function is more DRY and is the canonical source — the issue's suggested fix was superseded by repo reality.

2. **Keep the private duplicate as a 1-line delegate; do NOT delete it.** `_read_int_env` had 6 in-module callers. Collapsing its body to `return read_timeout_env(name, default)` is zero call-site churn and zero behavior change (both log + fall back on `ValueError` identically). Deleting it would force editing 6 call sites for no benefit.

3. **The import-time landmine is the real bug, not just the two automation call sites.** `helpers.py` reads `int(os.environ.get(...))` at MODULE TOP LEVEL, so a malformed value is fatal at IMPORT — before any handler runs — strictly worse than the function-body reads in `ci_driver`/`loop_runner`. Routing through the never-raising public reader removes the fatal-at-import path. (Cross-references `architecture-defer-env-coercion-lazy-resolver`.)

4. **Re-grep the literal expressions before editing — line numbers WILL drift.** Anchor on the literal expression, not the plan-time line numbers.

5. **Prove no import-surface leak before adding the import to a base-layer module.** Adding `from hephaestus.constants import read_timeout_env` to `helpers.py` (base layer) could pull `constants.py`'s transitive imports into the base `import hephaestus` surface, which forbids `curses/fcntl/pydantic/automation.*`. Run the import-surface + no-import-cycle tests; do not assert it's clean without running them.

6. **Convert the string default to the matching int default when swapping.** `int(os.environ.get(NAME, "1800"))` -> `read_timeout_env(NAME, 1800)`: the string defaults `"1800"/"200"/"10"/"120"` must become the matching int defaults. Diff each one — an easy typo.

## Verified Workflow

_Not applicable._ This skill was captured from a planning session and is `unverified`: no code was applied, no tests were run, and CI was not confirmed, so there is no verified workflow. The actionable, hypothesis-level methodology lives under **Proposed Workflow** above and must be treated as unvalidated until CI confirms it. (This placeholder section exists only because `scripts/validate_plugins.py` requires the literal `## Verified Workflow` heading; it makes no verification claim.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Follow the issue literally and export the private helper | Make `claude_timeouts._read_int_env` public and route the two automation sites through it | A PUBLIC, library-layer, tested `read_timeout_env` already existed in `constants.py` doing the same job — promoting the private duplicate is LESS DRY and creates two public readers | grep for an already-public equivalent BEFORE promoting a private one; the issue's suggested fix can be superseded by repo reality — reuse the existing public function as the canonical source |
| Delete the private `_read_int_env` after introducing the delegate | Remove the helper entirely and rewrite its 6 in-module callers to call `read_timeout_env` | 6 call-site edits for zero benefit; expands the diff and blast radius with no behavior change | Collapse the body to a 1-line `return read_timeout_env(...)` delegate; keep the symbol so its 6 callers are untouched |
| Fix only the two function-body call sites named in the issue | Route `ci_driver` / `loop_runner` reads through the reader, ignore `helpers.py` | Misses the WORST case: `helpers.py:top-level` `int(os.environ.get(...))` is fatal at IMPORT, before any handler — the actual bug | Audit for MODULE-TOP-LEVEL coercion first; fatal-at-import beats function-body reads in severity |
| Add `from hephaestus.constants import read_timeout_env` to `helpers.py` and assume no leak | Asserted (by grepping that `constants.py` doesn't import `helpers`/`utils`) that the base import surface stays clean — without running anything | `constants.py`'s OWN transitive imports were never inspected; they could pull `curses/fcntl/pydantic/automation.*` into the base `import hephaestus` surface that `test_import_surface.py` forbids | Run `tests/unit/test_import_surface.py` + `test_no_import_cycles.py`; a grep that one module doesn't import another does NOT prove the transitive surface is clean |
| Keep the string default when swapping to the typed reader | `read_timeout_env(NAME, "1800")` (leave the string) | The reader expects an int default; the string default must become `1800`/`200`/`10`/`120` — silent type/default drift | Convert each string default to the matching int and diff every one |
| Test by `importlib.reload`-ing the base-layer module mid-suite | New `test_helpers_timeouts.py` reloads `helpers` to re-read `METADATA_TIMEOUT`/`NETWORK_TIMEOUT` | Other modules may hold a reference to the OLD int constant; the reload can leak state across tests; `finally: importlib.reload(helpers)` is a mitigation, not a guarantee | Prefer testing `read_timeout_env` directly (already covered) and asserting `helpers` simply *calls* it — avoid reloading a base-layer module mid-suite |

## Results & Parameters

**Most uncertain assumptions a reviewer should focus on (all UNVERIFIED — this is the heart of the plan):**

- **Plan never executed.** No code applied, no tests run, CI not confirmed (verification = unverified). Everything here is a hypothesis.
- **Line numbers are UNVERIFIED-by-edit and WILL DRIFT.** `ci_driver.py:1516`, `loop_runner.py:1185,81`, `claude_timeouts.py:41-50,91-169`, `helpers.py:24-25`, `constants.py:70-91` were located by grep at plan time, NOT pinned by editing. Re-grep the literal expressions before editing (project memory: "anchor on the literal expression, not line numbers").
- **No-import-cycle claim is ASSERTED, not proven by running anything.** I grepped that `constants.py` doesn't import `helpers`/`utils`, and that `loop_runner.py:81` already imports from `hephaestus.constants`. But I did NOT run an import or `tests/unit/utils/test_no_import_cycles.py`. Adding `from hephaestus.constants import read_timeout_env` to `helpers.py` (base layer) could pull `constants.py`'s transitive imports into the base `import hephaestus` surface; `tests/unit/test_import_surface.py` forbids `curses/fcntl/pydantic/automation.*`. I did NOT inspect `constants.py`'s transitive imports — UNVERIFIED reliance. The reviewer/implementer MUST run both tests.
- **The two helpers are assumed behavior-equivalent but were EYEBALLED, not diffed under test.** `read_timeout_env` catches only `ValueError` (NOT `TypeError`) and logs a slightly different message ("Ignoring non-integer %s=%r; using default %ds") than `_read_int_env`. No test asserts the log message, so collapsing is assumed safe — a reviewer should confirm no test in `test_claude_timeouts.py` asserts the exact warning text or patches `_read_int_env` via `patch.object`.
- **`importlib.reload`-based test is FRAGILE.** Reloading a base-layer module mid-suite can leak state if another module holds a reference to the old `METADATA_TIMEOUT`/`NETWORK_TIMEOUT` int. The `finally: importlib.reload(helpers)` restore is a mitigation, not a guarantee. Prefer testing `read_timeout_env` directly and asserting `helpers` calls it.
- **Default-value drift.** `int(os.environ.get(NAME, "1800"))` -> `read_timeout_env(NAME, 1800)`: string defaults `"1800"/"200"/"10"/"120"` must become matching int defaults. Easy to typo; diff each default.

**Integration point:** ProjectHephaestus issue **#1431** — proposed exporting `claude_timeouts._read_int_env`; the plan instead reuses the existing public `hephaestus/constants.py` `read_timeout_env`. Plan-stage only — **unverified**.

**Generalization (the durable pattern):** When an issue proposes promoting/exporting a private helper, FIRST grep the package for an already-public equivalent and make THAT the canonical source — the issue's fix may be superseded by repo reality. Keep the private duplicate as a thin delegate when it has in-module callers (zero churn). Prioritize module-top-level env coercion as the real bug (fatal-at-import). Before routing a base-layer module through another module, RUN the import-surface and no-import-cycle tests — a grep does not prove the transitive surface is clean. Anchor every edit on the literal expression, never on line numbers.

## Related Skills

- `architecture-defer-env-coercion-lazy-resolver` — the import-time-safety angle: defer eager top-level `int()/float()/json.loads()` of env vars out of import. This skill's step 3 (the `helpers.py` top-level read) is the same fatal-at-import landmine; this skill adds the "reuse the existing public reader as canonical" planning move.
- `dry-refactoring-workflow` — general DRY consolidation. This skill is the narrower "discover an already-public equivalent supersedes the issue's export-the-private suggestion" case.
- `pola-consolidate-duplicated-silent-default-resolver` — consolidating duplicates into one shared resolver; shares the "collapse duplicates into a single canonical source" philosophy.
- `dry-refactoring-plan-assumption-audit` — the hidden-assumption checklist for DRY consolidation plans (shim re-export, test porting, signature collision); complements the import-surface and default-drift risks called out here.
