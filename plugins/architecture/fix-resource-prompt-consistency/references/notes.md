# Raw Session Notes: Fix Resource Prompt Consistency

## Session Date
2026-01-04

## Initial Request
User asked to investigate if tier-specific prompts tell the agent which tools/skills/MCPs to use, and if not, implement it.

## Discovery Phase

### What We Found
1. **Feature WAS already implemented** in `TierManager.build_resource_suffix()`
2. **Partial inconsistency**: `mcp_servers` at root level was being mapped, but `tools`, `agents`, `skills` were not
3. **Missing feature**: `tools: {enabled: all}` format wasn't handled

### Key Files Examined
- `/home/mvillmow/ProjectScylla/src/scylla/e2e/tier_manager.py:428-501` - `build_resource_suffix()` method
- `/home/mvillmow/ProjectScylla/src/scylla/e2e/tier_manager.py:143-146` - Existing `mcp_servers` mapping
- `/home/mvillmow/ProjectScylla/tests/fixtures/tests/test-001/t1/04-github/config.yaml` - Skills config example
- `/home/mvillmow/ProjectScylla/tests/fixtures/tests/test-001/t2/14-all-mcp/config.yaml` - MCP config example

## Implementation Details

### Change 1: Root-Level Field Mapping
**Location**: `src/scylla/e2e/tier_manager.py:148-161`

Pattern copied from existing `mcp_servers` handling:
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

### Change 2: Enhanced Prompt Messages
**Location**: `src/scylla/e2e/tier_manager.py:463-530`

Added count-based logic for all resource types:
- Multiple items: "Maximize usage of the following [type]s..."
- Single item: "Use the following [type]..." (singular)
- All enabled: "Maximize usage of all available [type]s..."

## Testing Strategy

### Test File Created
`/home/mvillmow/ProjectScylla/tests/unit/e2e/test_tier_manager.py`

### Test Classes
1. **TestBuildResourceSuffix** (7 tests)
   - test_tools_enabled_all
   - test_tools_with_names
   - test_mcp_servers
   - test_no_resources
   - test_single_tool
   - test_single_mcp_server
   - test_multiple_resource_types

2. **TestDiscoverSubtestsRootLevelMapping** (5 tests)
   - test_root_level_tools_mapped
   - test_root_level_mcp_servers_mapped
   - test_root_level_agents_mapped
   - test_root_level_skills_mapped
   - test_resources_field_takes_precedence

### Test Results
- Initial run: 9/10 passed (1 failure in test_multiple_resource_types)
- After fix: 10/10 passed
- After adding singular tests: 12/12 passed
- Full E2E suite: 82/82 passed

### Test Failure Analysis

**Failed Test**: `test_multiple_resource_types`

**Error**:
```
AssertionError: assert ('skills' in result.lower() or 'following skills' in result.lower())
```

**Root Cause**: Test used `skills: {"categories": ["github"], "names": []}` expecting filesystem lookup to work, but TierManager was initialized with `/tmp/tiers` which doesn't have the shared skills directory.

**Fix**: Changed to explicit skill names: `{"categories": [], "names": ["gh-create-pr-linked"]}`

## Pre-commit Hook Setup

Enabled pre-commit hooks to run automatically on commits:
```bash
pre-commit install
```

This ensures:
- Ruff linting runs on all commits
- Code formatting is enforced
- No need to manually run pre-commit before committing

## Configuration Examples

### Root-Level Format (Now Works)
```yaml
name: "All Tools"
description: "All built-in tools enabled"
tools:
  enabled: all
```

```yaml
name: "GitHub Skills"
description: "10 skills from the github category"
resources:
  skills:
    categories:
    - github
```

```yaml
name: "Filesystem MCP"
description: "Secure file operations"
mcp_servers:
  - name: filesystem
    source: modelcontextprotocol/servers
```

### Generated Prompts

**Example 1**: `tools: {enabled: all}`
```
Maximize usage of all available tools to complete this task.
```

**Example 2**: `tools: {names: [Read, Write, Bash]}`
```
Maximize usage of the following tools to complete this task:
- Bash
- Read
- Write
```

**Example 3**: `mcp_servers: [filesystem]` (single)
```
Use the following MCP server to complete this task:
- filesystem
```

**Example 4**: No resources
```
Complete this task using available tools and your best judgment.
```

## PR Information

**Branch**: `fix/resource-prompt-suffix-consistency`
**PR Number**: #127
**URL**: https://github.com/HomericIntelligence/ProjectScylla/pull/127

**Files Changed**:
- `src/scylla/e2e/tier_manager.py` (+57, -11)
- `tests/unit/e2e/test_tier_manager.py` (+268, new file)

**Commit Message**:
```
fix(e2e): enhance resource prompt suffixes with maximize usage wording

- Map root-level tools/agents/skills fields to resources (matching existing mcp_servers behavior)
- Update prompt messages to use "Maximize usage" for multiple resources
- Handle tools: {enabled: all} configuration with "Maximize usage of all available tools"
- Keep singular "Use" wording for single-item lists
- Add comprehensive unit tests (12 tests, all passing)

This ensures consistent behavior across all resource types and provides
clearer instructions to agents about utilizing available resources.
```

## Agent Usage

### Explore Agents Used (Phase 1)
1. **Agent 1**: Explored test prompt generation (ac589b0)
   - Found `build_resource_suffix()` method
   - Identified existing functionality

2. **Agent 2**: Explored tier config structure (a49bf6b)
   - Found tier definition files
   - Identified gap in configuration support

### Benefits of Using Agents
- Parallel exploration saved time
- Comprehensive codebase understanding before implementation
- Avoided reimplementing existing features

## Timeline

1. User request: "Update prompts so tool-specific prompts are added"
2. Discovery: Feature already exists but incomplete
3. User clarification: Fix the gaps
4. Implementation: ~30 minutes
5. Testing: 12 tests created, all passing
6. PR creation: Automated workflow
7. Retrospective: This skill creation

## Lessons Learned

1. **Always search first**: Use `/advise` or Explore agents before assuming nothing exists
2. **Follow existing patterns**: `mcp_servers` mapping showed the way
3. **Test realistically**: Don't assume filesystem structures in unit tests
4. **Singular matters**: Different wording for 1 vs many improves clarity
5. **Comprehensive testing**: Edge cases are important (single item, enabled: all, multiple types)
6. **Pre-commit hooks**: Enable them early to avoid formatting issues in commits
