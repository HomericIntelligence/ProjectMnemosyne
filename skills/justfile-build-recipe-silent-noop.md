---
name: justfile-build-recipe-silent-noop
description: 'Detect and fix build recipes that silently compile nothing due to
  over-eager find filter exclusions. Use when: (1) build succeeds suspiciously fast,
  (2) build/<mode>/ contains 0-1 files, (3) adding `-Werror` to a build that previously
  appeared green.'
category: ci-cd
date: 2026-05-11
version: 1.0.0
verification: verified-ci
user-invocable: false
---

## Overview

| Field | Value |
| ------- | ------- |
| **Problem** | A `just build` (or similar Make/justfile/script) recipe completes with "Build successful" but compiles 0-1 files — silently regressed because its `find` filter excludes every directory now holding real source |
| **Root Cause** | Exclusion-list filtering: `find . -name '*.mojo' -not -path './tests/*' -not -path './shared/*' …` — every new top-level source directory not listed continues to be silently excluded; if all source dirs end up excluded, the build is a no-op |
| **Fix** | Replace exclusion-based discovery with explicit per-directory enumeration; split executables (`mojo build`) from libraries (`mojo package`); add an end-of-recipe summary that prints the actual count and asserts a minimum |
| **Verification** | After fix in ProjectOdyssey PR #5389: 46 binaries + 1 .mojopkg compiled per mode; `--Werror` then surfaced 9+ real warnings the no-op recipe had been hiding |
| **Reference PR** | [HomericIntelligence/ProjectOdyssey#5389](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5389) |

## When to Use

- `just build` (or equivalent) completes in seconds — far faster than a realistic full compile of the codebase
- Build output prints "✅ Build successful" but you see no `→ Building: X` lines, or only 1-2 lines
- `ls build/<mode>/ | wc -l` returns 0 or 1 vs the dozens of executables you expect
- CI "Build Validation" job passes in well under a minute on a non-trivial codebase
- You're about to add `--Werror` / `-Werror` to a build step that has "always been green" — verify it isn't green because nothing was being compiled
- Adding a new top-level source directory (e.g. `papers/`, `experiments/`) that the build does not appear to pick up

## Verified Workflow

### Quick Reference

```bash
# 1. Diagnose: count how many files the recipe actually compiles
just build 2>&1 | grep -c "→ Building:"     # If 0-1, recipe is broken
ls build/debug/ 2>/dev/null | wc -l         # Should match expected count

# 2. Audit the find filter in the recipe
grep -nE 'find .* -name "\*\.\w+"' justfile
# Look for -not -path patterns that exclude every directory containing src

# 3. Replace with explicit per-directory enumeration
find examples   -name "*.mojo" -not -path "*/.*" -not -name "__init__.mojo" -not -name "model.mojo" -print0
find benchmarks -name "*.mojo" -not -path "*/.*" -not -name "__init__.mojo" -print0
find papers     -path "*/examples/*.mojo" -not -path "*/.*" -not -name "__init__.mojo" -print0

# 4. Filter for executable entry points (single xargs invocation, tolerate no-match)
... | xargs -0 grep -lE "^fn main|^def main" || true

# 5. For library directories with no main(), use the package builder, not the executable builder
mojo package shared -o build/debug/shared.mojopkg

# 6. Add a count-asserting summary
echo "Built: $BUILT executables, $FAILED failed"
if [ "$BUILT" -lt 5 ]; then
    echo "ERROR: suspiciously few binaries built — recipe likely regressed"
    exit 1
fi
```

### Detailed Steps

1. **Reproduce the silent no-op.** Run the recipe and count its actual outputs. A real
   build prints one line per compiled file; a no-op prints only summary text.

   ```bash
   just build 2>&1 | tee /tmp/build.log
   grep -c "→ Building:" /tmp/build.log        # Should be > 1
   ls build/debug/ 2>/dev/null | wc -l
   ```

2. **Locate the broken filter.** The pattern to look for is a `find` invocation that
   uses *exclusion* lists for source directories:

   ```bash
   find . \
       \( -path "./.pixi" -o -path "./worktrees" \) -prune -o \
       \( -name "*.mojo" \
           -not -path "./.claude/*" \
           -not -path "./tests/*" \
           -not -path "./shared/*" \
           -not -path "./examples/*" \
           -not -path "./benchmarks/*" \
       \) -print
   ```

   If every directory that contains real source is in the exclusion list, the recipe
   matches zero (or only a stray) files.

3. **Rewrite as explicit inclusion.** Enumerate the directories the build *should*
   visit, not the ones it should skip. New top-level directories then default to
   "excluded until added" — a safer default for a build recipe.

4. **Split executables from libraries.** `mojo build` requires `fn main` or
   `def main`. Library trees (`shared/`, packages with only `__init__.mojo`) must
   use `mojo package` instead. Mixing them causes spurious failures or pushes you
   back toward over-eager exclusion.

5. **Use a single `xargs` invocation for the main-detector grep.** `xargs -I{} grep -l
   "^fn main" {}` re-invokes grep once per file and exits 123 on any no-match — fatal
   when even one file lacks `main()`. The fix is one batched invocation tolerant of
   exit 1:

   ```bash
   printf '%s\0' "${candidates[@]}" | xargs -0 grep -lE "^fn main|^def main" || true
   ```

6. **Add a count-asserting summary.** This is the regression guard. Without it,
   the recipe can silently drift back to no-op as the tree evolves.

   ```bash
   BUILT=0; FAILED=0
   for f in "${entry_points[@]}"; do
       if mojo build "$f" -o "build/$mode/$(basename "$f" .mojo)"; then
           BUILT=$((BUILT+1))
       else
           FAILED=$((FAILED+1))
       fi
   done
   echo "Built: $BUILT executables, $FAILED failed"
   if [ "$BUILT" -lt 5 ]; then
       echo "ERROR: suspiciously few binaries built — recipe likely regressed"
       exit 1
   fi
   ```

7. **Avoid `find … | while read` loops** for the per-file build step. They mask
   failures of individual builds (the loop's exit code is the last command's, not
   the worst one). Use explicit BUILT/FAILED counters as above.

8. **Verify with `--Werror`.** Adding strict warning-as-error mode is the most
   reliable smoke test: a no-op recipe stays green, a real recipe surfaces every
   latent warning. In ProjectOdyssey PR #5389 this surfaced 9+ real warnings the
   prior no-op recipe had been hiding.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| 1 | Compile `shared/` per-file with `mojo build` | `__init__.mojo` and library modules have no `main()` — `mojo build` errors out | Library trees must use `mojo package shared -o build/<mode>/shared.mojopkg`, not `mojo build`; split executables from libraries |
| 2 | `xargs -I{} grep -l "^fn main" {}` to find entry points | Re-invokes grep per file; any file without `main()` returns exit 1, and xargs exits 123 — fatal for the whole pipeline | Use a single batched invocation tolerant of no-match: `xargs -0 grep -lE "^fn main\|^def main" \|\| true` |
| 3 | `find … \| while read f; do mojo build "$f"; done` | Loop exit status is last command's; individual build failures are silently lost | Use explicit `BUILT=$((BUILT+1))` / `FAILED=$((FAILED+1))` counters and final non-zero exit when `FAILED > 0` |
| 4 | Patch exclusion-based `find` filter by adding new `-not -path` clauses when CI breaks | Reactive — each new top-level source directory must be remembered, and the silent-no-op failure mode is preserved | Use explicit per-directory inclusion so new dirs are *added* (visible commit) rather than *implicitly excluded* (silent) |
| 5 | Trust "✅ Build successful" output as proof the recipe worked | Recipe prints success based on exit code, not actual artifact count | Add an end-of-recipe assertion: `if [ "$BUILT" -lt N ]; then exit 1; fi` for a known-minimum N |

## Results & Parameters

| Parameter | Value | Notes |
| --------- | ----- | ----- |
| **Pre-fix builds compiled** | 1 file (`scripts/verify_installation.mojo`) | Excluded every dir holding real source |
| **Post-fix builds compiled** | 46 executables + 1 `.mojopkg` per build mode | debug / release / asan / tsan |
| **Latent warnings surfaced** | 9+ | All hidden by the prior no-op behavior |
| **Recipe runtime change** | Seconds → minutes | A real compile is *expected* to take time |
| **Minimum-count guard threshold** | Project-specific (use `expected_count / 2` or known floor) | Tune per repo; goal is "obviously broken" detection, not exact match |
| **Verification level** | verified-ci | Shipped in [ProjectOdyssey#5389](https://github.com/HomericIntelligence/ProjectOdyssey/pull/5389) |
| **Generalizes to** | Any build recipe using exclusion-based `find`/`glob` discovery: Makefiles, justfiles, npm/yarn scripts, shell wrappers around compiler CLIs | The anti-pattern is language-agnostic |
