---
name: release-workflow-planning-assumptions-and-risks
description: "Planning-phase risk checklist for designing an automated release workflow in a repo (especially a meta-repo) that has NEVER shipped a versioned release. The implementation mechanics live in `gha-release-package-workflow-patterns` and `lockfile-and-release-pipeline-management`; this skill is the DIFFERENT search surface a plan REVIEWER reaches for — 'are the plan's release assumptions verified?' not 'how do I write release.yml'. Core thesis: a first-release plan is full of assertions that look like decisions but are actually unverified guesses — the target version, the CHANGELOG link-footer tags, the TOML table name, the runner Python version, and signing-key availability. Each must be VERIFIED during implementation, not asserted in the plan. Use when: (1) reviewing or writing a plan that bumps a manifest version to 'match' the CHANGELOG without reconciling against real git tags + GitHub Releases, (2) a plan hard-codes keepachangelog compare-URLs (.../compare/vA...vB) that assume those tags exist as real refs, (3) a reused consistency script hard-indexes pixi['workspace']['version'] (or assumes [project]) without reading the target file's actual table name, (4) scripts `import tomllib` with no `tomli` fallback and the CI runner Python version is unconfirmed, (5) a justfile/release recipe uses `git tag -s` but signing-key availability in CI/local was never confirmed, (6) the issue body cites commit SHAs or file states that do not match the live repo and the plan does not flag the mismatch, (7) a third-party action SHA was copied from a skill/template rather than re-looked-up at plan time, (8) an ecosystem CI-naming convention demands a canonical `release` check-run in a repo with NO release wiring at all — the plan must BOOTSTRAP the release contract (CHANGELOG, version-parity invariant, validator script) in the SAME PR as the gate, because a bare always-green job is exactly the fabricated check the convention forbids."
category: ci-cd
date: 2026-07-02
version: "1.3.0"
user-invocable: false
verification: unverified
history: release-workflow-planning-assumptions-and-risks.history
tags:
  - planning-methodology
  - planning
  - release-automation
  - version-reconciliation
  - git-tags
  - required-checks
  - branch-protection
  - signing
  - tomllib
  - meta-repo
  - first-release
  - version-drift
  - keepachangelog
  - compare-url-tags
  - git-tags-vs-releases
  - pixi-toml
  - workspace-vs-project
  - tomllib-fallback
  - signed-tags
  - signing-key-availability
  - issue-vs-reality-mismatch
  - third-party-action-sha
  - required-check-wiring
  - unverified-assumptions
  - verify-dont-assert
  - changelog-footer
  - compare-url
  - root-commit
  - cross-artifact-consistency
  - test-artifact-parity
  - tomllib
  - canonical-release-check
  - ci-naming-convention
  - never-tagged-repo
  - release-contract-bootstrap
  - orphan-workflow-call
  - json-version-regex-ordering
---

# Release Workflow Planning: Assumptions & Risks (First-Release / Meta-Repo)

**History:** [changelog](./release-workflow-planning-assumptions-and-risks.history)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable PLANNING-PHASE risks — and now the EXACT verification commands that resolve them — surfaced while writing (R0), re-planning (R1), then re-re-planning (R2) an implementation plan to add an automated release workflow to the Odysseus meta-repo (GitHub issue #189), a repo that had never shipped a versioned release. R0 made assertions that LOOK like decisions but were unverified guesses (target version, CHANGELOG link-footer tags, TOML table name, runner Python version, signing-key availability) and got a NOGO. R1 resolved each by checking ground truth (`git tag --list`, `gh release list`, `git log`, ruleset `name:` contexts) and added the meta-repo required-check wiring pattern — but R1 itself got a NOGO on a single CROSS-ARTIFACT finding: the same plan shipped a CHANGELOG footer (`…/commits/main`) and a regression test (`compare/…HEAD` regex) that asserted DIFFERENT forms — the prescribed file could not pass the prescribed test. R2 resolved it with the tagless root-SHA compare form and a producer/validator cross-check. R3 closed the residual reviewer request by ACTUALLY RUNNING the prescribed footer through all three regexes the plan ships (test #3 positive, test #4 phantom-rejection, verification grep) and pasting the observed PASS/not-tripped/MATCH results — a demonstrated parity, not an asserted one. Each must be VERIFIED, not asserted — AND the plan's own producer must satisfy the plan's own validator (execute the validator, don't claim it). |
| **Outcome** | Hypothesis only — no CI run validated the plan, so verification stays `unverified`. But the R1 ground-truth inspections (empty tag/release lists, absent issue SHAs, pinned ruleset contexts) and the R2 root-commit lookup (`git rev-list --max-parents=0 HEAD` = `b10bfdd`) were REAL and resolved every finding. This skill is a reviewer/author checklist plus a resolution-command cheat-sheet, not a verified procedure. |
| **Verification** | unverified |

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## When to Use

Reach for this when REVIEWING or WRITING a first-release / meta-repo release plan and you need to separate *verified decisions* from *unverified guesses*. Specifically:

- The plan **bumps a manifest version** (e.g. `pixi.toml` 0.1.1 → 0.4.0) to "match" the latest dated CHANGELOG section, **without** reconciling against published git tags (`git tag --list 'v*'`) or GitHub Releases. The CHANGELOG might be aspirational and `0.1.1` the real last release — bumping could skip real releases or claim a version never shipped.
- The plan emits a **keepachangelog link-footer** with compare-URLs (`.../compare/v0.2.0...v0.4.0`) that assume both the `OWNER/REPO` slug and every referenced tag exist. The slug was never confirmed with `git remote get-url origin`; the tags were never confirmed as real refs. Any missing tag → the compare link 404s.
- A reused `check_version_consistency.py` **hard-indexes `pixi["workspace"]["version"]`** (or assumes `[project]`) instead of reading the actual table name from the target file. Many pixi projects use `[project]` → the script `KeyError`s.
- Scripts **`import tomllib`** with no fallback, and the **CI runner Python version is unconfirmed**. `tomllib` is stdlib only on Python 3.11+.
- A `release` justfile recipe (or workflow step) uses **`git tag -s`** (signed tags) but **signing-key availability** in CI/local was never confirmed. A `.pre-commit-config.yaml` that enforces signed *commits* does NOT imply signed *tags* will work.
- The **issue body cites commit SHAs or file states that do not match the live repo** (e.g. issue #189 cited commits `b52a678`, `9d29e37`, `41ac0b8` as "adding significant features"; the real CHANGELOG content differed entirely). The plan should FLAG the mismatch to the reviewer, not silently ignore it.
- A **third-party action SHA** (e.g. `softprops/action-gh-release@de2c0eb…` / v0.1.15) was copied from a skill/template rather than re-looked-up at plan time — it may be outdated or yanked. Re-verify at plan time: `gh api repos/<owner>/<repo>/git/ref/tags/<vX.Y.Z>`.
- The plan adds a **new release gate as a standalone job to a non-required workflow** (e.g. a `release-contract-test` job in `ci.yml`) in a fleet/meta-repo whose branch-protection rulesets pin specific status-check contexts. In Odysseus, `.github/workflows/_required.yml` job `name:` values ARE the contexts pinned by `configs/github/org-ruleset*.json` (`"Required Checks / <name>"`) and `repo-ruleset*.json` (bare `"<name>"` + `integration_id: 15368`), documented in `configs/github/canonical-checks.md`. A new job in a non-required workflow is SILENTLY non-blocking — the gate exists but never blocks a merge.
- The plan authors BOTH a **producer** (a file/edit it prescribes — e.g. the CHANGELOG `[Unreleased]` footer string) AND its **validator** (a test/grep/regex it prescribes — e.g. `release.test.sh` test #3) but states them in TWO DIFFERENT forms, so the prescribed file cannot pass the prescribed test. In R1 the footer was `[Unreleased]: …/commits/main` while the regression test asserted `compare/…HEAD` — the plan literally cannot execute as written; the implementer is forced to pick between two stated "facts". This is a NOGO even with ZERO external/factual errors, because the artifact is internally inconsistent. The reviewer WILL grep the generated artifact against the generated test — so the plan author must run that exact cross-grep first. (This is a DIFFERENT axis from issue-vs-reality: it is plan-vs-plan internal consistency, not plan-vs-repo.)
- The plan emits an `[Unreleased]` footer for a **never-tagged repo** and oscillates between a phantom `compare/v0.1.0...HEAD` (404s — no such tag) and `…/commits/main` (valid but does NOT match a `compare/…HEAD` convention the test/skill expects). "Valid URL" and "matches the team-convention regex" are TWO requirements; only the tagless root-SHA compare form (`…/compare/<root-sha>...HEAD`) satisfies both.

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read every step below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

Run these checks at PLAN time (or demand them as implementation acceptance criteria) before treating any of the five assertions as a decision:

| # | Risky assertion in the plan | Verify-instead command / action | Fail signal |
| - | --------------------------- | -------------------------------- | ----------- |
| 1 | "Bump version to 0.4.0 to match CHANGELOG" | `git tag --list 'v*'` **AND** `gh release list` **AND** read the manifest — reconcile all THREE | A real tag/release exists at a version the bump would skip or overwrite |
| 2 | Hard-coded compare-URL footer (`compare/vA...vB`) | `git remote get-url origin` (slug) **+** `git rev-parse vA vB` for every referenced tag | Any tag is not a real ref → that compare link 404s |
| 3 | Script indexes `pixi["workspace"]["version"]` | Read the target `pixi.toml`: is it `[workspace]` or `[project]`? Detect at runtime | Table name differs → `KeyError` |
| 4 | Scripts `import tomllib` | Confirm CI runner `python --version` >= 3.11, OR add `tomli` fallback | Runner < 3.11 and no fallback → `ModuleNotFoundError` |
| 5 | `git tag -s` in the release recipe | Branch on `git config --get user.signingkey` — sign when present, else `git tag -a` | No key → hard `git tag -s` fails; signed *commits* in pre-commit do NOT cover tags |
| 6 | New release gate as a standalone job in a non-required workflow | `grep -nE 'name: (deps/version-sync|unit-tests)'` (contexts unchanged) **+** `grep -n '<script>'` (step attached to a required job) | Gate lives in `ci.yml` not `_required.yml` → silently non-blocking |
| 7 | Plan ships a file AND a test that checks it, in two different forms | EXECUTE the test regex against the literal footer string (`printf '%s' '<footer>' \| grep -E '<regex>'`) and paste the observed PASS/MATCH into the plan — don't just assert parity | Producer form ≠ validator form → the prescribed file fails the prescribed test (internal NOGO); an asserted match weighs less than a demonstrated one |
| 8 | `[Unreleased]` footer for a never-tagged repo | Use root SHA as compare base: `git rev-list --max-parents=0 HEAD` → `…/compare/<root-sha>...HEAD` | Phantom `compare/v0.1.0...HEAD` 404s; bare `…/commits/main` fails a `compare/…HEAD` regex |

**Plan-time verification command sequence** — run this exact block (or demand it as acceptance criteria) BEFORE choosing a target version or wiring any gate:

```bash
# (A) Has this repo EVER shipped a versioned release? Both empty => never-released.
git tag --list 'v*' --sort=-v:refname
gh release list
# If BOTH empty: do NOT converge the manifest onto any historical CHANGELOG
# entry (0.2.0/0.3.0/0.4.0 are documented-but-never-shipped). Leave the
# manifest as-is; make the next tag a fresh forward version.

# (B) CHANGELOG link-footer gate for a NEVER-TAGGED repo: do NOT use a phantom
# compare/v0.1.0...HEAD (404 — no tag) and do NOT settle for a bare
# .../commits/main (valid but fails a compare/...HEAD convention regex).
# Use the ROOT commit as the compare base — valid for any reachable ref, no tag needed:
ROOT_SHA=$(git rev-list --max-parents=0 HEAD)     # Odysseus root = b10bfdd
# Footer:  [Unreleased]: https://github.com/<slug>/compare/${ROOT_SHA}...HEAD
# Positive assertion (tolerant of a SHA base now AND a vX.Y.Z base later):
grep -qE "compare/[0-9a-fv.]+\.\.\.HEAD" CHANGELOG.md          # MUST match
# Negative assertion (reject phantom v-tag links); the root-SHA base (no 'v' prefix)
# must NOT trip this — design the two assertions so they cannot conflict:
grep -qE "releases/tag/v[0-9]|compare/v[0-9]" CHANGELOG.md && echo "PHANTOM v-tag -> NOGO" || echo "OK no phantom v-tag"

# (B') Producer/validator cross-check: the footer STRING the plan writes and the
# REGEX the plan's test asserts must be stated ONCE and confirmed to match verbatim.
FOOTER="[Unreleased]: https://github.com/<slug>/compare/${ROOT_SHA}...HEAD"
echo "$FOOTER" | grep -qE "compare/[0-9a-fv.]+\.\.\.HEAD" \
  && echo "OK producer satisfies validator" || echo "MISMATCH -> internal NOGO"

# (C) Required-check wiring: prove the gate attaches to an EXISTING required job
# (whose name: is the pinned ruleset context) — not a new job in a non-required workflow.
grep -nE 'name: (deps/version-sync|unit-tests)' .github/workflows/_required.yml  # contexts unchanged
grep -n 'check_version_consistency' .github/workflows/_required.yml              # step present in a required job

# (D) Issue-vs-reality: confirm cited SHAs actually exist in this repo.
git log --oneline -5
git cat-file -e <cited-sha> 2>/dev/null && echo "EXISTS" || echo "ABSENT -> flag in plan"
```

Two cross-cutting source-trust rules:

- **Issue-vs-reality mismatch:** if the issue's cited SHAs / file states don't match the live repo, STATE the contradiction explicitly and cite the live `file:line` (e.g. issue #189 claimed `[Unreleased]` empty + cited `b52a678`/`9d29e37`/`41ac0b8`, but live `CHANGELOG.md:8-50` is richly populated and those SHAs are absent from `git log`). Don't silently route around phantom evidence and solve a different problem.
- **Re-verify third-party action SHAs at plan time** against the published tag: `gh api repos/<owner>/<repo>/git/ref/tags/<vX.Y.Z>` — skill-carried SHAs go stale.
- **Cross-grep every generated artifact against every generated test that checks it (plan-vs-plan) — and EXECUTE the grep, don't assert it.** The reviewer WILL (and in R1 did) grep the prescribed file against the prescribed test — so the author must do the same first, run the validator against the literal artifact (`printf '%s' '<artifact>' | grep -E '<test-regex>'`), and PASTE the observed PASS / not-tripped / MATCH result into the plan. A reviewer weighs a DEMONSTRATED match above an ASSERTED one. For every assertion in a generated test, confirm the generated artifact it checks satisfies it VERBATIM. This is a distinct axis from issue-vs-reality: even with zero external errors, a plan whose producer and validator disagree is internally inconsistent and a NOGO.

### Detailed Steps

**1. Reconcile the target version across THREE sources, not two.**
The trap is treating manifest-vs-CHANGELOG as the whole picture. The CHANGELOG's dated sections may be aspirational; the manifest's `0.1.1` may be the real last shipped version. Before picking the version to converge on:

```bash
git tag --list 'v*' --sort=-v:refname        # what was actually tagged
gh release list --limit 50                    # what was actually published
grep -nE '^version' pixi.toml                 # what the manifest claims
grep -nE '^## \[' CHANGELOG.md                # what the CHANGELOG claims
```

Only after all four agree on the lineage do you choose the target. If they disagree, the disagreement IS the finding — surface it; do not paper over it with a bump. **If `git tag --list 'v*'` AND `gh release list` are BOTH empty, the repo has NEVER shipped:** the latest dated CHANGELOG section (e.g. `## [0.4.0]`) is documented-but-never-released history, NOT the last released version. Converging the manifest onto it would claim a never-shipped version and silently skip `0.2.0`/`0.3.0`/`0.4.0`. Leave the manifest as-is and make the next tag a fresh forward version. "Latest dated CHANGELOG section" is NOT a proxy for "last released version" — only git tags + GitHub Releases are.

**2. Treat the CHANGELOG link-footer as a verification task, not a templating task.**
A keepachangelog footer is only valid if (a) the `OWNER/REPO` slug is correct and (b) every referenced tag is a real ref.

```bash
git remote get-url origin                     # confirm the OWNER/REPO slug
for t in v0.1.0 v0.1.1 v0.2.0 v0.4.0; do
  git rev-parse --verify "refs/tags/$t" >/dev/null 2>&1 \
    && echo "OK   $t" || echo "MISSING $t  -> compare link will 404"
done
```

Generate the footer FROM the verified tag set; never hard-code compare-URLs whose tags you have not confirmed. **Gate footer generation on `git tag --list`:** if it is empty, the only valid `[Unreleased]` target is `.../commits/main` (or `.../commits/<default-branch>`), NOT `compare/<tag>...HEAD`. Add a regression assertion — `grep -c "releases/tag/v\|compare/v0" CHANGELOG.md` must be `0` — so the link-footer can never re-introduce a 404ing ref. A link-footer is a verification artifact, not a template: each tag in it must be a real ref.

**3. Read the actual TOML table name before indexing it.** See the detection snippet in *Results & Parameters*. A reusable consistency script must not assume `[workspace]` (pixi) or `[project]` (PEP 621) — read whichever the target file uses.

**4. Confirm the runner Python version or add the `tomli` fallback.** See the import snippet in *Results & Parameters*. `tomllib` is stdlib only on 3.11+; CI runners and pre-commit `language: python` envs vary.

**5. Scope the consistency guard to the moment its invariant must hold.** A naive `check_version_consistency.py` that forces `pixi.toml == top-CHANGELOG-dated-section` fails on day one (0.1.1 ≠ 0.4.0) and blocks every commit because of pre-existing documented history. Split it into two modes: (a) **default / pre-commit mode** = "manifest parses and declares a version" (no cross-file equality); (b) **`--expect VERSION` release-time mode** = "tag == `pixi.toml` == top dated CHANGELOG section, all equal `VERSION`". Only the release path (tag push) enforces the three-way match. See the script sketch in *Results & Parameters*.

**6. Wire new gates INTO existing required jobs — never add a standalone job to a non-required workflow.** In Odysseus, `.github/workflows/_required.yml` job `name:` values are the EXACT status-check contexts pinned by the branch-protection rulesets (`configs/github/org-ruleset*.json` use `"Required Checks / <name>"`; `repo-ruleset*.json` use bare `"<name>"` + `integration_id: 15368`; documented in `configs/github/canonical-checks.md`). Adding a `release-contract-test` job to `ci.yml` (non-required) makes the check SILENTLY non-blocking. Instead: attach the version-consistency step to the existing `deps/version-sync` job and the bash regression test to the existing `unit-tests` job. Do NOT rename any job `name:` — renaming breaks the pinned ruleset context and requires re-applying rulesets. Verify: `grep -nE 'name: (deps/version-sync|unit-tests)'` (contexts unchanged) + `grep -n '<script>'` (step present). Required-check status is conferred by the job name being in the ruleset, NOT by the test merely existing somewhere in CI.

**7. Make the signed-tag flow degrade gracefully — detect the key, don't assume it.** A `.pre-commit-config.yaml` that signs *commits* does not make signed *tags* work, and no signing key is known in CI. Branch on capability: `git tag -s -a` when `git config --get user.signingkey` is set, else annotated `git tag -a`. Signing is a capability to detect, not assume. See the pre-flight snippet in *Results & Parameters*.

## Sub-Pattern: Bootstrapping a Canonical release Check in a Repo With No Release Model (Mnemosyne #2913)

**Status: plan-only / unverified.**

> **Warning:** This sub-pattern is a PLAN (issue #2913); no code was executed beyond read-only ground-truth commands. Treat as hypothesis until CI confirms.

**Central insight:** when an ecosystem convention (here the Odysseus ci-naming convention) requires a canonical `release` check-run but the repo has NO release artifact or contract (no tags, no releases, no CHANGELOG), do NOT wire a trivially-green job — a bare always-green `release` job is exactly the fabricated check the convention forbids. Define the release model FIRST (here: a tagged marketplace snapshot at a repo-level semver already present in 4 files: `pixi.toml`, `pyproject.toml`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` — all `2.1.0`), then ship contract + validator + dry-run gate in ONE PR. The dry-run job lives in the already-required workflow (`_required.yml`, alongside the canonical aggregate `test` job); the publish path lives in a separate tag-triggered `release.yml`; BOTH jobs carry `name: release`.

**Ground truth VERIFIED this instance (second real application of this skill's checklist):**

- `git tag --list` empty → never tagged → root-SHA compare footer (`git rev-list --max-parents=0 HEAD` = `3c5616d…`).
- Producer/validator cross-grep EXECUTED and pasted, per Quick Reference row #7: footer matches `compare/[0-9a-fv.]+\.\.\.HEAD`; the root SHA rev-parses.
- Version parity `2.1.0` across all four files confirmed by reading each file directly.
- Existing validator script exit codes enumerated: all existing paths exit `1`, argparse errors exit `2` → picked collision-free exit code `3` for the new failure class.
- pixi python floor is `>=3.9` → rejected `tomllib` (stdlib only on 3.11+), chose anchored-regex TOML parsing instead.
- `_checks.yml` is `workflow_call`-only with ZERO callers (verified by grep) → NEW lesson: **grep for callers of every `workflow_call` workflow before assuming it emits checks — an orphan reusable workflow LOOKS canonical but never runs; the canonical home is the workflow actually triggered on PR/push.**

**UNVERIFIED assumptions carried by the plan (the reviewer-focus list for this instance):**

| # | Assumption | Why it is a risk |
| - | ---------- | ---------------- |
| 1 | Canonical-name semantics ("dry-run on main, publish on tag", no fabricated checks) taken from the issue body + prior skills | The Odysseus `ci-naming-convention.md` doc itself was never fetched — the plan may misstate the convention |
| 2 | Empty `git tag --list` treated as proof of never-released | `gh release list` was NOT run — a tagless draft GitHub Release would evade the tag check |
| 3 | `gh` CLI presence + `${{ github.token }}` release-create permission on ubuntu-24.04 runners | Assumed from memory, not verified in this repo's CI |
| 4 | Job `name: release` inside workflow "Required Checks" emits check-run `release`, but the ruleset context string is "Required Checks / release" | Bare-name vs prefixed-context mismatch is a known ruleset-pass trap; not re-verified against the ecosystem ruleset JSON |
| 5 | Proposed `_JSON_VERSION_RE` first-match regex on `marketplace.json` | ORDERING-DEPENDENT: the file also contains hundreds of per-plugin `"version"` keys; the top-level key happens to precede `plugins` today. Reviewer should demand `json.load` for JSON files instead of regex |
| 6 | markdownlint interaction with FUTURE CHANGELOG growth | e.g. MD024 duplicate `### Added` headings across versions — untested |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Bump manifest to match latest CHANGELOG section in a never-released repo | R0 bumped `pixi.toml` 0.1.1 → 0.4.0 to match `## [0.4.0]` in CHANGELOG, treating the latest dated section as the last released version | `git tag --list 'v*'` returns EMPTY and `gh release list` returns EMPTY — the repo has NEVER been tagged, so 0.4.0 is documented-but-never-shipped history; the bump would claim a never-released version and silently skip 0.2.0/0.3.0/0.4.0 | RESOLUTION: run `git tag --list 'v*' --sort=-v:refname` AND `gh release list` at PLAN time before choosing a target. If BOTH empty, do NOT converge the manifest onto any historical CHANGELOG entry — leave it as-is and make the next tag a fresh forward version. "Latest dated CHANGELOG section" is NOT a proxy for "last released version"; only git tags + GitHub Releases are |
| Templating the CHANGELOG link-footer with tags that don't exist | R0 emitted `compare/v0.1.1...v0.2.0`, `releases/tag/v0.1.0`, etc., assuming the slug and tags exist | With zero tags every compare/tag URL 404s; tags never confirmed as real refs | RESOLUTION: gate footer generation on `git tag --list` — if empty, the only valid `[Unreleased]` target is `…/commits/main` (or `…/commits/<default-branch>`), NOT `compare/<tag>...HEAD`. Add a regression assertion: `grep -c "releases/tag/v\|compare/v0" CHANGELOG.md` must be 0. A link-footer is a verification artifact, not a template — each tag in it must be a real ref |
| One-mode consistency guard that forces manifest == top CHANGELOG section | A naive `check_version_consistency.py` forced `pixi.toml` == top-dated-CHANGELOG-section on every commit | Fails on day one (0.1.1 ≠ 0.4.0) — blocks every commit because of pre-existing documented history; the guard is mis-scoped | RESOLUTION: split into (a) default/pre-commit mode = "manifest parses and declares a version" (no cross-file equality), and (b) `--expect VERSION` release-time mode = "tag == pixi.toml == top dated CHANGELOG section, all equal VERSION". Enforce the strict three-way invariant only at the moment it must hold (tag push), not on every commit |
| Hard-indexing `pixi["workspace"]["version"]` | `check_version_consistency.py` indexed the `[workspace]` table, confirmed only against this repo's `pixi.toml` | Many pixi/Python projects use `[project]` instead; the script `KeyError`s on those repos when reused | A reusable consistency script must READ the actual table name from the target file (detect `[workspace]` vs `[project]`), never assume one |
| `import tomllib` with no fallback | Scripts imported `tomllib` directly; CI runner Python version never verified | `tomllib` is stdlib only on Python 3.11+; on older runners / pre-commit envs the import is a `ModuleNotFoundError` | Either confirm the runner is >= 3.11 or add the `try: import tomllib / except ImportError: import tomli as tomllib` fallback |
| Standalone release-gate job added to a non-required workflow | R0 would add a `release-contract-test` job to `ci.yml` to run the version-consistency + footer regression checks | `ci.yml` is NOT in the branch-protection ruleset; the canonical contexts are the `name:` values of jobs in `.github/workflows/_required.yml` (pinned by `configs/github/org-ruleset*.json` as `"Required Checks / <name>"` and `repo-ruleset*.json` as bare `"<name>"` + `integration_id: 15368`). A new job in a non-required workflow is SILENTLY non-blocking | RESOLUTION: attach the version-consistency step to the existing `deps/version-sync` job and the bash regression test to the existing `unit-tests` job; do NOT rename any job `name:` (renaming breaks the pinned ruleset context and requires re-applying rulesets). Verify: `grep -nE "name: (deps/version-sync|unit-tests)"` (contexts unchanged) + `grep -n "<script>"` (step present). Required-check status is conferred by the job name being in the ruleset, not by the test existing somewhere in CI |
| `git tag -s` hard-called, assuming a signing key exists | R0's `just release` hard-called `git tag -s`; `.pre-commit-config.yaml` enforced signed *commits* only | Pre-commit signs COMMITS, not tags, and no signing key is known in CI — a hard `git tag -s` fails with no GPG/SSH key | RESOLUTION: branch on `git config --get user.signingkey` — sign (`git tag -s -a`) when present, else annotated (`git tag -a`). Signing is a capability to detect, not assume |

The rows above are plan assertions that looked like decisions but were unverified guesses — each "fails" in the sense that asserting it without verification is the failure mode; the *Lesson Learned* column now carries the EXACT command that resolves each one at plan time. Two further source-trust failure modes (not version-assertion guesses, but plan-quality risks):

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting issue-body evidence over the live repo | Issue #189 claimed `[Unreleased]` was empty and cited commits `b52a678`, `9d29e37`, `41ac0b8` as "adding significant features" | Live `CHANGELOG.md:8-50` is richly populated (contradicting "empty") and those SHAs are ABSENT from `git log`. R0 silently routed around the phantom evidence and solved a different problem instead of flagging the contradiction | RESOLUTION: when issue evidence contradicts the live repo, STATE the contradiction explicitly and cite the live `file:line`. Verify with `git log --oneline -5` and by reading the cited file (`git cat-file -e <sha>` to confirm a SHA exists). Don't silently route around it |
| Copying a third-party action SHA from a skill | Pinned `softprops/action-gh-release@de2c0eb…` (v0.1.15) straight from the team skill | The SHA came from a stored skill, not a fresh lookup — skill-carried SHAs go stale (outdated or yanked) | RESOLUTION: re-verify at plan time against the published tag — `gh api repos/<owner>/<repo>/git/ref/tags/<vX.Y.Z>` |
| Cross-artifact self-contradiction: the plan shipped a file AND a test that disagreed | R1 told the implementer to write the CHANGELOG footer as `[Unreleased]: …/commits/main`, but the SAME plan's `release.test.sh` test #3 asserted the footer matched `compare/…HEAD` | The prescribed footer FAILS the prescribed test — the plan literally cannot execute as written; the implementer is forced to pick between two stated "facts". This is a NOGO even with ZERO external/factual errors, because the artifact is internally inconsistent (plan-vs-plan, not plan-vs-repo) | RESOLUTION/LESSON: whenever a plan authors BOTH a producer (file/edit) and its validator (test/grep/regex), state them in ONE canonical form and cross-check in the plan — show the exact string and the exact regex side by side and confirm a verbatim match. A reviewer will grep one against the other. Add a planning self-check: "for every assertion in a generated test, does the generated artifact it checks satisfy it verbatim?" |
| Phantom v-tag compare footer vs bare commits-URL for a never-tagged repo | Iterations oscillated between `compare/v0.1.0...HEAD` (404 — no such tag) and `…/commits/main` (valid but didn't match the `compare/…HEAD` convention the test/skill expected) | "Valid URL" and "matches the team-convention regex" are TWO separate requirements — the phantom v-tag link satisfies neither (404s); the bare commits-URL satisfies validity but not the convention | RESOLUTION: use the repo ROOT commit as the compare base — `git rev-list --max-parents=0 HEAD` (Odysseus root = `b10bfdd`). `…/compare/<root-sha>...HEAD` is a valid non-404 URL for any reachable ref, needs no tag, AND fits a `compare/…HEAD` regex. Make the regex tolerant of both the SHA base now and a `vX.Y.Z` base later: `compare/[0-9a-fv.]+\.\.\.HEAD`. Pair with a SEPARATE assertion that rejects phantom v-tag links (`releases/tag/v[0-9]\|compare/v[0-9]` must be absent) — the root-SHA base (no `v` prefix) does not trip it. Design the positive-form and negative-phantom assertions so they cannot conflict |
| `tomllib` for TOML version parsing (Mnemosyne #2913, plan-time rejection) | The plan initially reached for `tomllib` to parse `pixi.toml`/`pyproject.toml` versions | pixi env floor is python >=3.9; `tomllib` is stdlib only on 3.11+ → local `pixi run` would `ModuleNotFoundError` | On a py<3.11 floor, use an anchored `[project]`-table regex (or add `tomli`) — decide from the target repo's floor, not the CI runner's version |
| Requiring a `## [<manifest-version>]` CHANGELOG section in DRY-RUN mode (Mnemosyne #2913, plan-time rejection) | The dry-run guard would have asserted a `## [2.1.0]` section exists in the bootstrapped CHANGELOG | manifest version 2.1.0 was never shipped; the guard's own live-tree acceptance test would fail on day one | Dry-run asserts only `[Unreleased]` + resolvable footer refs; the version-section requirement belongs to publish (`--tag`) mode only (guard-scope-on-shipped-tree) |
| Third-party release action (softprops etc.) for the publish step (Mnemosyne #2913, plan-time rejection) | Considered pinning a third-party GitHub-release action for the tag-triggered publish job | Stale/copied action SHAs are a known planning trap and add an unpinned trust surface | `gh release create` with `${{ github.token }}` — no new pinned action needed |

## Results & Parameters

This skill produced no execution results (it is `unverified`). What it produces is a reconciliation checklist, the **resolution commands** that close each R0 finding at plan time, a two-mode consistency-script sketch, and the `_required.yml` required-check wiring snippet.

**Resolution commands cheat-sheet — the exact command that resolves each R0 risk at PLAN time:**

```bash
# R1: never-released repo? Both empty => do NOT bump manifest onto a historical CHANGELOG entry.
git tag --list 'v*' --sort=-v:refname
gh release list

# R2: CHANGELOG footer for a NEVER-TAGGED repo — use the ROOT commit as compare base.
ROOT_SHA=$(git rev-list --max-parents=0 HEAD)        # Odysseus root = b10bfdd
# Footer: [Unreleased]: https://github.com/<slug>/compare/${ROOT_SHA}...HEAD
grep -qE "compare/[0-9a-fv.]+\.\.\.HEAD" CHANGELOG.md            # positive: MUST match
grep -qE "releases/tag/v[0-9]|compare/v[0-9]" CHANGELOG.md \
  && echo "PHANTOM v-tag -> NOGO" || echo "OK"                  # negative: phantom v-tag absent

# R3: two-mode consistency guard (see script sketch below).
python scripts/check_version_consistency.py            # pre-commit: manifest parses + declares a version
python scripts/check_version_consistency.py --expect 0.2.0   # release: tag == pixi == top CHANGELOG

# R4: required-check wiring — gate must attach to an EXISTING required job, contexts unchanged.
grep -nE 'name: (deps/version-sync|unit-tests)' .github/workflows/_required.yml
grep -n 'check_version_consistency' .github/workflows/_required.yml

# R5: signed-tag must degrade gracefully — detect, don't assume.
git config --get user.signingkey   # set => git tag -s -a ; unset => git tag -a

# Source-trust: confirm cited SHAs exist; re-verify pinned action SHAs.
git log --oneline -5
git cat-file -e <cited-sha> && echo EXISTS || echo "ABSENT -> flag in plan"
gh api repos/<owner>/<repo>/git/ref/tags/<vX.Y.Z>      # re-verify a skill-carried action SHA
```

**Version reconciliation checklist — tags vs releases vs manifest (do all three before choosing a target version):**

```bash
# 1. Real tags (sorted newest-first)
git tag --list 'v*' --sort=-v:refname

# 2. Real published releases
gh release list --limit 50

# 3. Manifest's declared version
grep -nE '^\s*version\s*=' pixi.toml

# 4. CHANGELOG's claimed sections
grep -nE '^## \[' CHANGELOG.md

# Decision: the target version must be reachable from the REAL lineage in (1)+(2),
# not invented from (4). If (1)/(2)/(3)/(4) disagree, the disagreement is the finding.
```

**Compare-URL footer validation (every referenced tag must be a real ref):**

```bash
SLUG=$(git remote get-url origin | sed -E 's#.*github.com[:/](.+/.+)(\.git)?$#\1#; s#\.git$##')
echo "slug=$SLUG"
for t in v0.1.0 v0.1.1 v0.2.0 v0.4.0; do
  git rev-parse --verify "refs/tags/$t" >/dev/null 2>&1 \
    && echo "OK   $t" || echo "MISSING $t  -> https://github.com/$SLUG/compare/...$t will 404"
done
```

**Tagless `[Unreleased]` footer for a NEVER-TAGGED repo (root-SHA compare base):**

A keepachangelog `[Unreleased]` footer needs a compare base, but a never-tagged repo has no `vX.Y.Z` ref. Two wrong answers and the right one:

- WRONG `…/compare/v0.1.0...HEAD` — 404s, the tag does not exist.
- WRONG `…/commits/main` — valid, but does NOT match a `compare/…HEAD` team-convention regex.
- RIGHT `…/compare/<root-sha>...HEAD` — the repo ROOT commit is always a reachable ref, needs no tag, gives a non-404 compare URL, AND fits a `compare/…HEAD` regex.

```bash
SLUG=$(git remote get-url origin | sed -E 's#.*github.com[:/](.+/.+)(\.git)?$#\1#; s#\.git$##')
ROOT_SHA=$(git rev-list --max-parents=0 HEAD)        # Odysseus root = b10bfdd
echo "[Unreleased]: https://github.com/$SLUG/compare/${ROOT_SHA}...HEAD"

# Positive assertion — tolerant of a SHA base NOW and a vX.Y.Z base LATER:
grep -qE "compare/[0-9a-fv.]+\.\.\.HEAD" CHANGELOG.md     # MUST match

# Negative assertion — reject phantom v-tag links. The root-SHA base (no 'v'
# prefix) does NOT trip this, so the two assertions cannot conflict:
grep -qE "releases/tag/v[0-9]|compare/v[0-9]" CHANGELOG.md && exit 1 || true
```

"Valid URL" and "matches the team-convention regex" are TWO requirements; the root-SHA compare form satisfies both. Design the positive-form and negative-phantom assertions so the chosen base cannot trip the rejection.

**Producer/validator cross-check checklist (plan-vs-plan internal consistency):**

When a plan authors BOTH a producer (a file/edit) and its validator (a test/grep/regex), the prescribed file MUST satisfy the prescribed test verbatim — or the plan cannot execute as written (a NOGO with zero external errors). Before submitting:

```bash
# State the producer string and the validator regex in ONE place, side by side,
# and prove the string satisfies the regex BEFORE the reviewer greps them apart.
ROOT_SHA=$(git rev-list --max-parents=0 HEAD)
FOOTER="[Unreleased]: https://github.com/<slug>/compare/${ROOT_SHA}...HEAD"   # producer
REGEX="compare/[0-9a-fv.]+\.\.\.HEAD"                                          # validator
echo "$FOOTER" | grep -qE "$REGEX" \
  && echo "OK producer satisfies validator" \
  || { echo "MISMATCH -> internal NOGO"; exit 1; }
```

- For EVERY assertion in a generated test, confirm the generated artifact it checks satisfies it verbatim.
- **Execute the validator against the literal artifact — don't just assert parity.** Run the generated validator against the literal artifact string (`printf '%s' '<artifact>' | grep -E '<test-regex>'`) and record the OBSERVED `PASS` / not-tripped / `MATCH` result in the plan; reviewers grep the artifact against the test and weigh a DEMONSTRATED match above an ASSERTED one. R3 of issue #189 closed the residual reviewer request precisely this way — running the CHANGELOG footer through test #3 (positive), test #4 (phantom-rejection: not tripped), and the verification grep, then pasting the three observed results to prove character-for-character agreement rather than merely claiming it.
- The R1 failure: footer written as `…/commits/main` but test #3 asserted `compare/…HEAD` — the prescribed file failed the prescribed test. A reviewer greps one against the other; so must the author.
- This is a DIFFERENT axis from issue-vs-reality (plan-vs-repo). It is plan-vs-plan: the plan contradicting itself.

**`tomllib` fallback snippet (Python < 3.11 safe):**

```python
try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]  # add `tomli` to dev deps
```

**`[workspace]` vs `[project]` table detection (don't assume the pixi table name):**

```python
with open("pixi.toml", "rb") as f:
    data = tomllib.load(f)

# Read whichever table the target file actually uses.
for table in ("workspace", "project"):
    if table in data and "version" in data[table]:
        version = data[table]["version"]
        break
else:
    raise SystemExit(
        "pixi.toml: no [workspace].version or [project].version found "
        "(do not hard-index one table name)"
    )
```

**Signing-key pre-flight + graceful degrade (detect the key; do not hard-call `git tag -s`):**

```bash
# Detect the capability and branch on it — sign when a key exists, annotate otherwise.
if [ -n "$(git config --get user.signingkey)" ]; then
  git tag -s -a "v$VERSION" -m "Release v$VERSION"     # signed annotated
else
  git tag -a    "v$VERSION" -m "Release v$VERSION"     # annotated, unsigned (document the gap)
fi
# Pre-commit signs COMMITS, not tags; no signing key is assumed in CI.
```

**Two-mode consistency guard (`check_version_consistency.py`) — strict invariant only at release time:**

```python
# default / pre-commit mode: manifest parses AND declares a version (no cross-file equality)
#   $ python scripts/check_version_consistency.py
# release-time mode: tag == pixi.toml == top dated CHANGELOG section, all equal VERSION
#   $ python scripts/check_version_consistency.py --expect 0.2.0
import argparse, re, sys
try:
    import tomllib
except ImportError:                       # Python < 3.11
    import tomli as tomllib               # add `tomli` to dev deps

def manifest_version(path="pixi.toml"):
    with open(path, "rb") as f:
        data = tomllib.load(f)
    for table in ("workspace", "project"):           # don't hard-index one table name
        if table in data and "version" in data[table]:
            return data[table]["version"]
    sys.exit("pixi.toml: no [workspace].version or [project].version found")

def top_changelog_version(path="CHANGELOG.md"):
    for line in open(path):
        m = re.match(r"^## \[(\d+\.\d+\.\d+)\]", line)   # skip [Unreleased]
        if m:
            return m.group(1)
    return None

ap = argparse.ArgumentParser()
ap.add_argument("--expect")              # release-time three-way match; absent => pre-commit mode
args = ap.parse_args()

mv = manifest_version()                   # both modes: the manifest must parse + declare a version
if not args.expect:
    print(f"OK pre-commit: manifest declares version {mv}")
    sys.exit(0)

cv = top_changelog_version()
if not (args.expect == mv == cv):
    sys.exit(f"version mismatch: --expect={args.expect} pixi={mv} changelog={cv}")
print(f"OK release: tag/pixi/changelog all == {args.expect}")
```

**`_required.yml` wiring — attach the gate to an EXISTING required job; never add a new job to a non-required workflow:**

```yaml
# .github/workflows/_required.yml  — job `name:` values ARE the ruleset-pinned status contexts.
# Do NOT rename a job `name:` (that breaks the pinned context + needs rulesets re-applied).
# Do NOT add a standalone `release-contract-test` job to ci.yml (silently non-blocking).
jobs:
  version-sync:
    name: deps/version-sync          # <-- ruleset context "Required Checks / deps/version-sync"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<pinned-sha>
      - name: version consistency (pre-commit mode)
        run: python scripts/check_version_consistency.py     # ADDED step, name unchanged
  unit-tests:
    name: unit-tests                 # <-- ruleset context "Required Checks / unit-tests"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<pinned-sha>
      - name: CHANGELOG footer regression (no nonexistent refs)
        run: test "$(grep -c 'releases/tag/v\|compare/v0' CHANGELOG.md)" -eq 0   # ADDED step
```

Proof the wiring is correct: `grep -nE 'name: (deps/version-sync|unit-tests)' .github/workflows/_required.yml` (contexts unchanged) and `grep -n 'check_version_consistency' .github/workflows/_required.yml` (step present in a required job). Required-check status is conferred by the job `name:` being pinned in `configs/github/*ruleset*.json`, not by the test existing somewhere in CI.

**Reviewer focus list (the risks, condensed):** (1) target version reconciled against real tags + Releases — never-released repo => no historical-CHANGELOG bump; (2) every compare-URL/tag footer ref is a real ref — never-tagged repo uses the root-SHA compare base (`compare/<root-sha>...HEAD`), no phantom v-tag; (3) two-mode consistency guard (strict three-way only at tag push); (4) `[workspace]` vs `[project]` table + Python 3.11+/`tomllib` availability; (5) new gates wired into existing `_required.yml` jobs (contexts unchanged), not a standalone job in a non-required workflow; (6) signing-key detected and degraded gracefully, never hard-called; (7) producer/validator cross-check — every prescribed file satisfies the prescribed test that checks it verbatim (plan-vs-plan consistency, distinct from plan-vs-repo).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #189 R0→R3 planning cycle (plan-only) | this file |
| Mnemosyne | Issue #2913 plan — canonical release check bootstrap (plan-only) | this file |

## Related Skills

- `gha-release-package-workflow-patterns` — the *implementation mechanics* of release.yml, keepachangelog, manifest consistency, signed tags (verified-ci). This skill is the planning-risk counterpart.
- `lockfile-and-release-pipeline-management` — lockfile recovery and release-pipeline mechanics.
- `release-tag-drift-recut-on-fixed-commit` — fixing a tag that drifted from the intended commit.
- `security-md-version-sync-planning-gaps` — adjacent planning-gap pattern for version sync.
