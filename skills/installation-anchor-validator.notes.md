# Session Notes — installation-anchor-validator

## Issue

GitHub issue #3915: Verify links from README to installation.md are correct.
Follow-up from #3304 and #3141.

## Context

- `README.md` had a plain link `[Installation Guide](docs/getting-started/installation.md)` — no anchor
- `docs/getting-started/installation.md` had 17 headings with potential anchor targets
- Existing `scripts/validate_links.py` explicitly strips anchors (line 77: `link.split("#")[0]`)
- Existing link-check CI workflow uses lychee but does not validate internal anchor fragments
- Pattern for scripts and tests established by `scripts/audit_shared_links.py` and `tests/test_audit_shared_links.py`

## What Was Built

- `scripts/validate_installation_anchors.py` — 160 lines, pure stdlib, typed
- `tests/test_validate_installation_anchors.py` — 33 hermetic tests, all passing
- `.github/workflows/link-check.yml` — new step after lychee
- `scripts/README.md` — documentation added

## Key Design Decisions

1. **Separate script, not a modification to validate_links.py** — existing script intentionally
   ignores anchors; modifying it would risk breaking callers and expand scope (YAGNI)

2. **GitHub slug algorithm in pure Python** — no external dependencies; regex-based approach
   handles all edge cases (backticks, parens, numbers)

3. **TemporaryDirectory in class-based tests** — `tmp_path` pytest fixture works with function-
   based tests; for class-based tests, `TemporaryDirectory` context manager is more portable

4. **Two-arg CLI convention** — `<sources...> <installation.md>` follows convention of other
   validation scripts; last positional arg = target file

## Real-world State

Current README only has a plain link (no anchor). The script passes cleanly today.
When a future PR adds a deep-link (e.g., `installation.md#prerequisites`), CI will catch
any regression if the heading is renamed.

## PR

- Branch: `3915-auto-impl`
- PR: https://github.com/HomericIntelligence/ProjectOdyssey/pull/4829
- Date: 2026-03-15