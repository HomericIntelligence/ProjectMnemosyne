---
name: mkdocs-nav-cleanup
description: 'Fix MkDocs build failures from nav referencing deleted files or relative
  links escaping the docs/ tree. Use when: (1) CI ''Deploy Documentation'' job fails
  after deleting doc stubs, (2) mkdocs build --strict reports missing files, (3) PR
  deletes placeholder docs but mkdocs.yml nav still references them, (4) --strict
  rejects a relative link like ../../docs/dev/file.md that escapes the docs/ root.'
category: ci-cd
date: 2026-03-27
version: 1.1.0
user-invocable: false
---

## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | mkdocs-nav-cleanup |
| **Category** | ci-cd |
| **Trigger** | CI Deploy Documentation failure after deleting placeholder doc stubs |
| **Scope** | mkdocs.yml nav section + any cross-links in remaining docs |

## When to Use

- A PR deletes placeholder/stub documentation files and CI "Deploy Documentation" fails
- `mkdocs build --strict` reports "Documentation file 'X.md' specified in nav is not found"
- A remaining markdown file contains a relative link to a now-deleted file
- Pre-existing link-check failures (root-relative paths) conflated with PR-caused failures
- A relative link uses `../../docs/dev/` from inside `docs/adr/` — escaping the mkdocs
  `docs/` root under `--strict`

## Verified Workflow

1. **Identify deleted files** — check the PR diff for removed `.md` files
2. **Audit mkdocs.yml nav** — find all nav entries referencing the deleted files
3. **Audit remaining docs for cross-links** — grep for relative links pointing to deleted files:

   ```bash
   grep -r "deleted-file-name" docs/ mkdocs.yml
   ```

4. **Remove nav entries** from `mkdocs.yml` — delete the entries (and their parent section
   if now empty)
5. **Remove broken relative links** from remaining docs — remove or update bullet points
   referencing deleted files
6. **Verify no remaining references**:

   ```bash
   grep -r "deleted-file1\|deleted-file2" docs/ mkdocs.yml
   ```

7. **Run pre-commit on changed files**:

   ```bash
   pre-commit run --files mkdocs.yml docs/path/to/changed.md
   ```

8. **Commit** with message format `fix: Address review feedback for PR #<N>`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Removing entire section blocks at once | Used Edit to replace multi-line nav blocks covering Core + Advanced + Development | Initially included Release Process (a surviving file) in the removal | Always check which files in a nav section still exist before removing the whole block |
| Treating link-check failures as in-scope | Considered fixing 20 root-relative path errors in CLAUDE.md, docs/adr/, notebooks/README.md | These were pre-existing on main, unrelated to the PR | Verify pre-existing CI failures with `gh run list --branch main --workflow "Check Markdown Links"` before scoping fixes |

## Results & Parameters

**What was fixed (PR #3308, issue #3142):**

- `mkdocs.yml`: Removed `Core` section (8 entries), 6 `Advanced` entries, 3 `Development`
  entries — all referencing deleted placeholder stubs
- `docs/advanced/benchmarking.md:666`: Removed `[SIMD Integration Guide](integration.md)` bullet

**Verification command:**

```bash
grep -r "core/project-structure\|core/workflow\|core/shared-library\|core/testing-strategy\|core/agent-system\|core/mojo-patterns\|core/configuration\|core/paper-implementation\|advanced/performance\|advanced/custom-layers\|advanced/visualization\|advanced/integration\|advanced/distributed-training\|advanced/debugging\|dev/architecture\|dev/ci-cd\|dev/api-reference" docs/ mkdocs.yml
```

Expected output: empty (no matches).

**Key distinction — two independent CI failure types:**

1. **In-scope**: `build-docs` fails because nav references deleted files → fix mkdocs.yml
   and cross-links
2. **Out-of-scope (pre-existing)**: `link-check` fails on root-relative paths (e.g.
   `/.claude/shared/`) → do not fix in this PR; confirm with
   `gh run list --branch main --workflow "..."` that it was already failing before the PR

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
