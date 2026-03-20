---
name: resolve-mojo-rebase-conflict
description: Resolve git rebase conflicts in Mojo test files by converting invalid
  Python syntax to valid Mojo patterns using Bool flags
category: ci-cd
date: 2026-03-07
version: 1.0.0
user-invocable: false
---
# Resolve Mojo Rebase Conflict Skill

| Field | Value |
|-------|-------|
| Date | 2026-03-07 |
| Objective | Resolve git rebase conflict in a Mojo test file caused by invalid Python syntax in incoming commit |
| Outcome | Conflict resolved with valid Mojo Bool-flag pattern; rebase completed; test passes |
| Category | ci-cd |

## When to Use

- A rebase conflict exists in a `.mojo` test file
- Incoming commit introduced Python-style code (dicts, sets, f-strings) that is invalid Mojo
- The intent of the incoming change was correct (e.g., order-agnostic assertions) but syntax was wrong
- Need to preserve the semantic intent while fixing to valid Mojo

## Verified Workflow

### 1. Read the conflicted file around the conflict markers

```bash
# Find conflict markers
grep -n "<<<<<<\|=======\|>>>>>>>" tests/shared/test_serialization.mojo
```

Then use the `Read` tool with `offset` and `limit` to see the exact context.

### 2. Replace the entire conflicted block in one Edit call

Include the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) and all content between them
in the `old_string`. Replace with valid Mojo code that preserves the intent.

**Pattern for order-agnostic tensor assertions (Bool tracking flags)**:

```mojo
        # Order-agnostic verification using name matching
        var found_weights = False
        var found_bias = False

        for i in range(len(loaded)):
            var name = loaded[i].name
            if name == "weights":
                found_weights = True
                assert_equal(loaded[i].tensor.numel(), 6, "Wrong size for weights")
            elif name == "bias":
                found_bias = True
                assert_equal(loaded[i].tensor.numel(), 3, "Wrong size for bias")

        assert_true(found_weights, "Missing weights tensor")
        assert_true(found_bias, "Missing bias tensor")
```

**Why this pattern**: Mojo has no `set`, `dict`, or `in` operator for collections.
Use `var` Bool flags + `for i in range(len(...))` index loops instead.

### 3. Stage and continue the rebase

```bash
git add tests/shared/test_serialization.mojo
GIT_EDITOR=true git rebase --continue
```

`GIT_EDITOR=true` skips the commit message editor (accepts the default message).

### 4. Verify with targeted test run

```bash
just test-group tests/shared "test_serialization.mojo"
```

Use `just test-group <dir> <pattern>` — faster than `just test-mojo` which runs everything.

## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Key Mojo vs Python Differences for Test Assertions

| Python (invalid in Mojo) | Mojo equivalent |
|--------------------------|-----------------|
| `expected = {"a": 1}` | `var found_a = False` (Bool flag) |
| `found = set()` | Multiple `var found_x = False` flags |
| `for item in collection:` | `for i in range(len(collection)):` |
| `name in expected` | `name == "a" or name == "b"` |
| `raise AssertionError(f"...")` | `assert_true(cond, "message")` |

## References

- `tests/shared/test_serialization.mojo` — the file fixed in this session
- `tests/examples/test_trait_based_serialization.mojo` — reference for Bool-flag pattern
- Commit `0b6f52a4` — the resolved commit
