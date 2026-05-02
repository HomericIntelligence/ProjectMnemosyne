---
name: agent-coverage-check
description: Check agent configuration coverage across hierarchy levels and phases.
  Use to ensure complete agent system coverage.
category: architecture
date: '2026-03-19'
version: 1.0.0
mcp_fallback: none
---
# Agent Coverage Check

## Overview

| Item | Details |
|------|---------|
| Date | N/A |
| Objective | Verify complete agent system coverage across all dimensions. - After adding new agents to system - Validating agent system completeness |
| Outcome | Operational |

Verify complete agent system coverage across all dimensions.

## When to Use

- After adding new agents to system
- Validating agent system completeness
- Finding gaps in coverage
- Ensuring all development phases covered

## Verified Workflow

### Quick Reference

```bash
# Check all coverage dimensions
./scripts/check_agent_coverage.sh

# Check specific dimension
./scripts/check_level_coverage.sh
./scripts/check_phase_coverage.sh
./scripts/check_section_coverage.sh
```

## Coverage Dimensions

**Hierarchy Levels**:

- L0: Chief Architect (1)
- L1: Section Orchestrators (6)
- L2: Design Agents (per section)
- L3: Specialists (per module)
- L4: Engineers
- L5: Junior Engineers

**Development Phases**:

- Plan
- Test
- Implementation
- Package
- Cleanup

**Sections**:

- Foundation
- Shared Library
- Tooling
- First Paper
- CI/CD
- Agentic Workflows

## Coverage Report Format

```text
Hierarchy Coverage:
  L0: ✅ 1 agent
  L1: ✅ 6 agents
  L2: ✅ 12 agents
  L3: ✅ 24 agents
  L4: ✅ 3 agents
  L5: ✅ 1 agent

Phases:
  Plan: ✅ Covered
  Test: ✅ Covered
  Implementation: ✅ Covered
  Package: ✅ Covered
  Cleanup: ✅ Covered

Sections:
  Foundation: ✅ Orchestrator + agents
  Shared Library: ✅ Orchestrator + agents
```

## Gap Patterns

**Missing level**: Any level with 0 agents

**Missing phase**: Phase not assigned to any agent

**Missing section**: Section without orchestrator

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

N/A — this skill describes a workflow pattern.

## References

- `agent-validate-config` - Validate individual agent configs
- `agent-test-delegation` - Test delegation completeness
- `.claude/agents/` - All agent configurations
