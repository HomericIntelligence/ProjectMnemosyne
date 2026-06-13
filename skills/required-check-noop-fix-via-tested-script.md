---
name: required-check-noop-fix-via-tested-script
description: "Use when: (1) fixing a no-op / decorative required GitHub Actions check that computes a value and echoes it but never branches on it (only `exit 1` in a dead branch), (2) reusing an already-existing tested script in CI instead of reimplementing logic in workflow bash — especially under `pip install -e . --no-deps`, where a script that imports the project package can hit a latent ModuleNotFoundError, (3) deciding whether to DELETE a redundant required check (query the ruleset first — a pinned context cannot be removed from a code PR), or (4) an audit issue cites workflow line numbers you are about to edit. Headline: trace the full import chain and verify in the env that SHIPS (clean venv), not the pixi env."
category: ci-cd
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: unverified
history: skills/required-check-noop-fix-via-tested-script.history
tags:
  - ci-cd
  - github-actions
  - required-status-checks
  - no-op-gate
  - exit-code-discipline
  - dry
  - reuse-tested-script
  - ci-invocation-path
  - no-deps-install
  - stale-audit-line-numbers
  - planning-quality
  - branch-protection
  - module-not-found-error
  - import-chain-trace
  - clean-venv-verification
  - pinned-required-context
  - nogo-revision
  - yagni
---

# Fixing a No-Op Required CI Check by Delegating to a Tested Script

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Plan a defect fix where a *required* GitHub Actions check (`deps/version-sync`) computes a value (`DYNAMIC`), echoes it, but never branches on it — its only `exit 1` lives in a dead `if [ -f VERSION ]` branch (no VERSION file exists), so the gate asserts nothing yet blocks merges as a required context |
| **Chosen fix (revised)** | Make the job invoke the existing tested checker (`scripts/check_version_single_source.py`) — but with **`pip install -e "."` (NO `--no-deps`)**, **restore the dropped `pixi lock --check` leg** so all three named files are asserted, and **delete the dead `if [ -f VERSION ]` branch** (YAGNI). KEEP the gate (do not delete the job): its context is PINNED in the org ruleset. |
| **Headline finding (NOGO-confirmed)** | The v1.0.0 plan's "uncertain risk" was a REAL latent `ModuleNotFoundError`: the enforcement line imports `hephaestus.utils.helpers`, which does `from packaging.requirements import ...` at module top; `packaging` is a DECLARED CORE DEP (`pyproject.toml:29`) that `--no-deps` skips. A GO plan resolves the risk; it does not merely flag it. |
| **Source** | Implementation-planning session for HomericIntelligence/ProjectHephaestus issue #1181; v1.0.0 NOGO'd at Grade D, this v1.1.0 captures the GO-quality revision (plan only — never executed) |
| **Verification** | unverified (CI never confirmed; the revised verification mirrors CI in a clean venv but was not run end-to-end) |

## When to Use

- A required status-check context is a job that *runs to completion* (so it always posts `success`) but never actually asserts the invariant it claims to guard — the computed value is echoed, never compared, and the only failing exit is in a dead/unreachable branch.
- You intend to fix it by **delegating to an existing tested script** rather than re-encoding the invariant in workflow bash (DRY — avoid re-introducing bugs the script already fixed).
- You must weigh **fix-in-place vs remove-and-de-list**: the gate may be redundant with a pre-commit hook that already enforces the same invariant as a separate required lint step.
- You are about to edit a workflow at line numbers an audit issue cited — re-derive them first.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — this is an implementation PLAN that was never executed. The headline risk (the `--no-deps` import surface) is reasoned, not run.

### Quick Reference

```bash
# 0. NEVER trust audit-cited line numbers — re-derive on disk first.
#    Issue cited :770-820, :812, :814; ground truth was :806, :831-838, :848, :850.
grep -nE "DYNAMIC|exit 1|if \[ -f VERSION" .github/workflows/_required.yml

# 1. TRACE THE FULL IMPORT CHAIN before asserting install requirements.
#    script → scripts_lib → hephaestus.utils.helpers → `from packaging.requirements import`
#    `packaging` is a DECLARED CORE DEP (pyproject.toml:29) → --no-deps OMITS it.
#    => the CI step MUST drop --no-deps.  "Only needs the checkout" is FALSE.
grep -nE "^import|^from" scripts/check_version_single_source.py hephaestus/utils/helpers.py

# 2. THE HEADLINE VERIFICATION: a green check in the wrong env is a FALSE GO.
#    Mirror CI EXACTLY in a CLEAN venv — NOT the project's managed pixi env.
python3 -m venv /tmp/cienv && . /tmp/cienv/bin/activate
pip install -e "."                                 # NO --no-deps (packaging must install)
python scripts/check_version_single_source.py      # bare python, NOT `pixi run python3`
echo "exit=$?"                                      # must be 0 on a clean tree

# 3. Prove the gate now BITES (synthetic-violation proof):
#    inject a static [project].version  -> expect exit 1
#    append a junk dep to pixi.toml     -> `pixi lock --check` exits non-zero

# 4. Restore any dropped contract leg. DoD names THREE files; the checker omits
#    pixi.lock — add `pixi lock --check` so all three are asserted.
grep -nE "deps/version-sync|pyproject|pixi.toml|pixi.lock" docs/DEFINITION_OF_DONE.md

# 5. Is the context PINNED in branch protection? If yes, DO NOT delete the job —
#    de-listing is an admin ruleset change, out of scope for a code PR. Make the
#    pinned gate assert its named contract instead.
gh api repos/HomericIntelligence/ProjectHephaestus/rulesets --jq '.[].id' \
  | xargs -I{} gh api repos/HomericIntelligence/ProjectHephaestus/rulesets/{} \
      --jq '.rules[]?|select(.type=="required_status_checks")|.parameters.required_status_checks[].context' \
  | grep -i 'deps/version-sync'
```

### Detailed Steps and the Durable Insights (v1.1.0 — post-NOGO)

> The v1.0.0 plan *flagged* insights 2–5 below as "uncertain risks" and shipped
> anyway. The reviewer NOGO'd at Grade D precisely because a GO plan must
> **resolve** these, not merely note them. The resolutions are the durable value.

1. **Stale audit line numbers are the norm, not the exception.** The issue cited
   `_required.yml:770-820`, `:812`, `:814`; ground-truth on disk was `:806`,
   `:831-838`, `:848`, `:850` — off by ~40 lines. ALWAYS re-derive line numbers
   on disk (`grep -n`) before planning edits; never copy audit-issue line cites
   into the plan as if they are current.

2. **HEADLINE — `--no-deps` + a script that imports the package = latent
   `ModuleNotFoundError`.** The enforcement line
   `python scripts/check_version_single_source.py` imports
   `hephaestus.utils.helpers`, which does `from packaging.requirements import ...`
   at MODULE TOP. `packaging` is a **declared CORE dependency**
   (`pyproject.toml:29`) that `pip install -e "." --no-deps` explicitly SKIPS.
   The v1.0.0 plan asserted "only needs the repo checkout" — FALSE: the script's
   transitive import chain (`script → scripts_lib → utils.helpers → packaging`)
   reaches a non-stdlib dep. **Resolution: drop `--no-deps` (use
   `pip install -e "."`).** Rule: when a CI step invokes ANY script that imports
   the project package (not just stdlib), the install must include deps OR you
   must trace the FULL import chain and prove every transitive import is
   stdlib-only. Reading the top of the script is not enough; follow the chain.

3. **HEADLINE — verifying in the full pixi env proves nothing about a CI step
   that uses bare `pip install -e .` + bare `python`.** The v1.0.0 verification
   ran `pixi run --environment default python3 …`, which has ALL deps. The
   shipping CI path was `--no-deps` + bare `python` — a DIFFERENT environment
   than the one that ships. A green check in the wrong env is a FALSE GO.
   **Resolution: verification must reproduce the EXACT install + interpreter of
   the CI step** — for a `--no-deps`/bare-`python` job, verify in a clean
   `python3 -m venv` with the identical `pip install` line, NOT in the project's
   managed env. (After resolution #2 drops `--no-deps`, the mirror is
   `pip install -e "."` in a clean venv.)

4. **A required check named for an N-part contract that asserts fewer parts is a
   silent scope narrowing — AND removal is not free when the context is pinned.**
   Two coupled sub-lessons:
   - **(a) Restore the dropped contract leg.** `docs/DEFINITION_OF_DONE.md:28`
     names a THREE-file contract (pyproject → pixi.toml → pixi.lock). The reused
     checker covers only pyproject + pixi.toml (never reads pixi.lock). The
     v1.0.0 plan silently dropped the pixi.lock leg. When reusing a tested helper
     to satisfy a named contract, diff the helper's actual coverage against the
     documented contract and restore any missing leg — here, **add
     `pixi lock --check`** — rather than quietly narrowing scope.
   - **(b) Don't delete a PINNED required context.** The KISS/DRY ideal was to
     DELETE the redundant job (its invariant is already enforced by the `lint`
     pre-commit hook and by `pixi-check`'s `pixi install --locked`). BUT
     `gh api repos/<owner>/<repo>/rulesets/<id>` showed `deps/version-sync` is a
     PINNED required status check in the active org ruleset. Deleting the job
     without de-listing the context BLOCKS every PR forever (the
     `ci-driver-blocked-required-context-drift` failure mode). Ruleset mutation
     is an admin API change, out of scope for a code PR. **Resolution: before
     recommending "delete the redundant required check," query the
     branch-protection/ruleset required-status-checks list; if the context is
     pinned, removal bricks the merge queue — instead make the pinned gate assert
     its named contract (justified defense-in-depth) and state the trade-off.**

5. **Delete known-dead enforcement branches; don't preserve them speculatively
   (YAGNI).** The v1.0.0 plan retained the dead `if [ -f VERSION ]` branch "in
   case a VERSION file is ever added" — reviewer flagged it minor. A dead branch
   with no roadmap should be DELETED; the live checker provides the real exit-1
   path. Speculative retention is a YAGNI violation, not safety.

### NOGO → revision — what WORKED in the GO-quality revision

The Grade-D NOGO converged to GO by doing exactly these four things — they are
the transferable recipe for any "fix a no-op required gate via a tested script":

1. **Trace the full import chain on disk before asserting install requirements**
   (`script → scripts_lib → utils.helpers → packaging`) — this is what exposed
   the `--no-deps` `ModuleNotFoundError` that "reading the script" had missed.
2. **Query the active ruleset's required-status-checks via
   `gh api .../rulesets/<id>`** to learn the context is PINNED — this reframed the
   whole fix from "maybe delete the redundant gate" to "make the pinned gate real."
3. **Clean-venv CI-mirrored verification** (`python3 -m venv`, the identical
   `pip install` line, bare `python`) **plus synthetic-violation proof** (inject a
   static `[project].version` → expect exit 1; append a junk dep to `pixi.toml` →
   `pixi lock --check` non-zero). Verify the env that SHIPS, then prove the gate
   bites.
4. **Restore the dropped contract leg (`pixi lock --check`)** so the gate asserts
   all three named files (pyproject + pixi.toml + pixi.lock), matching the DoD.

### What the Reviewer Should Focus On (priority order)

1. Did the install DROP `--no-deps` so the `packaging` import resolves (insight #2)?
2. Was verification run in a clean venv mirroring CI, not the pixi env (insight #3)?
3. Does the gate now BITE on a synthetic violation (synthetic-violation proof)?
4. Was the dropped `pixi lock --check` leg restored so all three DoD files are asserted (insight #4a)?
5. Was the pinned-context ruleset checked before any "delete the job" suggestion (insight #4b)?
6. Was the dead `if [ -f VERSION ]` branch deleted, not preserved (insight #5)?
7. Were edited line numbers re-derived on disk, not copied from the stale audit (insight #1)?

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Reimplement invariant in workflow bash | Encode the single-source check directly as `grep`/`bash` logic inside `deps/version-sync` | Would re-introduce the regex false-PASS bug already fixed in #435; duplicates logic the tested script owns | DRY: delegate to the existing tested script; never re-encode an invariant that a tested checker already implements |
| Trust audit-cited line numbers | Plan edits against issue-cited `_required.yml:770-820`, `:812`, `:814` | Lines were stale by ~40 lines; real positions were `:806`, `:831-838`, `:848`, `:850` | Re-derive line numbers on disk with `grep -n` before planning any workflow edit |
| Local `pixi run` as proof of CI correctness | Verify with `pixi run --environment default python3 scripts/check_version_single_source.py` | The CI job uses `pip install -e . --no-deps` + bare `python` (no pixi env) — pixi has the full deps, so it cannot surface a `--no-deps` ImportError | Verification must mirror the real CI invocation path (venv + `--no-deps` + bare `python`), not the convenient local one |
| Assume "only needs the repo checkout" | Conclude from *reading* the script that it has no runtime deps beyond stdlib + repo | `get_repo_root` / transitive imports may pull a dep `--no-deps` omits; reading code is not running it | The #1 uncertain assumption in any "delegate to existing script" plan is whether it imports cleanly in CI's minimal env — RUN it, don't read it |
| Silently narrow scope to match the chosen tool | Have `deps/version-sync` cover only what `check_version_single_source.py` checks | DoD documents pyproject + pixi.toml + `pixi.lock`; checker omits `pixi.lock` | Compare the reused tool's coverage against the documented gate intent (DoD) before adopting it; flag any narrowing explicitly |
| Ship `pip install -e "." --no-deps` then invoke the importing script | v1.0.0 kept `--no-deps` and asserted "only needs the repo checkout" | The script imports `hephaestus.utils.helpers`, which does `from packaging.requirements import …` at module top; `packaging` is a DECLARED CORE DEP (`pyproject.toml:29`) that `--no-deps` SKIPS → latent `ModuleNotFoundError` on every PR | When a CI step invokes a script that imports the project package, the install MUST include deps (drop `--no-deps`), OR trace the FULL import chain (`script → scripts_lib → utils.helpers → packaging`) and prove every transitive import is stdlib-only |
| Verify in the full pixi env to "prove" the CI step works | v1.0.0 ran `pixi run --environment default python3 …` (has all deps) to validate a job that ships `--no-deps` + bare `python` | The verification env had `packaging`; the shipping env did not — the test ran a DIFFERENT environment than the one that ships, so it could never surface the ImportError. A green check in the wrong env is a FALSE GO | Verification must reproduce the EXACT install + interpreter of the CI step: a clean `python3 -m venv` with the identical `pip install` line and bare `python` — never the project's managed pixi env |
| Recommend deleting the redundant required job (KISS/DRY) | v1.0.0 considered removing `deps/version-sync` since the invariant is already covered by the `lint` pre-commit hook + `pixi-check --locked` | `gh api .../rulesets/<id>` showed `deps/version-sync` is a PINNED required status check; deleting the job without de-listing the context BLOCKS every PR forever (`ci-driver-blocked-required-context-drift`). De-listing is an admin ruleset change, out of scope for a code PR | Before recommending "delete the redundant required check," query the ruleset's required-status-checks list; if the context is pinned, make the pinned gate assert its named contract (justified defense-in-depth) and state the trade-off — do NOT delete |
| Preserve the dead `if [ -f VERSION ]` branch speculatively | v1.0.0 kept the unreachable branch "in case a VERSION file is ever added" | No VERSION file exists and none is on the roadmap; the live checker already provides the real exit-1 path → the branch is pure dead code (YAGNI) | Delete known-dead enforcement branches; speculative retention is a YAGNI violation, not safety |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Repo / issue** | HomericIntelligence/ProjectHephaestus #1181 |
| **Defective gate** | `deps/version-sync` (required status check) in `.github/workflows/_required.yml` |
| **Defect class** | No-op gate: computes `DYNAMIC`, echoes it, never branches; only `exit 1` in dead `if [ -f VERSION ]` branch (no VERSION file) |
| **Chosen fix (v1.0.0 → revised v1.1.0)** | Invoke `scripts/check_version_single_source.py` from the job — but **drop `--no-deps`** (so `packaging` installs), **restore `pixi lock --check`** (third DoD leg), **delete the dead `if [ -f VERSION ]` branch**, and **KEEP the job** (its context is pinned) |
| **CI runtime** | `actions/setup-python` py3.12; **`pip install -e "."`** (revised — was `--no-deps`); bare `python scripts/...` |
| **Latent defect found** | `--no-deps` skips `packaging` (core dep, `pyproject.toml:29`) that `hephaestus.utils.helpers` imports at module top → `ModuleNotFoundError` on every PR |
| **Redundancy** | Same invariant also enforced by the `lint` pre-commit hook and `pixi-check`'s `pixi install --locked` — but the gate is kept as justified defense-in-depth because its context is pinned |
| **Required-context references** | `.github/README.md:47`, `docs/DEFINITION_OF_DONE.md:28`; context PINNED in active org ruleset (verified via `gh api .../rulesets/<id>`) — must NOT be deleted from a code PR |
| **DoD scope** | pyproject.toml + pixi.toml + pixi.lock; revised fix asserts all three (checker covers pyproject + pixi.toml; `pixi lock --check` covers pixi.lock) |
| **Reviewer verdict** | v1.0.0 NOGO Grade D → v1.1.0 revised to GO-quality (resolutions above) |
| **Verification status** | unverified — plan only; CI never confirmed. Revised verification mirrors CI in a clean venv but was not run end-to-end |

### Outcome

This is a PLANNING-QUALITY learning whose value is the NOGO→GO delta: the v1.0.0
plan *flagged* the install/scope risks but shipped anyway and was NOGO'd at Grade
D. The transferable rules for any "fix a no-op required CI gate by delegating to
an existing tested script" task:

1. **Trace the full import chain on disk** (`script → … → packaging`) before
   asserting "no deps needed" — and prefer dropping `--no-deps` over claiming
   every transitive import is stdlib-only.
2. **Verify in the env that SHIPS** — a clean venv with the identical `pip
   install` line and bare `python`, never the project's managed pixi env. A green
   check in the wrong env is a false GO.
3. **Query the ruleset before suggesting "delete the redundant gate"** — a pinned
   required context cannot be removed from a code PR without bricking the merge
   queue; make it assert its named contract instead.
4. **Restore any dropped contract leg** so the gate asserts every file the DoD
   names; **delete dead branches** rather than preserving them speculatively.
