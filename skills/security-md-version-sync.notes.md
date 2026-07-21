# SECURITY.md version sync — 2026-07-20 session notes

## Context

- Project: ProjectHephaestus
- Existing implementation commit: `31ed68e01a25303b8de5f516cce844ca4572542c`
- Latest release tag: `v0.10.0`
- Version model: hatch-vcs dynamic versioning; no static `[project].version`
- Policy correction: `0.10.x` is supported and versions below `0.10` are end-of-life
- Scope: policy data only; guard and tests remained unchanged

## Observed verification

```text
$ python3 scripts/check_security_version_consistency.py
OK: SECURITY.md supported = 0.10.x matches latest tag v0.10.*

$ uv run pytest tests/unit/scripts/test_check_security_version_consistency.py --no-cov -q
18 passed in 0.90s

$ uv run pytest 'tests/unit/scripts/test_scripts_smoke.py::test_script_help_exits_zero' \
    -k check_security_version_consistency --no-cov -q
1 passed, 17 deselected in 0.23s
```

Verification level is `verified-local`; the commands were executed against the repository and
available tags, but this learning session did not observe a new Mnemosyne PR CI result.

## Behavior-changing learning

The earlier skill treated `[project].version` and overlapping current/previous supported series
as general defaults. ProjectHephaestus demonstrates two necessary branches:

1. A hatch-vcs project derives the current minor from version-sorted Git tags and must not gain a
   static version field merely to simplify documentation checks.
2. The repository's existing guard can intentionally require exactly one supported release
   series. A generic recommendation to preserve the preceding minor would fail that invariant.

The smallest successful correction updates only the two policy cells in `SECURITY.md`, then runs
the direct guard, its focused unit suite, and the affected script smoke test.
