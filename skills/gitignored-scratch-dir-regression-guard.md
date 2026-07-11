---
name: gitignored-scratch-dir-regression-guard
description: "Guard a gitignored-but-name-colliding scratch directory (e.g. ProjectHephaestus `build/`, the sanctioned automation-loop scratch dir whose name collides with the Python packaging-output convention) with a `repo: local` Python pre-commit hook that asserts `git ls-files <dir>/` stays EMPTY — i.e. guard against the dir becoming git-TRACKED, NOT against on-disk runtime junk. Use when: (1) a strict repo audit flags a gitignored runtime/scratch dir as a packaging/distribution risk because its name collides with a tooling convention (build/, dist/, target/, out/); (2) you are tempted to `rm` live loop-written logs or edit a `.gitignore` that already ignores the dir — DON'T, a running loop regenerates them in seconds; (3) you want a durable regression guard that rides the existing required pre-commit CI gate with no new workflow; (4) you are about to ADD a new `scripts/*.py` guard to a repo whose smoke-test harness AUTO-DISCOVERS every script (a brand-new file silently inherits a `--help`-exits-0-with-output contract); (5) you reflexively reach for `# noqa: <code>` — under `RUF100` an unused noqa for a non-enabled rule is itself a lint error. PLANNING learning — the audit FACTS and the two R1 implementation gotchas were verified-local; the full revised fix was NOT executed end-to-end in CI."
category: ci-cd
date: 2026-06-12
version: "1.1.0"
history: gitignored-scratch-dir-regression-guard.history
user-invocable: false
verification: verified-local
tags:
  - ci-cd
  - pre-commit
  - regression-guard
  - gitignore
  - git-ls-files
  - scratch-dir
  - build-dir
  - packaging
  - sdist
  - hatch
  - runtime-state
  - untracked
  - planning
  - repo-audit
  - smoke-test
  - auto-discovery
  - ruff
  - ruff100
  - noqa
  - help-flag
  - tdd
---

# Guard a Gitignored Scratch Dir Against TRACKED State (Not On-Disk Junk)

> ⚠️ **PLANNING learning — FACTS verified-local, full fix NOT CI-verified.** Two
> classes of finding live here, with different verification levels:
>
> - **verified-local (observed directly):** the audit ground-truth git/grep facts
>   (`git ls-files build/` → 0 entries, `git check-ignore -v build/` →
>   `.gitignore:5:build/`, `pyproject.toml [tool.hatch.build.targets.sdist]
>   only-include` read directly) **AND** the two R1/NOGO implementation gotchas
>   below (Gotcha A — the auto-discovering `--help` smoke-test contract; Gotcha B —
>   `RUF100` rejecting a `# noqa` for a non-enabled rule). For the gotchas the
>   reviewer re-read `tests/unit/scripts/test_scripts_smoke.py`, `conftest.py`,
>   the template `--help` branch at `check_security_policy_no_hardcoded_date.py:44-45`,
>   and the `pyproject.toml` ruff `select` list directly.
> - **NOT CI-verified:** the overall revised fix (the `repo: local` hook plus the
>   corrected `scripts/check_build_dir_untracked.py` with the `--help` branch) was
>   designed but **NOT executed end-to-end in CI**. Treat the "Workflow" as a
>   blueprint to validate, not a recipe known to pass.
>
> Line numbers cited were read once and drift — anchor on content, not numbers.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-12 |
| **Objective** | A strict ProjectHephaestus audit (#1214) flagged the sanctioned, gitignored `build/` automation-loop scratch dir as a "junk drawer" packaging risk because its name collides with the Python packaging-output convention (`build/`, `dist/`), raising the spectre of a stray glob sweeping loop logs into a distribution. Design a durable guard that neutralizes the *real* risk without disrupting the live loop. |
| **Outcome (proposed)** | Do NOT delete on-disk runtime files and do NOT touch `.gitignore` (it already ignores `build/`). Instead add a `repo: local` Python pre-commit hook (`scripts/check_build_dir_untracked.py`) that asserts `git ls-files build/` stays EMPTY, mirroring the exact shape of an existing guard (`scripts/check_security_policy_no_hardcoded_date.py`): `get_repo_root()` walks up to `pyproject.toml`, a pure check fn, `sys.exit(1)` with a remediation message. It rides the already-required pre-commit CI gate — no new workflow. |
| **Verification** | verified-local for the FACTS (audit git/grep ground truth + the two R1/NOGO implementation gotchas, all observed directly); the full revised hook/script was NOT executed end-to-end in CI |
| **R1 / NOGO note** | The v1.0.0 plan's embedded ready-to-commit script body was NOGO'd by the reviewer over **two mechanical defects** it would have shipped: (A) the new script broke a PRE-EXISTING auto-discovered `--help` smoke test, and (B) a reflexive `# noqa: S603` triggered `RUF100` because `S603` is not in the ruff `select`. See Gotchas A/B below. |

## When to Use

- A **strict repo audit** flags a *gitignored* runtime/scratch directory as a
  packaging or distribution risk **because its name collides with a tooling
  convention** — `build/` (Python/CMake), `dist/`, `target/` (Rust/Maven),
  `out/`, `_build/`. The dir is sanctioned (a project doc mandates "all temp
  files go in `<dir>/`") but the name overlaps a convention some glob might sweep.
- You catch yourself wanting to **`rm` live runtime junk** (`build/loop_*.log`)
  to "clean up" what the audit flagged. DON'T — a live automation loop
  regenerates those files within seconds (the "Shape B" anti-pattern from the
  sibling skill `claude-code-scheduled-tasks-lockfile-gitignore`). Policing
  on-disk presence is futile.
- You are about to **edit `.gitignore`** for the flagged dir. First run
  `git check-ignore -v <dir>/`. If it already reports a matching rule, the
  gitignore is correct and needs no change — the residual risk is purely
  *future TRACKED state*, which a gitignore entry alone does not prevent
  (someone can `git add -f`, or the sdist allowlist can widen).
- You want a **build-free regression guard** that catches the dir becoming
  tracked and rides an **already-required** pre-commit CI gate, with **no new
  GitHub workflow** and no full test run.
- A nested checkout lives *inside* the scratch dir (e.g.
  `build/Mnemosyne`, a live clone read by an `/advise` pipeline). You
  must confirm it is **not stray** before any cleanup — the guard targets
  TRACKED state, so a gitignored live clone is irrelevant to it and must NOT be
  deleted.
- You are about to **add a new `scripts/*.py` guard** (or any script) to a repo
  whose test suite has an **auto-discovering smoke-test harness** — e.g.
  ProjectHephaestus `tests/unit/scripts/conftest.py` globs every `scripts/*.py`
  and parametrizes `test_scripts_smoke.py::test_script_help_exits_zero`. READ
  that harness FIRST: the new file silently inherits a contract the author never
  wrote (`--help` must exit 0 **and** print non-empty output). See **Gotcha A**.
- You catch yourself about to write **`# noqa: <code>`** out of habit. Under
  `RUF100` an unused noqa for a rule that is **not in the ruff `select` list** is
  itself a lint error (`RUF100 Unused noqa directive (non-enabled: …)`) that turns
  `ruff check` RED. Grep the `select` list BEFORE suppressing. See **Gotcha B**.
- You are **writing a plan that embeds full ready-to-commit file bodies.** The
  reviewer will lint/test those bodies as the deliverable artifact. Mentally run
  the repo's ACTUAL gates (auto-discovered tests + the exact ruff `select`)
  against the proposed code before submitting, or the plan ships a red artifact
  and gets NOGO'd on mechanical defects. See the **Meta-lesson** below.

## Verified Workflow

> ⚠️ **PROPOSED, NOT VERIFIED.** Despite the section title (required by the skill
> validator), the whole of this section is a blueprint that was designed but **not
> run**. Only the step-1 audit ground-truth checks were executed. Validate every
> other step before trusting it.

### Quick Reference

```bash
# 1. VERIFY the audit facts before acting (these WERE run for #1214):
git ls-files build/            # MUST be empty → dir is not tracked (the real risk is absent today)
git check-ignore -v build/     # Expected: .gitignore:N:build/  → gitignore already correct, do NOT edit it

# 2. VERIFY the packaging claim — only-include is an ALLOWLIST, not a denylist:
#    confirm build/ is ABSENT from [tool.hatch.build.targets.sdist] only-include
#    (absence = excluded from the sdist; the audit's "harmless to the wheel" claim held)

# 3. Do NOT delete live runtime junk and do NOT rm/edit .gitignore.

# 4. Add the regression guard hook + script (see below), then:
python3 scripts/check_build_dir_untracked.py   # exit 0 when build/ has no tracked files
pre-commit run check-build-dir-untracked --all-files
```

### Detailed Steps

1. **Verify the audit's ground-truth facts first.** Three checks decide whether
   there is anything to do:

   ```bash
   git ls-files build/            # → 0 entries for #1214 (no tracked files: real risk NOT yet realized)
   git check-ignore -v build/     # → .gitignore:5:build/ for #1214 (already ignored: leave .gitignore alone)
   ```

   And confirm the packaging exclusion by reading
   `pyproject.toml [tool.hatch.build.targets.sdist] only-include`: it is an
   **exact-path allowlist**, so `build/` being **absent** from it means it is
   genuinely excluded from the sdist. (Verify the wheel target too if present.)

2. **Frame the guard around TRACKED state, not on-disk presence.** The packaging
   risk is realized *only* if files in the dir become git-**tracked** (or the
   sdist allowlist widens to include the dir). Runtime-written on-disk files are
   harmless to distribution as long as they are never tracked. So the durable
   assertion is: **`git ls-files build/` stays EMPTY.** Do not write any check
   that inspects on-disk files — a live loop defeats it.

3. **Write the guard as a `repo: local` Python-script hook, mirroring an existing
   guard's exact shape.** Copy the structure of
   `scripts/check_security_policy_no_hardcoded_date.py`:
   `get_repo_root()` walks up parent dirs until it finds `pyproject.toml`; a pure
   check function returns the offending paths; `main()` prints a remediation
   message and `sys.exit(1)` if non-empty. Sketch:

   ```python
   #!/usr/bin/env python3
   """Assert build/ stays UNTRACKED (it is the gitignored automation-loop scratch dir)."""
   import subprocess
   import sys
   from pathlib import Path

   def get_repo_root() -> Path:
       p = Path(__file__).resolve()
       for parent in p.parents:
           if (parent / "pyproject.toml").exists():
               return parent
       raise SystemExit("could not locate repo root (no pyproject.toml found)")

   def tracked_under_build(root: Path) -> list[str]:
       out = subprocess.run(
           ["git", "ls-files", "build/"],
           cwd=root, capture_output=True, text=True, check=True,
       ).stdout
       return [line for line in out.splitlines() if line.strip()]

   def main() -> int:
       # GOTCHA A: the auto-discovering smoke test runs `<script> --help` and
       # asserts exit 0 AND non-empty stdout+stderr. Mirror the template branch
       # (check_security_policy_no_hardcoded_date.py:44-45) so --help prints the
       # docstring and returns 0 WITHOUT running the real check (which is silent
       # on a clean repo → would fail the non-empty-output assertion).
       if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
           print(__doc__)
           return 0
       offenders = tracked_under_build(get_repo_root())
       if offenders:
           print("ERROR: build/ is the gitignored automation-loop scratch dir and")
           print("must stay UNTRACKED, but these files are tracked:")
           for f in offenders:
               print(f"  {f}")
           print("Remediation: git rm --cached <file>  (do NOT commit build/ contents)")
           return 1
       return 0

   if __name__ == "__main__":
       sys.exit(main())
   ```

4. **Wire it into `.pre-commit-config.yaml` as a `repo: local` hook.** Insert it
   near the other local guards (for #1214 the candidate insertion point was
   *after* `check-security-policy-no-hardcoded-date`; anchor on that hook's `id:`,
   NOT on a line number). Use `language: system`, `pass_filenames: false`,
   `always_run: true`:

   ```yaml
   - repo: local
     hooks:
       - id: check-build-dir-untracked
         name: assert build/ scratch dir stays untracked
         entry: python3 scripts/check_build_dir_untracked.py
         language: system
         pass_filenames: false
         always_run: true
   ```

   It rides the already-required pre-commit CI gate, so **no new workflow** is
   needed. `language: system` assumes `python3` on PATH in the hook env (true for
   this repo); a repo that prefers isolated hook envs would use
   `language: python` with declared deps instead.

5. **Do NOT use `language: pygrep`.** The guard must shell out to `git ls-files`;
   a pygrep one-liner cannot express that. A `system` (or `python`) Python script
   is required.

6. **Leave the nested live clone alone.** If a real checkout lives under the dir
   (e.g. `build/Mnemosyne`, read by the `/advise` pipeline), confirm it is
   active, then leave it. The guard only sees *tracked* paths, so a gitignored
   nested clone is invisible to it and is correctly ignored.

7. **Optionally document the convention** in a repo-hygiene section of
   `CONTRIBUTING.md` (the plan assumed such a section exists — verify before
   inserting): "`build/` is the sanctioned gitignored scratch dir; never commit
   its contents; the `check-build-dir-untracked` hook enforces this."

### R1 implementation gotchas (the two empirically-confirmed NOGO defects)

These two defects in the v1.0.0 proposed script body were **reproduced this
session** and caused the plan's re-plan (R1) to be NOGO'd. Both are
verified-local — the reviewer re-read the harness, the template, and the ruff
`select` list directly.

8. **Gotcha A — obey the auto-discovering `--help` smoke-test contract.**
   ProjectHephaestus `tests/unit/scripts/conftest.py` auto-discovers EVERY
   `scripts/*.py` via a `_discover_scripts()` glob and parametrizes
   `tests/unit/scripts/test_scripts_smoke.py::test_script_help_exits_zero`. That
   test runs `python scripts/<name>.py --help` and asserts BOTH **exit code 0**
   AND **non-empty combined stdout+stderr** (`assert combined.strip()`) — unless
   the script is in the `HELP_RUNS_REAL_WORK` allowlist. A guard whose `main()`
   ignores argv runs the REAL check on `--help`; on a clean repo that returns 0
   with **zero output** → the non-empty-output assertion FAILS. A brand-new
   script thus silently breaks a PRE-EXISTING test the author never looked at.
   - **FIX:** mirror the established template's branch verbatim —
     `if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"): print(__doc__); return 0`
     (see `scripts/check_security_policy_no_hardcoded_date.py:44-45`; anchor on
     content, the line numbers drift). The script needs a real module docstring
     so `print(__doc__)` produces non-empty output.
   - **Also add a DIRECT unit test** for the `--help` contract so TDD drives the
     interface, not just the auto-discovered smoke test (e.g. assert `--help`
     exits 0 and prints non-empty output, in
     `tests/unit/scripts/test_check_build_dir_untracked.py`).
   - **LESSON:** when adding a file to a directory governed by an
     auto-discovering / parametrized test, READ that harness FIRST — the new
     file inherits a contract the author didn't write.

9. **Gotcha B — never add `# noqa: <code>` for a rule that isn't in `select`.**
   The v1.0.0 plan added `# noqa: S603` to the `subprocess.run(["git", ...])`
   call out of habit. But the ruff `select` in `pyproject.toml`
   (`["E","F","W","I","N","D","UP","S101","S102","S105","S106","B","SIM","C4","C901","RUF"]`)
   does NOT enable `S603` — only specific S-rules are on. With `RUF` enabled, an
   unused noqa fires `RUF100 Unused noqa directive (non-enabled: S603)` →
   `ruff check` goes RED, directly contradicting the plan's own "gates stay
   green" claim.
   - **FIX:** before writing ANY `# noqa: <code>`, confirm `<code>` is actually
     in the ruff `select` list (grep `pyproject.toml`). For a static-literal
     arglist `subprocess.run` with **no `shell=True`**, no enabled bandit rule
     fires, so **NO noqa is needed** — drop it.
   - **LESSON:** a defensive `# noqa` is not free — under `RUF100` it is a
     liability if the suppressed rule isn't enabled. Grep `select` before
     suppressing.

10. **Meta-lesson (planning).** When a plan embeds full ready-to-commit file
    bodies, the REVIEWER will (correctly) lint/test those bodies as the
    deliverable artifact. "Looks right" is not enough — mentally run the repo's
    ACTUAL gates (the auto-discovered/parametrized tests + the EXACT ruff
    `select` list) against the proposed code before submitting, or the plan ships
    a red artifact and gets NOGO'd on mechanical defects rather than substance.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Delete the on-disk runtime junk the audit flagged | `rm build/loop_*.log` to "clean the junk drawer" | A live automation loop (`loop_runner.py` writes work reports under `build/`) regenerates the files within seconds; you cannot out-race a running process from the client side | Guard against TRACKED state, not on-disk presence. Policing runtime-written files is the "Shape B" anti-pattern — futile by construction |
| Edit `.gitignore` to "fix" the flagged dir | Reached for the `.gitignore` to add/strengthen the `build/` rule | `git check-ignore -v build/` already returned `.gitignore:5:build/` — the dir was already ignored; editing it is a no-op that wastes a commit and risks breaking the existing rule | Always run `git check-ignore -v <dir>/` FIRST. If it already matches, the gitignore is correct and the residual risk is purely *future tracked-state*, which needs a guard, not a gitignore edit |
| Treat the gitignore entry as sufficient protection | Assumed "it's gitignored, so it can never enter a distribution" | A gitignore entry does not prevent `git add -f`, nor does it prevent the sdist `only-include` allowlist from later widening to include the dir; the realized risk is TRACKED state, which gitignore alone does not block | Add a regression guard that asserts `git ls-files build/` stays EMPTY — that is the invariant the packaging risk actually depends on |
| Write the guard with `language: pygrep` | Wanted a zero-script one-line pre-commit pattern | The check must shell out to `git ls-files build/`; pygrep can only match file contents/lines, not query the git index | Use a `repo: local` `language: system` (or `language: python`) Python script that runs `git ls-files`; pygrep cannot express an index query |
| Delete the nested `build/Mnemosyne` checkout as "stray junk" | Saw a whole repo clone inside the flagged scratch dir and assumed it was leftover junk | It is a LIVE clone the `/advise` pipeline reads on demand; deleting it breaks that pipeline. It is gitignored, so it is irrelevant to the tracked-state guard anyway | Confirm a nested checkout is active before any cleanup; the regression guard targets only tracked paths, so live gitignored clones are correctly invisible to it |
| Trust the cited line numbers verbatim | Plan referenced `pyproject.toml:158-165`, `loop_runner.py:351`, `CLAUDE.md:455`, `.gitignore:5`, and a `.pre-commit-config.yaml` insertion "~line 207" | Line numbers were read once and drift as files change; anchoring on them makes the workflow brittle | Anchor on CONTENT (the hook `id:`, the `only-include` key, the section heading), never on line numbers |
| **(R1/NOGO)** Ship a guard script whose `main()` ignores argv | The v1.0.0 plan's `scripts/check_build_dir_untracked.py` ran the real `git ls-files` check unconditionally, with no `--help`/`-h` branch | The auto-discovering `tests/unit/scripts/conftest.py` globs every `scripts/*.py` and parametrizes `test_script_help_exits_zero`, which runs `--help` and asserts exit 0 **AND non-empty** stdout+stderr; on a clean repo the real check returns 0 with ZERO output → the non-empty assertion FAILS, silently breaking a PRE-EXISTING test | When adding a file to a directory governed by an auto-discovering/parametrized test, READ that harness first. Mirror the template `--help` branch verbatim (`if sys.argv[1] in ("--help","-h"): print(__doc__); return 0`, see `check_security_policy_no_hardcoded_date.py:44-45`) and add a direct `--help` unit test so TDD drives the interface |
| **(R1/NOGO)** Add `# noqa: S603` to the `subprocess.run(["git",...])` call | Reflexively suppressed a bandit subprocess warning "to keep gates green" | Ruff's `select` in `pyproject.toml` does NOT enable `S603`; with `RUF` enabled, the unused noqa fires `RUF100 Unused noqa directive (non-enabled: S603)` and turns `ruff check` RED — the opposite of the intended effect | Before writing ANY `# noqa: <code>`, grep the ruff `select` list to confirm `<code>` is enabled. For a static-literal arglist subprocess call with no `shell=True`, no enabled rule fires → NO noqa is needed. Under `RUF100` a defensive noqa is a liability, not free insurance |
| **(R1/NOGO meta)** Submit a plan whose embedded code "looks right" without running the repo's gates against it | The plan embedded full ready-to-commit file bodies but the author never mentally executed the auto-discovered tests or the exact ruff `select` against them | The reviewer (correctly) lints/tests embedded bodies as the deliverable artifact; two mechanical defects (Gotchas A+B) made the artifact RED → NOGO on mechanics, not substance | When a plan embeds ready-to-commit code, mentally run the repo's ACTUAL gates (auto-discovered/parametrized tests + exact ruff `select`) against it before submitting; "looks right" is not the bar — passing the real gates is |

## Results & Parameters

**The core durable insight (this is the planning learning).** When an audit flags
a *gitignored* scratch/runtime dir whose name collides with a packaging convention,
the realized risk is **git-TRACKED state**, not on-disk junk. The durable guard
asserts `git ls-files <dir>/` stays EMPTY. Deleting live runtime files or editing
an already-correct `.gitignore` accomplishes nothing.

**The R1/NOGO implementation insight (added v1.1.0).** Designing the *right* guard
is necessary but not sufficient — the proposed SCRIPT BODY itself must pass the
repo's mechanical gates, which a reviewer evaluates as the deliverable artifact:

| Gotcha | The trap | The fix |
|--------|----------|---------|
| **A — auto-discovering `--help` smoke test** | `tests/unit/scripts/conftest.py` globs every `scripts/*.py` and parametrizes `test_script_help_exits_zero`, asserting `--help` exits 0 AND prints non-empty output. A `main()` that ignores argv runs the silent real check on `--help` → fails on a clean repo, breaking a PRE-EXISTING test | Mirror the template `--help`/`-h` branch verbatim (`print(__doc__); return 0`, `check_security_policy_no_hardcoded_date.py:44-45`); give the script a real docstring; add a direct `--help` unit test |
| **B — `RUF100` on a non-enabled `# noqa`** | The ruff `select` does NOT include `S603`; a habitual `# noqa: S603` fires `RUF100 Unused noqa directive (non-enabled: S603)` → `ruff check` RED | Grep `select` before any `# noqa`; a static-literal `subprocess.run` with no `shell=True` triggers no enabled rule → drop the noqa entirely |
| **Meta** | Embedded ready-to-commit code that "looks right" but was never run against the repo's gates ships RED → NOGO on mechanics | Mentally run the ACTUAL gates (auto-discovered tests + exact ruff `select`) against the proposed code before submitting |

**Ground-truth facts verified-local for ProjectHephaestus #1214** (these WERE run):

| Check | Command | Result |
|-------|---------|--------|
| Dir is untracked today | `git ls-files build/` | 0 entries (real risk not yet realized) |
| Dir is already ignored | `git check-ignore -v build/` | `.gitignore:5:build/` (do NOT edit gitignore) |
| Dir excluded from sdist | read `[tool.hatch.build.targets.sdist] only-include` | `build/` ABSENT from the exact-path allowlist → genuinely excluded ("harmless to wheel" claim held) |

**`only-include` is an ALLOWLIST, not a denylist.** A path's *absence* from
`[tool.hatch.build.targets.sdist] only-include` means it is **excluded** from the
sdist. Do not mistake it for a denylist where absence would mean "included."

**Hook config that rides the existing required gate (no new workflow):**

```yaml
- repo: local
  hooks:
    - id: check-build-dir-untracked
      name: assert build/ scratch dir stays untracked
      entry: python3 scripts/check_build_dir_untracked.py
      language: system        # assumes python3 on PATH; use `python` for isolated hook env
      pass_filenames: false
      always_run: true
```

**Uncertain assumptions / open risks (carried honestly from the planning session):**

- The `.pre-commit-config.yaml` insertion point ("after
  `check-security-policy-no-hardcoded-date`, ~line 207") and all cited line
  numbers (`pyproject.toml:158-165`, `loop_runner.py:351`, `CLAUDE.md:455`,
  `.gitignore:5`) were read once and **drift** — anchor on content.
- Whether `CONTRIBUTING.md` has a natural "repo hygiene" section for the doc note
  was **NOT directly verified**; the plan assumes one exists.
- `language: system` assumes `python3` is on PATH in the hook env (true for this
  repo). Repos preferring isolated envs should use `language: python` with
  declared deps.
- The nested `build/Mnemosyne` checkout is a **live** clone the `/advise`
  pipeline reads — confirmed not-stray; must NOT be deleted.

**Related skills (complementary, not duplicates):**

- `claude-code-scheduled-tasks-lockfile-gitignore` — the "Shape B" sibling:
  *untrack/gitignore* a live runtime file to silence CI/CLI dirty-tree guards.
  Shares the "don't fight the live process that regenerates the file" insight,
  but solves the inverse problem (silence guards) rather than this one (assert
  the dir stays untracked).
- `ci-hygiene-and-validation-gates` — the regression-guard / stale-detector
  family: build-free `repo: local` Python pre-commit hooks that catch
  regressions and ride the existing CI gate. This skill is a specific instance
  of that pattern applied to a gitignored scratch dir.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | Issue #1214 (strict audit, 2026-06-12) — `build/` (gitignored automation-loop scratch dir, name-colliding with Python packaging output) flagged as a "junk drawer" distribution risk | Audit FACTS verified-local: `git ls-files build/` → 0, `git check-ignore -v build/` → `.gitignore:5:build/`, `only-include` allowlist excludes `build/`. Proposed FIX (the `check-build-dir-untracked` `repo: local` hook + script) designed but NOT executed — this is a PLANNING learning |
| ProjectHephaestus | Issue #1214 **R1 re-plan** (2026-06-12) — prior plan NOGO'd over two empirically-confirmed defects in the proposed guard SCRIPT body | **Gotchas A+B verified-local:** reviewer re-read `tests/unit/scripts/test_scripts_smoke.py`, `tests/unit/scripts/conftest.py` (`_discover_scripts()` glob + `test_script_help_exits_zero`'s exit-0-AND-non-empty-output assertion + `HELP_RUNS_REAL_WORK` allowlist), the template `--help` branch at `check_security_policy_no_hardcoded_date.py:44-45`, and the `pyproject.toml` ruff `select` list (`S603` absent → `RUF100` fires on `# noqa: S603`). The corrected script (with the `--help` branch, no noqa) was NOT executed end-to-end in CI |
