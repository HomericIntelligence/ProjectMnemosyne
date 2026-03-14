# scripts-coverage-bare-import-resolution — Raw Notes

## Session Context

- Project: ProjectScylla (AI agent benchmarking framework)
- Date: 2026-03-13
- PR: HomericIntelligence/ProjectScylla#1479
- Branch: `quality-audit-fixes`

## Problem Statement

A codebase quality audit identified 5 scripts at 0% test coverage. These scripts
all use `sys.path.insert()` at module level to enable bare imports like
`from agent_utils import ...` and `from common import ...`. When pytest imports
them as package modules (`agents.check_frontmatter`), the bare imports fail
because `scripts/agents/` is not in pytest's pythonpath.

## Scripts Targeted

1. `scripts/agents/agent_stats.py` — AgentAnalyzer class with load/analyze/format
2. `scripts/agents/check_frontmatter.py` — YAML frontmatter validation
3. `scripts/agents/list_agents.py` — Agent listing with group_by_level
4. `scripts/agents/test_agent_loading.py` — Agent discovery and duplicate checking
5. `scripts/generate_figures.py` — FIGURES registry dict with 34 figure generators

## Key Discovery: validate_agents.py already works

`scripts/agents/validate_agents.py` adds THREE paths to sys.path:
```python
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_SCRIPT_DIR))  # <-- scripts/agents/
```

The other scripts only add `parent.parent` (scripts/) but NOT `parent` (scripts/agents/).
That's why `from agent_utils import ...` works at runtime (sys.path.insert runs) but
fails under pytest (conftest hasn't added the path yet).

## Double-Import Module Identity Issue

Python treats `agents.agent_utils.AgentInfo` and `agent_utils.AgentInfo` as different
classes even though they're the same file. This is because Python's import system
caches modules by their fully-qualified name. When imported via two paths, you get
two entries in `sys.modules` and two separate class objects.

Symptom: `isinstance(result, AgentInfo)` returns False even though `repr()` shows
`AgentInfo(level=3, name=test-agent)`.

## check_frontmatter.py Bug Found (Not Fixed)

`validate_frontmatter()` checks name format with `re.match()` even when the type
check already failed. If `name` is an int, `re.match(r"^[a-z]...", 123)` raises
`TypeError: expected string or bytes-like object, got 'int'`. The function should
skip format validation when the type is wrong. Not fixed — out of scope.
