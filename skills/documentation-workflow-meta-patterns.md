---
name: documentation-workflow-meta-patterns
description: 'Meta-patterns for documentation-only PR workflows. Use when: (1) starting
  any documentation task and needing to detect already-done work before beginning,
  (2) handling a review fix plan that concludes no changes are needed, (3) triaging
  a security review on a docs-only PR, (4) implementing a small targeted doc edit,
  (5) merging two overlapping markdown docs into one canonical source, (6) documenting
  a pre-commit hook incompatibility in CONTRIBUTING.md, or (7) expanding bare NOTE/TODO
  markers with structured deferred-item format.'
category: documentation
date: 2026-05-19
version: 1.0.0
user-invocable: false
history: documentation-workflow-meta-patterns.history
tags:
  - documentation
  - workflow
  - preflight
  - no-op
  - review
  - security
  - pre-commit
  - deferred-items
  - duplicate-detection
---
# Documentation Workflow Meta-Patterns

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-05-19 |
| Category | documentation |
| Objective | Canonical reference for workflow patterns surrounding documentation changes |
| Outcome | Merged from 9 member skills (M48 epic #1854) |
| Theme | Detecting duplicate work, handling no-op reviews, triaging docs-only security reviews, small targeted edits, merging overlapping docs, hook incompatibility docs |

## When to Use

Use this skill before starting **any documentation task** to pick the right sub-workflow:

| Situation | Sub-Workflow |
| --------- | ------------ |
| Branch already has a commit matching the issue; PR may exist | Already-committed detection (Steps 1-A) |
| `.claude-review-fix-*.md` says "no fixes required" | No-op review confirmation (Steps 1-B) |
| Security review triggered on a docs-only PR | Docs-only security triage (Steps 1-C) |
| Issue specifies exact insert location; single targeted edit | Small doc edit (Steps 1-D) |
| Two markdown files cover the same topic (DRY violation) | Merge duplicate docs (Steps 1-E) |
| Pre-commit hook skips on some hosts; no CONTRIBUTING.md entry | Document hook incompatibility (Steps 1-F) |
| Issue has bare NOTE/TODO; documentation-only cleanup issue | Expand NOTE markers (Steps 1-G) |

**Hard rule**: Always run the orientation check (git log + PR check) before touching any file.

## Verified Workflow

### Quick Reference

```bash
# Orientation — run first for any doc task
git log --oneline -5
git status
gh pr list --head "$(git branch --show-current)"

# Pre-commit (preferred over `just`)
pixi run pre-commit run --all-files

# Commit on GLIBC-incompatible host
SKIP=mojo-format git commit -m "docs(<scope>): <summary>"

# PR creation + auto-merge
gh pr create --title "docs(<scope>): <summary>" --body "$(cat <<'EOF'
## Summary
- <bullet>

Closes #<number>
EOF
)"
gh pr merge --auto --rebase <pr-number>
```

### Steps 1-A: Already-Committed Detection

Trigger when: branch named `<N>-auto-impl`, git status is clean, git log shows commit matching issue title.

1. `git log --oneline -3` + `git status` — if clean with matching commit, work is done.
2. **Read target files** to confirm expected content is present (do not trust commit message alone).
3. `gh pr list --head <branch>` — if open PR exists, retrieve PR number.
4. `gh pr view <pr-number>` — confirm auto-merge enabled and `Closes #<N>` in body.
5. **Stop and report**. Do NOT create a duplicate commit, push again, or open a second PR.

**Key decision point** (auto-impl with plan): Compare missing items against **Success Criteria**, not plan notes. If a file is only in plan notes but absent from Success Criteria, the PR is complete.

```bash
# Check PR linkage
gh pr view <pr-number> --json body -q '.body'

# Add Closes if missing
gh pr edit <pr-number> --body "$(gh pr view <pr-number> --json body -q '.body')

Closes #<number>"
```

### Steps 1-B: No-Op Review Confirmation

Trigger when: `.claude-review-fix-*.md` plan states "No fixes required" or "PR is ready to merge as-is".

1. **Read the fix plan** — confirm the "no fixes" conclusion is explicit.
2. **Verify CI failures are pre-existing** — check that failures exist on `main` before this PR.
3. `git status` — confirm clean working tree (only review instructions file untracked).
4. `git log --oneline -5` — confirm correct commit is on branch.
5. **Report** — explain PR is correct as-is. Do NOT create an empty commit or push.

```bash
git status
git log --oneline -5
```

### Steps 1-C: Docs-Only Security Triage

Trigger when: security review requested; all changed files are `.md`, static `.json`, `.txt`, or `.rst`.

1. **Classify all changed files** — list every path; check against attack surface criteria.
2. If ALL are docs/metadata → no attack surface → skip to Step 3.
3. If any file is executable code or a GitHub Actions workflow → perform full security review.
4. **Apply hard exclusion policy**: documentation files (`.md`) are categorically excluded.
5. **Issue clean no-findings report** (copy-paste template):

```text
No security vulnerabilities were identified in this PR.

The changes consist entirely of documentation files (markdown skill documentation,
plugin metadata JSON, and session notes). Per the hard exclusion rules, insecure
documentation findings are excluded, and these files contain no executable code,
user input handling, authentication logic, cryptographic operations, or other
attack surfaces.
```

**File-type attack surface reference**:

| File Type | Has Attack Surface? | Action |
| ---------- | ------------------- | ------ |
| `.md` markdown | No | Classify as docs-only |
| `plugin.json` (static metadata) | No | Classify as docs-only |
| `references/notes.md` | No | Classify as docs-only |
| `.py`, `.js`, `.ts`, `.sh` | Possibly | Full security review |
| `.yml` GitHub Actions workflow | Possibly (injection) | Check untrusted input in `run:` steps |

### Steps 1-D: Small Doc Edit

Trigger when: issue specifies exact insert location; single additive markdown change.

1. **Read the prompt/issue** — parse deliverable and exact insertion anchor.
2. **Read the target file** — confirm line numbers and surrounding context.
3. **Apply Edit** — anchor `old_string` to the line before AND after the insertion point.
4. `pixi run pre-commit run --all-files` — verify markdownlint and other hooks.
5. **Commit** — stage only the modified file; use conventional commit with `Closes #<N>`.
6. `git push -u origin <branch>` then `gh pr create`.
7. `gh pr merge --auto --rebase <pr-number>`.

```python
# Key Edit pattern — include surrounding context for uniqueness
old_string = "Line before insertion.\n\n---"
new_string = """Line before insertion.

**Output**: Added clarification here.

---"""
```

**Pre-commit caveat**: `mojo format` hook may print GLIBC errors but exits 0 — non-fatal.

### Steps 1-E: Merge Duplicate Docs

Trigger when: two markdown files document the same concept (DRY violation).

1. **Read both files in parallel** — identify shared vs. unique content.
2. **Find all cross-references**: `grep -rn "old-filename\.md" --include="*.md" .`
3. **Fix broken syntax** in the canonical file (fenced block closings, long lines, self-links).
4. **Append unique content** from the duplicate into the canonical file in logical order.
5. **Delete the duplicate**: `git rm <duplicate-file.md>`
6. **Update all cross-references** found in Step 2.
7. `SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files` — fix MD013/MD032.
8. `git add <all modified files>` + commit + PR.

**Common markdownlint fixes after merge**:

- Close fenced code blocks with plain ` ``` ` (never ` ```text ` as a closing tag).
- Wrap long lines (>120 chars) at natural phrase boundaries.
- Add blank lines before/after lists (MD032).
- Remove self-referential links in "See Also" pointing to the deleted file.

### Steps 1-F: Document Hook Incompatibility

Trigger when: pre-commit hook auto-skips on some hosts; no CONTRIBUTING.md entry explains it.

1. **Read the issue** — `gh issue view <N> --comments` for scope.
2. **Audit existing state** before writing anything:
   - `.pre-commit-config.yaml` for inline comments
   - `docs/dev/` for existing compatibility docs
   - `CONTRIBUTING.md` for existing mentions: `grep -n "GLIBC\|glibc\|SKIP="`
3. **Determine the actual gap** — often only CONTRIBUTING.md is missing; the config and docs/dev already have content.
4. **Add a `####` subsection** to CONTRIBUTING.md under the relevant policy section.
   Include: affected OS/glibc range, exact warning text, what hook does automatically, CI guarantee, Docker workaround, link to full compat doc.
5. `SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files` — validate.
6. `SKIP=mojo-format git commit -m "docs(contributing): document <hook> incompatibility"`.
7. Push, create PR, enable auto-merge.

**Template for CONTRIBUTING.md subsection**:

```markdown
#### Known Hook Incompatibility: <hook-name> on <OS> / <library> < <version>

The `<hook>` hook requires **<library> <version>+** (<distro> or newer).
On <older-distro>, the hook automatically detects the incompatibility and
**skips with a warning** instead of failing your commit.

You will see output like:

\`\`\`text
WARNING: <hook> skipped: host <library> is incompatible with <binary>.
\`\`\`

CI always runs on <ci-distro> and enforces <check> before merge.
See [docs/dev/<compat-doc>.md](docs/dev/<compat-doc>.md) for full details.
```

### Steps 1-G: Expand NOTE/TODO Markers

Trigger when: cleanup issue has bare NOTE/FIXME/TODO; documentation-only; no code implementation needed.

1. **Read the issue plan** — `gh issue view <N> --comments` for prescribed structured format.
2. **Read the target file** around the NOTE marker — note exact indentation and context.
3. **Read the README** fully — find best insertion point (before "Contributing" or after "References").
4. **Expand the inline comment**:

```text
# NOTE: <original one-liner>
# Status: Deferred (not implemented in <language>)
# Why deferred: <reason — missing stdlib feature, external blocker, etc.>
# Workaround: <brief description>. See <path/to/README.md>.
# Acceptance criteria: When <condition that resolves the deferral>
# Tracked in: GitHub issue #<number> (part of #<parent>)
```

5. **Add README `## <Feature> Limitations` section** with: one-paragraph description, `### Workaround` subsection with copy-paste snippet, `### Future Support` subsection linking to tracking issue.
6. `pixi run pre-commit run --all-files` — markdownlint and general hooks only.
7. `SKIP=mojo-format git commit -m "docs(...): ..."` if on incompatible host.
8. Push, create PR (`--label "cleanup"`), enable auto-merge.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Creating empty commit on no-op review | Committing `.claude-review-fix-*.md` or a dummy change | Adds noise to git history with no value | Only commit when there are real implementation changes |
| Running full test suite for docs-only PR | Running `pixi run python -m pytest tests/ -v` | Tests unrelated to docs-only PR; CI failures were pre-existing | Skip test runs for docs-only PRs when fix plan confirms no changes needed |
| Pushing unchanged branch after no-op review | Pushing origin even with no new commits | Script handles pushing; redundant no-op push | Trust the automation script's push step; only commit if there are changes |
| Re-committing in already-done worktree | Staging `.claude-prompt-*.md` or re-editing target files to "have something to commit" | Creates noise commit with unrelated files or duplicate changes | Never commit prompt files; verify file content before touching anything |
| Creating duplicate PR | Running `gh pr create` without checking `gh pr list --head <branch>` | Creates a second open PR for the same branch, causing CI confusion | Always check for existing PRs before creating one |
| Trusting commit message alone | Skipping file verification in already-done detection | Commit could exist but be partial | Always read target files to confirm expected content is present |
| Running `just pre-commit-all` | Used `just` command runner | `just` not on PATH in this environment | Fall back to `pixi run pre-commit run --all-files` directly |
| Committing without SKIP on incompatible host | Ran full pre-commit including mojo-format | mojo-format fails with GLIBC_2.32\|2.33\|2.34 not found on Debian Buster | Use `SKIP=mojo-format git commit` — known env constraint, not a code issue |
| Inserting README section after "References" | Tried appending after references section | "Contributing" section existed; insertion point was between References and Contributing | Use Edit with "Contributing" header as anchor to insert before it |
| Performing full multi-phase security review on docs-only PR | Running Phase 1 + Phase 2 + Phase 3 review on a PR with only `.md` and `plugin.json` files | Wastes time; all findings excluded by hard exclusion rule for documentation files | Classify file types first; if all are docs/metadata, issue no-findings report immediately |
| Flagging YAML examples in SKILL.md as injection risks | SKILL.md contained example GitHub Actions YAML with expression patterns | YAML is inside a markdown code block — documentation of a pattern, not an executable workflow | Code blocks inside `.md` files are documentation; apply the same hard exclusion |
| Closing code blocks with backtick-backtick-backtick-text | Original file used ` ```text ` to close fenced blocks | markdownlint treats it as opening a new block, not closing | Always close fenced code blocks with plain backtick-backtick-backtick |
| Adding merged content without checking line lengths | Pasted detailed spec content directly after merge | Lines from the source file were 150-241 chars, failing MD013 (120 char limit) | After merging content, always run markdownlint to catch line-length violations |
| Keeping self-referential "See Also" link | Canonical file had a link to the deleted file in its See Also section | Creates a broken link after deletion | When merging, remove all references to the deleted file from the canonical file itself |
| Changing `.pre-commit-config.yaml` for hook incompatibility | Plan included adding GLIBC comment to config | File already had a full comment block from a prior PR | Always read files before editing; audit existing state first |
| Running markdownlint via `pixi run npx markdownlint-cli2` | Called `pixi run npx markdownlint-cli2 FILE.md` | `npx` not in PATH on this host | Use `pixi run pre-commit run markdownlint-cli2 --all-files` instead |
| Checking only `git status` for completeness check | Looking at untracked/modified files | Clean status does not prove issue is done | Must check log AND files AND PR existence |

## Results & Parameters

### Commit Message Formats

```text
# Small doc edit
docs(<scope>): <what was added>

<One sentence why>

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

# Hook incompatibility doc
docs(contributing): document <hook-name> <library> incompatibility

Add named subsection under "<Section>" in CONTRIBUTING.md explaining
the <hook> < <version> limitation on <distro> hosts.

Closes #<issue-number>

# Cleanup/NOTE expansion
docs(<scope>): expand NOTE marker and add Limitations section

Closes #<issue-number>
Part of #<parent>
```

### PR Body Template

```markdown
## Summary
- <bullet 1>
- <bullet 2>

## Changes
- `<path/file>`: <description>

## Verification
- [x] `pixi run pre-commit run --all-files` passes (markdownlint, trailing-whitespace, etc.)
- [x] Documentation-only — no language tests required

Closes #<issue-number>
```

### Key Decision Signals

| Signal | Command |
| ------ | ------- |
| Commit message matches issue title | `git log --oneline -5` |
| PR already exists on branch | `gh pr list --head <branch>` |
| Target files contain expected changes | Read each file with line range |
| Working tree is clean | `git status` |
| CI failures pre-exist on main | Check main branch CI status |

### Pre-commit Invocation Reference

```bash
# Full run (preferred — not `just pre-commit-all`)
pixi run pre-commit run --all-files

# Markdownlint only
SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files

# Commit on GLIBC-incompatible host
SKIP=mojo-format git commit -m "docs(<scope>): <summary>"
```

### Docs-Only Security Review Decision Tree

```text
PR changed files → all .md / static .json?
├── YES → No attack surface → issue clean no-findings report
└── NO  → At least one executable/config file?
    ├── GitHub Actions .yml → check for untrusted input in run: steps
    ├── Python/JS/TS/Shell  → full security review
    └── Config with user input → full security review
```

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | Issues #3087, #3089, #3150, #3253 (auto-impl, preflight, review-fix, hook-doc) | Member skills |
| ProjectMnemosyne | PR security reviews, skill cleanup issues | Member skills |
