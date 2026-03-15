---
name: delegates-to-file-existence-check
description: "Add CI validation that every agent name in delegates_to frontmatter maps to a real .md file. Use when: adding referential integrity checks to agent config validators, catching stale cross-agent references automatically on PRs."
category: ci-cd
date: 2026-03-15
user-invocable: false
---

## Overview

| Field | Value |
|-------|-------|
| **Problem** | `delegates_to` fields in agent frontmatter can reference agents that no longer exist, silently creating broken delegation chains |
| **Solution** | Build a set of known agent stems at validator init time; check each `delegates_to` name against this set during frontmatter validation |
| **Scope** | `AgentConfigValidator` class in `tests/agents/validate_configs.py` |
| **Language** | Python 3.7+ |
| **Test file** | `tests/agents/test_validate_delegates_to.py` (16 pytest tests) |

## When to Use

- You have a directory of agent `.md` files with YAML frontmatter that includes `delegates_to` fields
- You want CI to automatically block PRs that introduce stale agent references
- You are extending `AgentConfigValidator` to enforce agent referential integrity
- A PR was merged that deleted an agent file but left `delegates_to` references pointing to it

## Verified Workflow

### Quick Reference

```python
# In AgentConfigValidator.__init__
self.existing_agents: set = (
    {f.stem for f in agents_dir.glob("*.md")}
    if agents_dir.exists()
    else set()
)

# In _validate_frontmatter, after model validation
if "delegates_to" in frontmatter:
    raw = frontmatter["delegates_to"].strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if inner:
            names = [n.strip() for n in inner.split(",") if n.strip()]
            for name in names:
                if name not in self.existing_agents:
                    errors.append(
                        f"delegates_to references non-existent agent: '{name}'"
                        f" (no .claude/agents/{name}.md)"
                    )
    else:
        errors.append(f"delegates_to must be a YAML inline list, got: '{raw}'")
```

### Step 1 — Build known-agents set in `__init__`

Add one line to `AgentConfigValidator.__init__` after `self.results`:

```python
self.existing_agents: set = (
    {f.stem for f in agents_dir.glob("*.md")}
    if agents_dir.exists()
    else set()
)
```

This captures all `.md` file stems (e.g. `implementation-engineer` from `implementation-engineer.md`)
at construction time, before any validation runs.

### Step 2 — Add `delegates_to` check in `_validate_frontmatter`

At the end of `_validate_frontmatter`, just before `return errors, warnings, frontmatter`:

```python
if "delegates_to" in frontmatter:
    raw = frontmatter["delegates_to"].strip()
    # Parse YAML inline list: [name-a, name-b] or empty []
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if inner:
            names = [n.strip() for n in inner.split(",") if n.strip()]
            for name in names:
                if name not in self.existing_agents:
                    errors.append(
                        f"delegates_to references non-existent agent: '{name}'"
                        f" (no .claude/agents/{name}.md)"
                    )
    else:
        errors.append(f"delegates_to must be a YAML inline list, got: '{raw}'")
```

Key details:
- Inline list format `[a, b, c]` must match the actual YAML frontmatter convention in the project
- Empty list `[]` is valid (no error)
- The error message includes the expected filename to make fixing obvious

### Step 3 — Fix any stale references caught by the new check

Run the validator to find existing broken references:

```bash
python3 tests/agents/validate_configs.py .claude/agents/
```

For each error like `delegates_to references non-existent agent: 'senior-implementation-engineer'`,
remove the name from the relevant agent's `delegates_to` field.

### Step 4 — Write pytest tests

Create `tests/agents/test_validate_delegates_to.py` with tests covering:

```python
class TestExistingAgentsSetInit:       # init populates set, empty dir, nonexistent dir
class TestDelegatesToValidationValid:  # [], single ref, multiple refs, spaces around commas
class TestDelegatesToValidationInvalid:  # missing ref → error, error message content, is_valid=False
class TestDelegatesToFormatValidation: # non-list value → error
class TestDelegatesToRealAgents:       # integration: all .claude/agents/ refs are valid
```

The integration test is the key regression guard:

```python
def test_all_agent_delegates_to_references_exist(self) -> None:
    agents_dir = self._find_agents_dir()
    validator = AgentConfigValidator(agents_dir)
    results = validator.validate_all()

    stale_errors = [
        f"{result.file_path.name}: {error}"
        for result in results
        for error in result.errors
        if "delegates_to references non-existent agent" in error
    ]
    assert stale_errors == [], (
        "Stale delegates_to references found:\n"
        + "\n".join(f"  {e}" for e in stale_errors)
    )
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Lazy lookup per validation | Re-glob the agents directory on each `_validate_frontmatter` call | Would be slow for large directories and misses the point of a single-pass validator | Build the set once at `__init__` time |
| Storing full paths instead of stems | `existing_agents = {f for f in agents_dir.glob("*.md")}` | Comparison against string names from frontmatter always fails | Store stems (`f.stem`) not full `Path` objects |
| Warning instead of error | Treating missing refs as warnings | Warnings don't fail CI; stale references are definite bugs not style issues | Use `errors.append(...)`, not `warnings.append(...)` |
| Validating format outside `_validate_frontmatter` | Adding a separate `_validate_delegates_to` method | Worked but required passing `frontmatter` dict as an extra argument, adding complexity | Inline the check inside `_validate_frontmatter` where `frontmatter` is already available |

## Results & Parameters

### Final configuration that passed all 54 tests

```python
# In AgentConfigValidator.__init__
self.existing_agents: set = (
    {f.stem for f in agents_dir.glob("*.md")}
    if agents_dir.exists()
    else set()
)
```

```python
# In _validate_frontmatter (inline list parser)
if "delegates_to" in frontmatter:
    raw = frontmatter["delegates_to"].strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if inner:
            names = [n.strip() for n in inner.split(",") if n.strip()]
            for name in names:
                if name not in self.existing_agents:
                    errors.append(
                        f"delegates_to references non-existent agent: '{name}'"
                        f" (no .claude/agents/{name}.md)"
                    )
    else:
        errors.append(f"delegates_to must be a YAML inline list, got: '{raw}'")
```

### Test results

```
54 passed in 0.14s
```

### Files changed

| File | Change |
|------|--------|
| `tests/agents/validate_configs.py` | Added `existing_agents` set to `__init__`; added `delegates_to` check in `_validate_frontmatter` |
| `.claude/agents/security-specialist.md` | Removed stale `senior-implementation-engineer` from `delegates_to` |
| `tests/agents/test_validate_delegates_to.py` | 16 new pytest tests (new file) |
