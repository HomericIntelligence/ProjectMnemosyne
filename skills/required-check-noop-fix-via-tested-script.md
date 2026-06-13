---
name: required-check-noop-fix-via-tested-script
description: "Use when: (1) planning a fix for a required GitHub Actions check that computes a value and echoes it but never branches on it (a no-op gate whose only `exit 1` is in a dead branch), (2) the chosen fix is to delegate enforcement to an already-existing tested script instead of reimplementing logic in workflow bash, (3) you must decide whether to fix-in-place vs remove-and-de-list a redundant required context, or (4) an audit issue cites workflow line numbers you are about to edit."
category: ci-cd
date: 2026-06-12
version: "1.0.0"
user-invocable: false
verification: unverified
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
---

# Fixing a No-Op Required CI Check by Delegating to a Tested Script

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-12 |
| **Objective** | Plan a defect fix where a *required* GitHub Actions check (`deps/version-sync`) computes a value (`DYNAMIC`), echoes it, but never branches on it — its only `exit 1` lives in a dead `if [ -f VERSION ]` branch (no VERSION file exists), so the gate asserts nothing yet blocks merges as a required context |
| **Chosen fix** | Make the job invoke an already-existing, already-tested checker (`scripts/check_version_single_source.py`) so enforcement reuses tested logic (DRY) instead of reimplementing it in bash |
| **Headline risk** | The reused script must run under the CI job's `pip install -e "." --no-deps` + bare-`python` invocation — NOT the local `pixi run` path. This was reasoned-from-reading, not run-and-verified. This is the #1 reviewer risk. |
| **Source** | Implementation-planning session for HomericIntelligence/ProjectHephaestus issue #1181 (plan only — never executed) |
| **Verification** | unverified |

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

# 1. THE HEADLINE VERIFICATION the reviewer must demand:
#    mirror CI EXACTLY (no pixi). The job uses actions/setup-python + bare python.
python3 -m venv /tmp/cienv && . /tmp/cienv/bin/activate
pip install -e "." --no-deps                       # <-- the real failure surface
python scripts/check_version_single_source.py      # bare python, NOT `pixi run python3`
echo "exit=$?"                                      # must be 0 on a clean tree

# 2. Confirm the checker actually FAILS on a violation (prove the gate now bites):
#    e.g. inject a static [project] version, re-run, expect non-zero exit.

# 3. Confirm scope vs the documented intent before narrowing it (see Failed Attempts).
grep -nE "deps/version-sync|pyproject|pixi.toml|pixi.lock" docs/DEFINITION_OF_DONE.md
```

### Detailed Steps and the Five Durable Insights

1. **Stale audit line numbers are the norm, not the exception.** The issue cited
   `_required.yml:770-820`, `:812`, `:814`; ground-truth on disk was `:806`,
   `:831-838`, `:848`, `:850` — off by ~40 lines. ALWAYS re-derive line numbers
   on disk (`grep -n`) before planning edits; never copy audit-issue line cites
   into the plan as if they are current.

2. **Most uncertain assumption — flag it as the #1 reviewer risk: the reused
   script must run under the CI job's `--no-deps` install.** The job does
   `pip install -e "." --no-deps`, then `python scripts/check_version_single_source.py`.
   The checker imports `hephaestus.utils.helpers.get_repo_root` and uses
   `tomllib` (py3.11+, job uses py3.12 — OK) with a `tomli` fallback only on
   <3.11. Risk: if `get_repo_root` or any transitive import pulls a dependency
   that `--no-deps` did not install, the bare `python scripts/...` invocation
   ImportErrors and the "fixed" gate fails on every PR. The plan asserted "only
   needs the repo checkout" — that was reasoned from reading the script, NOT
   verified by running it under a `--no-deps` install. Demand a run.

3. **Verify the reused script's invocation form matches CI's python.** The plan's
   local verification used `pixi run --environment default python3`, but CI uses
   bare `python` from `actions/setup-python` (no pixi, no full dependency
   environment). Local `pixi run` does NOT exercise the real failure surface
   (`pip install -e . --no-deps` then bare `python scripts/...`). The reviewer
   should require a verification command that mirrors CI exactly — venv +
   `--no-deps` + bare `python` — not the pixi path.

4. **"Redundant with pre-commit" is a real, unresolved design tension.** The same
   single-source invariant is already enforced by the `check-version-single-source`
   pre-commit hook, which runs as a *required* lint step. Making `deps/version-sync`
   assert the SAME invariant arguably duplicates enforcement across two required
   gates (DRY tension). The plan chose fix-in-place (don't delete) to preserve the
   required-context name referenced in `.github/README.md:47` and
   `docs/DEFINITION_OF_DONE.md:28`, but did not fully resolve the alternative:
   remove the redundant job and de-list it from branch protection. Reviewer must
   weigh assert-same-invariant-twice vs remove-redundant-gate.

5. **DoD scope mismatch — the fix silently narrows documented scope.**
   `docs/DEFINITION_OF_DONE.md:28` says `deps/version-sync` checks
   "pyproject.toml then pixi.toml then pixi.lock". The reused checker covers
   pyproject + pixi.toml but NOT `pixi.lock`. The plan quietly narrowed scope vs
   the documented intent. Reviewer should confirm whether `pixi.lock` sync is in
   scope; if it is, delegating to this checker alone is insufficient.

### What the Reviewer Should Focus On (priority order)

1. Run the script under `pip install -e . --no-deps` + bare `python` (insight #2/#3) — does it import and exit 0?
2. Does the script return non-zero on an actual violation (does the gate now bite)?
3. Is `pixi.lock` sync in scope (insight #5)? If yes, the checker is incomplete.
4. Fix-in-place vs remove-and-de-list (insight #4) — is two required gates for one invariant acceptable?
5. Were the edited line numbers re-derived on disk, not copied from the stale audit (insight #1)?

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Reimplement invariant in workflow bash | Encode the single-source check directly as `grep`/`bash` logic inside `deps/version-sync` | Would re-introduce the regex false-PASS bug already fixed in #435; duplicates logic the tested script owns | DRY: delegate to the existing tested script; never re-encode an invariant that a tested checker already implements |
| Trust audit-cited line numbers | Plan edits against issue-cited `_required.yml:770-820`, `:812`, `:814` | Lines were stale by ~40 lines; real positions were `:806`, `:831-838`, `:848`, `:850` | Re-derive line numbers on disk with `grep -n` before planning any workflow edit |
| Local `pixi run` as proof of CI correctness | Verify with `pixi run --environment default python3 scripts/check_version_single_source.py` | The CI job uses `pip install -e . --no-deps` + bare `python` (no pixi env) — pixi has the full deps, so it cannot surface a `--no-deps` ImportError | Verification must mirror the real CI invocation path (venv + `--no-deps` + bare `python`), not the convenient local one |
| Assume "only needs the repo checkout" | Conclude from *reading* the script that it has no runtime deps beyond stdlib + repo | `get_repo_root` / transitive imports may pull a dep `--no-deps` omits; reading code is not running it | The #1 uncertain assumption in any "delegate to existing script" plan is whether it imports cleanly in CI's minimal env — RUN it, don't read it |
| Silently narrow scope to match the chosen tool | Have `deps/version-sync` cover only what `check_version_single_source.py` checks | DoD documents pyproject + pixi.toml + `pixi.lock`; checker omits `pixi.lock` | Compare the reused tool's coverage against the documented gate intent (DoD) before adopting it; flag any narrowing explicitly |

## Results & Parameters

| Parameter | Value |
| --------- | ----- |
| **Repo / issue** | HomericIntelligence/ProjectHephaestus #1181 |
| **Defective gate** | `deps/version-sync` (required status check) in `.github/workflows/_required.yml` |
| **Defect class** | No-op gate: computes `DYNAMIC`, echoes it, never branches; only `exit 1` in dead `if [ -f VERSION ]` branch (no VERSION file) |
| **Chosen fix** | Invoke `scripts/check_version_single_source.py` from the job (reuse tested logic; fix-in-place, do not delete) |
| **CI runtime** | `actions/setup-python` py3.12; `pip install -e "." --no-deps`; bare `python scripts/...` |
| **Redundancy** | Same invariant also enforced by `check-version-single-source` pre-commit hook (separate required lint step) |
| **Required-context references** | `.github/README.md:47`, `docs/DEFINITION_OF_DONE.md:28` (so the name must be preserved if fixing in place) |
| **DoD scope** | pyproject.toml + pixi.toml + pixi.lock; reused checker covers pyproject + pixi.toml only (pixi.lock NOT covered) |
| **#1 reviewer risk** | `--no-deps` import surface of the reused script under bare `python` (insight #2) |
| **Verification status** | unverified — plan only; the headline risk was reasoned, not run |

### Outcome

This is a PLANNING-QUALITY learning: the value is the catalogue of the most
uncertain assumptions and the reviewer-focus list above, not executed code. The
single most transferable rule for any "fix a no-op required CI gate by delegating
to an existing tested script" task: **prove the script imports and exits correctly
under the EXACT CI invocation path (`--no-deps` + bare `python`) before claiming
the gate is fixed — reading the script is not running it.**
