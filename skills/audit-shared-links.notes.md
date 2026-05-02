# Session Notes — audit-shared-links

## Context

- **Issue**: HomericIntelligence/ProjectOdyssey#3366
- **Branch**: `3366-auto-impl`
- **PR**: HomericIntelligence/ProjectOdyssey#4024
- **Date**: 2026-03-07

## Problem Statement

After trimming CLAUDE.md, three `.claude/shared/` files existed on disk but were
absent from the Quick Links / Core Guidelines section at the top of the file:

- `git-commit-policy.md`
- `output-style-guidelines.md`
- `tool-use-optimization.md`

The issue also requested a periodic audit mechanism to prevent future drift.

## Approach

1. Manual audit: `grep -n "shared/" CLAUDE.md` vs `ls .claude/shared/`
2. Edit CLAUDE.md Quick Links to add the 3 missing files
3. Write `scripts/audit_shared_links.py`:
   - `list_shared_files(shared_dir)` → sorted list of `.claude/shared/*.md` paths
   - `extract_quick_links_section(content)` → regex capture of `## Quick Links` section
   - `extract_linked_shared_paths(section)` → set of linked paths (handles absolute,
     relative, and `#anchor` variants)
   - `audit(content, shared_dir)` → `(missing, present)` tuple
   - `main(argv)` → CLI entry point with `argparse`, exits 0/1
4. Write 20 pytest unit tests using `TemporaryDirectory` (no real repo dependency)
5. Add `audit-shared-links` pre-commit hook triggered on `CLAUDE.md` or `.claude/shared/` changes

## Key Bug Found During Implementation

Initial regex `\(/?\.claude/shared/([^)#\s]+)\)` failed to match links with anchors
like `(/.claude/shared/tool-use-optimization.md#agentic-loop-patterns)` because the
character class `[^)#\s]` stops before `#`, but the closing `)` requires an immediate
match after the capture group — which isn't the case when `#section` follows.

Fix: `\(/?\.claude/shared/([^)#\s]+)(?:#[^)]*)?\)` — the optional non-capturing group
`(?:#[^)]*)?` consumes the anchor before the required `)`.

## Files Changed

- `CLAUDE.md` — 3 entries added to Quick Links
- `scripts/audit_shared_links.py` — new audit script (155 lines)
- `tests/test_audit_shared_links.py` — 20 unit tests (280 lines)
- `.pre-commit-config.yaml` — new `audit-shared-links` hook

## Test Results

```
20 passed in 0.03s
AUDIT PASSED: All 10 .claude/shared/ file(s) are linked in CLAUDE.md Quick Links.
```

All pre-commit hooks passed on staged files.
