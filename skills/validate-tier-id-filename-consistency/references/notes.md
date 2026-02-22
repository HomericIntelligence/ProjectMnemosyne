# Raw Notes — validate-tier-id-filename-consistency

## Session Context

- **Date**: 2026-02-22
- **Issue**: ProjectScylla #807 (follow-up from #733)
- **Branch**: `807-auto-impl`
- **PR**: #945

## Problem Statement

`load_all_tiers()` globs `t*.yaml` files, extracts the filename stem (e.g. `"t0"`), calls
`load_tier(stem)`, and stores the result under that stem as the dict key. However, `load_tier()`
uses the body-level `tier:` field when present, only falling back to the filename stem when
`tier` is absent from the YAML. This means a file named `t0.yaml` with `tier: t1` in its body
produces `result["t0"].tier == "t1"` — the key and the object's own ID field disagree.

Any caller that trusts the dict key to be authoritative (e.g., for logging, routing, or display)
gets silently wrong data.

## Execution Log

### Step 1: Read issue and plan

Read `.claude-prompt-807.md` and ran `gh issue view 807 --comments`. The issue already had a
detailed implementation plan including:
- Exact lines to change in `loader.py`
- Which normalization to apply (`lower().strip()`, prefix with `"t"`)
- Warning not to add fixture files to shared dir (use `tmp_path`)

### Step 2: Read source files

Read `scylla/config/loader.py` (full file) and `tests/unit/test_config_loader.py` (full file).

Key observations:
- `load_tier()` normalizes at lines 211–213; stores body `tier` field at lines 218–220
- `load_all_tiers()` was 10 lines, no consistency check
- Existing `test_load_all_tiers` asserts `len(tiers) == 2` — confirmed `tmp_path` strategy correct

### Step 3: Implement production fix

Edit to `load_all_tiers()`: 14-line change replacing 1 line. Added `expected` computation +
guard block.

### Step 4: Add tests

Two methods added to `TestConfigLoaderTier`:
1. `test_load_all_tiers_mismatched_id_raises` — uses `tmp_path`, creates `t0.yaml` with `tier: t1`
2. `test_load_all_tiers_consistent_ids` — uses `FIXTURES_PATH`, asserts key == config.tier

### Step 5: Run tests

- Tier-only: 7/7 pass (coverage low in isolation — expected)
- Full suite: 2398/2398 pass, 74.16% coverage (above 73% threshold)

### Step 6: Commit

Pre-commit hook failed first attempt: E501 on docstring line 197 (101 chars).
Fixed by shortening `"when filename stem and config.tier disagree"` to
`"when filename and config.tier disagree"`.
Second commit succeeded: all hooks green.

### Step 7: Push and PR

```
git push -u origin 807-auto-impl
gh pr create --title "fix(config): Validate tier IDs in load_all_tiers() match filenames"
gh pr merge --auto --rebase
```

PR #945 created, auto-merge enabled.

## File Changes

| File | Type | Lines changed |
|------|------|--------------|
| `scylla/config/loader.py` | Modified | +14, -1 (lines 244–261) |
| `tests/unit/test_config_loader.py` | Modified | +25, -0 (after line 194) |

## Team Knowledge Used

The issue plan referenced these ProjectMnemosyne skills as prior learnings:
- `fix-resource-prompt-consistency`
- `fix-yaml-config-propagation`
- `resume-crash-debugging`
- `centralized-path-constants`
