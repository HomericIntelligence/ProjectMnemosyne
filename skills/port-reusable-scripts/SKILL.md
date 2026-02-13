# Skill: Port Reusable Scripts Between Repositories

## Overview

| Aspect | Details |
|--------|---------|
| **Date** | 2026-02-12 |
| **Objective** | Port 17 reusable scripts from ProjectOdyssey to ProjectScylla across 5 sequential PRs |
| **Outcome** | ✅ All 17 scripts ported successfully. Zero external dependencies added. Scripts work without PYTHONPATH. |
| **Key Achievement** | Eliminated PyGithub dependency by rewriting to use \`gh\` CLI subprocess calls |
| **Time Investment** | ~12.5 hours for complete 17-script migration |

## When to Use This Skill

1. **Cross-Repository Script Migration** - Porting utility scripts between projects
2. **Script Generalization** - Removing domain-specific code, updating to modern standards
3. **Dependency Elimination** - Replacing heavy libraries with CLI tools
4. **Large-Scale Refactoring** - Breaking migrations into sequential, reviewable PRs

## Verified Workflow

### Phase 1: Inventory and Planning

**Filter for reusable scripts** - Exclude:
- Domain-specific (Mojo, ML, etc.)
- Issue-specific fixes
- One-time migrations
- Hardcoded generators

**Organize into categories:**
- Foundation (common utilities, retry, validation)
- Agent management (frontmatter, stats, validation)
- Documentation (markdown fixes, links, READMEs)
- Git/GitHub (changelog, PR merging, statistics)
- Config/Coverage (linting, validation, coverage)

**Plan sequential PRs:**
```
PR 1 (Foundation) → PR 2, 3, 4, 5 (all depend on PR 1)
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
- ✅ Uses existing \`gh auth\`
- ✅ Faster for simple queries
- ✅ More portable

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

## Failed Attempts & Lessons

### ❌ Failed: Scripts required PYTHONPATH

**What happened:** \`ModuleNotFoundError: No module named 'scylla'\`

**Solution:** Add path setup to every script (see Step 6)

### ❌ Failed: Using PyGithub library

**Why failed:**
- Heavy external dependency
- Slower than gh CLI
- Complex authentication

**Solution:** Rewrote to gh CLI subprocess calls

**Metrics:**
- merge_prs.py: ~220 lines (vs ~150 with PyGithub)
- get_stats.py: ~310 lines (vs ~120 with PyGithub)
- Slightly more code but ZERO dependencies

### ❌ Failed: Leaving stubs

**Why failed:**
- Coverage checks always passed (useless)
- False sense of security

**Solution:** Implemented real XML parsing with \`xml.etree.ElementTree\`

### ⚠️ Warning: Pre-commit iterations

**Pattern:** Expect 3-4 fix cycles per PR
- First run: 10-15 errors (D400, D401, E501)
- Second run: 5-7 errors
- Final run: All pass

## Results & Parameters

### Final Statistics

| Metric | Value |
|--------|-------|
| Scripts ported | 17 |
| PRs created | 5 |
| Lines ported | ~4,500 |
| External deps added | 0 |
| PyGithub rewrites | 2 |
| PYTHONPATH fixes | 6 |
| Pre-commit iterations | ~12 total |

### PR Organization

**PR 1 - Foundation** (4 files, ~575 lines)
- scripts/common.py
- scripts/validation.py
- scylla/automation/retry.py
- tests/unit/automation/test_retry.py

**PR 2 - Agent Management** (6 files, ~1,478 lines)
- scripts/agents/*.py (5 scripts)

**PR 3 - Markdown Tools** (3 files, ~855 lines)
- fix_markdown.py, validate_links.py, check_readmes.py

**PR 4 - Git/GitHub Tools** (3 files, ~813 lines)
- generate_changelog.py, merge_prs.py (REWRITTEN), get_stats.py (REWRITTEN)

**PR 5 - Config/Coverage** (3 files, ~1,209 lines)
- lint_configs.py, validate_agents.py, check_coverage.py (real parsing)

### Copy-Paste Checklist

```markdown
## Script Porting Checklist

### Pre-Port
- [ ] Script is reusable (not domain-specific)
- [ ] Provides general utility
- [ ] No heavy dependencies
- [ ] Fits functional category

### Adaptation
- [ ] Remove domain constants/functions
- [ ] Add target-repo content
- [ ] Update type hints to 3.10+
- [ ] Replace libraries with CLI tools
- [ ] Implement stubs
- [ ] Add path setup (noqa: E402)
- [ ] Deduplicate common code

### Quality
- [ ] Works without PYTHONPATH
- [ ] Help output: \`python scripts/x.py --help\`
- [ ] Pre-commit passes
- [ ] Docstrings end with periods
- [ ] Imperative mood
- [ ] Lines < 100 chars
- [ ] __init__ has docstring

### PR
- [ ] Branch: \`port-<category>-tools\`
- [ ] Commit lists scripts, changes
- [ ] PR body includes dependencies
- [ ] PR includes "X/5" indicator
- [ ] Auto-merge enabled
```

### Verification Commands

```bash
# Test without PYTHONPATH
python scripts/check_coverage.py --help
python scripts/lint_configs.py --help
python scripts/agents/validate_agents.py --help

# Run pre-commit
pre-commit run --all-files

# Test functionality
echo "test: value" > /tmp/test.yaml
python scripts/lint_configs.py /tmp/test.yaml -v
```

## Key Takeaways

1. **Sequential PRs > Monolithic** - 5 PRs of 3-6 files beats 1 PR of 17
2. **CLI tools > Libraries** - gh CLI beats PyGithub for portability
3. **Reuse > Duplicate** - Import existing, don't copy
4. **Real > Stub** - Implement actual functionality
5. **Self-contained > Environment** - No PYTHONPATH needed
6. **Generalize > Copy** - Remove domain, add target
7. **Budget iterations** - Expect 3-4 pre-commit cycles
8. **Type hints matter** - Python 3.10+ \`dict\` > \`Dict\`

## Related Skills

- Script generalization patterns
- Dependency elimination strategies
- Python 3.10+ migration
- Pre-commit troubleshooting
- GitHub CLI automation
