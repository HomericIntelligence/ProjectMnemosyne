---
name: documentation-mkdocs-strict-out-of-tree-links
description: 'Fix mkdocs --strict build failures caused by relative links from files
  under docs/ pointing to repo paths outside docs/ (scripts/, .github/, etc.). Use when:
  (1) "Deploy Documentation" CI job aborts with "Aborted with N warnings in strict mode",
  (2) mkdocs warns "contains a link ''X'', but the target ''Y'' is not found among
  documentation files", (3) writing/editing docs that need to reference scripts, workflows,
  or other repo-root files. Fix: replace ../../foo/bar with absolute https://github.com/<org>/<repo>/blob/main/foo/bar.'
category: documentation
date: 2026-05-11
version: 1.0.0
user-invocable: false
---

## Overview

| Field | Value |
| ------- | ------- |
| **Skill** | documentation-mkdocs-strict-out-of-tree-links |
| **Category** | documentation |
| **Trigger** | mkdocs --strict aborts because a doc links to a file outside docs/ |
| **Scope** | Any markdown under docs/ that references scripts/, .github/, or other repo-root paths |
| **Fix** | Rewrite relative escapes (`../../...`) as absolute GitHub blob URLs |

## When to Use

- Writing or editing docs under `docs/` that need to reference `scripts/`, `.github/workflows/`,
  or any other path that lives at the repo root (not under `docs/`).
- CI failure: "Deploy Documentation" workflow (or any mkdocs job) aborts with
  `Aborted with N warnings in strict mode!`.
- mkdocs warning of the form:
  `WARNING - Doc file 'X.md' contains a link '../../scripts/foo.sh', but the target '../scripts/foo.sh' is not found among documentation files.`
- A reviewer points at links like `[script](../../scripts/foo.sh)` from inside `docs/dev/`.

## Verified Workflow

1. **Reproduce locally** with strict mode (matches CI):

   ```bash
   pixi run mkdocs build --strict
   # or, without pixi:
   mkdocs build --strict
   ```

2. **Read the warnings**. Strict mode lists every offending link with the source doc file
   and the unresolved target. Collect the set of out-of-tree paths (scripts/, .github/, etc.).

3. **Determine the canonical GitHub URL prefix** for the repo, e.g.
   `https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/`.

4. **Rewrite each offending link** from a relative escape to an absolute GitHub URL:

   ```markdown
   <!-- WRONG (mkdocs --strict aborts) -->
   See [the wrapper](../../scripts/mojo-under-gdb.sh) and
   [the workflow](../../.github/workflows/comprehensive-tests.yml).

   <!-- CORRECT -->
   See [the wrapper](https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/scripts/mojo-under-gdb.sh)
   and [the workflow](https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/.github/workflows/comprehensive-tests.yml).
   ```

5. **Re-run** `pixi run mkdocs build --strict`. Expected output:
   `Documentation built in N.NN seconds` with **no** `WARNING` lines. `INFO` lines (for
   absolute root paths like `/CLAUDE.md` or unrecognized relative paths like `operations/`)
   are not fatal — strict mode only aborts on `WARNING`-level "target not found among
   documentation files".

6. **Commit and push** with a clear scope:

   ```text
   docs(fix): use absolute URLs for out-of-tree links to satisfy mkdocs --strict
   ```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Add more `../` hops | Bumped `../../scripts/foo.sh` to `../../../scripts/foo.sh` to "fix" the path | Still escapes the `docs/` tree; mkdocs only resolves links to files it knows about (those configured in nav or present under `docs/`). The number of `../` is irrelevant. | mkdocs `--strict` rejects ANY relative link whose target is outside `docs/`, regardless of depth. |
| HTML anchor with relative href | Replaced `[text](../../scripts/foo.sh)` with `<a href="../../scripts/foo.sh">text</a>` | mkdocs still parses HTML anchors and runs the same target resolution; the same WARNING fires. | You cannot smuggle relative out-of-tree links past `--strict` by using HTML. |
| Symlink `docs/scripts -> ../scripts` | Created symlink inside `docs/` to expose repo-root scripts as docs files | mkdocs follows the symlink and tries to render `.sh` files as docs; build output gets polluted and other warnings appear. Also brittle on Windows checkouts. | Don't expose non-doc files into the docs tree; link to them on GitHub instead. |
| Ignore the warning | Removed `--strict` from the mkdocs invocation | Hides real broken links and defeats the purpose of CI gating; review feedback rejected. | Keep `--strict`; fix the links. |

## Results & Parameters

**Fixed in ProjectOdyssey PR #5381 (commit 63b9db7f9):**

- Replaced `../../scripts/mojo-under-gdb.sh` and `../../.github/workflows/...` style links
  in `docs/dev/mojo-jit-crash-capture-core.md` with full
  `https://github.com/HomericIntelligence/ProjectOdyssey/blob/main/...` URLs.

**Verification:**

```bash
pixi run mkdocs build --strict
# Documentation built in 1.95 seconds
# (no WARNING lines; only INFO lines, which strict ignores)
```

**Strict-mode severity model — what aborts vs. what's tolerated:**

- **Aborts strict build** (`WARNING` level):
  `WARNING - Doc file 'X' contains a link 'Y', but the target 'Z' is not found among
  documentation files.` — this is the fatal one. Always caused by a link from inside
  `docs/` to a target mkdocs cannot map to a documentation page.
- **Tolerated** (`INFO` level, does NOT abort `--strict`):
  - Absolute-root style links like `/CLAUDE.md` — mkdocs leaves them alone (assumed
    site-relative at deploy time).
  - Unrecognized relative paths like `operations/` with no trailing file — mkdocs logs
    INFO but does not warn.

**Decision rule for new links from `docs/`:**

| Target lives… | Use |
| --------------- | ----- |
| Inside `docs/` | Relative link within `docs/` (e.g., `../dev/foo.md`) — count `../` carefully so you don't escape `docs/` |
| Outside `docs/` (repo root, scripts/, .github/, etc.) | Absolute GitHub URL: `https://github.com/<org>/<repo>/blob/main/<path>` |
| External site | Absolute `https://…` URL |

**Related skill:** `mkdocs-nav-cleanup` covers the adjacent case of nav entries referencing
deleted files and relative links that escape `docs/` *but loop back into it* via
`../../docs/...`. This skill covers the case where the target is genuinely outside `docs/`
and there is no in-tree equivalent.
