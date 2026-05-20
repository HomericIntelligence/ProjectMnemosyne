---
name: justfile-and-local-build-verification
description: "Use when: (1) just recipe fails with 'inconsistent leading whitespace'\
  \ due to heredoc; (2) build completes suspiciously fast with 0-1 compiled files\
  \ (silent no-op from over-eager find exclusions); (3) running local builds before\
  \ push to mirror CI; (4) taking a dirty working tree through verify→fix→commit→PR."
category: ci-cd
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: justfile-and-local-build-verification.history
tags:
  - justfile
  - just
  - heredoc
  - build
  - local-verification
  - pre-commit
  - ci
---

## Overview

| Field | Value |
| ------- | ------- |
| **Theme** | Justfile recipe authoring pitfalls and local build verification workflows |
| **Date** | 2026-05-19 |
| **Objective** | Fix heredoc whitespace errors, detect silent no-op builds, run local builds matching CI, and ship verified commits |
| **Outcome** | Synthesized from 4 skills covering the full developer build loop |

## When to Use

- `just` recipe fails with `"Recipe line has inconsistent leading whitespace"` — heredoc in a `#!/usr/bin/env bash` recipe
- `just build` completes in seconds; `ls build/<mode>/ | wc -l` returns 0–1 instead of dozens of files
- About to add `--Werror` to a build that has "always been green" — verify it isn't green because nothing compiled
- Adding a new top-level source directory that the build does not appear to pick up
- Running local builds before pushing to catch issues before CI, faster iteration
- Implementation complete (possibly from a previous context-exhausted session) and you need to verify, fix pre-commit, and create a PR

## Verified Workflow

### Quick Reference

```bash
# Heredoc fix: diagnose the error
just --list 2>&1 | head -10
# Replace heredoc cat >> <<ENTRY ... ENTRY with printf in the recipe

# Silent no-op fix: check compile count
just build 2>&1 | grep -c "-> Building:"   # should be > 1
ls build/debug/ 2>/dev/null | wc -l        # should match expected

# Local build loop
eval "$(pixi shell-hook)"
just build && just test

# Verify + commit
pre-commit run --all-files
git add <files> && git commit -m "feat(scope): description"
gh pr create --title "..." --body "..."
gh pr merge --auto --squash
```

### Part 1 — Fix Heredoc Whitespace Error in just Recipe

#### Step 1: Identify the broken pattern

`just` requires all lines in a recipe body to share the same leading whitespace.
A `#!/usr/bin/env bash` recipe at 4-space indent with a heredoc whose body is 2-space
indented, and a terminator at column 0, triggers the error on every `just --list` or invocation.

```just
        cat >> "$OUTPUT" <<ENTRY
  {"field": "$var1", "field2": $var2}
ENTRY
```

#### Step 2: Replace with printf

```just
        printf '  {"field": "%s", "field2": %s}\n' \
            "$var1" "$var2" >> "$OUTPUT"
```

Key rules:

- Keep the same leading whitespace (4 spaces) as the rest of the recipe
- Use `%s` placeholders; add `"` around string values, omit for numerics
- Append `>> "$OUTPUT"` on the last line of the `printf` call
- Use `\` line continuation — `just` handles this correctly

#### Step 3: Verify

```bash
just --list | grep <recipe-name>
# Should now list the recipe without errors
```

#### Parameter Alias Pattern (bonus — enabled by bash shebang)

Use `if ... ; then ... fi` for normalization — never bare `&&` with `||`:

```just
train model="lenet_emnist":
    #!/usr/bin/env bash
    MODEL="{{model}}"
    if [ "$MODEL" = "lenet" ] || [ "$MODEL" = "lenet5" ]; then MODEL="lenet_emnist"; fi
    just _run "pixi run mojo run -I . examples/$MODEL/run_train.mojo"
```

### Part 2 — Detect and Fix Silent No-Op Build Recipes

#### Step 1: Reproduce the silent no-op

```bash
just build 2>&1 | tee /tmp/build.log
grep -c "-> Building:" /tmp/build.log   # Should be > 1
ls build/debug/ 2>/dev/null | wc -l
```

#### Step 2: Locate the broken find filter

Look for exclusion-based discovery — every new top-level source directory not listed
is silently skipped:

```bash
grep -nE 'find .* -name "\*\.\w+"' justfile
# Look for -not -path patterns that exclude every directory containing real source
```

#### Step 3: Rewrite as explicit inclusion

Replace with per-directory enumeration; new directories default to "excluded until added":

```bash
find examples   -name "*.mojo" -not -path "*/.*" -not -name "__init__.mojo" -print0
find benchmarks -name "*.mojo" -not -path "*/.*" -not -name "__init__.mojo" -print0
find papers     -path "*/examples/*.mojo" -not -path "*/.*" -not -name "__init__.mojo" -print0
```

#### Step 4: Split executables from libraries

`mojo build` requires `fn main`/`def main`. Library trees must use `mojo package`:

```bash
mojo package shared -o build/debug/shared.mojopkg
```

Filter for executable entry points with a single batched grep (tolerates no-match):

```bash
printf '%s\0' "${candidates[@]}" | xargs -0 grep -lE "^fn main|^def main" || true
```

#### Step 5: Add a count-asserting summary (regression guard)

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

### Part 3 — Run Local Build Matching CI

```bash
# Activate environment
eval "$(pixi shell-hook)"

# Verify toolchain
which mojo && mojo --version

# Build
just build   # or: mojo build -I . src/main.mojo

# Test
just test    # or: mojo test -I . tests/  /  pytest tests/

# Format
mojo format .   # Python: black .

# Pre-commit
pre-commit run --all-files
```

**Build flags:** `-I .` (include current dir), `-O` (release optimizations), `-v` (verbose).

### Part 4 — Verify → Fix → Commit → PR

#### Step 1: Run targeted tests first (fast feedback)

```bash
pixi run python -m pytest tests/unit/<module>/ -v --no-cov
```

#### Step 2: Run pre-commit

```bash
pre-commit run --all-files
```

Note which hooks fail. The hook modifies files in place; re-run after the first pass.

#### Step 3: Fix common pre-commit failures

**Ruff E501 (line too long):** wrap at a natural break point:

```python
# Before: one long string
"  rerun-agents /exp/ -> run --config <dir> --results-dir /exp/ --from replay_generated"
# After: split with \n
"  rerun-agents /exp/\n    -> run --config <dir> --results-dir /exp/\n        --from replay_generated"
```

**check-mypy-counts out of date:** regenerate the baseline:

```bash
pixi run python scripts/check_mypy_counts.py --update
```

Stage `MYPY_KNOWN_ISSUES.md` alongside your other changes.

#### Step 4: Re-confirm all green, then commit and PR

```bash
pre-commit run --all-files   # All Passed or Skipped

git checkout -b <issue-number>-<description>
git add <file1> <file2> ... MYPY_KNOWN_ISSUES.md
git commit -m "$(cat <<'EOF'
feat(scope): Short imperative description

- Key change 1
- Key change 2

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

git push -u origin <branch-name>

gh pr create \
  --title "feat(scope): Short description" \
  --body "$(cat <<'EOF'
## Summary
- Bullet 1

## Test plan
- [x] All tests pass
- [x] Pre-commit hooks pass

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"

gh pr merge --auto --squash
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Heredoc with terminator at column 0 | `cat >> "$OUTPUT" <<ENTRY\n  {...}\nENTRY` | `just` "inconsistent leading whitespace" — bare terminator at col 0 breaks recipe body indent | `just` validates ALL recipe lines including heredoc terminators; use `printf` instead |
| Indented heredoc terminator | Indented `ENTRY` to match recipe whitespace | bash requires heredoc terminators at column 0 (unless using `<<-` with tabs) | bash and `just` have conflicting heredoc whitespace requirements; `printf` resolves both |
| `<<-ENTRY` with tabs | Strip leading tabs via `<<-` heredoc | Recipe uses spaces throughout; mixing tabs in heredoc body is a maintenance hazard | `printf` is simpler and eliminates the bash/`just` conflict entirely |
| Bare `&&` alias form | `[ "$M" = "a" ] \|\| [ "$M" = "b" ] && M="full"` | Operator precedence bug: `\|\|` and `&&` evaluated left-to-right; first true `\|\|` short-circuits `&&` | Always use `if [ ... ] \|\| [ ... ]; then ...; fi` — eliminates precedence ambiguity |
| Exclusion-based `find` patching | Added `-not -path` clauses to fix CI breaks reactively | Each new top-level source dir must be remembered; silent no-op failure preserved | Use explicit per-directory inclusion so additions are visible commits, not silent omissions |
| `mojo build` on library trees | Compiled `shared/` per-file with `mojo build` | Library modules have no `main()` — `mojo build` errors out | Use `mojo package shared -o build/<mode>/shared.mojopkg` for library directories |
| `xargs -I{} grep -l "^fn main" {}` | Per-file grep to find entry points | Re-invokes grep per file; any file without `main()` returns exit 1, xargs exits 123 — fatal | Use single batched invocation: `xargs -0 grep -lE "^fn main\|^def main" \|\| true` |
| `find ... \| while read f; do build; done` | Loop over build targets | Loop exit status is last command's; individual build failures silently lost | Use explicit `BUILT` / `FAILED` counters with final non-zero exit when `FAILED > 0` |
| Trust "Build successful" output | Assumed exit-0 means artifacts were produced | Recipe prints success based on exit code, not artifact count | Add end-of-recipe assertion: `if [ "$BUILT" -lt N ]; then exit 1; fi` |

## Results & Parameters

### Heredoc → printf Template

```just
        printf '  {"<key1>": "%s", "<key2>": %s, "<key3>": "%s"}\n' \
            "$string_var" "$numeric_var" "$another_string_var" >> "$OUTPUT"
```

- `"%s"` with quotes for string JSON values; `%s` without for numerics

### Silent No-Op Build: Before / After (ProjectOdyssey reference)

| Metric | Before (broken) | After (fixed) |
| ------ | --------------- | ------------- |
| Files compiled | 1 (`scripts/verify_installation.mojo`) | 46 executables + 1 `.mojopkg` per mode |
| Latent warnings | 0 (hidden) | 9+ surfaced by `--Werror` |
| Recipe runtime | Seconds | Minutes (expected for real compile) |
| Verification level | verified-ci | PR HomericIntelligence/ProjectOdyssey#5389 |

### Minimum-Count Guard

Set `N` to `expected_count / 2` or a known floor. Goal is "obviously broken" detection, not exact match.

### Pre-commit Hook Reference Order (ProjectScylla)

| Step | Hook | Action |
| ---- | ---- | ------ |
| 1 | `ruff-format-python` | Auto-formats; re-run after first pass |
| 2 | `ruff-check-python` | E501 must be fixed manually |
| 3 | `mypy` | Type check (passes if no new errors) |
| 4 | `check-mypy-counts` | Baseline count; update with `--update` flag |
| 5 | Custom hooks | markdownlint, ShellCheck, YAML, model config naming |

### Build Verification Checklist

- [ ] Environment activated
- [ ] Build succeeds with no errors
- [ ] Zero warnings (if `-Werror` required)
- [ ] All tests pass
- [ ] Pre-commit hooks pass
- [ ] No new lint errors

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| ProjectOdyssey | `just test-timing` recipe authoring; PR #5351 | heredoc → printf fix |
| ProjectOdyssey | Build recipe fix; PR #5389 | silent no-op detection and explicit inclusion rewrite |
| ProjectScylla | PR #1081 — consolidate run subcommands | verify→fix→commit→PR workflow |
