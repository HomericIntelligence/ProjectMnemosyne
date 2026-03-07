# Session Notes: dockerfile-env-version-pin

## Session Context

- **Date**: 2026-03-07
- **Project**: ProjectOdyssey
- **Issue**: #3350 — Pin Pixi version in main Dockerfile (not just Dockerfile.ci)
- **PR**: #3986
- **Branch**: `3350-auto-impl`

## Objective

`Dockerfile.ci` was already updated to pin `PIXI_VERSION=0.65.0` (via a prior fix), but the main
`Dockerfile` still used the unpinned `curl -fsSL https://pixi.sh/install.sh | bash` at line 70 in
the development stage. This was a consistency gap that could cause non-reproducible builds.

## Exact Change Applied

**File**: `Dockerfile`, development stage

**Before** (line 69-70):
```dockerfile
# Install Pixi as dev user
RUN curl -fsSL https://pixi.sh/install.sh | bash
```

**After** (lines 69-71):
```dockerfile
# Install Pixi as dev user (pinned version for reproducible builds)
ENV PIXI_VERSION=0.65.0
RUN curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=${PIXI_VERSION} bash
```

## Discovery Process

1. Read `.claude-prompt-3350.md` — straightforward issue description with the exact fix pattern
2. Found both `Dockerfile` and `Dockerfile.ci` via Glob
3. Grep'd for `PIXI_VERSION` in both files — confirmed `Dockerfile.ci` already had the pattern
4. Applied the 3-line change using the Edit tool
5. Committed, pushed, created PR with auto-merge

## Git Workflow Used

```bash
git add Dockerfile
git commit -m "fix(docker): pin PIXI_VERSION in main Dockerfile development stage

Adds ENV PIXI_VERSION=0.65.0 and passes it to the install script in
the development stage, matching the pattern already used in Dockerfile.ci
for consistency and reproducible builds.

Closes #3350"

git push -u origin 3350-auto-impl
gh pr create --title "fix(docker): pin PIXI_VERSION in main Dockerfile development stage" \
  --body "Closes #3350 ..."
gh pr merge --auto --rebase 3986
```

## Pre-commit Hook Behavior

Pre-commit hooks ran on commit. Only Trim Trailing Whitespace, Fix End of Files, Check for Large
Files, and Fix Mixed Line Endings ran (all passed). Mojo format, markdownlint, etc. were skipped
as no relevant files changed.

## Key Insight

When a multi-Dockerfile repo has one Dockerfile already pinned correctly (`Dockerfile.ci`), the fix
for the unpinned Dockerfile (`Dockerfile`) is just to replicate the exact pattern. No version
research needed — the version is already declared in the reference file.
