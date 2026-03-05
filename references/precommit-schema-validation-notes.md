# Reference Notes: precommit-schema-validation

## Session Details

- **Date**: 2026-03-05
- **Project**: ProjectScylla
- **Issue**: HomericIntelligence/ProjectScylla#1382
- **PR**: HomericIntelligence/ProjectScylla#1439
- **Branch**: `1382-auto-impl`

## Files Created / Modified

| File | Change |
|------|--------|
| `scripts/validate_config_schemas.py` | New script (160 lines) |
| `tests/unit/scripts/test_validate_config_schemas.py` | New test file (26 tests) |
| `.pre-commit-config.yaml` | Added `validate-config-schemas` hook |

## Schema Mappings

| File pattern | Schema file |
|---|---|
| `config/defaults.yaml` | `schemas/defaults.schema.json` |
| `config/models/*.yaml` | `schemas/model.schema.json` |
| `tests/fixtures/config/tiers/*.yaml` | `schemas/tier.schema.json` |

## Key Design Decisions

### `pass_filenames: true` vs `pass_filenames: false`

Used `pass_filenames: true` so only changed files are validated per commit,
not the entire config directory. The script receives file paths as positional
args via `argparse` `nargs="*"`.

### `Draft7Validator.iter_errors()` vs `jsonschema.validate()`

`iter_errors()` collects all violations in a single pass. This is essential for
a pre-commit hook where you want to show everything at once.

### `resolve_schema()` handles both absolute and relative paths

pre-commit passes absolute paths. `resolve_schema` normalizes via
`file_path.resolve().relative_to(repo_root.resolve())`, with a fallback for
paths already relative to the repo root.

### Unknown paths → WARNING not FAIL

If a file matches the `files:` regex but not the internal `_SCHEMA_MAP`, the
hook warns to stderr and continues with exit 0. This prevents future breakage
when new file types match the broad regex.

## YAML Multi-line Regex in `.pre-commit-config.yaml`

The `files:` field uses folded block scalar (`>-`) to allow the regex to span
multiple lines without YAML syntax errors:

```yaml
files: >-
  ^(config/defaults\.yaml|config/models/.+\.yaml|
  tests/fixtures/config/tiers/.+\.yaml)$
```

yamllint requires this over inline multi-line strings.

## Test Coverage

26 tests across 4 classes:
- `TestResolveSchema` (8 tests) — pattern matching
- `TestValidateFile` (7 tests) — valid/invalid/malformed YAML handling
- `TestCheckFiles` (8 tests) — exit codes, verbose, warning on unknowns
- `TestMainIntegration` (3 tests) — real schemas + real config files

## Related Skills

- `wire-schema-validation` — wired the same schemas into `scylla/config/loader.py`
  at load time (PR #1424, issue #1380). This skill adds commit-time validation on top.
