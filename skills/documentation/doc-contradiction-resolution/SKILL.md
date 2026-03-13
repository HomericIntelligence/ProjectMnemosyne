# Skill: Resolve Documentation Contradictions Between Project Files

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-20 |
| Issue | #758 |
| PR | #871 |
| Category | documentation |
| Objective | Remove `--label "appropriate-label"` from `CONTRIBUTING.md` PR creation example to match CLAUDE.md's "Never use labels" policy |
| Outcome | Success - contradiction resolved, PR created and auto-merge enabled |

## When to Use

Trigger this skill when:

- Two project docs give contradictory guidance on the same topic (e.g., labels, branch naming, commit format)
- CLAUDE.md contains an explicit policy rule that conflicts with an example in CONTRIBUTING.md
- A contributor or AI agent reports confusion from inconsistent documentation
- `.claude/shared/` reference files may also be out of sync with the canonical source

## Verified Workflow

### 1. Identify the contradiction

```bash
# Confirm the conflicting text exists in each file
grep -n "label" CONTRIBUTING.md
grep -n "label" CLAUDE.md
grep -n "label" .claude/shared/pr-workflow.md
```

### 2. Determine the canonical policy

The order of authority in this project:

1. `CLAUDE.md` — operational guidance for agents and contributors (highest authority)
2. `.claude/shared/pr-workflow.md` — detailed PR process (aligns with CLAUDE.md)
3. `CONTRIBUTING.md` — contributor-facing guide (must follow CLAUDE.md)

When CLAUDE.md has an explicit, unambiguous rule (e.g., "Never use labels"), that wins.

### 3. Check all three files for the offending text

```bash
grep -n -- "--label" CONTRIBUTING.md
grep -n -- "--label" .claude/shared/pr-workflow.md
grep -n "label" CLAUDE.md
```

### 4. Make the minimal fix

Edit only the file(s) that are wrong. Do **not** modify the canonical source.

For the label contradiction specifically:

- Remove `--label "appropriate-label"` from the `gh pr create` code block in `CONTRIBUTING.md`
- If the preceding line ends with `\` (bash line continuation), also remove the `\` from that line

### 5. Verify no regressions

```bash
# Confirm the offending text is gone
grep -- "--label" CONTRIBUTING.md   # should return nothing

# Confirm the canonical policy is unchanged
grep "Never use labels" CLAUDE.md   # should still be present
```

### 6. Commit, push, and PR

```bash
git add CONTRIBUTING.md
git commit -m "fix(docs): Remove --label flag from CONTRIBUTING.md PR example

Resolves contradiction between CLAUDE.md (\"Never use labels\") and
CONTRIBUTING.md which included --label in the gh pr create example.

Closes #<issue>"

git push -u origin <branch>
gh pr create \
  --title "fix(docs): Resolve PR label contradiction between CLAUDE.md and CONTRIBUTING.md" \
  --body "Closes #<issue>"
gh pr merge --auto --rebase <pr-number>
```

## Failed Attempts

**Skill tool was denied**: Attempted to use `commit-commands:commit-push-pr` skill but it was denied by the permission mode (`don't ask mode`). Fell back to direct Bash git commands — this works fine and is the correct fallback.

**No other failures**: The fix was a 2-line removal. Pre-commit hooks passed immediately because only Markdown was modified (Python/YAML/Shell linters were all skipped).

## Results & Parameters

### Actual change made

| File | Location | Before | After |
|------|----------|--------|-------|
| `CONTRIBUTING.md` | Line ~190-191 | `- [x] Documentation updated" \` + `--label "appropriate-label"` | `- [x] Documentation updated"` |

### Files checked but not changed

| File | Status |
|------|--------|
| `CLAUDE.md` | Already correct — "Never use labels" rule present |
| `.claude/shared/pr-workflow.md` | Already correct — no `--label` usage |

### Pre-commit hook behavior for Markdown-only changes

Skipped (no Python/YAML/Shell files touched):

- Ruff Format Python
- Ruff Check Python
- Mypy Type Check Python
- Check Type Alias Shadowing
- YAML Lint
- ShellCheck
- Validate Model Config Naming
- Check Model Config Filename/model_id Consistency

Pass automatically:

- Markdown Lint
- Trim Trailing Whitespace
- Fix End of Files
- Check for Large Files
- Fix Mixed Line Endings

### Key insight: check `.claude/shared/pr-workflow.md` too

The issue notes explicitly called out `.claude/shared/pr-workflow.md` as a possible third source of the contradiction. Always verify all related files before declaring the fix complete — in this case it was already clean, requiring no change.
