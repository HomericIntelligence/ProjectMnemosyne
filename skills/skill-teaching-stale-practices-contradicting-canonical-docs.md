---
name: skill-teaching-stale-practices-contradicting-canonical-docs
description: "When a skill or guide teaches practices contradicting CLAUDE.md or other canonical docs, wholesale rewrite (not patching) is required to prevent contradiction persistence. Use when: (1) a skill teaches deprecated tools (flake8, black, requirements.txt, setup.py) contradicting CLAUDE.md Language Preference, (2) a skill references stale Python versions (3.8–3.9) contradicting current baseline (3.10+), (3) supporting files (session logs, references) contain the same stale practices as the main skill file, (4) patching individual sections would leave dangerous contradictions elsewhere, (5) stale guidance could mislead downstream consumers before they discover the newer canonical docs."
category: tooling
date: 2026-06-11
version: "1.1.0"
user-invocable: false
verification: verified-ci
history: skill-teaching-stale-practices-contradicting-canonical-docs.history
tags: [skill-quality, contradiction-resolution, canonical-docs, wholesale-rewrite, skill-maintenance]
---

# Resolving Canonical Contradictions in Skills

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-11 |
| **Objective** | Establish pattern for fixing skills that teach practices contradicting canonical docs (CLAUDE.md, project standards) |
| **Outcome** | Successful wholesale rewrite of github-actions-python-cicd skill from stale flake8/black/Python 3.8–3.9 to current stack (pixi/ruff/Python 3.10–3.13); PR #1014 reached green CI after a rebase that resolved a modify/delete conflict on the deleted `references/notes.md` — the wholesale-rewrite + delete-supporting-files approach is validated end-to-end |
| **Verification** | verified-ci (ProjectHephaestus issue #720, PR #1014 reached green CI: pre-commit all-hooks green, 4134 tests pass, modify/delete conflict resolved on rebase) |

## When to Use

- A skill or guide teaches practices contradicting the current CLAUDE.md or canonical standards
- Supporting files (notes.md, references/, examples/) teach the same stale practices as the main file
- Patching individual sections would leave dangerous contradictions elsewhere
- The skill is actively used and its stale guidance could mislead downstream consumers
- The contradictions span multiple dimensions (tooling, versions, patterns, build systems)

## Verified Workflow

### Quick Reference

```bash
# 1. Identify contradictions: skill vs. CLAUDE.md
grep -E "flake8|black|src/|requirements.txt|setup.py" skills/github-actions-python-cicd/SKILL.md
grep -n "^## Language Preference" CLAUDE.md

# 2. Determine scope: is patching sufficient or wholesale rewrite?
# If contradictions span >2 sections, plan for wholesale rewrite

# 3. Find ALL supporting files (not just .md)
find skills/github-actions-python-cicd/ -type f | grep -v .git

# 4. Plan verification commands (map each contradiction to a testable criterion)
# Python 3.8/3.9 removed → grep confirms matrix is 3.10+ only
# flake8 removed → no flake8 tokens anywhere in directory
# src/ layout removed → only "hephaestus/" references in examples

# 5. Delete contradictory supporting files (wholesale removal, not patching)
git rm skills/github-actions-python-cicd/references/notes.md

# 6. Rewrite the main skill file with CLAUDE.md cross-references
# Include quotations: See CLAUDE.md § Language Preference
# Document why EACH choice contradicted the old version

# 7. Verify comprehensively (directory-level, not file-level)
! grep -rnE 'flake8|black|requirements.txt|setup.py|src/' skills/github-actions-python-cicd/
grep -n 'ruff check' skills/github-actions-python-cicd/SKILL.md
grep -n 'python-version.*3\.1[0-3]' skills/github-actions-python-cicd/SKILL.md
pre-commit run markdownlint-cli2 --files skills/github-actions-python-cicd/SKILL.md
```

### Detailed Steps

1. **Identify the contradiction**: Diff the skill's recommended practices against CLAUDE.md
   - Read CLAUDE.md § Language Preference and § Python Development Guidelines
   - Note every tool, version, and pattern that differs from the skill
   - Classify: How many sections contradict? (1–2 sections = patch candidate; 3+ = rewrite)

2. **Find ALL supporting files**: Don't assume skill is a single .md file
   ```bash
   find skills/github-actions-python-cicd/ -type f
   # May find: SKILL.md, references/notes.md, examples/, session_log.md, etc.
   ```
   **Every supporting file must be audited** — stale session logs are the most common vector for contradiction persistence.

3. **Plan verification BEFORE editing**: Map each contradiction to a testable criterion
   - Python 3.8/3.9 removed → grep confirms matrix is 3.10–3.13 only
   - flake8 removed → `! grep -rn 'flake8'` returns exit 0 (no matches)
   - src/ layout removed → only "hephaestus/" references in examples
   - requirements.txt removed → `! grep -rn 'requirements'` returns exit 0
   - All changes logged as verification commands (copy-paste ready)

4. **Delete contradictory supporting files**: A stale session log that contradicts CLAUDE.md cannot be "fixed in place"
   - If `references/notes.md` teaches flake8, **delete it entirely** (`git rm`)
   - If `examples/` contains setup.py, **delete it entirely** (`git rm examples/`)
   - Do NOT try to patch — wholesale removal is cleaner and leaves no residue

5. **Rewrite the main skill file**: Use CLAUDE.md sections as the single source of truth
   - Include quotations: `See CLAUDE.md § Language Preference`
   - Document why EACH choice contradicted the old version
   - Add a "Canonical References" section linking back to CLAUDE.md with specific § numbers
   - Explain the consequence of the old practice (e.g., "flake8 doesn't catch unused imports the way ruff does")

6. **Verify comprehensively**: Directory-level verification, not file-level
   ```bash
   # Check ENTIRE directory for stale tokens (critical — catches hidden files)
   ! grep -rnE 'flake8|black|requirements.txt|setup.py|src/' skills/github-actions-python-cicd/
   # Exit 0 ✓ (no stale tokens found)

   # Positive match: confirm correct version/pattern is present
   grep -n 'ruff check' skills/github-actions-python-cicd/SKILL.md
   grep -n 'python-version.*3\.1[0-3]' skills/github-actions-python-cicd/SKILL.md

   # Format gate
   pre-commit run markdownlint-cli2 --files skills/github-actions-python-cicd/SKILL.md
   ```

7. **Commit with evidence**: Reference the verification commands in commit message
   - Title: `feat: rewrite github-actions-python-cicd skill to match CLAUDE.md stack`
   - Body: List every verification command that passed
   - Rationale: Explain why wholesale rewrite was necessary vs. patching

### Deleting a supporting file can resurface as a rebase conflict

`git rm`-ing a stale supporting file (e.g. `references/notes.md`) is not the
end of it: if main independently MODIFIES that same file before your PR
merges, the rebase produces a **modify/delete conflict**
(`CONFLICT (modify/delete): <path> deleted in <commit> and modified in
HEAD`). Resolve it the same way you decided to delete in the first place —
re-confirm the base/main copy is still the stale content
(`git show origin/main:<path> | grep -niE '<stale-tokens>'`), then `git rm
<path>` and `GIT_EDITOR=true git rebase --continue`. This is exactly what
blocked PR #1014 until rebased. See `pr-rebase-conflict-resolution-patterns`
for the modify/delete rebase resolution.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Patch individual sections | Replace flake8→ruff in SKILL.md, leave notes.md | references/notes.md still taught flake8; contradiction persisted | Always search entire directory for contradictory files; stale session logs must be deleted |
| Skip directory-wide verification | Only grepped SKILL.md for "flake8\|black" | Missed references/notes.md with same anti-patterns | Verification must cover all files; use `find` + `grep -r` before committing |
| Rewrite without mapping to CLAUDE.md | Updated tool chain but didn't cross-reference docs | Future maintainers couldn't tell why choices changed | Always include CLAUDE.md § section references in the rewritten skill |
| Assume supporting files are auto-generated | Left references/ as-is thinking they were notes | Session logs are human-created and persist after rewrite | Audit supporting directories; delete anything created by human hands that contradicts |
| Verify with inline grep only | Ran `grep flake8 SKILL.md` | Missed `references/notes.md:## Tools to Remove: flake8, black` | Use `-r` flag: `grep -r` not `grep` to catch nested files |

## Results & Parameters

### Applied to issue #720

**Original state**:
- `skills/github-actions-python-cicd/SKILL.md` (438 lines) taught flake8, black, Python 3.8–3.12, requirements.txt, setup.py, src/ layout
- `skills/github-actions-python-cicd/references/notes.md` (stale session log) reinforced the same practices
- Examples used setup.py and src/ layout patterns
- Multiple Python version matrix entries for 3.8 and 3.9

**Rewritten state**:
- SKILL.md (242 lines, −45% bloat) teaches pixi, ruff, mypy, yamllint, Python 3.10–3.13
- Deleted `references/notes.md` entirely (stale session log)
- Deleted contradictory example files (setup.py patterns)
- Added "Canonical References" section with CLAUDE.md § links
- Added "Install Patterns — which to use when" table explaining pixi vs other patterns
- Cross-referenced CLAUDE.md § Language Preference, § Python Development Guidelines, § Version Management, § Common Commands, § Pre-commit Hooks

### Verification Commands (All Passed)

```bash
# AC1: No obsolete tokens anywhere in skill directory
! grep -rnE 'flake8|\bblack\b|\bsrc/|requirements\*\.txt|requirements-dev\.txt|setup\.py' \
    skills/github-actions-python-cicd/
# Exit 0 ✓

# AC2: Python 3.10-3.13 matrix present; no 3.8/3.9
grep -nE '"3\.10", "3\.11", "3\.12", "3\.13"' skills/github-actions-python-cicd/SKILL.md
# Prints line 75 ✓

# AC3: CLAUDE.md cross-referenced (≥3 times); all sections verified
grep -nE 'CLAUDE\.md' skills/github-actions-python-cicd/SKILL.md | wc -l
# 9 references ✓
grep -qE "^## Language Preference" CLAUDE.md && echo "✓" || echo "✗"
# ✓ (and 4 other sections verified)

# AC4: All GitHub Actions digest-pinned with version comments
! grep -nE '^\s*-?\s*uses:\s*[A-Za-z0-9_/.-]+@v[0-9]+\s*$' skills/github-actions-python-cicd/SKILL.md
# Exit 0 ✓

# AC5: Markdownlint format gate
pre-commit run markdownlint-cli2 --files skills/github-actions-python-cicd/SKILL.md
# PASSED ✓
```

### Canonical References Template

When rewriting a skill to match canonical docs, include this section:

```markdown
## Canonical References

This skill reflects **ProjectHephaestus CLAUDE.md as the single source of truth** for tooling decisions:

| Topic | CLAUDE.md Section | Verified | Notes |
|-------|-------------------|----------|-------|
| Language version | § Language Preference (line N) | 2026-06-05 | Python 3.10+ is the floor; no 3.8/3.9 support |
| Linter choice | § Python Development Guidelines (line N) | 2026-06-05 | ruff replaces flake8 + black for speed and coverage |
| Package manager | § Environment Setup (line N) | 2026-06-05 | pixi is the canonical environment manager |
| Test command | § Common Commands (line N) | 2026-06-05 | `pixi run pytest` not pytest directly |
| Precommit hooks | § Pre-commit Hooks (line N) | 2026-06-05 | All hooks managed via `.pre-commit-config.yaml` |
```

### Checklist for Wholesale Skill Rewrite

When you encounter a skill contradicting canonical docs, apply this checklist:

```markdown
## Checklist for Wholesale Skill Rewrite

- [ ] Read all relevant CLAUDE.md sections being contradicted
- [ ] Find ALL supporting files (use `find`, not just .md filenames)
- [ ] Audit each supporting file for contradictions
- [ ] Plan verification commands (map contradictions to testable criteria)
- [ ] Delete contradictory supporting files (use `git rm`, not patching)
- [ ] Rewrite main skill file with CLAUDE.md section references
- [ ] Add Canonical References table with verification dates
- [ ] Run directory-level verification (`grep -rn` over entire skill dir)
- [ ] Run all verification commands before committing
- [ ] Commit with verification evidence
- [ ] Push and create PR
```

## Related Skills

- `stale-documentation-audits-and-sync` — Detect contradictions between code and docs (counts, future work)
- `dry-consolidate-to-canonical-refactor` — Consolidate duplicate implementations into single canonical source
- `skill-corpus-merge-consolidation-workflow` — Maintain skills corpus: deduplication, merging, format migration
- `code-quality-enforcement-gates` — Decide when to promote warnings to errors vs. accepting legacy patterns

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #720: github-actions-python-cicd skill modernization | Rewritten 438 lines → 242 lines; deleted stale supporting files; all verifications pass; PR #1014 reached green CI after a rebase resolved a modify/delete conflict on the deleted `references/notes.md` (pre-commit 32/32 hooks + 4134 tests green) |
