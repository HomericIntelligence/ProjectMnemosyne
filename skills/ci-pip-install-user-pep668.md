---
name: ci-pip-install-user-pep668
description: "Use pip install --user in GitHub Actions to guard against PEP 668 externally-managed-environment errors. Use when: (1) writing a pip install step in a GitHub Actions workflow that does NOT use actions/setup-python first, (2) the job installs pyyaml, yamllint, or any other package on ubuntu-latest, (3) you see 'error: externally-managed-environment' from pip on a CI runner, (4) reviewing workflow run: steps that use bare pip install <pkg>, (5) future-proofing pip installs against runner image upgrades that enforce PEP 668."
category: ci-cd
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - ci-cd
  - pip
  - pep668
  - github-actions
  - ubuntu-latest
  - python
  - externally-managed-environment
  - pyyaml
  - yamllint
  - runner
  - future-proofing
  - workflow
---

# CI pip install --user: PEP 668 Protection in GitHub Actions

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Future-proof `pip install` steps in GitHub Actions workflow `run:` blocks against PEP 668 (`externally-managed-environment`) errors |
| **Outcome** | Successful — `pip install --user <pkg>` pattern adopted in Odysseus PR #330; review comment required fix across ALL jobs in a workflow (not just the one flagged) |
| **Verification** | `verified-local` — pre-commit clean; CI on PR #330 pending |
| **Source** | HomericIntelligence/Odysseus issue #198 / PR #330 code review |

## When to Use

- Writing a `pip install <pkg>` step in a GitHub Actions `run:` block that does NOT use `actions/setup-python` first.
- Installing `pyyaml`, `yamllint`, or any Python package on `ubuntu-latest` runners in workflow steps.
- A CI job shows `error: externally-managed-environment` from pip (PEP 668 enforcement).
- Reviewing PR workflow changes that add bare `pip install <pkg>` without `--user` or `actions/setup-python`.
- After adding `--user` to one job in a workflow in response to a review comment — check EVERY other job in the same workflow for the same pattern.

## Verified Workflow

### Quick Reference

```yaml
# WRONG — works today but not future-proof against PEP 668
- name: Install PyYAML
  run: pip install pyyaml

# RIGHT — always use --user when not using actions/setup-python
- name: Install PyYAML
  run: pip install --user pyyaml

- name: Install yamllint
  run: pip install --user yamllint
```

### The Two Approaches

**Option A: `pip install --user` (lighter weight, preferred)**

```yaml
steps:
  - uses: actions/checkout@v4
  - name: Install PyYAML (for compose validator)
    run: pip install --user pyyaml
  - name: Validate docker-compose files
    run: python3 tools/validate_compose.py e2e/docker-compose.yml
```

**Option B: `actions/setup-python` (heavier, use when pinning Python version)**

```yaml
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - name: Install PyYAML
    run: pip install pyyaml   # safe: setup-python manages its own env
  - name: Validate docker-compose files
    run: python3 tools/validate_compose.py e2e/docker-compose.yml
```

### Detailed Steps

1. **Audit every `pip install` step in the workflow.** Search ALL jobs in the file — not just the job being modified. A review comment about `--user` applies to every `pip install` in the file.

```bash
grep -n "pip install" .github/workflows/*.yml
```

2. **For each `pip install` step without `actions/setup-python` before it, add `--user`.**

3. **Verify `--user` is present in every affected job.** If a reviewer flags one job and you fix only that one, the review will be re-opened for the others. Fix all at once.

4. **Do not add `--user` to pip install steps that run inside `actions/setup-python`'s managed environment** — there it is unnecessary (and slightly awkward). Only add it to bare `pip install` steps that target the runner's system Python.

### Why `--user` Works

- `pip install --user <pkg>` installs into `~/.local/lib/python3.x/site-packages/`, which is not managed by the OS package manager and is not subject to PEP 668 restrictions.
- PEP 668 allows distros to mark system Python as "externally managed" to prevent pip from corrupting system packages. When enforced, bare `pip install` fails with: `error: externally-managed-environment`.
- `ubuntu-latest` runners do NOT enforce PEP 668 today (as of mid-2026), so bare `pip install` works — but this is not guaranteed for future runner image upgrades.
- `--user` installs are available on `$PATH` for scripts invoked via `python3 -m <pkg>` and for packages that provide console scripts (e.g., `yamllint`).

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Bare `pip install pyyaml` | Used in first draft of compose-validator CI step | Works today but not future-proof; reviewer flagged as PEP 668 risk | Always use `pip install --user` in workflow `run:` blocks that don't use `actions/setup-python` |
| Fixing only one job | Fixed `--user` in the `validate-configs` job after review comment | Reviewer re-opened because `validate-recipes` job also had bare `pip install yamllint` | When a reviewer flags a pattern, fix it in ALL occurrences in the workflow file, not just the one cited |

## Results & Parameters

```yaml
# Pattern to follow for all pip install steps in GitHub Actions
pip_install_rule:
  with_setup_python: "pip install <pkg>"        # safe — managed env
  without_setup_python: "pip install --user <pkg>"  # REQUIRED — system python

# Common packages in HomericIntelligence CI workflows
common_packages:
  - "pip install --user pyyaml"      # compose validator, YAML parsing
  - "pip install --user yamllint"    # config linting (yamllint depends on pyyaml)
  - "pip install --user pytest"      # only if not using pixi/setup-python

# Audit command — run before submitting any workflow PR
audit_command: "grep -n 'pip install' .github/workflows/*.yml"
# Flag any line that: (1) does NOT have --user, AND (2) is NOT preceded by actions/setup-python

pep668_status_on_ubuntu_latest:
  enforced_today: false         # as of mid-2026, bare pip install still works
  future_risk: true             # runner image upgrades may enforce PEP 668
  safe_pattern: "--user"        # install into ~/.local, bypasses PEP 668
```

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| HomericIntelligence/Odysseus | 2026-06-20, issue #198, PR #330 code review | Two separate review round-trips: first fixed one job, second fixed both jobs. Final workflow has `pip install --user pyyaml` in `validate-configs` job and `pip install --user yamllint` in `validate-recipes` job. |

## References

- [PEP 668 — Marking Python base environments as externally managed](https://peps.python.org/pep-0668/)
- [Odysseus issue #198](https://github.com/HomericIntelligence/Odysseus/issues/198)
- [Odysseus PR #330](https://github.com/HomericIntelligence/Odysseus/pull/330)
- [ci-config-validators-binary-free-python skill](ci-config-validators-binary-free-python.md) — the validators that use these pip installs
