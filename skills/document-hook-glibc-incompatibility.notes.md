# Session Notes: Issue #3253

## Context

- **Issue**: Fix mojo-format pre-commit hook GLIBC incompatibility
- **Branch**: `3253-auto-impl`
- **PR**: #3821
- **Date**: 2026-03-07

## What the Issue Asked For

Document the `mojo-format` pre-commit hook failure on hosts with GLIBC < 2.32 (Debian Buster)
in `CONTRIBUTING.md` and/or `.pre-commit-config.yaml`. Follow-up from #3061 / #3170.

## Existing State (discovered before making changes)

- `.pre-commit-config.yaml` lines 5-9: Already had a 5-line GLIBC comment block (added in #3170)
- `docs/dev/mojo-glibc-compatibility.md`: Comprehensive 80-line doc covering affected OS table,
  wrapper script behaviour, long-term resolution options, developer workflow
- `scripts/mojo-format-compat.sh`: Wrapper script already in place — hook auto-skips on incompatible hosts
- `CONTRIBUTING.md`: Zero mentions of GLIBC, glibc, or mojo-format compat — this was the gap

## Changes Made

Single file changed: `CONTRIBUTING.md` — added 26 lines under "Hook Failure Policy" section.

## Commands That Worked

```bash
# Markdown linting (npx not available)
SKIP=mojo-format pixi run pre-commit run markdownlint-cli2 --all-files

# Commit on incompatible host
SKIP=mojo-format git commit -m "docs(contributing): ..."

# PR creation
gh pr create --title "..." --body "$(cat <<'EOF' ... EOF)"
gh pr merge --auto --rebase <PR-number>
```

## Commands That Failed

```bash
# npx not available on this host
pixi run npx markdownlint-cli2 CONTRIBUTING.md
# Error: npx: command not found
```