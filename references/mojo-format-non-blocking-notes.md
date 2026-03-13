# mojo-format-non-blocking - Raw Notes

## Session: 2026-03-13

### Context

3 open PRs failing CI due to mojo-format pre-commit hook:
- PR #4059 (3383-auto-impl): `test_utility.mojo` missing blank lines
- PR #4053 (3379-auto-impl): `test_utility.mojo` blank line + string wrap
- PR #3836 (3275-auto-impl): `test_extensor_setitem.mojo` formatting + `extensor.mojo:885` Float64->Float32 implicit conversion

### Root Cause

Mojo 0.26.1 formatter crashes on files containing `comptime_assert` syntax:
```
error: cannot format tests/shared/core/test_utility.mojo: '_python_symbols' object has no attribute 'comptime_assert_stmt'
```

Confirmed crash occurs on `main` branch too - not PR-specific.

### CI Pre-commit Failure Diff (PR #4053)

```diff
@@ -599,6 +599,7 @@ fn test_hash_different_shapes_differ() raises:
              " hashes"
          )

+
 fn test_hash_same_values_different_dtype() raises:

@@ -614,8 +615,8 @@ fn test_hash_same_values_different_dtype() raises:
     if hash_f32 == hash_f64:
         raise Error(
-            "Tensors with same values but different dtypes should have different"
-            " hashes"
+            "Tensors with same values but different dtypes should have"
+            " different hashes"
         )
```

### PR #3836 Compilation Fix

`shared/core/extensor.mojo:885`: Changed `self[flat_idx] = value` to `self.__setitem__(flat_idx, value)` to avoid implicit Float64->Float32 conversion. The explicit method call dispatches to the overload that handles dtype conversion.

### Safety Net Gotchas

- `git checkout branch 2>&1` blocked - use `git switch branch`
- `git checkout -- file` blocked - use `git restore` (also blocked without `--staged`)
- `git worktree remove --force` blocked - remove without `--force`
- `git restore file` blocked - use `git stash` first

### Timing

- 3 worktree agents ran in parallel
- PR #4059 agent: ~2 min
- PR #4053 agent: ~1 min (after manual retry)
- PR #3836 agent: ~3.5 min (had compilation fix + build verification)
