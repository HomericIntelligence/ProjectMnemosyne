# Session Notes: replace-curl-sh-with-pixi

## Session Context

- **Date**: 2026-03-15
- **Issue**: ProjectOdyssey #3941 — "Add SHA256 verification to other binary downloads in CI workflows"
- **Follow-up from**: #3316 (which added sha256sum verification to gitleaks in security.yml)
- **PR created**: ProjectOdyssey #4837

## Objective

Audit all `.github/workflows/*.yml` files for `wget`/`curl` commands that download executables or
archives without hash verification, and apply appropriate hardening.

## Steps Taken

1. Listed all 25 workflow files with `Glob`
2. Searched for `curl`, `wget`, and pipe-to-sh patterns across all workflows
3. Found one insecure pattern in `validate-configs.yml`:
   - Job: `test-config-loading`
   - Steps: `Install Modular CLI` (curl -s https://get.modular.com | sh -) + `Install Mojo` (modular install mojo)
   - Both had `continue-on-error: true`
4. Verified `.github/actions/setup-pixi/action.yml` exists
5. Confirmed Mojo is provided via Pixi (already used in 10+ other jobs)
6. Replaced both steps with single `uses: ./.github/actions/setup-pixi` step
7. Committed, pushed, and created PR #4837

## Files Changed

- `.github/workflows/validate-configs.yml`: Removed 9 lines (2 steps), added 2 lines (1 step)

## Key Observations

- All other workflows (10+) already use `setup-pixi` — this was the only outlier
- The `modular install mojo` pattern predates the Pixi-based CI setup
- `continue-on-error: true` was hiding the fact that this install often failed silently
- The `workflow-binary-sha256-verification` skill (from #3316) covers the separate case of
  verifying a pinned wget binary download — this session covered the different case of
  eliminating a live-URL curl|sh installer entirely

## Audit Results (All Other Workflows)

All other workflows either:
- Use `uses: ./.github/actions/setup-pixi` (correct)
- Use pinned action SHAs (e.g., `actions/checkout@<hash>`) (correct)
- Use `wget` with `sha256sum --check` (correct, from #3316)
- Use `pip install` or `pixi run` (correct — package managers, not raw binaries)
- Use `curl` only to fetch JSON/text (not to pipe to shell) (correct)
