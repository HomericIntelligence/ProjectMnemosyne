---
name: "Refactor for Extensibility"
description: "Systematic workflow for preparing codebases for extensibility through extraction, parameterization, and protocol-based abstraction"
category: architecture
date: 2026-02-05
user-invocable: false
---
# Refactor for Extensibility

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-05 |
| **Objective** | Prepare codebase for dynamic benchmark generator by extracting reusable logic, eliminating coupling, and formalizing interfaces |
| **Outcome** | ✅ Successfully completed 6/9 PRs: extracted discovery library, removed 1,051 lines of dead/duplicate code, created pluggable SubtestProvider, formalized TestFixture schema |
| **Net Impact** | -415 lines while adding significant extensibility capabilities |

## When to Use This Skill

Use this workflow when you need to:
- Prepare a codebase for a new feature that requires pluggable behavior
- Extract hardcoded logic that blocks extensibility
- Remove tight coupling between components
- Formalize implicit contracts into explicit schemas/protocols
- Add new capabilities without breaking existing code

**Trigger phrases:**
- "Prepare the codebase for [new feature]"
- "Make [component] pluggable/extensible"
- "Extract [hardcoded logic] into reusable library"
- "We need to support [alternative implementation]"

## Verified Workflow

### Phase 1: Discovery and Planning

1. **Identify coupling points** - Where is behavior hardcoded?
   - Filesystem paths (`self._get_shared_dir()`)
   - Discovery logic (`_discover_subtests()`)
   - Magic values (prefix lengths, defaults)
   - One-time migration scripts

2. **Design the end state** - What does extensibility look like?
   - Protocol interfaces for pluggable behavior
   - Parameterized constructors for overridable paths
   - Reusable library modules
   - Formal dataclass schemas

3. **Plan PR sequence** - Break into small, focused PRs:
   ```
   PR1: Extract library (create new)
   PR2: Delete old code (remove references)
   PR3: Consolidate duplication
   PR4: Document relationships
   PR5: Extract protocol interface
   PR6: Formalize schemas
   ```

### Phase 2: Extract Before Delete

**CRITICAL: Never delete until extraction is complete and merged.**

```python
# Step 1: Create library with reusable logic
# scylla/discovery/agents.py
def discover_agents(source_dir: Path) -> dict[int, list[Path]]:
    """Parameterized version - no hardcoded paths."""
    ...

# Step 2: Wait for PR merge

# Step 3: Delete old script
# scripts/organize_agents.py → DELETE
```

**Why this order:**
- Extraction is reversible (just delete new files)
- Deletion is destructive (Git history recovery is inconvenient)
- Separate PRs are easier to review

### Phase 3: Protocol-Based Abstraction

Use Protocol for pluggable behavior without breaking existing code:

```python
# Define protocol
class SubtestProvider(Protocol):
    def discover_subtests(
        self, tier_id: TierID, skip_agent_teams: bool = False
    ) -> list[SubTestConfig]: ...

# Create default implementation
class FileSystemSubtestProvider:
    def __init__(self, shared_dir: Path) -> None:
        self.shared_dir = shared_dir

    def discover_subtests(self, tier_id, skip_agent_teams=False):
        # Extract existing logic here
        ...

# Make client accept protocol
class TierManager:
    def __init__(
        self,
        tiers_dir: Path,
        subtest_provider: SubtestProvider | None = None,  # NEW
    ):
        if subtest_provider is None:
            subtest_provider = FileSystemSubtestProvider(shared_dir)
        self.subtest_provider = subtest_provider
```

**Benefits:**
- 100% backward compatible (defaults to old behavior)
- Enables future `DynamicSubtestProvider` without changing TierManager
- Type-safe with mypy/pyright

### Phase 4: Parameterize Hardcoded Paths

Replace path computation with optional parameters:

```python
# Before (hardcoded)
class TierManager:
    def __init__(self, tiers_dir: Path):
        self.tiers_dir = tiers_dir
        config_dir = Path(__file__).parent.parent.parent / "config"
        self._shared_dir = self._get_shared_dir()  # Computed from tiers_dir

# After (parameterized)
class TierManager:
    def __init__(
        self,
        tiers_dir: Path,
        shared_dir: Path | None = None,      # NEW
        config_dir: Path | None = None,      # NEW
    ):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent.parent / "config"
        if shared_dir is None:
            shared_dir = self._get_shared_dir()

        self._shared_dir = shared_dir  # Store for reuse
```

**Pattern:**
1. Add optional parameter with `None` default
2. Compute default value only if not provided
3. Store computed/provided value for reuse
4. Replace all `_get_x()` calls with stored value

### Phase 5: Formalize Implicit Schemas

Convert dict-based configs to dataclasses with I/O methods:

```python
@dataclass
class TestFixture:
    """Formalized schema - the contract generators must satisfy."""
    id: str
    name: str
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
        """Load from standard layout."""
        ...

    def to_directory(self, path: Path) -> None:
        """Write to standard layout."""
        ...
```

**Why dataclass over dict:**
- Type checking catches errors early
- Auto-generated `__init__`, `__repr__`
- Clear schema documentation
- Round-trip I/O methods

### Phase 6: Extract Magic Values

```python
# Before (scattered magic values)
if not file_name[:2].isdigit():  # What is 2?
    continue
extends_previous = tier_id != TierID.T0 or int(subtest_id) >= 2  # What is 2?
system_prompt_mode = config_data.get("system_prompt_mode", "custom")  # Why "custom"?

# After (named constants)
SUBTEST_ID_PREFIX_LENGTH = 2  # "NN" prefix in filenames
DEFAULT_SYSTEM_PROMPT_MODE = "custom"
T0_FIRST_EXTENDING_SUBTEST = 2  # T0 00-01 don't extend, 02+ do

if not file_name[:SUBTEST_ID_PREFIX_LENGTH].isdigit():
    continue
extends_previous = tier_id != TierID.T0 or int(subtest_id) >= T0_FIRST_EXTENDING_SUBTEST
```

## Failed Attempts & Lessons Learned
| Attempt | Issue | Resolution |
|---------|-------|------------|
| See detailed notes below | Various approaches tried | Refer to documentation in this section |


### ❌ Failed: Trying to refactor everything in one PR

**What happened:** Initially considered a single large PR with all changes.

**Why it failed:**
- Too many changes to review at once
- Hard to isolate if something breaks
- Difficult to roll back specific changes
- Reviewers overwhelmed by scope

**Solution:** Split into 9 focused PRs following dependency order.

### ❌ Failed: Deleting scripts before creating library

**What happened:** Considered deleting old scripts first, then extracting logic.

**Why it failed:**
- Would break existing workflows during transition
- No way to verify extraction matches original behavior
- Higher risk of data loss

**Solution:** Extract → Verify → Delete pattern. Keep old code until new code is proven.

### ❌ Failed: Linter reverting SubtestProvider changes

**What happened:** After committing SubtestProvider extraction, linter reverted `tier_manager.py` to old code.

**Why it failed:**
- Didn't notice linter ran between commit and next work
- Lost track of which branch had which changes

**Solution:**
- Always `git status` before starting new work
- Verify imports work immediately after refactoring
- Check for linter changes in git diff before committing

### ❌ Avoided: Breaking backward compatibility

**Almost tried:** Removing optional parameters and requiring all callers to pass values.

**Why that would fail:**
- Breaks all existing callers
- Forces changes across entire codebase
- Hard to test incrementally

**Solution:** Make all new parameters optional with smart defaults. Old code works unchanged.

## Results & Parameters

### Completed PRs

| PR | Phase | Files Changed | Lines Changed | Status |
|----|-------|---------------|---------------|--------|
| #356 | 1.1 | +4 new | +439 | ✅ Merged |
| #357 | 1.2 | -6 deleted | -945 | ✅ Merged |
| #358 | 1.3 | +1, ~2 | +37/-153 | ✅ Merged |
| #359 | 1.4 | ~6 | +130 | ✅ Merged |
| #360 | 2.1-2.2 | +1, ~1 | +197/-115 | ✅ Merged |
| #361 | 2.3-2.4 | ~2 | +189/-12 | ✅ Merged |

**Total Impact:**
- Created: 5 new files
- Deleted: 6 old scripts
- Modified: 11 files
- Net: -415 lines (removed 1,051, added 636)

### Key Files Created

```
scylla/discovery/__init__.py         # Public API exports
scylla/discovery/agents.py           # Agent discovery (78 lines → library)
scylla/discovery/skills.py           # Skill discovery (161 lines → library)
scylla/discovery/blocks.py           # Block extraction (81 lines → library)
scylla/e2e/subtest_provider.py       # Protocol + FileSystemSubtestProvider
scripts/docker_common.sh             # Shared Docker functions
```

### Key Patterns Used

**1. Extract-Parameterize-Protocol Pattern:**
```
Old: Hardcoded logic in _private_method()
  ↓
New: Reusable function(source_dir: Path)
  ↓
Protocol: class Provider(Protocol): def discover(...): ...
  ↓
Client: accepts Provider, defaults to FileSystemProvider
```

**2. Optional Parameter with Smart Default:**
```python
def __init__(
    self,
    required: Path,
    optional: Path | None = None,  # None = use default
):
    if optional is None:
        optional = self._compute_default()
    self._value = optional
```

**3. Backward-Compatible Schema Evolution:**
```python
@classmethod
def from_directory(cls, path: Path) -> Schema:
    try:
        # Try new structured loading
        return cls._load_structured(path)
    except (FileNotFoundError, ValueError):
        # Fallback to old dict-based parsing
        return cls._load_legacy(path)
```

## Commands Used

```bash
# Standard PR workflow
git checkout -b prN-feature-name
git add <files>
git commit -m "type(scope): description

Details...

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
git push -u origin prN-feature-name
gh pr create --title "..." --body "..." --label "type"
gh pr merge --auto --rebase

# Verification between changes
python -c "from scylla.discovery import *; print('Success')"
git status  # Check for linter changes
git diff    # Review before commit
```

## References

- Plan file: See conversation transcript for full 5-phase, 9-PR plan
- CLAUDE.md: Never push directly to main - all changes via PR
- Related skills: `gh-create-pr-linked`, `phase-implement`

## Future Enhancements

**Remaining PRs (7-9):**
- PR7: Rename `executor.TierConfig` → `GlobalTierConfig` (name collision fix)
- PR8: Add `BenchmarkSpec`, `RubricSpec`, `ResourceSpec` schemas
- PR9: Verification tests for discovery library and providers

**Next steps for dynamic generator:**
- Implement `DynamicSubtestProvider(BenchmarkSpec)`
- Create LLM-based benchmark generation pipeline
- Add validation tests for generated benchmarks
