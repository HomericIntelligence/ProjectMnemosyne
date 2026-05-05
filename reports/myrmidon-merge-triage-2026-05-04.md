# Myrmidon Swarm Merge Triage Report
**Date**: 2026-05-04
**Branch**: feature/myrmidon-merge-triage
**Method**: Two-pass sketch architecture (Wave 1 fingerprint → Wave 2 global cluster → Wave 3 verify)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total skill files (non-notes) | 1024 |
| Files fingerprinted (Wave 1) | 838 (81.8% coverage) |
| Clusters identified (Wave 2) | 59 |
| Files in clusters | 175 |
| Wave 3 verified clusters | 59 |
| **False matches (do NOT merge)** | **3** |
| **Near-exact merge candidates** | **2** |
| **High-overlap (absorb then delete)** | **22** |
| **Topic clusters (reduce count)** | **32** |
| Merge safe immediately | 19 |
| Requires content absorption first | 40 |

**Coverage gap**: Shards 2 and 3 produced ~186 fewer fingerprints than expected. Skills in the alphabetical ranges `consolidate-review-agents` → `fix-review-feedback-missing-assertion` and `fix-review-feedback-runner-path-untested` → `mojo-param-method-collision` may have additional unclustered duplicates not captured here.

**No content will be lost**: All 59 clusters have explicit `unique_content_per_file` inventories from Wave 3 agents. The 3 `distinct` clusters must NOT be merged. All `high-overlap` clusters require absorption of listed unique content before any deletion.

---

## Tier 1: Near-Exact Duplicates (2 clusters, 6 files)

These files share >80% content. Verify unique_content_per_file then delete — minimal absorption needed.

### C014 — pytest asyncio hang patterns (4 files)
**Tier**: near-exact | **Verdict**: Keep all — different root causes
- `testing-pytest-asyncio-daemon-coroutine-patch.md`
- `testing-pytest-asyncio-event-mock-hang.md`
- `testing-pytest-ini-shadows-pyproject.md`
- `testing-pytest-timeout-thread-method-asyncio.md`

**Agent verdict**: All four describe pytest hanging on asyncio tests in the same project, sharing the `epoll.poll(-1)` symptom, but each addresses a distinct root cause and fix. They are complementary diagnostic steps, not duplicates. **Do not merge.**

**Unique content per file**:
- `daemon-coroutine-patch`: patch target selection, AsyncMock instead of patching internal helpers
- `event-mock-hang`: asyncio.Event constructor injection, pre-set event before run()
- `ini-shadows-pyproject`: pytest.ini silently shadows pyproject.toml (config precedence table)
- `timeout-thread-method-asyncio`: pytest-timeout signal vs thread method, SIGALRM cannot interrupt epoll

---

### C015 — GitHub Actions CI patterns (3 files)
**Tier**: near-exact | **Verdict**: Keep all — distinct failure modes
- `ci-github-actions-pull-request-trigger.md`
- `ci-github-actions-secrets-context-unavailable-job-if.md`
- `ci-github-ruleset-matrix-status-context.md`

**Agent verdict**: All three are distinct GitHub Actions CI failure-mode fixes with no shared workflows. **Do not merge.**

**Unique content per file**:
- `pull-request-trigger`: force push triggers pull_request event, path-filter re-evaluation
- `secrets-context-unavailable-job-if`: secrets context unavailable in job-level if:, vars alternative
- `ruleset-matrix-status-context`: matrix jobs emit expanded context names, Python script to rewrite ruleset JSON

---

## Tier 2: High-Overlap Pairs (22 clusters, 48 files)

These files share 40-80% content. Each has **unique content that must be absorbed** into the canonical before deletion. Sorted by absorb-first priority.

### HIGH PRIORITY — Strong merge candidates where absorption is small

#### C041 — JSON logging formatter (2 files)
**Canonical**: `logging-stdlib-json-formatter.md` | **Absorb from**: `tooling-structured-json-logging-stdlib.md`
- **Unique in tooling-structured**: lazy import export pattern, `msg/args` frozenset addition, `basicConfig` format kwarg failed attempt, `formatTime` timestamp variant
- **Estimated absorption**: 1-2 new subsections in canonical's "Implementation Notes"

#### C023 — gitleaks TOML config (2 files)
**Canonical**: `ci-gitleaks-sarif-false-positive-fix.md` | **Absorb from**: `ci-gitleaks-toml-allowlist-slice-vs-map.md`
- **Unique in slice-vs-map**: TOML `[[double bracket]]` vs `[single bracket]` semantic, exact error message, gitleaks v8 format requirement
- **Estimated absorption**: 1 new "TOML Syntax Pitfall" subsection

#### C046 — Mojo alias removal (2 files)
**Canonical**: `mojo-deprecated-alias-removal.md` | **Absorb from**: `mojo-comptime-alias-removal.md`
- **Unique in comptime**: phase 3 docstring/return-statement granular update examples, Conv-module-specific context
- **Estimated absorption**: Phase 3 detail expansion in canonical

#### C047 — Mojo hash testing (2 files)
**Canonical**: `mojo-hash-testing-patterns.md` | **Absorb from**: `mojo-empty-tensor-hash-test.md`
- **Unique in empty-tensor**: 0-element shape discrimination test functions, numel=0 data loop skip explanation
- **Estimated absorption**: 1 new "Empty Tensor Edge Cases" subsection

#### C049 — Mojo NOTE standardization (2 files)
**Canonical**: `mojo-note-to-docstring.md` | **Absorb from**: `mojo-limitation-note-standardization.md`
- **Unique in limitation-note**: specific issue #3071 file list, 3 failed attempts (grep pitfalls, replace_all cross-file)
- **Estimated absorption**: Add to Failed Attempts table

---

### STANDARD HIGH-OVERLAP (absorption required)

#### C004 — Mojo JIT/heap crash debugging (8 files)
**Canonical**: `mojo-jit-crash-retry.md` | **Absorb from**: all others
- `investigate-mojo-heap-corruption.md` → unique: ADR-009 test splitting, heap threshold
- `mojo-always-inline-worsens-jit-crashes.md` → unique: negative @always_inline guidance (CRITICAL anti-pattern)
- `mojo-asap-destruction-perturbation-loop-fix.md` → unique: post-test-output UAF crash diagnostic
- `mojo-bitcast-always-inline-crash-fix.md` → unique: codebase-wide swarm pattern, blog PR workflow
- `mojo-copyinit-double-free.md` → unique: synthesized __copyinit__ shallow copy fix
- `mojo-kgen-jit-buffer-overflow-diagnostic.md` → unique: 4-condition KGEN trigger, upstream issue #6445
- `mojo-library-import-audit.md` → unique: module-level import audit (distinct from test-file audit)
- **Complexity**: 8 files, substantial unique content in each. Recommend consolidating into 2-3 files first.

#### C007 — E2E checkpoint/resume debugging (5 files)
**Canonical**: `e2e-framework-crash-recovery-bugs.md`
- `e2e-resume-restore-run-context.md` → unique: _restore_run_context() loading fix
- `resume-crash-debugging.md` → unique: progressive resume failures debugging methodology
- `resume-functionality-tests.md` → unique: 15 pytest fixture patterns
- `until-resume-debugging.md` → unique: TierState naming confusion, --until stepping command sequence

#### C009 — Mojo AnyTensor circular import (5 files)
**Canonical**: `mojo-circular-import-type-identity-fix.md`
- `mojo-dual-type-tensor-review.md` → unique: architecture design review, quantitative codebase audit data
- `mojo-method-api-symmetry.md` → unique: thin method wrapper pattern
- `mojo-method-wrapper-circular-import.md` → unique: local-scope single-method wrapper technique
- `mojo-overload-ambiguity-typed-tensor-isolation.md` → unique: package isolation for overload ambiguity

#### C010 — Python/Pydantic refactoring (4 files)
**Canonical**: `type-alias-consolidation.md` (already at v3.0.0, absorbed 2 prior skills)
- `codebase-consolidation.md` → unique: general duplicate discovery, true-vs-intentional-variant taxonomy
- `migrate-dataclass-to-pydantic.md` → unique: 24-class migration checklist, pytest fixture migration
- `pydantic-model-dump.md` → unique: v1→v2 .to_dict() → .model_dump() quick-reference fix

#### C019 — Academic paper validation (2 files)
**Canonical**: `academic-paper-validation.md`
- `academic-paper-myrmidon-swarm-review.md` → unique: swarm orchestration configs, false-alarm protocol, architecture research doc pattern

#### C020 — Additive resume tests (2 files)
**Canonical**: `additive-resume-integration-tests.md`
- `tier-state-additive-resume-tests.md` → unique: TierStateMachine-specific helpers, 5 tier_states test scenarios

#### C025 — Claude plugin schema (2 files)
**Canonical**: `claude-plugin-format.md`
- `claude-plugin-marketplace.md` → unique: CLI workflow (claude plugin marketplace add/install), multi-plugin install pattern

#### C030 — Noncontiguous tensor stride (2 files)
**Canonical**: `fix-non-contiguous-tensor-stride-access.md`
- `fix-concatenate-noncontiguous-stride-bug.md` → unique: concatenate-specific offset accumulation, general-axis scope warning, direct _strides mutation test

#### C032 — Markdown fixes + agent docs (2 files)
**Canonical**: `fix-markdown-agent-docs.md`
- `fix-markdown-fenced-code-blocks.md` → unique: clean markdownlint quick-reference rule table, concise 7-step format

#### C038 — Issue preflight checks (2 files)
**Canonical**: `issue-cleanup-already-resolved-detection.md`
- `issue-already-implemented-preflight-check.md` → unique: PR auto-merge status check, commits-ahead detection pattern

#### C050 — Mojo gradient tests (2 files)
**Canonical**: `mojo-numerical-gradient-test.md`
- `mojo-param-gradient-check.md` → unique: perturbing parameters (gamma/beta), tuple result indexing

#### C052 — SIMD vectorization patterns (2 files)
**Canonical**: `optimization-mojo-simd-nan-inf-vectorization.md`
- `optimization-simd-gradient-clipping-vectorization.md` → unique: L2 norm accumulation, in-place scaling/clamping

#### C055 — PR rebase (2 files)
**Canonical**: `pr-rebase-pipeline.md`
- `pr-rebase-stale-plan-fix.md` → unique: stale automated plan verification, comment-only conflict resolution

#### C056 — Pre-commit hook configuration (2 files)
**Canonical**: `pre-commit-hook-configuration.md` (v2.2.0, 566 lines)
- `pre-commit-detect-private-key-fixture-exclusion.md` → unique: credential-vs-fixture distinction, don't-delete-hook warning

#### C057 — Python repo improvement (2 files)
**Canonical**: `python-repo-modernization.md`
- `python-repo-audit-implementation.md` → unique: security fix patterns, subprocess DRY consolidation, error handling migration

#### C058 — State machine (2 files)
**Canonical**: `state-machine-interrupt-handling.md`
- `state-machine-wiring.md` → unique: closure action map construction, namespace dict pattern, sys.argv refactoring

#### C059 — Workflow README (2 files)
**Canonical**: `workflow-readme-audit.md`
- `workflow-readme-migration-sync.md` → unique: 6-location stale-prose checklist, verify-before-edit migration step

---

## Tier 3: Topic Clusters (32 clusters, 121 files)

These are related but distinct skills. Merging is optional — do only to reduce marketplace noise. Agent verdict: **most should be kept separate**. Key exceptions where consolidation is practical:

### Practical topic-cluster consolidations

#### C017 — Docker healthcheck sequence (2 files)
**Merge safe**: yes
- `docker-compose-v5-healthcheck-array-split.md` + `e2e-compose-python-stub-to-cpp-server.md`
- Chronological sequence in same compose file; the stub-migration explains WHY wget was chosen which v5 file then documents a fix for.

#### C048 — Mojo format vs lint (2 files)
**Canonical**: `mojo-lint-syntax.md` (lint file subsumes format file's content + adds substantially more)
- `mojo-format.md` → unique: error-handling table, idempotency note
- These could be merged since lint-syntax is a superset

### Keep separate (false groupings or distinct enough)

| Cluster | Files | Reason |
|---------|-------|--------|
| C001 | 8 | Each covers a distinct CI failure mode with unique fix |
| C002 | 8 | Each covers a distinct Docker/GitHub CI failure class |
| C003 | 8 | Each covers a distinct CI failure diagnosis |
| C005 | 7 | Mixed Mojo migration + tooling — false grouping |
| C006 | 7 | Git/worktree distinct operational angles |
| C008 | 5 | Plugin tooling distinct operations |
| C011 | 4 | Cross-host deployment distinct topologies |
| C012 | 4 | E2E framework distinct bug types |
| C013 | 4 | Repo audit distinct scopes |
| C016 | 3 | CI workflow distinct concerns (consolidate, harden, optimize) |
| C018 | 3 | HomericIntelligence install distinct contexts |
| C021 | 2 | Architecture analysis complementary — keep both |
| C022 | 2 | Different abstraction levels (library vs orchestration) |
| C024 | 2 | Different trigger conditions (slash commands vs version adoption) |
| C026 | 2 | Different problems (add tests vs split file) |
| C027 | 2 | Different evaluation aspects |
| C028 | 2 | Orthogonal concerns (checkpoint vs metrics) |
| C029 | 2 | Orthogonal problems (OOM bug vs 3-stage workflow) |
| C031 | 2 | Unrelated Docker bugs (platform vs TTY) |
| C033 | 2 | Different mypy/ruff focus |
| C035 | 2 | Different test anti-patterns |
| C036 | 2 | Different linters (hadolint vs yamllint) |
| C037 | 2 | Orthogonal hatch-vcs problems |
| C040 | 2 | Orthogonal gradient axes |
| C042 | 2 | Different markdownlint scopes |
| C043 | 2 | Different model config directions |
| C044 | 2 | Companion files (ADR meta + SIMD implementation) |
| C051 | 2 | Different NATS problems |
| C053 | 2 | Different pip-audit strategies |
| C054 | 2 | Different podman startup failures |

---

## Tier 4: False Matches — Do NOT Merge (3 clusters)

| Cluster | Files | Reason |
|---------|-------|--------|
| C034 | fix-randn-seed-bug + mojo-setitem-lvalue-semantics | Completely unrelated: PRNG seeding vs subscript assignment semantics |
| C039 | latex-paper-parallel-assembly + latex-table-underscore-escape-missing-dollar | Completely unrelated: large-scale assembly workflow vs narrow underscore fix |
| C045 | mojo-anytensor-copy-pointer-leak + mojo-anytensor-uint-set-float-bitcast | Completely unrelated: memory leak vs silent write failure — both in same file but distinct bugs |

---

## Recommended Execution Order

### Phase 1: High-confidence, small absorption (< 30 min each)
Start with these — lowest risk, small diffs:
1. **C041**: Absorb `tooling-structured-json-logging-stdlib` → `logging-stdlib-json-formatter`
2. **C023**: Absorb `ci-gitleaks-toml-allowlist-slice-vs-map` → `ci-gitleaks-sarif-false-positive-fix`
3. **C046**: Absorb `mojo-comptime-alias-removal` → `mojo-deprecated-alias-removal`
4. **C047**: Absorb `mojo-empty-tensor-hash-test` → `mojo-hash-testing-patterns`
5. **C049**: Absorb `mojo-limitation-note-standardization` → `mojo-note-to-docstring`
6. **C017**: Merge `e2e-compose-python-stub-to-cpp-server` → `docker-compose-v5-healthcheck-array-split`

### Phase 2: Medium absorption (30-60 min each, 2-3 pair batches via parallel agents)
7. C019, C020, C025, C038, C050, C052, C055, C056, C057, C058, C059
8. C030, C032, C048

### Phase 3: Complex multi-file clusters (parallel agent swarms, 1-2 hours each)
9. C004 (8 files, Mojo crash debugging) — most complex
10. C007 (5 files, E2E checkpoint/resume)
11. C009 (5 files, Mojo AnyTensor circular import)
12. C010 (4 files, Python/Pydantic)

### Phase 4: Optional topic-cluster consolidation
- Only if user wants to further reduce skill count
- Agent verdict recommends keeping most Tier 3 clusters separate

---

## Content-Preservation Attestation

All 59 clusters have explicit `unique_content_per_file` inventories verified by Wave 3 agents reading actual `.md` files. No high-overlap or near-exact cluster is marked `merge_safe` without confirming that unique sections can be absorbed into the canonical file.

The 3 `distinct` clusters (C034, C039, C045) are **false algorithmic matches** — the files must not be merged.

---

## Coverage Gap Notice

Wave 1 fingerprinted 838/1024 skills (81.8%). Skills missed in shards 2 and 3 (alphabetical ranges `consolidate-review-agents` → `fix-review-feedback-missing-assertion` and `fix-review-feedback-runner-path-untested` → `mojo-param-method-collision`) may have additional undetected duplicates. A follow-up targeted scan of those ~186 files is recommended after Phase 1-2 merges.

---

## Baseline Verification

| Check | Status |
|-------|--------|
| Skill files before triage run | 1659 (including .notes.md) / 1024 (skill-only) |
| `python3 -m pytest tests/ -q` | 171 passed ✅ |
| `python3 scripts/validate_plugins.py` | 1024/1024 valid ✅ |
| Files modified this run | **0** (discovery only) |
| Branch | feature/myrmidon-merge-triage |

---

*Generated by 4-wave Myrmidon swarm (1 Wave 1 ×5 Sonnet + 1 Wave 2 Opus + 5 Wave 3 Sonnet + 1 coordinator). Cluster disjoint check: 0 duplicates across 59 clusters.*

---

## Second Pass Addendum (2026-05-04)

### Coverage Gap Recovery

The first pass had 81.8% fingerprint coverage (838/1024 rows). Recomputing against the post-merge corpus showed **205/987 surviving skill files were never fingerprinted** — concentrated in c/d/e/f/g/m letter ranges. This second pass adds fingerprints for all 205 files and re-clusters globally.

**Wave 1b**: 2 shards × ~103 files each (general-purpose agents with Write tool, not Explore) → 205 new fingerprint rows, all valid JSON.  
**Wave 2b**: Combined 987-row global cluster → 21 new clusters (C060–C080), 75 files, all disjoint.  
**Wave 3b**: 5 parallel verification agents → verdicts below.

---

### Tier 2: High-Overlap Merges (5 clusters, 8 files)

#### C066 — GRPO external vs self-hosted inference (2 files)
**Canonical**: `baseten-miles-grpo-external-inference.md`
- `dynamo-miles-grpo-self-hosted-inference.md` → unique: Dynamo architecture (frontend + SGLang workers), Slurm two-job pattern, disaggregated serving config (prefill/decode split), weight update endpoint, v1.0.0 logprobs bug, Dynamo vs Baseten comparison table

#### C068 — Mojo trait conformance (2 files)
**Canonical**: `mojo-trait-conformance-for-sequential-integration.md`
- `mojo-trait-conformance-fix.md` → unique: minimal 1-line fix pattern, GLIBC `SKIP=mojo-format` workaround, exact CI error message format, root cause note (`__hash__` alone insufficient)

#### C072 — Deprecated alias removal + notes file (2 files)
**Canonical**: `mojo-deprecated-alias-removal.md` (v1.2.0)
- `mojo-deprecated-alias-removal.notes-conv.md` → unique: **none** — all content already absorbed in v1.2.0. Safe to delete directly.

#### C075 — Pixi lock drift / Dependabot (2-of-4 files)
**Canonical**: `pixi-lock-rebase-regenerate.md`
- `ci-cd-dependabot-pixi-lock-drift-fix.md` → unique: multi-PR sequential fixing pattern, local/origin divergence from prior force-push, `git commit --amend --no-edit` for untracked pixi.lock post-conflict
- `cross-repo-dep-pypi-publish-fix.md` — **keep separate** (OIDC publish, path dep replacement, ShellCheck — distinct topic)
- `cross-repo-python-utility-port.md` — **keep separate** (circuit breaker porting, re-export shims — mis-clustered)

#### C077 — FP16 precision docs (2 files)
**Canonical**: `fp16-accumulation-threshold-math-docs.md`
- `fp16-precision-test-documentation.md` → unique: test file docstring targeting (vs dev guide), mixed-precision training context, Documentation section template with `=` underline heading style, per-file assessment step (expected-limitation vs bug-candidate), docs(tests): commit format

---

### Tier 3: Topic Clusters (16 clusters, 67 files — keep separate)

| Cluster | Files | Reason |
|---------|-------|--------|
| C060 | 9 cpp-* | All distinct C++ failure modes (ADL, TSan, clang-tidy, httplib UB, JSON, stale commits, cmake, natsc) |
| C061 | 5 github issue | Distinct scenarios (single upstream, bulk rate-limit, comment dedup, branch rename, OSS audit) |
| C062 | 4 github rulesets | Distinct (CI patterns consolidated v2.2.0, org ruleset API, PR-blocked diagnosis, SSH signing) |
| C063 | 8 docker/dockerfile | Distinct (cascade map, cascading fixes, multiarch build, uid mismatch, precommit, to-podman, cargo regression, cargo→binary) |
| C064 | 4 myrmidon/e2e | Distinct (OOM fixes, mesh dispatch debugging, volume mapping, swarm orchestration) |
| C065 | 6 documentation/audit | Distinct (6-dim rubric, citation discovery, parallel remediation, LaTeX audit, data pipeline, 10-dim corpus audit) |
| C067 | 5 mojo migration | Distinct (0.26.3 breaking changes, Python interop guide, Python→stdlib migration, version strategy, Writable migration) |
| C069 | 3 mojo destructor | Distinct (bad-free/ASAN, Tuple.__del__ clone pattern, Tuple return syntax) |
| C070 | 2 | FALSE MATCH: alias cleanup (ci-cd) vs type safety (optimization) — zero content overlap |
| C071 | 2 | FALSE MATCH: runtime crash bisection vs runtime output pattern audit — completely different domains |
| C073 | 4 conv2d gradient | Distinct (analytical values, finite-diff patterns, depthwise-specific, API migration history) |
| C074 | 3 git worktree | Distinct (preservation audit, management patterns v2.6.0, rebase decision methodology) |
| C076 | 2 dockerfile | Distinct (FROM inline comment parse error vs version pinning regression tests) |
| C078 | 2 documentation | Distinct (role drift detection vs multi-file listing sync) |
| C079 | 2 documentation | Parent-child: audit skill references security-md as a sub-procedure — keep separate |
| C080 | 2 | FALSE MATCH: internal randn seed fix vs upstream bug filing standard — zero content overlap |

---

### Second Pass Summary

| Tier | Clusters | Files to absorb | Action |
|------|----------|----------------|--------|
| Tier 2 high-overlap | 5 | 5 files | Merge (C066, C068, C072-delete, C075-partial, C077) |
| Tier 3 topic-cluster | 13 | — | Keep separate |
| False matches | 3 (C070, C071, C080) | — | Do not merge |
| **Total** | **21** | **5** | — |

Second pass merges reduce corpus by **5 additional files** (987 → 982).

