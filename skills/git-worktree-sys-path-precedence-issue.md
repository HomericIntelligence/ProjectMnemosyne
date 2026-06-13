---
name: git-worktree-sys-path-precedence-issue
description: "Document the sys.path ordering issue in workspace-based git worktrees where the main project directory comes before the worktree in Python's module search path, causing subprocess-spawned entry points (console scripts) to import modules from the main repo instead of the worktree, even though the editable install (.pth file) correctly points to the worktree. Code changes work in direct Python imports but fail in subprocess invocations. Use when: (1) running console scripts via subprocess that load stale code from the main repo, (2) debugging entry points that work in direct Python imports but fail via pixi run or subprocess.run(), (3) code changes in a git worktree work when imported directly but fail when invoked as a console script, (4) sys.path shows main project directory before worktree path, (5) VERIFYING a console-script fix from inside a worktree where the installed entry point emits empty/unpatched output and you might wrongly conclude 'the fix does not work' — re-verify via python -m <module> and probe module.__file__ / inspect.getsource(main)."
category: tooling
date: 2026-06-12
version: "1.1.0"
user-invocable: false
verification: verified-local
tags:
  - git-worktree
  - sys-path
  - PYTHONPATH
  - editable-install
  - console-scripts
  - entry-points
  - subprocess
  - pixi
  - python-environment
  - monorepo
  - module-resolution
---

# Git Worktree sys.path Precedence Issue

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-06 |
| **Objective** | Understand why console script entry points load stale code from the main project repo instead of from the current git worktree, even though editable installs and direct imports work correctly |
| **Outcome** | Discovered sys.path precedence issue where the main project directory is listed BEFORE the worktree path in Python's module search order. Code changes work in direct Python imports but fail when invoked via subprocess entry points. Root cause is the .pth file search path ordering, not the editable install itself. |
| **Verification** | verified-local — Discovered and validated locally during Issue #724 implementation (added -V/--version flag to 44 console scripts). Subprocess invocations from worktrees consistently loaded stale code; pixi run and direct Python imports both worked correctly. Solution approaches tested locally (PYTHONPATH export and pixi run context) but CI was not examined. |

## When to Use

- Running console scripts via `subprocess.run()` from a git worktree and observing stale code from the main repo being executed
- Code changes work correctly when imported directly (`python3 -c 'import mymodule; mymodule.func()'`) but fail when invoked as an entry point (`subprocess.run(['mymodule-cli', '--version'])`)
- Workspace-based git monorepos using pixi and editable installs (`pip install -e .`) where worktrees share `.pixi/envs/default` with the parent checkout
- Debugging why console scripts report old function behavior, old version strings, or missing recent code additions despite the worktree containing the updated files
- Building automation tools or test suites that spawn console scripts as subprocess commands from within a git worktree
- **Verifying a console-script fix locally from inside a worktree** — when running the installed entry point (e.g. `hephaestus-check-repo-analyze-skills --json`) emits EMPTY or UNPATCHED output and tempts you to conclude "the fix does not work." The script-execution path resolves `hephaestus` from the OUTER repo source tree (which lacks your fix); `python -m <module>` and direct `from <module> import main` both load the patched worktree code. Re-verify there before believing the fix failed.

Do NOT use this skill when:

- The issue is a full env-resolve wipe (see [`pixi-env-resolve-drops-editable-install`](pixi-env-resolve-drops-editable-install.md)) — that's a different failure mode with `ModuleNotFoundError` at the top level
- The console script itself is stale (see [`tooling-pyproject-scripts-dev-install-after-merge`](tooling-pyproject-scripts-dev-install-after-merge.md)) — if the script entry point does not exist or is outdated
- Running tests directly via `pytest` or importing directly in the REPL — those don't exhibit the issue because they run in the same Python process with the current sys.path

## Verified Workflow

### Quick Reference

```bash
# 1. Check what sys.path subprocess sees (run from worktree)
python3 -c 'import sys; print(sys.path)'
# Expected: Should show worktree path early, but often shows main project FIRST

# 2. Verify editable install location
ls -la .pixi/envs/default/lib/python*/site-packages/ | grep _editable_impl
cat .pixi/envs/default/lib/python*/site-packages/_editable_impl_*.pth
# Output should show: /path/to/worktree

# 3. Confirm direct import works (from worktree)
pixi run python -c "import hephaestus; print(hephaestus.__version__)"
# Works ✓ (loads from worktree)

# 4. Test subprocess invocation that fails (from worktree)
pixi run hephaestus-agent-stage --version
# May load stale code from main repo ✗

# 5. Solution: Use pixi run (same environment context as parent)
pixi run hephaestus-agent-stage --version
# Loads from worktree ✓

# 6. Alternative solution: Prepend worktree to PYTHONPATH (explicit)
export PYTHONPATH="/path/to/worktree:$PYTHONPATH"
pixi run hephaestus-agent-stage --version
```

### Console-Script Verification Probe (which tree resolved?)

When verifying a fix from a worktree, the DEFINITIVE check is which file actually
loaded — not the console-script's output. Probe `module.__file__` and the source:

```python
# Run from inside the worktree
from hephaestus.validation import repo_analyze_skills as m
import inspect
print("MODFILE:", m.__file__)                       # reveals which tree resolved
print("HAS_FIX:", "args.json" in inspect.getsource(m.main))
# If MODFILE points OUTSIDE the worktree (e.g. /home/.../ProjectHephaestus/hephaestus/...
# instead of /home/.../build/.worktrees/issue-NNNN/hephaestus/...), the editable
# install is shadowing your code and HAS_FIX will be False.
```

Authoritative LOCAL verification of a console-script fix inside a worktree is
`python -m <module>` OR `python -c "from <module> import main; main([...])"` — NOT
the installed entry-point script. Note: `pixi run dev-install` re-points
`which <console-script>` to the worktree's bin but does NOT fix the
script-execution `sys.path[0]` shadowing, because the shared pixi env's `.pth`
still references the outer source tree. CI checks the branch out into a clean
standalone tree, so the entry point resolves correctly there.

### Detailed Steps

**Step 1 — Detect the symptom.**

Create a simple test: modify a function in the worktree, then invoke the console script:

```bash
# In worktree: edit hephaestus/__init__.py to change __version__ or add a marker function
cd /path/to/worktree
echo "print('MARKER FROM WORKTREE')" >> hephaestus/__init__.py

# Via subprocess, invoke the console script
pixi run hephaestus-agent-stage --version
# Output: Old version from main repo (not the worktree modification)
# ✗ If you see the old code, sys.path is loading from main repo
```

**Step 2 — Inspect sys.path order in subprocess context.**

```bash
# From the worktree, print the full sys.path that a subprocess sees
python3 -c 'import sys; [print(i, path) for i, path in enumerate(sys.path)]'
```

Look for:
- `/home/mvillmow/Projects/ProjectHephaestus` (main repo) — appears EARLY
- `/home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724` (worktree) — appears LATER

If main repo path comes BEFORE worktree path, that's the issue.

**Step 3 — Verify the .pth file points to the worktree.**

```bash
# Check which editable install was registered
find .pixi/envs/default/lib/python*/site-packages/ -name '_editable_impl_*.pth' -exec cat {} \;
# Output should be: /home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724
#                   (the worktree path, NOT the main repo)
```

If the .pth file is correct but sys.path still has main repo first, the issue is path precedence.

**Step 4 — Understand why this happens.**

When `pip install -e .` runs, it creates a `.pth` file that gets prepended to the Python path. However, if you are running Python from a directory context (worktree) while the parent repo is also in sys.path (from earlier setup), Python's import system may search the parent first depending on how the module search order is constructed.

The key insight: **The editable install .pth file is correct, but the main project directory is ALSO in sys.path due to environment inheritance or explicit path configuration.**

**Step 5 — Apply Solution 1: Use pixi run (preferred).**

When you invoke subprocess commands through `pixi run`, you preserve the same Python environment context (same sys.path, same .pixi/envs/default). This avoids the path precedence issue entirely:

```bash
# Instead of raw subprocess.run(['console-script', '--version']),
# use pixi run in your automation:
pixi run hephaestus-agent-stage --version
```

In Python:

```python
import subprocess
result = subprocess.run(
    ['pixi', 'run', 'hephaestus-agent-stage', '--version'],
    cwd='/path/to/worktree',
    capture_output=True,
    text=True
)
print(result.stdout)  # Loads from worktree ✓
```

**Step 6 — Apply Solution 2: Explicit PYTHONPATH (if pixi run is not available).**

If you must use raw subprocess invocation (not pixi run), prepend the worktree to PYTHONPATH:

```bash
# From worktree or parent, set PYTHONPATH explicitly
export PYTHONPATH="/home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724:$PYTHONPATH"
/path/to/bin/hephaestus-agent-stage --version
# Loads from worktree ✓
```

In Python:

```python
import os
import subprocess

worktree_path = '/home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724'
env = os.environ.copy()
env['PYTHONPATH'] = f"{worktree_path}:{env.get('PYTHONPATH', '')}"

result = subprocess.run(
    ['/path/to/bin/hephaestus-agent-stage', '--version'],
    cwd=worktree_path,
    env=env,
    capture_output=True,
    text=True
)
print(result.stdout)  # Loads from worktree ✓
```

**Step 7 — Verify the fix.**

After applying the solution, re-run the console script and check that it now loads from the worktree:

```bash
pixi run hephaestus-agent-stage --version
# Should now show the current git SHA or modified version (proof it's loading from worktree)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|---|---|---|
| Reinstalling the package | Ran `pip uninstall hephaestus && pip install -e .` to refresh the editable install | sys.path still showed main project before worktree; the .pth file was refreshed but the path ordering was NOT reordered | Reinstalls don't fix path ordering; the issue is sys.path search precedence, not the editable install metadata. .pth file location is correct; the parent directory is also in the search path. |
| Deleting .pyc and __pycache__ | Removed all Python bytecode cache to force a fresh import | Subprocess still loaded stale code from main repo; caching was never the issue | Root cause is sys.path ordering at the module resolution layer, not compilation artifacts. Python doesn't cache the module search path itself. |
| Running console script directly without pixi | Executed `/path/to/.pixi/envs/default/bin/hephaestus-agent-stage` as a raw subprocess | Still loaded from main repo; the issue is that the Python interpreter inside that executable was started with a sys.path that included the main repo before the worktree | The problem is not the shell invocation; it's the Python process's environment and sys.path ordering. Pixi run context preserves the environment better. |
| Setting PYTHONPATH in shell before invoking subprocess | Exported `PYTHONPATH=/path/to/worktree:$PYTHONPATH` in bash, then called subprocess | subprocess.run() did NOT inherit the shell's exported PYTHONPATH; only env passed explicitly to subprocess gets it | When using subprocess.run() in Python, env vars are NOT inherited from the parent shell unless explicitly passed via the `env=` parameter; `os.environ.copy()` is required. |
| Checking only the main .pth file | Examined `.pth` file in main repo's site-packages | Missed that the worktree was using the SAME `.pixi/envs/default` and the .pth file there was also pointing to the worktree (correctly) | Both the main repo and worktree share `.pixi/envs/default`; the .pth file is correct in both cases. The issue is NOT the .pth target but the sys.path ordering. |
| Trusting an empty console-script run as proof the fix is broken | Verified an `--json` console-script fix by running the installed entry point `hephaestus-check-repo-analyze-skills --json` from inside the worktree (Issue #1217); it emitted EMPTY/unpatched output (exit 0, no JSON envelope), suggesting the fix did not work | The script-execution `sys.path[0]` became the wrapper's bin dir and the editable `.pth` resolved `hephaestus` from the OUTER repo tree (which lacks the fix). `python -m hephaestus.validation.repo_analyze_skills --json` and a direct `from ... import main; main([...])` both emitted the correct envelope | Never conclude "the fix doesn't work" from an empty/unpatched console-script run inside a worktree. Re-verify with `python -m <module>` and probe `module.__file__`; if it points outside the worktree, the editable install is shadowing your code. CI resolves correctly because it checks out a clean standalone tree. |
| Running `pixi run dev-install` to fix the console-script shadowing | Ran `pixi run dev-install` (≈ `pip install -e .`) in the worktree expecting the installed entry point to then load the worktree code | `which <console-script>` re-pointed to the worktree's bin, but the script-execution `sys.path[0]` shadowing persisted because the shared pixi env's `.pth` still references the OUTER source tree | `dev-install` updates the bin shim, not the `.pth` precedence for script execution. For LOCAL verification use `python -m <module>` / direct import; the entry point itself is only reliable in CI's clean checkout. |

## Results & Parameters

### Diagnostic Commands (Copy-Paste Ready)

```bash
# From a git worktree, check what sys.path subprocess sees
python3 -c 'import sys; [print(i, path) for i, path in enumerate(sys.path)]'
# Output example:
#   0 
#   1 /home/mvillmow/Projects/ProjectHephaestus
#   2 /home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724
#   3 /path/to/.pixi/envs/default/lib/python3.14t/site-packages
#   ...
# ↑ Main repo at [1], worktree at [2] = PROBLEM

# Check which directory the editable install .pth file points to
find .pixi/envs/default/lib/python*/site-packages/ -name '_editable_impl_*.pth' -exec cat {} \;
# Output should be: /home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724

# Verify that direct imports work (same worktree context)
pixi run python3 -c "import hephaestus; print(hephaestus.__version__)"
# Output: 0.9.4.dev14+g3cc2f0fb (current worktree commit SHA)

# Test subprocess invocation (shows the problem)
pixi run hephaestus-agent-stage --version
# If this shows old version (from main repo), the issue is reproduced

# Test subprocess after PYTHONPATH fix
export PYTHONPATH="/home/mvillmow/Projects/ProjectHephaestus/build/.worktrees/issue-724:$PYTHONPATH"
pixi run hephaestus-agent-stage --version
# Should now show current version (if fix works)
```

### Example: Issue #724 Reproduction

During the implementation of Issue #724 (add -V/--version flag to 44 console scripts), the following pattern emerged:

```python
# Code added to cli/__init__.py (in worktree)
def add_version_arg(parser: argparse.ArgumentParser) -> None:
    """Add -V/--version flag to a console script."""
    version_str = importlib.metadata.version('hephaestus')
    parser.add_argument('-V', '--version', action='version', version=version_str)

# Test in the same Python process:
pixi run python -c "from hephaestus.cli import add_version_arg; print('✓ Import works')"
# Output: ✓ Import works (code from worktree loaded)

# Test via subprocess console script:
pixi run hephaestus-agent-stage --version
# Output: ModuleNotFoundError: No module named 'cli' (stale code from main repo)
# OR: 0.9.3 (old version from main repo, not 0.9.4.devN+worktree-sha)
```

The fix applied: All console-script invocations in automation were changed from raw `subprocess.run()` to `pixi run <script>` to preserve the environment context.

### sys.path Inspection Pattern

To diagnose in any Python subprocess context:

```python
import subprocess
import sys

# What does THIS process see?
print("=== Direct import (current process) ===")
print(sys.path[:3])

# What does a subprocess see?
result = subprocess.run(
    ['python3', '-c', 'import sys; print(sys.path[:3])'],
    capture_output=True,
    text=True
)
print("=== Subprocess invocation ===")
print(result.stdout)

# What does pixi run see?
result = subprocess.run(
    ['pixi', 'run', 'python3', '-c', 'import sys; print(sys.path[:3])'],
    capture_output=True,
    text=True
)
print("=== pixi run invocation ===")
print(result.stdout)
```

### Decision Tree: When to Use Which Solution

```
Does your code run subprocess commands from a git worktree?
├─ YES
│  ├─ Is the command a console script (entry point)?
│  │  ├─ YES
│  │  │  ├─ Can you use `pixi run <script>` (in same directory context)?
│  │  │  │  ├─ YES → Solution 1: Use pixi run (PREFERRED)
│  │  │  │  └─ NO → Solution 2: Export PYTHONPATH explicitly
│  │  │  └─ Is the script defined in [project.scripts]?
│  │  │     ├─ YES → Same issue applies, use pixi run
│  │  │     └─ NO → Check if it's a shell wrapper or compiled binary
│  │  └─ NO (raw Python invocation)
│  │     └─ Direct import in subprocess context — apply Solution 2 (PYTHONPATH)
│  └─ NO → Not affected by this issue
└─ NO → Not affected by this issue
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #724: Add -V/--version flag to 44 console scripts | 2026-06-06 — Discovered during implementation that `pixi run hephaestus-agent-stage --version` loaded stale code from main repo in a git worktree. Direct imports worked correctly. Root cause: sys.path ordering with main repo before worktree. Solution: Use `pixi run` for all subprocess invocations of console scripts. Verified locally (pixi run works, direct subprocess fails). CI not examined in detail. |
| ProjectHephaestus | Issue #1217: Wire inert `--json` into `hephaestus-check-repo-analyze-skills` via `emit_json_status()` | 2026-06-12 — During VERIFICATION the installed console script emitted EMPTY/unpatched output from the worktree, falsely suggesting the fix failed. Probing `module.__file__` showed `hephaestus` resolving to the OUTER repo tree; `inspect.getsource(m.main)` showed `"args.json" in src` was False. `python -m hephaestus.validation.repo_analyze_skills --json` and direct `main([...])` import both emitted the correct JSON envelope. `pixi run dev-install` re-pointed `which` but did NOT fix script-execution shadowing. Lesson: authoritative local console-script verification inside a worktree is `python -m` / direct import, not the entry point. verified-local; CI for PR #1253 pending. |

## References

- [`pixi-env-resolve-drops-editable-install`](pixi-env-resolve-drops-editable-install.md) — Related but different: full env wipe after `pyproject.toml` edits, not path ordering
- [`tooling-pyproject-scripts-dev-install-after-merge`](tooling-pyproject-scripts-dev-install-after-merge.md) — Related but different: stale console-script entry points after branch merge, not path ordering
- [`git-worktree-parallel-execution-lifecycle`](git-worktree-parallel-execution-lifecycle.md) — Comprehensive worktree lifecycle guide
- [Python sys.path initialization](https://docs.python.org/3/library/sys.html#sys.path) — Official Python documentation
- [pip editable installs (.pth files)](https://pip.pypa.io/en/stable/cli/pip_install/#editable-installs) — How .pth files are created and used
