---
name: tooling-bulk-rename-relative-path-trap
description: "Bulk path renames (sed/perl across a repo) silently break relative-pattern argument lists like `just test-group \"tests\" \"shared/fuzz/test_*.mojo\"` because the relative arg already has an implicit base path. Use when: (1) planning a `shared/`->`src/<pkg>/` rename, (2) refactoring any directory name that appears in wrapper-script invocations (just, xargs, find -path, Makefile includes, Dockerfile COPY), (3) debugging a CI coverage validator that fails after an otherwise-green bulk refactor, (4) writing perl/sed sweeps with path-boundary lookbehinds and want to audit the false-negative cases."
category: tooling
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: [bulk-rename, perl, sed, refactoring, ci-validation, test-coverage]
---

# Bulk Rename Relative-Path Trap

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-18 |
| **Objective** | Rename `shared/` -> `src/projectodyssey/` across the ProjectOdyssey repo (770 files) using targeted perl substitutions while preserving wrapper-script argument semantics. |
| **Outcome** | Most rewrites correct, but one CI job (`pre-commit-benchmark` -> `validate_test_coverage.py`) failed because a *relative* pattern argument inside a `just test-group` invocation got an absolute-style prefix applied. Fix was one-line, but the failure mode is invisible to grep-based review. |
| **Verification** | verified-ci (failure observed on PR #5414; fix verified locally with `validate_test_coverage.py` + `pre-commit run`) |

## When to Use

- You're about to run a bulk `find ... | xargs perl -i -pe 's/<old>/<new>/g'` or `sed -i` sweep across a repo.
- The old name is a directory name (e.g., `shared/`, `lib/`, `src/`) likely to appear inside string arguments.
- The repo uses wrapper scripts that take a base path + relative pattern args: `just test-group <base> <patterns>`, `xargs -I {} cmd <prefix>{}`, `find <root> -path '...'`, Makefile/Dockerfile glob lists.
- A CI coverage/path validator is failing after a refactor whose other workflows are all green.
- You are tightening a perl regex with a lookbehind like `(?<![\w./])` and want to know which legitimate-looking matches still slip through.

## Verified Workflow

### Quick Reference

```bash
# 1. BEFORE the bulk rewrite — find wrapper-script invocations carrying implicit base paths.
grep -rnE 'test-group|xargs.*\b<OLD>\b|find\s+\S+\s+-path' \
  .github/ justfile Makefile* Dockerfile* scripts/ \
  | grep -v '\.git/'

# 2. For each match, decide manually: is the <OLD>/ token a path RELATIVE to a base
#    argument earlier on the same line? If so, the rewrite should NOT prepend the new
#    prefix — drop the prefix entirely so the wrapper still composes correctly.

# 3. Run the bulk rewrite with a path-boundary lookbehind.
git ls-files -z | xargs -0 perl -i -pe 's{(?<![\w./])<OLD>/}{<NEW>/}g'

# 4. IMMEDIATELY run path/coverage validators (not just at the end of the refactor).
pixi run python scripts/validate_test_coverage.py   # ProjectOdyssey
# or repo-equivalent: pytest --collect-only, bazel query, etc.

# 5. Re-grep the wrapper invocations from step 1 and eyeball the relative-pattern args.
grep -rnE 'test-group|xargs.*\b<NEW>\b|find\s+\S+\s+-path' .github/ justfile Makefile* Dockerfile*
```

### Detailed Steps

1. **Inventory wrapper-script invocations BEFORE rewriting.** The trap is invisible after
   the fact. Save a list of every line in `.github/workflows/`, `justfile`, `Makefile`,
   `Dockerfile`, and shell scripts that calls a wrapper taking `<base> <pattern>` form.
   In ProjectOdyssey the offender was:

   ```yaml
   # .github/workflows/comprehensive-tests.yml
   run: |
     just test-group "tests" \
       "test_*.mojo training/test_*.mojo unit/test_*.mojo \
        integration/test_*.mojo helpers/test_*.mojo \
        tooling/benchmarks/test_*.mojo shared/fuzz/test_*.mojo"
   ```

   The second arg is RELATIVE to `"tests"`. So `shared/fuzz/...` actually meant
   `tests/shared/fuzz/...` on disk.

2. **Run the perl/sed sweep with a path-boundary lookbehind.** The one used here was
   `s{(?<![\w./])shared/}{src/projectodyssey/}g`. This catches most cases but the
   lookbehind allows `quote+space` (which is exactly what wrapper-arg lists look like),
   so the relative-pattern case still mutates.

3. **Run coverage/path validators immediately after each rewrite phase.** Don't batch
   them to the end. In ProjectOdyssey:

   ```bash
   pixi run python scripts/validate_test_coverage.py
   # Exits 1 with explicit "uncovered files" list naming
   # tests/projectodyssey/fuzz/test_tensor_fuzz.mojo
   ```

4. **For each wrapper-script line, manually decide the right rewrite.** If the token
   appears as a relative pattern (no leading slash, no leading variable, preceded by a
   quoted base-path arg earlier on the line), drop the prefix part of the new name. In
   ProjectOdyssey the fix was:

   ```diff
   - tooling/benchmarks/test_*.mojo src/projectodyssey/fuzz/test_*.mojo
   + tooling/benchmarks/test_*.mojo projectodyssey/fuzz/test_*.mojo
   ```

   The `just test-group "tests"` base prefixes `tests/` to produce the correct
   `tests/projectodyssey/fuzz/test_*.mojo`.

5. **Re-run the validator and `pre-commit run` to confirm.** All other CI workflows
   pass even with the bug present — the path validator is the only signal.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1. Path-boundary lookbehind | `perl -pe 's{(?<![\w./])shared/}{src/projectodyssey/}g'` over all files | Lookbehind correctly excluded mid-path matches like `a/shared/b`, but ALLOWED quote+space (which appears inside wrapper-script arg lists). The relative-pattern token `shared/fuzz/test_*.mojo` inside `"...benchmarks/test_*.mojo shared/fuzz/..."` matched and was rewritten with the absolute-style prefix. | A path-boundary lookbehind cannot distinguish "absolute-position path token" from "relative path argument to a wrapper". The wrapper context is what matters, not the lexical neighborhood. |
| 2. Grep audit of the end state | `git diff` + `grep -rn 'src/projectodyssey/'` over rewritten files to spot anomalies | The rewritten line `src/projectodyssey/fuzz/test_*.mojo` is syntactically valid and "looks right" — there's nothing visually wrong with it. The bug only manifests when `just test-group "tests"` composes its base path onto it at runtime. | Visual review of bulk-rewrite diffs cannot catch path-composition bugs. The error surface is dynamic, not lexical. Need a path validator that resolves the composition. |
| 3. Trusting the main test workflows | CI was green on `comprehensive-tests`, `build-validation`, `mojo-test`, `pre-commit` — only `pre-commit-benchmark` failed | The missing fuzz test was a no-op skip at the YAML level for everything except the coverage validator. Glob `tests/src/projectodyssey/fuzz/test_*.mojo` matched zero files and silently expanded to nothing in the test runner; only `scripts/validate_test_coverage.py` cross-checked that EVERY test file under `tests/` is covered by SOME workflow glob. | Coverage validators are the canary for path-composition bugs. Always run them — and treat their exit status as authoritative — after any bulk path rewrite, even when 9/10 CI jobs are green. |

## Results & Parameters

### Detection signal (ProjectOdyssey)

```text
$ pixi run python scripts/validate_test_coverage.py
ERROR: Found uncovered test files (not matched by any workflow glob):
  - tests/projectodyssey/fuzz/test_tensor_fuzz.mojo
exit 1
```

### Minimum-effective audit grep (run BEFORE the bulk rewrite)

```bash
# Replace <OLD> with the directory being renamed (here: shared)
grep -rnE 'test-group|xargs.*\b<OLD>\b|find\s+\S+\s+-path|COPY\s+<OLD>/|include\s+<OLD>/' \
  .github/ justfile Makefile* Dockerfile* scripts/ 2>/dev/null
```

### Perl rewrite with path-boundary lookbehind (still imperfect — needs manual audit)

```bash
git ls-files -z | xargs -0 perl -i -pe 's{(?<![\w./])shared/}{src/projectodyssey/}g'
```

### Reference PR

- ProjectOdyssey PR #5414: <https://github.com/HomericIntelligence/ProjectOdyssey/pull/5414>
- Faulty commit chain: 488f1e76 -> daa4c6d7 -> a3b3c010
- Fix: change `src/projectodyssey/fuzz/test_*.mojo` -> `projectodyssey/fuzz/test_*.mojo` in
  `.github/workflows/comprehensive-tests.yml` (one line)

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectOdyssey | PR #5414 — shared/ -> src/projectodyssey/ rename, 770 files | `validate_test_coverage.py` flagged `tests/projectodyssey/fuzz/test_tensor_fuzz.mojo` after the perl sweep mutated a relative arg in `comprehensive-tests.yml`. One-line fix landed on the same PR. |
