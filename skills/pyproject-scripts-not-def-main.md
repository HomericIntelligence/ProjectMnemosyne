---
name: pyproject-scripts-not-def-main
description: "When sweeping a change across every console_script, enumerate `[project.scripts]` in pyproject.toml — NOT `grep '^def main'`. The grep misses *_main-suffixed callables (e.g. check_version_consistency_main). Use when: (1) adding a flag to every CLI, (2) refactoring shared CLI infrastructure, (3) writing a parametrized integration test that must cover every binary."
category: tooling
date: 2026-05-26
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [python, packaging, cli, console-scripts, pyproject]
---

# Use `[project.scripts]`, Not `grep '^def main'`, for Full CLI Inventory

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-26 |
| **Objective** | Document why `grep '^def main'` undercounts a project's CLI surface and what to use instead |
| **Outcome** | Caught 10 missed CLIs in a 41-CLI repo by switching to pyproject-driven enumeration |
| **Verification** | verified-local (a parametrized integration test caught the misses on the first run) |

## When to Use

- Adding a flag (`--json`, `--quiet`, `--version`, etc.) to every console script in a Python project
- Refactoring a shared CLI helper (e.g. extracting `add_logging_args`, `format_output`) and need to update every consumer
- Auditing CLI consistency (exit codes, help text, output format)
- Writing a parametrized integration test that must cover every binary the package ships
- Migrating from one CLI framework to another (argparse → click, etc.)

## Verified Workflow

### Quick Reference

```python
# In pytest: parametrize over ALL console_scripts
import tomllib
from pathlib import Path

def _load_entry_points() -> list[tuple[str, str, str]]:
    data = tomllib.loads(Path("pyproject.toml").read_text())
    scripts = data["project"]["scripts"]
    return [(cmd, *target.partition(":")[::2]) for cmd, target in sorted(scripts.items())]
```

```bash
# Quick shell inventory of (command, module:callable):
python3 -c "
import tomllib
print('\n'.join(f'{c}\t{t}' for c,t in tomllib.loads(open('pyproject.toml','rb').read())['project']['scripts'].items()))
" | sort
```

### Detailed Steps

**The pitfall:** A natural way to inventory "all CLIs" in a Python repo is:

```bash
grep -rln '^def main' hephaestus/   # returns 33 files
```

This works for projects where every entry point is `module:main`. It silently misses entry points that use suffixed names:

```toml
[project.scripts]
hephaestus-check-version-consistency = "hephaestus.version.consistency:check_version_consistency_main"
hephaestus-bench-precommit            = "hephaestus.ci.precommit:bench_precommit_main"
hephaestus-validate-agents            = "hephaestus.agents.frontmatter:validate_agents_main"
# ...etc
```

The grep matches `^def main` but not `^def check_version_consistency_main`. In one verified session, this pattern missed **10 of 41 console_scripts** (24%).

**Why suffixed names exist:** A module can host multiple CLIs (e.g. `hephaestus/validation/markdown.py` exposes BOTH `main` for `hephaestus-validate-links` AND `check_readmes_main` for `hephaestus-check-readmes`). Suffixed names are correct, idiomatic, and not going away.

**Reliable inventory:** Read `pyproject.toml [project.scripts]` directly. It's the source of truth — by definition, every binary the package ships is listed there. Anything you can't see from `[project.scripts]` does not become a binary.

**Detection / regression-prevention:** Write a parametrized integration test that loads `[project.scripts]` at collection time and asserts your invariant on every entry:

```python
# tests/integration/test_cli_entry_points.py
@pytest.mark.parametrize("command,module_path,attr", ENTRY_POINTS, ids=ENTRY_POINT_IDS)
def test_advertises_json_flag(self, command, module_path, attr):
    binary = shutil.which(command) or pytest.skip(f"{command} not on PATH")
    result = subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=30)
    assert "--json" in result.stdout + result.stderr, f"{command} missing --json"
```

When a new console_script is added, the test parametrize set grows automatically and immediately exercises the invariant. No manual list to maintain.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `grep -rln '^def main' hephaestus/` | Find every CLI by looking for `def main` | Missed 10 of 41 (24%) — any `*_main` suffix is invisible to the regex | Don't use file-content grep for entry-point inventory |
| `grep -rln 'def .*_main\|def main'` | Extend regex to suffixed names | Better, but still relies on a naming convention; also matches non-CLI helpers named `*_main` (e.g. test helpers) | Source of truth is config, not convention |
| `find hephaestus -name '*.py' \| xargs grep -l argparse` | Find files that use argparse | Matches library modules that build parsers but don't ship as CLIs (e.g. shared parser helpers) | Too broad; doesn't distinguish CLI from library |
| `ls /path/to/venv/bin/hephaestus-*` | List installed binaries | Works AFTER `pip install`, but order-dependent: if you forgot to add a `[project.scripts]` entry, the binary won't exist to be listed | Detects missing config, but won't help you survey what SHOULD be configured |
| Manual checklist | Maintain a doc listing every CLI | Goes stale within 1 PR; doc rot | Use the parametrized test instead — the test list IS the inventory |

## Results & Parameters

**Observed miss rate:** 10 of 41 (24%) in one ProjectHephaestus session.

**Time-cost-saved:** The first integration-test run after the `^def main` sweep failed loudly with 10 specific CLIs named. Re-grep + fix took 5 minutes. Without the test, the misses would have shipped silently to a PR review where reviewers might also miss them.

**Recipe for "add flag F to every CLI":**

1. **Inventory:** Parse `[project.scripts]` from pyproject.toml. Bucket by module to group co-located CLIs.
2. **Helper:** Add a shared `add_F_arg(parser)` helper (or `emit_F_envelope` for output, etc.) in your CLI utils module.
3. **Sweep:** Edit every entry point in the inventory. For modules with multiple `*_main` callables, edit EACH one.
4. **Test:** Parametrize the integration test over `_load_entry_points()`. Assert the invariant.
5. **Run:** Test failures name the specific missed entry points. Iterate until 100%.

**Concrete numbers:**
- pyproject parse + inventory: ~20 LOC of pytest fixture.
- Test class: ~30 LOC parametrized over the fixture.
- Catch rate on the first sweep: 76% (31/41); test caught the remaining 24%.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | 2026-05-26 --json sweep across 41 console_scripts (PR #603) | Initial sweep via `grep '^def main'` found 33 files. Parametrized `TestCLIJsonFlag` test caught 10 missing CLIs from `*_main` suffixed callables in `hephaestus/version/consistency.py`, `hephaestus/config/dep_sync.py`, `hephaestus/ci/precommit.py`, `hephaestus/ci/workflows.py`, `hephaestus/agents/frontmatter.py`. Final pass to 41/41 took one additional sub-agent run. |
