---
name: monorepo-subproject-gitignore-and-github-template-gotchas
description: "Two related gotchas when adding per-subproject config to a project that lives in a SUBDIRECTORY of a monorepo. (1) A monorepo-root .gitignore rule silently blocks committing files in a subproject — `git add` does nothing, `git status` shows nothing — and un-ignoring requires re-including the parent directory FIRST before any file negation takes effect. (2) GitHub issue/PR templates are NOT auto-wired from a monorepo subdirectory; GitHub reads templates only from the repository-root .github/, root, or docs/. Use when: (1) adding a .claude/, .vscode/, or other tool-config directory to a monorepo subproject and `git add` appears to do nothing; (2) `git status` does not show new files you just created inside a monorepo subproject; (3) adding GitHub issue or PR templates to one subproject of a monorepo; (4) writing a CONTRIBUTING.md for a monorepo subproject."
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [monorepo, gitignore, git-check-ignore, github-templates, issue-template, subproject, claude-config]
---

# Monorepo-Subproject Gotchas: `.gitignore` Negation Order and Non-Wired GitHub Templates

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-19 |
| **Objective** | Add project-scoped `.claude/` agent config and GitHub issue/PR templates to a project that lives in a *subdirectory* of a 5-project monorepo, and have the config files actually commit and behave as intended. |
| **Outcome** | Two distinct gotchas surfaced. (1) The monorepo-root `.gitignore` had `.claude/`, so the subproject's new `.claude/` files were silently un-committable — `git add` was a no-op and `git status` did not list them. Fixed with a negation block in the *subproject's own* `.gitignore` that re-includes the directory first. (2) GitHub did not surface the subproject's `.github/ISSUE_TEMPLATE/` and `pull_request_template.md` in the UI, because GitHub only auto-wires templates from the *repository root*. Resolved by documenting the limitation in `CONTRIBUTING.md` and directing contributors to `gh ... --body-file`. |
| **Verification** | verified-local |

## When to Use

- Adding a `.claude/`, `.vscode/`, or other tool-config directory to a project that is a subdirectory of a larger monorepo, and `git add` appears to do nothing.
- `git status` does not show new files you just created, and you are inside a monorepo subproject.
- Adding GitHub issue or PR templates to one subproject of a monorepo.
- Writing a `CONTRIBUTING.md` for a monorepo subproject.
- Any time a config file's behavior in a monorepo subproject differs from what you would expect in a standalone repo.

## Verified Workflow

### Quick Reference

```bash
# Diagnose: is a new config file blocked by an ancestor .gitignore?
git check-ignore -v <subproject>/.claude/settings.json
# Output like ".gitignore:1:.claude/  <path>" => an ancestor rule is matching.

# Fix: in the SUBPROJECT's own .gitignore, un-ignore the dir, re-exclude contents,
# then re-include the specific files (order matters):
#   !.claude/
#   .claude/*
#   !.claude/settings.json
#   !.claude/agents/
#   !.claude/agents/*.md

# Verify the fix:
git check-ignore <subproject>/.claude/settings.json   # prints nothing => committable
git status --short <subproject>/.claude/              # shows ?? => untracked, will commit
```

### Detailed Steps

#### Gotcha 1 — monorepo-root `.gitignore` silently blocks subproject files

1. **Diagnose with `git check-ignore -v`.** When `git add <subproject>/.claude/` seems to do nothing and `git status` does not list the new files, do not assume the files are tracked or that the add succeeded. Run:

   ```bash
   git check-ignore -v <subproject>/.claude/settings.json
   ```

   If it prints a line like `.gitignore:1:.claude/  <path>`, an ancestor `.gitignore` (here, the monorepo root) has a rule matching the path. `git add` silently skips ignored files — no error, no warning.

2. **Apply the negation in the SUBPROJECT's own `.gitignore`, with the correct order.** The critical subtlety: **a `.gitignore` negation cannot re-include a file if its parent directory is still excluded** — git will not even descend into an excluded directory, so a bare `!.claude/settings.json` has no effect. You must:

   1. Un-ignore the directory: `!.claude/`
   2. Re-exclude everything inside it: `.claude/*`
   3. Re-include only the specific files you want: `!.claude/settings.json`, etc.

   ```gitignore
   # Re-include specific project-scoped .claude files (monorepo root ignores .claude/ wholesale)
   !.claude/
   .claude/*
   !.claude/settings.json
   !.claude/agents/
   !.claude/agents/*.md
   ```

   Order matters: `!.claude/` un-ignores the directory; `.claude/*` re-excludes its contents; the subsequent `!` lines re-include the chosen files. For nested paths (`.claude/agents/*.md`), you must also re-include the intermediate directory (`!.claude/agents/`) — the same descend rule applies at every level.

3. **Verify.** `git check-ignore <path>` printing the path means it is *still* ignored; printing *nothing* means it is committable. Then `git status --short <subproject>/.claude/` should show the files as untracked (`??`).

#### Gotcha 2 — GitHub issue/PR templates are not auto-wired from a subdirectory

4. **Know the rule: GitHub reads templates from the repository root only.** GitHub surfaces `ISSUE_TEMPLATE/` and `pull_request_template.md` in its "New issue" / "New PR" UI only when they live at the *repository root* — specifically in the root `.github/`, the root directory itself, or `docs/`. Templates placed at `<subproject>/.github/` are **never** surfaced in the GitHub UI.

5. **Do not move per-subproject templates to the monorepo root.** Putting them at the repo root would apply them to *every sibling project* in the monorepo — pollution. In a monorepo where each subproject wants its own templates, non-wiring is unavoidable.

6. **Resolve by documentation, not auto-wiring.** Place the subproject's templates inside the subproject's own `.github/` as the *documented project standard*, and have the subproject's `CONTRIBUTING.md` explicitly state the limitation and tell contributors to use:

   ```bash
   gh issue create --body-file <subproject>/.github/ISSUE_TEMPLATE/<template>.md
   gh pr create   --body-file <subproject>/.github/pull_request_template.md
   ```

   instead of relying on the GitHub UI to pre-fill the template.

**General principle for both gotchas:** monorepo-root configuration (`.gitignore`, `.github/`) has repo-wide reach; a subproject cannot assume its local config files behave the way they would in a standalone repo. Always `git check-ignore` a new committed config file in a monorepo subproject, and never assume GitHub template auto-wiring works below the repository root.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | `git add .claude/` in a monorepo subproject — created `.claude/settings.json` + `.claude/agents/*.md` and ran `git add` | The monorepo-root `.gitignore` had `.claude/`; `git add` silently added nothing and `git status` did not list the files | In a monorepo subproject, `git check-ignore -v <path>` any new config file before assuming `git add` worked — an ancestor `.gitignore` may be matching |
| 2 | A bare `!.claude/settings.json` negation — added only that one line to the subproject `.gitignore` to un-ignore one file | Git will not descend into an excluded directory, so a negation on a file inside a still-excluded dir has no effect | A `.gitignore` negation must re-include the parent directory FIRST (`!.claude/`), then re-exclude contents (`.claude/*`), then re-include specific files |
| 3 | Put issue/PR templates in `<subproject>/.github/` expecting GitHub to use them — placed `ISSUE_TEMPLATE/` and `pull_request_template.md` under the subproject's `.github/` | GitHub only auto-wires templates from the repository-root `.github/` (or root or `docs/`), never from a subdirectory | In a monorepo, per-subproject templates are documentation-only; state the limitation in `CONTRIBUTING.md` and use `gh ... --body-file`. Do not move them to the repo root — that pollutes sibling projects |
| 4 | Considered moving the subproject templates to the monorepo-root `.github/` so GitHub would wire them | That would apply the templates to every sibling project in the monorepo | Per-subproject templates are inherently incompatible with GitHub's root-only auto-wiring; accept non-wiring and document it rather than polluting siblings |

## Results & Parameters

Working `.gitignore` negation block (place in the **subproject's own** `.gitignore`):

```gitignore
# Re-include specific project-scoped .claude files (monorepo root ignores .claude/ wholesale)
!.claude/
.claude/*
!.claude/settings.json
!.claude/agents/
!.claude/agents/*.md
```

Verification commands:

```bash
# Before fix — confirms an ancestor rule matches:
git check-ignore -v <subproject>/.claude/settings.json
#   .gitignore:1:.claude/   <subproject>/.claude/settings.json

# After fix — committable when this prints NOTHING:
git check-ignore <subproject>/.claude/settings.json

# Confirm git now sees the files as untracked:
git status --short <subproject>/.claude/
#   ?? <subproject>/.claude/settings.json
#   ?? <subproject>/.claude/agents/...
```

Heuristic table:

| Observation | Meaning | Action |
|---|---|---|
| `git check-ignore <path>` prints the path | Path is still ignored by some `.gitignore` rule | Run `-v` to find the matching rule; add a negation block |
| `git check-ignore <path>` prints nothing | Path is committable | `git add` will work |
| `git status` does not list a file you just created (in a monorepo subproject) | Likely ignored by an ancestor `.gitignore` | `git check-ignore -v` it |
| `!file` negation has no visible effect | Parent directory is still excluded | Add `!parentdir/` before the file negation |

GitHub template-location rule: GitHub auto-wires `ISSUE_TEMPLATE/` and `pull_request_template.md` from the `.github/`, root, or `docs/` directory **of the repository root only** — never from a subdirectory. Per-subproject templates in a monorepo are therefore documentation-only; surface them via `gh issue create --body-file` / `gh pr create --body-file` and document the limitation in `CONTRIBUTING.md`.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| predictive-coding research project (a subdirectory of the `mvillmow/Random` 5-project monorepo) | Adding project-scoped `.claude/` config and GitHub templates to a monorepo subproject, 2026-05-19 | The monorepo-root `.gitignore` `.claude/` rule silently blocked the subproject's `.claude/settings.json` + `.claude/agents/*.md`; fixed with a directory-first negation block. GitHub did not surface the subproject's `.github/` templates; resolved by documenting `gh ... --body-file` usage in `CONTRIBUTING.md` |
