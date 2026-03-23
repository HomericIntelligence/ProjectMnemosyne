# Session Notes: Centralizing Shared Scripts into ProjectHephaestus

## Session Context

- **Date**: 2026-03-22
- **Repos explored**: ProjectHephaestus, ProjectScylla, ProjectOdyssey, ProjectTelemachy, ProjectHermes, ProjectArgus, AchaeanFleet, Myrmidons
- **Tool**: Claude Code with `/advise` skill for prior art search

## Modules Created

### Phase 1 — Standalone (no new deps)
1. `hephaestus/validation/type_aliases.py` — Type alias shadowing detection
2. `hephaestus/validation/audit.py` — pip-audit CVSS severity filter
3. `hephaestus/validation/test_structure.py` — Merged test directory mirror + loose file check

### Phase 2 — TOML-dependent
4. `hephaestus/validation/python_version.py` — Merged pyproject.toml + Dockerfile consistency
5. `hephaestus/validation/coverage.py` — Coverage threshold gate with per-module config

### Phase 3 — External tool dependent
6. `hephaestus/validation/complexity.py` — Ruff C901 wrapper
7. `hephaestus/validation/schema.py` — YAML-against-JSON-schema validation

### Phase 4 — Enhancement
8. `hephaestus/validation/markdown.py` — Added link validation pipeline (validate_all_links, validate_file_links, etc.)

### Phase 5 — AST-based
9. `hephaestus/validation/docstrings.py` — Docstring fragment detection

## Key Duplication Findings

### Identical scripts across repos
- `check_python_version_consistency.py`: Hephaestus (regex-based, checks pyproject internal) vs Scylla (tomllib-based, checks pyproject vs Dockerfile)
- `check_unit_test_structure.py`: Hephaestus (mirror check) vs Scylla (no-loose-files check)

### Scylla-only scripts worth sharing
- `check_coverage.py`, `check_max_complexity.py`, `filter_audit.py`, `validate_config_schemas.py`, `validate_links.py`, `check_type_alias_shadowing.py`, `check_docstring_fragments.py`

### Utility duplication
- `get_repo_root()` reimplemented in Odyssey's `scripts/common.py` and Scylla's `scylla/automation/git_utils.py`
- Markdown validation utilities duplicated between Odyssey's `scripts/validation.py` and Hephaestus's `hephaestus/validation/markdown.py`
- `Colors` ANSI class in Odyssey's `common.py` vs Hephaestus's `hephaestus/cli/colors.py`

## GitHub Issues Filed

- ProjectScylla #1537: https://github.com/HomericIntelligence/ProjectScylla/issues/1537
- ProjectOdyssey #5061: https://github.com/HomericIntelligence/ProjectOdyssey/issues/5061

## Implementation Decisions

1. **Schema map is configurable**: Scylla's `validate_config_schemas.py` had a hardcoded `_SCHEMA_MAP`. The library version takes a `SchemaMapping` parameter and supports loading from a JSON file via `--schema-map`.

2. **Dockerfile check is optional**: Not all repos have Dockerfiles, so `check_python_version_consistency()` has `check_dockerfile=False` by default.

3. **Coverage graceful fallback**: If `defusedxml` is not installed, `parse_coverage_report()` returns None and `check_coverage()` passes gracefully rather than failing.

4. **No Scylla-specific scope filters**: Scylla's `check_docstring_fragments.py` had `_is_scylla_file()` hardcoded. Replaced with configurable `--directory` argument.
