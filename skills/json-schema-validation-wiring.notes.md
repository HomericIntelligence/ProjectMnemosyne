# Session Notes: json-schema-validation-wiring

**Date:** 2026-03-07
**Issue:** ProjectScylla #1438
**PR:** ProjectScylla #1465

## Context

`ConfigLoader` already had `_validate_schema()` used by `load_defaults()`, `load_tier()`, and `load_model()`. Both `schemas/test.schema.json` and `schemas/rubric.schema.json` existed but were never called from `load_test()` / `load_rubric()`. Issue #1438 (follow-up from #1380) asked to wire them in.

## Key Discovery: Schema vs Reality Mismatches

The schemas were written aspirationally and did not match actual fixture data:

### test.schema.json mismatches
1. `id` pattern `^[0-9]{3}-[a-z0-9]+(-[a-z0-9]+)*$` — fixtures use `test-001` format; some tests use `001-test`
2. `required` missing `language` — all fixtures have `language: python|mojo`
3. No `tiers` field — all fixtures have `tiers: [T0, T1, ...]`

### rubric.schema.json mismatches
1. `required: ["requirements", "grading"]` — test-001 uses `categories` format (no `requirements`)
2. No `criteria`, `skill_validation`, `skill_source` fields — test-002 uses all three in requirement items
3. `minLength: 10` on `description` — too restrictive for short descriptions in test fixtures

## Schema Design Decisions

**rubric.schema.json:** Made `requirements` optional (only `grading` required). Added `categories` as an alternative top-level format. Both formats can coexist in one rubric file (the schema allows it even if unusual). Used `additionalProperties: false` on category items but `additionalProperties: false` on requirement items after adding all observed optional fields.

**test.schema.json:** Used `^[a-z0-9][a-z0-9]*(-[a-z0-9]+)*$` as the ID pattern — allows `test-001`, `001-test`, and `001-justfile-to-makefile` forms.

## Fixture Files Tested

- `tests/fixtures/tests/test-001/test.yaml` — python, uses `categories` rubric
- `tests/fixtures/tests/test-002/test.yaml` — mojo, uses `requirements` rubric with `criteria`/`skill_validation`
- `tests/fixtures/tests/test-003/test.yaml` — mojo, clean requirements rubric
- Orchestrator test fixtures (created in tmpdir): `001-test` ID format, `language: mojo`

## Pre-commit Behavior

- First run: ruff auto-formats test file (7 fixes)
- Second run: all hooks pass including custom schema validators

## Test Count Delta

Before: 4475 unit tests
After: 4481 unit tests (+6 from TestTestSchema and TestRubricSchema; parametrized tests add more)
