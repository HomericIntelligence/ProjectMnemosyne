# Session Notes: pixi-audit-task-alias

## Verified Examples

### Example 1: ProjectScylla — Issue #872

**Date**: 2026-02-22
**Context**: Issue #872 requested that `pip-audit` be available to developers without the `--environment lint` flag. pip-audit was already declared in `[feature.lint.pypi-dependencies]` from a prior commit (d1c47937, follow-up from #755).

**Specific Commands Used**:

```bash
# Verify lint env resolves
pixi install --environment lint

# Check task appears
pixi task list

# Confirm tests pass (2436 tests, 74.16% coverage)
pixi run python -m pytest tests/ -v
```

**Specific Fix/Solution Applied**:

```diff
--- a/pixi.toml
+++ b/pixi.toml
@@ -11,6 +11,7 @@ lint = "ruff check scylla scripts tests"
 format = "ruff format scylla scripts tests"
 plan-issues = "python scripts/plan_issues.py"
 mypy-regression = "python scripts/check_mypy_counts.py"
+audit = "pixi run --environment lint pip-audit"
```

**Key insight**: `pip-audit` was already in `[feature.lint.pypi-dependencies]` (added in a prior commit). The only missing piece was the top-level task alias. Reading pixi.toml first before adding dependencies prevented a redundant/conflicting dependency declaration.

**Links**:

- PR: https://github.com/HomericIntelligence/ProjectScylla/pull/976
- Issue: https://github.com/HomericIntelligence/ProjectScylla/issues/872

---

## Raw Findings

- The issue description offered two options: (A) add pip-audit to `[pypi-dependencies]` default env, or (B) add a task alias. Option B was chosen per KISS/YAGNI — the lint environment is already the right home for security/quality tooling.
- The implementation plan comment on the issue (from the planning agent) also recommended Option B.
- Pre-commit hooks skipped cleanly on `pixi.toml` changes (only Python/YAML hooks ran, none matched TOML).
- `pixi task list` output confirms the alias appears alongside standard tasks (`test`, `lint`, `format`, `audit`).

## External References

- pixi tasks documentation: https://prefix.dev/docs/pixi/reference/pixi_manifest#tasks
- pip-audit: https://pypi.org/project/pip-audit/
