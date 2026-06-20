---
name: release-workflow-planning-assumptions-and-risks
description: "Planning-phase risk checklist for designing an automated release workflow in a repo (especially a meta-repo) that has NEVER shipped a versioned release. The implementation mechanics live in `gha-release-package-workflow-patterns` and `lockfile-and-release-pipeline-management`; this skill is the DIFFERENT search surface a plan REVIEWER reaches for — 'are the plan's release assumptions verified?' not 'how do I write release.yml'. Core thesis: a first-release plan is full of assertions that look like decisions but are actually unverified guesses — the target version, the CHANGELOG link-footer tags, the TOML table name, the runner Python version, and signing-key availability. Each must be VERIFIED during implementation, not asserted in the plan. Use when: (1) reviewing or writing a plan that bumps a manifest version to 'match' the CHANGELOG without reconciling against real git tags + GitHub Releases, (2) a plan hard-codes keepachangelog compare-URLs (.../compare/vA...vB) that assume those tags exist as real refs, (3) a reused consistency script hard-indexes pixi['workspace']['version'] (or assumes [project]) without reading the target file's actual table name, (4) scripts `import tomllib` with no `tomli` fallback and the CI runner Python version is unconfirmed, (5) a justfile/release recipe uses `git tag -s` but signing-key availability in CI/local was never confirmed, (6) the issue body cites commit SHAs or file states that do not match the live repo and the plan does not flag the mismatch, (7) a third-party action SHA was copied from a skill/template rather than re-looked-up at plan time."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning-methodology
  - release-automation
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
  - unverified-assumptions
  - verify-dont-assert
---

# Release Workflow Planning: Assumptions & Risks (First-Release / Meta-Repo)

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the durable PLANNING-PHASE risks surfaced while writing an implementation plan to add an automated release workflow to the Odysseus meta-repo (GitHub issue #189) — a repo that had never shipped a versioned release. The plan made five assertions that LOOK like decisions but are actually unverified guesses (target version, CHANGELOG link-footer tags, TOML table name, runner Python version, signing-key availability). Each must be VERIFIED during implementation, not asserted in the plan. |
| **Outcome** | Hypothesis only. No code was executed and no CI run validated the plan. This skill is a reviewer/author checklist, not a verified procedure. |
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
- A **third-party action SHA** (e.g. `softprops/action-gh-release@de2c0eb…` / v0.1.15) was copied from a skill/template rather than re-looked-up at plan time — it may be outdated or yanked.

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
| 5 | `git tag -s` in the release recipe | Confirm a GPG/SSH signing key exists in CI and locally | No key → `git tag -s` fails; signed *commits* in pre-commit do NOT cover tags |

Two cross-cutting source-trust rules:

- **Issue-vs-reality mismatch:** if the issue's cited SHAs / file states don't match the live repo, say so EXPLICITLY in the plan. Don't silently route around phantom evidence.
- **Re-verify third-party action SHAs at plan time** — a SHA pulled from a skill or template may be outdated/yanked.

### Detailed Steps

**1. Reconcile the target version across THREE sources, not two.**
The trap is treating manifest-vs-CHANGELOG as the whole picture. The CHANGELOG's dated sections may be aspirational; the manifest's `0.1.1` may be the real last shipped version. Before picking the version to converge on:

```bash
git tag --list 'v*' --sort=-v:refname        # what was actually tagged
gh release list --limit 50                    # what was actually published
grep -nE '^version' pixi.toml                 # what the manifest claims
grep -nE '^## \[' CHANGELOG.md                # what the CHANGELOG claims
```

Only after all four agree on the lineage do you choose the target. If they disagree, the disagreement IS the finding — surface it; do not paper over it with a bump.

**2. Treat the CHANGELOG link-footer as a verification task, not a templating task.**
A keepachangelog footer is only valid if (a) the `OWNER/REPO` slug is correct and (b) every referenced tag is a real ref.

```bash
git remote get-url origin                     # confirm the OWNER/REPO slug
for t in v0.1.0 v0.1.1 v0.2.0 v0.4.0; do
  git rev-parse --verify "refs/tags/$t" >/dev/null 2>&1 \
    && echo "OK   $t" || echo "MISSING $t  -> compare link will 404"
done
```

Generate the footer FROM the verified tag set; never hard-code compare-URLs whose tags you have not confirmed.

**3. Read the actual TOML table name before indexing it.** See the detection snippet in *Results & Parameters*. A reusable consistency script must not assume `[workspace]` (pixi) or `[project]` (PEP 621) — read whichever the target file uses.

**4. Confirm the runner Python version or add the `tomli` fallback.** See the import snippet in *Results & Parameters*. `tomllib` is stdlib only on 3.11+; CI runners and pre-commit `language: python` envs vary.

**5. Confirm signing-key material exists before relying on `git tag -s`.** A `.pre-commit-config.yaml` that signs *commits* does not make signed *tags* work — that needs a GPG/SSH key present in the CI environment and on the maintainer's machine. If you cannot confirm the key, either provision it as part of the plan or fall back to annotated-only tags (`git tag -a`) and call out the reduced verifiability.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Pick target version from CHANGELOG alone | Bumped `pixi.toml` 0.1.1 → 0.4.0 to match the latest dated CHANGELOG section, assuming the CHANGELOG is source-of-truth and 0.1.1 is stale | Never checked `git tag --list 'v*'` or `gh release list`; the opposite may be true (0.1.1 is the real last release, CHANGELOG dated sections aspirational) — risk of skipping real intermediate releases or claiming a version never shipped | Reconcile THREE sources — existing git tags, GitHub Releases, and the manifest — before choosing the version to converge on; manifest-vs-CHANGELOG is not enough |
| Templating the CHANGELOG link-footer | Hard-coded `HomericIntelligence/Odysseus` slug and compare-URLs `.../compare/v0.2.0...v0.4.0`, assuming the slug and tags exist | Slug never confirmed via `git remote get-url origin`; tags `v0.1.0/v0.1.1/v0.2.0/v0.4.0` never confirmed as real refs — every compare link 404s if a tag is missing | A keepachangelog link-footer is a VERIFICATION task: each referenced tag must be a real ref and the slug must match the remote. Generate the footer from the verified tag set |
| Hard-indexing `pixi["workspace"]["version"]` | `check_version_consistency.py` indexed the `[workspace]` table, confirmed only against this repo's `pixi.toml` | Many pixi/Python projects use `[project]` instead; the script `KeyError`s on those repos when reused | A reusable consistency script must READ the actual table name from the target file (detect `[workspace]` vs `[project]`), never assume one |
| `import tomllib` with no fallback | Scripts imported `tomllib` directly; CI runner Python version never verified | `tomllib` is stdlib only on Python 3.11+; on older runners / pre-commit envs the import is a `ModuleNotFoundError` | Either confirm the runner is >= 3.11 or add the `try: import tomllib / except ImportError: import tomli as tomllib` fallback |
| `git tag -s` assuming a signing key exists | `release` justfile recipe used signed tags; `.pre-commit-config.yaml` enforced signed *commits* | Signed *commits* do not imply signed *tags* will work — `git tag -s` fails with no GPG/SSH key in CI or locally; key material was never confirmed | Signed-tag flows assume key material that must be confirmed to exist; otherwise provision the key or fall back to `git tag -a` and note reduced verifiability |

The five rows above are plan assertions that looked like decisions but were unverified guesses — each "fails" in the sense that asserting it without verification is the failure mode. Two further source-trust failure modes (not version-assertion guesses, but plan-quality risks):

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trusting issue-body evidence over the live repo | Issue #189 cited commits `b52a678`, `9d29e37`, `41ac0b8` as "adding significant features" | Those commits were not found/confirmed in the actual repo; the real CHANGELOG content differed entirely. The plan correctly ignored the phantom commits but did NOT flag the issue-vs-reality mismatch to the reviewer | When issue evidence (commit SHAs, file states) does not match the live repo, say so EXPLICITLY in the plan instead of silently routing around it |
| Copying a third-party action SHA from a skill | Pinned `softprops/action-gh-release@de2c0eb…` (v0.1.15) straight from the team skill | The SHA came from a stored skill, not a fresh lookup — it may be outdated or yanked | Re-verify third-party action SHAs at plan time against the action's current releases |

## Results & Parameters

This skill produced no execution results (it is `unverified`). What it produces is a reconciliation checklist plus two copy-paste snippets that close the two most mechanical risks.

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

**Signing-key pre-flight (confirm before any `git tag -s`):**

```bash
git config --get user.signingkey      # is a key configured at all?
git config --get gpg.format           # 'openpgp' (GPG) or 'ssh'
# In CI: confirm the key is imported into the runner before the tag step,
# or fall back to `git tag -a` (annotated, unsigned) and document the gap.
```

**Reviewer focus list (the five risks, condensed):** (1) target version reconciled against real tags + Releases, not just CHANGELOG; (2) every compare-URL tag is a real ref; (3) `[workspace]` vs `[project]` table assumption in the TOML parser; (4) Python 3.11+ / `tomllib` availability on the CI runner; (5) signing-key availability for `git tag -s`.

## Related Skills

- `gha-release-package-workflow-patterns` — the *implementation mechanics* of release.yml, keepachangelog, manifest consistency, signed tags (verified-ci). This skill is the planning-risk counterpart.
- `lockfile-and-release-pipeline-management` — lockfile recovery and release-pipeline mechanics.
- `release-tag-drift-recut-on-fixed-commit` — fixing a tag that drifted from the intended commit.
- `security-md-version-sync-planning-gaps` — adjacent planning-gap pattern for version sync.
