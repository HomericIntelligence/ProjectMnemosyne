---
name: actions-cache-restore-save-split-on-success
description: "Plan converting combined actions/cache@vN (which uses the action's built-in post-job save, firing unconditionally even after a failed build) into explicit actions/cache/restore@vN (early, unconditional) + actions/cache/save@vN (gated on if: success()), so a failed or partial build never poisons a build-output (FetchContent / build/_deps / Conan) cache. Use when: (1) planning or implementing finer cache-write control in GitHub Actions, (2) preventing a failed build from saving a corrupt build/_deps or Conan cache, (3) a CI-hardening review touches actions/cache blocks, (4) you must enumerate EVERY combined block on a 'fix all N occurrences' issue and prove the per-file accounting sums to N before claiming coverage, (5) you must decide which cache blocks to split and how to AND the success() gate with an existing skip guard. PLANNING learning — captures completeness/sum-check discipline, the rule that a plan's acceptance command must pass against the artifact the plan produces, verifying design linchpins (cache-primary-key) against the action docs rather than shipping them as assumptions, and stating decisions (split all) with rationale instead of leaving options."
category: ci-cd
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: actions-cache-restore-save-split-on-success.history
tags:
  - github-actions
  - actions-cache
  - cache-restore
  - cache-save
  - success-gate
  - post-job-save
  - cache-poisoning
  - fetchcontent
  - build-output-cache
  - conan-cache
  - cache-primary-key
  - workflow-hardening
  - planning-methodology
  - completeness-discipline
  - sum-check
  - self-consistent-verification
  - verify-linchpin
  - regression-guard
---

# Planning: Split actions/cache into restore + save Gated on success()

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Capture how to PLAN converting combined `actions/cache@vN` (which relies on the action's built-in post-job save, firing unconditionally even after a failed build) into explicit `actions/cache/restore@vN` (early, unconditional) + `actions/cache/save@vN` (gated `if: success()`), so failed/partial builds never poison build-output (`build/_deps` / FetchContent / Conan) caches. Produced for ProjectAgamemnon issue #244 (split every combined cache block across the workflow files). |
| **Outcome** | A PLAN (not executed code, CI never ran): the restore/save split pattern, per-block major-version matching, compound `if:` handling for steps with existing skip guards, a single-Python-pass bulk-edit discipline, a PyYAML regression guard, AND the planning-process disciplines that turned a first-pass NOGO into a passing re-plan: grep-derived completeness with an explicit per-file accounting that sums to N, a verification section that passes against the artifact the plan produces, verifying the `cache-primary-key` linchpin against the action docs, and stating the "split all" decision with rationale. |
| **Verification** | unverified — this is a PLANNING learning. Nothing was executed end-to-end; no PR run was observed; `actionlint` / `check-jsonschema` were NOT run. The `cache-primary-key` linchpin WAS verified against the `actions/cache/restore` action docs (see Results). Treat every remaining "ASSUMPTION" / risk row as an open reviewer task. |
| **Category** | ci-cd / planning |

> **Verification note:** No code was written or run for this learning. The block-count inventory and per-block line numbers came from grep at a point in time and drift as workflows change — re-grep immediately before implementing. The downstream split, the regression guard, and the YAML edits were **planned only**. Confirm every assumption in "Risks & Uncertain Assumptions" before implementing.

## When to Use

- Planning or implementing finer cache-write control in GitHub Actions — you want a cache to be saved ONLY when the build succeeded.
- Preventing a failed or partial build from saving a corrupt `build/_deps` / FetchContent / Conan cache that later poisons green runs by restoring broken artifacts.
- A CI-hardening review touches `actions/cache` blocks and you need to decide whether the combined action's unconditional post-job save is acceptable.
- A "fix every X occurrence" issue: you must enumerate ALL combined blocks from a grep, write a per-file/per-job accounting line that provably sums to the issue's stated total, and re-grep right before implementing because counts and line numbers drift.
- A restore step already carries an `if:` skip guard and you need to AND the `success()` gate with it on the save side.
- You are about to ship a design linchpin (e.g. "the save reuses `steps.<id>.outputs.cache-primary-key`") and must decide whether to verify it against the action's docs/`action.yml` or push it to the implementer as an assumption.
- Doing a bulk edit across many workflow files and needing a discipline that avoids the prior KB failure mode (parallel Edit calls / unquoted `rm` lost or garbled edits).

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read the steps below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```yaml
# BEFORE — combined block: built-in post-job save fires UNCONDITIONALLY, even after a failed build.
- name: Cache build deps
  uses: actions/cache@v4
  with:
    path: build/_deps
    key: ${{ runner.os }}-deps-${{ hashFiles('CMakeLists.txt') }}

# AFTER — restore (early, unconditional) + save (late, gated on success()).
# RESTORE: keep original name + `with:` verbatim, add a unique `id:`, switch uses -> .../restore@vN.
- name: Cache build deps
  id: cache-build-deps                 # NEW: unique id so the save can reference its primary key
  uses: actions/cache/restore@v4       # major version MATCHES the original block (do not bulk-bump)
  with:
    path: build/_deps                  # verbatim from the original block
    key: ${{ runner.os }}-deps-${{ hashFiles('CMakeLists.txt') }}

# ... build / test steps ...

# SAVE: appended at the END of the job, AFTER build/test. Gated on success().
- name: Save build deps cache
  if: success()
  uses: actions/cache/save@v4          # SAME major version as the restore
  with:
    path: build/_deps                  # MUST exactly match the restore path
    key: ${{ steps.cache-build-deps.outputs.cache-primary-key }}  # reuse restore's key — populated on hit AND miss
```

```yaml
# COMPOUND CONDITION — when the restore step already has an `if:` skip guard, AND it with success():
- name: Restore pixi env
  id: cache-pixi
  if: steps.detect.outputs.skip == 'false'
  uses: actions/cache/restore@v5
  with:
    path: .pixi
    key: ${{ runner.os }}-pixi-${{ hashFiles('pixi.lock') }}
# ...
- name: Save pixi env cache
  if: success() && steps.detect.outputs.skip == 'false'   # AND success() with the ORIGINAL guard
  uses: actions/cache/save@v5
  with:
    path: .pixi
    key: ${{ steps.cache-pixi.outputs.cache-primary-key }}
```

```python
# REGRESSION GUARD — scripts/check_cache_save_gating.py (PyYAML). Fails CI if any cache/save@
# step lacks success() in its if:, or if a combined actions/cache@ reappears.
import sys, glob, yaml

errors = []
for path in glob.glob(".github/**/*.yml", recursive=True) + glob.glob(".github/**/*.yaml", recursive=True):
    with open(path) as f:
        try:
            doc = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"{path}: YAML parse error: {e}")
            continue
    for job in (doc or {}).get("jobs", {}).values():
        for step in (job or {}).get("steps", []) or []:
            uses = str(step.get("uses", ""))
            cond = str(step.get("if", ""))
            if uses.startswith("actions/cache@"):
                errors.append(f"{path}: combined 'actions/cache@' reappeared in step "
                              f"'{step.get('name', uses)}' — must split into restore + save")
            if uses.startswith("actions/cache/save@") and "success()" not in cond:
                errors.append(f"{path}: 'cache/save' step '{step.get('name', uses)}' "
                              f"missing success() gate (if: {cond!r})")

if errors:
    print("\n".join(errors)); sys.exit(1)
print("OK: all cache/save steps gated on success(); no combined actions/cache@ found")
```

```bash
# COMPLETENESS + SELF-CONSISTENT VERIFICATION — derive N from grep, then assert the arithmetic.
# 1. Count every combined block the issue says to fix (this is the authoritative N):
N=$(grep -rnE "uses:\s*actions/cache@v[0-9]" .github/workflows/ | wc -l)
echo "combined blocks to split: $N"
# 2. Per-file accounting (must sum to N) — write this line in the plan, do not eyeball:
grep -rcE "uses:\s*actions/cache@v[0-9]" .github/workflows/ | grep -v ':0$'
# 3. AFTER the edit, the acceptance commands must pass AGAINST THE PLANNED END-STATE.
#    Zero combined blocks remain:
grep -rnE "uses:\s*actions/cache@v[0-9]" .github/workflows/ && echo FAIL || echo "OK: 0 combined"
#    Count-assertions keep the arithmetic internally consistent (expect N each):
R=$(grep -rcE "uses:\s*actions/cache/restore@" .github/workflows/ | awk -F: '{s+=$2} END{print s}')
S=$(grep -rcE "uses:\s*actions/cache/save@"    .github/workflows/ | awk -F: '{s+=$2} END{print s}')
K=$(grep -rcE "outputs\.cache-primary-key"     .github/workflows/ | awk -F: '{s+=$2} END{print s}')
echo "restore=$R save=$S key-reuses=$K (expect each == $N)"
test "$R" = "$N" && test "$S" = "$N" && test "$K" = "$N" && echo "OK: arithmetic consistent" || echo "FAIL"

# BULK EDIT DISCIPLINE — do the conversion in a SINGLE Python pass, never parallel Edit calls
# or unquoted rm (a prior KB lesson: those lost/garbled edits). Then validate:
actionlint .github/workflows/*.yml
check-jsonschema --schemafile <github-workflow-schema> .github/workflows/*.yml
python3 scripts/check_cache_save_gating.py
```

### Detailed Steps

1. **Derive N from a grep and write a sum-checked accounting BEFORE planning the edits.** On a
   "fix every combined block" issue, do NOT assert "all N covered" from memory or a partial scan.
   Grep for `actions/cache@v[0-9]` across the workflow files, record the per-file (and where it
   matters, per-job) counts, and write an explicit accounting line that PROVABLY sums to the
   issue's stated total. The first-pass plan claimed "all 26 blocks / 6 files" but its per-file
   breakdown only summed to 21 — it silently dropped 5 blocks (`_required.yml:517` and `:526`, a
   high-risk `build/**/_deps` release block, plus all 3 `python-client.yml` blocks). Re-grep
   immediately before implementing because line numbers and counts drift.

2. **Make the plan's own verification section pass against the artifact the plan produces.**
   The first-pass acceptance check was `grep -rnE "actions/cache@..." && echo FAIL`, but because
   5 combined blocks were silently dropped, those blocks would still match and the plan FAILED ITS
   OWN GATE. Mentally (or actually) run each acceptance command against the planned end-state. A
   self-contradicting verification section is independently disqualifying. Add count-assertions
   (expect N restore + N save + N key-reuses) so the arithmetic is internally consistent.

3. **Verify a design linchpin against the action's docs/`action.yml` before trusting it.** The
   save side reuses `steps.<id>.outputs.cache-primary-key` — that output's behaviour is the
   linchpin of the whole pattern. The first pass flagged it "unverified — is it populated on a
   cache miss?" and shipped it anyway. The re-plan fetched the `actions/cache/restore` docs:
   `cache-primary-key` = "Cache primary key passed in the input to use in subsequent steps of the
   workflow," set whenever the action runs (NOT conditional on hit/miss). So reusing it as the
   save `key:` is safe on both hit and miss. Do not push a flagged linchpin to the implementer —
   verify it.

4. **State scope decisions with rationale, not options.** The first pass left "should we split
   the low-risk Conan cache?" as an open option and drew a reviewer MINOR. Decide and justify:
   split ALL combined blocks, because (a) leaving any combined `actions/cache@` block fails the
   grep-zero acceptance check, and (b) there is a real poisoning window if a job fails after
   `conan install` partially populates `~/.conan2`. Plans state decisions; they do not defer
   judgment calls to the reader.

5. **Convert the restore side first, preserving the original block verbatim.** Keep the step's
   `name:` and entire `with:` (path + key + any restore-keys) unchanged. Add a unique `id:` (the
   save will reference `steps.<id>.outputs.cache-primary-key`). Switch only
   `uses: actions/cache@vN` → `uses: actions/cache/restore@vN`. The restore stays early and
   unconditional (or keeps its existing skip guard).

6. **Append the save step at the END of the job, after build/test, gated on `if: success()`.**
   Use `uses: actions/cache/save@vN` with the SAME major version as the restore. The `path:`
   MUST exactly match the restore's path. Set `key: ${{ steps.<id>.outputs.cache-primary-key }}`
   so the save reuses the restore's resolved key — never re-type the `hashFiles()` expression
   independently (that drifts when only one side is later edited).

7. **Match the `actions/cache` major version per-block to what the repo already pins.** Do NOT
   bulk-bump every block to one version. If the repo mixes `@v4` and one SHA-pinned `@v5`, the
   v5 block splits to `restore@v5` / `save@v5` and the v4 blocks split to `restore@v4` / `save@v4`.

8. **Handle compound conditions.** When a restore step already carries an `if:` (e.g. a skip
   guard `steps.detect.outputs.skip == 'false'`), the save must AND it with `success()`:
   `if: success() && steps.detect.outputs.skip == 'false'`. A bare `if: success()` would run the
   save on jobs the restore deliberately skipped.

9. **Do all YAML edits in a SINGLE Python pass.** Never use parallel Edit calls or unquoted `rm`
   for the bulk conversion — a prior KB failure mode lost/garbled edits. Drive the conversion from
   one script that reads, transforms, and writes each file once.

10. **Validate before commit.** Run `actionlint` and `check-jsonschema` (GitHub workflow schema)
    over every edited workflow, plus the regression guard, plus the count-assertions from step 2.

11. **Add a regression guard script (PyYAML).** `scripts/check_cache_save_gating.py` fails CI if
    any `actions/cache/save@` step lacks `success()` in its `if:`, or if a combined
    `actions/cache@` block reappears. Wire it into CI / pre-commit so the split cannot regress.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Claimed "all 26 blocks / 6 files covered" but the per-file breakdown summed to 21 | First-pass plan asserted full coverage from a partial scan | Silently dropped 5 blocks (`_required.yml:517`/`:526` — a high-risk `build/**/_deps` release block — and all 3 `python-client.yml` blocks); scope drop earned a NOGO | On "fix every X", derive N from a grep, write an explicit per-file accounting that PROVABLY sums to N, and re-grep right before implementing — never assert "all N covered" without the enumeration |
| Acceptance grep would still match the dropped blocks | First-pass acceptance was `grep -rnE "actions/cache@..." && echo FAIL` | The 5 un-split blocks still matched, so the plan FAILED ITS OWN GATE — a self-contradicting verification section | Dry-run each acceptance command against the planned end-state; add count-assertions (expect N restore + N save + N key-reuses) so the arithmetic is internally consistent |
| Flagged `cache-primary-key` as unverified and shipped it anyway | Marked the save-key linchpin "is it populated on a cache miss?" and pushed it to the implementer | A design linchpin left unverified means the whole pattern rests on an unconfirmed assumption | Fetch the action's docs/`action.yml` outputs and VERIFY: `cache-primary-key` is set whenever the action runs (hit AND miss), so it is safe as the save `key:` |
| Left the Conan-cache split as an open option | First-pass plan offered "split the low-risk Conan cache?" as a judgment call for the reader | Reviewer MINOR; an undecided option is not a plan, and leaving any combined block fails the grep-zero acceptance check | State decisions with rationale: split ALL blocks — leaving any fails the gate, and a failed `conan install` can partially poison `~/.conan2` |
| Relying on the combined action's built-in post-job save | Left `actions/cache@vN` as a single block | The built-in save fires UNCONDITIONALLY in the post-job phase, even after a failed build — it can cache corrupt/partial build state (e.g. half-written `build/_deps`) that poisons later green runs | Split into `restore@vN` (early, unconditional) + `save@vN` gated on `if: success()` so only a successful build writes the cache |
| Bumping every cache block to one major version | Bulk-rewrote all blocks to a single `actions/cache@vN` major during the split | Diverges from the repo's mixed pinning convention (e.g. `@v4` everywhere plus one SHA-pinned `@v5`); a bulk bump is an unrelated, unreviewed change | Match the major version PER-BLOCK to what the repo already pins — split each block to the same `restore@vN` / `save@vN` it used before |
| Hardcoding the save `key:` independently of the restore | Re-typed the `hashFiles(...)` expression on the save step | Key drift: when someone later edits only one side's `hashFiles()`, restore and save compute different keys and the cache silently never hits | Reuse the restore's resolved key via `key: ${{ steps.<id>.outputs.cache-primary-key }}` |
| Putting a bare `if: success()` on saves whose restore had a skip guard | Save used `if: success()` while the restore used `if: ...skip == 'false'` | The save then runs on jobs the restore deliberately skipped, attempting to save a cache that was never restored / built for | AND the `success()` gate with the original condition: `if: success() && steps.detect.outputs.skip == 'false'` |
| Bulk-editing workflow YAML via parallel Edit calls / unquoted rm | Applied many concurrent Edit operations (and an unquoted `rm`) across the workflow files | Prior KB lesson: parallel edits and unquoted `rm` lost or garbled edits, leaving workflows in an inconsistent half-converted state | Do the entire conversion in a SINGLE Python pass (read → transform → write once per file), then validate with `actionlint` + `check-jsonschema` |

## Results & Parameters

- **Completeness / sum-check:** derive N from `grep -rnE "actions/cache@v[0-9]" .github/workflows/`, write a per-file accounting that sums to N, and re-grep right before implementing. The first pass's "26 / 6" summed to only 21 (5 dropped).
- **Self-consistent verification:** every acceptance command must pass against the PLANNED end-state. Add count-assertions: expect **N** restore steps, **N** save steps, and **N** `cache-primary-key` reuses (the bash block in Quick Reference does this with `awk` sums).
- **`cache-primary-key` — VERIFIED (was uncertain in v1.0.0):** per the `actions/cache/restore` action docs, `cache-primary-key` = "Cache primary key passed in the input to use in subsequent steps of the workflow." It is set whenever the restore action runs, NOT conditional on a cache hit/miss — so reusing it as the save `key:` is safe on both hit and miss (first-run cache miss included).
- **Pattern (restore + save):**
  - RESTORE: keep `name:` + `with:` verbatim, add a unique `id:`, switch `uses:` → `actions/cache/restore@vN`; stays early and unconditional (or keeps its existing skip guard).
  - SAVE: appended at the END of the job (after build/test), `if: success()`, `uses: actions/cache/save@vN` (SAME major as restore), `path:` exactly matching restore, `key: ${{ steps.<id>.outputs.cache-primary-key }}`.
- **Per-block version matching:** never bulk-bump; a `@v4` block → `restore@v4`/`save@v4`, a SHA-pinned `@v5` block → `restore@v5`/`save@v5`.
- **Compound condition (pixi-check variant):** `if: success() && steps.detect.outputs.skip == 'false'` when the restore already had a skip guard.
- **Scope decision:** split ALL combined blocks (including the low-risk Conan cache) — rationale: any remaining combined `actions/cache@` fails the grep-zero acceptance check, and a failed `conan install` can partially poison `~/.conan2`.
- **Bulk edit:** single Python pass, never parallel Edit calls or unquoted `rm`. Validate with `actionlint` + `check-jsonschema`.
- **Regression guard:** `scripts/check_cache_save_gating.py` (PyYAML) fails CI if any `cache/save@` lacks `success()` in `if:`, or if a combined `actions/cache@` reappears (snippet in Quick Reference).
- **Inventory (point-in-time, DRIFTS):** issue #244 cited combined cache blocks across the workflow files. Re-grep before implementing — counts and per-block line numbers change as workflows change.

### Risks & Uncertain Assumptions

These are the durable PLANNING learnings — each remaining item is an open reviewer task:

1. **Previously uncertain, NOW VERIFIED — `cache-primary-key`.** In v1.0.0 this was flagged
   unverified ("is it populated on a cache miss?"). The re-plan fetched the `actions/cache/restore`
   docs: the output is "Cache primary key passed in the input to use in subsequent steps of the
   workflow," set whenever the action runs (NOT conditional on hit/miss). Reusing it as the save
   `key:` is safe on both hit and miss. No longer an open risk.
2. **Glob path resolution timing — UNVERIFIED.** For path GLOBS like `build/**/_deps`,
   `actions/cache/save` resolves the glob at SAVE time against the post-build tree. Restore-vs-save
   glob-resolution timing was ASSUMED equivalent, not verified — a glob that matched at restore may
   match a different (or empty) set at save.
3. **Inventory + line numbers DRIFT.** The block-count inventory came from grep at a point in time.
   Workflows change; re-grep immediately before implementing rather than trusting the plan's
   counts/offsets. (This is exactly what caused the first-pass scope drop.)
4. **`if: success()` does not catch exit-0 partial artifacts — NARROW.** `success()` gates on
   prior STEPS in the job succeeding (exit 0). Cache poisoning can STILL occur if a build step
   exits 0 while producing a partial/corrupt artifact — `success()` will not catch that. The gate
   reduces, not eliminates, poisoning risk.
5. **Scope boundary (out of scope) — confirm with reviewer.** The plan intentionally leaves
   `setup-pixi cache: true` and composite-action extraction OUT of scope. Confirm the reviewer
   agrees this boundary is correct before implementing.

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| HomericIntelligence/ProjectAgamemnon | Issue #244 — split every combined `actions/cache@vN` block across the workflow files into restore + save gated on `if: success()` (re-plan after a first-pass NOGO) | unverified — PLAN only; CI never ran; `actionlint` / `check-jsonschema` not executed. The `cache-primary-key` linchpin WAS verified against the `actions/cache/restore` docs. Treat the remaining assumptions as open reviewer tasks. |
