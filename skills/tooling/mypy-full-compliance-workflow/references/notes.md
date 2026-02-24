# References: Mypy Full Compliance Workflow

## Session Context

- **Project**: ProjectScylla
- **Issue**: #687 — Bring mypy to compliance for scylla/ and scripts/
- **Branch series**: 687-phase0 through 687-phase9
- **PRs**: #1068–#1077

## Key Commands

```bash
# Check current mypy violation counts
pixi run python scripts/check_mypy_counts.py

# Update MYPY_KNOWN_ISSUES.md baseline
pixi run python scripts/check_mypy_counts.py --update

# Enable a specific error code to find violations
pixi run mypy scylla/ scripts/ --enable-error-code=var-annotated 2>&1 | grep "\[var-annotated\]"

# Run full mypy on source directories
pixi run mypy scylla/ scripts/

# Regenerate pixi.lock after pyproject.toml changes
pixi lock
```

## Phase Branch Stacking

Each phase branch was created from the prior phase branch (not from main):

```
main
└── 687-phase0-zero-codes
    └── 687-phase1-tests-override
        └── 687-phase2-var-annotated
            └── 687-phase3-misc
                └── 687-phase4-index-attr
                    └── 687-phase5-operator
                        └── 687-phase6-assignment
                            └── 687-phase7-arg-type
                                └── 687-phase8-union-attr
                                    └── 687-phase9-infra
```

## Key Files Modified

- `pyproject.toml` — `disable_error_code` entries removed over 9 phases
- `scripts/check_mypy_counts.py` — tracking script updated; `DISABLED_ERROR_CODES`, `TESTS_ONLY_ERROR_CODES`, `run_mypy_per_dir()` simplified
- `MYPY_KNOWN_ISSUES.md` — baseline updated after each phase
- `tests/__init__.py` — created in Phase 1 to enable `tests.*` module matching
