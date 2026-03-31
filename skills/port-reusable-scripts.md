---
name: port-reusable-scripts
description: >-
  Port and generalize reusable scripts or full libraries between repositories with
  proper adaptations, dependency elimination, and Python path setup. Covers both
  script-level migrations and full installable package ports. Use when migrating
  utility scripts or libraries from one project to another, deprecating source-repo
  code after a successful port, or resolving CI failures during cross-repo library
  migration.
category: tooling
date: 2026-03-30
version: 1.1.0
user-invocable: false
verification: verified-ci
history: port-reusable-scripts.history
tags: []
---
# Skill: Port Reusable Scripts and Libraries Between Repositories

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-03-30 |
| **Objective** | Port reusable scripts or full libraries between HomericIntelligence repositories using sequential PRs |
| **Outcome** | Proven across two major migrations: 17 scripts (Odyssey to Scylla, 5 PRs) and full `scylla.automation` library (~4,400 lines, 16 modules to Hephaestus, 4 PRs + 1 cleanup PR) |
| **Verification** | verified-ci — all PRs passed full CI (Python 3.10-3.13, lint, mypy, pre-commit) |
| **History** | [changelog](./port-reusable-scripts.history) |

## When to Use

1. **Cross-Repository Script Migration** - Porting utility scripts between projects
2. **Full Library Port** - Migrating an installable Python library to a new home repo
3. **Script Generalization** - Removing domain-specific code, updating to modern standards
4. **Dependency Elimination** - Replacing heavy libraries with CLI tools
5. **Source Repo Cleanup** - Deprecating and removing code after a successful port
6. **Large-Scale Refactoring** - Breaking migrations into sequential, reviewable PRs

## Verified Workflow

### Quick Reference

```bash
# After any pyproject.toml dependency change — always commit pixi.lock too
pixi install   # regenerates pixi.lock
git add pyproject.toml pixi.lock
git commit -m "feat: add <dep> dependency"

# Exclude orchestrator modules from coverage (in pyproject.toml):
# [tool.coverage.run]
# omit = ["*/automation/implementer.py", "*/automation/reviewer.py", ...]

# Source-repo cleanup after all target PRs are CI green:
git rm -r src/old_library/ tests/unit/old_library/
grep -r "old_library" src/ scripts/ tests/   # must return zero matches

# ruff S101-compliant type narrowing:
# if x is None: raise ImportError("message")  -- not: assert x is not None
```

### Phase 1: Inventory and Planning

**Filter for reusable scripts** - Exclude:
- Domain-specific (Mojo, ML, etc.)
- Issue-specific fixes
- One-time migrations
- Hardcoded generators

**For script migrations, organize into categories:**
- Foundation (common utilities, retry, validation)
- Agent management (frontmatter, stats, validation)
- Documentation (markdown fixes, links, READMEs)
- Git/GitHub (changelog, PR merging, statistics)
- Config/Coverage (linting, validation, coverage)

**For full library ports, organize by dependency layer:**

| PR | Layer | Contents |
|----|-------|----------|
| 1 | Foundation | Common utilities, retry, pydantic models, data classes |
| 2 | GitHub/Worktree Layer | Git utilities, GitHub API wrappers, worktree helpers |
| 3 | Orchestration | Subprocess-orchestrating modules (implementer, reviewer, planner) |
| 4 | CLI/Version | Entry points, version bumping, public-facing scripts |
| 5 | Source Cleanup | Remove old library from source repo (only after PR 1-4 CI green) |

**Plan sequential PRs:**
```
PR 1 (Foundation) → PR 2, 3, 4, 5 (each builds on the previous)
```

### Phase 2: Per-Script Adaptation

#### Step 1: Remove Domain-Specific Content

```python
# REMOVE Mojo-specific:
MOJO_KEYWORDS = {...}
def validate_mojo_content(...): ...

# REMOVE ML-specific:
self.deprecated_keys = {"optimizer.type": ...}
self.perf_thresholds = {"batch_size": (1, 1024)}
```

#### Step 2: Add Target-Repo Content

```python
# ADD Scylla evaluation sections:
REQUIRED_SECTIONS = {"Role", "Scope", "Evaluation Focus"}
WORKFLOW_PHASES = ["Plan", "Test", "Implementation", "Review"]

# ADD Scylla labels:
LABEL_COLORS = {"research": "d4c5f9", "evaluation": "1d76db"}
```

#### Step 3: Modernize Type Hints (Python 3.10+)

```python
# OLD:
from typing import Optional, Dict, List
def func(x: Optional[str]) -> Dict[str, List[int]]:

# NEW:
def func(x: str | None) -> dict[str, list[int]]:
```

#### Step 4: **CRITICAL** - Eliminate External Dependencies

**Replace PyGithub with gh CLI subprocess:**

```python
# BEFORE (PyGithub dependency):
from github import Github
g = Github(token)
repo = g.get_repo("owner/repo")
prs = repo.get_pulls(state='open')

# AFTER (gh CLI subprocess):
import subprocess

def get_repo_name() -> str:
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def get_open_prs():
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title"],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)
```

**Benefits:**
- ✅ Zero Python dependencies
- ✅ Uses existing `gh auth`
- ✅ Faster for simple queries
- ✅ More portable

#### Step 4b: **CRITICAL** - Add New Dependencies to pyproject.toml (not just pixi.toml)

If the ported library introduces new dependencies (e.g., pydantic), add them to **both** files:

```toml
# pyproject.toml — read by: pip install -e ".[dev]" in CI
[project]
dependencies = [
    "pydantic>=2.0",
]

# pixi.toml — read by: pixi environments (local dev only)
[dependencies]
pydantic = ">=2.0"
```

Adding a dependency only to `pixi.toml` causes `ModuleNotFoundError` in CI because CI uses
`pip install -e ".[dev]"` which reads `pyproject.toml` only.

**After any pyproject.toml dependency change, regenerate and commit pixi.lock:**
```bash
pixi install   # regenerates pixi.lock
git add pyproject.toml pixi.lock
```

The `check-pixi-lock` pre-commit hook enforces a fresh lock file.

#### Step 4c: Handle API Signature Mismatches with Thin Adapters

When source and target repos have utilities with different signatures, write thin adapter
functions in the new module rather than modifying all callers:

```python
# Source repo: git_utils.run() -> (stdout, stderr, returncode)
# Target repo: run_subprocess() -> CompletedProcess

# Adapter in hephaestus.automation.git_utils:
def run(cmd: list[str], cwd: Path | None = None) -> tuple[str, str, int]:
    """Thin adapter bridging hephaestus run_subprocess to the old scylla signature."""
    result = run_subprocess(cmd, cwd=cwd)
    return result.stdout, result.stderr, result.returncode

# Source repo: detect_rate_limit() -> (bool, int)
# Target repo: detect_rate_limit() -> int | None
def detect_rate_limit(response_text: str) -> tuple[bool, int]:
    """Adapter for callers expecting the old (is_limited, wait_seconds) tuple."""
    wait = _detect_rate_limit_internal(response_text)
    return (wait is not None, wait or 0)
```

#### Step 4d: Exclude Orchestrator Modules from Coverage

Modules that orchestrate subprocess calls (`claude`, `gh` CLI) cannot be unit-tested
meaningfully. Exclude them from coverage measurement rather than forcing artificial tests:

```toml
# pyproject.toml
[tool.coverage.run]
omit = [
    "*/automation/implementer.py",
    "*/automation/reviewer.py",
    "*/automation/pr_manager.py",
    "*/automation/planner.py",
    "*/automation/follow_up.py",
    "*/automation/learn.py",
]
```

#### Step 4e: Fix ruff S101 — Replace assert with ImportError

```python
# BAD — ruff S101 violation in production code:
assert x is not None

# GOOD — type-narrow and ruff-compliant, also satisfies mypy union-attr narrowing:
if x is None:
    raise ImportError("message explaining why x must not be None")
```

#### Step 5: Implement Real Functionality

**Replace stubs with real implementations:**

```python
# BEFORE (stub):
def parse_coverage_report(coverage_file: Path) -> float | None:
    print("Not implemented")
    return None

# AFTER (real XML parsing):
import xml.etree.ElementTree as ET

def parse_coverage_report(coverage_file: Path) -> float | None:
    """Parse Cobertura XML from pytest-cov."""
    if not coverage_file.exists():
        return None
    try:
        tree = ET.parse(coverage_file)
        root = tree.getroot()
        line_rate = root.get("line-rate")
        return float(line_rate) * 100.0 if line_rate else None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None
```

#### Step 6: **CRITICAL** - Fix Python Path Issues

**Add this to EVERY script:**

```python
#!/usr/bin/env python3
"""Script docstring."""

import sys
from pathlib import Path

# Enable importing from repo root and scripts directory
_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_SCRIPT_DIR))

from common import get_repo_root  # noqa: E402
```

**For subdirectories (e.g., scripts/agents/):**

```python
_SCRIPT_DIR = Path(__file__).parent
_SCRIPTS_DIR = _SCRIPT_DIR.parent  # scripts/
_REPO_ROOT = _SCRIPTS_DIR.parent   # repo root
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_SCRIPTS_DIR))
sys.path.insert(0, str(_SCRIPT_DIR))

from agent_utils import extract_frontmatter_parsed  # noqa: E402
from common import get_agents_dir, get_repo_root  # noqa: E402
```

**Why \`# noqa: E402\`:**
- Ruff/flake8 require imports at top
- We MUST modify sys.path before imports
- \`noqa: E402\` suppresses warning (correct pattern)

#### Step 7: Fix Pre-commit Errors

**Common errors:**

```python
# D400: First line should end with period
def main():
    """Run the coverage check script."""  # ✅ ends with period

# D401: Use imperative mood
def main():
    """Run the script."""  # ✅ not "Main entry point"

# E501: Line too long
# BAD:
result.add_error(f"Field '{field}' should be {expected_type.__name__}, got {type(value).__name__}")

# GOOD:
expected = expected_type.__name__
actual = type(value).__name__
result.add_error(f"Field '{field}' should be {expected}, got {actual}")

# D107: Missing __init__ docstring
def __init__(self, file_path: Path) -> None:
    """Initialize validation result.

    Args:
        file_path: Path being validated
    """
```

#### Step 8: Deduplicate Common Code

```python
# BAD - duplicate implementation:
def get_repo_root() -> Path:
    # ... duplicate code ...

# GOOD - reuse existing:
from scylla.automation.git_utils import get_repo_root
```

### Phase 3: Sequential PR Creation

```bash
# 1. Create feature branch
git checkout -b port-<category>-tools

# 2. Make changes, run pre-commit
pre-commit run --all-files

# 3. Commit with detailed message
git commit -m "feat(scripts): add <category> tools (PR X/5)

Port <category> tools from ProjectOdyssey:
- scripts/file1.py: Description (~NNN lines)
- scripts/file2.py: Description (~NNN lines)

Key changes:
- Removed domain-specific content
- Added target-repo specifics
- All pre-commit hooks pass
- Works without PYTHONPATH

Depends on PR #XXX"

# 4. Push and create PR
git push -u origin port-<category>-tools
gh pr create --title "feat(scripts): add <category> tools (PR X/5)" \
  --body "..." --label tooling

# 5. Enable auto-merge
gh pr merge --auto --rebase
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| pydantic only in pixi.toml | Added pydantic to pixi.toml but not pyproject.toml | CI uses `pip install -e ".[dev]"` which reads pyproject.toml only; `ModuleNotFoundError: No module named 'pydantic'` in all matrix jobs | Always add dependencies to `[project.dependencies]` in pyproject.toml; pixi.toml is local-only |
| Coverage without omit list | Tried to get full coverage including orchestrator modules | Orchestrators shell out to `claude`, `gh` — no meaningful unit test possible without full integration environment | Exclude orchestrator modules via `[tool.coverage.run] omit` in pyproject.toml |
| Force-push to stale branch | Force-pushed to a years-old stale branch after rebasing | Only CodeQL triggered, not the full test suite (pytest, mypy, lint) | Rebase onto fresh main and push again to trigger complete CI matrix |
| assert for type narrowing | Used `assert x is not None` in production code | ruff S101 bans assert statements in non-test files | Use `if x is None: raise ImportError(...)` — ruff-compliant and mypy-friendly |
| Scripts required PYTHONPATH | Imported modules without path setup | `ModuleNotFoundError` when running scripts directly outside pixi | Add `sys.path.insert` setup at top of every script with `# noqa: E402` |
| Using PyGithub library | Added PyGithub as a Python dependency | Heavy external dependency, complex auth, slower than gh CLI; merge_prs.py ~150 lines became ~220 but zero deps | Rewrite to `gh` CLI subprocess calls — slightly more code but zero dependencies |
| Leaving stubs unimplemented | Left placeholder functions returning None | Coverage checks always passed (useless), false sense of security | Implement real functionality (e.g., XML parsing with `xml.etree.ElementTree`) |
| Single monolithic PR | Attempted to port all 17 scripts in one PR | Massive diff, hard to review, CI failures hard to isolate | Break into 4-5 sequential PRs by dependency layer |

**Pre-commit iteration budget:** Expect 3-4 fix cycles per PR (first run: 10-15 errors; final run: all pass).

## Results & Parameters

### Migration Statistics

| Session | Source | Target | Lines | Modules/Scripts | PRs | CI Result |
|---------|--------|--------|-------|-----------------|-----|-----------|
| 2026-02-12 | ProjectOdyssey scripts | ProjectScylla scripts | ~4,500 | 17 scripts | 5 | green |
| 2026-03-30 | scylla.automation library | hephaestus.automation | ~4,400 | 16 modules | 4 + 1 cleanup | green (Python 3.10-3.13) |

### Sequential PR Layer Template (Full Library Port)

```
PR 1 (Foundation):       pydantic models, retry, data classes, base utilities
PR 2 (GitHub Layer):     git_utils, github_api, worktree helpers — depends on PR 1
PR 3 (Orchestration):    implementer, reviewer, planner, pr_manager — depends on PR 2
PR 4 (CLI/Version):      entry points, version bumping, public scripts — depends on PR 3
PR 5 (Source Cleanup):   remove old library from origin repo — only after PR 1-4 CI green
```

### Coverage Omit Pattern for Orchestrator Modules

```toml
# pyproject.toml
[tool.coverage.run]
omit = [
    "*/automation/implementer.py",
    "*/automation/reviewer.py",
    "*/automation/pr_manager.py",
    "*/automation/planner.py",
    "*/automation/follow_up.py",
    "*/automation/learn.py",
]
```

### Copy-Paste Checklist

```markdown
## Script/Library Port Checklist

### Pre-Port
- [ ] Target content is reusable (not domain-specific)
- [ ] Sequential PR layers planned (bottom-up dependency order)

### Per-PR (Library Port)
- [ ] New deps in pyproject.toml [project.dependencies] (not just pixi.toml)
- [ ] pixi install run to regenerate pixi.lock
- [ ] pixi.lock committed alongside pyproject.toml
- [ ] Orchestrator modules added to [tool.coverage.run] omit
- [ ] API adapters written for signature mismatches
- [ ] assert replaced with raise ImportError pattern (ruff S101)
- [ ] pre-commit passes (all hooks, not just formatting)
- [ ] PR rebased on fresh main before pushing

### Per-Script (Script Migration)
- [ ] Remove domain constants/functions
- [ ] Update type hints to Python 3.10+ (dict, list, str | None)
- [ ] Replace libraries with CLI tools (gh vs PyGithub)
- [ ] Implement stubs (no placeholders returning None)
- [ ] Add path setup (sys.path.insert + # noqa: E402)
- [ ] Deduplicate common code via imports

### Source Cleanup (Final PR)
- [ ] All target PRs merged, CI green on all Python versions
- [ ] Non-automation imports in source repo updated
- [ ] Backwards-compatible wrapper scripts created
- [ ] New package added to source pyproject.toml dependencies
- [ ] git rm -r old library directory (source + tests)
- [ ] grep confirms zero remaining references
```

### Verification Commands

```bash
# Test without PYTHONPATH
python scripts/check_coverage.py --help
python scripts/lint_configs.py --help

# Run pre-commit
pre-commit run --all-files

# Verify no stale references after source cleanup
grep -r "scylla.automation" src/ scripts/ tests/

# After pyproject.toml change, verify pixi.lock is fresh
pixi install
git status pixi.lock  # should show modified
```

## Key Takeaways

1. **Sequential PRs > Monolithic** - 4-5 PRs by layer beats 1 PR of 16 modules
2. **pyproject.toml is king** - CI reads it; pixi.toml is local-only
3. **pixi.lock must travel with pyproject.toml** - always commit them together
4. **Orchestrators cannot be unit tested** - add to coverage omit list
5. **CLI tools > Libraries** - gh CLI beats PyGithub for portability
6. **Adapters bridge signatures** - thin wrappers avoid cascading caller changes
7. **assert is banned in production** - use `if x is None: raise ImportError(...)` (ruff S101)
8. **Stale branches hide CI** - rebase onto fresh main to trigger full matrix
9. **Budget iterations** - expect 3-4 pre-commit cycles per PR
10. **Type hints matter** - Python 3.10+ `dict` > `Dict`, `str | None` > `Optional[str]`

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Port 17 scripts from ProjectOdyssey (PRs #1-5) | 2026-02-12 session |
| ProjectHephaestus | Port scylla.automation library (PRs #209-212, cleanup PR #1742) | 2026-03-30 session |
