---
name: cross-repo-script-and-library-porting
description: >-
  Systematic patterns for porting scripts, utilities, and libraries between repositories. Use when:
  (1) migrating utility scripts or full libraries from one project to another with dependency
  elimination and CI validation, (2) diff-analyzing two repos' diverged implementations to
  cherry-pick missing features without downgrading the destination, (3) porting skills from
  upstream OSS repos (Modular Apache 2.0, third-party MIT, or Agent Skills Standard format) with
  attribution, (4) installing and adapting external skills into a local Codex environment, or
  (5) creating re-export shims in the source repo after a successful port.
category: tooling
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: cross-repo-script-and-library-porting.history
tags:
  - porting
  - cross-repo
  - python
  - re-export
  - shim
  - apache-2.0
  - mit-license
  - modular-upstream
  - agent-skills-standard
  - codex
  - sequential-prs
  - dependency-elimination
---

# Skill: Cross-Repo Script and Library Porting

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-19 |
| **Objective** | Systematic patterns for porting scripts, utilities, and libraries across repositories: diff analysis, cherry-pick decisions, dependency elimination, re-export shims, and CI validation |
| **Outcome** | Consolidated from 5 skills covering Python library migration, feature diff porting, upstream OSS integration (Apache 2.0 / MIT), and Codex skill installation |
| **Verification** | verified-ci across multiple sessions (Python 3.10–3.13, lint, mypy, pre-commit) |
| **History** | [changelog](./cross-repo-script-and-library-porting.history) |

## When to Use

1. **Cross-Repo Script Migration** — Porting utility scripts between projects (filter, adapt, CI-validate)
2. **Full Library Port** — Migrating an installable Python library (sequential PRs by dependency layer)
3. **Feature Diff Port** — Two repos have diverged implementations; cherry-pick only what destination lacks
4. **Dependency Elimination** — Replacing heavy libraries with CLI tools (PyGithub → `gh` CLI subprocess)
5. **Source Repo Cleanup** — Deprecating and removing code after a successful port via re-export shims
6. **Upstream OSS Skill Porting** — Integrating skills from Modular (Apache 2.0) or third-party repos (MIT)
7. **Codex External Skill Installation** — Importing GitHub-hosted skills into `~/.codex/skills` with metadata
8. **Large-Scale Refactoring** — Breaking migrations into sequential, reviewable PRs (4–5 PRs by layer)
9. **Single-PR from Staging Copy** — Complete module in a staging location that never reached the target repo

## Verified Workflow

### Quick Reference

```bash
# --- Python Library / Script Migration ---

# Pre-port audit: always check what already exists in target repo
grep -A 30 '\[project.scripts\]' pyproject.toml
ls <project-root>/<target-module>/
grep -r "function_name_to_port" <project-root>/

# After any pyproject.toml dependency change — commit pixi.lock too
pixi install   # regenerates pixi.lock
git add pyproject.toml pixi.lock
git commit -m "feat: add <dep> dependency"

# Source-repo cleanup after all target PRs are CI green
git rm -r src/old_library/ tests/unit/old_library/
grep -r "old_library" src/ scripts/ tests/   # must return zero matches

# ruff S101-compliant type narrowing
# if x is None: raise ImportError("message")  -- not: assert x is not None

# --- Upstream Skill Porting ---

# Clone and audit source repo
gh repo clone <org>/<repo> /tmp/source-repo
ls /tmp/source-repo/  # check for SKILL.md, hooks/, agents/, .claude-plugin/

# Overlap analysis before porting
grep -rl "topic_keyword" <project-root>/skills/

# Validate after porting
python3 scripts/validate_plugins.py

# --- Codex Skill Installation ---

python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <org>/<repo> \
  --path skills/<skill-a> skills/<skill-b> \
  --dest ~/.codex/skills

python3 ~/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py \
  ~/.codex/skills/<skill> --name <skill> \
  --interface display_name='<Name>' \
  --interface short_description='<desc>' \
  --interface default_prompt='<prompt>'
```

---

### Part A: Python Script and Library Migration

#### Phase 0: CRITICAL — Pre-Port Audit of Target Repo

Before writing a single line of code, audit the target repository to prevent duplicate work:

```bash
# 1. Check existing CLI entry points
grep -A 30 '\[project.scripts\]' pyproject.toml

# 2. Check existing modules
ls <project-root>/<target-module>/

# 3. Search for function names you plan to port
grep -r "validate_readme\|extract_version_from_pyproject" <project-root>/

# 4. Check existing test coverage
ls tests/unit/<target-module>/
```

**Extend, don't duplicate:** Add only the missing delta to existing modules.

**Pre-Port Audit Checklist:**

```markdown
- [ ] Checked pyproject.toml [project.scripts] for existing entry points
- [ ] Checked ls <project-root>/<target-module>/ for existing functions
- [ ] Grepped for function names before porting
- [ ] Verified test coverage of existing functions (don't re-test what's covered)
```

#### Phase 1: Inventory and Planning

Filter for reusable scripts — exclude domain-specific, issue-specific, one-time migrations, and hardcoded generators.

**For full library ports, organize by dependency layer:**

| PR | Layer | Contents |
| ---- | ------- | ---------- |
| 1 | Foundation | Common utilities, retry, pydantic models, data classes |
| 2 | GitHub/Worktree Layer | Git utilities, GitHub API wrappers, worktree helpers |
| 3 | Orchestration | Subprocess-orchestrating modules (implementer, reviewer, planner) |
| 4 | CLI/Version | Entry points, version bumping, public-facing scripts |
| 5 | Source Cleanup | Remove old library from source repo (only after PR 1–4 CI green) |

**When target modules are independent (no shared files), use 6 parallel agents in a single wave:**

```
Wave 1 (all parallel, isolated worktrees):
├── PR A: git/changelog.py — extend with changelog_has_version() + extract_version_from_pyproject()
├── PR B: validation/tier_labels.py — new module + CLI
├── PR C: markdown/fixer.py — extend with new rules
├── PR D: validation/markdown.py — extend with validate_readme()
├── PR E: validation/doc_policy.py — new module + CLI
└── PR F: resilience/ — new subpackage

Wave 2 (after all Wave 1 merge):
└── Source-repo PR: thin wrappers replacing scripts with re-export shims
```

**Prerequisite for parallel agents:** Each PR must touch DIFFERENT files. If any two agents need to modify `pyproject.toml` simultaneously, serialize them.

#### Phase 2: Per-Script Adaptation

**Step 1: Remove Domain-Specific Content** — Strip Mojo-specific, ML-specific, or other domain constants and functions.

**Step 2: Modernize Type Hints (Python 3.10+):**

```python
# OLD:
from typing import Optional, Dict, List
def func(x: Optional[str]) -> Dict[str, List[int]]: ...

# NEW:
def func(x: str | None) -> dict[str, list[int]]: ...
```

**Step 3: CRITICAL — Eliminate External Dependencies:**

```python
# BEFORE (PyGithub dependency):
from github import Github
g = Github(token)
prs = g.get_repo("owner/repo").get_pulls(state='open')

# AFTER (gh CLI subprocess — zero deps, uses existing auth):
import subprocess, json

def get_open_prs() -> list:
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title"],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout)
```

**Step 4: Add New Dependencies to pyproject.toml (not just pixi.toml):**

```toml
# pyproject.toml — read by CI (pip install -e ".[dev]")
[project]
dependencies = ["pydantic>=2.0"]

# pixi.toml — local dev only
[dependencies]
pydantic = ">=2.0"
```

Adding a dependency only to `pixi.toml` causes `ModuleNotFoundError` in CI.

**Step 5: Handle API Signature Mismatches with Thin Adapters:**

```python
# Source repo: git_utils.run() -> (stdout, stderr, returncode)
# Target repo: run_subprocess() -> CompletedProcess
def run(cmd: list[str], cwd: Path | None = None) -> tuple[str, str, int]:
    """Thin adapter bridging signatures."""
    result = run_subprocess(cmd, cwd=cwd)
    return result.stdout, result.stderr, result.returncode
```

**Step 6: Exclude Orchestrator Modules from Coverage:**

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

**Step 7: Fix ruff S101 — Replace assert with ImportError:**

```python
# BAD — ruff S101 violation in production code:
assert x is not None

# GOOD — ruff-compliant, also satisfies mypy union-attr narrowing:
if x is None:
    raise ImportError("message explaining why x must not be None")
```

**Step 8: Add mypy Overrides for tests/ and scripts/:**

```toml
[tool.mypy]
explicit_package_bases = true

[[tool.mypy.overrides]]
module = ["tests.*", "scripts.*"]
disallow_untyped_defs = false
disallow_incomplete_defs = false
disallow_any_generics = false
warn_return_any = false
check_untyped_defs = false
```

**Step 9: CRITICAL — Fix Python Path Issues:**

```python
#!/usr/bin/env python3
"""Script docstring."""
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
_REPO_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_SCRIPT_DIR))

from common import get_repo_root  # noqa: E402
```

**Step 10: Implement Real Functionality — never leave stub functions returning `None`.**

#### Phase 3: Sequential PR Creation

```bash
# 1. Create feature branch
git checkout -b port-<category>-tools

# 2. Make changes, run pre-commit
pre-commit run --all-files

# 3. Commit with detailed message
git commit -m "feat(scripts): add <category> tools (PR X/5)"

# 4. Push and create PR
git push -u origin port-<category>-tools
gh pr create --title "feat(scripts): add <category> tools (PR X/5)" --label tooling

# 5. Enable auto-merge
gh pr merge --auto --rebase
```

#### Phase 3b: Backwards-Compatible Thin Wrappers with Symbol Re-exports

When the source repo has tests that import internal symbols directly from scripts, re-export all symbols:

```python
#!/usr/bin/env python3
"""Thin wrapper. Delegates to <package>.<module>."""
from package.module import (  # noqa: F401
    Finding, Severity, scan_file, scan_repository, format_text_report
)
from package.module import main
import sys
if __name__ == "__main__":
    sys.exit(main())
```

#### Phase 3c: Cross-Repo PR Dependency Ordering

1. Create all target-repo (Hephaestus) PRs first and enable auto-merge
2. Wait for at least one target PR to merge before creating source-repo wrapper PRs
3. Mention the dependency in the source-repo PR description

#### Model Tier Selection

| Task | Model |
| ------ | ------- |
| "Add these 3 functions to an existing file" (fully specified) | Haiku |
| "Read existing file, identify what's missing, implement the delta" | Sonnet |

---

### Part B: Feature Diff Porting (Two Diverged Implementations)

#### Phase 1 — Side-by-Side Feature Analysis

Read both files completely. Build a feature matrix:

| Feature | Source | Destination | Action |
| --------- | -------- | ------------- | -------- |
| Core state machine | ✓ | ✓ | Skip (exists) |
| `success_threshold` | ✓ | ✗ | **Port** |
| `half_open_max_calls` | ✗ | ✓ | Skip (dest is better) |
| Global registry | ✗ | ✓ | Skip |
| Logging | ✗ | ✓ | Skip |

**Rule:** Port features the source has that the destination lacks. Never downgrade the destination to match a weaker source.

#### Phase 2 — Implement in Destination (Backward-Compatible)

Add parameters as backward-compatible additions with defaults matching old behavior:

```python
def __init__(
    self,
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    half_open_max_calls: int = 1,
    success_threshold: int = 1,   # NEW — default 1 = old behavior
) -> None:
```

#### Phase 3 — Merge Test Suites

Don't duplicate tests already in the destination. Add only tests for new features, time-mocking tests, and parametrized threshold configs.

#### Phase 4 — File Cleanup Issue in Source Repo

```bash
gh issue create \
  --repo <source-org>/<source-repo> \
  --title "cleanup: replace <path> with re-export from <dest-package>" \
  --body "## Objective
Replace source file with re-export shim once destination PR merges.
## Dependencies
- <dest-repo> branch <name> must merge first"
```

Re-export shim pattern:

```python
"""<description> — re-exports from <package>.<module>."""
from package.module import ClassA, ClassB, EnumC, func_d, func_e

__all__ = ["ClassA", "ClassB", "EnumC", "func_d", "func_e"]
```

---

### Part C: Upstream OSS Skill Porting (Modular / Third-Party Plugins)

#### 1. Audit and Overlap Analysis

```bash
gh repo clone <org>/<repo> /tmp/source-repo
# Check for SKILL.md files, hooks/hooks.json (conflict risk), hardcoded paths
grep -rl "topic_keyword" <project-root>/skills/
```

**Decision matrix:**

| Scenario | Action |
| ---------- | -------- |
| Upstream covers same topic as existing skill | Merge into existing skill, bump version |
| Upstream covers new topic | Create new skill |
| Upstream is subset of existing | Skip |

**Integration approach:**

| Approach | When | Risk |
| ---------- | ------ | ------ |
| Install as separate plugin | No overlap AND no hook conflicts | SessionStart hook conflicts |
| Fork/vendor | Need all skills AND can maintain | High — ongoing sync burden |
| Port select skills | Only need subset, source has hardcoded conventions | Low |

#### 2. Format Adaptation Checklist (Agent Skills Standard → Mnemosyne)

| Feature | Agent Skills Standard | Mnemosyne Format |
| --------- | ---------------------- | ------------------ |
| Structure | Directory per skill (`skill-name/SKILL.md`) | Flat file (`skills/skill-name.md`) |
| Frontmatter | `name` and `description` only | Full: `name`, `description`, `category`, `date`, `version`, `verification`, `tags` |
| Sections | Free-form markdown | Structured: Overview, When to Use, Verified Workflow, Failed Attempts, Results |

**Do NOT use `npx skills add`** — installs in Agent Skills Standard format, incompatible with Mnemosyne validator.

Adaptation checklist:

```markdown
[ ] Add full Mnemosyne YAML frontmatter (category, date, version, verification, tags)
[ ] Add traceability tag (e.g., modular-upstream, superpowers-port)
[ ] Restructure into required sections
[ ] For Failed Attempts on upstream-sourced skills with no local experimentation: "(none — sourced from upstream)"
[ ] Add attribution footer on each ported file
[ ] Cross-reference related existing skills
[ ] If merging into existing skill: preserve all existing Failed Attempts and battle-tested content
[ ] Validate: python3 scripts/validate_plugins.py
```

#### 3. Attribution Footers

Apache 2.0 (Modular):

```markdown
---
*Adapted from [modular/skills](https://github.com/modular/skills) under Apache License 2.0.
Copyright (c) Modular Inc.*
```

MIT (third-party, e.g., obra/superpowers):

```markdown
---
*Adapted from [obra/superpowers](https://github.com/obra/superpowers) under MIT License.
Copyright (c) 2025 Jesse Vincent.*
```

Place `THIRD_PARTY_LICENSES.md` at **repo root** — NOT in `skills/` (validator rejects files without frontmatter there).

#### 4. Merge Strategy for Overlapping Skills

1. Keep all existing content intact (especially Failed Attempts — battle-tested)
2. Add upstream content as a clearly labeled new section
3. Bump the version (minor for additive content, major for restructuring)
4. Add the traceability tag to the existing skill's tag list

**Version bump guide:**

| Change size | Version bump |
| --- | --- |
| 1–3 new skills | Minor (2.0.0 → 2.1.0) |
| 4+ new skills or restructuring | Major (2.0.0 → 3.0.0) |
| Bug fixes or attribution only | Patch (2.0.0 → 2.0.1) |

#### 5. Meta-Skill vs SessionStart Hook

Convert SessionStart hook-injected advisors to manually-invoked meta-skills to avoid hook conflicts:

```markdown
## Automatic Skill Selection

Before beginning any substantive task, invoke /skill-advisor with a brief task description.
```

---

### Part D: Codex External Skill Installation

#### Steps

1. **Install skill folders from GitHub:**

   ```bash
   python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
     --repo <org>/<repo> \
     --path skills/<skill-a> skills/<skill-b> \
     --dest ~/.codex/skills
   ```

2. **Generate Codex UI metadata** (pass `--name` to bypass frontmatter parsing if PyYAML is absent):

   ```bash
   python3 ~/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py \
     ~/.codex/skills/<skill> --name <skill> \
     --interface display_name='<Name>' \
     --interface short_description='<short desc>' \
     --interface default_prompt='<default prompt>'
   ```

   Normalize each generated file:

   ```yaml
   policy:
     allow_implicit_invocation: true
   ```

3. **Patch Claude-centric skills for Codex:**
   - `$ARGUMENTS` → "triggering request text"
   - Mandatory sub-agent delegation → optional unless user explicitly requests it
   - `gh repo clone ...` → `git clone ... \|\| gh repo clone ...`

4. **Seed supporting repos and caches:**

   ```bash
   mkdir -p ~/.agent-brain
   if [ ! -d ~/.agent-brain/Mnemosyne/.git ]; then
     git clone --depth 1 https://github.com/HomericIntelligence/Mnemosyne ~/.agent-brain/Mnemosyne
   else
     git -C ~/.agent-brain/Mnemosyne pull --ff-only origin main
   fi
   ```

5. **Advertise skills in the target repo's `AGENTS.md`:**

   ```markdown
   ## Recommended ProjectHephaestus flow
   - Use `$advise` before unfamiliar implementation or debugging
   - Use `$repo-analyze-quick` for a fast health check
   - Use `$learn` after finishing meaningful work
   ```

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| pydantic only in pixi.toml | Added pydantic to pixi.toml but not pyproject.toml | CI uses `pip install -e ".[dev]"` reading pyproject.toml only; `ModuleNotFoundError` in all matrix jobs | Always add dependencies to `[project.dependencies]` in pyproject.toml; pixi.toml is local-only |
| Coverage without omit list | Attempted full coverage including orchestrator modules | Orchestrators shell out to `claude`, `gh` — no meaningful unit test possible | Exclude orchestrator modules via `[tool.coverage.run] omit` in pyproject.toml |
| Force-push to stale branch | Force-pushed to a years-old stale branch after rebasing | Only CodeQL triggered, not the full test suite | Rebase onto fresh main and push again to trigger complete CI matrix |
| assert for type narrowing | Used `assert x is not None` in production code | ruff S101 bans assert in non-test files | Use `if x is None: raise ImportError(...)` — ruff-compliant and mypy-friendly |
| Scripts required PYTHONPATH | Imported modules without path setup | `ModuleNotFoundError` when running scripts directly outside pixi | Add `sys.path.insert` setup at top of every script with `# noqa: E402` |
| Using PyGithub library | Added PyGithub as a Python dependency | Heavy external dependency, complex auth, slower than `gh` CLI | Rewrite to `gh` CLI subprocess calls — zero dependencies |
| Leaving stubs unimplemented | Left placeholder functions returning None | Coverage checks always passed (useless), false sense of security | Implement real functionality (e.g., XML parsing with `xml.etree.ElementTree`) |
| Single monolithic PR | Attempted to port all 17 scripts in one PR | Massive diff, hard to review, CI failures hard to isolate | Break into 4–5 sequential PRs by dependency layer |
| Creating new modules without auditing target | Planned new modules that already existed in target | Hephaestus already had `hephaestus-check-coverage`, `hephaestus-check-docstrings`; would have created duplicates | Always run Phase 0 pre-port audit before writing any code |
| Thin wrappers with main() only | Source-repo wrappers exposed only `main()` | Source tests import internal symbols directly; CI broke with ImportError | Re-export all symbols used by tests with `# noqa: F401` |
| git stash + Safety Net conflict | Used `git stash` then `git checkout --` to discard hook-modified files | Safety Net blocked `git checkout --` on hook-modified files | `git add` hook-modified files first; never use `git checkout --` to discard |
| markdownlint auto-fixer strips spaces | Tried indentation to fix `# For amendments` bash comment triggering MD025 | Auto-fixer strips leading spaces on every run — infinite fix-revert loop | Use `<!-- markdownlint-disable MD025 -->` at the top of the file |
| Coverage threshold at boundary | Copied 15 automation files; coverage dropped from ~82% to 79.97% | Low-coverage orchestration files pulled aggregate under 80% threshold | Add to coverage omit AND write minimal non-TTY path tests for modules with testable branches |
| Port the entire source implementation over destination | Replaced destination `circuit_breaker.py` wholesale | Destination had more features (registry, logging, `half_open_max_calls`) | Never replace destination with source — feature diff first; only port what's missing |
| success_threshold=2 with half_open_max_calls=1 | First success probe left `_half_open_calls` exhausted | `CircuitBreakerOpenError` raised on second probe instead of passing through | When `success_threshold > 1`, reset `_half_open_calls = 0` after each non-final success |
| Run tests with coverage | Ran `pixi run python -m pytest -v` without `--no-cov` | Coverage measured whole project at 3.88% (far below 80% floor) → exit 1 | Use `--no-cov` for targeted test runs; full coverage run only at CI step |
| Install source plugin as separate plugin | Would add all 14 superpowers skills without modification | SessionStart hook in hooks.json conflicts with existing hooks; dual routing confusion | Check for hook conflicts before choosing separate plugin installation |
| Fork/vendor upstream OSS repo | Maintained full upstream compatibility | Forking a rapidly-evolving repo creates ongoing sync burden for only 7 needed skills | Prefer selective porting over forking when you only need a subset |
| Direct copy without adaptation | Saved time on each skill port | Hardcoded paths (`docs/superpowers/specs/`) and tooling refs didn't match project | Always audit for hardcoded paths before copying; adapt all project-specific references |
| Merging code-review into two separate skills | Matched superpowers' split (requesting + receiving) | Reviewer persona and both sides naturally belong together | Consolidate closely related source skills into one ported skill |
| Placed THIRD_PARTY_LICENSES.md in skills/ | Centralized license file alongside skill files | Validator rejected it — all files in skills/ must have YAML frontmatter | Place non-skill files (licenses, READMEs) at repo root, not in skills/ |
| Used `npx skills add` automated install | Would save manual porting effort | Installs in Agent Skills Standard directory-per-skill format, incompatible with Mnemosyne | Always do manual selective port when target format differs from source |
| Generating openai.yaml without `--name` | Ran `generate_openai_yaml.py` directly | Local Python lacked `PyYAML`; `ModuleNotFoundError: No module named 'yaml'` | Pass `--name <skill-name>` to bypass frontmatter parsing |
| Importing `advise`/`learn` unchanged into Codex | Kept upstream SKILL.md content exactly as shipped | Docs referenced Claude slash commands and mandatory sub-agent behavior incompatible with Codex | Treat imported skills as source material; patch interaction-model assumptions |
| Stopping after global installation | Installed skills into `~/.codex/skills` but did not surface in repo | Future sessions not nudged toward new skills, reducing discoverability | Update repo-local `AGENTS.md` after installation |

## Results & Parameters

### Migration Statistics

| Session | Source | Target | Lines | Modules/Scripts | PRs | CI Result |
| --------- | -------- | -------- | ------- | ----------------- | ----- | ----------- |
| 2026-02-12 | ProjectOdyssey scripts | ProjectScylla scripts | ~4,500 | 17 scripts | 5 | green |
| 2026-03-30 | scylla.automation library | hephaestus.automation | ~4,400 | 16 modules | 4 + 1 cleanup | green (Python 3.10–3.13) |
| 2026-03-30 | ProjectScylla validation/resilience | hephaestus.validation + resilience | ~202 tests | 7 scripts + 2 modules | 6 Hephaestus + 1 Scylla | verified-ci |
| 2026-04-10 | Odysseus staging copy | ProjectHephaestus hephaestus.automation | 15 source files | 15 modules (never committed to actual repo) | 1 single PR | verified-local |
| 2026-04-12 | Scylla orphaned worktree | ProjectHephaestus CircuitBreaker | +10 tests | `success_threshold` feature | 1 PR | verified-local |

### Sequential PR Layer Template (Full Library Port)

```
PR 1 (Foundation):       pydantic models, retry, data classes, base utilities
PR 2 (GitHub Layer):     git_utils, github_api, worktree helpers — depends on PR 1
PR 3 (Orchestration):    implementer, reviewer, planner, pr_manager — depends on PR 2
PR 4 (CLI/Version):      entry points, version bumping, public scripts — depends on PR 3
PR 5 (Source Cleanup):   remove old library from origin repo — only after PR 1–4 CI green
```

### Copy-Paste Checklist

```markdown
## Cross-Repo Port Checklist

### Pre-Port Audit (CRITICAL — do before writing any code)
- [ ] grep pyproject.toml [project.scripts] for existing CLIs in target repo
- [ ] ls <project-root>/<target-module>/ for existing module functions
- [ ] grep <project-root>/ for function names you plan to port
- [ ] Target content is reusable (not domain-specific)
- [ ] Sequential or parallel PR layers planned (parallel if files are independent)

### Per-PR (Library Port — Sequential)
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

### Source-Repo Thin Wrappers (After Target PRs Merge)
- [ ] All target PRs merged and CI green
- [ ] Check which symbols source tests import directly (not just main())
- [ ] Re-export all required symbols in wrapper (# noqa: F401 on each re-export)
- [ ] PR description mentions dependency on target PRs
- [ ] Verify thin wrapper passes source repo CI

### Source Cleanup (Final PR)
- [ ] All target PRs merged, CI green on all Python versions
- [ ] Backwards-compatible wrapper scripts created
- [ ] New package added to source pyproject.toml dependencies
- [ ] git rm -r old library directory (source + tests)
- [ ] grep confirms zero remaining references

### Upstream OSS Skill Port
- [ ] License identified (MIT, Apache 2.0) — attribution footer added per file
- [ ] THIRD_PARTY_LICENSES.md created at repo root (NOT in skills/)
- [ ] Overlap analysis complete — merge into existing vs create new
- [ ] Full Mnemosyne YAML frontmatter added
- [ ] Traceability tag added (modular-upstream, etc.)
- [ ] python3 scripts/validate_plugins.py passes

### Codex External Skill Install
- [ ] install-skill-from-github.py run (creates ~/.codex/skills/<skill>/)
- [ ] agents/openai.yaml generated with --name flag
- [ ] policy.allow_implicit_invocation: true added
- [ ] Claude-specific assumptions patched ($ARGUMENTS, mandatory sub-agents, hardcoded paths)
- [ ] ~/.agent-brain/Mnemosyne seeded or updated
- [ ] Repo-local AGENTS.md updated to advertise new skills
```

### Key Takeaways

1. **Audit before porting** — Always check existing entry points and module functions before writing new code
2. **Extend, don't duplicate** — Add only the missing delta to existing modules
3. **Sequential PRs > Monolithic** — 4–5 PRs by layer beats 1 PR of 16 modules
4. **Parallel PRs for independent modules** — 6 parallel agents with isolated worktrees, no merge conflicts
5. **pyproject.toml is king** — CI reads it; pixi.toml is local-only
6. **pixi.lock must travel with pyproject.toml** — always commit them together
7. **Orchestrators cannot be unit tested** — add to coverage omit list
8. **CLI tools > Libraries** — `gh` CLI beats PyGithub for portability
9. **Re-export symbols in thin wrappers** — source tests import internals; main()-only wrappers break them
10. **Cross-repo dependency ordering** — Target PRs must merge before source wrapper PRs enter CI
11. **Feature diff first** — Never replace destination with source; only port what's missing
12. **Never downgrade destination** — If dest already has a better implementation, skip
13. **Attribution required** — MIT and Apache 2.0 both require attribution; create THIRD_PARTY_LICENSES.md at repo root
14. **Manual selective port > automated install** — when target format differs from source
15. **Hook conflicts matter** — Check for SessionStart hook conflicts before choosing separate plugin installation
16. **Patch imported skills** — Treat as source material; adapt hardcoded paths and platform assumptions
17. **AGENTS.md discoverability** — Always update repo-local AGENTS.md after installing skills in Codex
18. **--no-cov for targeted runs** — Full coverage run only at CI step
19. **Budget iterations** — Expect 3–4 pre-commit cycles per PR

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Port 17 scripts from ProjectOdyssey (PRs #1–5) | 2026-02-12 session |
| ProjectHephaestus | Port scylla.automation library (PRs #209–212, cleanup PR #1742) | 2026-03-30 session |
| ProjectHephaestus | Port 7 validation/resilience scripts + 2 library modules from Scylla (PRs #213–218, Scylla PR #1743) | 2026-03-30 session |
| ProjectHephaestus | Port hephaestus/automation/ 15-file module from Odysseus staging copy (PR #268) — 596 tests pass, 80.63% coverage | 2026-04-10 session |
| ProjectHephaestus | CircuitBreaker.success_threshold ported from Scylla orphaned worktree — 29/29 tests | 2026-04-12 session |
| Mnemosyne | Modular skills integration (Apache 2.0), PR #1213 — 4 skills ported (3 new, 1 merged) | 2026-04-09 session |
| ProjectHephaestus | obra/superpowers integration (MIT), PR #206 — 8 skills ported | 2026-03-28 session |
| Radiance | Codex local setup — 5 skills installed, metadata generated, AGENTS.md updated | 2026-04-02 session |
