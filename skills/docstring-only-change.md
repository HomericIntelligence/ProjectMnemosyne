---
name: docstring-only-change
description: 'Workflow for implementing docstring-only changes to Python scripts:
  expand module docstrings with routing rules, target structure tables, or auxiliary
  subdirectory documentation. Use when a GitHub issue requests documenting implicit
  behaviour in a module docstring with no code or test changes required.'
category: documentation
date: 2026-03-15
version: 1.0.0
user-invocable: false
---
## Overview

| Field | Value |
|-------|-------|
| **Category** | documentation |
| **Complexity** | XS (extra-small) |
| **Typical runtime** | < 3 minutes |
| **Key tools** | Read, Edit, Bash (python3 -m py_compile, git, gh) |

## When to Use

- A GitHub issue requests documenting existing implicit behaviour in a Python module docstring
- The change is pure docstring prose — no function signatures, tests, or logic changed
- The issue specifies exact content to add (e.g. target structure table, auxiliary routing block)
- All existing tests must pass without modification after the edit
- The script already has a module-level docstring that needs to be expanded

## Verified Workflow

1. **Read the prompt file** — parse the issue requirements including exact sections to add and their
   content. The prompt file is usually at the repo root as `.claude-prompt-<issue-number>.md`.
2. **Read the target script** — confirm the current module docstring structure and find the
   exact insertion point (usually the end of the docstring, just before the closing `"""`).
3. **Apply Edit** — use `old_string` anchored to unique surrounding text (the line before and
   after the insertion point) to avoid ambiguity.
4. **Verify Python syntax** — run `python3 -m py_compile <script>` to confirm no syntax errors
   were introduced.
5. **Run existing tests** — run the script's test suite (e.g. `python3 -m pytest tests/scripts/`)
   with no new tests needed; all 21 (or however many exist) should pass.
6. **Stage only the modified file** — use `git add <specific-file>` to avoid staging untracked
   `__pycache__/` directories or other noise.
7. **Commit** — use conventional commit format `docs(scope): description` with `Closes #N` on
   its own line.
8. **Push and create PR** — `git push -u origin <branch>` then `gh pr create`.
9. **Enable auto-merge** — `gh pr merge --auto --rebase <pr-number>`.

### Key Edit Pattern

Anchor `old_string` on the last unique line before the closing `"""` to insert new content:

```python
# old_string example — the closing triple-quote is the unique anchor
old_string = "    last existing line in docstring\n\"\"\""

# new_string — original line + new content + closing quote
new_string = '''    last existing line in docstring

Auxiliary subdirectory routing
-------------------------------
    references/   -> plugin root (not inside skills/<name>/)
    others/       -> inside skills/<skill-name>/
    hidden dirs   -> excluded (not copied)
"""'''
```

### Commit Message Format

```text
docs(<scope>): <what was documented>

<One sentence explaining why — what implicit behaviour is now explicit.>

Closes #<issue-number>

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### PR Body Format

```markdown
## Summary

- Expanded module docstring in `scripts/<script>.py` to document <what>
- Added <section name> block covering <routing rules / target structure / etc.>

## Test plan

- [x] `python3 -m py_compile scripts/<script>.py` — syntax valid
- [x] Existing test suite passes (N tests, 0 failures)
- [x] Documentation-only change — no new tests required

Closes #<issue-number>
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Staging with `git add -A` | Added all untracked files | Picked up `tests/__pycache__/` and `tests/scripts/__pycache__/` directories | Always use `git add <specific-file>` for docstring-only changes to keep the commit clean |
| Using Skill tool for commit | Invoked `commit-commands:commit` skill | Skill tool denied in don't-ask mode for this session | Fall back to direct `git commit -m "$(cat <<'EOF'...EOF)"` bash command |
| Writing new docstring from scratch | Attempted to overwrite the entire docstring | Risk of losing existing content and introducing whitespace differences | Always Read the file first, then use Edit with targeted `old_string`/`new_string` |

## Results & Parameters

### Session Details (Issue #3771)

- **Repo**: HomericIntelligence/ProjectOdyssey
- **Branch**: `3771-auto-impl`
- **Script**: `scripts/migrate_odyssey_skills.py`
- **PR**: #4792
- **Date**: 2026-03-15

### What Was Changed

The module docstring was expanded with two new blocks:

1. **Target structure** section — showed all four output paths (`SKILL.md`,
   `scripts/`, `templates/`, `references/`) alongside the existing `SKILL.md` entry.
2. **Auxiliary subdirectory routing** block — documented three routing rules:
   - `references/` directories go to plugin root (not inside `skills/<name>/`)
   - Other named subdirectories go inside `skills/<skill-name>/`
   - Hidden directories (`.git`, `__pycache__`) are excluded
3. **Category Routing** rename — the existing "Subdir Routing" label was renamed to
   "Category Routing" to disambiguate it from the new auxiliary routing documentation.

### Validation Commands

```bash
# Verify syntax
python3 -m py_compile scripts/migrate_odyssey_skills.py

# Run existing tests (no new tests needed)
python3 -m pytest tests/scripts/ -v

# Stage only the modified file
git add scripts/migrate_odyssey_skills.py

# Commit
git commit -m "$(cat <<'EOF'
docs(scripts): document subdir routing rules in migrate_odyssey_skills docstring

Closes #3771

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

### Auto-merge Command

```bash
gh pr merge --auto --rebase <pr-number>
```
