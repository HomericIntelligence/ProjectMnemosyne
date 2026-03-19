# Session Notes: mojo-jit-crash-doc

## Session Context

- **Date**: 2026-03-07
- **Project**: HomericIntelligence/ProjectOdyssey
- **Branch**: 3330-auto-impl
- **Issue**: #3330 — Document Mojo JIT crash workaround in CLAUDE.md or dev docs
- **Follow-up from**: #3120 (Core Loss test crashes)

## Objective

Document the intermittent `libKGENCompilerRTShared.so` JIT crash in Mojo v0.26.1 so future
developers recognize it as a compiler flake rather than a test bug.

## Issue Requirements (from #3330)

1. What 'execution crashed' in mojo output means
2. That it's a compiler bug not a test bug
3. The retry pattern fix
4. How to verify by checking if the crash appears before any test output

## Files Changed

- **Created**: `docs/dev/mojo-jit-crash-workaround.md` (new, ~120 lines)
- **Modified**: `CLAUDE.md` — added Quick Links entry under Core Guidelines
- **Modified**: `docs/dev/mojo-test-failure-patterns.md` — added blockquote callout

## Key Technical Findings

### CI Context (from comprehensive-tests.yml)

The workflow uses `continue-on-error: true` for Core Tensors, Integration Tests, and
Benchmarking test groups as a stopgap for the JIT crash. The comment at line 272:

```
# Some test groups have flaky Mojo runtime segfaults (libKGENCompilerRTShared.so crashes)
# on CI runners due to memory/runtime constraints.
```

### Relationship to ADR-009

ADR-009 documents a *different* `libKGENCompilerRTShared.so` crash — deterministic heap
corruption after ~15 cumulative tests in one file. That was fixed by file splitting. The
JIT crash (#3330) is non-deterministic and fixed by retrying.

### markdownlint Command

```bash
pixi run pre-commit run markdownlint-cli2 --files <file1> <file2>
```

`npx` is not available in the pixi environment. `just` is not on PATH in worktree shells.

## Approach Taken

1. Read existing workaround docs (`mojo-glibc-compatibility.md`, ADR-009) for style reference
2. Read CI workflow to understand current mitigation (`continue-on-error`)
3. Created new doc with all 4 required items from the issue
4. Added cross-references in CLAUDE.md and mojo-test-failure-patterns.md
5. Ran `pixi run pre-commit run markdownlint-cli2` — passed
6. Committed, pushed, created PR #3958, enabled auto-merge

## Errors Encountered

- `pixi run npx markdownlint-cli2` → `npx: command not found`
- `just pre-commit-all` → `just: command not found`
- Edit CLAUDE.md without prior Read → tool rejected with "File has not been read yet"

## PR Result

- PR #3958: https://github.com/HomericIntelligence/ProjectOdyssey/pull/3958
- Auto-merge enabled
- Label: documentation