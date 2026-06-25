---
name: plan-authoring-ci-justfile-fix-risk-surfacing
description: "How to AUTHOR a high-confidence, reviewable implementation plan for a \"passes locally, fails in CI\" justfile/CI-recipe fix AND self-surface the plan's own weak points to the reviewer. This is about PLAN-AUTHORING DISCIPLINE, not execution: the durable artifact is a checklist that separates verified-local recipe mechanics from the UNVERIFIED core root-cause claim, and that loudly flags every assumption a reviewer must scrutinize. Use when: (1) writing a plan for an issue like \"validate-configs fails in CI, passes locally\" where the failing CI log was never read; (2) the issue names a workflow (build.yml/ci.yml) but you have NOT grepped ALL of .github/ for the recipe name to find the REAL caller (e.g. the build job in _required.yml); (3) a directory-target linter (yamllint configs/) may be a SILENT NO-OP because its default glob matches zero files; (4) the plan removes a `pip install <tool>` CI step and assumes `pixi run <tool>` resolves without regenerating/committing pixi.lock; (5) \"verified locally\" was actually done with an AMBIENT tool from an unrelated active env, not the tool the plan introduces; (6) a new count-assert guard over a `git ls-files '**/*.json'` pathspec could convert a benign empty glob into a HARD self-inflicted build failure; (7) a verification block references tools (check-jsonschema) not present in pixi.toml. Sibling to justfile-and-local-build-verification (EXECUTION mechanics) and ci-failure-triage-and-diagnosis (DIAGNOSIS) — this one is the PLAN-AUTHORING + risk-surfacing layer."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - planning-methodology
  - plan-authoring
  - ci-fix
  - justfile
  - validate-configs
  - yamllint
  - silent-no-op
  - empty-glob-guard
  - pixi
  - pixi-lock
  - ambient-tool-verification
  - unverified-root-cause
  - reviewer-risk-flags
  - ci-log-reconciliation
  - meta-repo
  - odysseus
  - self-surfacing-assumptions
  - verification-honesty
---

## Overview

| Field | Value |
|-------|-------|
| **Theme** | Authoring a reviewable CI/justfile-fix plan and self-surfacing its weak points |
| **Date** | 2026-06-20 |
| **Objective** | Produce a high-confidence plan for Odysseus issue #252 ("validate-configs fails in CI, passes locally") and flag every assumption a reviewer must scrutinize |
| **Outcome** | Plan produced; recipe MECHANICS verified-local (commands actually run in the planner's shell), but the CORE ROOT-CAUSE claim is UNVERIFIED against the actual failing CI run |
| **Verification** | verified-local (recipe mechanics) / unverified (CI root cause) |
| **Category** | CI/CD / Planning |
| **Related Issues** | Odysseus #252 |

> **Verification honesty gate.** The recipe mechanics below (yamllint glob behavior,
> JSON-as-YAML brace errors, the `_required.yml` caller) were verified by running
> commands in the planner's shell — `verified-local`. But the **CORE root-cause claim
> is `unverified` against CI**: the failing run's log (run 25217481782) was never
> fetched, and in the planner's clean-checkout reproduction the recipe PASSED both
> locally and in a fresh checkout. So the plan **hardens a fragile recipe but does NOT
> reproduce the reported CI failure.** Treat the Proposed Workflow accordingly.

The durable, reusable lesson is **NOT the specific yamllint/pixi fix**. It is the
**plan-authoring checklist** for the class of "CI fails, local passes — write a fix
plan" and the discipline of **self-surfacing the plan's weakest assumptions** so the
reviewer knows exactly where to push.

---

## When to Use

Use this skill when authoring a plan and ANY of these apply:

1. The issue is **"passes locally, fails in CI"** for a justfile/CI recipe, and you have
   **not read the failing run's log** (API says "no detailed error output available").
2. The issue **names a workflow** (e.g. `build.yml`, `ci.yml`) but you have not grepped
   ALL of `.github/` for the recipe name to confirm the **real caller**.
3. A **directory-target linter** (`yamllint configs/`) might be a **silent no-op** because
   its default file glob matches zero files in that directory.
4. The plan **removes a `pip install <tool>` CI step** and assumes `pixi run <tool>`
   resolves in a fresh checkout — without regenerating and committing `pixi.lock`.
5. "Verified locally" was actually done with an **ambient tool from an unrelated env**
   (not the tool/version the plan introduces).
6. A **new count-assert guard** over a `git ls-files '**/*.json'` pathspec could flip a
   benign empty glob into a **hard build failure** (self-inflicted regression).
7. A **verification block references tools not in `pixi.toml`** (e.g. `check-jsonschema`).

---

## Verified Workflow

> **Proposed Workflow.** Recipe mechanics are `verified-local`; the dominant
> root-cause claim is `unverified` against the failing CI run. Validate every step
> against the on-disk repo and the actual CI log before acting.

### Quick Reference

| Step | Do this | Anti-pattern to avoid |
|------|---------|------------------------|
| Find the real CI caller | `grep -rn "<recipe>" .github/` across ALL workflows | Trusting the issue's named workflow (build.yml/ci.yml) |
| Read the failing log | Fetch the actual failing run's log before hypothesizing | Reasoning to a root cause from the issue text alone |
| Audit directory-linters | Check WHAT the linter globs: `git ls-files <dir> \| grep -E '\.ya?ml$' \| wc -l` | Assuming "exit 0" means it linted something |
| Verify the fix tool's source | Confirm the tool comes from THIS repo's pixi, at the pinned version | Quoting behavior of an ambient tool from another env |
| Guard the new guard | Confirm `git ls-files '**/*.json'` returns the expected N files | A count-assert that hard-fails on an empty glob |
| Reconcile before merge | Match hypothesized cause to the literal failing run | Shipping "harden recipe" while claiming "fix the failure" |

1. **Grep ALL workflow files for the recipe name before trusting the issue's workflow
   attribution.** Issue #252 said the "build job"; `build.yml` and `ci.yml` did NOT call
   `validate-configs`. The real caller was the `build` job in
   `.github/workflows/_required.yml:276` running `just validate-configs`. Run
   `grep -rn "validate-configs" .github/` first — the issue's workflow name is a hint,
   not ground truth.

2. **Read the failing run's log before reasoning to a root cause.** The single biggest
   risk in this plan: the issue said "no detailed error output available via API," so the
   plan REASONED to a cause (unpinned `pip install yamllint` + bare `yamllint` on PATH +
   silent no-op) but never read run 25217481782. With a committed `.yamllint.yml` and
   yamllint 1.38.0, the recipe passed BOTH locally and in a clean checkout — so the plan
   does not actually reproduce the reported failure. If you cannot read the log, REFRAME
   the plan as "harden a fragile recipe," not "fix the reported failure."

3. **Audit what a directory-target linter actually globs — it may lint nothing.**
   `yamllint configs/` was a SILENT NO-OP: `configs/` held zero `*.yml`/`*.yaml` files
   (only `.json`/`.conf`/`.hcl`/`.md`), and yamllint's default `yaml-files` glob is
   `['*.yaml', '*.yml', '.yamllint']`, so a directory scan matched nothing and exited 0.
   Verified: `git ls-files configs/ | grep -E '\.ya?ml$' | wc -l` → 0, and
   `yamllint -c .yamllint.yml configs/` → exit 0. A recipe that "passes" may be linting
   NOTHING. JSON is valid YAML, so pointing yamllint at the `.json` files directly
   surfaced 34 real `too many spaces inside braces` errors — proof the recipe had never
   exercised them.

4. **Confirm the fix tool's provenance and version — not an ambient one.** The planner's
   yamllint 1.38.0 came from an UNRELATED active env (Hephaestus), NOT from Odysseus's
   pixi. So "verified locally" for yamllint behavior used an ambient tool, not the tool
   the plan introduces (`yamllint >=1.35,<2` added to `[dependencies]`). State this
   explicitly; do not let ambient-tool output masquerade as repo-tool verification.

5. **Guard the new guard: confirm the pathspec enumerates real files.** A new recipe using
   `mapfile` + `git ls-files 'configs/**/*.json'` assumes git's pathspec double-star
   semantics actually enumerate `configs/github/backups/...json`. If `**` silently returns
   empty, a downstream count-assert would FAIL the build — a self-inflicted regression.
   Verify the glob returns the expected files (e.g. the 5 JSON files) BEFORE wiring an
   assert that hard-fails on empty.

6. **Don't remove a CI install step without regenerating the lockfile.** Removing
   `pip install yamllint` assumes `pixi run yamllint` resolves in a fresh CI checkout
   AFTER adding yamllint to `[dependencies]` AND regenerating/committing `pixi.lock`. The
   plan listed `pixi install` → stage `pixi.lock` as a step but the planner did NOT run it
   (lockfile was v6, pixi warned to re-lock). If `pixi.lock` is not committed, CI breaks.

7. **Every verification command must reference a tool that exists in `pixi.toml`.** The
   plan's verification block included `pixi run check-jsonschema --builtin-schema
   vendor.github-workflows`, but `check-jsonschema` is NOT in `pixi.toml` dependencies, so
   that command would itself fail. Audit your own verification block against the manifest.

8. **Separate verified-local mechanics from the unverified core claim, in the plan body.**
   List which commands were actually run (glob counts, brace errors, the `_required.yml`
   caller) versus what was reasoned (the CI root cause). A reviewer should be able to see
   the honesty boundary without re-deriving it.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Trusted the issue's named workflow | Assumed the failing recipe ran in the "build job" of `build.yml`/`ci.yml` as the issue implied | Neither workflow called `validate-configs`; the real caller was the `build` job in `_required.yml:276` | `grep -rn "<recipe>" .github/` across ALL workflows before trusting the issue's workflow attribution |
| Assumed recipe failure without reading the CI log | Reasoned to a root cause (unpinned `pip install yamllint` + bare PATH yamllint + silent no-op) from issue text only; never fetched run 25217481782 | The recipe PASSED in both local and clean-checkout reproduction, so the plan does not reproduce the reported failure — the core claim stayed unverified | Read the failing run's log first; if unavailable, REFRAME as "harden a fragile recipe," not "fix the failure," and label the root cause `unverified` |
| Relied on ambient yamllint from an unrelated env | Cited yamllint 1.38.0 behavior as "verified locally" | The 1.38.0 binary came from an active Hephaestus env, NOT Odysseus's pixi; the plan introduces `yamllint >=1.35,<2`, a different provenance | Verify tool behavior with the tool/version the plan actually introduces, from THIS repo's pixi — never an ambient binary |
| Trusted the directory-target linter's exit code | Treated `yamllint configs/` exiting 0 as "configs are clean" | `configs/` had zero `*.yml`/`*.yaml` files and yamllint's default glob matched nothing → exit 0 while linting NOTHING | Check WHAT a directory-target linter globs: `git ls-files <dir> \| grep -E '\.ya?ml$' \| wc -l`; a "passing" recipe may exercise no files |
| Count-assert over an unverified glob | New recipe used `git ls-files 'configs/**/*.json'` + a guard that fails if count is low | If git's `**` pathspec returns empty, the guard converts a benign empty glob into a HARD build failure (self-inflicted regression) | Confirm the pathspec enumerates the expected N files before wiring an assert that hard-fails on empty |
| Removed `pip install yamllint` without re-locking | Planned to drop the CI install step and rely on `pixi run yamllint` | `pixi.lock` (v6, pixi warned to re-lock) was never regenerated/committed; `pixi run yamllint` would fail in a fresh CI checkout | When removing a `pip install` step in favor of pixi, regenerate AND commit `pixi.lock` in the same change; actually run `pixi install` |
| Verification command for a tool not in pixi | Put `pixi run check-jsonschema --builtin-schema vendor.github-workflows` in the verification block | `check-jsonschema` is not in `pixi.toml` dependencies, so the verification command itself would fail | Audit every verification command against `pixi.toml`; a verification step that can't run is worse than none |

---

## Results & Parameters

The plan for Odysseus issue #252 proposed: add `yamllint` to pixi `[dependencies]`
(`>=1.35,<2`), regenerate/commit `pixi.lock`, rewrite `validate-configs` to lint the
actual `configs/**/*.json` files (with a count-assert guard), remove the CI
`pip install yamllint` step, and run via `pixi run yamllint`. **The fix mechanics were
exercised locally; the CI root cause was never confirmed against the failing run.**

### Verified-local (commands actually run during planning)

| Claim | Command / evidence |
|-------|--------------------|
| Real caller is `_required.yml`, not build.yml/ci.yml | `grep -rn "validate-configs" .github/` → `_required.yml:276` `just validate-configs` |
| `configs/` has zero YAML files | `git ls-files configs/ \| grep -E '\.ya?ml$' \| wc -l` → 0 |
| `yamllint configs/` is a silent no-op | `yamllint -c .yamllint.yml configs/` → exit 0 (default glob `['*.yaml','*.yml','.yamllint']` matched nothing) |
| JSON is valid YAML; real errors existed | yamllint on the `.json` files surfaced 34 `too many spaces inside braces` errors |

### MOST UNCERTAIN assumptions a reviewer MUST scrutinize (verbatim)

1. **Root cause is UNCONFIRMED against the actual CI log.** The plan reasons to a cause
   but never read run 25217481782. With committed `.yamllint.yml` and yamllint 1.38.0 the
   recipe passes locally AND in a clean checkout — the plan does NOT reproduce the reported
   failure. This is the single biggest risk: the fix hardens the recipe but may not address
   the literal failing run.
2. **`git ls-files 'configs/**/*.json'` pathspec semantics.** The new recipe assumes git's
   `**` enumerates `configs/github/backups/...json`; `mapfile` + `git ls-files` `**`
   behavior must be verified to actually return the files and not silently return empty
   (which would trip the new guard and FAIL the build).
3. **`pixi run yamllint` resolution after re-lock.** Removing `pip install yamllint`
   assumes `pixi run yamllint` resolves in a fresh CI checkout AFTER adding yamllint to
   `[dependencies]` AND regenerating/committing `pixi.lock`. The planner did NOT run
   `pixi install`; the lockfile is v6 and pixi warned to re-lock. If `pixi.lock` is not
   committed, CI fails.
4. **yamllint version provenance.** The `>=1.35,<2` pin was "verified" using an ambient
   1.38.0 from an unrelated active env (Hephaestus), NOT Odysseus's pixi.

### External things relied on WITHOUT direct verification

- The CI failure log itself (never fetched — run 25217481782).
- Whether conda-forge `yamllint` at `>=1.35,<2` resolves on `linux-64` in this pixi
  workspace (not run).
- `pixi run check-jsonschema --builtin-schema vendor.github-workflows` — `check-jsonschema`
  is NOT in `pixi.toml`, so that verification command would itself fail unless added.

### Reviewer risk-flags (where to focus)

- **Reconcile the actual failing-run log with the hypothesized cause before merge**, OR
  reframe the plan as "harden a fragile recipe" rather than "fix the reported failure."
- **The new count-assert guard can turn a benign empty glob into a HARD build failure** —
  confirm `git ls-files 'configs/**/*.json'` returns the 5 JSON files.
- **`pixi.lock` MUST be regenerated and committed**, else removing `pip install yamllint`
  breaks CI.
- **Verification commands referencing tools not in pixi (`check-jsonschema`) are not
  runnable as written** — fix or remove them.

### Verification level

`verified-local` at best for the recipe mechanics (commands were run in the planner's
shell); the core root-cause claim is `unverified` against CI. The Proposed Workflow
heading reflects that the dominant content (the reported failure's cause) is unverified.
