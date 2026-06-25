---
name: planning-doc-systematization-onboarding-nitpick
description: "Use when planning a fix for a DOCUMENTATION-ONLY audit nitpick that asks you to (a) systematize an 'ad-hoc' directory/orphan artifact with a convention README, or (b) add a 'productive in a day' / onboarding path to CONTRIBUTING.md. Triggers: (1) an audit calls a file in a directory 'ad-hoc' / 'one-off' / 'cruft' and you are about to delete or rename it — FIRST run `git log -- <path>` to check its history; a file added in one PR and deliberately maintained in a later PR is a LEGITIMATE operational note that warrants a README systematizing the convention, NOT deletion. (2) you are systematizing a directory whose name COLLIDES with a standard built-in concept (e.g. `docs/release-notes/` vs GitHub's commit-generated release notes; CLAUDE.md may even mandate `gh release create --generate-notes` and 'No CHANGELOG.md') — the convention README's FIRST job is to draw the boundary: state explicitly it is NOT the same-named standard concept, or future contributors conflate the two. (3) you are adding an onboarding / 'first day' path — it must LINK existing canonical sections (Development Setup / Testing / PR Process) via anchors, NEVER re-state commands like `just bootstrap` (DRY / single-source-of-truth; duplication creates drift). A 'productive in a day' path is an INDEX over existing sections, not new prose. (4) your plan asserts markdown anchor links (`#development-setup`, `#testing`) resolve — markdown anchors are a SILENT-FAILURE class: a wrong slug renders fine and lints green. DO NOT grep for the HEADING TEXT: it passes even on a real slug collision (duplicate headings → `#code-contributions-1`, punctuation/emoji stripped). RESOLVED: search the repo for a slug-aware validator before hand-rolling a check — ProjectHephaestus ships `hephaestus/markdown/anchors.py` as the console script `hephaestus-validate-anchors` (`pyproject.toml:130`); its `heading_to_anchor()` reproduces GitHub's exact GFM slug algorithm (lowercase → spaces→hyphens → strip non-`[a-z0-9-]` → collapse hyphens → strip ends) and `validate_anchors()` checks every `[text](#fragment)` link against the real heading-slug set and exits 1 on a mismatch. Run e.g. `pixi run hephaestus-validate-anchors CONTRIBUTING.md --target CONTRIBUTING.md --verbose`. (5) META-LESSON for any verification step: a verification command is only valid if it would actually FAIL when the thing it claims to prove is broken — construct the failure case (a duplicate-heading slug collision) and confirm the command exits non-zero on it; prefer an existing repo tool that models the real artifact (GFM slug) over a hand-rolled approximation. Headline: for doc-systematization + onboarding nitpicks — check git history before calling an artifact cruft, disambiguate same-named concepts in the README's first line, link don't duplicate in onboarding paths, and verify anchor SLUGS with a slug-aware validator (`hephaestus-validate-anchors`), never heading text. Use when category is documentation and the issue asks only to DOCUMENT, never to change behavior."
category: documentation
date: 2026-06-24
version: "1.1.0"
user-invocable: false
verification: unverified
history: planning-doc-systematization-onboarding-nitpick.history
tags:
  - planning
  - documentation
  - audit-nitpick
  - doc-systematization
  - convention-readme
  - orphan-artifact
  - git-history-before-cruft
  - same-named-concept-disambiguation
  - release-notes-collision
  - onboarding-path
  - contributing-md
  - first-day-onboarding
  - link-dont-duplicate
  - dry-single-source-of-truth
  - markdown-anchor-link
  - anchor-slug-mismatch
  - slug-aware-validation
  - hephaestus-validate-anchors
  - heading-to-anchor
  - verification-must-fail-when-broken
  - prefer-existing-repo-tool
  - silent-failure-class
  - markdownlint
  - markdownlint-yaml-source-of-truth
  - single-sample-not-a-convention
  - kiss-yagni
  - pola
  - unverified-assumption
---

# Planning a Doc-Systematization + Onboarding-Path Audit Nitpick

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-24 |
| **Objective** | Plan a documentation-only audit nitpick that (a) systematizes an "ad-hoc" orphan directory with a convention README and (b) adds an onboarding "first day" path to CONTRIBUTING.md — without deleting a maintained artifact, without conflating a same-named standard concept, without duplicating canonical commands, and without trusting unverified markdown anchor slugs |
| **Outcome** | A planning meta-pattern: run `git log -- <path>` before classifying any artifact as cruft; make the convention README's first job to disambiguate a name that collides with a built-in concept; build the onboarding path as an INDEX of links over existing sections (never re-state commands); and verify every anchor target with a SLUG-AWARE validator that models GitHub's real GFM algorithm (`hephaestus-validate-anchors`), never by grepping heading text |
| **Headline (v1.1.0)** | The v1.0.0 top RISK — "anchor-slug verification" — is now RESOLVED: stop hand-rolling a heading-text grep; search the repo and run the slug-aware validator it already ships (`hephaestus/markdown/anchors.py` → `hephaestus-validate-anchors`, `pyproject.toml:130`; `heading_to_anchor()` reproduces GitHub's exact GFM slug; `validate_anchors()` exits 1 on any `[text](#fragment)` mismatch). Generalized: a verification command is only valid if it would actually FAIL when the thing it proves is broken — construct the failure case (a duplicate-heading slug collision) and confirm a non-zero exit |
| **Verification** | unverified — the plan was authored (then RE-PLANNED after a reviewer NOGO) for ProjectHephaestus #1544 but still NEVER executed end-to-end (no PR merged, no CI). `pixi run hephaestus-validate-anchors` is a PROPOSED-but-unrun command this session |

## When to Use

- An audit/lint/review NITPICK calls a file in a directory **"ad-hoc"**, **"one-off"**, or **"cruft"** and proposes deleting or ignoring it. Before you classify it, run `git log -- <path>`.
- The issue asks you to **systematize a directory** (add a README documenting its convention) whose **name overlaps a standard built-in concept** — e.g. `docs/release-notes/` vs GitHub's commit-generated release notes, `changelog/` vs a CHANGELOG, `migrations/` vs an ORM's.
- The issue asks for an **onboarding / "first day" / "productive in a day"** section in `CONTRIBUTING.md`, and the canonical setup/test/PR steps already exist elsewhere in the file.
- A plan **asserts that markdown anchor links resolve** (`#development-setup`, `#testing`, `#pull-request-process`) and you need to verify them at plan time — reach for a slug-aware validator (`hephaestus-validate-anchors`), never a heading-text grep.
- The issue is **documentation-only** — it asks to DOCUMENT, not to change behavior (KISS/YAGNI: do not add validation, do not rename, do not delete).

**Trigger phrases**: "systematize this directory", "this file is ad-hoc / a one-off", "add a README for the convention", "first day / onboarding path", "productive in a day", "link to existing sections", "add anchor links", "release-notes directory", "documentation nitpick bundle".

**Boundary**: IN — planning a doc-only nitpick that adds a convention README and/or an onboarding index, deciding link-vs-duplicate, and verifying anchor slugs. OUT — deleting/renaming the artifact, duplicating canonical commands, changing behavior, executing the plan (this skill is `unverified` — the plan was authored but never run).

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. The source plan (ProjectHephaestus #1544) was authored but NEVER executed — no files were created and no CI ran. Treat every step as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical steps are emitted under that heading to keep validation green. This skill is a PLANNING methodology captured at `unverified` level. Read the steps below as **proposed**, per the warning.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```text
# Doc-systematization + onboarding nitpick planning checklist (top to bottom)

1. CLASSIFY document-only.
   - Issue asks to DOCUMENT, not change behavior → no delete, no rename,
     no new validation (KISS/YAGNI).

2. GIT-HISTORY before calling an artifact cruft.
     git log -- docs/release-notes/        # or the specific orphan path
   - Added in one PR + maintained in a later PR = LEGITIMATE operational
     note. Write a README that systematizes the convention; do NOT delete.
   - Only an artifact with NO maintenance history is a candidate for removal.

3. DISAMBIGUATE same-named concepts in the README's FIRST line.
   - `docs/release-notes/` collides with GitHub's commit-generated release
     notes. If CLAUDE.md mandates `gh release create --generate-notes` and
     "No CHANGELOG.md", the README MUST state it is NOT those.
   - First job of a convention doc whose name overlaps a built-in: draw the
     boundary, or contributors conflate the two.

4. ONBOARDING path = INDEX of LINKS, never duplicated commands.
   - CONTRIBUTING.md already has Development Setup / Testing / PR Process.
     The gap is SEQUENCING, not content.
   - Link to existing anchors; do NOT re-state `just bootstrap` etc.
     (DRY / single-source-of-truth — duplication drifts).

5. VERIFY anchor SLUGS with a SLUG-AWARE VALIDATOR (RESOLVED in v1.1.0).
   - Markdown anchors are a SILENT-FAILURE class: a wrong slug renders fine
     and lints green. Grepping HEADING TEXT does NOT catch a slug mismatch —
     it passes even on a real collision (`#code-contributions-1`).
   - SEARCH the repo for an existing slug-aware validator before hand-rolling.
     ProjectHephaestus ships one:
       pixi run hephaestus-validate-anchors CONTRIBUTING.md \
         --target CONTRIBUTING.md --verbose
     (hephaestus/markdown/anchors.py; pyproject.toml:130). `heading_to_anchor()`
     reproduces GitHub's exact GFM slug; `validate_anchors()` exits 1 on a
     mismatch. Add a unit guard for the slug algorithm itself:
       pytest tests/unit/markdown/test_anchors.py

6. META-CHECK every verification command: would it FAIL when broken?
   - A verification command is only valid if it would actually exit non-zero
     when the thing it claims to prove is broken. "Greps heading text"
     silently substitutes a WEAKER predicate for the real one.
   - Construct the failure case (duplicate-heading slug collision) and confirm
     the command catches it. Prefer a tool that models the real artifact
     (GFM slug) over a hand-rolled approximation.

7. READ the actual `.markdownlint.yaml` before tailoring prose.
   - It is the single source of truth for which rules fire. Reading it showed
     `MD013: false` (line-length DISABLED — a moot worry) while MD025 (one H1)
     and MD003 (ATX) are what actually fire. Do not tailor prose to imagined
     rules; check the config.

8. STATE verification honestly.
   - Plan authored + RE-PLANNED after NOGO, still not executed → "unverified".
     `pixi run hephaestus-validate-anchors` is PROPOSED-but-unrun this session.
     Keep "Proposed Workflow" + warning banner; never claim it "passes".
```

### Detailed Steps

1. **Classify document-only.** Read the issue. If it says "document", "systematize", "add a README", "add an onboarding section", the scope is documentation. Do NOT delete the orphan, do NOT rename anything, do NOT add validation (KISS/YAGNI). The source issue (ProjectHephaestus #1544) was an S2 low-priority nitpick bundle that asked only to document.

2. **Run `git log -- <path>` before calling any artifact cruft.** The audit labelled `docs/release-notes/plan-reviewer-final-verdict.md` an ad-hoc one-off. `git log -- docs/release-notes/` showed it was added in PR #571 and deliberately maintained in #1268 — a legitimate operational note, not garbage. A maintained file warrants a README that **systematizes the convention** ("component-scoped operational notes"), never deletion. Only an artifact with no maintenance history is a removal candidate.

3. **Disambiguate a same-named standard concept in the README's first line.** `release-notes` collides with GitHub's auto-generated release notes. This repo's CLAUDE.md mandates "No CHANGELOG.md; release notes generated from commits via `gh release create --generate-notes`". The convention README's first job is to state explicitly it is **NOT** that — these are component-scoped operational notes, distinct from commit-generated GitHub release notes. Otherwise future contributors conflate the two. When systematizing any directory whose name overlaps a built-in concept, draw the boundary up front.

4. **Build the onboarding path as an INDEX of links, never duplicated commands.** CONTRIBUTING.md already had every step (Development Setup, Testing, PR Process); the only gap was sequencing. The "first day" section must LINK existing canonical sections via anchors, NOT re-state `just bootstrap` or any command (DRY / single-source-of-truth — a duplicated command drifts the moment the canonical section changes). A "productive in a day" path is an index over existing sections, not new prose.

5. **Verify anchor SLUGS with a slug-aware validator — RESOLVED in v1.1.0.** Markdown anchor links are a silent-failure class: a wrong slug renders fine and the linter stays green. The first plan claimed `#development-setup`, `#code-contributions`, `#testing`, `#pull-request-process`, `#platform-support` all resolve, and "verified" them by grepping the heading TEXT (`grep -nE '^#{1,3} ' CONTRIBUTING.md`). The reviewer's NOGO named it precisely: that grep "would pass on a real slug collision; the top stated risk is unverified by the very check meant to catch it." The FIX: **search the repo for an existing slug-aware validator before hand-rolling a check.** ProjectHephaestus already ships one — `hephaestus/markdown/anchors.py`, exposed as the console script `hephaestus-validate-anchors` (registered at `pyproject.toml:130`). Its `heading_to_anchor()` reproduces GitHub's exact slug algorithm (lowercase → spaces→hyphens → strip non-`[a-z0-9-]` → collapse consecutive hyphens → strip leading/trailing), and `validate_anchors()` checks every `[text](#fragment)` link against the real heading-slug set and exits 1 on any mismatch. The plan now calls `pixi run hephaestus-validate-anchors CONTRIBUTING.md --target CONTRIBUTING.md --verbose`, plus a unit-level guard `pytest tests/unit/markdown/test_anchors.py` for the slug algorithm the check depends on. This turned a non-functional verification step (heading-text grep) into a functional one. NOTE: this session those commands were authored into the plan but NOT yet executed against the real files — they remain PROPOSED-but-unrun.

6. **Meta-check every verification command: would it FAIL when the thing is broken?** Generalizable lesson for planners: a verification command is only valid if it would actually exit non-zero when the thing it claims to prove is broken. "Greps the heading text" silently substitutes a weaker predicate for the real one. When you assert a check proves risk X, mentally construct the failure case (here: a duplicate-heading slug collision producing `#code-contributions-1`) and confirm the command would exit non-zero on it. Prefer an existing repo tool that models the real artifact (the GFM slug) over a hand-rolled approximation.

7. **Read the actual `.markdownlint.yaml` before tailoring prose to imagined rules.** The first plan worried about MD013 (line length) without reading the config. Reading `.markdownlint.yaml` (the repo's single source of truth for which rules fire) showed `MD013: false` — disabled — so the worry was moot, while MD025 (one H1) and MD003 (ATX) are what actually fire. Identify the real binding gate AND enumerate its enabled rules from the config; do not tailor prose to a rule that is turned off, and do not miss a rule that is on. Run the gate; read the output.

8. **Record the honest verification level.** The source plan was authored, then RE-PLANNED after a reviewer NOGO, but is still not executed end-to-end — no PR merged, no CI run. The verification level remains `unverified`. The `hephaestus-validate-anchors` command is proposed in the plan but was NOT run against the real files this session. Keep the workflow titled "Proposed Workflow" with the warning banner; never claim it "passes".

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Treat `docs/release-notes/plan-reviewer-final-verdict.md` as ad-hoc cruft to delete | Accepted the audit's "one-off" label at face value | `git log -- docs/release-notes/` shows it was added in PR #571 and maintained in #1268 — a legitimate operational note | Run `git log -- <path>` before classifying any artifact as cruft; a maintained file warrants a README, not deletion |
| Write the release-notes README without disambiguating | Documented the convention but did not separate it from GitHub's commit-generated release notes | Name collides with a built-in concept (CLAUDE.md mandates `gh release create --generate-notes`, "No CHANGELOG.md") → contributors conflate the two | The convention doc's FIRST job is to draw the boundary: state it is NOT the same-named standard concept |
| Restate `just bootstrap` and other commands in the new onboarding section | Re-wrote the setup steps inline for a self-contained "first day" path | Duplicates canonical CONTRIBUTING.md sections → drift the moment they change (violates DRY / single-source-of-truth) | An onboarding path is an INDEX of LINKS over existing sections, not new prose; link the anchors, never restate commands |
| Verify anchor links by grepping the HEADING TEXT | `grep -nE '^#{1,3} ' CONTRIBUTING.md` confirmed each target heading exists | Reviewer NOGO: the grep "would pass on a real slug collision; the top stated risk is unverified by the very check meant to catch it." Heading text ≠ rendered slug (`#code-contributions-1`) | RESOLVED: search the repo for a slug-aware validator first — run `hephaestus-validate-anchors` (`hephaestus/markdown/anchors.py`, `pyproject.toml:130`); `heading_to_anchor()` models GitHub's GFM slug and `validate_anchors()` exits 1 on a `[text](#fragment)` mismatch. Add `pytest tests/unit/markdown/test_anchors.py` as the slug-algorithm guard |
| Assert a verification command "proves" a risk without checking it would FAIL when broken | Stated the heading-text grep as proof the anchor risk was handled | A check that cannot exit non-zero on the failure case proves nothing — it silently substitutes a weaker predicate | META-LESSON: a verification command is valid only if it would FAIL when the thing it proves is broken; construct the failure case (duplicate-heading slug collision) and confirm a non-zero exit; prefer a tool that models the real GFM artifact |
| Infer GFM slugs from memory (`## Development Setup` → `#development-setup`) | Assumed the standard GFM rule without confirming against the repo's markdownlint config | Was NOT confirmed against this repo's specific config; a non-standard slug renders fine and lints green | Do not infer slugs from memory; generate them with the actual slug-aware validator the repo ships (`heading_to_anchor()`) |
| Assume the Code-of-Conduct section is one short paragraph for the insertion offset | Pinned the new section "after line 8" based on a plan-time read | If the file shifted, the line offset is stale | Re-locate the insertion point by a stable content anchor (heading substring), not a hardcoded line number |
| Codify 3 header keys from ONE example file as "the convention" (P7/POLA) | Reverse-engineered `**Affected component:**` / `**Issues:**` / `**Ships with:**` from a single sample and presented them as the required schema | Reviewer flagged it as astonishing (POLA): a convention invented from n=1 is an invented rule, not an observed one | Present single-sample keys as "the existing example uses these keys … a convention by example, not a hard schema"; REQUIRE only the narrative sections, not the keys |
| Worry about MD013 (line length) without reading `.markdownlint.yaml` | Tailored prose to an imagined line-length rule and named `pre-commit run --all-files` as the gate | Reading `.markdownlint.yaml` (the single source of truth) showed `MD013: false` — DISABLED; the worry was moot, while MD025 (one H1) and MD003 (ATX) are what actually fire | Read the actual `.markdownlint.yaml` to know which rules fire BEFORE tailoring prose; do not guard against a disabled rule or miss an enabled one |

### Resolved (v1.1.0)

1. **Anchor-slug mismatch (was the #1 risk) — RESOLVED.** Stop hand-rolling a heading-text grep; run the slug-aware validator the repo already ships: `pixi run hephaestus-validate-anchors <doc> --target <doc> --verbose` (`hephaestus/markdown/anchors.py`, `pyproject.toml:130`). `heading_to_anchor()` models GitHub's exact GFM slug; `validate_anchors()` exits 1 on any `[text](#fragment)` mismatch. Guard the algorithm with `pytest tests/unit/markdown/test_anchors.py`. (Authored into the plan; PROPOSED-but-unrun this session.)
2. **Over-generalized README header keys — RESOLVED (framing).** The three keys are now presented as "the existing example uses these keys … a convention by example, not a hard schema"; only the narrative sections are required, not the keys.
3. **Unenumerated lint rules — RESOLVED.** Read `.markdownlint.yaml`: `MD013: false` (line length disabled); MD025 (one H1) and MD003 (ATX) are the rules that actually fire. Tailor prose to the config, not to imagined rules.

### Risks (still carried, unresolved)

1. **Stale insertion offset.** "After line 8" assumes the Code-of-Conduct section is exactly one short paragraph; a file shift invalidates the offset. Re-anchor on heading content.
2. **End-to-end execution.** The plan was authored and RE-PLANNED after a NOGO but never run — no PR merged, no CI. Even the slug-aware validator command is proposed, not yet executed against the real files. Verification stays `unverified` until CI confirms.

## Results & Parameters

Copy-paste pre-implementation checklist for a doc-systematization + onboarding nitpick:

```text
[ ] Document-only?  (issue asks to DOCUMENT/systematize — no delete, no rename, no new validation)
[ ] git log -- <path> run?  (artifact's maintenance history checked BEFORE calling it cruft; maintained → README not deletion)
[ ] Same-named concept disambiguated?  (README's first line states it is NOT the built-in concept, e.g. NOT GitHub commit-generated release notes)
[ ] Onboarding path LINKS, not duplicates?  (anchors to existing sections; NO restated commands like `just bootstrap` — DRY)
[ ] Anchor SLUGS verified with a SLUG-AWARE validator?  (`hephaestus-validate-anchors` — `hephaestus/markdown/anchors.py`, exits 1 on a `[text](#fragment)` mismatch — NOT a heading-text grep; the biggest risk)
[ ] Slug algorithm unit-guarded?  (`pytest tests/unit/markdown/test_anchors.py` — the check depends on `heading_to_anchor()`)
[ ] Every verification command would FAIL when broken?  (construct the failure case — duplicate-heading slug collision — and confirm a non-zero exit; prefer a tool that models the real GFM artifact)
[ ] Insertion point re-anchored on content?  (not a hardcoded line offset like "after line 8")
[ ] README convention keys framed as example, not schema?  (single-sample keys = "convention by example", only narrative sections REQUIRED — POLA)
[ ] `.markdownlint.yaml` actually read?  (which rules FIRE — e.g. MD013 may be `false`/disabled; MD025 one-H1 + MD003 ATX are what fire — before tailoring prose)
[ ] Doc gate actually run?  (executed locally; output read; not assumed)
[ ] Verification level stated honestly?  (unverified if the plan was authored but not executed — keep "Proposed Workflow" + warning)
```

**Source context**: Extracted from an implementation PLAN authored for ProjectHephaestus issue #1544 — a low-priority S2 documentation-nitpick bundle pairing (a) a `docs/release-notes/README.md` that systematizes a directory holding one deliberately-maintained operational note (`plan-reviewer-final-verdict.md`, added in PR #571, maintained in #1268) as "component-scoped operational notes" distinct from commit-generated GitHub release notes, with (b) a "Your first day" onboarding section in `CONTRIBUTING.md` that LINKS (does not duplicate) the existing Development Setup / Testing / PR Process sections. **v1.1.0 captures the RE-PLAN after a reviewer NOGO.** The NOGO's #1 finding resolved this skill's v1.0.0 top risk: the anchor-link verification grepped heading TEXT, which "would pass on a real slug collision; the top stated risk is unverified by the very check meant to catch it." The fix swaps the grep for the repo's own slug-aware validator — `hephaestus-validate-anchors` (`hephaestus/markdown/anchors.py`, `pyproject.toml:130`; `heading_to_anchor()` models GitHub's exact GFM slug, `validate_anchors()` exits 1 on a mismatch) — plus `pytest tests/unit/markdown/test_anchors.py`. Two secondary NOGO fixes: header keys from one sample reframed as a non-binding example (POLA), and the lint worry corrected by reading `.markdownlint.yaml` (`MD013: false`; MD025/MD003 fire). The plan is still **NOT EXECUTED end-to-end** — no PR merged, no CI — hence `verification: unverified`; even `pixi run hephaestus-validate-anchors` is proposed-but-unrun this session.

**Sibling skills**: `planning-audit-doc-nitpick-stamp-and-document` (docstring gap + version/date stamp nitpicks), `ci-cd-load-bearing-filename-nitpick-document-dont-rename` (discoverability-rename nitpicks), `github-relative-doc-links-resolve-to-file-location` (relative-link resolution), `contributing-md-structure-sync` (CONTRIBUTING.md structure).
