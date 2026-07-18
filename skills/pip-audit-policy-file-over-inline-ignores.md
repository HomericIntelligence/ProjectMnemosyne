---
name: pip-audit-policy-file-over-inline-ignores
description: "Route a task-runner audit recipe (just/pixi/make 'audit') through the repo's configured suppression-policy mechanism — a severity-filter CLI reading a policy file (e.g. pip-audit --format json | hephaestus-filter-audit + .pip-audit-ignore.txt) — instead of raw pip-audit with inline --ignore-vuln flags. Use when: (1) an audit finding says 'just audit runs raw pip-audit rather than the configured/Pixi task carrying the suppression policy', (2) the same advisory ID is hardcoded as --ignore-vuln in multiple places (justfile + CI workflows), (3) an issue references tooling that no longer exists after a build-system migration (Pixi→uv) and you must map 'the configured policy' to the current mechanism via git log -S, (4) carrying an inline suppression into a policy file — first run the scanner live to check the advisory still fires (pip advisories stop firing under uv because uv envs omit pip), (5) deciding whether to widen the fix to CI — switching CI from fail-on-any-vuln raw pip-audit to a HIGH/CRITICAL-only filter WEAKENS the gate and needs its own issue, (6) adding a repo-root policy file — first grep unit tests for default-path lookups that could flip."
category: tooling
date: 2026-07-17
version: "1.0.0"
verification: verified-local
tags: [pip-audit, suppression-policy, ignore-vuln, justfile, uv-migration, severity-filter, security-scanning, stale-tooling-reference]
---

# Route Task-Runner Audit Recipes Through the Policy-File Filter, Not Inline `--ignore-vuln`

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-17 |
| **Objective** | Plan the fix for ProjectHephaestus issue #2167: `just audit` ran raw `uv run pip-audit --ignore-vuln PYSEC-2025-183` instead of the repository's configured audit policy (`hephaestus-filter-audit` + `.pip-audit-ignore.txt`) |
| **Outcome** | Implementation plan posted to #2167: pipe `pip-audit --format json` into the filter CLI, move the suppression into a commented `.pip-audit-ignore.txt`, add bats recipe-wiring tests; CI workflows deliberately left out of scope |
| **Verification** | verified-local — planning-stage evidence only: live `uv run pip-audit --format json` run (0 vulns, proving the carried suppression no longer fires), filter-CLI source inspection, unit-test default-path audit, and `git log -S` provenance trace. The justfile change itself had not merged when this was written |

## When to Use

- An audit/repo-review finding reads like "`just audit` runs raw pip-audit rather than the
  task that carries the project suppression policy."
- The same advisory ID appears inline (`--ignore-vuln <ID>`) in several places — task runner
  recipe plus one or more CI workflows — i.e. the suppression policy has no single source.
- The issue names tooling the repo no longer uses (e.g. "the Pixi task" after a Pixi→uv
  migration) and you must resolve what "the configured policy" means *today*.
- You are about to copy an old inline suppression into a policy file and need to know whether
  it still fires at all.
- You are tempted to "finish the job" by also switching CI to the severity filter.

## Verified Workflow

### 1. Identify the repo's actual configured-policy mechanism (not the issue's stale name)

The issue said "the Pixi task", but the repo had migrated Pixi→uv. Resolve the current
mechanism from the repo itself:

```bash
# Who owns audit filtering today?
grep -n "audit" pyproject.toml          # -> hephaestus-filter-audit = "hephaestus.validation.audit:main"
sed -n '1,15p' hephaestus/validation/audit.py   # docstring documents the intended pipeline:
# pip-audit --format json | hephaestus-filter-audit  (+ .pip-audit-ignore.txt at repo root)

# Where did the inline suppression come from?
git log --all --oneline -S "PYSEC-2025-183"     # -> introduced #425 (pixi era), preserved by uv migration #2236
```

Key point: `git log -S <advisory-id>` is the fastest way to prove a stale-terminology issue
maps to a real current defect rather than being obsolete.

### 2. Verify the carried-over suppression still fires BEFORE preserving it

```bash
uv run pip-audit --format json > /tmp/audit.json; echo "exit=$?"
# -> exit=0, "No known vulnerabilities found"
```

The suppressed advisory (PYSEC-2025-183, a `pip` advisory) no longer fired: uv-managed
environments do not install `pip`, so pip advisories vanish after a Pixi/venv→uv migration.
Record that in the policy file instead of silently keeping a dead flag:

```text
# Carried over from the inline --ignore-vuln flag (introduced in #425,
# preserved through the uv migration in #2236). No longer fires in the
# uv-managed environment; retained for parity with the CI workflows'
# inline suppression until those are migrated.
PYSEC-2025-183
```

### 3. Rewrite the recipe as the policy pipeline

```just
audit:
    uv run pip-audit --format json | uv run hephaestus-filter-audit
```

Pipe-exit semantics are safe by design: `just` runs recipes via `sh -c` without `pipefail`,
so the pipeline's exit code is the *filter's* — the filter is the policy decision point.
Malformed/empty scanner output is handled by the filter's input parser returning non-zero.

### 4. Audit blast radius of the new repo-root policy file

Before adding `.pip-audit-ignore.txt` at the repo root, grep the unit tests for the loader's
default-path behavior: a test asserting "returns empty set when no file exists" against the
repo root would flip. (Here `tests/unit/validation/test_audit.py` used only explicit
`tmp_path` paths — safe.)

### 5. Scope: do NOT silently migrate CI to the filter

CI ran raw `pip-audit --ignore-vuln <ID>` (fails on **any** vuln). The filter blocks only
HIGH/CRITICAL (CVSS ≥ 7.0). Switching CI to the filter **weakens the required gate** — that
is a policy-semantics change needing its own issue, not a rider on a MINOR recipe fix. Note
the parity intent in the policy-file comment instead.

### 6. Prove the policy file is actually read

The filter prints `pip-audit: ignoring N advisory ID(s)` when it loads the ignore file — make
that observable line part of the acceptance evidence, plus a direct loader check:

```bash
uv run python -c "from hephaestus.validation.audit import load_ignore_list; assert 'PYSEC-2025-183' in load_ignore_list()"
```

Add task-runner tests in the repo's existing style (bats asserting the recipe exists via
`just --list`, plus a recipe-body assertion that the pipeline is wired and no `--ignore-vuln`
remains).

## Failed Attempts / Traps

| Attempt | Why it fails |
|---------|--------------|
| Reading the issue literally and looking for a Pixi task to call | The repo migrated Pixi→uv; the named mechanism no longer exists. Resolve the *intent* (configured suppression policy) against current tooling via `git log -S` |
| Copying the inline advisory ID into the policy file without a live scanner run | Preserves a dead suppression with no provenance; nobody later knows whether removing it is safe |
| Also switching CI workflows to the severity filter "for DRY" | Changes CI from fail-on-any-vuln to fail-on-HIGH/CRITICAL — a silent gate weakening; needs its own reviewed issue |
| Assuming a repo-root config file is additive-only | Loader default-path lookups in unit tests can flip when the file appears; grep tests for the default path first |

## Results & Parameters

- Result: implementation plan for #2167 delivered (recipe pipeline + commented policy file +
  two bats tests); live-run evidence showed 0 current vulnerabilities, so the recipe change
  is behavior-neutral today while centralizing the policy.
- Advisory/scanner pair here: `pip-audit` + PYSEC advisory IDs; the pattern generalizes to any
  scanner with inline ignore flags vs a policy-file-driven wrapper.
- Severity threshold of the filter: CVSS ≥ 7.0 (HIGH/CRITICAL) blocking; below → warning.

## Evidence

- ProjectHephaestus issue #2167 (`[mino] Make just audit use the configured audit policy`).
- Live run: `uv run pip-audit --format json` → exit 0, "No known vulnerabilities found"
  (2026-07-17), proving PYSEC-2025-183 no longer fires under uv.
- Provenance: `git log --all -S "PYSEC-2025-183"` → introduced in #425 (pixi-era
  `security.yml`), carried through uv migration #2236 (commit a0d96ca6).
- Filter contract: `hephaestus/validation/audit.py` (`load_ignore_list` default path
  `<repo-root>/.pip-audit-ignore.txt`; `#` comments supported; non-zero on malformed input).

## Related

- `tooling-precommit-check-convention-to-invariant` — enforcing that each suppression in a
  ledger carries re-review metadata (complementary: that skill machine-checks the ledger this
  skill creates).
- `lockfile-and-release-pipeline-management` — scoping pip-audit allowlists to
  package/version/advisory/expiry.
- `pr-ci-failure-triage-preexisting-vs-introduced` — stale-cache pip-audit CI failures.
