---
name: placeholder-and-stub-doc-lifecycle
description: >-
  Manage the full lifecycle of placeholder and stub documentation. Use when:
  (1) stub files contain only placeholder text and should be deleted under YAGNI,
  (2) a navigation index loses sections after stub deletion and needs a deferred
  comment placeholder, (3) a design doc Future Improvements list needs structured
  deferral annotations, (4) a placeholder doc needs rewriting with accurate codebase-
  grounded content (quickstart, installation, README, or other guides),
  (5) an existing installation doc needs IDE setup section or version-constraint tightening.
category: documentation
date: 2026-05-19
version: 1.0.0
user-invocable: false
history: placeholder-and-stub-doc-lifecycle.history
tags:
  - placeholder
  - stub
  - documentation
  - yagni
  - deferred
  - installation
  - readme
  - rewrite
---

# Placeholder and Stub Doc Lifecycle

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Canonical skill for all placeholder/stub doc decisions: delete, defer, annotate, or rewrite |
| **Outcome** | Union of 7 absorbed skills covering the full decision tree |
| **Status** | Canonical (merged from M47 cluster) |

## When to Use

Apply this skill when encountering any placeholder or stub documentation situation:

1. **Delete** — files contain only boilerplate like `Content here.` and the YAGNI principle applies
2. **Defer (index comment)** — a navigation hub (`docs/index.md`) lost a section because stubs were
   deleted and a follow-up issue tracks restoring it when real docs exist
3. **Annotate deferral** — a design doc `Future Improvements` section has bare bullet items confirmed
   unimplemented; future contributors need status/why/acceptance-criteria to avoid re-investigating
4. **Rewrite** — a placeholder doc (quickstart, installation, README) must be replaced with accurate
   content verified against the live codebase
5. **Extend** — an existing real installation doc needs an IDE setup section or tighter version
   constraints in prerequisites

**Do NOT use** when:

- Files are auto-generated from code (edits get overwritten)
- Items are actively in-flight (mark WIP instead)
- Only one or two links are missing from an index (add a TODO inline)

## Verified Workflow

### Decision Tree

```text
Stub file exists?
  Yes → Does it have real content?
    No  → Delete it (YAGNI) → update referencing files → see "Delete stubs" below
    Yes → Does it need extending?
      Yes → see "Extend installation docs" below
      No  → nothing to do

Navigation index lost a section after stub deletion?
  Yes → Insert HTML comment placeholder → see "Deferred index placeholder" below

Design doc has bare Future Improvements?
  Yes → Inspect implementation files → annotate each item → see "Annotate deferral" below

Placeholder needs replacing with real content?
  Yes → Verify paths/APIs first → rewrite → see "Rewrite placeholder doc" below
```

### Delete Stubs (YAGNI)

1. **Confirm stubs** — grep for placeholder text before touching anything:

   ```bash
   grep -rl "Content here\." docs/
   ```

2. **Find all references** — search every referencing file before deleting:

   ```bash
   grep -rl "stub-filename\|other-stub" docs/
   ```

3. **Delete stub files** in one command:

   ```bash
   rm docs/advanced/stub1.md docs/core/stub2.md docs/dev/stub3.md
   ```

4. **Update referencing files** — remove broken link lines; if a section becomes empty,
   remove the whole section. Keep links to substantive files.

5. **Verify no broken links remain**:

   ```bash
   grep -rl "deleted-path" docs/
   # Should return nothing
   ```

6. **Run pre-commit** (skip environment-broken hooks):

   ```bash
   SKIP=mojo-format pixi run pre-commit run --all-files
   ```

7. **Commit message format**:

   ```text
   docs: delete N empty placeholder documentation stubs

   Remove all documentation files containing only "Content here." as
   placeholder text. Per YAGNI, documentation should be written alongside
   feature implementation, not created as empty stubs beforehand.

   Also remove all broken links to the deleted files from:
   - docs/index.md
   - docs/README.md

   Closes #NNNN
   ```

### Deferred Index Placeholder

After stub deletion removes an entire section from `docs/index.md`, insert an HTML comment
at the section's former location:

```markdown
<!-- DEFERRED: <Section Name> section
  The following topics were linked in docs/index.md but their source files
  were placeholder stubs deleted in #<stub-deletion-issue>. Re-add each entry
  once the corresponding doc is written.

  - <topic-slug> (<path/to/file.md>)
    Status: Deferred — doc not yet written
    Why: Stub deleted in #<issue> (YAGNI)
    Acceptance criteria: Write <path/to/file.md>; re-add link here

  Tracking issue: #<follow-up-issue>
-->
```

Key rules:

- Use an HTML comment — it must not render in output, only in source
- List **every** topic that was in the removed section
- Include all affected sections (Advanced Topics, Dev Guides, etc.)
- Add `Tracking issue: #<number>` at the bottom for self-referencing

Verify after editing:

```bash
grep -n "\[.*\](missing-path" docs/index.md   # should return nothing
awk 'length > 120 {print NR": "length" chars"}' docs/index.md
```

### Annotate Future Improvements

1. Find the section:

   ```bash
   grep -n "Future Improvements" docs/design/*.md
   ```

2. Inspect actual implementation files (Dockerfile, scripts, source) to confirm status.
   Look for flags/directives the item would require. If absent → Deferred. If present → Implemented.

3. For each item, write three sub-bullets:

   ```markdown
   1. **Item name**: One-line description.

      - **Status**: Deferred (not implemented)
      - **Why deferred**: Concrete reason grounded in what you saw in the code.
      - **Acceptance criteria**: Measurable conditions to implement (2–3 bullets).
   ```

4. Surface already-implemented items:

   ```markdown
   5. **Health checks**: Verify container readiness.

      - **Status**: Implemented — see `docker/Dockerfile` lines 116–117.
   ```

### Rewrite Placeholder Doc

Covers quickstart, installation, README, and any other stub:

1. **Read in parallel** — read the placeholder, adjacent docs, and the issue:

   ```bash
   gh issue view <n> --comments
   ```

2. **Verify every path and import** before writing:
   - Use `Glob` to verify file paths
   - Read `__init__.mojo` or package index for actual exports
   - Use `ls` on referenced directories
   - Source versions from `pixi.toml`, not memory
   - Source command names from `justfile`, not README (may be stale)

3. **Write replacement content** — standard sections for installation docs:

   ```text
   # Installation
   ## Prerequisites
   ## Installing Pixi
   ## Cloning the Repository
   ## Installing Dependencies
   ## Mojo Version Requirements
   ## Verifying the Installation
   ## Docker Alternative
   ## IDE Setup        ← add when IDE guidance is missing
   ## Troubleshooting
   ```

4. **Validate markdown** — use pre-commit (npx is often not in pixi conda env):

   ```bash
   pixi run pre-commit run markdownlint-cli2 --files <path/to/file.md>
   ```

5. **Stage only the target file**:

   ```bash
   git add docs/getting-started/installation.md
   # Do NOT: git add .  (worktree may contain .claude-prompt-N.md)
   ```

### Extend Installation Docs (IDE Setup)

When an existing installation doc lacks IDE guidance:

1. Read `installation.md` + `shared/INSTALL.md` in parallel
2. Add `## IDE Setup` immediately **before** `## Troubleshooting`
3. Standard subsections:

   ```markdown
   ### VS Code

   Install the **Mojo** extension (publisher: Modular) from the VS Code marketplace.

   Add to `.vscode/settings.json`:

   ```json
   {
       "mojo.mojoPath": "${workspaceFolder}/.pixi/envs/default/bin/mojo"
   }
   ```

   Verify: **View → Output → Mojo Language Server**.

   ### Other Editors

   Point LSP to: `.pixi/envs/default/bin/mojo-lsp-server`

   Formatter: `pixi run mojo format <file>`
   ```

4. Tighten prerequisites with explicit version numbers:

   ```markdown
   - **Git** >= 2.x (any modern 2.x release is sufficient)
   - **Pixi** >= 0.24 package manager (installation steps below)
   ```

### Quick Reference

| Scenario | Key command / pattern |
| --------- | ---------------------- |
| Confirm stubs | `grep -rl "Content here\." docs/` |
| Find referencing files | `grep -rl "stub-name" docs/` |
| Run pre-commit (skip broken hooks) | `SKIP=mojo-format pixi run pre-commit run --all-files` |
| Validate single markdown file | `pixi run pre-commit run markdownlint-cli2 --files <file>` |
| Source Mojo version | Read `pixi.toml` — use range (`>=0.26.1,<0.27`), not nightly string |
| Source command names | Read `justfile` directly, not README |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Deleting files without checking references first | Ran `rm` on all stubs immediately | Left broken links in `docs/README.md`, `docs/glossary.md`, and other files | Always `grep -rl` for all references before deleting |
| Running `just pre-commit-all` | Used `pixi run just` to invoke pre-commit | `just` not in PATH in this environment | Use `pixi run pre-commit run --all-files` directly |
| Full pre-commit suite without skipping | Ran hooks on host with GLIBC mismatch | `mojo-format` fails due to GLIBC version mismatch (environment issue, not code) | Use `SKIP=mojo-format` when hook failure is environmental |
| `pixi run npx markdownlint-cli2 <file>` | Used npx inside pixi conda env | `npx: command not found` — not installed in conda env | Use `pixi run pre-commit run markdownlint-cli2 --files <file>` instead |
| Running pixi markdownlint as background task | `run_in_background=true` for markdownlint | Pixi env init takes ~2 minutes, causing repeated timeouts | Run markdownlint synchronously with ≥120s timeout |
| Documenting APIs from EXAMPLES.md | Copied import examples from shared EXAMPLES doc | EXAMPLES.md uses aspirational/planned APIs, not what is actually implemented | Always read `__init__.mojo` or package index to find real exports |
| Hardcoding Mojo nightly version string | Wrote `0.26.1.0.dev2025122805` directly | Full nightly build strings go stale immediately | Use the version range from `pixi.toml` (`>=0.26.1,<0.27`) |
| Using Skill tool for commit+push+PR | Invoked `commit-commands:commit-push-pr` skill | Skill tool denied in `don't ask` permission mode | Fall back to direct `git add` + `git commit` + `git push` + `gh pr create` |
| Copying IDE section from shared/INSTALL.md | Read shared INSTALL.md hoping for IDE config to lift | Shared INSTALL.md covers Docker/pixi install, not IDE config | Write IDE Setup from scratch using standard VS Code + LSP patterns |
| Linking to installation.md before reading it | Referenced installation.md as a real doc | The installation.md was itself a placeholder at the time | Read the target file before referencing it — never assume docs are real |

## Results & Parameters

### Markdownlint Rules

- Language tags on all fenced code blocks (` ```bash `, ` ```toml `, ` ```text `)
- Blank line before and after every code block
- Blank line before and after every list
- Lines <= 120 characters

### Pixi Markdownlint (Reliable Path)

```bash
# WORKS
pixi run pre-commit run markdownlint-cli2 --files <path/to/file.md>
pixi run pre-commit run --all-files markdownlint-cli2

# FAILS — npx not in pixi conda env
pixi run npx markdownlint-cli2 path/to/file.md
```

### Version Range Pattern

```toml
# Read from pixi.toml — use constraint range, not nightly build string
[dependencies]
mojo = ">=0.26.1.0.dev2025122805,<0.27"
# Document as: mojo >= 0.26.1, < 0.27
```

### HTML Comment — markdownlint Safe

HTML comments (`<!-- ... -->`) pass `markdownlint-cli2` MD033 even with
`allowed_elements` restrictions because comments are not HTML elements.

### Files Most Likely to Reference Stubs

- `docs/index.md` — main navigation hub (most links)
- `docs/README.md` — directory tree + Next Steps
- `docs/glossary.md` — See Also section
- `docs/getting-started/first_model.md` — Learn More + Related Documentation
- Topic-specific docs with cross-reference sections

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3142, PR #3308 | Deleted 17 stub files, updated 5 referencing docs |
| ProjectOdyssey | Issue #3312, PR #3932 | Deferred HTML comment for Core Documentation section in index |
| ProjectOdyssey | Issue #3304, PR #3913 | Wrote complete installation.md from 11-line placeholder |
| ProjectOdyssey | Issue #3305, PR #3917 | Replaced quickstart.md placeholder with real content |
| ProjectOdyssey | Issue #3918, PR #4830 | Extended installation.md with IDE setup section |
| ProjectOdyssey | Issue #3141, PR #3303 | Replaced placeholder README with codebase-grounded description |
| ProjectScylla | Issue #881, PR #990 | Annotated Future Improvements with Status/Why/Acceptance Criteria |
