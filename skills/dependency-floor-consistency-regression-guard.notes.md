# Session Notes: Issue #631 (ProjectHephaestus)

## Date

2026-05-28

## Objective

Document the dependency floor consolidation workflow from ProjectHephaestus issue #631. PyGithub 1.x and 2.x have API-incompatible interfaces; the project needed to consolidate the floor across manifests (pyproject.toml and pixi.toml) to prevent publishing install contracts permitting untested versions.

## Repository

ProjectHephaestus (`HomericIntelligence/ProjectHephaestus`)

## Files Changed in Issue #631

- `pyproject.toml` — Raised PyGithub floor from `>=1.55,<3` to `>=2.9.1,<3` (matches pixi.toml)
- `pixi.toml` — Already had `pygithub = ">=2.9.1,<3"` (dev/test environment floor)
- `.github/dependabot.yml` — Added commit-message prefix and groups for pip and github-actions ecosystems
- `tests/unit/scripts/test_dependency_floor_consistency.py` — New regression test (2 test functions)

## Key Findings

### Why Floor Consolidation Matters

**Problem State:**
- Published contract (pyproject.toml): `PyGithub>=1.55,<3`
- Dev/test environment (pixi.toml): `PyGithub>=2.9.1,<3`
- Result: Users installing from published contract get PyGithub 1.x (within contract), but code requires 2.x → silent runtime failures

**Root Cause:**
PyGithub 1.x and 2.x are API-incompatible:
- 1.x: Uses older API patterns
- 2.x: Refactored API (incompatible with 1.x code)

Code in ProjectHephaestus targets 2.x API; installing 1.x breaks silently.

### Regression Test Strategy

The regression test uses `tomllib` to:
1. Parse both manifests as TOML files
2. Extract PyGithub constraint strings
3. Parse floor version from constraint (`>=X.Y.Z` syntax)
4. Compare floors across manifests
5. Verify floor is 2.x or higher

**Test Functions:**
- `test_pygithub_floor_matches_pixi()` — Ensures pyproject.toml and pixi.toml have identical floors
- `test_pygithub_floor_is_2x_or_higher()` — Ensures floor is at least 2.x

### Dependabot Configuration Note

Dependabot has a quirk: when commit-message prefix ends with `)`, it auto-appends a colon:
- Prefix: `chore(deps)` → Auto-becomes: `chore(deps): ...`
- This is documented in `.github/dependabot.yml` with a comment referencing GitHub docs

**POLA (Principle of Least Astonishment)**: Without documentation, future maintainers might be confused why Dependabot adds the colon. The commit-message config documents this behavior.

### Verification

PR #652 (fixes #631) passed all CI checks:
- Unit tests: 2566 passing (including new regression tests)
- Pre-commit hooks: ruff, mypy, YAML validation
- CI workflow: verified-ci (all green)

## Learnings for Other Projects

This workflow applies to **any dependency with API-incompatible major versions**:
- Validate that all manifests declare the same floor
- Create regression tests (using tomllib or equivalent TOML parser)
- Document any auto-behavior in configs (like Dependabot's auto-colon)
- Commit tests to enforce consistency going forward

## Implementation Details

### _floor() Helper Function

```python
def _floor(spec: str) -> str:
    """Extract floor version from PEP 508 / pixi constraint.
    
    Args:
        spec: e.g., "PyGithub>=2.9.1,<3" or ">=2.9.1,<3"
    
    Returns:
        e.g., "2.9.1"
    """
    if ">=" not in spec:
        raise AssertionError(f"No '>=' floor found in constraint spec: {spec}")
    
    after_gte = spec.split(">=", 1)[1]
    version = after_gte.split(",")[0].strip()
    return version
```

Key points:
- Handles both full constraint strings (`PyGithub>=...`) and bare versions (`>=...`)
- Robust against whitespace
- Stops at comma (before ceiling constraint)

### Test Structure

```python
@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[3]

class TestDependencyFloorConsistency:
    def test_pygithub_floor_matches_pixi(self, repo_root: Path) -> None:
        # Load pyproject.toml with tomllib.load()
        # Navigate to [project.optional-dependencies.github]
        # Find PyGithub spec
        # Load pixi.toml with tomllib.load()
        # Navigate to [dependencies.pygithub]
        # Compare floors using _floor() helper
        # Assert equality
    
    def test_pygithub_floor_is_2x_or_higher(self, repo_root: Path) -> None:
        # Load pyproject.toml
        # Extract PyGithub floor
        # Parse major version
        # Assert >= 2
```

## PR Details

**PR #652**: https://github.com/HomericIntelligence/ProjectHephaestus/pull/652

Merge strategy: Squash merge (ProjectHephaestus policy: no rebase merges)

Commit message:
```
fix(deps): consolidate PyGithub floor and add dependabot commit-convention config

- Raise pyproject.toml PyGithub floor from >=1.55 to >=2.9.1 to match pixi.toml
  and prevent publishing install contracts permitting API-incompatible 1.x versions
- Add commit-message.prefix and groups to .github/dependabot.yml (pip and
  github-actions ecosystems) to match conventional-commit policy
- Add regression test to verify PyGithub floor consistency across manifests

Fixes #631
```

## Test Verification

```bash
pytest tests/unit/scripts/test_dependency_floor_consistency.py -v
# Output:
# tests/unit/scripts/test_dependency_floor_consistency.py::TestDependencyFloorConsistency::test_pygithub_floor_matches_pixi PASSED [ 50%]
# tests/unit/scripts/test_dependency_floor_consistency.py::TestDependencyFloorConsistency::test_pygithub_floor_is_2x_or_higher PASSED [100%]
# ========================== 2 passed in 0.23s ==========================
```

All 2566 unit tests pass; no regressions.

## Related Documentation

- ProjectHephaestus CLAUDE.md: Security and dependency management guidelines
- Python tomllib docs: TOML parsing (built-in to 3.11+)
- GitHub Dependabot docs: Commit-message configuration options
- PEP 508: Version specifier syntax (`>=X.Y.Z,<N`)

## Skill Scope

This skill documents the **detection and prevention** workflow for dependency floor skew. It applies to:
- Multi-manifest projects (pyproject.toml, pixi.toml, requirements.txt, etc.)
- Dependencies with API-incompatible major versions
- Regression test strategies using TOML parsing
- Dependabot configuration for manifest consistency

**Out of scope:**
- General dependency management (dependency upgrades, version pinning strategies)
- Specific to PyGithub (workflow applies to any incompatible-version dependency)
- CI/CD configuration beyond the dependency-specific workflow
