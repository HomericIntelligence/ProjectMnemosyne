---
name: mojo-jit-crash-doc
description: 'Document Mojo JIT compiler crashes (libKGENCompilerRTShared.so ''execution
  crashed'') with diagnosis guide and retry workaround. Use when: CI produces ''execution
  crashed'' before any test output, or developers report intermittent mojo test failures
  on known-good code.'
category: documentation
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Skill: mojo-jit-crash-doc

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Objective | Document the intermittent Mojo v0.26.1 JIT crash so developers recognize it as a compiler flake, not a test bug |
| Outcome | Success — `docs/dev/mojo-jit-crash-workaround.md` created, CLAUDE.md Quick Links updated, cross-reference added to mojo-test-failure-patterns.md, PR #3958 created |
| Category | documentation |

## When to Use

Use this skill when:

- CI produces `execution crashed` (with no preceding test output) on a test group that passes
  consistently on main
- A developer spends time debugging test code for a crash that is actually a Mojo compiler flake
- A new Mojo compiler bug with a known workaround needs a developer-facing doc under `docs/dev/`
- Adding a quick-link to CLAUDE.md for a new workaround guide

## Verified Workflow

### 1. Read the issue and existing docs for context

```bash
gh issue view <number> --comments
```

Check `docs/dev/` for existing workaround docs (e.g., `mojo-glibc-compatibility.md`,
`mojo-test-failure-patterns.md`) to match style. Read `ADR-009` for context on the
related heap-corruption crash — it is **distinct** from the JIT flake.

### 2. Create `docs/dev/mojo-jit-crash-workaround.md`

Required sections:

- **Problem** — what `execution crashed` means, that it originates in
  `libKGENCompilerRTShared.so`, and that it is a Mojo compiler bug not a test bug
- **Diagnosis table** — crash before any test output = compiler flake; crash after
  test output = real test bug; specific assertion failure = real test bug
- **Workaround: CI Retry Pattern** — shell retry loop + GitHub Actions
  `nick-fields/retry` snippet
- **Relationship to ADR-009** — comparison table distinguishing the two crashes
- **Long-term resolution** — checklist for what to remove when upgrading Mojo

Sample diagnosis table (copy-paste into the doc):

```markdown
| Symptom | Cause |
|---------|-------|
| `execution crashed` before any test output | Compiler flake — retry |
| `execution crashed` after test output | Likely a real test bug |
| Specific assertion failure message | Real test bug — investigate |
```

### 3. Update CLAUDE.md Quick Links

Add a link under `### Core Guidelines`:

```markdown
- [Mojo JIT Crash Workaround](docs/dev/mojo-jit-crash-workaround.md) - `libKGENCompilerRTShared.so` flake
```

Insert it after the `Mojo Anti-Patterns` line so all Mojo-related links are grouped together.

### 4. Add callout in `docs/dev/mojo-test-failure-patterns.md`

Insert a blockquote after the `## Executive Summary` header:

```markdown
> **Note**: For `execution crashed` errors that appear _before_ any test output, see
> [Mojo JIT Crash Workaround](mojo-jit-crash-workaround.md) — this is a compiler flake,
> not a test bug. Retry the test run to confirm.
```

This surfaces the JIT crash doc when developers search "execution crashed" in the test
failure patterns file.

### 5. Run markdownlint

```bash
pixi run pre-commit run markdownlint-cli2 --files \
  docs/dev/mojo-jit-crash-workaround.md \
  docs/dev/mojo-test-failure-patterns.md \
  CLAUDE.md
```

Expected output: `Markdown Lint............. Passed`

### 6. Commit, push, create PR

```bash
git add docs/dev/mojo-jit-crash-workaround.md \
        docs/dev/mojo-test-failure-patterns.md \
        CLAUDE.md

git commit -m "docs(dev): document Mojo JIT crash workaround for libKGENCompilerRTShared.so

Add docs/dev/mojo-jit-crash-workaround.md explaining the intermittent
'execution crashed' error in Mojo v0.26.1.

Closes #<issue-number>"

git push -u origin <branch>

gh pr create \
  --title "docs(dev): document Mojo JIT crash workaround for libKGENCompilerRTShared.so" \
  --body "Closes #<issue-number>" \
  --label "documentation"

gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct `pixi run npx markdownlint-cli2` | Ran markdownlint via npx through pixi | `npx: command not found` — npx is not in the pixi environment | Use `pixi run pre-commit run markdownlint-cli2 --files <files>` instead |
| Running `just pre-commit-all` | Tried the justfile recipe for pre-commit | `just: command not found` in the worktree shell | Use `pixi run pre-commit run <hook> --files <files>` directly |
| Edit CLAUDE.md without Read | Tried to Edit CLAUDE.md before reading it | Tool rejected: "File has not been read yet" | Always Read before Edit, even for small targeted changes |

## Results & Parameters

| Parameter | Value |
|-----------|-------|
| New file | `docs/dev/mojo-jit-crash-workaround.md` |
| Files modified | `CLAUDE.md`, `docs/dev/mojo-test-failure-patterns.md` |
| Lines added | ~120 (new doc) + 2 (CLAUDE.md) + 4 (test-failure-patterns.md) |
| Markdownlint hook | `pixi run pre-commit run markdownlint-cli2 --files <files>` |
| PR | https://github.com/HomericIntelligence/ProjectOdyssey/pull/3958 |
| Issue | #3330 |
| Branch | `3330-auto-impl` |
| Time to complete | ~10 minutes |

## Key Insights

1. **Diagnosis by output position**: The single most useful heuristic — if `execution crashed`
   appears before any test output, it is always a JIT compiler flake. If tests ran first,
   investigate the test code.

2. **Distinguish from ADR-009**: The heap corruption crash (ADR-009) is deterministic (fires
   after ~15 cumulative tests) and workarounded by file splitting. The JIT crash is
   non-deterministic and workarounded by retrying. Both produce `libKGENCompilerRTShared.so`
   in the crash, so documenting the difference prevents confusion.

3. **Cross-reference placement matters**: Adding a blockquote at the top of
   `mojo-test-failure-patterns.md` (not buried at the bottom) ensures developers see the
   pointer to the JIT crash doc when they land on the patterns file looking for "execution
   crashed".

4. **markdownlint via pre-commit, not npx**: In this pixi environment, `npx` is unavailable.
   The correct command is `pixi run pre-commit run markdownlint-cli2 --files <files>`.

5. **`just` unavailable in worktree shells**: The `just` binary is not on PATH in bare
   worktree shells. Use `pixi run <command>` directly.
