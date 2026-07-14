# hephaestus-env-var-fallback-path-resolution — Session Notes

## Issue Context

**ProjectHephaestus Issue #741**: "Centralize fragile __file__.parents[N] path resolution patterns"

**Discovery**: 5 sites across production and test code use identical patterns to resolve repository root or scripts directory:
- 1 production site: `hephaestus/automation/loop_runner.py:763`
- 4 test sites: automation tests, integration tests, utils tests

All use fragile `__file__.parents[N]` indexing that breaks if directory depth changes or between editable installs and CI packaging.

## Implementation Details

### Pattern Pattern Recognition

All 5 sites follow this structure:

```python
# BEFORE: Fragile and duplicate
some_path = Path(__file__).parents[N] / 'scripts'  # or similar
```

The `parents[N]` index varies by file depth:
- `loop_runner.py` (3 levels deep: hephaestus/automation/loop_runner.py) → needs `parents[2]` to reach repo
- Test files (various depths) → need different indices depending on location

This brittle fragmentation is the **core problem** — any directory structure change requires coordinating updates across 5 files.

### Solution Architecture

**File: `hephaestus/constants.py`** (module-level location ensures both test and production code can import)

```python
def repo_root() -> Path:
    """Env override → pyproject.toml walk-up → RuntimeError"""

def scripts_dir() -> Path:
    """Env override → repo_root derivation → RuntimeError"""

REPO_ROOT = repo_root()
SCRIPTS_DIR = scripts_dir()
```

**Why this pattern?**

1. **Env-var override first** — enables CI to pass HEPHAESTUS_REPO_ROOT without code changes
2. **Walk-up fallback** — mirrors hephaestus/config/paths.py:resolve_projects_dir (existing pattern in codebase)
3. **Explicit failure** — RuntimeError if path not found (not silent None) helps debug CI issues
4. **Module-level export** — both `from hephaestus.constants import REPO_ROOT` and `constants.REPO_ROOT` work
5. **Iteration limit** — `for _ in range(10)` prevents infinite loops in malformed filesystem

### Why Env-Var + Walk-Up (Not Just Walk-Up)

**Editable installs** (`pip install -e .`):
- __file__ points to source tree location
- Walk-up finds pyproject.toml reliably
- ✅ Works great

**Packaged CI environments** (containers, isolated venvs):
- __file__ may point to site-packages location
- pyproject.toml is NOT in site-packages
- Walk-up fails unless repo is present in the container
- ✅ HEPHAESTUS_REPO_ROOT env var saves the day

**Hybrid approach** = works everywhere

### Parallel Pattern: hephaestus/config/paths.py:resolve_projects_dir

This skill mirrors an existing pattern in the codebase:

```python
# From hephaestus/config/paths.py
def resolve_projects_dir() -> Path:
    if env_path := os.getenv('PROJECTS_DIR'):
        path = Path(env_path)
        if path.exists():
            return path
    # Walk-up fallback...
```

**Consistency win**: Using the same pattern ensures:
- Uniform error handling across all path resolvers
- Team familiarity (once you know resolve_projects_dir, repo_root() pattern is obvious)
- No "special cases" — all path resolvers follow env-var + fallback

### Import Placement Issue (ruff isort)

**Failed attempt**: Placed imports after module constants

```python
# WRONG — ruff fails with I001
SCRIPTS_DIR = __file__.parents[2] / 'scripts'

from pathlib import Path  # ❌ Import after constant = I001 error
from hephaestus.constants import REPO_ROOT
```

**Solution**: Always import at top

```python
# RIGHT — isort happy
from pathlib import Path
from hephaestus.constants import REPO_ROOT

SCRIPTS_DIR = REPO_ROOT / 'scripts'
```

This is a standard Python convention (PEP 8), but easy to overlook when refactoring.

## Testing Strategy

### All 5 Sites Replaced in Single Commit

**Why not piecemeal?**
- Initial plan fixed only tests, left production code (loop_runner.py:763)
- Would allow 4 test merges without fixing the production bypass
- Enables technical debt to split across PRs

**Resolution**: All 5 sites fixed in PR #931 commit, caught by pre-merge audit

### Pre-Merge Audit (Critical for DRY verification)

```bash
grep -rn "__file__.*parents.*scripts\|loop_runner.__file__" tests/ hephaestus/
```

**Before PR #931:**
```
hephaestus/automation/loop_runner.py:763:        scripts_root = loop_runner.__file__.parents[2] / "scripts"
tests/unit/automation/test_loop_runner.py:19:    scripts_dir = __file__.parents[3] / 'scripts'
tests/integration/test_cli_entry_points.py:14:    repo_root = __file__.parents[4]
tests/unit/automation/test_implementation_runner.py:31:    scripts_dir = __file__.parents[3] / 'scripts'
tests/unit/utils/test_general_utils.py:26:    scripts_data = __file__.parents[2] / 'data'
```

**After PR #931:**
```
(zero hits)
```

**Why grep instead of IDE search?**
- Catches both __file__ and loop_runner.__file__ patterns (IDE might miss the latter)
- Searches both tests/ AND hephaestus/ (easy to overlook production code)
- Runs in 2 seconds across entire codebase
- Non-negotiable before merging path-related PRs

## Lessons for Future Path Centralization

### 1. Env-Var + Walk-Up Pattern is Robust

✅ Works in:
- Editable installs (pixi, local development)
- Packaged CI (containers with REPO_ROOT set)
- Tests with fixture overrides (can set HEPHAESTUS_REPO_ROOT)

❌ Fails silently in:
- Pure walk-up (doesn't work in packaged CI)
- Pure env-var (doesn't work in editable installs without external setup)

**Recommendation**: Always use both, in that order (env first for override, fallback for robustness)

### 2. No YAGNI Violations

The implementation is minimal:
- **No caching** — repo_root() called once at import time, not in loops
- **No __all__** — module has no prior exports, not needed yet
- **No logging** — caplog/capsys handle test verification if needed
- **No complexity** — env check, walk-up, RuntimeError fit in ~30 lines

Adding any of these would violate KISS without solving a real problem.

### 3. Fixture Approach Doesn't Serve Production Code

Initial idea: Use pytest fixture for `repo_root` in tests

**Why it failed**:
- Fixtures are test-only
- loop_runner.py (production code) can't import a pytest fixture
- Would require keeping both test fixture AND production implementation = more duplication

**Why constants.py works**:
- Both test code and production code import the same module
- Single import serves both test fixtures and production code at module-import time
- True DRY

### 4. Coordinate All Sites in One PR

**Never split path centralization across multiple PRs:**
- PR 1: Fix 4 test sites → merges with tests passing
- PR 2: Fix production site → merges separately
- Result: 2 commits with different patterns, defeats the purpose

**Always fix all identical sites together** — easier to review, easier to audit, prevents staggered debt.

## Related Code References

**Similar pattern in codebase:**
- `hephaestus/config/paths.py:resolve_projects_dir()` — original reference implementation
- `hephaestus/utils/subprocess.py` — other path resolution patterns

**Test coverage:**
- `tests/unit/automation/test_loop_runner.py` — verifies SCRIPTS_DIR resolution
- All other tests verify repo structure integrity

## Verification Checklist (for future centralizations)

- [ ] Identified all identical-pattern sites (grep across both tests/ and production/)
- [ ] Created helper in module-level constants file
- [ ] Used env-var override + fallback pattern (not just one)
- [ ] Placed all imports at top (ruff isort compliance)
- [ ] Replaced all 5 sites in single commit
- [ ] Ran pre-merge grep audit (expect zero hits)
- [ ] Full test suite passes (all phases)
- [ ] No YAGNI additions (no caching/logging/complexity without concrete need)

## References

- Issue: https://github.com/HomericIntelligence/ProjectHephaestus/issues/741
- PR: https://github.com/HomericIntelligence/ProjectHephaestus/pull/931
- Commit: `6c71c29` (fix(automation): centralize scripts_dir resolution in hephaestus.constants)
