---
name: env-manager-migration-python-version-drift
description: "Migrating between Python environment managers (pixi->uv, conda->uv, poetry->uv) can make the new resolver pick a DIFFERENT interpreter version, silently re-exposing latent version-dependent bugs the old version masked. Use when: (1) migrating a repo's Python env manager (pixi->uv, conda->uv, poetry->uv), (2) CI goes red right after an env-manager swap even though nothing 'real' changed, (3) a test that was green before the migration now fails on the same source, (4) you must decide whether a newly-surfaced failure is a real bug or a version regression, (5) a repo policy forbids a top-level pyproject.toml but the uv migration needs one to lock the build toolchain."
category: ci-cd
date: 2026-07-18
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - python-version-drift
  - env-manager-migration
  - pixi-to-uv
  - uv
  - latent-bug
  - scipy
  - mypy
  - python-version-pin
  - tooling-pyproject
  - package-false
---

# Env-Manager Migration Python-Version Drift Re-Exposes Latent Bugs

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-18 |
| **Objective** | Record that swapping a repo's Python environment manager can change the resolved interpreter version, which silently re-exposes latent version-dependent bugs the old interpreter tolerated — and how to isolate, diagnose, and fix that safely |
| **Outcome** | Successful — verified in CI on the HomericIntelligence pixi->uv migration (ProjectScylla, Keystone); interpreter pin + real source fixes + a targeted dependency cap restored green for the *right* reasons |
| **Verification** | verified-ci |

## When to Use

- You are migrating a repo between Python environment managers (pixi->uv, conda->uv, poetry->uv, etc.)
- CI turns red immediately after an env-manager swap even though no application logic changed
- A test that was "green before the migration" now fails on identical source code
- You need to decide whether a newly-surfaced failure is a real latent bug to fix or a genuine version-cap regression
- A repo whose policy FORBIDS a top-level `pyproject.toml` ("ships no Python") now needs a uv `pyproject.toml` to lock the BUILD toolchain

## Verified Workflow

### Quick Reference

```bash
# 1. Before trusting a migration as "green", compare the resolved interpreter.
uv python find            # what uv would resolve to now
# ... vs the version the OLD manager (pixi/conda/poetry) actually used.

# 2. Pin the interpreter to the OLD manager's version to isolate the
#    toolchain change from a version change.
uv python pin 3.14        # writes/commits .python-version
cat .python-version

# 3. Re-run CI. Any failure that remains is a REAL latent bug (or a genuine
#    dependency regression) — fix it in source, never skip/silence the test.
```

### Detailed Steps

1. **Do not trust "green under the old manager" as proof of correctness.** It only proves the
   old interpreter *tolerated* the code. The new manager's resolver may pick a different Python
   (e.g. pixi resolved 3.14 on ProjectScylla; uv pinned 3.12), and that delta re-exposes latent
   bugs.

2. **Measure the interpreter delta first.** Compare `uv python find` (or the committed
   `.python-version`) against the version the old manager resolved. Treat the delta as the prime
   suspect for any "nothing changed but CI is red" failure.

3. **Pin the interpreter explicitly with `uv python pin` / a committed `.python-version`.** Pin to
   the version the OLD manager used so the migration isolates the *toolchain* change from a
   *version* change. This stops uv from silently grabbing a newer/older Python and lets you land
   the manager swap and the version bump as separate, reviewable steps.

4. **Treat every newly-exposed failure as a REAL bug and fix it in source.** Never weaken, skip,
   `xfail`, or delete the test. Two latent bugs surfaced only under py3.12 in ProjectScylla:

   - `scipy.stats.mannwhitneyu(identical, identical)` returns `p=NaN` in newer scipy (zero rank
     variance), so a test asserting `p > 0.05` failed as `assert nan > 0.05`. **Real fix:** add an
     all-ties degenerate guard in the source stats function that returns `p=1.0` (identical
     distributions ARE not significant) — do not weaken the test to accept NaN.

   - `Path(long_string).is_file()` raised `OSError: [Errno 36] File name too long` (ENAMETOOLONG)
     on a 300-char argument under py3.12, whereas py3.14's `is_file()` SWALLOWS that OSError.
     **Real fix:** wrap the call in a helper that catches `OSError`/`ValueError` and treats an
     over-long path as "not a file".

5. **Handle dependency-resolution divergence with a documented cap, not a silence.** The new
   resolver may also pick newer transitive deps whose behavior/type-stubs differ. uv resolved
   numpy 2.5.1 whose PEP 695 `type X =` stubs fail mypy under `target-version = py310`. **Real
   fix:** cap `numpy<2.5` to restore the last-known-good behavior, with an inline comment
   explaining the stub regression — a genuine version-cap, not a workaround.

6. **Reconcile the "ships no Python" ADR/convention conflict as a tooling-only pyproject.** If a
   repo policy forbids a top-level `pyproject.toml` but the uv migration needs one to lock the
   build toolchain, make it a TOOLING-ONLY manifest (see Results & Parameters) and narrow the
   forbidding check to fail only when the pyproject actually SHIPS a Python package.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Trust the old-manager green | Treated "green under the old env manager" as proof the code was correct | The new manager's different Python version then failed CI — the old interpreter had merely tolerated a latent bug | "Green before the migration" proves tolerance, not correctness; compare the resolved interpreter delta before trusting a migration |
| Weaken the scipy assertion | Considered relaxing the `p > 0.05` test to also accept `NaN` | Would hide a real degenerate-input bug where identical distributions produced no valid p-value | Fix the source: add an all-ties guard returning `p=1.0`; identical distributions are not significant |
| Let uv pick the interpreter | Ran the uv migration without pinning `.python-version` | uv silently resolved a different Python than the old manager, conflating a toolchain change with a version change | Pin the interpreter to the old manager's version so the two changes are isolated and reviewable |
| Forbid the pyproject on existence | Kept the "ships no Python" check failing on mere presence of `pyproject.toml` | Blocked the tooling-only uv manifest needed to lock the build toolchain | Narrow the check to fail only when the pyproject actually ships a package (`package != false` or has scripts/packages) |

## Results & Parameters

### Configuration

**Interpreter pin (isolate toolchain change from version change):**

```text
# .python-version  (committed; matches the version the OLD manager resolved)
3.14
```

```bash
uv python pin 3.14   # avoid uv silently grabbing a newer/older Python
```

**scipy all-ties degenerate guard (source fix, not a test weakening):**

```python
# identical distributions are NOT significant -> p = 1.0, never NaN
if _all_ties(sample_a, sample_b):
    return MannWhitneyResult(statistic=0.0, pvalue=1.0)
return scipy.stats.mannwhitneyu(sample_a, sample_b)
```

**OSError-catch helper for over-long paths (py3.12 ENAMETOOLONG):**

```python
def safe_is_file(path: str) -> bool:
    # py3.14 is_file() swallows ENAMETOOLONG; py3.12 raises OSError [Errno 36]
    try:
        return Path(path).is_file()
    except (OSError, ValueError):
        return False
```

**numpy cap for the mypy PEP-695 stub regression (documented dependency cap):**

```toml
# numpy 2.5.x ships PEP 695 `type X =` stubs that fail mypy under
# target-version = py310; cap to the last-known-good behavior.
numpy<2.5
```

**Tooling-only pyproject to reconcile a "ships no Python" repo with a uv build-toolchain lock:**

```toml
[project]
name = "keystone-buildtools"   # <repo>-buildtools, tooling identity only

[tool.uv]
package = false                 # does NOT ship a Python package

[dependency-groups]
dev = ["mypy", "ruff"]          # build/dev tooling ONLY
# no [project.scripts], no packages, no distributable module
```

Narrow the forbidding check so it fails only if the pyproject actually SHIPS a package:

```bash
# check-extraction.sh: fail only when pyproject ships Python
# (package != false, OR has [project.scripts]/packages), not on mere existence.
```

### Expected Output

- The interpreter delta is identified and pinned via a committed `.python-version` before the
  migration is trusted as green
- Every newly-surfaced failure is diagnosed as either a REAL latent bug (fixed in source) or a
  genuine version/behavior regression (fixed with a documented dependency cap)
- No test is skipped, `xfail`ed, weakened, or deleted to make the migration "pass"
- A "ships no Python" repo can still lock its uv build toolchain via a `package = false`
  tooling-only pyproject, with the forbidding check narrowed to package-shipping pyprojects

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | HomericIntelligence pixi->uv migration | pixi resolved py3.14, uv pinned py3.12; two latent bugs surfaced only under 3.12 — scipy `mannwhitneyu` all-ties `p=NaN` (fixed with a `p=1.0` guard) and `Path.is_file()` ENAMETOOLONG `OSError` (fixed with an OSError-catch helper); numpy resolved to 2.5.1 whose PEP-695 stubs failed mypy under `py310` (capped `numpy<2.5`) |
| Keystone | ADR-016 ("Keystone ships no Python") vs ADR-018 uv migration | `check-extraction.sh` narrowed to allow a `package = false` tooling-only pyproject that locks the build toolchain without shipping a Python package |
