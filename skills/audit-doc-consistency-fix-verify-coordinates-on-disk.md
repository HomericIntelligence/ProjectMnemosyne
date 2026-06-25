---
name: audit-doc-consistency-fix-verify-coordinates-on-disk
description: "Use when planning a fix for a documentation-consistency issue (drifted line numbers/paths, a command that disagrees across docs), OR when authoring the verification commands that prove such a fix. Trigger: (1) an issue, a PRIOR PLAN, or a repo audit cites file:line coordinates that may have drifted since they were captured — re-derive them on disk before quoting, (2) N docs disagree on the same command/snippet and one must be brought into line with a canonical copy, (3) a repo-wide grep surfaces matches inside throwaway worktree/build copies that must be scoped out, (4) a prior-learnings suggestion proposes drift-guard CI tooling that is disproportionate for a one-line docs fix, (5) you are writing a plan's verification-command grep assertions and they must be PORTABLE and actually able-to-fail (no cross-line / GNU-only regex; pair a positive with a negative assertion)."
category: documentation
date: 2026-06-20
version: "1.1.0"
user-invocable: false
verification: verified-local
history: audit-doc-consistency-fix-verify-coordinates-on-disk.history
tags:
  - audit-coordinate-drift
  - doc-consistency
  - verify-on-disk
  - canonical-source
  - line-number-drift
  - yagni
  - pre-commit-verification
  - planning-methodology
  - cross-doc
  - inherited-coordinate-rederive
  - verification-command-portability
  - grep-positive-negative-assertion
---

# Audit Doc-Consistency Fix: Verify Coordinates On Disk

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Plan a fix for a documentation-consistency issue (drifted coordinates, a command that disagrees across docs) without trusting stale coordinates inherited from an audit, an issue body, or a prior plan; without over-scoping into throwaway worktree copies; without bolting on disproportionate CI tooling; and while authoring portable, able-to-fail verification-command grep assertions |
| **Outcome** | A repeatable planning methodology: re-derive every inherited file:line on disk with `grep -n <stable-substring>`, source the replacement verbatim from an already-correct canonical doc, scope out worktree/build copies, decline drift-guard CI tooling (YAGNI), author portable positive+negative grep assertions (no cross-line / GNU-only regex), and verify docs-only via markdownlint + grep agreement |
| **Verification** | verified-local |
| **History** | See `audit-doc-consistency-fix-verify-coordinates-on-disk.history` (v1.0.0 → v1.1.0, 2026-06-20) |

## When to Use

- An issue, a **prior plan**, or a **repository audit** cites `file:line` coordinates that may have drifted between when they were captured and execution (e.g. `README.md:58-61` that is really at `README.md:60`; or a prior plan saying "lines 91-93" when the entry is really at 93-95). **Re-derive every inherited file:line on disk with `grep -n <stable-substring> <file>` before you quote it** — the source does not matter (audit output, issue body, or your own previous plan); any coordinate captured earlier should be assumed drifted.
- The cited path itself may be wrong (e.g. an audit said `scripts/install_hooks.sh:41` but the file lives at `scripts/shell/install_hooks.sh:9`).
- You are **authoring a plan's verification block** and need its `grep` assertions to be PORTABLE and actually able-to-fail: no cross-line / multi-line regex for line-oriented `grep`, no GNU-only `\s`/`\d` classes when portability matters, and a positive assertion paired with a negative `! grep` so the command can both pass on the good state and fail on the bad state.
- Two or more documents disagree on the same command/snippet and you must bring the offender into line with the others.
- A repo-wide `grep` surfaces matches inside `.claude/worktrees/...`, `build/.worktrees/...`, or other throwaway/untracked copies that must be explicitly scoped out.
- A prior-learnings or reviewer suggestion proposes a grep-based CI drift-guard for a change that is only a one-line docs edit.
- The change is documentation-only and you need to decide what the actual verification gate is (spoiler: markdownlint via pre-commit, not unit tests).

## Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.
>
> **Heading note:** The repository validator (`scripts/validate_plugins.py`) hard-requires the literal section string `## Verified Workflow`, so the canonical workflow steps below are emitted under that heading to keep validation green. This skill is a **planning methodology** captured at `verified-precommit` level — the planning steps and on-disk grep facts were directly verified this session, but the end-to-end fix was NOT executed or CI-confirmed. Read the steps below as **proposed**, per the warning above.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

### Quick Reference

```bash
# 0. Re-derive an INHERITED file:line (from an issue body, a prior plan, or an audit)
#    on disk before quoting it. Anchor on a STABLE SUBSTRING, not the stale number.
#    Example: a prior plan said "lines 91-93"; re-derive ->
grep -n 'CI unit/integration' CLAUDE.md   # prints the real start line (e.g. 93)
#    Where possible, quote the verbatim block too so the target survives line drift.

# 1. Re-anchor EVERY cited coordinate on disk before planning any edit.
#    Do not trust file:line from an audit-filed issue OR a prior plan.
grep -rn "pre-commit install" --include='*.md' --include='*.sh' . \
  | grep -v -e '\.claude/worktrees/' -e 'build/\.worktrees/' -e '/build/'

# 2. List ONLY tracked copies (excludes throwaway worktree/build copies by construction).
git ls-files | grep -E '(README|CONTRIBUTING)\.md|install_hooks\.sh'
git grep -n "pre-commit install" -- $(git ls-files)

# 3. Identify which copies are already canonical/correct, then copy their EXACT form
#    into the offender. Never compose a new command from scratch.
git grep -n "pixi run pre-commit install"   # the canonical form already present elsewhere

# 4. Apply the one-line edit in the offending doc only (verbatim from canonical copy).

# 5. Verify (docs-only => markdownlint via pre-commit is the ONLY gate; no unit tests).
pixi run pre-commit run --files README.md
# then assert all tracked copies now agree:
git grep -n "pre-commit install" -- $(git ls-files) \
  | grep -v "pixi run pre-commit install"   # expect: ZERO lines

# 6. PORTABLE, able-to-fail verification assertions for a PLAN.
#    Match a SINGLE stable substring on ONE line. Do NOT use cross-line regex
#    (`\s*\n*` is dead — line-oriented grep never sees `\n`) or GNU-only `\s`/`\d`.
#    Pair a positive assertion (proves the addition) with a negative one (proves the
#    removal), so the command can both pass on the good state AND fail on the bad state:
grep -q 'CI badge is now load-bearing' FILE && ! grep -q 'do not rely on the green CI badge' FILE
#    Prefer fixed strings (grep -F) over regex when no metacharacters are needed.
```

### Detailed Steps

1. **Re-anchor every audit coordinate on disk.** For each `file:line` the issue
   cites, `grep -n` the actual repo. Treat the cited line numbers AND paths as
   hints only. In issue #1215 the audit cited `README.md:58-61`,
   `CONTRIBUTING.md:43`, and `install_hooks.sh:41`; on disk the real locations
   were `README.md:60`, `CONTRIBUTING.md:61`, and
   `scripts/shell/install_hooks.sh:9` (wrong subdir too). The finding HELD, but
   every cited coordinate was stale. Plan against disk reality, not the issue body.

2. **Identify the canonical copy; source the fix verbatim.** When N docs disagree
   on a command, find which copies are already correct and copy their EXACT form
   into the offender. In #1215, `CONTRIBUTING.md` and
   `scripts/shell/install_hooks.sh` already used `pixi run pre-commit install`;
   the fix was to make `README.md` match them — not to invent a new command form
   that could become a third divergent variant.

3. **Grep ALL copies; scope out throwaway worktree/build dirs.** Run a repo-wide
   grep so you do not miss a divergent copy, but a raw `grep -rn` will surface hits
   under `.claude/worktrees/...` and `build/.worktrees/...`. Those are
   untracked/throwaway worktree copies. Exclude them via `grep --exclude-dir`, or
   (cleaner) filter to `git ls-files` / use `git grep -- $(git ls-files)` so only
   tracked source is in scope. State the out-of-scope dirs explicitly in the plan.

4. **Apply YAGNI to drift-guard tooling.** If a prior-learnings or reviewer
   suggestion proposes a grep-based CI consistency guard to prevent future drift,
   recognize it as disproportionate scope for a one-line docs fix. DECLINE it, and
   write the decline + the reason into the plan rather than silently dropping it.

5. **Verify as docs-only.** No unit tests apply. The only gate is markdownlint via
   pre-commit: `pixi run pre-commit run --files <file>`, plus grep assertions that
   all tracked copies now agree on the command. Project-specific ship gates
   (ProjectHephaestus: `state:implementation-go` label + `pr-policy`) come from
   project memory and should be re-verified, not assumed.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusted audit line numbers `README.md:58-61` / `install_hooks.sh:41` blindly | Planned edits directly at the cited coordinates | Every cited coordinate was stale — real locations were `README.md:60`, `CONTRIBUTING.md:61`, and `scripts/shell/install_hooks.sh:9` (wrong subdir too) | Grep the repo to re-anchor before trusting any audit-filed coordinate |
| Repo-wide grep matched `.claude/worktrees/` and `build/.worktrees/` copies | Scoped the fix from a raw `grep -rn` hit list | Those are throwaway, untracked worktree copies, not tracked source — risks editing the wrong file or over-scoping | Exclude worktree/build dirs explicitly, or filter to `git ls-files` / `git grep` |
| Composing a new corrected command from scratch for README | Inventing the fixed command form rather than copying an existing one | Risks introducing a THIRD divergent form instead of converging on the canonical one | Copy the exact form verbatim from an already-correct canonical doc |
| Considered adding a grep-based CI drift-guard | Proposed a consistency-check CI step to prevent recurrence | Disproportionate scope for a one-line docs fix (YAGNI violation) | Apply YAGNI; state the decline + reason explicitly in the plan |
| Cited inherited line numbers verbatim | Trusted "lines 91-93" from the issue/prior plan without re-deriving | Actual entry was at lines 93-95 (2-line drift); reviewer flagged the stale offset | Re-derive every inherited file:line with `grep -n <substring> <file>` at planning time; anchor on a stable substring, quote the verbatim block so the target survives drift |
| Cross-line / GNU-only regex in a plan's grep assertion | `grep -q 'green\s*\n*.*load-bearing\|...'` as a verification check | Line-oriented grep never sees `\n`, so `\s*\n*` is dead; `\s` is a non-portable GNU extension; the branch could never match and only the fallback passed | Match a single stable substring on one line; avoid `\s`/`\d`/cross-line patterns; pair a positive assertion with a negative `! grep` so the command can both pass on good state and fail on bad state |

## Results & Parameters

Concrete facts from the ProjectHephaestus issue #1215 planning session (a one-line
README fix: prefix `pre-commit install` so it reads `pixi run pre-commit install`):

- **Audit-cited vs on-disk coordinates (all cited coordinates were stale):**

  | Audit cited | Real on-disk location |
  | ----------- | --------------------- |
  | `README.md:58-61` | `README.md:60` |
  | `CONTRIBUTING.md:43` | `CONTRIBUTING.md:61` |
  | `scripts/install_hooks.sh:41` | `scripts/shell/install_hooks.sh:9` |

- **Canonical form to copy verbatim:** `pixi run pre-commit install` — already used
  by TWO independent canonical sources (`CONTRIBUTING.md`,
  `scripts/shell/install_hooks.sh`). The offender was `README.md`.

- **Scope-out dirs (throwaway, untracked):** `.claude/worktrees/...`,
  `build/.worktrees/...`. Exclude via `grep --exclude-dir` or `git ls-files`.

- **Verification gate (docs-only):** `pixi run pre-commit run --files <file>`
  (markdownlint). No unit tests apply. Plus a grep assertion that every tracked
  copy now reads `pixi run pre-commit install`.

### Verified On

| Project / Issue | What was observed (locally, this session) |
| --------------- | ----------------------------------------- |
| ProjectProteus, issue #182 re-plan (R1 NOGO → addressed) | CLAUDE.md "Known Critical Defects" entry cited in a prior plan as **lines 91-93**; re-derived to **lines 93-95** via `grep -n 'CI unit/integration' CLAUDE.md` (entry begins at line 93). The 2-line drift was cosmetic only because the plan also quoted the verbatim block. Separately, a dead `grep -q 'green\s*\n*.*load-bearing\|...'` BRE branch in the Criterion-2 verification was removed — line-oriented grep never sees `\n` (so `\s*\n*` could never match) and `\s` is a non-portable GNU extension; only the `|| grep -q 'resolved by PR #173'` fallback had been passing. |

> **Honesty note (planning-phase learnings).** The verification COMMANDS named above
> (`grep -n 'CI unit/integration' CLAUDE.md` returning line 93; the dead-branch
> analysis) WERE actually run / observed this session, which is what `verified-local`
> attests to. The downstream ProjectProteus #182 plan ITSELF was **not implemented or
> CI-validated** — these are coordinate-rederivation and grep-portability rigor lessons
> from the planning phase, not an executed fix.

### Risks for the plan reviewer

- **Source-consistency, not failure-reproduction.** The plan relies on
  `pixi run pre-commit install` being the genuinely-correct form. It was verified
  that TWO independent canonical sources already use it, but the command was NOT
  actually executed on a clean machine — verification is by source-consistency, NOT
  by reproducing the original "command not found" failure.
- **Project-specific ship gates not re-verified.** The `state:implementation-go`
  label requirement and `pr-policy` gating are ProjectHephaestus-specific and were
  taken from project memory, not re-verified this session. Re-confirm before relying
  on them.
- **Coordinate drift is the default, not the exception.** Any audit-filed issue
  whose coordinates were captured at filing time should be assumed drifted; the
  finding can hold while every coordinate is wrong.
