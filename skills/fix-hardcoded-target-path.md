---
name: fix-hardcoded-target-path
description: 'Fix hardcoded output/target directory paths in migration and tooling
  scripts by adding CLI flag, env var fallback, and safe default. Use when: a script
  has a hardcoded absolute path that fails on other machines.'
category: tooling
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# fix-hardcoded-target-path

## Overview

| Item | Details |
|------|---------|
| Name | fix-hardcoded-target-path |
| Category | tooling |
| Problem | Script has a hardcoded absolute path constant that works only on the original developer's machine |
| Solution | Add three-level path resolution: CLI arg → env var → safe default |

## When to Use

- A script fails with "directory not found" because it has a hardcoded absolute path like `/home/user/...`
- A migration or tooling script targets an external repository clone at a user-specific location
- You need to make a script portable without breaking existing callers that rely on the constant

## Verified Workflow

### 1. Identify the hardcoded constant

```python
# Before — hardcoded, breaks on other machines
MNEMOSYNE_DIR = Path("/home/mvillmow/Odyssey2/build/ProjectMnemosyne")
MNEMOSYNE_SKILLS_DIR = MNEMOSYNE_DIR / "skills"
```

### 2. Add a resolver function with three-level priority

```python
import os

DEFAULT_MNEMOSYNE_DIR = Path("/tmp/ProjectMnemosyne")  # nosec B108


def resolve_mnemosyne_dir(target: Optional[str]) -> Path:
    """Resolve the ProjectMnemosyne directory path.

    Priority: --target-dir CLI arg > MNEMOSYNE_DIR env var > /tmp/ProjectMnemosyne default.

    Args:
        target: Value of the --target-dir CLI argument, or None if not provided.

    Returns:
        Resolved Path to the ProjectMnemosyne root directory.
    """
    if target is not None:
        return Path(target)
    env = os.environ.get("MNEMOSYNE_DIR")
    if env:
        return Path(env)
    return DEFAULT_MNEMOSYNE_DIR


# Keep old constants for backward compat with tests that patch them directly
MNEMOSYNE_DIR = DEFAULT_MNEMOSYNE_DIR
MNEMOSYNE_SKILLS_DIR = MNEMOSYNE_DIR / "skills"
```

### 3. Add `--target-dir` CLI argument (default=None, not the hardcoded string)

```python
parser.add_argument(
    "--target-dir",
    metavar="DIR",
    default=None,  # IMPORTANT: None, not str(MNEMOSYNE_DIR)
    help="Path to ProjectMnemosyne clone (default: $MNEMOSYNE_DIR env var or /tmp/ProjectMnemosyne)",
)
```

### 4. Use the resolver in `main()` and improve the error message

```python
target_dir = resolve_mnemosyne_dir(args.target_dir)

if not target_dir.exists():
    print(
        f"ERROR: ProjectMnemosyne directory not found: {target_dir}\n"
        f"Use --target-dir PATH or set MNEMOSYNE_DIR env var.",
        file=sys.stderr,
    )
    return 1
```

### 5. Update helper functions to accept path explicitly (avoid global state)

```python
def skill_already_exists(skill_name: str, mnemosyne_skills_dir: Optional[Path] = None) -> bool:
    """Check if a skill already exists."""
    skills_dir = mnemosyne_skills_dir if mnemosyne_skills_dir is not None else MNEMOSYNE_SKILLS_DIR
    if not skills_dir.exists():
        return False
    ...
```

Call site in `main()`:

```python
if not args.force and skill_already_exists(skill_name, target_skills_dir):
```

### 6. Fix Bandit B108 warning for `/tmp/` paths

Bandit flags hardcoded `/tmp/` paths as B108. Suppress with inline comment:

```python
DEFAULT_MNEMOSYNE_DIR = Path("/tmp/ProjectMnemosyne")  # nosec B108
```

### 7. Write tests for the resolver

```python
class TestResolveMnemosyneDir:
    def test_explicit_target_takes_priority(self, module, tmp_path):
        env_path = str(tmp_path / "env_path")
        explicit_path = str(tmp_path / "explicit_path")
        with patch.dict("os.environ", {"MNEMOSYNE_DIR": env_path}):
            result = module.resolve_mnemosyne_dir(explicit_path)
        assert result == Path(explicit_path)

    def test_env_var_used_when_no_target(self, module, tmp_path):
        env_path = str(tmp_path / "from_env")
        with patch.dict("os.environ", {"MNEMOSYNE_DIR": env_path}):
            result = module.resolve_mnemosyne_dir(None)
        assert result == Path(env_path)

    def test_default_used_when_neither_set(self, module):
        env = {k: v for k, v in os.environ.items() if k != "MNEMOSYNE_DIR"}
        with patch.dict("os.environ", env, clear=True):
            result = module.resolve_mnemosyne_dir(None)
        assert result == Path("/tmp/ProjectMnemosyne")  # nosec B108
```

### 8. Document in README

Add a section to `scripts/README.md` with:

- **Required Setup** explaining the three ways to specify the path
- **Usage Examples** showing `--target-dir`, env var export, and `--dry-run`

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Set `default=str(MNEMOSYNE_DIR)` in argparse | Used the hardcoded constant as the CLI default | Still evaluates the hardcoded path at import time; users get the wrong default path | Set `default=None` and resolve in `main()` via `resolve_mnemosyne_dir()` |
| Used `/tmp/` default without `# nosec B108` | Added default path `/tmp/ProjectMnemosyne` | Bandit B108 flagged it as a security issue, blocking commit | Add `# nosec B108` inline comment on the line with the `/tmp/` path |
| Removed unused variable without re-staging | Fixed ruff F841 but didn't re-stage the file | Ruff Format hook auto-reformatted the file, causing the second commit to also fail | After any hook auto-fix, `git add` the modified files before re-running commit |
| Patched module-level constant in tests | Tests used `patch.object(module, "MNEMOSYNE_SKILLS_DIR", ...)` for `skill_already_exists` | Works for `migrate_skill()` but `skill_already_exists()` still used the global | Accept `mnemosyne_skills_dir` as an explicit parameter with `None` default |

## Results & Parameters

### Three-level priority (copy-paste pattern)

```python
def resolve_<x>_dir(target: Optional[str]) -> Path:
    if target is not None:
        return Path(target)
    env = os.environ.get("<ENV_VAR_NAME>")
    if env:
        return Path(env)
    return DEFAULT_<X>_DIR  # safe fallback, add # nosec B108 if /tmp/
```

### argparse argument (always use `default=None`)

```python
parser.add_argument("--target-dir", metavar="DIR", default=None,
    help="Path to <repo> clone (default: $<ENV_VAR> env var or <default_path>)")
```

### Backward-compat constants (keep old names, point to new default)

```python
# Keep for tests that patch these directly
OLD_DIR = DEFAULT_DIR
OLD_SKILLS_DIR = OLD_DIR / "skills"
```
