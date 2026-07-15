---
name: code-quality-audit-principles
description: "Use when reviewing, planning, or implementing repository changes that must apply KISS, YAGNI, TDD, DRY, SOLID, modularity, and POLA without creating brittle prose tests or maintenance-only artifacts."
category: tooling
date: 2026-07-15
version: "2.0.0"
user-invocable: false
verification: verified-ci
tags:
  - code-quality
  - repository-review
  - pull-request-review
  - kiss
  - yagni
  - tdd
  - dry
  - solid
  - modularity
  - pola
  - behavior-testing
  - durable-artifacts
---

# Code Quality Decisions Through Development Principles

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-15 |
| **Objective** | Apply seven development principles to both product changes and the review process, while adding only behavior-changing or directly useful repository artifacts. |
| **Outcome** | Replaced a report-generating audit recipe with an evidence-first decision method. Athena PR #9 implemented the policy, passed 110 tests with 92% branch coverage, passed every required CI check, and merged. |
| **Verification** | verified-ci |

## When to Use

Use this guidance when:

- reviewing a repository or pull request for unnecessary complexity, duplication, coupling, weak
  tests, surprising interfaces, or unclear module boundaries;
- deciding whether a finding warrants code, a computable regression test, documentation, a tracking
  issue, or no new artifact;
- planning a fix whose proposed scaffolding, compatibility layer, registry, report, or generator may
  cost more to maintain than the product change;
- evaluating a test that asserts prose, headings, counts, snapshots, timing, network state, or an
  implementation detail instead of the behavior that failed.

Use the repository's `repo-review` or `pr-review` workflow for audit coverage, evidence collection,
grading, and verdicts. This lesson supplies decision rules; it does not duplicate those review
rubrics.

## Verified Workflow

### Quick Reference

1. Identify the current requirement, affected consumer, and executable failure.
2. Apply KISS, YAGNI, TDD, DRY, SOLID, modularity, and POLA to the proposed remedy.
3. Add an artifact only when it directly implements, verifies, distributes, operates, secures, or
   explains the current product.
4. For executable defects, prove a focused RED test, make the smallest GREEN change, then refactor.
5. Run the repository's focused checks, complete required gate, and current-head CI.
6. Report evidence in the review or PR. Create another persistent artifact only when a demonstrated
   consumer or explicit repository policy requires it.

### 1. Establish evidence before scoring

Read repository policy, linked requirements, affected code, public contracts, tests, packaging, and
CI configuration. Treat file size, coverage, nesting, and duplication metrics as investigation
signals, not universal pass/fail thresholds. A finding needs a concrete consumer impact, violated
contract, demonstrated risk, or failed executable check.

Do not hide an executable failure behind a grade average. Conversely, do not manufacture work from
an arbitrary metric when the code remains simple, tested, and unsurprising in its actual context.

### 2. Apply the seven principles to the remedy

| Principle | Decision rule |
| --------- | ------------- |
| KISS | Prefer the smallest design that satisfies the demonstrated requirement. Reject scaffolding whose only justification is possible future work. |
| YAGNI | Do not add compatibility layers, generators, registries, reports, extension points, or configuration without a current consumer. |
| TDD | For executable behavior, first reproduce the defect with a focused failing test, make it pass minimally, then refactor under the test. |
| DRY | Keep one authority for each rule or data set. Remove duplicated logic and manually synchronized representations when a single source works. |
| SOLID | Keep responsibilities cohesive, extend through stable seams when extension is required, preserve substitutability, expose focused interfaces, and inject unstable dependencies at boundaries. |
| Modularity | Give independent modules explicit inputs, outputs, ownership, and tests; avoid ambient state and hidden working-directory contracts. |
| POLA | Make defaults, names, failures, side effects, and authority boundaries match a reasonable user's expectations. Fail closed when safety or identity is ambiguous. |

These principles constrain the review process too. A quality audit should not create the complexity,
duplication, speculative machinery, or surprising side effects it criticizes.

### 3. Use the durable-artifact gate

Before adding a file, require a clear answer to both questions:

1. Which current product or contributor workflow consumes this artifact?
2. Who or what keeps it correct when the underlying behavior changes?

Add the artifact only when it directly implements, verifies, distributes, operates, secures, or
explains the current product. Prefer an existing repository surface over a parallel representation.

Do not create these by default:

- generated or periodic audit reports;
- manually maintained changelogs when release policy does not require one;
- duplicated or dynamic registries, catalogs, indexes, inventories, or count summaries;
- generated documentation without an existing supported generation pipeline and consumer;
- inline known-issue comments that merely repeat a tracking issue;
- unrelated cleanup files bundled with the requested change.

A repository may legitimately require one of these artifacts. In that case, cite the existing
consumer and update mechanism rather than inferring a generic best practice.

### 4. Test behavior and executable contracts

For a code or automation defect, the regression test must fail for the reported defect before the
fix and pass after it. Assert computable outcomes such as return values, state transitions, parsed
data, exit status, security boundaries, archive membership, schema validity, or filesystem effects.

Do not add tests that freeze:

- documentation sentences, headings, paragraphs, word counts, or snapshots;
- README or policy wording used only as prose;
- manually repeated counts or catalog contents;
- private implementation details that are not part of an executable contract;
- real time, external network availability, nondeterministic ordering, or host-specific state when
  a deterministic boundary can be injected.

Use existing Markdown lint and link checks for documentation syntax. A documentation-only change
does not justify a new test harness. Structured documentation may be tested only when a real tool
consumes it as executable data; test the parser or schema contract, not editorial wording.

### 5. Verify proportionally and report in place

Run the focused regression first, then the repository's formatter, linter, type checks, complete
test suite, packaging or distribution checks, and required CI as applicable. Record exact commands,
results, revision, and any authorized deferral in the PR or review response.

Create a GitHub issue only for genuinely deferred work that needs ownership and only when the user or
repository workflow authorizes that external write. Do not create an issue for every observation.
Do not create a separate audit document merely to restate the review.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Mandatory audit artifacts | Required every audit to generate a dated report, inline known-issue comments, many issues, and recurring rating updates | The artifacts had no guaranteed consumer, duplicated live evidence, created maintenance work, and violated KISS and YAGNI | Keep findings in the review or PR unless an existing workflow explicitly requires another durable artifact |
| Prose-string regression tests | Tested documentation wording, headings, counts, and snapshots to prevent drift | Editorial changes broke tests without changing executable behavior, while the tests still could not prove the product contract | Test computable behavior or a real parser/schema contract; lint prose with existing documentation checks |
| Universal numeric thresholds | Treated file length, function length, nesting, and coverage percentages as correctness grades | Context-free thresholds produced false positives and encouraged metric gaming | Use metrics to locate risk, then require repository-specific impact and evidence |
| Speculative infrastructure | Added generators, registries, compatibility layers, and abstraction seams for hypothetical consumers | The extra machinery increased coupling and update burden before any requirement existed | Add the simplest current solution and extend only when a real consumer appears |
| Issue per observation | Filed external work items for every review note | This created noise, fragmented ownership, and expanded scope without authority | Fix in scope, report non-actionable context, and track only explicitly authorized deferrals |

## Results & Parameters

### Artifact decision matrix

| Proposed change | Default decision | Evidence that can justify it |
| --------------- | ---------------- | ---------------------------- |
| Focused behavior test | Add for an executable defect | Demonstrated RED before the fix and GREEN after it |
| Documentation edit | Edit the existing canonical page | Current user or contributor need; existing lint/link checks pass |
| New documentation test | Reject | Only justified when a real parser consumes structured data; test its schema, not prose |
| Audit report file | Reject | Existing repository policy names a consumer, owner, location, and update lifecycle |
| Changelog entry | Reject unless required | Release tooling or documented release policy consumes it |
| Registry, catalog, or generated index | Reject unless required | A current runtime or contributor workflow consumes one authority with an automated update path |
| Tracking issue | Ask or follow explicit policy | Deferred actionable work needs ownership and external-write authority |

### Evidence recorded from the verified implementation

| Evidence | Result |
| -------- | ------ |
| Focused and full tests | 110 of 110 passed |
| Aggregate branch coverage | 92% |
| Per-executable coverage floor | Every executable script at or above 80% |
| Static and distribution gates | Ruff, formatting, strict mypy, plugin validation, packaging, workflow schema, and Markdown lint passed |
| Required CI | All jobs and the aggregate required-check gate passed on Athena PR #9 head `69e806f` |
| Delivery | Athena PR #9 merged as `9a03d9f` |

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| Athena | PR #9, merged 2026-07-15 | Review skills and development policy adopted the seven principles, prohibited brittle prose tests and maintenance-only artifacts, and passed the complete local and required CI gates. |

## References

- [Athena PR #9](https://github.com/HomericIntelligence/Athena/pull/9)
- [Athena development policy](https://github.com/HomericIntelligence/Athena/blob/main/docs/policies/development.md)
