# Session Notes — stale-script-detector

## Context

- **Issue**: ProjectOdyssey #3969 — "Add automated stale-script detection to CI or pre-commit"
- **Follow-up from**: #3148, #3337 (two manual audit rounds that removed ~29 one-time scripts)
- **Branch**: `3969-auto-impl`
- **PR**: #4844

## What Was Accomplished

1. Wrote `scripts/check_stale_scripts.py` — stdlib-only, always exits 0
2. Wrote 20 pytest unit tests in `tests/unit/scripts/test_check_stale_scripts.py`
3. Added `check-stale-scripts` pre-commit hook to `.pre-commit-config.yaml`
4. Committed and created PR with auto-merge enabled

## One Bug Fixed During Development

Initial `test_cross_script_reference` test wrote `"from util import helper"` to `caller.py`
and searched for `"util.py"` — this failed because the import uses the module name without
`.py` extension. Fixed by making the reference use `subprocess.run(['python', 'scripts/util.py'])`,
which contains the full filename.

**Lesson**: Basename matching (full `.py` filename) is correct for this detection approach.
Cross-script references that go through Python import machinery won't be detected — and that's
intentional, since the ALWAYS_ACTIVE allowlist covers shared library modules.

## File Layout

```
scripts/check_stale_scripts.py           # The detector script
tests/unit/scripts/test_check_stale_scripts.py  # 20 unit tests
.pre-commit-config.yaml                  # Added check-stale-scripts hook
```

## Key Design Choices

- **Exit 0 always**: warning-only so it never blocks commits
- **Self-reference exclusion**: script appearing in its own file doesn't count
- **ALWAYS_ACTIVE allowlist**: `common.py` and the script itself exempt
- **Basename matching**: searches full filename including `.py` extension
- **Reference targets**: `.github/**/*.yml`, `justfile`, `.pre-commit-config.yaml`, `scripts/*.py`