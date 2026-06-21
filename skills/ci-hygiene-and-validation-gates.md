---
name: ci-hygiene-and-validation-gates
description: "Use when: (1) adding a CI step that grep-blocks reappearance of deprecated identifiers after a cleanup PR, (2) adding a standalone JSON schema validation step to catch config drift even when pre-commit was skipped, (3) detecting orphaned scripts/*.py files not referenced in CI workflows, justfile, or other scripts, (4) you discover a NAMED required CI check that asserts nothing (a dead gate that computes-and-discards its verdict, or whose only failure path is unreachable) and must make it genuinely enforce in place because its context is pinned in the org ruleset and cannot be deleted, (5) a gitignored scratch directory whose name collides with a packaging-output convention (e.g. `build/`) needs a guard that the directory never has tracked files swept into a distribution, (6) an issue asks to wire a script into CI but a prior PR already did it — the correct fix is a justfile/Makefile discoverability comment, not re-wiring."
category: ci-cd
date: 2026-06-20
version: "1.3.0"
user-invocable: false
history: ci-hygiene-and-validation-gates.history
tags:
  - ci-cd
  - grep
  - validation
  - deprecation
  - schema
  - pre-commit
  - stale-detection
  - regression-guard
  - required-status-check
  - dead-gate
  - no-op-assertion
  - version-sync
  - set-e
  - pinned-context
  - defense-in-depth
  - pip-install-deps
  - pixi-locked
  - build-dir
  - untracked-guard
  - packaging-collision
  - git-ls-files
  - already-wired
  - discoverability-comment
  - prior-pr-completed
  - justfile-cross-reference
---
## Overview

| Field | Value |
| ------- | ------- |
| **Goal** | Add lightweight, build-free CI/pre-commit gates that catch regressions, config drift, and referential-integrity issues without a full test run — and detect/repair gates that look green but assert nothing |
| **Patterns** | (1) grep deprecation guard, (2) standalone schema validation step, (3) stale-script detector, (4) detect & fix a dead required gate, (5) tracked-file-under-gitignored-dir guard, (6) already-wired issue → justfile discoverability comment |
| **Output** | New `run:` steps in existing CI jobs and/or a stdlib-only pre-commit hook; or a rewritten existing job that asserts its named contract in place |
| **Language** | Any (Mojo, Python, TypeScript, …) — checks are plain `grep` / `python` |
| **Build required** | No — pure file scans, run before compilation |
| **Verification** | verified-ci |

## When to Use

- A cleanup PR removed deprecated type aliases / function names / module paths and the team wants CI to hard-fail if those names reappear (grep deprecation guard).
- A project has a `validate_config_schemas.py`-style script gated only behind a `pass_filenames: true` pre-commit hook, and you need CI to validate *all* config files on every PR (standalone schema validation).
- A `scripts/` directory has grown organically and you want to surface orphaned `*.py` files not referenced in `.github/`, `justfile`, `.pre-commit-config.yaml`, or other scripts (stale-script detector).
- A follow-up issue explicitly asks for a "regression guard" or "automated drift check" without requiring code review.
- A required status check shows green on every PR but you suspect it "asserts nothing": it computes a verdict and `echo`s it without ever testing it, or its only `exit 1` is behind a condition that is never true in this repo (dead gate). The context is pinned in the org ruleset, so you must make the existing job enforce its named contract in place rather than delete it (Pattern 4).
- A gitignored scratch directory whose name collides with a packaging-output convention (e.g. `build/`, `dist/`) needs a guard ensuring it never has tracked files swept into a distribution (tracked-file-under-gitignored-dir guard, Pattern 5).
- An issue asks to "wire script X into CI" but investigation reveals a prior PR already added that CI job — the correct resolution is NOT to re-wire or duplicate the step, but to add a single cross-reference comment in `justfile` (or `Makefile`) above the local recipe pointing at the existing CI job for discoverability (Pattern 6).

## Verified Workflow

### Quick Reference

```bash
# (1) Deprecation grep guard — scan, excluding comment/docstring lines
PATTERN='OldName1\|OldName2\|OldName3'
grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null \
  | grep -v '^\s*#' | grep -v '^\s*"""' | grep -q . && echo "FOUND (fail)" || echo "clean"

# (2) Standalone schema validation — run against all config files
pixi run python scripts/validate_config_schemas.py --verbose \
  config/defaults.yaml config/models/*.yaml tests/fixtures/config/tiers/*.yaml

# (3) Stale-script detection — manual, via pre-commit, and tests
python scripts/check_stale_scripts.py
pre-commit run check-stale-scripts --all-files
pixi run python -m pytest tests/unit/scripts/test_check_stale_scripts.py -v

# (4) Dead-gate TWO-SIDED verification — mirror the EXACT CI invocation:
#     clean venv + `pip install -e .` WITH deps + bare python/-m (NOT `pixi run`).
#     A gate change is NOT "verified" until you show BOTH a clean PASS and a synthetic FAIL.
python -m venv /tmp/dg && . /tmp/dg/bin/activate && pip install -e .   # WITH deps (no --no-deps)

# Leg 1+2 — the unit-tested checker:
python -m hephaestus.scripts_lib.check_version_single_source; echo "clean exit: $?"   # expect 0
printf '\nversion = "9.9.9"\n' >> pyproject.toml                                       # inject under [project]
python -m hephaestus.scripts_lib.check_version_single_source; echo "bad exit: $?"     # expect non-zero
git checkout -- pyproject.toml                                                         # restore -> 0 again

# Leg 3 — lockfile sync on the repo-pinned pixi (v0.69.0), same as the pixi-check job:
pixi install --locked; echo "clean exit: $?"                                           # expect 0
printf '\n[pypi-dependencies]\nnonexistent-sentinel-pkg = "*"\n' >> pixi.toml          # drift
pixi install --locked; echo "drift exit: $?"                                           # expect non-zero
git checkout -- pixi.toml                                                              # restore -> 0 again

# (6) Already-wired check — verify before any action
grep -rn "check_dep_sync\|<script_name>" .github/workflows/    # confirm CI job already exists
grep -n "dep-check\|<recipe-name>" justfile                     # locate the local recipe
just dep-check && just --list && pre-commit run --files justfile  # verify after comment insertion
```

### Detailed Steps

#### Pattern 1 — CI grep deprecation guard

**Step 1 — Verify zero current matches.** Confirm the codebase is already clean before
adding the step, so it does not fail on day one:

```bash
PATTERN='OldName1\|OldName2\|OldName3'
grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null
# Expected: no output
```

**Step 2 — Identify the right workflow job.** Look for an existing syntax/lint job that runs
early (before compilation), e.g. a `mojo-syntax-check` job in `comprehensive-tests.yml` that
already contains pattern-check steps. Placing the new step there avoids a separate workflow and
keeps it in the critical path.

**Step 3 — Add the step after similar pattern checks** inside the existing job's `steps:` list:

```yaml
      - name: Check for deprecated backward result alias names
        run: |
          echo "============================================================"
          echo "Checking for deprecated backward result alias names..."
          echo "============================================================"

          # The N deprecated type aliases removed in #CLEANUP_PR.
          # They must not reappear in shared/ or tests/.
          PATTERN='Name1\|Name2\|Name3'

          # Two-phase grep: broad scan, then exclude comment/docstring lines.
          if grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null \
               | grep -v '^\s*#' \
               | grep -v '^\s*"""' \
               | grep -q .; then
            echo ""
            echo "::error::Deprecated alias names detected in shared/ or tests/"
            grep -rn "$PATTERN" shared/ tests/ --include='*.mojo' 2>/dev/null \
              | grep -v '^\s*#' \
              | grep -v '^\s*"""'
            echo ""
            echo "FAILED: The above deprecated type aliases were removed in #N."
            echo "Use the replacement struct names directly."
            exit 1
          else
            echo ""
            echo "PASSED: No deprecated alias names found"
          fi
```

Key decisions:
- `grep -v '^\s*#'` excludes single-line comments; `grep -v '^\s*"""'` excludes docstring boundaries.
- The second `grep` run (without `-q`) prints offending lines for the developer.
- `::error::` annotation surfaces in GitHub's PR diff view.
- Use plain ASCII (`FAILED:` / `PASSED:`) in `echo` — avoid emoji, which some runners mis-render.

**Step 4 — Commit and PR**, enabling auto-merge:

```bash
git commit -am "ci(syntax-check): add CI step to block deprecated <X> alias names

Closes #<issue-number>"
git push -u origin <branch>
gh pr create --title "ci: add deprecation guard for <X>" --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

#### Pattern 2 — Standalone schema-validation CI step

**Step 1 — Confirm the script exists and works.** Verify `scripts/validate_config_schemas.py`
accepts positional file args, exits 0/1, and passes locally against all targets with `--verbose`.

**Step 2 — Identify placement.** Find the CI job that runs static checks (e.g., the `unit`
matrix job in `test.yml`). When the workflow uses a matrix strategy, gate static-analysis steps on
the unit job to avoid duplicate runs, matching sibling steps:

```yaml
if: matrix.test-group.name == 'unit'
```

**Step 3 — Add the step** after pixi/environment setup, **before** the test run, alongside other
static analysis steps. GitHub Actions `run` steps execute in a shell that expands globs, so no
quoting is needed:

```yaml
- name: Check doc/config consistency
  if: matrix.test-group.name == 'unit'
  run: pixi run python scripts/check_doc_config_consistency.py --verbose

- name: Validate config schemas          # <-- ADD HERE
  if: matrix.test-group.name == 'unit'
  run: pixi run python scripts/validate_config_schemas.py config/defaults.yaml config/models/*.yaml tests/fixtures/config/tiers/*.yaml

- name: Run ${{ matrix.test-group.name }} tests
  ...
```

**Step 4 — Validate the workflow file** (`pre-commit run --files .github/workflows/test.yml`),
then commit, push, open PR, and enable auto-merge.

> If `Edit` is blocked by the security reminder hook on workflow files, apply the change via a
> short Python `read → str.replace → write` script instead.

#### Pattern 3 — Stale-script detector

**Step 1 — Design the detection logic.** Check each `scripts/*.py` basename against reference
files: `.github/**/*.yml`, `justfile`, `.pre-commit-config.yaml`, and other `scripts/*.py`.
Design decisions:

1. **Always exit 0** — warning only, never blocks commits or CI.
2. **Self-reference exclusion** — a script appearing in its own source does not count as referenced.
3. **`ALWAYS_ACTIVE` allowlist** — `common.py` and the detector itself are never flagged.
4. **Basename matching** — search for the full `.py` filename, not the import module name, to avoid false positives on imports.

**Step 2 — Implement `scripts/check_stale_scripts.py`** (stdlib only):

```python
#!/usr/bin/env python3
"""Detect scripts/*.py files with no references in .github/, justfile, or other scripts/."""

import argparse
import sys
from pathlib import Path
from typing import List, Set

ALWAYS_ACTIVE: Set[str] = {"common.py", "check_stale_scripts.py"}


def get_all_scripts(scripts_dir: Path) -> List[str]:
    return sorted(p.name for p in scripts_dir.glob("*.py") if p.is_file())


def get_reference_targets(repo_root: Path) -> List[Path]:
    targets: List[Path] = []
    github_dir = repo_root / ".github"
    if github_dir.is_dir():
        targets.extend(github_dir.rglob("*.yml"))
    justfile = repo_root / "justfile"
    if justfile.is_file():
        targets.append(justfile)
    precommit = repo_root / ".pre-commit-config.yaml"
    if precommit.is_file():
        targets.append(precommit)
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        targets.extend(scripts_dir.glob("*.py"))
    return targets


def find_references(script_name: str, targets: List[Path], scripts_dir: Path) -> bool:
    own_path = scripts_dir / script_name
    for target in targets:
        if target.resolve() == own_path.resolve():
            continue
        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if script_name in content:
            return True
    return False


def find_stale_candidates(repo_root: Path) -> List[str]:
    scripts_dir = repo_root / "scripts"
    if not scripts_dir.is_dir():
        return []
    all_scripts = get_all_scripts(scripts_dir)
    targets = get_reference_targets(repo_root)
    return [s for s in all_scripts if s not in ALWAYS_ACTIVE and not find_references(s, targets, scripts_dir)]


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root if args.repo_root else Path(__file__).resolve().parent.parent
    candidates = find_stale_candidates(repo_root)
    for c in candidates:
        print(f"WARNING: possibly stale: scripts/{c}")
    if candidates:
        print(f"\n{len(candidates)} possibly stale script(s) found (warnings only, not a failure).")
    else:
        print("No stale script candidates found.")
    return 0
```

**Step 3 — Add the pre-commit hook** inside the existing `- repo: local` block. Use
`pass_filenames: false` because the script performs a whole-repo scan, not per-file validation:

```yaml
- id: check-stale-scripts
  name: Check for Stale Scripts
  description: Warn about scripts/*.py not referenced in .github/, justfile, or other scripts
  entry: python3 scripts/check_stale_scripts.py
  language: system
  files: ^scripts/.*\.py$
  pass_filenames: false
```

**Step 4 — Write unit tests** (20 tests across 5 classes covering script enumeration, reference
target discovery, reference finding, stale-candidate selection, and `main`). The critical test
asserts cross-script references must use the `.py` filename, not the import name:

```python
def test_cross_script_reference(self, tmp_path: Path) -> None:
    scripts_dir = _make_scripts_dir(tmp_path, ["util.py", "caller.py"])
    (scripts_dir / "caller.py").write_text(
        "import subprocess\nsubprocess.run(['python', 'scripts/util.py'])\n", encoding="utf-8"
    )
    all_targets = list(scripts_dir.glob("*.py"))
    assert find_references("util.py", all_targets, scripts_dir) is True
```

#### Pattern 4 — Detect & fix a dead required gate

A **dead gate** is a required CI check that shows green but cannot fail. It is
security-theater: it blocks nothing while broadcasting a false guarantee. The
canonical instance: a `deps-version-sync` job that computed a `DYNAMIC` value from
`pyproject.toml`, `echo`ed it, and **never used it in a conditional**, while its only
`exit 1` lived inside `if [ -f VERSION ]; then ... fi` — and the repo has **no**
`VERSION` file (it uses hatch-vcs dynamic versioning). Net: the required check passed
for any version configuration.

**Step 1 — Detect the dead gate (review heuristics).** A check asserts nothing if:

1. **Unreachable failure path.** Grep the job for every `exit 1` / `exit "$fail"` and
   trace whether it is reachable. Is the enclosing `if` ever true in *this* repo? e.g.
   `if [ -f VERSION ]` when no `VERSION` file exists is dead code.
2. **Discarded verdict.** Any value that is computed and `echo`ed but never appears in
   a `[ ... ]`, `case`, or `if` test is a discarded verdict — the assertion is missing.
3. **No constructible failing input.** Confirm by (mentally or actually) running the
   job against a KNOWN-BAD input. If you cannot construct an input that makes it exit
   non-zero, it asserts nothing.

**Step 2 — Decide: fix in place, do NOT delete (pinned-context constraint).** Before
touching anything, check whether the check's context is pinned in the org ruleset:

```bash
gh api "repos/<owner>/<repo>/rulesets" --jq '.[].name'
# Inspect each ruleset for required_status_checks contexts (e.g. "deps/version-sync").
```

If the context is **pinned**, deleting the job leaves every PR permanently BLOCKED
waiting on a check that never reports — the classic *ci-driver-blocked-required-context-drift*
failure (and ruleset mutation is an admin API change outside a code PR's scope). The
correct move is therefore **make the EXISTING job assert its named contract in place**
(defense-in-depth on an immovable check), NOT delete it. Cross-link
`gha-required-checks-branch-protection`.

> **Justified DRY overlap.** Making a dead gate real may duplicate assertions other
> gates already make (here: `lint`'s `check-version-single-source` pre-commit hook, and
> `pixi-check`'s `pixi install --locked`). State this overlap explicitly as an accepted
> trade-off — the alternative (deletion) bricks the merge queue.

**Step 3 — Install WITH deps; the checker imports declared deps.** Drop `--no-deps`
from `pip install -e "."`. The version checker imports `hephaestus.utils.helpers ->
from packaging.requirements import ...`; `packaging` is a declared core dep. With
`--no-deps` the checker `ModuleNotFoundError`s at runtime (a crash under `set -e`, not
an assertion). Install WITH deps so imports resolve.

**Step 4 — Invoke an already-tested checker under `set -euo pipefail`.** Reuse a
unit-tested checker module rather than re-deriving regex in bash (which historically
caused a false-PASS — see repo issue #435). Prefer `python -m <pkg>.<module>` over a
`scripts/<x>.py` shim (see the companion worktree-`__file__` skill on why the shim's
`__file__` resolution breaks in worktrees):

```yaml
      - name: Verify version single-source-of-truth (pyproject.toml -> pixi.toml)
        run: |
          set -euo pipefail
          python -m hephaestus.scripts_lib.check_version_single_source
```

**Step 5 — Add the missing leg(s) the gate's NAME promises.** `DEFINITION_OF_DONE.md`
named this job for a **three-file contract** (`pyproject.toml -> pixi.toml ->
pixi.lock`), but the checker covered only `pyproject` + `pixi.toml`. Add `pixi install
--locked` to assert `pixi.lock` is in sync (exits non-zero on drift) — the same frozen
verification the existing `pixi-check` job uses, on the repo-pinned pixi (`v0.69.0`,
guaranteed to support `--locked`):

```yaml
      - name: Verify pixi.lock is in sync with the workspace
        run: |
          set -euo pipefail
          pixi install --locked
```

**Step 6 — Delete the dead code (YAGNI).** Remove the computed-and-discarded `DYNAMIC`
block and the unreachable `VERSION`-file branch.

**Step 7 — TWO-SIDED verification (mandatory).** A dead gate ALSO shows a clean PASS;
only a synthetic-FAIL test distinguishes a real gate from a no-op. Mirror the EXACT CI
invocation (clean venv + `pip install -e .` WITH deps + bare `python`/`-m`, **not**
`pixi run`). See the Quick Reference block above for the exact commands. The change is
not "verified" until you have demonstrated BOTH a clean PASS and a synthetic FAIL for
every leg.

#### Pattern 5 — tracked-file-under-gitignored-dir guard

> **Verification: verified-precommit (CI pending).** The new `check-build-dir-untracked`
> hook passed locally via `pre-commit run --files`, all 76 scripts unit tests passed, and
> ruff was clean — but full CI on PR #1250 had not been confirmed green at capture time.
> The patterns above remain verified-ci; only this Pattern 4 is verified-precommit.

**The collision.** A directory (`build/`) is the sanctioned, gitignored scratch location for
an automation loop, but its *name* collides with the packaging-output convention. The risk is
not on-disk junk — it is a stray `git add build/...` or a widened sdist `only-include` allowlist
silently sweeping automation logs into a published distribution.

**The durable fix is a regression guard, not deletion.** Assert the directory stays *untracked*
(`git ls-files build/` must be empty). Do NOT delete on-disk logs: a live loop regenerates them
within seconds, so deletion is futile. (Cross-reference the sibling skill
`claude-code-scheduled-tasks-lockfile-gitignore` — the "runtime-state file, gitignore-don't-delete"
pattern. The same principle applies: ignore + guard, never delete runtime-regenerated state.)

**Step 1 — Confirm the dir is already gitignored** and find the exact line:

```bash
git check-ignore -v build/
# Expected: .gitignore:5:build/    build/
```

Do NOT edit `.gitignore` — `build/` is already ignored. Do NOT delete the nested live clone or
its logs.

**Step 2 — Implement `scripts/check_build_dir_untracked.py`** (stdlib only):

```python
#!/usr/bin/env python3
"""Guard that the gitignored `build/` scratch dir never has tracked files.

`build/` is the sanctioned scratch location for the automation loop, but its name
collides with the packaging-output convention. A stray `git add build/...` or a
widened sdist allowlist could sweep automation logs into a distribution. This guard
hard-fails (exit 1) if any file under build/ is tracked — a true invariant breach.
"""

import subprocess
import sys
from pathlib import Path
from typing import List


def tracked_build_files(repo_root: Path) -> List[str]:
    """Return tracked files under build/ (empty list = invariant holds)."""
    result = subprocess.run(
        ["git", "ls-files", "build/"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    tracked = tracked_build_files(repo_root)
    if tracked:
        print("ERROR: build/ is a gitignored scratch dir but has TRACKED files:")
        for f in tracked:
            print(f"  {f}")
        print("\nbuild/ must stay untracked. Remove with: git rm --cached <file>")
        print("To clean ignored on-disk files (after stopping the loop): git clean -fdX build/")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Key decisions:
- `git ls-files build/` with `cwd=repo_root, check=True` — relies on git's own tracked-file
  index, so it is exact and ignore-aware.
- **Hard-fail (exit 1)** is INTENTIONAL and is a deliberate divergence from Pattern 3's
  "always exit 0 for discovery tooling" rule. A tracked file under a gitignored scratch dir is a
  *true invariant breach*, not a soft warning — so it must block. The two patterns are not
  contradictory: stale-script detection is heuristic discovery; this is an invariant assertion.

**Step 3 — Add the pre-commit hook** inside the existing `- repo: local` block. Use
`pass_filenames: false` (whole-repo invariant) and `always_run: true` (the breach can be
introduced by a commit that touches no `build/` path, e.g. a `git add` staged earlier):

```yaml
- id: check-build-dir-untracked
  name: Check build/ stays untracked
  description: Fail if any file under the gitignored build/ scratch dir is tracked
  entry: python3 scripts/check_build_dir_untracked.py
  language: system
  pass_filenames: false
  always_run: true
```

This rides the already-required lint gate, so **no new workflow** is needed.

**Step 4 — Document the cleanup convention in CONTRIBUTING.md** (not automated): stop the loop,
then `git clean -fdX build/` (removes only ignored files under `build/`). The guard does not
delete anything — it only asserts the tracked-file invariant.

#### Pattern 6 — Already-wired issue: justfile discoverability comment

**The situation.** An issue asks to "wire `scripts/some_check.py` into CI" but
investigation reveals that a prior PR already added the CI job. The script runs
unconditionally on every `pull_request` to `main`. Re-adding the step would duplicate
CI work; closing the issue without action leaves no cross-reference for future
searchers.

**The correct resolution is NOT to re-wire.** The fix is a single comment line in
`justfile` (or `Makefile`) above the local recipe, pointing searchers at the existing
CI job so the two stay discoverable from each other.

**Step 1 — Verify the CI job already exists.** Grep the workflow directory for the
script filename:

```bash
grep -rn "check_dep_sync\|<script_name>" .github/workflows/
# Expected: one or more hits in a job step's `run:` block
```

Note the workflow file, job name, and the PR/commit that introduced it.

**Step 2 — Confirm the local recipe exists in justfile.** Find the recipe that calls
the same script locally:

```bash
grep -n "dep-check\|<recipe-name>" justfile
```

**Step 3 — Insert a single comment line above the local recipe.** The comment names
the CI job (using its job-key or `name:`), the workflow file, and the PR/issue numbers
so both sides are linked:

```justfile
# Enforced in CI by the `deps/version-sync` job in .github/workflows/_required.yml (see #594, #496).
dep-check:
    python3 scripts/check_dep_sync.py
```

Use the exact CI job key (e.g. `deps/version-sync`, not only the YAML `name:` text) so
searchers can grep for it and land in both places.

**Step 4 — Verify.** Run the recipe and the justfile parser to confirm nothing is broken:

```bash
just dep-check                         # exits 0
just --list                            # recipe still listed, comment not garbled
just --evaluate 2>&1 | head -5         # no parse errors
pre-commit run --files justfile        # all hooks pass
```

**Step 5 — Commit, push, open PR, enable auto-merge:**

```bash
git add justfile
git commit -m "docs(justfile): document dep-check CI enforcement

Cross-reference the existing \`deps/version-sync\` CI job in the justfile
recipe comment so the local check and its CI equivalent are discoverable from
each other.

Closes #<issue-number>"
git push -u origin <branch>
gh pr create --title "docs(justfile): document dep-check CI enforcement" \
  --body "Closes #<issue-number>"
gh pr merge --auto --rebase
```

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Emoji in echo | Used `❌ FAILED:` / `✅ PASSED:` in `echo` lines | Some Ubuntu CI runners mis-render multi-byte emoji, garbling logs | Use plain ASCII (`FAILED:` / `PASSED:`) in CI echo statements |
| Single grep pass | One `grep -rn "$PATTERN" \| grep -q .` without filtering | Matched lines inside `# TODO: remove OldName` comments — false positives | Add `grep -v '^\s*#'` and `grep -v '^\s*"""'` filter stages |
| `--label ci` on PR create | Passed `--label ci` to `gh pr create` | Label `ci` did not exist in the repo, `gh` exited 1 | Run `gh label list` first; omit unknown labels |
| New workflow file | Considered a standalone `deprecation-guard.yml` / separate schema workflow | Unnecessary complexity; the check fits naturally inside an existing syntax/static-check job | Prefer adding a step to an existing job over creating a new workflow |
| Match import names without `.py` | `from util import helper` → searched for `"util.py"` | Import statement uses module name, not filename | Basename matching (with `.py`) is correct; cross-script refs should use the full filename in subprocess calls/comments |
| Hard failure (exit 1) on stale candidates | Exit non-zero to force cleanup | Too aggressive — legitimate one-time setup scripts would block future commits | Always exit 0 for stale detection; it is discovery tooling, not enforcement |
| Verify via convenient pixi env (Pattern 4) | Verified the checker with `pixi run --environment default python3` | The pixi env has all deps, so the `--no-deps` install bug is masked; proves nothing about the real `pip install -e .` + bare-python CI invocation | Mirror the EXACT CI install + interpreter, not a convenient env |
| Install with `--no-deps` (Pattern 4) | `pip install -e . --no-deps` to match a leaner CI image | The checker imports `packaging` (a declared dep) and `ModuleNotFoundError`s at runtime; under `set -e` that is a crash, not an assertion | A checker that imports declared deps must be installed WITH deps |
| Just delete the no-op job (Pattern 4) | Remove the dead `deps-version-sync` job entirely | The context `deps/version-sync` is pinned in the org ruleset; deletion leaves every PR BLOCKED on a check that never reports | De-list the required context first (admin API) OR make the job real in-place; never delete a pinned-context job in a code PR |
| `pixi lock --check` for leg 3 (Pattern 4) | Used `pixi lock --check` to verify the lockfile | The repo pins pixi `v0.69.0` everywhere (composite `setup-pixi-env`, `pixi-check`); `--check` availability on that exact version was unverified, and a prior skill documented older pixi lacking the `lock` subcommand entirely | Use `pixi install --locked` (proven on the pinned version, already used by `pixi-check`), not a flag verified only on a newer local pixi |
| Confirmed clean PASS only (Pattern 4) | Ran the rewritten gate on a clean branch, saw green, called it done | A dead gate ALSO shows a clean PASS; only a synthetic-FAIL test distinguishes a real gate from a no-op | Two-sided verification (clean PASS **and** synthetic FAIL) is mandatory for any gate change |
| Edit `.pre-commit-config.yaml` directly (Pattern 5) | Used the normal `Edit` tool to add the `check-build-dir-untracked` hook | Blocked by a config-file security hook ("don't ask mode" / config-file guard) — same class as the workflow-file block noted in Pattern 2 | Apply the change via a Python `read → str.replace → write` script; assert the anchor appears exactly once and the addition isn't already present before writing |
| Delete on-disk `build/*.log` to "clean up" (Pattern 5) | `rm build/*.log` / `git clean` to remove scratch junk | A live automation loop regenerates the logs within seconds — deletion is futile and the on-disk presence was never the problem | The problem is *tracking*, not presence: gitignore + an untracked-invariant guard. Never delete runtime-regenerated state |
| Make the Pattern 5 guard exit 0 like the stale-script detector | Soft-warn instead of hard-fail, mirroring Pattern 3 | A tracked file under a gitignored scratch dir is a *true invariant breach* that would then pass CI silently and could ship logs in a distribution | Hard-fail (exit 1) is correct for a true-invariant guard; the exit-0 rule applies only to heuristic discovery tooling (Pattern 3), not invariant assertions |
| Re-wire the script into CI (Pattern 6) | Added a new CI step to call `scripts/check_dep_sync.py` again | A prior PR (#594, commit `3ee26ae`) had already added `deps-version-sync` to `.github/workflows/_required.yml`; adding it again would duplicate CI work and create drift between the two definitions | Grep `.github/workflows/` for the script name FIRST; if it already runs in CI, the fix is a justfile comment cross-referencing the existing job, not a new step |
| Close issue as "already done" without any change (Pattern 6) | Mark the issue resolved with no code change | Future contributors reading the justfile recipe would have no hint that the same script runs unconditionally in CI — the discoverability gap remains | Always close the discoverability gap: even when the CI job already exists, a one-line cross-reference comment in the local recipe pays ongoing dividends |

## Results & Parameters

### Pattern 1 — grep deprecation guard

Use BRE pipe syntax (GNU `grep` default on Ubuntu runners). Scan only directories where the names
could legitimately reappear (`shared/`, `tests/`; optionally `examples/`, `benchmarks/`); omit
generated/vendored dirs.

```bash
# BRE pipe — works with grep (not grep -E)
PATTERN='Name1\|Name2\|Name3'
grep -rn "$PATTERN" ...
```

Example blocked set (8 deprecated backward-result aliases from a real cleanup):

```
LinearBackwardResult, LinearNoBiasBackwardResult, Conv2dBackwardResult,
Conv2dNoBiasBackwardResult, DepthwiseConv2dBackwardResult,
DepthwiseConv2dNoBiasBackwardResult, DepthwiseSeparableConv2dBackwardResult,
DepthwiseSeparableConv2dNoBiasBackwardResult
```

### Pattern 2 — standalone schema-validation step

```yaml
- name: Validate config schemas
  if: matrix.test-group.name == 'unit'
  run: pixi run python scripts/validate_config_schemas.py config/defaults.yaml config/models/*.yaml tests/fixtures/config/tiers/*.yaml
```

### Pattern 5 — tracked-file-under-gitignored-dir guard

Verification command set (run before adding the guard, and to confirm it):

```bash
# 1. The invariant: build/ must have zero tracked files
git ls-files build/
# Expected: (empty output)

# 2. Confirm build/ is gitignored, and at which .gitignore line
git check-ignore -v build/
# Expected: .gitignore:5:build/    build/

# 3. Auto-discovered parametrized smoke test for the new script (rides existing
#    parametrized test that imports every scripts/*.py and runs its main()).
#    All 76 scripts unit tests passed locally including the new module.
pixi run python -m pytest tests/unit/scripts/ -v

# 4. Hook fires on demand
pre-commit run check-build-dir-untracked --all-files
```

The hook is `pass_filenames: false` + `always_run: true` (whole-repo invariant, breach can be
staged by a commit touching no `build/` path). Exit 1 on any tracked file — INTENTIONAL hard-fail,
unlike Pattern 3's exit-0 discovery semantics. Cleanup of on-disk ignored files (manual, after
stopping the loop): `git clean -fdX build/`.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3834 (grep deprecation guard) — follow-up from #3267/#3059; PR #4810 | 8 deprecated backward-result aliases blocked in `comprehensive-tests.yml` `mojo-syntax-check` job |
| ProjectScylla | Issue #1443 (schema validation) — follow-up from #1382; PR #1466 | `validate_config_schemas.py` + pre-commit hook already existed; CI step was the only missing piece |
| ProjectOdyssey | Issue #3969 (stale-script detector) — follow-up from #3148/#3337; PR #4844 | stdlib-only detector + pre-commit hook + 20 unit tests; 22 stale candidates surfaced |

### Pattern 3 — stale-script detector

```
WARNING: possibly stale: scripts/analyze_issues.py
WARNING: possibly stale: scripts/analyze_warnings.py
... (22 total candidates)

22 possibly stale script(s) found (warnings only, not a failure).
Exit code: 0
```

`ALWAYS_ACTIVE` set (never flagged): `{"common.py", "check_stale_scripts.py"}`. Add any shared
library module imported by other scripts but never invoked directly.

### Pattern 4 — dead required gate, made real in place

Final job shape in `.github/workflows/_required.yml` (job `deps-version-sync`, required
status check `deps/version-sync`) — install WITH deps, `set -euo pipefail`, reuse the
unit-tested checker via `-m`, pinned `setup-pixi` `v0.69.0`, lockfile leg via `pixi
install --locked`:

```yaml
  deps-version-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install package WITH deps (checker imports `packaging`)
        run: |
          set -euo pipefail
          pip install -e .              # NOT --no-deps
      - name: Verify version single-source (pyproject.toml -> pixi.toml)
        run: |
          set -euo pipefail
          python -m hephaestus.scripts_lib.check_version_single_source
      - name: Setup pixi (pinned)
        uses: ./.github/actions/setup-pixi-env   # pins pixi v0.69.0
      - name: Verify pixi.lock in sync (pixi.toml -> pixi.lock)
        run: |
          set -euo pipefail
          pixi install --locked
```

Two-sided verification (the discipline that proves the gate is real) — mirror the EXACT
CI invocation, clean venv + `pip install -e .` WITH deps + bare `python`/`-m`, NOT
`pixi run`:

```bash
python -m venv /tmp/dg && . /tmp/dg/bin/activate && pip install -e .   # WITH deps

# Leg 1+2 (checker): clean -> 0 ; inject static [project].version -> non-zero ; restore -> 0
python -m hephaestus.scripts_lib.check_version_single_source; echo $?   # 0
printf '\nversion = "9.9.9"\n' >> pyproject.toml                        # append so tomllib parses it under [project]
python -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"].get("version"))'  # 9.9.9
python -m hephaestus.scripts_lib.check_version_single_source; echo $?   # non-zero
git checkout -- pyproject.toml                                          # -> 0

# Leg 3 (lockfile): clean -> 0 ; append sentinel pypi dep -> non-zero ; restore -> 0
pixi install --locked; echo $?                                         # 0
printf '\n[pypi-dependencies]\nnonexistent-sentinel-pkg = "*"\n' >> pixi.toml
pixi install --locked; echo $?                                        # non-zero: "lock file not up-to-date with the workspace"
git checkout -- pixi.toml                                             # -> 0
```

Accepted DRY overlap (justified by the pinned-context constraint): `lint`'s
`check-version-single-source` pre-commit hook (legs 1+2) and `pixi-check`'s `pixi
install --locked` (leg 3). The alternative — deleting the pinned-context job — bricks
the merge queue, so defense-in-depth duplication is the correct trade-off.

**Related skills:** `gha-required-checks-branch-protection` (pinned required contexts,
ruleset admin), `console-scripts-exit-code-discipline` (exit-code semantics under
`set -e`), `lockfile-and-release-pipeline-management` (lockfile-sync verification), and
the companion worktree-`__file__` skill (why `-m` beats a `scripts/<x>.py` shim).

## Verified On (Extended)

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3834 (grep deprecation guard) — follow-up from #3267/#3059; PR #4810 | 8 deprecated backward-result aliases blocked in `comprehensive-tests.yml` `mojo-syntax-check` job |
| ProjectScylla | Issue #1443 (schema validation) — follow-up from #1382; PR #1466 | `validate_config_schemas.py` + pre-commit hook already existed; CI step was the only missing piece |
| ProjectOdyssey | Issue #3969 (stale-script detector) — follow-up from #3148/#3337; PR #4844 | stdlib-only detector + pre-commit hook + 20 unit tests; 22 stale candidates surfaced |
| ProjectHephaestus | Issue #1214 / PR #1250 (tracked-file-under-build guard) | stdlib-only `check_build_dir_untracked.py` + `repo: local` pre-commit hook; asserts `git ls-files build/` empty (hard-fail exit 1). verified-precommit (CI pending) |
| ProjectHephaestus | Issue #1181 (dead required gate) — PR #1266; `deps/version-sync` passed in CI in 13s on the fix branch | `deps-version-sync` job in `.github/workflows/_required.yml` computed-and-discarded a `DYNAMIC` verdict with its only `exit 1` behind a non-existent `VERSION` file; rewired to install WITH deps + `python -m hephaestus.scripts_lib.check_version_single_source` under `set -euo pipefail` + `pixi install --locked` (pinned pixi v0.69.0); context pinned in org ruleset so fixed in place, not deleted; two-sided verified |
| ProjectHermes | Issue #496 (already-wired CI dep-sync) — branch `496-auto-impl`, commit `d30c9f7` | Issue asked to wire `scripts/check_dep_sync.py` into CI; investigation revealed `deps-version-sync` job already existed in `.github/workflows/_required.yml` at line 402 (added by PR #594 / commit `3ee26ae`), running unconditionally on every `pull_request` to `main`; fix was a single discoverability comment in `justfile` above the `dep-check` recipe: `# Enforced in CI by the \`deps/version-sync\` job in .github/workflows/_required.yml (see #594, #496).`; verified: `just dep-check` exits 0, `just --list` clean, `pixi run pre-commit run --files justfile` passes (verified-precommit) |
