---
name: ci-matrix-timeout-guidance
description: "Add timeout monitoring guidance comments to GitHub Actions matrix entries. Use when: (1) a CI matrix has a shared timeout and groups may approach the limit, (2) groups grew after consolidation and risk timing out, (3) you want to document split thresholds and file counts inline without changing runtime behavior."
category: ci-cd
date: 2026-03-07
user-invocable: false
---

# CI Matrix Timeout Guidance

Add inline YAML comments to GitHub Actions matrix entries documenting timeout risk, file counts,
and actionable split thresholds — without modifying any runtime behavior.

## Overview

| Date | Objective | Outcome |
|------|-----------|---------|
| 2026-03-07 | Add timeout monitoring comments to 15-group Mojo CI matrix after consolidation from 31 groups | 24-line pure-comment diff; all pre-commit hooks pass; YAML valid |

## When to Use

- (1) A CI matrix has a shared `timeout-minutes` and some groups grew large after consolidation
- (2) You want to document which groups are highest risk and what the split threshold is
- (3) Follow-up to `consolidate-ci-matrix` skill — after merging groups, add monitoring guidance
- (4) Group file counts are not obvious from glob patterns alone

## Verified Workflow

1. **Read the matrix** in the workflow file (e.g. `comprehensive-tests.yml`):

   ```bash
   # Count files in each explicit-pattern group
   # Pattern field is space-separated .mojo filenames
   echo "test_a.mojo test_b.mojo" | wc -w  # → 2
   ```

2. **Add a matrix-level policy block** directly above `test-group:`:

   ```yaml
   matrix:
     # ---------------------------------------------------------------------------
     # Timeout policy: all groups share the single 15-minute timeout-minutes above.
     # After each CI run, check the "duration" field in test-results-*.json artifacts
     # to monitor wall-clock time per group.
     # Action threshold: if a group consistently exceeds 10 minutes, split it into
     # two non-overlapping entries (see ADR-009 for the split pattern).
     # File counts below are based on the explicit pattern lists; glob-only groups
     # are marked "monitor" because the count varies as new tests are added.
     # ---------------------------------------------------------------------------
     test-group:
   ```

3. **Categorize each matrix entry** by pattern type:
   - **Explicit-pattern groups**: count the space-separated filenames, assign risk tier
   - **Glob-pattern groups** (`test_*.mojo`): mark as "monitor — file count varies"
   - **Mixed groups** (some explicit + some globs): mark as "Mixed explicit + glob patterns — monitor"

4. **Risk tiers for explicit-pattern groups**:

   | File count | Risk | Comment |
   |-----------|------|---------|
   | 20+ | High | "N files — highest timeout risk; split first if consistently >10 min" |
   | 10-19 | Medium | "N files — medium risk; monitor before splitting" |
   | 5-9 | Medium | "N files — medium risk; monitor wall-clock time" |
   | 1-4 | Low | "N files — low risk; split unlikely needed" |

5. **Add per-entry comments** on the line immediately before `- name: "..."`:

   ```yaml
   # ---- Section header comment (existing) ----
   # 20 files — highest timeout risk; split first if consistently >10 min
   - name: "Core Tensors"
   ```

6. **For glob-only groups**, add the comment before the existing section header or after it:

   ```yaml
   # ---- Autograd engine + shared benchmarking helpers ----
   # Glob pattern — file count varies; monitor wall-clock time before splitting
   - name: "Autograd & Benchmarking"
   ```

7. **Validate YAML** and run pre-commit:

   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/workflows/comprehensive-tests.yml').read()); print('YAML valid')"
   pixi run pre-commit run --files .github/workflows/comprehensive-tests.yml
   # Or: just pre-commit-all
   ```

8. **Commit and PR** — pure documentation change, no matrix entry names modified:

   ```bash
   git add .github/workflows/comprehensive-tests.yml
   git commit -m "docs(ci): add timeout-minutes guidance to CI matrix comments"
   gh pr create --title "docs(ci): add timeout-minutes guidance to CI matrix comments" \
     --body "Closes #<issue-number>" --label "documentation"
   gh pr merge --auto --rebase
   ```

## Key Decisions

### What to annotate

| Group type | Annotation strategy |
|-----------|-------------------|
| Explicit-pattern (20+ files) | File count + "highest timeout risk; split first" |
| Explicit-pattern (8-19 files) | File count + "medium risk; monitor before splitting" |
| Explicit-pattern (1-4 files) | File count + "low risk; split unlikely needed" |
| Glob-only | "Glob pattern — file count varies; monitor wall-clock time before splitting" |
| Mixed explicit+glob | "Mixed explicit + glob patterns — monitor wall-clock time before splitting" |

### Placement rules

- Matrix-level policy block goes between `fail-fast:` and `test-group:`
- Per-entry comments go on the line immediately before `- name:` (after any existing section header)
- Never modify the `name:` values — they are referenced by `continue-on-error` logic and CI display
- Never modify `pattern:`, `path:`, or `continue-on-error` fields — documentation only

### What NOT to change

- `timeout-minutes` value (requires actual timing data from CI runs)
- Matrix entry names (break `continue-on-error` expressions and CI dashboards)
- `pattern:` fields (would change which tests run)
- Job-level `continue-on-error` expressions

## Results & Parameters

### Diff profile

```
.github/workflows/comprehensive-tests.yml | 24 ++++++++++++++++++++++++
1 file changed, 24 insertions(+)
```

All 24 lines are YAML comments — zero runtime behavior change.

### Policy block template

```yaml
matrix:
  # ---------------------------------------------------------------------------
  # Timeout policy: all groups share the single <N>-minute timeout-minutes above.
  # After each CI run, check the "duration" field in test-results-*.json artifacts
  # to monitor wall-clock time per group.
  # Action threshold: if a group consistently exceeds <N-5> minutes, split it into
  # two non-overlapping entries (see <ADR-reference> for the split pattern).
  # File counts below are based on the explicit pattern lists; glob-only groups
  # are marked "monitor" because the count varies as new tests are added.
  # ---------------------------------------------------------------------------
  test-group:
```

### Pre-commit hooks that run on workflow files

| Hook | Result |
|------|--------|
| `check-yaml` | Must pass — validates YAML syntax |
| `trailing-whitespace` | Must pass — no trailing spaces |
| `end-of-file-fixer` | Must pass — file must end with newline |
| `validate-test-coverage` | Must pass — checks no matrix names changed |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding file counts to glob-pattern groups | Tried to count glob matches dynamically | Glob count varies by repo state; misleading in a static comment | Use "file count varies; monitor" phrasing for globs |
| Modifying `name:` values to include file counts | Added "(20 files)" suffix to `name: "Core Tensors"` | `continue-on-error` expressions reference the name string directly; breaks the check | Never touch `name:` — annotation goes in YAML comments only |
| Setting per-group `timeout-minutes` override | Tried adding `timeout-minutes: 12` to large groups | GitHub Actions matrix entries do not support per-entry `timeout-minutes`; only job-level is valid | Timeout is job-level only; inline comments are the correct approach |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | Issue #3357, PR #4001 | Follow-up to consolidate-ci-matrix (#3156); 15-group Mojo test matrix |

## References

- See `consolidate-ci-matrix` skill — precursor that creates the groups being annotated
- ADR-009 in ProjectOdyssey — split pattern reference for when groups exceed threshold
- `validate_test_coverage.py` in ProjectOdyssey — validates no test files were dropped
