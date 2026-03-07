# Session Notes: ban-matmul-call-sites

## Context

- **Date**: 2026-03-07
- **Project**: HomericIntelligence/ProjectOdyssey
- **Issue**: #3215 — "Add pre-commit hook or CI check to ban __matmul__ call sites"
- **Follow-up from**: #3112 (codebase standardized on `matmul(A, B)`)
- **Branch**: `3215-auto-impl`
- **PR**: #3733

## What Was Implemented

### `.pre-commit-config.yaml`

Added `no-matmul-call-sites` hook in the first `local` repo block (alongside `mojo-format` and
`check-list-constructor`):

```yaml
- id: no-matmul-call-sites
  name: Enforce no .__matmul__() call sites
  description: Ban .__matmul__( call sites in Mojo files (use matmul(A, B) instead). Ref #3215
  entry: bash -c 'violations=$(grep -rn "\.__matmul__(" . --include="*.mojo" --exclude-dir=".pixi" --exclude-dir=".git" | grep -v "fn __matmul__(" | grep -v "# __matmul__" | grep -v "__matmul__.*deprecated"); if [ -n "$violations" ]; then echo "Found .__matmul__() call sites (use matmul(A, B) instead):"; echo "$violations"; exit 1; fi'
  language: system
  pass_filenames: false
  always_run: true
```

### `.github/workflows/pre-commit.yml`

Added step after `Run pre-commit hooks`:

```yaml
- name: Enforce no .__matmul__() call sites
  run: |
    violations=$(grep -rn "\.__matmul__(" . --include="*.mojo" --exclude-dir=".pixi" --exclude-dir=".git" | grep -v "fn __matmul__(" | grep -v "# __matmul__" | grep -v "__matmul__.*deprecated")
    if [ -n "$violations" ]; then
      echo "::error::Found .__matmul__() call site(s). Use matmul(A, B) instead."
      echo "$violations"
      exit 1
    fi
    echo "No .__matmul__() call sites found."
```

## Verification Commands Run

```bash
# Baseline check — confirmed zero violations
violations=$(grep -rn "\.__matmul__(" . --include="*.mojo" --exclude-dir=".pixi" --exclude-dir=".git" \
  | grep -v "fn __matmul__(" | grep -v "# __matmul__" | grep -v "__matmul__.*deprecated")
# result: empty (clean)

# Positive test — confirmed hook catches violations
echo "var a.__matmul__(b)" > /tmp/test_matmul.mojo
grep -n "\.__matmul__(" /tmp/test_matmul.mojo | grep -v "fn __matmul__("
# result: 1:var a.__matmul__(b)

# Negative test — confirmed definitions are excluded
echo "fn __matmul__(self, rhs: Self) -> Self:" > /tmp/test_def.mojo
grep -n "\.__matmul__(" /tmp/test_def.mojo | grep -v "fn __matmul__("
# result: empty (correctly excluded)
```

## Pre-commit Hook Run Output on Commit

```
Mojo Format..........................................(no files to check)Skipped
Check for deprecated List[Type](args) syntax.........(no files to check)Skipped
Enforce no .__matmul__() call sites......................................Passed
Bandit Security Scan.................................(no files to check)Skipped
...
[3215-auto-impl 3186921e] feat(lint): ban .__matmul__() call sites via pre-commit hook and CI
 2 files changed, 17 insertions(+)
```

## Existing Pattern in Codebase (Precedent)

The existing `check-list-constructor` hook used `language: pygrep` which works for simple pattern
matching. This session established that `language: system` with `bash -c` is needed when exclusion
filters (`grep -v`) are required.
