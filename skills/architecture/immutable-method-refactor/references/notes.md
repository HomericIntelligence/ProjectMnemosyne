# Session Notes: Immutable Method Refactor (Issue #1223)

## Session Context

- **Date**: 2026-03-02
- **Project**: ProjectScylla
- **Issue**: #1223 — ResumeManager.handle_zombie() mutates rm.checkpoint but callers reassign self.checkpoint independently
- **Branch**: 1223-auto-impl
- **PR**: HomericIntelligence/ProjectScylla#1311

## Root Cause Analysis

`ResumeManager` was designed as an immutable collaborator: all mutating methods use
`self.config.model_copy(update=...)` and return `(config, checkpoint)` tuples. Callers
must use the return value — `rm.checkpoint` is never the source of truth after a call.

However, `handle_zombie()` violated this contract:

```python
# Line 92 (before fix) — mutates self.checkpoint
self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
```

This was filed as a follow-up to #1148.

## Fix Applied

```diff
-            self.checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
+            reset_checkpoint = reset_zombie_checkpoint(self.checkpoint, checkpoint_path)
+            return self.config, reset_checkpoint
```

## Test Change

```diff
+        original_checkpoint = rm.checkpoint
         ...
+        assert rm.checkpoint is original_checkpoint
```

## Verification

All 30 unit tests in `tests/unit/e2e/test_resume_manager.py` pass.

## Pre-commit Hook Behavior

The push pre-commit hook runs all tests. The combined coverage floor is 9% (unit tests
use `--cov-fail-under=75` separately). The hook's 8.60% report is a pre-existing condition
unrelated to this change — the push still succeeds because the branch was already at that level.
