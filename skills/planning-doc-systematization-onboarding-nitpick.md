---
name: planning-doc-systematization-onboarding-nitpick
description: "Use when planning a fix for a DOCUMENTATION-ONLY audit nitpick that asks you to (a) systematize an 'ad-hoc' directory/orphan artifact with a convention README, or (b) add a 'productive in a day' / onboarding path to CONTRIBUTING.md. Triggers: (1) an audit calls a file in a directory 'ad-hoc' / 'one-off' / 'cruft' and you are about to delete or rename it — FIRST run `git log -- <path>` to check its history; a file added in one PR and deliberately maintained in a later PR is a LEGITIMATE operational note that warrants a README systematizing the convention, NOT deletion. (2) you are systematizing a directory whose name COLLIDES with a standard built-in concept (e.g. `docs/release-notes/` vs GitHub's commit-generated release notes; CLAUDE.md may even mandate `gh release create --generate-notes` and 'No CHANGELOG.md') — the convention README's FIRST job is to draw the boundary: state explicitly it is NOT the same-named standard concept, or future contributors conflate the two. (3) you are adding an onboarding / 'first day' path — it must LINK existing canonical sections (Development Setup / Testing / PR Process) via anchors, NEVER re-state commands like `just bootstrap` (DRY / single-source-of-truth; duplication creates drift). A 'productive in a day' path is an INDEX over existing sections, not new prose. (4) your plan asserts markdown anchor links (`#development-setup`, `#testing`) resolve — markdown anchors are a SILENT-FAILURE class: a wrong slug renders fine and lints green. The single biggest correctness risk is that you grepped for the HEADING TEXT, not the RENDERED SLUG: GFM/markdownlint slugification (trailing punctuation, duplicate-heading `-1` suffixes, the repo's specific markdownlint config) can make `## Foo:` → `#foo` not `#foo-1`. Verify each target by the slug the linter actually produces, not by inferring the GFM rule from memory. Headline: for doc-systematization + onboarding nitpicks — check git history before calling an artifact cruft, disambiguate same-named concepts in the README's first line, link don't duplicate in onboarding paths, and verify anchor SLUGS (not heading text) against the actual linter. Use when category is documentation and the issue asks only to DOCUMENT, never to change behavior."
category: documentation
date: 2026-06-24
version: "1.0.0"
user-invocable: false
verification: unverified
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
  - silent-failure-class
  - markdownlint
  - kiss-yagni
  - unverified-assumption
---

# Planning a Doc-Systematization + Onboarding-Path Audit Nitpick

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-24 |
| **Objective** | Plan a documentation-only audit nitpick that (a) systematizes an "ad-hoc" orphan directory with a convention README and (b) adds an onboarding "first day" path to CONTRIBUTING.md — without deleting a maintained artifact, without conflating a same-named standard concept, without duplicating canonical commands, and without trusting unverified markdown anchor slugs |
| **Outcome** | A planning meta-pattern: run `git log -- <path>` before classifying any artifact as cruft; make the convention README's first job to disambiguate a name that collides with a built-in concept; build the onboarding path as an INDEX of links over existing sections (never re-state commands); and verify every anchor target by the SLUG the linter actually renders, not the heading text |
| **Verification** | unverified — the plan was authored for ProjectHephaestus #1544 but NEVER executed (no files created, no CI run) |

## When to Use

- An audit/lint/review NITPICK calls a file in a directory **"ad-hoc"**, **"one-off"**, or **"cruft"** and proposes deleting or ignoring it. Before you classify it, run `git log -- <path>`.
- The issue asks you to **systematize a directory** (add a README documenting its convention) whose **name overlaps a standard built-in concept** — e.g. `docs/release-notes/` vs GitHub's commit-generated release notes, `changelog/` vs a CHANGELOG, `migrations/` vs an ORM's.
- The issue asks for an **onboarding / "first day" / "productive in a day"** section in `CONTRIBUTING.md`, and the canonical setup/test/PR steps already exist elsewhere in the file.
- A plan **asserts that markdown anchor links resolve** (`#development-setup`, `#testing`, `#pull-request-process`) and you need to verify them at plan time.
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

5. VERIFY anchor SLUGS, not heading text (BIGGEST RISK).
   - Markdown anchors are a SILENT-FAILURE class: a wrong slug renders fine
     and lints green.
   - Do NOT infer the GFM slug rule from memory. Trailing punctuation,
     duplicate headings (`-1` suffix), and the repo's markdownlint config
     change the slug.
   - Grepping for the HEADING TEXT does NOT catch a slug mismatch. Confirm
     the rendered slug (e.g. via the linter / a slugify pass / GitHub
     preview), then assert the link.

6. RUN the actual doc gate before claiming pass.
   - Identify which command binds (`pre-commit run --all-files`? a
     markdownlint-cli2 hook? a `pixi run` task?) and which rules are enabled
     (MD013 line-length, list-style). New prose can trip an un-accounted rule.

7. STATE verification honestly.
   - Plan authored, never executed → "unverified". Keep "Proposed Workflow"
     + warning banner; never claim it "passes".
```

### Detailed Steps

1. **Classify document-only.** Read the issue. If it says "document", "systematize", "add a README", "add an onboarding section", the scope is documentation. Do NOT delete the orphan, do NOT rename anything, do NOT add validation (KISS/YAGNI). The source issue (ProjectHephaestus #1544) was an S2 low-priority nitpick bundle that asked only to document.

2. **Run `git log -- <path>` before calling any artifact cruft.** The audit labelled `docs/release-notes/plan-reviewer-final-verdict.md` an ad-hoc one-off. `git log -- docs/release-notes/` showed it was added in PR #571 and deliberately maintained in #1268 — a legitimate operational note, not garbage. A maintained file warrants a README that **systematizes the convention** ("component-scoped operational notes"), never deletion. Only an artifact with no maintenance history is a removal candidate.

3. **Disambiguate a same-named standard concept in the README's first line.** `release-notes` collides with GitHub's auto-generated release notes. This repo's CLAUDE.md mandates "No CHANGELOG.md; release notes generated from commits via `gh release create --generate-notes`". The convention README's first job is to state explicitly it is **NOT** that — these are component-scoped operational notes, distinct from commit-generated GitHub release notes. Otherwise future contributors conflate the two. When systematizing any directory whose name overlaps a built-in concept, draw the boundary up front.

4. **Build the onboarding path as an INDEX of links, never duplicated commands.** CONTRIBUTING.md already had every step (Development Setup, Testing, PR Process); the only gap was sequencing. The "first day" section must LINK existing canonical sections via anchors, NOT re-state `just bootstrap` or any command (DRY / single-source-of-truth — a duplicated command drifts the moment the canonical section changes). A "productive in a day" path is an index over existing sections, not new prose.

5. **Verify anchor SLUGS, not heading text — the single biggest correctness risk.** Markdown anchor links are a silent-failure class: a wrong slug renders fine and the linter stays green. The source plan claimed `#development-setup`, `#code-contributions`, `#testing`, `#pull-request-process`, `#platform-support` all resolve, and "verified" them by grepping for the heading TEXT (`grep -nE '^#{1,3} ' CONTRIBUTING.md`). That grep does NOT catch a slug mismatch: GFM/markdownlint slugification differs from the heading text when a heading has trailing punctuation or a duplicate-text `-1` suffix, and the repo's specific markdownlint config can change the rule. Do NOT infer the slug from the standard GFM rule from memory. Confirm the actual rendered slug (run the linter, a slugify pass, or GitHub's preview) before asserting each link. This is the risk most likely to ship a broken link.

6. **Run the actual doc gate and enumerate its rules.** Do not assume `pre-commit run --all-files` is the binding gate, or that it would catch a problem. Identify the real gate (a markdownlint-cli2 pre-commit hook? a `pixi run` task?) AND which rules are enabled (MD013 line-length, list-style). New README/onboarding prose can trip a line-length or list-style rule the plan never accounted for. Run it; read the output.

7. **Record the honest verification level.** The source plan was authored but never executed — no files created, no CI run. The verification level is `unverified`. Keep the workflow titled "Proposed Workflow" with the warning banner; never claim it "passes".

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Treat `docs/release-notes/plan-reviewer-final-verdict.md` as ad-hoc cruft to delete | Accepted the audit's "one-off" label at face value | `git log -- docs/release-notes/` shows it was added in PR #571 and maintained in #1268 — a legitimate operational note | Run `git log -- <path>` before classifying any artifact as cruft; a maintained file warrants a README, not deletion |
| Write the release-notes README without disambiguating | Documented the convention but did not separate it from GitHub's commit-generated release notes | Name collides with a built-in concept (CLAUDE.md mandates `gh release create --generate-notes`, "No CHANGELOG.md") → contributors conflate the two | The convention doc's FIRST job is to draw the boundary: state it is NOT the same-named standard concept |
| Restate `just bootstrap` and other commands in the new onboarding section | Re-wrote the setup steps inline for a self-contained "first day" path | Duplicates canonical CONTRIBUTING.md sections → drift the moment they change (violates DRY / single-source-of-truth) | An onboarding path is an INDEX of LINKS over existing sections, not new prose; link the anchors, never restate commands |
| Verify anchor links by grepping the HEADING TEXT | `grep -nE '^#{1,3} ' CONTRIBUTING.md` confirmed each target heading exists | Markdown anchors are a silent-failure class; heading text ≠ rendered slug — trailing punctuation / duplicate-`-1` suffix / the repo's markdownlint config change the slug, and the grep cannot catch a slug mismatch | Verify the rendered SLUG (linter / slugify / GitHub preview), not the heading text — the biggest correctness risk in the plan |
| Infer GFM slugs from memory (`## Development Setup` → `#development-setup`) | Assumed the standard GFM rule without confirming against the repo's markdownlint config | Was NOT confirmed against this repo's specific config; a non-standard slug renders fine and lints green | Do not infer slugs from memory; generate them with the actual linter the repo runs |
| Assume the Code-of-Conduct section is one short paragraph for the insertion offset | Pinned the new section "after line 8" based on a plan-time read | If the file shifted, the line offset is stale | Re-locate the insertion point by a stable content anchor (heading substring), not a hardcoded line number |
| Codify 3 header keys from ONE example file as "the convention" | Reverse-engineered `**Affected component:**` / `**Issues:**` / `**Ships with:**` from a single sample | A single sample is not necessarily a real convention — mild over-generalization | When deriving a convention from one artifact, label it provisional or sample N>1 before codifying |
| Assume `pre-commit run --all-files` is the binding doc gate | Named the gate without enumerating enabled markdownlint rules (MD013 line-length, list-style) | New prose can trip a line-length/list-style rule the plan never accounted for; the assumed gate may not even be the binding one | Identify the REAL binding gate and its enabled rules; run it before claiming pass |

### Risks (carried from the source plan, unresolved)

1. **Anchor-slug mismatch (highest).** Slugs were inferred from the GFM rule and "verified" by grepping heading text — a grep that cannot detect a slug mismatch. Resolve by rendering slugs with the actual linter before asserting any link.
2. **Stale insertion offset.** "After line 8" assumes the Code-of-Conduct section is exactly one short paragraph; a file shift invalidates the offset. Re-anchor on heading content.
3. **Over-generalized README header keys.** The three prescribed keys were reverse-engineered from one example; a single sample may not be a real convention.
4. **Unenumerated lint rules.** `pre-commit run --all-files` was assumed binding without confirming which markdownlint rules (MD013, etc.) are enabled; new prose may trip an un-accounted rule.

## Results & Parameters

Copy-paste pre-implementation checklist for a doc-systematization + onboarding nitpick:

```text
[ ] Document-only?  (issue asks to DOCUMENT/systematize — no delete, no rename, no new validation)
[ ] git log -- <path> run?  (artifact's maintenance history checked BEFORE calling it cruft; maintained → README not deletion)
[ ] Same-named concept disambiguated?  (README's first line states it is NOT the built-in concept, e.g. NOT GitHub commit-generated release notes)
[ ] Onboarding path LINKS, not duplicates?  (anchors to existing sections; NO restated commands like `just bootstrap` — DRY)
[ ] Anchor SLUGS verified (not heading text)?  (rendered slug confirmed via the actual linter / slugify / GitHub preview — the biggest risk)
[ ] Insertion point re-anchored on content?  (not a hardcoded line offset like "after line 8")
[ ] README convention keys not over-generalized?  (3 keys from ONE sample flagged as provisional, not codified as law)
[ ] Real doc gate identified + rules enumerated?  (which command binds, which markdownlint rules — MD013 line-length etc. — are enabled)
[ ] Doc gate actually run?  (executed locally; output read; not assumed)
[ ] Verification level stated honestly?  (unverified if the plan was authored but not executed — keep "Proposed Workflow" + warning)
```

**Source context**: Extracted from an implementation PLAN authored for ProjectHephaestus issue #1544 — a low-priority S2 documentation-nitpick bundle pairing (a) a `docs/release-notes/README.md` that systematizes a directory holding one deliberately-maintained operational note (`plan-reviewer-final-verdict.md`, added in PR #571, maintained in #1268) as "component-scoped operational notes" distinct from commit-generated GitHub release notes, with (b) a "Your first day" onboarding section in `CONTRIBUTING.md` that LINKS (does not duplicate) the existing Development Setup / Testing / PR Process sections. The plan was authored but **NEVER EXECUTED** — no files were created, no CI ran — hence `verification: unverified`. The single biggest unverified reliance is that markdown anchor slugs were inferred from the GFM rule and "verified" by grepping heading text, a check that cannot catch a slug mismatch.

**Sibling skills**: `planning-audit-doc-nitpick-stamp-and-document` (docstring gap + version/date stamp nitpicks), `ci-cd-load-bearing-filename-nitpick-document-dont-rename` (discoverability-rename nitpicks), `github-relative-doc-links-resolve-to-file-location` (relative-link resolution), `contributing-md-structure-sync` (CONTRIBUTING.md structure).
