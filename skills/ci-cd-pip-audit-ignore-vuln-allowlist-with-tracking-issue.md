---
name: ci-cd-pip-audit-ignore-vuln-allowlist-with-tracking-issue
description: "Allowlist specific pip-audit CVE findings inline via repeated `--ignore-vuln <ID>` flags with a tracking issue + planned review date. Use when: (1) pip-audit step is being flipped from advisory (`|| echo \"::warning::\"`, `--exit-code 0`, or wrapped in `if !`) to fail-fast and real CVE findings surface, (2) findings are in baseline runner-image packages (pip, setuptools, urllib3, etc.) that the repo doesn't directly control, (3) findings are in transitive deps with no upstream fix yet, (4) need a documented allowlist mechanism that's clearly NOT `|| true`/`::warning::`/`--exit-zero` (per the no-silent-failures policy), (5) replacing `pixi-pip-audit-cve-pinning` (bump deps) or `pixi-pip-audit-severity-filter` (filter by severity) — those work when you control the dep version; this skill is for when you don't."
category: ci-cd
date: 2026-05-11
version: "1.0.0"
user-invocable: false
verification: verified-ci
tags:
  - pip-audit
  - cve
  - allowlist
  - ignore-vuln
  - tracking-issue
  - fail-fast
  - security-scan
  - baseline-runner-cve
  - transitive-deps
---

# ci-cd-pip-audit-ignore-vuln-allowlist-with-tracking-issue

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-11 |
| **Objective** | Allowlist specific pip-audit CVE findings via `--ignore-vuln` flags with a tracking issue, so a fail-fast `pip-audit` step in CI doesn't block PRs on known-and-tracked findings that the repo can't immediately fix. |
| **Outcome** | Used in 3 PRs (Myrmidons#712, AchaeanFleet#656, ProjectOdyssey#5387) — total 107 CVEs allowlisted with 3 tracking issues (Myrmidons#713, AchaeanFleet#655, ProjectOdyssey#5386). All three PRs' `security/dependency-scan` checks went green. |
| **Verification** | verified-ci |

## When to Use

- pip-audit step is being flipped from advisory mode to fail-fast (per `ci-cd-forbid-suppressions-pygrep-lint-guard` v2.0.0 Bucket F)
- CVE findings surface that are in the runner image's baseline Python packages (pip, setuptools, requests, urllib3, jinja2, cryptography, etc.) — the repo itself declares zero or minimal PyPI deps
- CVE findings are in transitive deps where no upstream fix exists yet (e.g., pip 25.3 CVE-2026-3219, mistune CVE-2026-44708)
- You explicitly want a documented, reviewable allowlist mechanism rather than `pixi-pip-audit-severity-filter`'s blanket severity reduction
- The repo cannot easily bump the affected dep version (vs. `pixi-pip-audit-cve-pinning` which works when you can)

## Verified Workflow

### 1. Confirm fail-fast first

The whole point of this skill is to keep pip-audit in fail-fast mode. Don't read this skill if you're keeping `|| true`/`::warning::` wrappers — fix that first per `ci-cd-forbid-suppressions-pygrep-lint-guard`.

### 2. Surface the actual finding set

Locally:

```bash
pip-audit --desc --strict 2>&1 | tee /tmp/pip-audit-findings.log
```

Or from CI (preferred — runner-image differs from local):

```bash
gh run list --repo HomericIntelligence/<repo> --branch <PR branch> --workflow=<workflow file> --limit 5
gh run view <run-id> --repo HomericIntelligence/<repo> --log-failed 2>&1 | grep -E "ID:|GHSA-|CVE-|PYSEC-" | head -200
```

### 3. Classify each finding

- **(A) Own-dep finding** (in `pixi.toml [pypi-dependencies]` or `requirements*.txt`) → bump the dep version. Use `pixi-pip-audit-cve-pinning` skill. Don't allowlist.
- **(B) Runner-baseline finding** (pip, setuptools, requests, etc., from the runner image's Python env, NOT in the repo's deps) → allowlist with this skill's pattern.
- **(C) Transitive-dep finding with no upstream fix yet** → allowlist with this skill's pattern AND note in the tracking issue that the upstream is unresolved.

### 4. Open a tracking issue

```bash
gh issue create --repo HomericIntelligence/<repo> \
  --title "pip-audit: <runner-image|transitive-deps> CVEs allowlist (review YYYY-MM-DD)" \
  --body "$(cat <<EOF
Tracking issue for the <type> CVEs surfaced by the fail-fast pip-audit step in PR #<N>.

Per the no-silent-failures policy (HomericIntelligence/Odysseus#280, #282), pip-audit runs in fail-fast mode. These CVEs are <runner-baseline / transitive-with-no-upstream-fix>; the repo's own deps don't include them <or: include them via X transitive>.

Review date: $(date -d '+90 days' +%Y-%m-%d)

Findings (from CI run <id>):
- GHSA-XXXX-XXXX-XXXX: <package version> — <brief description>
- CVE-YYYY-NNNNN:     <package version> — <brief description>
- PYSEC-YYYY-NNN:     <package version> — <brief description>
...

Resolution path:
- [ ] On <review-date>, re-check whether the runner image refresh / upstream fix has landed
- [ ] If yes: remove the corresponding --ignore-vuln flag and verify pip-audit still passes
- [ ] If no: bump the review date by another 90 days and document why
EOF
)"
```

Capture the issue number — you'll reference it in the workflow.

### 5. Add `--ignore-vuln` flags with tracking comment

Edit the pip-audit step in the workflow:

```yaml
- name: pip-audit
  run: |
    set -euo pipefail
    pip install --quiet pip-audit
    # Baseline runner-image CVEs allowlisted per issue #<N> (review YYYY-MM-DD).
    # Each --ignore-vuln below corresponds to a finding in #<N>; revisit after
    # ubuntu-latest base image refreshes / upstream fix lands.
    pip-audit \
      --ignore-vuln GHSA-XXXX-XXXX-XXXX \
      --ignore-vuln CVE-YYYY-NNNNN \
      --ignore-vuln PYSEC-YYYY-NNN \
      ...
```

NO `|| true`, NO `continue-on-error: true`, NO `::warning::`, NO `--exit-code 0`, NO `--exit-zero`. The tool runs fail-fast; only the explicit finding set is narrowed.

### 6. Verify

```bash
# Local
pip-audit --ignore-vuln <ID1> --ignore-vuln <ID2> ...
# Should report no findings if the allowlist is complete

# Push and watch CI
git add .github/workflows/<file>.yml
git commit -m "ci: allowlist <runner-image|transitive-deps> pip-audit findings (#<issue>)"
git push
gh run watch <run-id> --repo HomericIntelligence/<repo>
```

### Quick Reference

```yaml
- name: pip-audit
  run: |
    set -euo pipefail
    pip install --quiet pip-audit
    # Allowlist tied to issue #<N> (review YYYY-MM-DD)
    pip-audit \
      --ignore-vuln <ID-1> \
      --ignore-vuln <ID-2> \
      ...
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---|---|---|---|
| 1 | `pip-audit \|\| true` (the original suppression that this skill replaces) | Banned by `ci-cd-forbid-suppressions-pygrep-lint-guard` v1.0.0 (Bucket A). Also: silently swallowed all findings indefinitely. | Use `--ignore-vuln` per finding, with a tracking issue. |
| 2 | `if ! pip-audit; then echo "::warning::..."; fi` (the Bucket E refactor) | Banned by v2.0.0 Bucket F. CI step still passes when findings exist. | Same — use `--ignore-vuln` per finding. |
| 3 | `pip-audit --exit-code 0` or `pip-audit --exit-zero` | Tool-level opt-out flag, equivalent to `\|\| true`. Banned by v2.0.0. | Banned. Use `--ignore-vuln` per finding. |
| 4 | Allowlisted the entire vulnerable package via `--ignore-package` (which pip-audit doesn't support — that flag doesn't exist) and assumed it would work | pip-audit only supports `--ignore-vuln <ID>`. There is no per-package ignore. Trying `--ignore-package` fails with `unrecognized arguments`. | Use `--ignore-vuln <ID>` per finding ID, not per package. If a package has many CVEs, list every ID. |
| 5 | Allowlisted CVEs in a separate `.pip-audit-allowlist` file referenced via `--ignore-vuln-file <path>` | pip-audit 2.x does not support a file-based allowlist. Only CLI flags. | Inline `--ignore-vuln <ID>` flags are the supported pattern; the file-based approach is a wishlist item upstream (pip-audit issue #XXX, no fix). |
| 6 | Bumped the affected dep version (`pixi-pip-audit-cve-pinning` skill) for runner-baseline packages | Runner-baseline packages live in the runner image's system Python env, NOT in the repo's `pixi.toml`. Bumping in pixi has no effect on the runner image's pip/setuptools/etc. | When the package is baseline-runner-image, allowlist (this skill). When it's a project dep, bump (`pixi-pip-audit-cve-pinning`). |
| 7 | Set `pip-audit --severity HIGH` to narrow scope (`pixi-pip-audit-severity-filter` skill) | Blanket severity filter loses visibility on MEDIUM findings that may matter. Also: doesn't track which findings were silenced or why. | Severity filter is a less-precise tool. Use it only if you have a documented reason to ignore an entire severity band (e.g., "we accept all MEDIUM in dev branches"). Otherwise prefer per-finding `--ignore-vuln`. |
| 8 | Committed the allowlist WITHOUT opening a tracking issue | Six months later, no one remembers why the CVEs were ignored. Allowlist drifts permanent. | Always open the tracking issue FIRST, reference its number in the inline comment AND the commit message, set a review date in the issue body. |

## Results & Parameters

The verified-ci uses of this pattern:

| Repo | PR | Tracking issue | CVE count | Categorization | Review date |
|---|---|---|---|---|---|
| HomericIntelligence/Myrmidons | #712 | #713 | 37 unique IDs across 15 packages | Runner-baseline (none in own deps) | 2026-08-08 |
| HomericIntelligence/AchaeanFleet | #656 | #655 | 57 unique IDs across 14 packages | Transitive (via aider-chat) — most fixable by upstream bump | 2026-08-10 |
| HomericIntelligence/ProjectOdyssey | #5387 | #5386 | 13 unique IDs across 5 packages | Mix: transitive + 2 with no upstream fix yet | 2026-08-11 |

Notes:

- pip 25.3's `CVE-2026-3219` has no upstream fix at time of writing — flagged in issue #5386 as "may stay allowlisted long-term."
- mistune's `CVE-2026-44708` similar status.
- Each allowlist entry should be re-validated on the review date. The `gh issue list --label "pip-audit-allowlist"` query lets you find all such tracking issues at once.

## Verified On

| Project | Context | Details |
|---|---|---|
| HomericIntelligence/Myrmidons | PR #712 — pip-audit flipped to fail-fast in `_required.yml:132`, 37 baseline-runner CVEs allowlisted | Issue #713, review 2026-08-08 |
| HomericIntelligence/AchaeanFleet | PR #656 — pip-audit flipped to fail-fast in `ci.yml:247` (after fixing the broken `--require aider-chat` argparse), 57 transitive CVEs allowlisted | Issue #655, review 2026-08-10. Also exposed an argparse silent-mismatch bug — see `debugging-argparse-ambiguous-flag-silent-mismatch` |
| HomericIntelligence/ProjectOdyssey (research) | PR #5387 — pip-audit flipped to fail-fast in `_required.yml:252`, 13 CVEs allowlisted | Issue #5386, review 2026-08-11 |
