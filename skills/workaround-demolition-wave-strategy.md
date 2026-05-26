---
name: workaround-demolition-wave-strategy
description: "Multi-PR sequencing framework for safely ripping out workarounds after an upstream library/compiler bug is fixed. Use when: (1) an upstream dependency (compiler, runtime, library) just shipped a fix for a bug your repo has accumulated workarounds for, (2) workarounds are spread across CI retry loops, continue-on-error flags, build flags, debug infrastructure, ADRs, dev docs, reproducer files, test-file comments, and agent-facing skills/memory, (3) you need to avoid one giant unreviewable demolition PR and instead want a safe, bisectable, reviewable sequence, (4) you have to decide between scorched-earth deletion vs preservation-with-Superseded-markers for documentation/ADRs, (5) some workaround-removals are risky one-liners not exercised by your validation matrix and need their own CI gate."
category: ci-cd
date: 2026-05-25
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [workaround-removal, multi-pr-strategy, upstream-fix, wave-sequencing, ci-discipline, demolition, rollback-strategy]
---

# Workaround Demolition: Multi-Wave PR Strategy

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-25 |
| **Objective** | Frame the safe, bisectable, reviewable sequence for tearing out an accumulated tangle of workarounds after the upstream bug they targeted has been fixed. |
| **Outcome** | Verified end-to-end on a real upstream-fix-landed scenario (modular/modular#6413 family). Wave 0/1/1.5/2/3 PRs were all green/merging in the target repo. |
| **Verification** | verified-ci |

## When to Use

- An upstream dependency just shipped a fix for a bug your repo worked around in many places
- Workarounds span MULTIPLE surface types (CI config, build flags, debug infra, docs, repro files, test comments, agent guidance)
- A single demolition PR would touch >20 files and span >3 logical categories — unreviewable
- Some removals are risky one-liners (build flags, codegen-affecting changes) that your validation matrix didn't fully exercise
- You need to decide: scorched-earth deletion vs preservation with Superseded markers
- You want a durable canary PR that proves the new pin is operational, kept separate from demolition
- You want guardrails (CLAUDE.md notes, pre-commit greps) so the workaround patterns don't sneak back in

Do NOT use if:
- The workaround is in ONE file and removal is trivially reviewable — just open one PR
- The upstream fix isn't validated yet on your workload — see [[validate-upstream-mojo-fix-hostile-home-matrix]] or your project's analogous validation skill first

## Verified Workflow

### Quick Reference

```text
Wave 0: validation gate PR    — bump pin + unavoidable API fixes only. Kept OPEN as canary.
Wave 1: CI/infra demolition   — retry loops, continue-on-error, debug wrappers, re-enable disabled jobs + add guardrail note.
Wave 1.5: risky one-line strips — anything not exercised by Wave 0's CI gets its own PR.
Wave 2: scorched-earth purge  — ADRs, dev docs, repro files, workflow YAML, test-file comments.
Wave 3: agent memory updates  — user-context-specific feedback files, NOT a PR (edit directly).
Wave 4: cross-repo skills     — amend team-knowledge skills (Mnemosyne-style marketplaces).
```

### Sequencing Dependency Graph

```text
Wave 0 (validation gate) ─────────────────────► kept OPEN as canary
   │
   ▼
Wave 1 (CI demolition + guardrails) ──► merge ──► main
   │                                              │
   │                                              ▼
   ├──► Wave 1.5 (risky strips, independent gate) ──► rebase + merge
   │
   ├──► Wave 2 (scorched earth)                    ──► rebase + merge
   │
   └──► Wave 3 (memory edit, no PR — done immediately)

Wave 4 (cross-repo skills) ─► independent timeline, no dep on Waves 0-3
```

### Detailed Steps

#### Wave 0 — Validation Gate (separate PR, kept open as canary)

Goal: prove the new pin is operational on your full required-check matrix, in isolation from any demolition.

1. Create branch `<issue#>-validate-<dep>` off `main`.
2. Bump the dependency pin past the upstream fix's shipped version.
3. Apply ONLY changes that are unavoidable for the bump to compile (e.g., stdlib API regressions that came with the new version). NO workaround removal yet.
4. Open as a DRAFT PR. Run the full required-check matrix.
5. Keep this PR OPEN until at least Wave 1 has merged. It is durable evidence the new pin works on your workload — and a fallback if Wave 1 breaks for unrelated reasons.

#### Wave 1 — CI Infrastructure Demolition + Guardrails

Single PR including:

- The pin bump (cherry-pick from Wave 0, or rebase Wave 0's commits in)
- Any stdlib API regression fix from Wave 0
- Removal of retry loops wrapping the affected tool's invocations
- Removal of `continue-on-error: true` on the affected test groups
- Removal of debug/forensics infrastructure (gdb wrappers, coredump-capture composite actions)
- Re-enabling any test jobs that were disabled citing the upstream bug
- Add a CLAUDE.md / AGENTS.md / `notes/` entry: "<dep> is stable as of <version>; execution crashes are real bugs, do NOT add retry loops"
- (Recommended) Pre-commit guard that grep-fails on workaround marker strings (e.g., the issue number, the retry loop's signature comment)

EXCLUDE from Wave 1: any change that is workaround-removal-shaped but was not exercised by Wave 0's CI. Those belong in Wave 1.5.

#### Wave 1.5 — Risky One-Line Strips (separate PR, depends on Wave 1)

When the bulk Wave 1 PR would otherwise include a change Wave 0's CI didn't exercise (e.g., stripping a build flag still applied throughout Wave 0's runs), split that change into its own PR off Wave 1's branch (or off `main` post-Wave-1-merge).

Wave 1.5's whole purpose is to be the INDEPENDENT CI gate for the risky change.

Rule: any workaround removal you can't point to GREEN CI evidence for should be its own PR.

#### Wave 2 — Scorched-Earth Doc/Repro/Test-Comment Purge

POLICY DECISION required up front (commit to one early — it shapes hundreds of file edits):
- **Scorched earth**: delete everything; audit-trail via GitHub-issue comments
- **Preservation**: keep ADRs marked Superseded; move forensics notes to `docs/archive/`

Either is defensible. Pick one before opening Wave 2.

Includes:

- Deleting ADRs that documented the workaround
- Deleting dev docs explaining the workaround
- Deleting reproducer files (`.mojo` / `.py` / `.md`) that targeted the fixed bug
- Deleting workflow YAML for `repro-N.yml` / `soak-N.yml` jobs
- Stripping stale test-file comments referencing the bug (sed batch across N test files is fine)
- Scrubbing issue-reference comments from related ADRs/skills that survive

**Audit-trail-via-issue-comments pattern** (scorched-earth variant):

Before any deletion, capture `git log -1 --format=%H -- <path>` for every doomed file. Build a markdown table:

```text
| Path | Last commit hash | Recovery command |
```

Post as a comment on each related tracking GitHub issue (now-closed is fine — comment for audit completeness). Future agents asking "what happened to file X?" find the recovery command via issue search.

**Pre-deletion cross-reference audit**: see [[mkdocs-pre-deletion-audit]]. Grep surviving docs/README/ADRs for references to the to-be-deleted files BEFORE pushing. Otherwise `mkdocs --strict` (or your docs builder) fails and you need follow-up commits.

#### Wave 3 — Memory / Agent-Guidance Updates (no PR — direct edit)

Update agent-facing memory/feedback files (e.g., `~/.claude/projects/.../memory/feedback_*.md`) to:

- Strengthen existing "don't dismiss crashes as <thing>" entries with the upstream-fix-resolved status
- Add a new "don't re-introduce <workaround pattern>" feedback file naming the specific patterns (retry loops, `continue-on-error`, build flags, debug infrastructure)
- Index in `MEMORY.md`

These live OUTSIDE the repo in user-specific memory; no PR is involved. The main agent does this directly rather than delegating — memory files are user-context-specific.

#### Wave 4 — Cross-Repo Skill Amendment

Amend any team-knowledge skills (Mnemosyne, ProjectMnemosyne-style marketplaces) that documented the workaround patterns. For each:

- Bump skill version
- Mark workaround-recommendation sections as obsolete with explicit anti-recommendations
- Preserve methodology patterns that survive (minimal-reproducer bisection, closed-source-boundary docs, validation matrices) — the body becomes archaeology

Independent timeline; no dependency on Waves 0-3 merging.

### Related Skills (parallel-tactical companions)

- [[mojo-sanitizer-and-build-flags]] — the build-flag taxonomy when sanitizer builds need a flag that release builds no longer do (the Wave 1.5 case study)
- [[validate-upstream-mojo-fix-protocol]] — generalized validation-gate protocol for Wave 0
- [[mkdocs-pre-deletion-audit]] — cross-reference scanning before Wave 2 deletions
- [[validate-upstream-mojo-fix-hostile-home-matrix]] — specific validation pattern for one upstream Mojo fix family
- [[ecosystem-wide-multi-repo-sweep-orchestration]] — related but distinct: that skill is for sweeping fixes ACROSS repos; this skill is for ONE repo with multi-surface workarounds

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Combine gdb-wrapper removal and build-flag strip in one commit | Both were "remove justfile JIT workaround" shaped, so bundled into Wave 1 | Build-flag strip needed its OWN CI gate; bundling required surgical interactive-rebase + amend to split after the fact | If you can't point to green CI for a change, it belongs in its own PR. Split early or pay the rebase tax later. |
| Delegate bulk file deletion to a sub-agent | Spawned sub-agent to execute Wave 2 deletions; it "ran out of token budget" | Agent produced a comprehensive deletion-list report but did not execute the `git rm`s | For bulk-mechanical work (delete N files, sed N files), main agent's direct bash is more efficient than delegation. Reserve sub-agents for reasoning/exploration. |
| Debug "why is Wave 1 lint failing" on the branch | Spent time bisecting branch commits | A stale `.claude/scheduled_tasks.lock` had been committed accidentally in an unrelated prior PR and was failing pre-commit on every branch including ours | Before blaming your branch for a CI failure, check whether the same failure exists on `main`. Rebase early to inherit recent main fixes. |
| Push Wave 2 doc deletions and let CI find broken links | Pushed deletions, doc-deploy job (mkdocs --strict) failed | 3 separate iterations needed to chase broken links from surviving docs to deleted docs | Always pre-audit doc cross-references before deletion. See [[mkdocs-pre-deletion-audit]]. |
| Put workaround-removal AND demolition in the validation PR | Tried to make Wave 0 do double duty | Conflated "does the bump work?" with "does removing X work?" — when CI failed, signal was muddled and rollback was painful | Keep Wave 0 a pure canary. Demolition belongs in Wave 1+ where the diff scope makes failures attributable. |

## Results & Parameters

### Branch naming convention (suggested)

```text
<issue#>-validate-<dep>          # Wave 0 (validation canary)
<issue#>-demolition-wave1        # Wave 1 (CI + guardrails)
<issue#>-demolition-wave1p5      # Wave 1.5 (risky one-line strips)
<issue#>-demolition-wave2        # Wave 2 (scorched earth)
# Wave 3: no branch — direct edit to ~/.claude/.../memory/
# Wave 4: <repo>-amend-<skill>   # cross-repo skill amendments
```

### Guardrail note template (drop into CLAUDE.md or notes/)

```markdown
## <Dep> stability note (as of <YYYY-MM-DD>)

<Dep> is stable as of version <X.Y.Z>. The upstream bug that prompted our
retry loops / `continue-on-error` / debug infrastructure was fixed in <upstream-issue-link>.

**Do NOT re-introduce:**
- Retry loops around `<tool-invocation>`
- `continue-on-error: true` on `<test-group>`
- gdb wrappers, coredump-capture composite actions
- Build flags: `<flag-1>`, `<flag-2>` (sanitizer-only exception: see [[mojo-sanitizer-and-build-flags]])

Execution crashes are real bugs. Root cause them; do not dismiss as the old upstream flake.
```

### Pre-commit guard template (workaround-marker grep)

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: no-workaround-markers
      name: no-workaround-markers
      entry: bash -c 'grep -rnE "modular/modular#<issue>|continue-on-error.*<group>|retry.*<tool>" --include="*.yml" --include="*.yaml" --include="*.mojo" . && exit 1 || exit 0'
      language: system
      pass_filenames: false
```

### Audit-trail issue-comment template (Wave 2 scorched-earth)

```markdown
## Wave 2 deletions — audit trail

The following files were deleted as part of workaround demolition after upstream fix <link>.
Recovery is possible via the listed commit hashes.

| Path | Last commit hash | Recovery command |
|------|-----------------|------------------|
| docs/adr/ADR-N-foo.md | abc123 | `git show abc123:docs/adr/ADR-N-foo.md` |
| .github/workflows/repro-N.yml | def456 | `git show def456:.github/workflows/repro-N.yml` |

Rationale: scorched-earth policy chosen because (a) workaround is fully obsolete,
(b) ADR content is historical-only with no surviving design impact,
(c) recovery via git history is sufficient for any future archaeology.
```

### Verification observed

- Wave 0 PR ran the full required-check matrix on the bumped pin: GREEN.
- Wave 1 PR merged after Wave 0 confirmation: GREEN.
- Wave 1.5 PR (build-flag strip) caught a SIGILL regression in sanitizer builds on FIRST push — the strip had to be amended to retain the flag for sanitizer codegen only. Had this ridden inside Wave 1's 7-commit PR, bisection would have been painful. The split paid for itself immediately.
- Wave 2 PR scorched-earth deletions: green after pre-deletion audit caught surviving cross-references.
- Wave 3 memory edits: applied locally, indexed in MEMORY.md, no PR needed.
- Wave 4 cross-repo skill amendments: independent green merges.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Upstream Mojo runtime fix (modular/modular#6413 family) — multiple-surface workaround demolition spanning CI retry loops, `continue-on-error`, gdb wrappers, build flags (`--target-features -avx512*`), ADRs, dev docs, reproducer files, agent memory | This skill is the framework extracted from that demolition. PR sequence ran Wave 0 → Wave 1 → Wave 1.5 → Wave 2 → Wave 3 (memory) → Wave 4 (cross-repo skills, including this one). |
