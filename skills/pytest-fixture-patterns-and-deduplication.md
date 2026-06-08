---
name: pytest-fixture-patterns-and-deduplication
description: "Use when: (1) pytest.mark.parametrize lists hardcode fixture filenames that must be manually updated when new fixtures are added — replace with glob-based auto-discovery; (2) test fixtures have duplicated YAML configs — find | md5sum shows 40+ duplicates and runtime block-based composition eliminates them; (3) duplicated test fixture configs should be migrated to a centralized shared location; (4) a schema validation test parametrizes over tier fixture files but only early tiers exist (e.g. t0/t1) and new tiers need coverage across the full range; (5) YAML fixture files and test parametrize lists must be expanded when new tiers are added to the tier registry; (6) a second division's fixture set is added to a flat tests/fixtures/ directory and capture-fixtures CLI needs named subdirs; (7) testing multi-level directory nesting in shutil.copytree migrations where deep paths must survive migration; (8) fixture and implementation symmetry must be validated — fixture YAML keys must match tested interface fields; (9) checkpoint state machine fixtures encode multi-state test scenarios and need refactoring for reuse; (10) an autouse fixture in conftest.py must reset module-level singleton state (asyncio objects, circuit breakers) at the broadest scope."
category: testing
date: 2026-06-07
version: "1.0.0"
user-invocable: false
history: pytest-fixture-patterns-and-deduplication.history
tags:
  - pytest
  - fixtures
  - parametrize
  - deduplication
  - test-fixtures
  - auto-discovery
  - tier-fixtures
  - shared-fixtures
  - copytree
  - checkpoint
---
# pytest-fixture-patterns-and-deduplication

Unified patterns for managing pytest fixtures: auto-discovering parametrize fixtures, deduplicating and migrating fixture configs to shared locations, expanding tier fixture coverage, organizing multi-division fixture directories, validating fixture-implementation symmetry, and building checkpoint state-machine fixtures.

## Overview

| Item | Details |
| ------ | --------- |
| Date | 2026-06-07 |
| Objective | Consolidate fixture auto-discovery, deduplication/migration, tier coverage, multi-division layout, copytree nesting coverage, fixture-implementation symmetry, and checkpoint-fixture patterns into one canonical |
| Outcome | Success — patterns verified across ProjectScylla, ProjectOdyssey, and TitanSchedule (thousands of tests passing, fixture sizes reduced up to 97%) |
| Verification | verified-ci |

## When to Use

- A `pytest.mark.parametrize` list enumerates fixture filenames by hand and should auto-discover via glob
- Test fixtures duplicate the same YAML/markdown content across many directories (`find | md5sum` shows 10+/40+ duplicates)
- Duplicated test fixture configs should be centralized in a single shared location with runtime loading
- A schema validation test parametrizes over tier fixtures but only early tiers (t0/t1) exist
- New tiers are added to the tier registry and both fixture files and parametrize lists / count assertions must expand
- A second division's fixture set is added to a flat `tests/fixtures/` directory and the capture CLI needs named subdirs
- Testing multi-level directory nesting survives a `shutil.copytree`-based migration
- Fixture YAML keys must stay symmetric with the tested interface (fixture tests must go through the loader, not the validator directly)
- Checkpoint state-machine fixtures encode multi-state scenarios and need cross-level consistency or shared-fixture extraction

## Verified Workflow

### Quick Reference

```python
# Auto-discover parametrize fixtures (glob, sorted, readable IDs)
@pytest.mark.parametrize(
    "fixture_file",
    sorted(TIER_FIXTURES_DIR.glob("t*.yaml")),
    ids=lambda p: p.name,
)
def test_real_tier_fixture_is_valid(self, schema, fixture_file: Path) -> None:
    check_schema(load_yaml(fixture_file), schema)
```

```bash
# Quantify fixture duplication before any dedup/migration
find tests -type f -name "config.yaml" | xargs md5sum \
  | awk '{print $1}' | sort | uniq -c | sort -rn | head -30
```

```python
# Checkpoint fixture: a higher state MUST have backing lower state
checkpoint = E2ECheckpoint(
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    run_states={"T0": {"01": {"1": "worktree_cleaned"}}},  # "01" backed
)
```

### Detailed Steps

#### 1. Auto-discover parametrize fixtures (replace hardcoded lists)

Replace a hardcoded `@pytest.mark.parametrize` filename list with glob-based discovery so new fixture files are picked up at collection time with zero code changes.

Before:

```python
TIER_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures" / "config" / "tiers"

@pytest.mark.parametrize(
    "fixture_file",
    ["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"],
)
def test_real_tier_fixture_is_valid(self, schema, fixture_file: str) -> None:
    data = load_yaml(TIER_FIXTURES_DIR / fixture_file)
    check_schema(data, schema)
```

After:

```python
from pathlib import Path

@pytest.mark.parametrize(
    "fixture_file",
    sorted(TIER_FIXTURES_DIR.glob("t*.yaml")),
    ids=lambda p: p.name,
)
def test_real_tier_fixture_is_valid(self, schema, fixture_file: Path) -> None:
    data = load_yaml(fixture_file)  # full path, no joining
    check_schema(data, schema)
```

Key changes:

1. Parameter type `str` → `Path` (glob yields full paths, no joining)
2. `sorted()` — `Path.glob()` order is filesystem-dependent; sorting stabilizes order across Linux/macOS/CI runs
3. `ids=lambda p: p.name` — keeps test IDs readable (`t0.yaml`) instead of full absolute paths

#### 2. Deduplicate fixtures via runtime block-based composition

When the same content is duplicated across many fixture dirs, decompose it into reusable blocks and compose at runtime.

```bash
# Identify the duplication, then list files sharing a hash
find tests -type f -name "*.md" | xargs md5sum | awk '{print $1}' | sort | uniq -c | sort -rn | head -20
grep -r "_compose\|_symlink\|resources" src/ --include="*.py"   # check existing infra first
```

Map directory names to block compositions, write a migration script with `--dry-run`, then delete duplicates after the config update:

```python
DIRECTORY_TO_BLOCKS = {
    "00-empty": [],
    "02-critical-only": ["B02"],
    "03-full": ["B01", "B02", "B03"],  # ... B01-B18
}
```

```yaml
# config.yaml after migration — runtime composition from shared blocks
name: "Full CLAUDE.md"
extends_previous: false
resources:
  claude_md:
    blocks: [B01, B02, B03, B04, B05, B06, B07, B08, B09, B10]
```

Result on ProjectScylla: removed 1034 CLAUDE.md files (239,888 lines), fixtures 56MB → 47MB. Always run hash analysis first; check for existing composition infra (it may exist but never have been run).

#### 3. Migrate duplicated configs to a centralized shared location

When configs are test-independent but duplicated per-test, move the unique set to a shared dir and load it at runtime, overlaying only true per-test overrides.

```bash
mkdir -p tests/claude-code/shared/subtests/t{0,1,2,3,4,5,6}
# Copy canonical configs from one test; rename NN-subtest/config.yaml -> NN-subtest.yaml
```

```python
def _discover_subtests(self, tier_id, tier_dir):
    shared_dir = self._get_shared_dir() / "subtests" / tier_id.value.lower()
    subtests = self._load_shared_subtests(tier_id, shared_dir)   # shared first
    subtest_by_id = {s.id: s for s in subtests}
    if tier_dir.exists():
        self._overlay_test_specific(subtest_by_id, tier_dir, tier_id)  # overlay
    return list(subtest_by_id.values())
```

Result on ProjectScylla: 47MB → 1.4MB (97% reduction), 5,361 → 160 config files, 120,735 lines deleted. Only prompts and expected results need to be per-test.

#### 4. Tier fixture schema coverage — add a fixture per tier

When schema tests parametrize over tier fixtures but only t0/t1 exist, add one fixture per tier exercising a distinct boolean capability combination. The `tier:` field must equal the filename stem (else `ConfigurationError`).

```yaml
# t2.yaml — Tooling tier: only uses_tools
tier: "t2"
name: "Tooling"
description: "External tools and MCP servers"
uses_tools: true
uses_delegation: false
uses_hierarchy: false
```

Coverage matrix (each tier hits a unique schema path):

| Tier | uses_tools | uses_delegation | uses_hierarchy |
| ------ | ----------- | ---------------- | ---------------- |
| t0 | — | — | — |
| t1 | — | — | — |
| t2 | true | false | false |
| t3 | false | true | false |
| t4 | false | false | true |
| t5 | true | true | false |
| t6 | true | true | true |

#### 5. Expand tier fixture coverage — sync fixtures AND assertions

When a new tier is added to the registry, both the fixture files and the test assertions must expand. Update the count assertion in `test_load_all_tiers` and the parametrize list in the schema test.

```python
# test_config_loader.py — count + name assertions
assert len(tiers) == 7
assert "t2" in tiers
assert tiers["t2"].name == "Tooling"
# ... repeat for t3-t6

# test_json_schemas.py — parametrize list (or prefer glob, see step 1)
@pytest.mark.parametrize(
    "fixture_file",
    ["t0.yaml", "t1.yaml", "t2.yaml", "t3.yaml", "t4.yaml", "t5.yaml", "t6.yaml"],
)
```

A hardcoded count assertion out of sync with the fixture set is the common failure here. Verify with `pixi run python -m pytest tests/unit/config/ -v`.

#### 6. Multi-division fixture directories — flat to slugged subdirs

When adding a second division's fixture set to a flat `tests/fixtures/`, move existing fixtures into a named subdir, teach the capture CLI to auto-name subdirs from the division name, and parametrize tests to auto-discover all sets.

```python
# capture CLI: resolve division name first, write to output_dir / slug
slug = _slugify(division_name)               # "18s - 15s Power League" -> "18s-15s-power-league"
output_dir = output_dir / slug
output_dir.mkdir(parents=True, exist_ok=True)

# integration test: discover all subdirs containing the marker file
FIXTURES_ROOT = Path(__file__).parent / "fixtures"
def _fixture_dirs() -> list[Path]:
    if not FIXTURES_ROOT.exists():
        return []
    return sorted(d for d in FIXTURES_ROOT.iterdir()
                  if d.is_dir() and (d / "plays.json").exists())

_ALL = _fixture_dirs()
@pytest.mark.skipif(len(_ALL) == 0, reason="run capture-fixtures <URL>")
@pytest.mark.parametrize("fixture_dir", _ALL, ids=[d.name for d in _ALL])
class TestEndToEndWithFixtures:
    ...
```

For test classes that only apply to dirs with certain files, filter at parametrize time:
`[d for d in _ALL if any(d.glob("poolsheet_*.json"))]`. Adding a division now adds 7N tests automatically.

#### 7. copytree deep-path coverage — verify nested dirs survive migration

`shutil.copytree` is recursive by default but coverage is often missing for multi-level nesting. Add a test that creates a nested subdir and asserts the full destination path survives.

```python
skill_dir = make_skill_dir(odyssey_skills, "agent-run-orchestrator")
nested_dir = skill_dir / "scripts" / "utils"
nested_dir.mkdir(parents=True)
(nested_dir / "helper.sh").write_text("#!/bin/bash\necho helper")

# ... call migrate_skill(...)

nested_helper = (
    mnemosyne_skills / "tooling" / "agent-run-orchestrator"
    / "skills" / "agent-run-orchestrator" / "scripts" / "utils" / "helper.sh"
)
assert nested_helper.exists(), f"Expected deeply nested helper at {nested_helper}"
```

Destination path follows `<category>/<skill>/skills/<skill>/<subdir>/<nested>`. No production change needed — the test protects recursive behavior against regression.

#### 8. Fixture-implementation symmetry — test through the loader

When one loader's fixture tests call the validator directly while another goes through the loader, eliminate the asymmetry: add the validator to the loader and write fixture tests that go through `loader.load_X()`, using `caplog` for warnings.

```python
# validator skips _-prefixed fixtures; returns warnings, never raises
def validate_filename_tier_consistency(config_path: Path, tier: str) -> list[str]:
    stem = config_path.stem
    if stem.startswith("_"):
        return []                      # skip test fixtures
    if stem == tier:
        return []
    return [f"Config filename '{stem}.yaml' does not match tier '{tier}'."]

# loader: guard normalization for _-prefixed names, then call validator
if not tier.startswith("_"):
    tier = tier.lower().strip()
    if not tier.startswith("t"):
        tier = f"t{tier}"
config = TierConfig(**data)
for w in validate_filename_tier_consistency(tier_path, config.tier):
    logger.warning(w)
```

```python
# test goes through the loader, asserts on caplog (NOT a direct validator call)
def test_filename_mismatch_warns(self, tmp_path, caplog):
    (tmp_path / "config" / "tiers").mkdir(parents=True)
    (tmp_path / "config" / "tiers" / "t1.yaml").write_text("tier: t0\nname: Vanilla\n")
    loader = ConfigLoader(str(tmp_path))
    with caplog.at_level(logging.WARNING):
        config = loader.load_tier("t1")
    assert config.tier == "t0"
    assert len(caplog.records) == 1
    assert "t1.yaml" in caplog.text and "t0" in caplog.text
```

The `_` prefix convention is first-class: it appears in both the validator (skip validation) and the loader (skip normalization) and both must stay consistent.

#### 9. Checkpoint state-machine fixtures — cross-level consistency

Checkpoint fixtures span a 4-level hierarchy; a higher state assertion requires backing lower-state data or the resume orphan detector resets it to `"pending"`.

```
experiment_state → tier_states → subtest_states → run_states
```

| Higher State | Required Lower State | Validator |
| --- | --- | --- |
| subtest `"aggregated"`/`"runs_complete"` | ≥1 entry in `run_states[tier][subtest]` | `_find_orphaned_subtest_states()` |
| tier `"complete"` | All subtests `"aggregated"` | `_reset_tier_state_for_rerun()` |
| experiment `"complete"` | All tiers complete-family | `_reset_intermediate_runs_in_complete_experiment()` |

```python
# RIGHT — "01" aggregated has a terminal backing run, orphan detector leaves it alone
checkpoint = E2ECheckpoint(
    experiment_state="failed",
    tier_states={"T0": "failed"},
    subtest_states={"T0": {"00": "failed", "01": "aggregated"}},
    run_states={"T0": {"01": {"1": "worktree_cleaned"}}},
)
```

Use `"worktree_cleaned"` as the canonical terminal run state. Audit every fixture:
`grep -n '"aggregated"\|"runs_complete"' tests/unit/e2e/test_runner.py` — each match needs a backing `run_states` entry.

Extract repeated object construction into a shared fixture (adopt all-or-nothing within a class):

```python
@pytest.fixture
def wired_runner(mock_config, mock_tier_manager, tmp_path):
    with patch.object(TierManager, "__init__", return_value=None):
        runner = E2ERunner(mock_config, tmp_path / "tiers", tmp_path / "results")
    runner.tier_manager = mock_tier_manager
    runner.experiment_dir = tmp_path / "experiment"
    runner.experiment_dir.mkdir(parents=True)
    return runner
```

For zombie-detection tests use a guaranteed-dead PID (`_DEAD_PID = 999_999_999`) and real disk I/O instead of mocking `os.kill`. `is_zombie()` requires all three: `status=="running"` AND dead PID AND stale heartbeat.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Minimal checkpoint fixture with `subtest_states` only | Set subtest `"01": "aggregated"` without any `run_states` entry | `_find_orphaned_subtest_states()` correctly reset `"01"` to `"pending"` — an aggregated subtest with no backing run is orphaned | Fixtures must be cross-level consistent; a higher-state assertion requires lower-state backing data |
| Fix only the first failing fixture after a rebase | Fixed one fixture and pushed | A second test in a different class had the same root cause | Audit ALL fixtures with `grep '"aggregated"'` across the whole file, not just the first failure |
| Use a shared `_run_resume` helper for complex checkpoint fixtures | Helper always built `run_states={}` | No way to inject `run_states` through the helper | For tests needing `run_states`, build the checkpoint inline instead of via shared helper |
| `completed_runs={"T0": {"00": {"3": "passed"}}}` (string inner key) | Used `"3"` as the inner dict key | Type is `dict[str, dict[str, dict[int, str]]]` — inner key is `int` | Match declared types exactly; use `{3: "passed"}` |
| Mock-based DataLoader reset assertion (Mojo) | Wrap loader to count `reset()` calls | Mojo structs have no vtable-based mocking / spy trait | Use direct field mutation + observable side effects (finite loss proves reset ran) |
| Parametrize over an unsorted `glob()` result | `Path.glob("t*.yaml")` without `sorted()` | Filesystem-dependent order made failures non-reproducible across platforms/CI | Always wrap glob results in `sorted()` and add `ids=` for readable test IDs |
| Forget normalization guard for `_`-prefixed fixture names | `load_tier("_test-fixture")` without the guard | Became `t_test-fixture` after normalization; the `_test-fixture.yaml` file was never found | Check `tier.startswith("_")` before any normalization; the guard must come first |

## Results & Parameters

- Auto-discovery pattern: `sorted(FIXTURES_DIR.glob("<pattern>"))` + `ids=lambda p: p.name` + `fixture_file: Path`
- Duplication detection: `find tests -name "*.yaml" | xargs md5sum | awk '{print $1}' | sort | uniq -c | sort -rn`
- Tier fixture invariant: `tier:` field == filename stem (else `ConfigurationError`)
- Multi-division slug: `re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'unknown'`
- copytree destination path: `<category>/<skill>/skills/<skill>/<subdir>/<nested>`
- `_` prefix convention: skip both validation and normalization for fixture names
- Checkpoint terminal run state: `"worktree_cleaned"`; zombie PID `999_999_999`; stale heartbeat 300s, fresh 10s (120s default timeout)

Measured outcomes:

| Change | Before | After |
| -------- | -------- | ------- |
| Block-based dedup (ProjectScylla) | 1034 files, 56MB | 0 files, 47MB |
| Shared-config migration (ProjectScylla) | 5,361 files, 47MB | 160 files, 1.4MB |
| Tier fixture expansion | t0-t1 (2 fixtures) | t0-t6 (7 fixtures), 4331 tests pass |
| Multi-division scaling | 7 tests / 1 division | 7N tests / N divisions (automatic) |

Run commands:

```bash
# Schema / config fixture tests
pixi run python -m pytest tests/unit/config/test_json_schemas.py tests/unit/config/test_config_loader.py -v
# Integration tests, suppress coverage floor when run in isolation
pixi run python -m pytest tests/integration/ -v --override-ini="addopts="
# copytree nesting test class
pixi run python -m pytest tests/scripts/test_migrate_odyssey_skills.py::TestMigrateSkillAuxiliaryDirs -v
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Auto-discovery #1433/#1458; dedup; shared migration; tier coverage #1381/#1423; symmetry #808/#950; checkpoint fixtures #815/#1149/#1312/#1485 | [history](pytest-fixture-patterns-and-deduplication.history) |
| ProjectOdyssey | copytree nesting #3769/#4790; Mojo DataLoader reset #3687/#4770 | [history](pytest-fixture-patterns-and-deduplication.history) |
| TitanSchedule | Multi-division AES fixture management (Python 3.14, pytest 9.0.2) | [history](pytest-fixture-patterns-and-deduplication.history) |
