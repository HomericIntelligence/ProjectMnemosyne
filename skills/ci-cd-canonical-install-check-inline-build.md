---
name: ci-cd-canonical-install-check-inline-build
description: "Plan/implement a canonical `install` CI check-run (clean-venv install smoke of the built artifact, per the Odysseus ci-naming convention) when the upstream `package` job does NOT exist yet and the repo may not even be buildable. Use when: (1) an ecosystem CI-naming issue asks for `name: install` but the sibling `package` gap issue has not merged (no [build-system] in pyproject.toml, setuptools flat-layout auto-discovery failure), (2) you must decide between `needs: package` + download-artifact handoff vs building the wheel inline inside the install job, (3) designing an import-smoke that must not depend on the not-yet-decided package layout — derive modules from the installed wheel's top_level.txt and fail loudly if empty, (4) tempted to add a 'skip if not buildable' branch to a canonical check (don't — a skipping canonical check emits green without testing), (5) the repo keeps mirrored workflow files (a PR/push gate like _required.yml plus a workflow_call mirror like _checks.yml) and every canonical job must be added to both, (6) writing the plan's step 1 as an explicit buildability gate (`python -m build`) that STOPS implementation if the prerequisite is still missing."
category: ci-cd
date: 2026-07-02
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - canonical-checks
  - ci-naming-convention
  - install-check
  - package-check
  - install-smoke
  - clean-venv
  - import-smoke
  - top-level-txt
  - wheel
  - sdist
  - python-build
  - blocked-prerequisite
  - workflow-mirror
  - fail-loud
  - signal-fidelity
  - planning-methodology
---

# CI: Canonical `install` Check via Inline Build When `package` Doesn't Exist Yet

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-02 |
| **Objective** | Plan the canonical `install` check-run (Mnemosyne issue #2912, Odysseus ecosystem CI-naming unification) for a repo whose `package` prerequisite is unmerged and whose `pyproject.toml` has no `[build-system]` — i.e. the artifact the check must install-smoke cannot be built yet. |
| **Outcome** | Plan produced (R0). Key design: self-contained `install` job that builds the wheel inline, clean-venv installs it, and import-smokes modules derived from the wheel's own `top_level.txt`. NOT executed — plan only. |
| **Verification** | unverified |

## When to Use

- An ecosystem CI-naming issue asks for a canonical `install` check but the sibling `package` issue (buildability) has not merged.
- Deciding between `needs: package` + `actions/download-artifact` handoff and an inline `python -m build` inside the install job.
- Designing an install/import smoke that must survive an unknown future package layout.
- The repo mirrors its job set across a PR/push workflow (`_required.yml`) and a `workflow_call` twin (`_checks.yml`).
- Writing a plan for an issue that is explicitly "blocked on" another issue — the plan must encode the block as an executable gate, not prose.

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end. It is an implementation PLAN (R0, pre-review, nothing executed — no YAML committed, no CI run). Treat as a hypothesis until CI confirms.

### Quick Reference

```yaml
# Canonical install job — self-contained (no needs: package while that job doesn't exist)
install:
  name: install
  runs-on: ubuntu-24.04
  timeout-minutes: 10
  steps:
    - uses: actions/checkout@<same-SHA-pin-as-sibling-jobs>
    - uses: actions/setup-python@<same-SHA-pin-as-sibling-jobs>
      with:
        python-version: '3.11'
    - name: Build distributable (wheel + sdist)
      run: |
        pip install build
        python -m build --outdir dist/
    - name: Clean-venv install smoke
      run: |
        python -m venv /tmp/install-venv
        /tmp/install-venv/bin/pip install --no-cache-dir dist/*.whl
        /tmp/install-venv/bin/pip check
    - name: Import smoke
      run: |
        /tmp/install-venv/bin/python - <<'EOF'
        import importlib
        import importlib.metadata as md
        dist = md.distribution("<dist-name>")
        tops = (dist.read_text("top_level.txt") or "").split()
        if not tops:
            raise SystemExit("ERROR: wheel records no top-level modules; nothing to import-smoke")
        for name in tops:
            importlib.import_module(name)
        EOF
```

```bash
# Plan step 1 — buildability gate: if this fails, the issue is STILL blocked; stop.
python -m build --outdir /tmp/dist-check
```

### Detailed Steps

1. **Grep for the predecessor jobs before designing.** `grep -rn 'name: install\|name: package' .github/workflows/` — confirm neither exists. A `needs: package` design is un-implementable when `package` is absent from the tree, and the future `package` job's artifact-upload contract (artifact name, wheel vs bundle) is unknown. Decide: build inline, keep the build step isolated and named so a later switch to `needs: package` + `download-artifact` is a small, separable follow-up.

2. **Encode the "blocked on" as an executable gate, step 1 of the implementation order.** Run `python -m build` at repo root; if it fails (no `[build-system]`, flat-layout auto-discovery error), STOP and report the blocking state. Do not paper over it in the job.

3. **No skip branch in a canonical check.** A "skip if not buildable" branch makes the check emit green without testing anything — the canonical name's whole value is signal fidelity. If the tree regresses to unbuildable, `install` goes red; that is the point. Also keeps parity with a forbid-suppressions gate (no `|| true`, no `continue-on-error: true`).

4. **Derive the import-smoke population from the installed wheel itself** (`top_level.txt` via `importlib.metadata.distribution(...).read_text`), and fail loudly when the list is empty. This decouples the smoke from the package-layout decision the sibling issue will make, and prevents a vacuous pass when the wheel ships no importable code.

5. **Mirror the job into every workflow twin.** If the repo keeps a PR/push gate plus a `workflow_call` mirror with parallel job sets, add the identical job to both — even if the mirror has no in-repo caller (it may be invoked cross-repo).

6. **Match sibling-job idiom exactly:** same SHA-pinned action versions, same runner label, `timeout-minutes` set, yamllint line-length respected. Verify with the repo's own gates: `yamllint`, `check-jsonschema --builtin-schema vendor.github-workflows`, and a suppressions grep.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `needs: package` + `actions/download-artifact` handoff | Canonical convention reads "install verifies the artifact produced by package", so first instinct was a job dependency | The `package` job does not exist in the tree yet, and its artifact contract (name, contents) is undecided in the unmerged sibling issue — the YAML would not even be valid | When the upstream job is unmerged, build inline in an isolated named step; switch to the artifact handoff as a follow-up once `package` lands |
| Metadata-only smoke (`pip show` / version check) | Simplest post-install assertion | Verifies dist-info exists but never imports code — a wheel that ships zero importable modules would pass | Import-smoke must actually `importlib.import_module` something; derive the module list from the wheel's `top_level.txt` and error when empty |
| "Skip if not buildable" guard branch in the job | Would let the check land before the `package` PR merges | A canonical check that skips emits green without testing — defeats the signal-fidelity purpose of the canonical name | Sequence the PR after the prerequisite instead of weakening the check; encode the block as a stop-the-work gate in the plan |
| Hardcoding the import target (e.g. `import scripts`) | Direct and readable | The sibling `package` issue has not decided the package layout/top-level module names yet — any hardcoded name is a guess that breaks when the layout lands | Read `top_level.txt` from the installed distribution at runtime instead of guessing the layout |

## Results & Parameters

- **Job shape:** see Quick Reference. Substitute the repo's exact SHA-pinned `actions/checkout` / `actions/setup-python` (copy from a sibling job) and the real distribution name from `pyproject.toml [project].name`.
- **Insertion points (Mnemosyne, at plan time — line numbers WILL drift):** after the `build` job in `.github/workflows/_required.yml` (~line 305) and `.github/workflows/_checks.yml` (~line 243).
- **Local simulation of the job body:**

```bash
rm -rf dist/ && pip install build && python -m build --outdir dist/
python -m venv /tmp/install-venv
/tmp/install-venv/bin/pip install --no-cache-dir dist/*.whl
/tmp/install-venv/bin/pip check
```

### Known uncertain assumptions (carry into review)

- **`top_level.txt` is a setuptools convention.** Hatchling and flit do NOT write it. If the sibling `package` issue picks a non-setuptools backend, the import smoke fails loudly on a perfectly good wheel (false red). Mitigation if that happens: fall back to parsing `RECORD` for top-level packages, or pin the module list once the layout is decided.
- **The Odysseus `ci-naming-convention.md` was never fetched** — the plan relied on the issue body's paraphrase of the convention (canonical name `install`, clean-venv smoke semantics, artifact-of-`package` relationship).
- **The `workflow_call` mirror (`_checks.yml`) has no in-repo caller** (grep found none) — mirroring into it assumes cross-repo callers exist; if it is dead, the mirror edit is harmless but unverifiable.
- **Cited line numbers** (`_required.yml:305`, `_checks.yml:243`) are read-once and will drift; re-grep at implementation time.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Mnemosyne | Issue #2912 planning session (plan only, not executed) | Canonical `install` check plan for the Odysseus CI-naming unification |
