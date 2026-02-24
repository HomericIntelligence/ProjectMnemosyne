---
name: fix-resource-prompt-consistency
description: Workflow for fixing inconsistent root-level field mapping in tier configurations and enhancing resource prompt suffixes
category: architecture
date: 2026-01-04
tags: [tier-config, prompt-engineering, resource-mapping, testing]
---

# Fix Resource Prompt Consistency

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-01-04 |
| **Objective** | Fix inconsistent root-level field mapping in tier configurations and enhance resource prompt suffixes to encourage maximum usage |
| **Outcome** | ✅ Successfully mapped root-level `tools`, `agents`, and `skills` to resources dict; enhanced all prompt messages to use "Maximize usage" wording for multiple items |
| **Files Modified** | `src/scylla/e2e/tier_manager.py`, `tests/unit/e2e/test_tier_manager.py` (new) |
| **Tests Added** | 12 comprehensive unit tests, all passing |

## When to Use This Skill

Use this skill when:

1. **Discovering inconsistent configuration handling** - Some root-level fields are mapped to resources while others aren't
2. **Adding new resource types** - Need to ensure consistent handling across all resource types (tools, skills, MCP servers, agents)
3. **Enhancing prompt engineering** - Want to change wording to encourage specific agent behaviors (e.g., "maximize usage" vs "use")
4. **Configuration schema changes** - Supporting both nested and root-level configuration formats

**Context clues:**
- User asks "is this already implemented?"
- Configuration files use inconsistent patterns (some `mcp_servers:` at root, some under `resources:`)
- Different resource types generate different prompt formats
- Need to handle `enabled: all` configuration format

## Verified Workflow

### Phase 1: Investigate Existing Implementation

1. **Search for existing functionality** using parallel Explore agents:
   ```
   Agent 1: Search for prompt generation code
   Agent 2: Search for tier configuration structure
   ```

2. **Read key implementation files**:
   - `src/scylla/e2e/tier_manager.py` - Focus on `build_resource_suffix()` and `_discover_subtests()`
   - Test fixture configs to understand usage patterns

3. **Identify the gap**:
   - Found: `mcp_servers` at root level WAS being mapped (lines 143-146)
   - Missing: `tools`, `agents`, `skills` at root level NOT mapped
   - Missing: `tools: {enabled: all}` format not handled

### Phase 2: Design the Fix

**Pattern to follow** (from existing `mcp_servers` handling):

```python
# In _discover_subtests() after line 141:
resources = config_data.get("resources", {})

# Map root-level fields into resources
field_name = config_data.get("field_name", default)
if field_name:
    resources["field_name"] = field_name
```

**Two changes needed**:
1. Add root-level mapping for `tools`, `agents`, `skills` (lines 148-161)
2. Enhance `build_resource_suffix()` to handle multiple items and `enabled: all`

### Phase 3: Implementation

**File: `src/scylla/e2e/tier_manager.py`**

**Change 1: Add root-level field mapping** (after line 146):

```python
# Map tools at root level
tools = config_data.get("tools", {})
if tools:
    resources["tools"] = tools

# Map agents at root level
agents = config_data.get("agents", {})
if agents:
    resources["agents"] = agents

# Map skills at root level
skills = config_data.get("skills", {})
if skills:
    resources["skills"] = skills
```

**Change 2: Enhance prompt messages** (lines 463-530):

For each resource type, add count-based logic:

```python
if len(resource_names) > 1:
    prefix = "Maximize usage of the following [type]s to complete this task:"
else:
    prefix = "Use the following [type] to complete this task:"
suffixes.append(f"{prefix}\n{bullet_list}")
```

For `tools: {enabled: all}`:

```python
if tools_spec.get("enabled") == "all":
    suffixes.append("Maximize usage of all available tools to complete this task.")
```

### Phase 4: Add Comprehensive Tests

**File: `tests/unit/e2e/test_tier_manager.py` (new)**

Create two test classes:

1. **`TestBuildResourceSuffix`** - Test prompt generation:
   - `test_tools_enabled_all()` - Verify "Maximize usage of all available tools"
   - `test_tools_with_names()` - Verify multiple tools use "Maximize usage"
   - `test_single_tool()` - Verify single tool uses "Use"
   - `test_mcp_servers()` - Verify MCP server handling
   - `test_single_mcp_server()` - Verify singular handling
   - `test_no_resources()` - Verify fallback message
   - `test_multiple_resource_types()` - Verify combined resources

2. **`TestDiscoverSubtestsRootLevelMapping`** - Test field mapping:
   - `test_root_level_tools_mapped()`
   - `test_root_level_mcp_servers_mapped()`
   - `test_root_level_agents_mapped()`
   - `test_root_level_skills_mapped()`
   - `test_resources_field_takes_precedence()`

**Key testing pattern** (using `tmp_path` fixture):

```python
def test_root_level_tools_mapped(self, tmp_path: Path) -> None:
    # Create tier directory structure
    tier_dir = tmp_path / "t5"
    tier_dir.mkdir()
    subtest_dir = tier_dir / "01-test"
    subtest_dir.mkdir()

    # Write config with root-level tools
    config_file = subtest_dir / "config.yaml"
    config_file.write_text(yaml.safe_dump({
        "name": "Test Tools",
        "tools": {"enabled": "all"}
    }))

    # Discover subtests
    manager = TierManager(tmp_path)
    subtests = manager._discover_subtests(TierID.T5, tier_dir)

    # Verify mapping
    assert "tools" in subtests[0].resources
```

### Phase 5: Verify and Commit

1. **Run tests**:
   ```bash
   pixi run pytest tests/unit/e2e/test_tier_manager.py -v
   ```
   Result: 12 passed

2. **Run full test suite**:
   ```bash
   pixi run pytest tests/unit/e2e/ -v
   ```
   Result: 82 passed

3. **Run pre-commit hooks**:
   ```bash
   pre-commit run --files src/scylla/e2e/tier_manager.py tests/unit/e2e/test_tier_manager.py
   ```
   Result: All checks passed

## Failed Attempts

| Attempt | What We Tried | Why It Failed | Lesson Learned |
|---------|---------------|---------------|----------------|
| **Assumed feature was not implemented** | Started planning to implement the entire feature from scratch | The feature WAS already partially implemented - `mcp_servers` root-level mapping existed, and `build_resource_suffix()` was functional | Always search for existing implementation before assuming nothing exists. Use parallel Explore agents to check both implementation and configuration patterns |
| **Test assumed filesystem structure** | Initial test used `skills: {"categories": ["github"], "names": []}` expecting category lookup to work in `/tmp/tiers` | Test directory doesn't have the shared skills directory structure, so no skills were found and assertion failed | Use explicit skill names in tests: `{"categories": [], "names": ["skill-name"]}` instead of relying on filesystem lookups |

### Failed Test Code

**Code that failed**:
```python
resources={
    "skills": {"categories": ["github"], "names": []},  # ❌ Won't find anything
    "tools": {"enabled": "all"},
}
```

**Working code**:
```python
resources={
    "skills": {"categories": [], "names": ["gh-create-pr-linked"]},  # ✅ Explicit names
    "tools": {"enabled": "all"},
}
```

## Results & Parameters

### Prompt Message Patterns (Copy-Paste Ready)

**For multiple items**:
```python
if len(items) > 1:
    prefix = "Maximize usage of the following [type]s to [action]:"
else:
    prefix = "Use the following [type] to [action]:"
```

**For enabled: all**:
```python
if spec.get("enabled") == "all":
    message = "Maximize usage of all available [type]s to [action]."
```

### Configuration Formats Supported

**Root-level format** (now works):
```yaml
tools:
  enabled: all

mcp_servers:
  - name: filesystem
  - name: git

agents:
  levels: [2, 3]

skills:
  categories: [github, mojo]
```

**Resources format** (always worked):
```yaml
resources:
  tools:
    names: [Read, Write, Bash]
  mcp_servers:
    - filesystem
  agents:
    levels: [2]
  skills:
    names: [gh-create-pr-linked]
```

### Expected Prompt Outputs

| Configuration | Output |
|---------------|--------|
| `tools: {enabled: all}` | "Maximize usage of all available tools to complete this task." |
| `tools: {names: [Read, Write]}` | "Maximize usage of the following tools to complete this task:\n- Read\n- Write" |
| `tools: {names: [Read]}` | "Use the following tool to complete this task:\n- Read" |
| `mcp_servers: [fs, git]` | "Maximize usage of the following MCP servers to complete this task:\n- fs\n- git" |
| No resources | "Complete this task using available tools and your best judgment." |

### Test Coverage Summary

```
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_tools_enabled_all PASSED
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_tools_with_names PASSED
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_mcp_servers PASSED
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_no_resources PASSED
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_single_tool PASSED
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_single_mcp_server PASSED
tests/unit/e2e/test_tier_manager.py::TestBuildResourceSuffix::test_multiple_resource_types PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_tools_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_mcp_servers_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_agents_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_root_level_skills_mapped PASSED
tests/unit/e2e/test_tier_manager.py::TestDiscoverSubtestsRootLevelMapping::test_resources_field_takes_precedence PASSED

12 passed in 0.12s
```

## Key Takeaways

1. **Search before implementing** - Use Task tool with Explore agents to find existing implementations
2. **Follow existing patterns** - When `mcp_servers` mapping existed, copy that pattern for other fields
3. **Test with realistic data** - Don't assume filesystem structures exist in test environments
4. **Singular vs plural matters** - Different wording for single vs multiple items improves clarity
5. **Comprehensive testing pays off** - 12 tests caught edge cases and verified all scenarios

## Related Skills

- `skills-registry-commands:advise` - Search for prior learnings before starting
- Test-first development for configuration changes
- Parallel agent usage for faster exploration
