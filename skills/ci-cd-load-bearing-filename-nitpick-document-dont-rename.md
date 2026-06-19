---
name: ci-cd-load-bearing-filename-nitpick-document-dont-rename
description: "Use when: (1) an audit/lint/review NITPICK proposes renaming a file or symbol 'for discoverability/clarity' — first check whether the name is a load-bearing CROSS-REPO convention before planning the rename, (2) the candidate name is wired into branch-protection rulesets, CI status-check contexts, runbooks, canonical-checks docs, or sibling/fleet repos — the right fix is to make the name self-documenting (header comment + rationale at the source-of-truth doc), NOT to rename, (3) you must SCOPE the blast radius of a rename and need to distinguish a FILENAME change (cosmetic: breaks docs/runbook references + fleet uniformity) from a JOB-NAME change (load-bearing: breaks ruleset status-check contexts, which key off the BARE JOB NAME, not the workflow filename), (4) you are about to claim N files are 'identical across the fleet' from a single-line grep match — matching a workflow NAME or a header line is NOT byte-identity; the convention is the job-name CONTRACT, not literal file equality. Headline: a discoverability rename against a cross-repo convention has disproportionate blast radius and can deadlock ruleset rollout — DOCUMENT the rationale instead of renaming."
category: ci-cd
date: 2026-06-19
version: "1.1.0"
user-invocable: false
verification: unverified
history: ci-cd-load-bearing-filename-nitpick-document-dont-rename.history
tags:
  - ci-cd
  - planning-quality
  - audit-nitpick
  - discoverability-rename
  - load-bearing-convention
  - cross-repo-convention
  - branch-protection
  - required-status-checks
  - ruleset-context
  - bare-job-name
  - blast-radius-scoping
  - filename-vs-job-name
  - document-dont-rename
  - self-documenting-name
  - fleet-uniformity
  - grep-identity-fallacy
  - ruleset-context-format-split
  - org-vs-repo-ruleset
  - active-ruleset-is-enforced
  - false-mechanism-as-docs
  - pixi-task-verification
  - forbid-suppressions-guard
---

# CI/CD: Load-Bearing Filename NITPICK — Document, Don't Rename

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-19 |
| **Objective** | Resolve a "rename `.github/workflows/_required.yml` for discoverability" NITPICK (issue #215, sole open child of Epic #174) in the Odysseus meta-repo, where `_required.yml` is a deliberate org-wide convention shared across ~15 repos |
| **Outcome** | Plan WRITTEN but NOT executed/merged. Recommendation: DOCUMENT the rationale (in-file header comment + source-of-truth canonical-checks doc) rather than rename. v1.0.0's plan received a NOGO because it committed a FALSE mechanism as docs; v1.1.0 folds in grep/read-VERIFIED corrections (the org-vs-repo ruleset context-format split, the real pixi task list, the forbid-suppressions guard) that promote the prior "uncertain assumptions" to verified facts + lessons. |
| **Verification** | `unverified` — planning learning; the corrected plan was written and re-reviewed but the actual edits were never executed/merged. The ground-truth FACTS below ARE grep/read-verified against the Odysseus repo; the recommended workflow is not. |
| **History** | [changelog](./ci-cd-load-bearing-filename-nitpick-document-dont-rename.history) — amended 1.0.0 → 1.1.0 |

## When to Use

- An **audit/lint/review NITPICK** says "rename file X / symbol Y **for discoverability** (or clarity)" and X/Y looks arbitrary — STOP and check whether the name is a load-bearing convention before you plan the rename.
- The candidate name appears in **branch-protection rulesets, CI status-check contexts, runbooks, canonical-checks docs, or sibling/fleet repos**. If so, prefer making the name self-documenting (header comment + rationale doc) over renaming.
- You need to **scope the blast radius** of a rename and must separate FILENAME impact (cosmetic) from JOB-NAME impact (load-bearing) — they are NOT the same in GitHub Actions branch protection.
- You are about to assert "these N files are identical across the fleet" from a **single grep line match** (workflow `name:`, a header line) — that is a NAME/CONTRACT match, not byte identity.
- You see a "low-effort cleanup" framed nitpick that, if executed, would touch many repos and could **deadlock a ruleset rollout**.

## Verified Workflow

> **Warning (Proposed Workflow):** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms. Verification level: `unverified` — this is a planning learning. The corrected plan was written and re-reviewed but the actual edits were never executed/merged. NOTE: the ground-truth FACTS cited below (the org-vs-repo ruleset context-format split, the job-`name:` carriers, the pixi task list, the markdownlint scope) ARE grep/read-verified against the Odysseus repo — only the recommended end-to-end workflow is unverified. v1.0.0's plan was NOGO'd for committing a FALSE mechanism ("renaming the file breaks enforcement") as documentation; see Failed Attempts #6 (the headline correction) and #7 (the ruleset context-format split). Reason the recommendation, do not trust it blindly.

### Quick Reference

```bash
# === DECISION RULE for a "rename X for discoverability" NITPICK ===
# 1. Is the name a load-bearing CROSS-REPO convention? Check ALL of these:

ORG=HomericIntelligence; REPO=Odysseus
NAME="_required.yml"   # the file the nitpick wants to rename

# (a) Is it referenced by branch-protection RULESETS / required status-check contexts?
#     NOTE: contexts derive from each job's `name:` value, NOT the workflow filename.
#     So renaming the FILE alone does NOT change ruleset contexts — but the file is
#     still the canonical CARRIER of the convention. Grep ALL FOUR ruleset JSONs:
#     the context FORMAT is NOT uniform across them (VERIFIED in Odysseus):
#       org-ruleset.json / org-ruleset-active.json  -> WORKFLOW-PREFIXED:
#           "Required Checks / lint", "Required Checks / unit-tests", ...  (9 entries)
#       repo-ruleset.json / repo-ruleset-active.json -> BARE job names:
#           "lint" + "integration_id": 15368, ...                          (8 entries)
#     canonical-checks.md:33 claims "bare job names" — only the repo-ruleset files
#     honor that; the org-ruleset files CONTRADICT the doc. Treat *-active.json as the
#     actually-enforced files. A diff that hard-codes ONE format silently passes vs
#     org-ruleset and is WRONG for repo-ruleset.
grep -RnE '"context"|integration_id' \
  configs/github/org-ruleset.json configs/github/org-ruleset-active.json \
  configs/github/repo-ruleset.json configs/github/repo-ruleset-active.json 2>/dev/null

# (a2) Confirm the load-bearing carrier is the JOB `name:` values, not the filename:
grep -nE '^    name:' .github/workflows/_required.yml
#   -> lint(16) unit-tests(150) build(240) schema-validation(261) deps/version-sync(279)
#      + non-required forbid-suppressions(66). Renaming the FILE changes no context;
#      renaming/removing a JOB does. "renaming the file breaks enforcement" is FALSE.

# (b) Is the name referenced in runbooks / canonical-checks docs / onboarding?
grep -RnF "$NAME" docs/ .github/ 2>/dev/null

# (c) Does the SAME name exist across sibling/fleet repos (a fleet convention)?
#     Matching the workflow `name:` line proves the CONTRACT, NOT byte-identity.
#     Do NOT claim "identical files" from one grep line — `name:` may sit at a
#     different line number per repo (e.g. line 1 here, line 7 in Scylla/Odyssey).
for d in */*/; do
  [ -f "$d/.github/workflows/$NAME" ] && \
    grep -nE "^\s*name:\s*Required Checks" "$d/.github/workflows/$NAME" \
      | sed "s|^|$d: |"
done

# 2. If ANY of (a)/(b)/(c) is true => DO NOT RENAME. Instead DOCUMENT:
#    - Add a self-documenting header comment to the file explaining WHY the name
#      is canonical and load-bearing (and that renaming has cross-repo blast radius).
#    - Add/strengthen the rationale at the SOURCE-OF-TRUTH doc (canonical-checks
#      / branch-protection runbook) so discoverability is solved without a rename.

# 3. SCOPE the blast radius precisely (do not overstate):
#    - Renaming the FILENAME  => breaks docs/runbook references + fleet uniformity
#                                (COSMETIC w.r.t. enforcement; ruleset contexts unaffected).
#    - Renaming the JOB NAMES => breaks ruleset required-status-check CONTEXTS
#                                (LOAD-BEARING; can deadlock ruleset enforcement).
#    State this distinction explicitly in the plan.

# 4. Verify your runner commands are REAL tasks before citing them in the plan.
#    VERIFIED: pixi.toml [tasks] here = lint("just lint"), validate("just validate-configs"),
#    build, test, clean, ci, status, check-submodule-drift, bootstrap.
#    There is NO `pixi run yamllint` and NO `pixi run markdownlint` task. Real calls:
sed -n '/\[tasks\]/,/^\[/p' pixi.toml         # list the REAL task names first
#   pixi run -- yamllint -d relaxed <file>     # binary on PATH, NOT a named task
#   pixi run lint                              # the named aggregate lint task
#   markdownlint runs ONLY in ci.yml against `docs/architecture.md docs/adr/*.md`
#   => configs/github/canonical-checks.md is in NO required markdown-lint scope.
grep -nE 'markdownlint' .github/workflows/ci.yml   # confirm the real md-lint scope

# 5. If you add an explanatory comment block to a workflow, keep it FREE of suppression
#    tokens (noqa / nosec / disable= / # type: ignore) so it cannot trip a
#    forbid-suppressions guard job (present at _required.yml:66). _required.yml may
#    already be excluded (.pre-commit-config.yaml:63) — but do NOT rely on that.
```

### Detailed Steps

1. **Pause on the word "discoverability."** A rename-for-clarity nitpick against an
   inscrutable-looking name is a trap: the name is often inscrutable *because* it is a
   terse, load-bearing convention. Treat "rename for discoverability" as a prompt to
   *investigate the name's role*, not as an approved task.
2. **Establish whether the name is a cross-repo convention.** Check the three carriers:
   (a) branch-protection rulesets / required status-check contexts, (b) runbooks +
   canonical-checks / onboarding docs, (c) sibling repos in the fleet. Any hit means the
   name is part of a contract.
3. **If it is a convention → DOCUMENT, do not rename.** The correct resolution of a
   discoverability nitpick against a cross-repo convention is to make the name
   *self-documenting*: a header comment in the file explaining why the name is canonical
   and load-bearing, plus a rationale paragraph at the source-of-truth doc. This delivers
   the discoverability the nitpick wanted, at near-zero blast radius.
4. **Scope blast radius precisely — separate filename from job names (VERIFIED).** In
   GitHub Actions branch protection, the required status-check context is **derived from
   each job's `name:` value**, NOT the workflow filename. Renaming the **file** breaks
   docs/runbook references and fleet uniformity but does **NOT** alter any ruleset context;
   renaming/removing a **job** breaks the contexts and can deadlock enforcement rollout. A
   plan that says "renaming the file breaks the rulesets/enforcement" is **FALSE** and, if
   committed as documentation, is worse than the nitpick it fixes (P7 / Principle of Least
   Astonishment — a false rationale shipped as docs is the exact defect a NOGO reviewer
   catches). Say "renaming the file breaks docs/uniformity; renaming jobs breaks ruleset
   enforcement." NOTE the context FORMAT is NOT uniform: org-ruleset pins
   `"Required Checks / <job>"`, repo-ruleset pins bare `"<job>"` — see step 7.
5. **Do not claim fleet-wide file identity from a single grep line (CONFIRMED).** Matching
   the workflow `name:` (or any header line) proves the **job-name contract + path
   convention**, not byte-identical files. The same `name:` can appear at different line
   numbers across repos — Scylla/Odyssey have `name:` at line 7, not line 1. Assert the
   contract, not file equality, and verify line placement per-repo (`head -3`) before
   saying "prepend above line 1."
6. **Verify every runner command you cite against `pixi.toml [tasks]` (VERIFIED).** Do NOT
   assume `pixi run <linter>` task names exist. In Odysseus `[tasks]` defines `lint =
   "just lint"`, `validate = "just validate-configs"`, plus build/test/clean/ci/status/
   check-submodule-drift/bootstrap — there is **no** `pixi run yamllint` and **no**
   `pixi run markdownlint`. Real invocations: `pixi run -- yamllint -d relaxed <file>`
   (binary on PATH) or `pixi run lint`. markdownlint runs ONLY in `ci.yml` against
   `docs/architecture.md docs/adr/*.md`, so `configs/github/canonical-checks.md` is in
   NO required markdown-lint scope. Cite the real invocation and state honestly when a
   file is covered by no gating check.
7. **Diff ALL FOUR ruleset JSONs; do not assume they match (KEY, VERIFIED).** The context
   FORMAT is NOT uniform: `org-ruleset.json` + `org-ruleset-active.json` pin
   workflow-PREFIXED contexts (`"Required Checks / lint"`, … 9 entries); `repo-ruleset.json`
   + `repo-ruleset-active.json` pin BARE job names (`"lint"` + `"integration_id": 15368`,
   … 8 entries). `canonical-checks.md:33` claims "bare job names" — only the repo-ruleset
   files honor that; the org-ruleset files contradict the doc. Treat the `*-active.json`
   files as the actually-enforced ones. A verification `diff` that hard-codes one context
   format (e.g. `"Required Checks / <job>"`) silently passes against org-ruleset and is
   wrong for repo-ruleset.
8. **Keep any added workflow comment free of suppression tokens.** When documenting the
   rationale in-file, avoid `noqa` / `nosec` / `disable=` / `# type: ignore` so the comment
   cannot trip a `forbid-suppressions`-style guard job (present at `_required.yml:66`).
   `_required.yml` may already be excluded (`.pre-commit-config.yaml:63`) — don't rely on it.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Took the NITPICK at face value and scoped a plan to rename `_required.yml` "for discoverability." | The name is NOT arbitrary — it is a deliberate, org-wide, load-bearing convention wired into branch-protection enforcement and runbooks across ~15 repos. A rename has disproportionate blast radius and can deadlock ruleset rollout. | For a "rename for clarity" nitpick against a cross-repo convention, the correct fix is to make the name self-documenting (header comment + rationale doc), NOT to rename. |
| 2 (KEY) | Asserted "renaming the file would break the ruleset rollout." | Ruleset required-status-check **contexts key off the BARE JOB NAME** (e.g. `lint`), not the workflow filename or a `Required Checks / lint` prefix. Renaming the **file alone** does NOT change the contexts — only renaming the **jobs** would. The plan overstated the file rename's blast radius. | Distinguish FILENAME (cosmetic: breaks docs/runbook refs + fleet uniformity) from JOB NAMES (load-bearing: breaks ruleset contexts). The real risk of a file rename is broken docs/uniformity, not broken enforcement. State this split explicitly. |
| 3 | Claimed the file is "identical across 14 submodules" based on `grep "name: Required Checks"` matching line 1 in each. | Matched the workflow NAME (a single header line), not byte-identical contents. Scylla/Odyssey had `name:` at line 7, not line 1 — the files are NOT byte-identical. | A single grep line match proves the job-name CONTRACT, not literal file equality. Never claim fleet-wide file identity from one matched line. |
| 4 | Cited `pixi run markdownlint` and `pixi run yamllint` as the repo's verification runners. | Never verified those exact pixi task names exist in Odysseus's `pixi.toml`. | Confirm the exact task name in `pixi.toml`/`justfile` before writing any runner command into a plan. |
| 5 | Read `org-ruleset.json` (9 status-check contexts) and `.pre-commit-config.yaml:63` via grep preview, then assumed sibling ruleset files and the full pre-commit config matched. | Did not diff `org-ruleset-active.json` / `repo-ruleset*.json` against `org-ruleset.json`, and read the pre-commit exclude line via grep preview only, not the full file. | Diff ALL source-of-truth artifacts you depend on; a single read + an assumption of parity is an unverified claim, not evidence. |
| 6 (NOGO root cause) | Wrote "renaming the file breaks enforcement/the ruleset rollout" into the plan and proposed committing it as in-file documentation. | FALSE mechanism: the status-check context derives from each job's `name:` value (VERIFIED: lint(16), unit-tests(150), build(240), schema-validation(261), deps/version-sync(279) in `_required.yml`), NOT the filename. Renaming the file changes no context. Committing a false rationale as docs is worse than the nitpick it fixes (P7 / POLA) — this is the exact defect the reviewer NOGO'd. | Verify the mechanism before committing a rationale as documentation. A wrong "why" shipped as docs misleads every future reader; renaming the FILE is cosmetic, renaming/removing a JOB is load-bearing. |
| 7 (KEY, VERIFIED) | Wrote a verification `diff` that hard-coded one ruleset context format (`"Required Checks / <job>"`) to check all ruleset JSONs. | The four ruleset JSONs are NOT uniform: org-ruleset(`-active`).json use the prefixed `"Required Checks / lint"` form (9 entries); repo-ruleset(`-active`).json use BARE `"lint"` + `"integration_id": 15368` (8 entries). The hard-coded diff silently PASSES against org-ruleset and is WRONG for repo-ruleset; `canonical-checks.md:33` only matches the repo-ruleset half. | NEVER assume the four ruleset JSONs are identical. Diff all four; treat `*-active.json` as the enforced ones. Do not hard-code one context format in a verification diff. |
| 8 | Cited `pixi run yamllint` / `pixi run markdownlint` as verification runners without checking `pixi.toml [tasks]`. | Those tasks DO NOT EXIST. `[tasks]` defines `lint = "just lint"`, `validate = "just validate-configs"`, build/test/clean/ci/status/check-submodule-drift/bootstrap. yamllint is a PATH binary (`pixi run -- yamllint -d relaxed <file>`); markdownlint runs only in `ci.yml` against `docs/architecture.md docs/adr/*.md`, so `canonical-checks.md` is in no required md-lint scope. | Grep `pixi.toml [tasks]` and the workflow files BEFORE citing a `pixi run X` command; cite the real invocation and say honestly when a file is gated by nothing. |
| 9 | Treated a cross-repo `grep "name: Required Checks"` match as proof the workflow files are byte-identical across the fleet. | A name match proves a shared job-name CONTRACT + path convention, not file equality — Scylla/Odyssey have `name:` at line 7, not line 1. A plan saying "prepend above line 1" would be wrong for those repos. | Assert the contract, not file identity; verify line placement per-repo (`head -3`) before claiming a fixed insertion point. |

## Results & Parameters

**Decision rule (copy-paste into a plan):**

```text
NITPICK: "rename <X> for discoverability/clarity"
  └─ Is <X> a load-bearing cross-repo convention?
       Carriers to check:
         (a) branch-protection rulesets / required status-check contexts
         (b) runbooks / canonical-checks / onboarding docs
         (c) sibling/fleet repos using the same name
     ├─ NO  → a local rename may be fine (still verify references).
     └─ YES → DO NOT RENAME. Make the name self-documenting:
                • header comment in the file (why it's canonical + blast radius)
                • rationale paragraph at the source-of-truth doc
              This delivers the discoverability with near-zero blast radius.
```

**Blast-radius table (GitHub Actions branch protection):**

| You rename… | Breaks… | Severity | Why |
|-------------|---------|----------|-----|
| the **workflow FILENAME** (`_required.yml`) | docs/runbook references + fleet uniformity | Cosmetic w.r.t. enforcement | Context derives from each job's `name:`, NOT the filename — enforcement is unaffected |
| a **JOB `name:`** (`lint`, `unit-tests`, …) | ruleset required-status-check CONTEXTS | Load-bearing | The context IS the job's `name:` value — renaming/removing it deadlocks enforcement until rulesets are updated |

**VERIFIED ruleset context-format split (Odysseus, `configs/github/`):** the four ruleset
JSONs are NOT uniform — diff all four, treat `*-active.json` as the enforced ones.

| File | Context format | Count | Example |
|------|----------------|-------|---------|
| `org-ruleset.json` | workflow-PREFIXED | 9 | `"Required Checks / lint"`, `"Required Checks / unit-tests"` |
| `org-ruleset-active.json` | workflow-PREFIXED | 9 | same as above |
| `repo-ruleset.json` | BARE job name + `integration_id` | 8 | `{ "context": "lint", "integration_id": 15368 }` |
| `repo-ruleset-active.json` | BARE job name + `integration_id` | 8 | same as above |

`canonical-checks.md:33` claims "context strings are **bare job names**" — only the
repo-ruleset files honor that; the org-ruleset files CONTRADICT the doc. `integration_id`
is `15368` (the GitHub Actions app, to scope the match to Actions). A verification `diff`
that hard-codes ONE format silently passes vs org-ruleset and is WRONG for repo-ruleset.

**VERIFIED job `name:` carriers in `_required.yml`:** lint(16), unit-tests(150),
build(240), schema-validation(261), deps/version-sync(279); non-required
forbid-suppressions(66). Renaming the FILE changes none of these; renaming a JOB does.

**VERIFIED `pixi.toml [tasks]`:** `bootstrap`, `status`, `check-submodule-drift`,
`build`, `test`, `clean`, `lint = "just lint"`, `validate = "just validate-configs"`,
`ci`. NO `pixi run yamllint`, NO `pixi run markdownlint`. Real calls:
`pixi run -- yamllint -d relaxed <file>` or `pixi run lint`. markdownlint runs ONLY in
`ci.yml` (`markdownlint docs/architecture.md docs/adr/*.md`) — `configs/github/canonical-checks.md`
is in NO required markdown-lint scope. forbid-suppressions guard at `_required.yml:66`;
`_required.yml` excluded from the pre-commit suppression check at `.pre-commit-config.yaml:63`.

**Case context:** Odysseus meta-repo, GitHub issue #215 (sole open child of Epic #174),
file `.github/workflows/_required.yml`. Recommended resolution: document the rationale
in-file + at the canonical-checks source-of-truth doc; do NOT rename. v1.0.0's plan was
NOGO'd for committing a false "rename breaks enforcement" mechanism as docs.

**Related skill (CI mechanics):** `gha-required-checks-branch-protection` covers the
underlying mechanics — bare-job-name = context, job key vs `name:` field disambiguation,
the reusable-workflow `_required.yml` aggregator pattern. This skill is the *planning
decision* layer on top of it (when NOT to rename, and how to scope the blast radius).

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Odysseus | Implementation plan for issue #215 / Epic #174 (`_required.yml` rename NITPICK) — plan written, NOT executed; v1.0.0 NOGO'd for committing a false "rename breaks enforcement" mechanism as docs | unverified — planning learning; v1.1.0 ground-truth FACTS (ruleset format split, job-`name:` carriers, pixi tasks, md-lint scope) grep/read-verified |
