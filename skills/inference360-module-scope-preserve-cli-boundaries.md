---
name: inference360-module-scope-preserve-cli-boundaries
description: "Keep Inference360 module-scope refactors behavior-preserving. Use when: (1) implementing docs/issue-346-module-scope-plan.md, (2) moving helpers out of the package root while preserving `inference360 = \"inference360:main\"`, (3) enforcing CLI/domain/foundation import boundaries, (4) reviewing wizard/tools coverage during a module-boundary cleanup."
category: architecture
date: 2026-07-05
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - inference360
  - module-scope
  - cli
  - warden
  - slurm
  - manifest
  - wizard
  - tools
  - h200
  - boundaries
---

# Inference360 Module Scope: Preserve CLI Boundaries

## Overview

| Field | Value |
| --- | --- |
| **Date** | 2026-07-05 |
| **Objective** | Implement and review the Inference360 issue #346 module-scope plan so the project becomes properly module-scoped without changing operator-facing behavior. |
| **Outcome** | Successful locally. The package root stayed a small facade, domain ownership moved to focused modules, wizard/tools surfaces were included, and operator CLI behavior stayed stable. Related PRs #348 and #353-#359 were observed merged with green checks; this skill PR still needs its own Mnemosyne CI. |
| **Verification** | verified-local. Local host/container validation passed in the Inference360 checkout; related Inference360 PR CI was observed green, but do not overclaim CI for future changes until the current PR's checks pass. |

Inference360 is a manifest-driven internal H200 Slurm inference platform. Slurm
remains the scheduler of record; Warden owns lifecycle; generated artifacts
must stay reproducible from manifests, Registry state, templates, and referenced
checkpoint facts. Do not introduce Kubernetes as a v1 requirement while applying
this pattern.

## When to Use

- You are implementing or reviewing `docs/issue-346-module-scope-plan.md`.
- A refactor touches `inference360/__init__.py`, `inference360/cli.py`, Warden, checks, manifests, gateway, registry, Slurm helpers, wizard, or tools.
- The package root is starting to accumulate business helpers or private legacy aliases.
- A domain or foundation module imports `inference360.cli` or imports through root aliases with `from inference360 import ...`.
- Wizard or tools commands are treated as outside the refactor even though `uv run inference360 wizard ...` and `uv run inference360 tools ...` are operator-facing surfaces.
- Review needs mechanical proof that module ownership changed without changing the console-script path or command set.

## Verified Workflow

### Quick Reference

```bash
cd <Inference360 checkout>

uv run inference360 --help
uv run pytest tests/test_module_boundaries.py -q
uv run ruff check inference360 scripts tests
uv run ruff format --check inference360 scripts tests
uv run mypy inference360
just _validate-host
just validate
```

### Detailed Steps

1. Re-read the repo contract before changing architecture: `README.md`,
   `AGENTS.md`, and `docs/inference360-design.md`. For issue #346 work, also
   read `docs/issue-346-module-scope-plan.md`.

2. Preserve the public entrypoint exactly:

   ```toml
   [project.scripts]
   inference360 = "inference360:main"
   ```

   Keep `inference360/__init__.py` as a small facade exposing `main` from
   `inference360.cli` plus intentional public or transition aliases. Do not move
   business helper implementations into the package root.

3. Keep the stable ownership map explicit:

   | Module | Ownership |
   | --- | --- |
   | `cli.py` | Parser construction and thin command dispatch |
   | `manifests.py` | Service manifest loading, defaults selection, software-version facts, schema/contract helpers |
   | `registry.py` | Registry state and promotion evidence records |
   | `slurm.py` | Slurm command construction/parsing and allocation action helpers |
   | `gateway.py` | HAProxy/gateway rendering and promotion readiness helpers |
   | `warden.py` | Lifecycle orchestration, artifact rendering, process/server routes, HAProxy publication/reload, long-lived Slurm job lifecycle |
   | `checks.py` | `inference360 check ...` and local status/check orchestration; must not mutate lifecycle state |
   | `paths.py`, `utils.py`, `templating.py`, `errors.py` | Foundation modules; import canonical modules directly, never through package-root aliases |

4. Enforce dependency direction:

   - Domain modules must not import `inference360.cli`.
   - Foundation and domain modules should import canonical modules directly, not
     `from inference360 import ...` root aliases.
   - CLI may import domain modules; domain modules should not depend on CLI.
   - Warden route dispatch should call focused lifecycle helpers rather than
     growing inline route-specific sprawl.
   - Script-backed commands may remain thin CLI dispatch surfaces when scripts
     own the implementation.

5. Include wizard/tools in scope. Keep `uv run inference360 wizard ...` and
   `uv run inference360 tools ...` behavior stable. Wizard/tools should import
   canonical foundation and manifest modules. Avoid a wizard -> CLI dependency
   cycle; an injected runner or the public `inference360.main` compatibility path
   is acceptable where the launch flow needs it. Track wizard/tools gaps as
   explicit follow-up issues when the main issue range might miss them.

6. Keep `tests/test_module_boundaries.py` as the mechanical ownership guard. It
   should assert that:

   - parser construction remains out of the package root;
   - domain modules do not import CLI;
   - the root has no helper implementations or private legacy aliases;
   - CLI dispatches through public helpers;
   - Warden route dispatch is focused;
   - scripts avoid private Warden helpers;
   - wizard/tools imports are canonical.

7. Pair tests with import audits and direct source inspection:

   ```bash
   rg -n "from inference360 import|import inference360.cli|from inference360.cli|_warden_|wizard|tools" inference360 scripts tests
   ```

   The boundary tests prove the guard exists; `rg` plus file inspection proves
   the actual ownership shape is real and not only documented.

8. Verify operator-facing behavior before declaring success. `uv run
   inference360 --help` must still expose the expected commands, including
   `login`, `warden`, `allocate`, `registry`, `start`, `stop`, `deallocate`,
   `check`, `status`, `wizard`, `validate-inferencex-pin`,
   `inferencex-benchmark`, `server`, `launch-server`, and `tools`.

9. Run targeted and repository gates. Use `just validate` when Enroot and the
   SquashFS validation image are available. For focused host checks, run the
   closest targeted `uv run pytest` and any affected `uv run inference360 check
   ...` commands.

10. Treat `inference360 check all` fail-closed readiness signals as distinct
    from command failure. It may report pre-health or promotion readiness false
    while command status remains ok; that is expected until every promotion gate
    passes.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --- | --- | --- | --- |
| Partial validation after context compaction | Relied on remembered or partial output from a prior validation run | The current checkout did not have a complete fresh exit code in hand | Re-run validation in the current checkout before claiming success |
| Non-escalated dependency resolution | Ran `uv run ...` under sandboxed DNS while packages needed PyPI resolution | DNS resolution failed before the test command could exercise project behavior | If the command is required, rerun with approved network access and a local UV cache; do not classify DNS failure as a test failure |
| Assuming stacked branch refs remain stable | Checked local intermediate commit IDs after stacked PRs merged | GitHub head refs can differ and remote branches may be auto-deleted after merge | Verify merge state and checks, not only branch refs or local intermediate SHAs |
| Treating wizard/tools as out of scope | Focused only on root, CLI, and domain modules | Wizard/tools are operator-facing CLI surfaces and can introduce import cycles or stale root aliases | Include wizard/tools in boundary tests and file follow-up issues when they need separate cleanup |
| Importing through root aliases for convenience | Used `from inference360 import ...` in foundation or domain modules | Root aliases make dependency direction opaque and can reintroduce facade sprawl | Import canonical modules directly from their owning modules |
| Reading fail-closed readiness as validation failure | Treated false pre-health/promotion readiness in `inference360 check all` as a failed command | Readiness gates are supposed to fail closed until all required evidence exists | Distinguish command status from promotion readiness booleans |

## Results & Parameters

Observed local validation from the issue #346 module-scope session:

| Check | Result |
| --- | --- |
| `uv run inference360 --help` | Passed; showed operator commands including `login`, `warden`, `allocate`, `registry`, `start`, `stop`, `deallocate`, `check`, `status`, `wizard`, `validate-inferencex-pin`, `inferencex-benchmark`, `server`, `launch-server`, and `tools` |
| `uv run pytest tests/test_module_boundaries.py -q` | 22 passed |
| `uv run ruff check inference360 scripts tests` | All checks passed |
| `uv run ruff format --check inference360 scripts tests` | 69 files already formatted |
| `uv run mypy inference360` | Success, 21 source files |
| `just _validate-host` | Exited 0; 1226 passed, 1 skipped, total coverage 84.30% |
| `just validate` | Exited 0; 1218 passed, 9 skipped, total coverage 84.28% |

Related GitHub state checked during the session:

| Item | Purpose |
| --- | --- |
| Issue #346 | Tracked the module-scope plan |
| Issues #351 and #352 | Tracked wizard/tools follow-ups |
| PRs #348 and #353-#359 | Merged module-scope implementation/review/follow-up PRs with green checks observed |

Redaction rule: do not put endpoint addresses, absolute infrastructure paths,
checkpoint paths, private prompts, tokens, cookies, or user-specific locations
in skills, PR bodies, docs, tests, examples, release notes, or issue comments.
Use placeholders such as `<REDACTED_ENDPOINT>`, `<REDACTED_CHECKPOINT_PATH>`, or
`<REDACTED_INFRA_PATH>` only when shape matters.

## Verified On

| Project | Context | Details |
| --- | --- | --- |
| LLM360/Inference360 | Issue #346 module-scope implementation/review/validation session on 2026-07-05 | Local host/container validation passed; related Inference360 PR checks were observed green before capture. |
