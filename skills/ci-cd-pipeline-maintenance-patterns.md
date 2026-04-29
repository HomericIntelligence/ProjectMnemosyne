---
name: ci-cd-pipeline-maintenance-patterns
description: "Use when: (1) adding or auditing lint/format enforcement jobs to GitHub Actions workflows, (2) cross-repo conflict resolution on rename/refactor PRs, (3) CI-only crashes caused by debug_assert or JIT compilation overhead in Mojo, (4) enforcing required status checks across a GitHub organization, (5) triaging flaky CI failures to separate infrastructure issues from deterministic bugs, (6) fixing justfile build recipes that silently skip library validation, (7) standardizing default branches and fixing broken CI across multiple repos, (8) fixing pre-commit failures from mypy/ruff/coverage issues on cross-Python-version packages, (9) promoting monolithic CI matrix groups to per-subdirectory auto-discovery entries, (10) fixing CI workflows with missing pip dependency installs, (11) optimizing CI wall-clock time via runner pinning, changed-files-only pre-commit, and Dockerfile pixi copy"
category: ci-cd
date: 2026-04-28
version: "2.1.0"
user-invocable: false
verification: unverified
history: ci-cd-pipeline-maintenance-patterns.history
tags: []
---

# CI/CD Pipeline Maintenance Patterns

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-28 |
| **Objective** | Consolidated reference for common CI/CD maintenance patterns across the HomericIntelligence ecosystem |
| **Outcome** | Merged from 11 source skills covering linting, org-wide governance, Mojo JIT debugging, flaky test triage, build validation, and optimization |
| **Verification** | unverified |
| **History** | [changelog](./ci-cd-pipeline-maintenance-patterns.history) |

## When to Use

- Repository has ruff/lint rules but no CI enforcement, or pre-commit hooks can be bypassed
- A rename/refactor PR shows CONFLICTING merge state after main advances
- Tests pass locally but CI crashes with `execution crashed` / `libKGENCompilerRTShared.so` after adding `debug_assert` to `@always_inline` methods
- Multiple repos in an org lack branch protection or required status checks
- CI tests fail intermittently — some PRs pass, some fail with identical code
- A `just build` recipe silently excludes important source directories from compilation
- Repos have inconsistent default branch names (master vs main) and CI never triggers
- mypy reports `Unused "type: ignore"` on CI but the ignore is needed locally; or ruff/coverage failures after adding new modules
- A single CI matrix group covers multiple subdirectories via compound patterns and silently misses new files
- A GitHub Actions workflow fails with `ModuleNotFoundError` for a Python package
- CI is too slow: `ubuntu-latest` causes cache invalidation, pre-commit runs on all files, Dockerfile reinstalls dependencies

## Verified Workflow

### Quick Reference

```bash
# --- Ruff lint job: verify locally first ---
pixi run ruff check hephaestus scripts tests
pixi run ruff format --check hephaestus scripts tests
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/test.yml')); print('OK')"

# --- Cross-repo rename PR conflict resolution ---
git fetch origin && git checkout <branch> && git rebase origin/main
for f in $(git diff --name-only --diff-filter=U); do git checkout --theirs "$f" && git add "$f"; done
git rebase --continue
python3 scripts/validate_plugins.py
git push --force-with-lease
gh pr view <number> --json mergeStateStatus --jq '.mergeStateStatus'

# --- Diagnose Mojo CI-only crash (debug_assert + @always_inline) ---
grep -n "debug_assert" shared/tensor/any_tensor.mojo
grep -rn "\.load\[DType\.\|\.store\[DType\." shared/ --include="*.mojo" | wc -l

# --- Org-wide required checks audit ---
python3 scripts/audit_ci_status.py --runs 20
python3 scripts/enforce_required_checks.py --apply

# --- Flaky CI triage ---
gh run view <RUN_ID> --log-failed 2>&1 | grep -E "FAILED|execution crashed|error:|504|Cache not found" | head -40

# --- Justfile build validation ---
NATIVE=1 just check     # fast library type-check (no artifacts)
NATIVE=1 just ci-build  # full build: entry points + library packaging

# --- Branch rename (org-wide) ---
gh api --method POST repos/ORG/REPO/branches/master/rename --field new_name=main

# --- Pre-commit mypy fix: use importlib for version-dependent imports ---
# See detailed steps below

# --- Promote matrix subgroups ---
python3 scripts/validate_test_coverage.py

# --- Missing dependency in CI ---
grep -rl "script_name.py" .github/workflows/

# --- CI optimization: pin runners ---
for f in .github/workflows/*.yml; do sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"; done
grep -rc "ubuntu-latest" .github/workflows/*.yml | grep -v ":0"
```

### Adding a Ruff Lint Job to CI

1. Verify codebase passes lint locally before modifying CI. If violations exist, fix them first in a separate commit.
2. Add a separate `lint` job to the existing test workflow. Use a separate job (not a step) so it runs in parallel with independent failure reporting.
3. Use a shorter timeout for the lint job (10 minutes vs 30 for tests).
4. Add workflow-level hardening if not already present: `concurrency` group with `cancel-in-progress: true`, `permissions: contents: read`.

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.sha }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v6
      - name: Install pixi
        uses: prefix-dev/setup-pixi@v0.9.4
        with:
          pixi-version: v0.63.2
      - name: Cache pixi environments
        uses: actions/cache@v5
        with:
          path: |
            .pixi
            ~/.cache/rattler/cache
          key: pixi-${{ runner.os }}-${{ hashFiles('pixi.lock') }}
          restore-keys: |
            pixi-${{ runner.os }}-
      - name: Lint check
        run: pixi run ruff check hephaestus scripts tests
      - name: Format check
        run: pixi run ruff format --check hephaestus scripts tests
```

### Cross-Repo Rename PR Conflict Resolution

For rename/refactor PRs where all conflicts follow the same pattern (both sides changed the renamed text):

1. Fetch and rebase: `git fetch origin && git checkout <branch> && git rebase origin/main`
2. Check that all conflicts are homogeneous (same rename pattern): `git diff --name-only --diff-filter=U`
3. Batch-resolve with `--theirs` (the PR's renamed version):
   ```bash
   for f in $(git diff --name-only --diff-filter=U); do
     git checkout --theirs "$f" && git add "$f"
   done
   git rebase --continue
   ```
4. Validate repo integrity: `python3 scripts/validate_plugins.py`
5. Push and verify merge state: `git push --force-with-lease && gh pr view <number> --json mergeStateStatus --jq '.mergeStateStatus'`

For coordinating skill definition updates in a second repo after the rename, create an independent PR that references the original. Neither PR should block the other.

**Decision: When to use --theirs vs manual merge**
```text
Is the PR a rename/refactor where the intent is to change text references?
+-- YES: Are all conflicts in the renamed text (not structural changes)?
|   +-- YES -> Use --theirs for all conflicts (the rename IS the intent)
|   +-- NO  -> Manual merge for structural conflicts, --theirs for rename text
+-- NO -> Use standard conflict resolution (manual or --ours as appropriate)
```

### Diagnosing debug_assert JIT Compilation Overhead (Mojo)

When `debug_assert` is added to `@always_inline` methods and CI starts failing with mass `execution crashed`, but tests pass locally:

1. Count call sites that inline the modified method: `grep -rn "\.load\[DType\.\|\.store\[DType\." shared/ --include="*.mojo" | wc -l`
2. Compare failing jobs vs main's failing jobs — zero overlap means it's your regression
3. Distinguish from pre-existing failures: `gh api repos/<owner>/<repo>/actions/runs/<run_id>/jobs --jq '.jobs[] | select(.conclusion == "failure") | .name' | sort`
4. Fix: remove `debug_assert` from `@always_inline` methods. The method body becomes a pure pass-through:
   ```mojo
   @always_inline
   fn load[dtype: DType](self, index: Int) -> Scalar[dtype]:
       return self._data.bitcast[Scalar[dtype]]()[index]
   ```

**Why it works locally but fails in CI**: Fresh JIT cache + Docker container environment + concurrent compilation pressure pushes total compilation footprint past the internal JIT buffer overflow threshold. The crash signature is `libc.so.6+0x45330` (fortify_fail_abort).

### Org-Wide Required Status Checks Enforcement

1. **Audit all repos** (read-only): `python3 scripts/audit_ci_status.py --runs 20`
2. **Dry-run**: `python3 scripts/enforce_required_checks.py`
3. **Apply incrementally** — start with safest repo: `python3 scripts/enforce_required_checks.py --apply --repo ProjectScylla`
4. **Apply all**: `python3 scripts/enforce_required_checks.py --apply`
5. **Verify**: `python3 scripts/audit_ci_status.py --runs 5`

Key filtering rules for which jobs qualify as required checks:
- Minimum 3 executed runs (not skipped/cancelled)
- 100% pass rate
- Workflow triggers on `pull_request`
- No `paths:` filter on `pull_request` trigger (path-filtered jobs don't run on every PR)
- Exclude GitHub-automated jobs (Dependabot, CodeQL `Analyze` jobs)

GitHub API patterns:
```bash
# Repo has existing required checks (PATCH replaces entire list)
gh api --method PATCH repos/ORG/REPO/branches/BRANCH/protection/required_status_checks \
  --input - <<< '{"strict":false,"contexts":["existing","new-check"]}'

# Repo has no protection (PUT with full body)
gh api --method PUT repos/ORG/REPO/branches/BRANCH/protection \
  --input - <<< '{"required_status_checks":{"strict":false,"contexts":["check"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}'
```

### Flaky CI Root Cause Triage

For each failing test, classify into exactly one bucket before attempting any fix:

| Bucket | Signature | Action |
|--------|-----------|--------|
| **Infrastructure** | `504 Gateway Time-out`, `Cache not found`, container build failure | Fix CI config |
| **Deterministic bug** | `failed to parse`, `error:` with line number, assertion failure | Fix code |
| **Genuine JIT flake** | `execution crashed` with `libKGENCompilerRTShared.so`, NO test output before crash | Upstream Mojo bug |

```bash
# Full triage of a failed CI run
RUN_ID=<your-run-id>
gh run view $RUN_ID --log-failed 2>&1 | grep "❌ FAILED" | sort -u
gh run view $RUN_ID --log-failed 2>&1 | grep -E "504|Cache not found|Gateway" | head -5
gh run view $RUN_ID --log-failed 2>&1 | grep -E "failed to parse|error:.*line" | head -10
gh run view $RUN_ID --log-failed 2>&1 | grep "execution crashed" | head -5
```

**Docker Hub Thundering Herd fix** (replace Podman storage cache with image tar cache):
```yaml
- name: Cache container image tar
  uses: actions/cache@v5
  with:
    path: /tmp/podman-image-cache
    key: container-image-${{ hashFiles('Dockerfile', 'pixi.toml', 'pixi.lock') }}

- name: Load cached image or build
  run: |
    if [ -f /tmp/podman-image-cache/dev.tar ]; then
      podman load -i /tmp/podman-image-cache/dev.tar
    else
      podman compose build projectodyssey-dev
      mkdir -p /tmp/podman-image-cache
      podman save -o /tmp/podman-image-cache/dev.tar projectodyssey:dev
    fi
```

**Mojo syntax fixes for deterministic bugs**:
```mojo
# f-strings in function call arguments (parse error in Mojo)
# WRONG: assert_value_at(t, i, 1.0, message=f"t[{i}] should be 1.0")
# CORRECT:
assert_value_at(t, i, 1.0, message="t[" + String(i) + "] should be 1.0")

# Tuple destructuring (unknown declaration error)
# WRONG: var (a, b, c) = fn_returning_tuple()
# CORRECT:
var result = fn_returning_tuple()
var a = result[0]; var b = result[1]; var c = result[2]
```

### Justfile Build Validation Gaps

When `mojo build` is used for library code but library modules have no `fn main()`:

1. Fill empty `ci-build` recipe to run both entry-point compilation and library packaging:
   ```just
   ci-build:
       @just build ci
       @just package ci
   ```
2. Add `just check` recipe for fast developer feedback:
   ```just
   check:
       @just _run "just _check-inner"

   [private]
   _check-inner:
       #!/usr/bin/env bash
       set -euo pipefail
       REPO_ROOT="$(pwd)"
       OUT=$(mktemp -d)
       trap "rm -rf $OUT" EXIT
       pixi run mojo package --Werror -I "$REPO_ROOT" shared -o "$OUT/shared.mojopkg"
   ```
3. Update `validate` to delegate to `ci-build` — single source of truth.
4. Replace inline `mojo package` commands in CI YAML with `NATIVE=1 just ci-build`.

| Command | Requires main()? | Use For |
|---------|-------------------|---------|
| `mojo build` | Yes | Entry point binaries |
| `mojo package` | No | Library validation |

### Org-Wide Branch Rename and CI Fix

1. Identify repos needing rename:
   ```bash
   for repo in $(gh repo list ORG --no-archived --json name --jq '.[].name'); do
     branch=$(gh api repos/ORG/$repo --jq '.default_branch')
     if [ "$branch" != "main" ]; then echo "RENAME: $repo ($branch -> main)"; fi
   done
   ```
2. Rename via API (atomically updates default branch, PRs, and protection rules):
   ```bash
   gh api --method POST repos/ORG/REPO/branches/master/rename --field new_name=main
   ```
3. Fix self-hosted runner issues by switching to `ubuntu-latest` in workflow YAML.
4. Fix common broken workflow configs: remove invalid Semgrep `generateSarif: true` parameter; add `continue-on-error: true` to advisory security scans.
5. Re-audit and enforce: `python3 scripts/audit_ci_status.py --runs 20 --min-runs 1 && python3 scripts/enforce_required_checks.py --apply --remove-failing`

Use 4 worktree-isolated parallel agents for CI fixes across repos:
```python
Agent(isolation="worktree", run_in_background=True, prompt="Fix REPO CI...")
```

### Pre-Commit mypy / ruff / Coverage Fixes (Cross-Python-Version)

**mypy unused-ignore on version-dependent imports**: Use `importlib.import_module()` instead of `try/except import` with `type: ignore` comments:

```python
# WRONG: type:ignore breaks on Python 3.12 CI (tomllib in stdlib) but needed on 3.10
try:
    import tomllib  # type: ignore[no-redef]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

# CORRECT: importlib avoids all type:ignore issues
import importlib
tomllib = None
for _mod_name in ("tomllib", "tomli"):
    try:
        tomllib = importlib.import_module(_mod_name)
        break
    except ModuleNotFoundError:
        continue
```

**Fix ruff issues in order**:
```bash
pixi run ruff format hephaestus/ tests/          # 1. Format first
pixi run ruff check . --select=F401,I001 --fix   # 2. Unused imports + sorting
pixi run ruff check . --select=RUF059 --fix --unsafe-fixes  # 3. Unused unpacked vars
pixi run ruff check . --select=C901              # 4. Check complexity manually
```

**Coverage gaps from main() functions** — add tests that monkeypatch `sys.argv`:
```python
class TestMain:
    def test_clean_returns_zero(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.argv", ["cmd", "--repo-root", str(tmp_path)])
        assert main() == 0

    def test_stdin_input(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["cmd"])
        monkeypatch.setattr("sys.stdin", io.StringIO('{"data": []}'))
        assert main() == 0
```

Other ruff rules: N817 (CamelCase as acronym — rename `ET` to `ElementTree`); D301 (backslashes in docstrings — use `r"""`); SIM102 (collapse nested `if`).

### Promoting CI Matrix Subgroups for Auto-Discovery

Replace a monolithic CI matrix entry that uses compound patterns with per-subdirectory entries:

```yaml
# BEFORE (1 group — silently misses new subdirectory files)
- name: "Data"
  path: "tests/shared/data"
  pattern: "test_*.mojo datasets/test_*.mojo samplers/test_*.mojo transforms/test_*.mojo"

# AFTER (6 groups — each subdirectory auto-discovers test_*.mojo)
- name: "Data Core"
  path: "tests/shared/data"
  pattern: "test_*.mojo"
  continue-on-error: true
- name: "Data Datasets"
  path: "tests/shared/data/datasets"
  pattern: "test_*.mojo"
  continue-on-error: true
# ... one entry per subdirectory
```

Key insight: `Path.glob("dir/test_*.mojo")` is non-recursive — parent and subdirectory entries never overlap. Validate after editing: `python3 scripts/validate_test_coverage.py`.

### Missing Dependency in CI Workflow

1. Identify failure: `gh run list --branch main --limit 5` then `gh run view <run-id> --log-failed`
2. Find root cause: look for `ModuleNotFoundError` and the missing package name
3. Check sibling workflows: `grep -rl "script_name.py" .github/workflows/` — they likely already install the dependency
4. Add install step between "Set up Python" and the script execution step:
   ```yaml
   - name: Install dependencies
     run: pip install <missing-package>
   ```
5. Submit via PR — do NOT commit regenerated output files alongside the fix.

### CI Optimization (Runner Pinning, Changed-Files Pre-commit, Dockerfile)

**Pin all runners to avoid cache invalidation**:
```bash
for f in .github/workflows/*.yml; do
  sed -i 's/runs-on: ubuntu-latest/runs-on: ubuntu-24.04/g' "$f"
done
grep -rc "ubuntu-latest" .github/workflows/*.yml | grep -v ":0"  # Should be empty
```

**Changed-files-only pre-commit for PRs**:
```yaml
- name: Run pre-commit hooks
  env:
    EVENT_NAME: ${{ github.event_name }}
    BASE_REF: ${{ github.base_ref }}
  run: |
    if [ "$EVENT_NAME" = "pull_request" ]; then
      git fetch origin "$BASE_REF" --depth=1
      SKIP=mojo-format pixi run pre-commit run --from-ref "origin/$BASE_REF" --to-ref HEAD --show-diff-on-failure
    else
      SKIP=mojo-format pixi run pre-commit run --all-files --show-diff-on-failure
    fi
```

Always use `env:` to capture `github.event_name` and `github.base_ref` — never inline `${{ }}` expressions in `run:` commands (workflow injection security check).

**Dockerfile multi-stage: copy .pixi instead of reinstalling**:
```dockerfile
# Runtime stage — copy from builder, don't reinstall
COPY --from=builder /root/.pixi /root/.pixi
COPY --from=builder /build/.pixi /app/.pixi
COPY pixi.toml pixi.lock ./
# Remove curl from apt-get (no longer needed for pixi installer)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Adding lint as a step in the test job | Considered adding ruff as a step inside existing test matrix | Would run redundantly for each matrix entry; couples lint to test failures | Use a separate job — runs once, in parallel, with independent failure reporting |
| Protecting branch "main" when default was "master" | Earlier enforcement script assumed all repos use `main` | GitHub API returned 404 "Branch not found" for repos with `master` default | Always detect actual default branch via API; never assume "main" |
| `gh api --jq` with `parse_json=True` | Used `parse_json=True` when `--jq` extracts a scalar | `json.loads("master")` fails; wrong branch for 5 repos | When `--jq` extracts a scalar, use `parse_json=False` — output is plain text, not JSON |
| Including Dependabot/CodeQL jobs as required checks | Initial audit recommended `Analyze (actions)`, `Dependabot` | These are GitHub-automated jobs that don't run on every PR | Filter out automated job names; requiring them would block all PRs |
| `min-runs=1` for all repos | Lowered threshold to include repos with limited CI history | Included 19+ jobs with only 1 run (benchmarks, container builds) — too aggressive | Keep `min-runs=3`; jobs that only ran once are likely scheduled/manual, not PR-triggered |
| Including path-filtered workflows as required checks | Shell Tests (`bats`) passes 100% but triggers only on `**/*.sh` | PRs not touching `.sh` files would never get the check and be blocked forever | Detect `paths:` filter in workflow YAML; exclude those jobs from required checks |
| Assumed all CI failures were JIT flakes | Investigated `libKGENCompilerRTShared.so` crashes as the sole root cause | Only 1 of 4 failing tests was actually a JIT crash; rest were parse errors and a logic bug | Always read actual CI error output — classify each failure individually |
| Assumed debug_assert was broken in JIT | Created self-contained reproducer with 2 call sites | Reproducer PASSED — debug_assert works fine in isolation | The issue isn't debug_assert itself; it's cumulative inlining overhead at 100+ call sites |
| Relied on Podman storage cache | Cached `~/.local/share/containers` keyed on Dockerfile hash | Podman storage directory exceeded 10 GB cache limit — tar save always failed silently | Image tar cache (`podman save/load`) is much smaller and stays under the limit |
| Retry logic to handle JIT crashes | `run_test_group.sh` had 3-attempt retry with exponential backoff | Retry masked real deterministic failures | Retry is a workaround, not a fix; remove it to make all failures immediately visible |
| Include shared/ in `_build-inner` find for mojo build | Added shared/ .mojo files to the `mojo build` loop | `mojo build` requires `fn main()` — library modules don't have one | Library code must be validated with `mojo package`, not `mojo build` |
| `type: ignore[no-redef]` on tomllib import | Added type:ignore to suppress mypy on tomli fallback | CI runs Python 3.12 where tomllib exists, so mypy flags the ignore as unused | Use `importlib.import_module()` — zero type annotations needed |
| RUF059 rename then forget references | Renamed `versions` to `_versions` but left `assert versions == {}` on next line | F821 undefined name | After any RUF059 rename, grep for remaining references to the old name |
| Format after lint fix | Fixed lint issues then expected format to be clean | Lint fixes can change formatting | Always run format AFTER lint fixes |
| Leave original test file after adding glob-covered parts | Keep `test_elementwise.mojo` alongside split parts | `validate_test_coverage.py` reports original as "uncovered" | Original must be deleted; split files fully replace it |
| Inline `${{ github.event_name }}` in `run:` | Used expression directly in shell | Pre-commit security hook blocked the edit (workflow injection risk) | Always use `env:` block even for non-sensitive context values |
| Glob tool for .github/workflows files | Used Glob with `.github/workflows/*.yml` | Glob doesn't match hidden directories | Use Bash or full paths instead |
| `workflow_dispatch` to trigger CI on Keystone | Triggered CI via `gh workflow run` to get fresh failure logs | Job cancelled during provisioning | Workflow dispatch may be cancelled by concurrency settings; use push-triggered runs |
| pre-commit actionlint rev set to commit SHA | Set `rev: 5408c5b...` (a full commit SHA) in `.pre-commit-config.yaml` for the `rhysd/actionlint` pre-commit hook | pre-commit `rev` field must be a **git tag** (or branch), not a bare commit SHA. `git checkout <SHA>` on the hook repo fails with `fatal: unable to read tree` because pre-commit uses the rev to fetch the repo at that ref and a SHA alone is not a fetchable ref in all git server configurations. | Always use a tag (e.g. `v1.7.7`) in the `rev:` field of `.pre-commit-config.yaml`. If a hook repo doesn't publish tags, use the tag-annotated format or pin to a branch. Never use a bare commit SHA. |
| aquasecurity/trivy-action@0.30.0 in GitHub Actions | Used `uses: aquasecurity/trivy-action@0.30.0` for filesystem vulnerability scanning | The action fails at "Set up job" — the action appears withdrawn or broken at this tag (GitHub runner can't download/initialize the action). Error appears before any user code runs. | Replace with direct trivy binary install: `curl -sSfL "${base}/v${TV_VER}/trivy_${TV_VER}_Linux-64bit.tar.gz" \| tar -xz -C /usr/local/bin trivy && trivy fs --severity HIGH,CRITICAL --exit-code 0 .`. Keep the scan non-blocking (`--exit-code 0 \|\| true`) for informational posture. Put the version in an env var to keep the URL under 80 chars for yamllint. |

## Results & Parameters

### Ruff Lint Job Parameters

| Decision | Rationale |
|----------|-----------|
| Separate job (not step) | Parallel execution, clearer failure attribution |
| 10-minute timeout | Lint is fast; 30 minutes is wasteful |
| No `setup-python` in lint job | Pixi manages Python; redundant with `setup-pixi` |
| Simpler cache key | No matrix dimensions to vary |

### Org-Wide CI Governance Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `--runs` | 10 | Number of recent runs to analyze per repo |
| `--min-runs` | 3 | Minimum executed runs for a job to qualify |
| `--min-pass-rate` | 1.0 | Required pass rate (1.0 = 100%) |
| `--include-path-filtered` | false | Include path-filtered jobs (risky) |

### Flaky CI Classification Statistics

| Metric | From ProjectOdyssey PR #5097 |
|--------|------------------------------|
| Total CI failures investigated | 4 unique test files |
| Infrastructure failures | 1 (Docker 504) |
| Deterministic code bugs | 3 (parse errors + logic bug) |
| Genuine JIT flakes | 1 |
| "Flaky" that were actually deterministic | 75% |

### Mojo JIT Threshold Model

The Mojo JIT compiler has an internal buffer that overflows after enough code is compiled. `debug_assert` in 3 `@always_inline` methods × 100+ call sites = significant overhead. Whether a specific test crashes depends on: (1) how much the test imports, (2) how many `@always_inline` methods are instantiated, (3) JIT cache state (fresh in CI, warm locally), (4) memory layout.

### Pre-commit Fix Iteration Pattern (Cross-Python-Version)

```
Iteration 1: Fix format + unused imports + mypy type:ignore + C901 + coverage
Iteration 2: Fix remaining RUF059 + F821 from variable renames
Iteration 3: Fix importlib approach for tomllib + D301 + SIM102 + E501
```

### Rollback for Required Checks

```bash
# Manual rollback for a single repo
gh api --method PATCH repos/ORG/REPO/branches/BRANCH/protection/required_status_checks \
  --input - <<< '{"strict":false,"contexts":["original","checks","only"]}'

# Remove branch protection entirely
gh api --method DELETE repos/ORG/REPO/branches/BRANCH/protection
```
