# Raw Session Notes - Refactor for Extensibility

## Session Timeline

1. **Started:** Analysis of plan to prepare codebase for dynamic benchmark generator
2. **PR1 (#356):** Created `scylla/discovery/` library
3. **PR2 (#357):** Deleted 6 scripts (3 extracted + 3 one-time migrations)
4. **PR3 (#358):** Consolidated Docker scripts into `docker_common.sh`
5. **PR4 (#359):** Added recovery script documentation
6. **PR5 (#360):** Extracted `SubtestProvider` protocol, parameterized `TierManager`
7. **PR6 (#361):** Added `TestFixture` dataclass with I/O methods

## Detailed PR Breakdown

### PR #356: Discovery Library
**Files:**
- `scylla/discovery/__init__.py` - Exports
- `scylla/discovery/agents.py` - Agent level parsing, discovery, organization
- `scylla/discovery/skills.py` - Skill categorization, discovery
- `scylla/discovery/blocks.py` - CLAUDE.md block extraction

**Key Functions:**
```python
# Agents
parse_agent_level(file_path: Path) -> int | None
discover_agents(source_dir: Path) -> dict[int, list[Path]]
organize_agents(source_dir: Path, dest_dir: Path) -> dict[int, list[str]]

# Skills
get_skill_category(skill_name: str) -> str
discover_skills(source_dir: Path) -> dict[str, list[Path]]
organize_skills(source_dir: Path, dest_dir: Path) -> dict[str, list[str]]

# Blocks
discover_blocks(claude_md_path: Path, block_defs=None) -> list[tuple[...]]
extract_blocks(source_file: Path, output_dir: Path, block_defs=None) -> list[Path]
```

**Pattern:** Separate discovery (returns data) from organization (writes files)

### PR #357: Delete Extracted Scripts
**Deleted:**
- `scripts/organize_agents.py` (78 lines)
- `scripts/organize_skills.py` (161 lines)
- `scripts/extract_blocks.py` (81 lines)
- `scripts/migrate_to_symlinks.py` (292 lines)
- `scripts/migrate_t0_to_blocks.py` (223 lines)
- `scripts/add_test_docstrings.py` (116 lines)

**Total:** 951 lines removed

### PR #358: Docker Consolidation
**Created:** `scripts/docker_common.sh`
**Functions:**
- `check_docker_prerequisites()`
- `ensure_image_built()`
- `prepare_credential_mount()`
- `prepare_env_vars()`
- `cleanup_temp_creds()`

**Reduced:** ~100 lines of duplication between two scripts

### PR #359: Recovery Documentation
**Updated:** `scripts/README.md`
**Added:** Recovery Scripts section with decision table
**Cross-references in:**
- `rerun_agents.py`
- `rerun_judges.py`
- `regenerate_results.py`
- `regenerate_agent_results.py`
- `repair_checkpoint.py`

### PR #360: SubtestProvider Protocol
**Created:** `scylla/e2e/subtest_provider.py`

**Protocol:**
```python
class SubtestProvider(Protocol):
    def discover_subtests(
        self, tier_id: TierID, skip_agent_teams: bool = False
    ) -> list[SubTestConfig]: ...
```

**Implementation:**
```python
class FileSystemSubtestProvider:
    def __init__(self, shared_dir: Path) -> None:
        self.shared_dir = shared_dir

    def discover_subtests(self, tier_id, skip_agent_teams=False):
        # Extracted from TierManager._discover_subtests()
        ...
```

**TierManager Changes:**
```python
def __init__(
    self,
    tiers_dir: Path,
    shared_dir: Path | None = None,           # NEW
    config_dir: Path | None = None,           # NEW
    subtest_provider: SubtestProvider | None = None,  # NEW
):
    # Auto-detect if not provided
    if shared_dir is None:
        shared_dir = self._get_shared_dir()
    self._shared_dir = shared_dir

    if subtest_provider is None:
        subtest_provider = FileSystemSubtestProvider(self._shared_dir)
    self.subtest_provider = subtest_provider
```

**Constants Extracted:**
- `SUBTEST_ID_PREFIX_LENGTH = 2`
- `DEFAULT_SYSTEM_PROMPT_MODE = "custom"`
- `T0_FIRST_EXTENDING_SUBTEST = 2`

### PR #361: TestFixture Schema
**Added to `scylla/e2e/models.py`:**

```python
@dataclass
class TestFixture:
    id: str
    name: str
    description: str
    language: str
    source_repo: str
    source_hash: str
    task_prompt: str
    criteria: str
    rubric: dict[str, Any]
    tiers: list[str]
    timeout_seconds: int = 3600

    @classmethod
    def from_directory(cls, path: Path) -> TestFixture:
        # Load test.yaml, prompt.md, expected/criteria.md, expected/rubric.yaml
        ...

    def to_directory(self, path: Path) -> None:
        # Write standard directory structure
        ...
```

**ExperimentConfig Additions:**
```python
criteria_file: Path | None = None
rubric_file: Path | None = None
```

**Updated:** `scripts/run_e2e_experiment.py` to use `TestFixture.from_directory()` with fallback

## Technical Decisions

### Why Protocol over ABC?
- No inheritance required for implementations
- More Pythonic (duck typing)
- Compatible with structural subtyping
- Easier to test (no need to subclass)

### Why dataclass over Pydantic?
- Simpler dependencies
- Sufficient for this use case
- Standard library (no external deps)
- Good mypy support

### Why Optional Parameters over Builder Pattern?
- Simpler API
- Backward compatible by default
- Common Python idiom
- No additional complexity

## Linter Issues Encountered

**Problem:** Black reformatted `tier_manager.py` between commits, removing SubtestProvider changes

**Detection:** System reminder about file modifications

**Resolution:** Always run `git status` and `git diff` before new work to catch linter changes

## Testing Strategy

**Each PR:**
1. Verify imports: `python -c "from module import *; print('Success')"`
2. Check git status for linter changes
3. Run pytest (mentioned in PRs but not shown in execution)

**No tests written yet** - marked for PR #9

## Remaining Work (PRs 7-9)

### PR 7: Rename TierConfig
**Problem:** Name collision between:
- `scylla.e2e.models.TierConfig` (per-test dataclass)
- `scylla.executor.tier_config.TierConfig` (global Pydantic model)

**Solution:** Rename executor version to `GlobalTierConfig`

### PR 8: Schema Definitions
**Files to create:**
- `scylla/e2e/benchmark_spec.py` - Complete benchmark specification
- `scylla/e2e/rubric_spec.py` - Rubric schema with validation
- `scylla/e2e/resource_spec.py` - Typed resource specifications

### PR 9: Verification Tests
**Files to create:**
- `tests/unit/discovery/test_discovery.py`
- `tests/unit/e2e/test_subtest_provider.py`
- `tests/unit/e2e/test_benchmark_spec.py`
- `tests/unit/e2e/test_rubric_spec.py`
- `tests/unit/e2e/test_resource_spec.py`

## Key Metrics

**Code Reduction:**
- Scripts deleted: 951 lines
- Docker consolidation: ~100 lines
- Total removed: ~1,051 lines

**Code Addition:**
- Discovery library: 439 lines
- SubtestProvider: ~160 lines
- TestFixture: ~150 lines
- Documentation: ~130 lines
- Total added: ~879 lines

**Net:** -172 lines while adding significant capabilities

## Anti-Patterns Avoided

1. ❌ Big bang refactoring → ✅ Incremental PRs
2. ❌ Delete then extract → ✅ Extract then delete
3. ❌ Breaking changes → ✅ Backward compatible defaults
4. ❌ Implicit contracts → ✅ Explicit schemas/protocols
5. ❌ Magic values → ✅ Named constants
6. ❌ Hardcoded paths → ✅ Parameterized constructors
