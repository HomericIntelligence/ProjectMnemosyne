---
name: tooling-portable-shared-repo-fork-resolution
description: "Make a hardcoded shared-knowledge-base repo reference (e.g. HomericIntelligence/Mnemosyne) org-aware/portable via a clone-or-fork resolution ladder, so any GitHub user can read and contribute to it instead of only the canonical org. Use when: (1) a script/skill hardcodes an `owner/repo` slug everywhere and only that org can use it, (2) /learn or /advise-style automation always targets the canonical upstream and you want it to target the caller's own fork, (3) you need a single resolver returning the correct owner/slug across env-override > gh-login-fork > upstream-fallback, (4) you must mirror the same resolution logic across a Python source-of-truth and a bash SKILL.md (cannot import Python), (5) you are about to call `gh repo fork` programmatically and need to handle the can't-fork-into-own-org case."
category: tooling
date: 2026-06-27
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags: ["gh-cli", "fork", "repo-resolution", "portability", "dry", "python-bash-mirror"]
---

# Portable Shared-Repo Fork Resolution

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-06-27 |
| **Objective** | A hardcoded `HomericIntelligence/Mnemosyne` slug was scattered across skills (/advise, /learn) AND the Python automation pipeline, so only that org could use the shared knowledge base and every /learn PR targeted the canonical upstream. Make it work for any GitHub user. |
| **Outcome** | Successful — one shared Python resolver + mirrored bash ladder; automation targets the caller's own fork (created on demand). |
| **Verification** | verified-ci (merged as ProjectHephaestus PR #1668, all required CI green) |

## When to Use

- A script or skill hardcodes a shared `owner/repo` slug and only the original org can use it.
- A knowledge-base/automation flow always opens PRs against the canonical upstream instead of the caller's own fork.
- You need a single resolver returning `(owner, slug, is_fork_of_upstream)` with a clear precedence ladder.
- You must keep the same resolution logic in Python (source of truth) AND in bash inside a SKILL.md (skills cannot import Python).
- You are about to call `gh repo fork` from code and must handle "the login IS the upstream owner" (cannot fork a repo into its own org).

## Verified Workflow

### Quick Reference

```python
# hephaestus/github/mnemosyne_repo.py — single source of truth
from dataclasses import dataclass

UPSTREAM_OWNER = "HomericIntelligence"
UPSTREAM_SLUG = f"{UPSTREAM_OWNER}/Mnemosyne"

@dataclass(frozen=True)
class MnemosyneTarget:
    owner: str
    slug: str
    is_fork_of_upstream: bool

def resolve_mnemosyne_target(*, override_owner=None, allow_fork=True) -> MnemosyneTarget:
    # 1. explicit override (env HEPH_MNEMOSYNE_OWNER or arg)
    owner = override_owner or os.environ.get("HEPH_MNEMOSYNE_OWNER")
    if owner:
        if owner == UPSTREAM_OWNER:
            return MnemosyneTarget(owner, UPSTREAM_SLUG, False)
        slug = f"{owner}/Mnemosyne"
        return MnemosyneTarget(owner, slug, True)
    # 2. gh-authenticated login -> its own fork (create if missing)
    login = gh_authenticated_login()           # gh api user --jq .login (via gh_call)
    if login and login != UPSTREAM_OWNER:
        slug = f"{login}/Mnemosyne"
        if remote_repo_exists(slug) or (allow_fork and fork_upstream(login)):
            return MnemosyneTarget(login, slug, True)
    # 3. login IS upstream owner, or undeterminable -> upstream directly
    return MnemosyneTarget(UPSTREAM_OWNER, UPSTREAM_SLUG, False)
```

```bash
# Mirror the SAME ladder in bash inside SKILL.md (skills can't import Python)
resolve_mnemosyne_target() {
  local upstream_owner="HomericIntelligence"
  local owner="${HEPH_MNEMOSYNE_OWNER:-}"
  if [ -z "$owner" ]; then owner="$(gh api user --jq .login 2>/dev/null || true)"; fi
  if [ -z "$owner" ] || [ "$owner" = "$upstream_owner" ]; then
    echo "$upstream_owner/Mnemosyne"; return
  fi
  if gh repo view "$owner/Mnemosyne" --json name >/dev/null 2>&1; then
    echo "$owner/Mnemosyne"; return
  fi
  gh repo fork "$upstream_owner/Mnemosyne" --clone=false >/dev/null 2>&1 || true
  echo "$owner/Mnemosyne"
}
```

### Detailed Steps

1. **Create ONE Python resolver as source of truth.** `resolve_mnemosyne_target(*, override_owner=None, allow_fork=True) -> MnemosyneTarget(owner, slug, is_fork_of_upstream)` with a frozen dataclass return. Precedence: (1) `HEPH_MNEMOSYNE_OWNER` env/arg override; (2) gh-authenticated login's own `<login>/Mnemosyne` fork, created via `gh repo fork` if absent — but if the login IS the upstream owner, clone upstream directly (you cannot fork a repo into its own org); (3) fall back to upstream if the login is undeterminable.
2. **Add small single-purpose gh helpers**: `gh_authenticated_login()` = `gh api user --jq .login`; `remote_repo_exists(slug)` = `gh repo view <slug> --json name`; `fork_upstream(owner)` = `gh repo fork <upstream> --clone=false`.
3. **Route EVERY gh call through the existing rate-limit / circuit-breaker adapter** (`gh_call`) — never bare `subprocess.run(["gh", ...])`. Reuse existing timeout constants (`METADATA_TIMEOUT`, `NETWORK_TIMEOUT`) rather than inventing new ones.
4. **Wire the automation through the resolver.** The clone step (`advise_runner._clone_mnemosyne`) clones the resolved slug, not the hardcoded one.
5. **Broaden evidence/confirmation regexes.** Change `HomericIntelligence/Mnemosyne` literals to `[A-Za-z0-9._-]+/Mnemosyne` so a push to a fork still counts as confirmation in /learn evidence checks.
6. **Mirror the ladder into the SKILL.md bash** as a `resolve_mnemosyne_target` shell function. Keep the canonical `skills/<name>/SKILL.md` and the plugin-mirror `plugins/hephaestus/skills/<name>/SKILL.md` BYTE-IDENTICAL (`diff -q` them) — every skill exists in two trees.
7. **Add tests that patch the resolver, not the literal.** New tests in `tests/unit/github/test_mnemosyne_repo.py` mock `gh_call` at the module namespace; tests that previously asserted the old literal in a clone command must patch `resolve_mnemosyne_target` and assert the resolved slug.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Fork into own org | Call `gh repo fork` unconditionally for the login | `gh` cannot fork a repo into the org that already owns it; the login may BE the upstream owner | Branch on `login == UPSTREAM_OWNER` → clone/target upstream directly, skip the fork |
| Keep the hardcoded test assertion | Test asserted `"HomericIntelligence/Mnemosyne" in clone_cmd` | Once resolution is dynamic the clone command contains the resolved fork slug, so the assertion breaks | Patch `resolve_mnemosyne_target` in the test and assert the resolved slug instead of the upstream literal |
| Mock only `gh_call` generically | Tests mocked `gh_call` to return a bare `MagicMock` | `.stdout.strip()` on a MagicMock is truthy, so the login resolver treated the mock as a real login and went down the fork path | Patch the resolver itself (or give `gh_call` a concrete `stdout` string), not just a generic `gh_call` mock |
| Narrow confirmation regex | Left evidence regex matching only `HomericIntelligence/Mnemosyne` | A push to a user's fork (`<login>/Mnemosyne`) no longer matched, so /learn never registered confirmation | Broaden to `[A-Za-z0-9._-]+/Mnemosyne` |
| Duplicate logic in bash by hand | Re-implemented the ladder in bash independently of the Python | Drift risk: the two copies silently diverge | Treat Python as source of truth and deliberately MIRROR it in bash; document that every skill lives in two byte-identical trees and `diff -q` them |
| Pre-arm auto-merge on the Heph PR | `gh pr merge --auto` before `state:implementation-go` | The `auto-merge-policy` CI gate fails if auto-merge is armed before the GO label (documented convention; gate happened to be non-required here) | On ProjectHephaestus, arm auto-merge only after the GO label. NOTE: this gate is specific to HomericIntelligence/ProjectHephaestus — other repos (incl. Mnemosyne) have no such gate |

## Results & Parameters

- **Language**: Python 3.10+.
- **Env override var**: `HEPH_MNEMOSYNE_OWNER`.
- **Return type**: `MnemosyneTarget` — a frozen dataclass `(owner: str, slug: str, is_fork_of_upstream: bool)`.
- **Resolver module**: `hephaestus/github/mnemosyne_repo.py` (single source of truth).
- **Tests**: `tests/unit/github/test_mnemosyne_repo.py`, mocking `gh_call` at the module namespace.
- **Reuse-before-invent survey** (existing infra in this repo to reuse rather than re-writing subprocess patterns):
  - `gh_call` — rate-limit + circuit-breaker gh adapter (route all gh calls through it)
  - `fleet_sync.ensure_repo_clone` — idempotent clone
  - `loop_repo_manager._detect_cwd_repo` — cwd repo detection
  - `git_utils.get_repo_info` — repo metadata
  - `resolve_fleet_config` / `resolve_projects_dir` — the override > env > config > cwd precedence pattern to model the ladder after
- **Cross-reference**: for making a hardcoded LOCAL filesystem path portable (CLI arg > env var > default), see the related `fix-hardcoded-target-path` skill. This skill is the GitHub-slug / fork-resolution analog.
- **Merge-policy gotcha**: don't pre-arm `gh pr merge --auto` on ProjectHephaestus before the `state:implementation-go` label (auto-merge-policy gate). This is Hephaestus-specific.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #1668 (org-aware Mnemosyne resolution), all required CI green | resolver `hephaestus/github/mnemosyne_repo.py`; tests `tests/unit/github/test_mnemosyne_repo.py` |
