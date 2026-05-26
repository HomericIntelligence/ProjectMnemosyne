---
name: mkdocs-nav-cleanup
description: 'Fix and PREVENT MkDocs build failures from nav or cross-references pointing
  at deleted files. Use when: (1) about to push a PR that deletes documentation/ADR/repro
  files (run pre-deletion audit first), (2) CI ''Deploy Documentation'' job fails after
  deleting doc stubs, (3) mkdocs build --strict reports missing files, (4) PR deletes
  placeholder docs but mkdocs.yml nav still references them, (5) --strict rejects a
  relative link like ../../docs/dev/file.md that escapes the docs/ root.'
category: ci-cd
date: 2026-05-25
version: 1.2.0
user-invocable: false
verification: verified-ci
history: mkdocs-nav-cleanup.history
tags: []
---

## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mkdocs-nav-cleanup |
| **Category** | ci-cd |
| **Trigger** | PR about to delete (or has deleted) documentation files referenced by `mkdocs.yml` or by other surviving docs |
| **Scope** | mkdocs.yml nav section + every surviving markdown file under `docs/` |
| **Verification** | verified-ci |
| **History** | [changelog](./mkdocs-nav-cleanup.history) |

## When to Use

- **Preferred (preventive):** A PR is about to delete one or more `.md` files (docs, ADRs,
  reproductions, workflow stubs). Run the Pre-Deletion Audit before pushing.
- A PR deletes placeholder/stub documentation files and CI "Deploy Documentation" fails
- `mkdocs build --strict` reports "Documentation file 'X.md' specified in nav is not found"
- A remaining markdown file contains a relative link to a now-deleted file
- Pre-existing link-check failures (root-relative paths) conflated with PR-caused failures
- A relative link uses `../../docs/dev/` from inside `docs/adr/` — escaping the mkdocs
  `docs/` root under `--strict`
- A surviving doc enumerates inventory (e.g. `"ADR-001 through ADR-XYZ"` in
  `docs/README.md`) that becomes stale when entries are removed — mkdocs does not catch
  this; the basename audit does

## Verified Workflow

### Quick Reference

```bash
# Pre-deletion audit — run BEFORE pushing any documentation deletion PR
FILES_TO_DELETE="docs/adr/ADR-014-foo.md docs/dev/mojo-jit-crash-workaround.md"
PATTERN=$(echo "$FILES_TO_DELETE" | tr ' ' '\n' | xargs -n1 basename | sed 's/\.md$//' | paste -sd'|')
grep -rn -E "$PATTERN" docs/ mkdocs.yml --exclude-dir=.git
# Any hits MUST be fixed in the same commit as the deletion.
```

### Pre-Deletion Audit (preferred path)

`mkdocs --strict` catches broken links INSIDE the doc tree at build time, but there is
no `mkdocs check-links --dry-run` to warn you BEFORE the deletion lands. Without an
upfront audit, each CI run only surfaces the first batch of broken links it encounters —
a deletion PR with cross-references in N surviving docs typically takes N red CI runs
to fix incrementally. Run this audit in the deletion PR's branch before pushing:

1. **Enumerate the deletion set** — list every `.md` file the PR removes:

   ```bash
   FILES_TO_DELETE=$(git diff --name-only --diff-filter=D origin/main...HEAD -- '*.md')
   echo "$FILES_TO_DELETE"
   ```

2. **Build a basename grep pattern** — basenames catch relative links, absolute links,
   and bare filename mentions in prose (e.g. enumeration lists):

   ```bash
   PATTERN=$(echo "$FILES_TO_DELETE" | xargs -n1 basename | sed 's/\.md$//' | paste -sd'|')
   ```

3. **Grep surviving docs + mkdocs.yml** for any reference to the to-be-deleted files:

   ```bash
   grep -rn -E "$PATTERN" docs/ mkdocs.yml --exclude-dir=.git
   ```

4. **Fix every hit in the same commit as the deletion.** Options per hit:
   - Surviving doc links to deleted file → remove or repoint the link
   - `mkdocs.yml` nav entry → remove the entry (and the parent section if empty)
   - Inventory enumeration (`ADR-001 through ADR-XYZ`) → update the range
   - Surviving doc has an unavoidable external reason to keep its reference → repoint to
     an archive URL or footnote the deletion; never leave the bare link

5. **Re-run the grep — must return empty** before committing.

6. **(Optional, when available locally) run `mkdocs build --strict`** to double-check.

### Post-Hoc Cleanup (fallback when CI has already failed)

If the deletion PR already shipped and CI is red, the original v1.1.0 workflow still
applies — fix the next batch and re-run the audit grep before re-pushing to avoid
another red iteration:

1. **Identify deleted files** — check the PR diff for removed `.md` files
2. **Audit mkdocs.yml nav** — find all nav entries referencing the deleted files
3. **Audit remaining docs for cross-links** using the Pre-Deletion Audit grep above —
   do this in one pass; do NOT push partial fixes
4. **Remove nav entries** from `mkdocs.yml` (and parent sections if empty)
5. **Remove or repoint broken cross-links** in surviving docs
6. **Verify with the grep — must return empty**
7. **Run pre-commit on changed files**:

   ```bash
   pre-commit run --files mkdocs.yml docs/path/to/changed.md
   ```

8. **Commit and push**

### Relative Link Escaping the docs/ Root

`mkdocs --strict` rejects relative links that resolve outside the `docs/` directory:

```markdown
# WRONG — from docs/adr/ADR-014.md, this goes to repo-root then docs/dev/
[link](../../docs/dev/mojo-jit-crash-workaround.md)

# CORRECT — from docs/adr/, ../dev/ stays within docs/
[link](../dev/mojo-jit-crash-workaround.md)
```

**Rule**: Count `../` hops from the file location. From `docs/adr/file.md`:

- `../` goes to `docs/` (safe)
- `../../` goes to repo root (escapes docs/, rejected by --strict)

**Diagnosis**: `mkdocs build --strict` error:
`"path '../../docs/dev/...' is not within the documentation directory"`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Removing entire section blocks at once | Used Edit to replace multi-line nav blocks covering Core + Advanced + Development | Initially included a surviving file in the removal | Always check which files in a nav section still exist before removing the whole block |
| Treating link-check failures as in-scope | Considered fixing 20 root-relative path errors in unrelated files | These were pre-existing on main, unrelated to the PR | Verify pre-existing CI failures with `gh run list --branch main --workflow "Check Markdown Links"` before scoping fixes |
| Push deletion PR with no upfront cross-reference audit (iteration 1) | Scorched-earth deletion PR (~32 files) pushed; mkdocs `--strict` failed on two surviving dev docs both linking to a just-deleted JIT-crash workaround page | mkdocs only reports broken links at build time and stops on the first batch it finds; without a basename grep beforehand, the first red CI run only surfaces the most prominent hits | Run the Pre-Deletion Audit grep in the same commit as the deletion — do not rely on CI to enumerate broken links |
| Fix the CI-reported links and re-push (iteration 2) | After fixing the two dev docs, pushed again; mkdocs `--strict` failed AGAIN on a surviving ADR (kept due to external references) that linked to a different deleted ADR and to the same deleted JIT workaround | Incremental fixing addresses only what the previous CI run surfaced, not the full deletion fallout; partial fixes guarantee at least one more red iteration per missed referrer | After ANY CI failure caused by a deletion, immediately run the full basename audit grep against the deletion set before pushing the next fix — never patch only the file CI named |
| Rely on mkdocs to catch stale inventory enumerations (iteration 3, quieter case) | A surviving `docs/README.md` enumerated `"ADR-001 through ADR-008, ADR-010, ADR-012–ADR-015"`; two of those ADRs were deleted but mkdocs ignored the prose mention because it was not a markdown link | mkdocs `--strict` only validates parsable link targets, not bare filename or ID mentions in prose | Include basename grep (not just link-target grep) in the Pre-Deletion Audit so inventory lists, footnotes, and prose references to deleted artifacts are caught alongside real links |

## Results & Parameters

**Recommended pre-deletion audit (copy-paste):**

```bash
# Inside a feature branch with deletions staged or already committed
FILES_TO_DELETE=$(git diff --name-only --diff-filter=D origin/main...HEAD -- '*.md')
if [ -z "$FILES_TO_DELETE" ]; then
  echo "No .md deletions detected."
else
  PATTERN=$(echo "$FILES_TO_DELETE" | xargs -n1 basename | sed 's/\.md$//' | paste -sd'|')
  echo "Auditing for references to: $PATTERN"
  grep -rn -E "$PATTERN" docs/ mkdocs.yml --exclude-dir=.git || echo "Clean — safe to push."
fi
```

**Expected output when clean:** the literal string `Clean — safe to push.` (or empty grep
output). Any other output is a list of `file:line:match` triples that MUST be addressed
before the deletion commit is pushed.

**Key distinction — two independent CI failure types:**

1. **In-scope**: `build-docs` fails because nav references deleted files → fix
   `mkdocs.yml` and cross-links (and prevent next time with the Pre-Deletion Audit)
2. **Out-of-scope (pre-existing)**: `link-check` fails on root-relative paths (e.g.
   `/.claude/shared/`) → do not fix in this PR; confirm with
   `gh run list --branch main --workflow "..."` that it was already failing before the PR

**Empirical result of the pre-deletion audit:** running the basename grep post-hoc
against the deletion set after the third fix landed returned a clean result — confirming
that a single up-front audit pass would have surfaced all three iterations' worth of
broken references in one commit.
