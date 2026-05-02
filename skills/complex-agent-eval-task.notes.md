# Session Notes: Complex Agent Eval Task Design

## Context

Session date: 2026-01-01
Project: ProjectScylla
Task: Create T2+ test case for dtype migration evaluation

## User Requirements

1. Create sophisticated test case (not just hello world) for T2+ tiers
2. Clone ProjectOdyssey at commit before PR #3017
3. Use PR #3017 as the task and reference solution
4. Read GitHub issue #3012 and PR #3017 for context
5. Agent cannot access git commits, issues, or GitHub API
6. Agent creates patchfile, judge compares against reference
7. Limit turns to 50 (initially 20, relaxed by user)

## Key Decisions

### Why Patchfile + Workspace (not just patchfile)

- Patchfile shows what changed
- Workspace state shows final file contents
- Both needed for comprehensive evaluation
- Deleted files list extracted separately

### Why 50 Turns (not 20)

- Complex refactoring task (~15 files, ~5000 lines)
- Agent needs exploration time
- Real-world complexity requires flexibility
- User explicitly requested relaxation

### Why Forbidden Actions

- Prevents agents from "cheating" by viewing solution
- Tests true problem-solving ability
- Git history contains the exact solution
- GitHub API exposes issue/PR content

## Files Created

### ProjectScylla (test case)
- tests/002-dtype-native-migration/test.yaml
- tests/002-dtype-native-migration/prompt.md
- tests/002-dtype-native-migration/expected/rubric.yaml
- tests/002-dtype-native-migration/expected/criteria.md
- tests/002-dtype-native-migration/expected/reference/METADATA.yaml
- tests/002-dtype-native-migration/expected/reference/reference.patch
- tests/002-dtype-native-migration/constraints/forbidden.md

### ProjectScylla (infrastructure changes)
- src/scylla/e2e/models.py - Added max_turns field
- src/scylla/e2e/subtest_executor.py - Pass max_turns to adapter
- src/scylla/e2e/llm_judge.py - Patchfile generation and reference comparison
- config/judge/system_prompt.md - Patchfile quality criteria

## Skills Found via /advise

1. `dtype-native-migration` - Exact solution workflow documented
   - Use comptime not alias
   - E8M0 requires manual conversion helpers
   - Bitcast patterns for byte access

2. `e2e-judge-rubric-design` - Rubric design patterns
   - 10 criteria across 3 weighted categories
   - Validity tracking for rate-limited runs
   - Check is_error before subtype

## Technical Details

### max_turns Implementation

```python
# In ExperimentConfig (models.py)
max_turns: int | None = None

# In subtest_executor.py
extra_args: list[str] = []
if self.config.max_turns is not None:
    extra_args.extend(["--max-turns", str(self.config.max_turns)])

adapter_config = AdapterConfig(
    ...
    extra_args=extra_args,
)
```

### Patchfile Generation

```python
def _get_patchfile(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Truncate if > 500 lines
```

### Reference Patch Loading

```python
def _load_reference_patch(reference_path: Path) -> str | None:
    if not reference_path.exists():
        return None
    return reference_path.read_text()
```

## PR Details

- PR #107: feat(e2e): add T2+ dtype migration test case with patchfile comparison
- Branch: feat/002-dtype-native-migration-test
- Files changed: 11
- Lines added: 8975
