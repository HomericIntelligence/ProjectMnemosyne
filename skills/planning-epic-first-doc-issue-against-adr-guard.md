---
name: planning-epic-first-doc-issue-against-adr-guard
description: "Plan the FIRST, code-free documentation sub-issue of a large epic — an 'ADR + architecture-doc skeleton' issue whose entire job is to transcribe the epic's already-approved design VERBATIM while satisfying an existing executable ADR structural-guard test. The plan writes no product code; its only machine-checked acceptance gate is the ADR guard, so treat that test as the spec and READ it directly. Use when: (1) an epic body already carries the full approved design (prompt-function paths, stage tables, diagrams) and the first sub-issue is 'write ADR-NNNN + the architecture doc' — transcribe from the epic body, do NOT re-derive; (2) the repo enforces ADR structure with an executable guard (e.g. ProjectHephaestus tests/unit/docs/test_adr_records.py) and you must derive requirements from the test's asserts, not from prose docs; (3) you must confirm a long-table / un-tagged-fence doc will lint before assuming it — grep .markdownlint.yaml for MD013 (line-length) and MD040 (fenced-code-language) being false and MD025 (single H1) true; (4) you are tempted to choose ADR Status Accepted vs Proposed for a decision whose code is not yet written; (5) the plan's acceptance criteria include human-judged checks (N stages present, tags, paths) that a self-written grep 'verifies' — recognize the self-fulfilling gate and flag it. This is the PLANNING-AGAINST-A-GUARD companion to architecture-executable-convention-guard-pattern (which is about AUTHORING the guard) and to adr-authoring-indexing-and-maintenance (which is about ADR mechanics)."
category: documentation
date: 2026-07-04
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - planning
  - documentation-plan
  - epic-first-issue
  - adr
  - architecture-decision-record
  - executable-guard-as-spec
  - verbatim-transcription
  - epic-body-source-of-truth
  - markdownlint-config
  - md013-md040-md025
  - self-fulfilling-gate
  - line-number-drift
  - status-accepted-vs-proposed
  - code-free-issue
  - nygard-4digit
  - projecthephaestus
---

# Planning: The Epic's First Doc Issue Against an ADR Guard

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-07-04 |
| **Objective** | Capture the durable planning discipline for the FIRST, code-free documentation sub-issue of a large epic: an "ADR + architecture-doc skeleton" issue whose plan must transcribe the epic's approved design VERBATIM and satisfy an existing executable ADR structural-guard test |
| **Outcome** | PLAN ONLY — a plan for ProjectHephaestus issue #1810 (`docs(adr): ADR-0006 queue-based in-process automation pipeline + architecture doc skeleton`, first of epic #1809). No files were written, no tests run, no CI. Distilled discipline: read the guard test as the spec; transcribe from the epic body, don't re-derive; grep the markdownlint config; and honestly flag the self-fulfilling greps and epic-sourced line numbers |
| **Category** | documentation |
| **Verification** | unverified (plan not executed) |

The concrete trigger: epic #1809 defines a queue-based in-process automation pipeline
and its first sub-issue #1810 is a **code-free** ADR-0006 + architecture-doc skeleton.
The epic body already contains the full approved design — the exact prompt-function
paths (e.g. `prompts/planning.py:223 get_plan_prompt`), the stage table, and the
pipeline diagram. The plan's whole job is to move that design into a durable ADR +
architecture doc that PASSES the repo's ADR structural guard, without inventing or
re-deriving anything. This skill is the planning-side companion to
`architecture-executable-convention-guard-pattern` (which is about *making* a guard
executable) and `adr-authoring-indexing-and-maintenance` (which is about ADR
mechanics/index sync) — neither covers *planning a doc issue AGAINST an existing guard
while faithfully transcribing an epic's contract*.

## When to Use

Use this skill when planning a task that has ALL of these shapes:

- The issue is the **FIRST sub-issue of a large epic** and its deliverable is
  **documentation only** — an ADR plus an architecture-doc skeleton — with **no product
  code**. (In ProjectHephaestus this is `state:needs-plan` + `architecture` label + a
  `docs(adr): ...` title, e.g. #1810.)
- The **epic body already carries the full approved design** (prompt-function file:line
  paths, a stage/queue table, a mermaid/text pipeline diagram). The plan's job is
  transcription, not design.
- The repo enforces ADR structure with an **executable structural-guard test** (in
  ProjectHephaestus: `tests/unit/docs/test_adr_records.py`) — so the *spec* for the ADR
  is that test's asserts, not any prose in `docs/adr/README.md`.
- You need to confirm a doc full of **long table rows and un-tagged code fences will
  lint** before assuming it (grep `.markdownlint.yaml`).
- You must pick an **ADR Status** for a decision whose implementing code does not exist
  yet.
- The plan's acceptance criteria mix a **machine-checked gate** (the ADR guard) with
  **human-judged checks** ("all 8 stages present", "paths present", "tags on fences")
  that a self-written `grep` appears to "verify" — you must recognize that the grep is
  self-fulfilling, not an external gate.

**Key trigger:** you catch yourself about to *re-derive* a design that the epic body
already states verbatim, OR about to *assume* the ADR/doc will pass CI without having
read the guard test and the markdownlint config.

## Verified Workflow

> **Verification level: `unverified`.** This is a PLAN that was NOT executed — no files
> were written, no tests run, no CI. Everything below is a hypothesis until CI confirms.
> In particular, the prompt-function line numbers (e.g. `prompts/planning.py:223
> get_plan_prompt`) are **epic-sourced and NOT re-grepped against the live tree** — treat
> them as verify-at-implementation. The step-by-step is titled **Proposed Workflow** for
> that reason (the `## Verified Workflow` heading is retained only to satisfy the flat
> skill schema).

### Quick Reference

```bash
# 1. TRANSCRIBE, DON'T RE-DERIVE. The epic body is the approved contract. Fetch it
#    and quote its exact prompt-function paths / stage table / diagram verbatim.
gh issue view 1809 --repo HomericIntelligence/ProjectHephaestus   # the EPIC, not the sub-issue

# 2. READ THE GUARD AS THE SPEC. Derive ADR requirements from the test's asserts,
#    NOT from prose in docs/adr/README.md. In ProjectHephaestus:
sed -n '1,60p' tests/unit/docs/test_adr_records.py
#   It enforces (see the asserts, not any doc):
#     - filename ^\d{4}-[a-z0-9-]+\.md$            (4-digit zero-padded, kebab slug)
#     - title    ^# ADR-NNNN:                       (regex-anchored to the filename prefix)
#     - literal  - Status:   and   - Date:          (list-style metadata, not **Status**:)
#     - sections ## Context / ## Decision / ## Alternatives considered / ## Consequences
#                 (note the LOWERCASE 'c' in "Alternatives considered")
#     - numbers  contiguous from 0001, no gaps or dupes
#     - README   linked set == on-disk ADR set      (BIDIRECTIONAL index sync)

# 3. VERIFY THE DOC WILL LINT — grep the config, don't assume.
grep -nE 'MD013|MD040|MD025' .markdownlint.yaml
#   MD013: false  -> long table rows / unwrappable lines PASS (line length unbounded)
#   MD040: false  -> ```mermaid / ```text fences without a language tag PASS
#   MD025: true   -> EXACTLY ONE H1 per doc (the "# ADR-NNNN:" title is that H1)

# 4. RE-GREP EPIC-SOURCED PATHS AT IMPLEMENTATION (do NOT trust epic line numbers).
grep -rn 'def get_plan_prompt' prompts/          # confirm the file:line hasn't drifted
```

### Proposed Workflow

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis
> until CI confirms.

1. **Fetch the EPIC body and treat it as the approved contract — transcribe verbatim.**
   When an epic carries the full approved design in its body, the first documentation
   sub-issue's plan must *transcribe* that design, not re-derive it — any deviation
   drifts from the approved contract. Run `gh issue view <epic#>` (here #1809, NOT the
   sub-issue #1810) and quote the exact prompt-function paths, stage/queue tables, and
   pipeline diagram it already contains. Re-deriving a stage's fail-target, budget, or
   ordering from memory is how the doc silently diverges from what was signed off.

2. **Read the ADR structural-guard test and treat its asserts as the spec.** The only
   machine-checked acceptance gate for a code-free ADR issue is the guard test — so read
   it directly rather than trusting the prose in `docs/adr/README.md`. In
   ProjectHephaestus that is `tests/unit/docs/test_adr_records.py`, which enforces:

   | Requirement | Exact form the test asserts |
   | ----------- | --------------------------- |
   | Filename | `^\d{4}-[a-z0-9-]+\.md$` — 4-digit zero-padded prefix + kebab slug (e.g. `0006-queue-based-automation-pipeline.md`) |
   | Title | `^# ADR-NNNN:` regex-anchored to the filename's 4-digit prefix (title `NNNN` must equal the filename `NNNN`) |
   | Metadata | literal `- Status:` and `- Date:` LIST-style lines (NOT `**Status**:`) |
   | Sections | `## Context`, `## Decision`, `## Alternatives considered` (lowercase 'c'), `## Consequences` — all four present |
   | Numbering | numeric prefixes contiguous from `0001`, no gaps or duplicates |
   | Index sync | README linked-set **==** on-disk ADR set (bidirectional — a stale link OR a missing link both fail) |

   This is an INSTANCE of the executable-convention-guard pattern; the difference is you
   are *satisfying* an existing guard, not authoring one. Derive every ADR requirement
   from an assert you can point at.

3. **Confirm the doc will lint by grepping `.markdownlint.yaml` — never assume.** An ADR
   + architecture doc is full of long table rows and un-tagged code fences; whether that
   lints depends entirely on the config. Grep it:
   - `MD013: false` → line length is unbounded, so long table rows and long unwrappable
     instruction lines pass. (If MD013 were on at 120, the stage table would fail.)
   - `MD040: false` → fenced code blocks without a language (` ```mermaid ` / ` ```text `)
     pass. (If MD040 were on, every diagram fence would need a tag.)
   - `MD025: true` → exactly ONE H1 per document. The `# ADR-NNNN:` title IS that single
     H1 — so the architecture doc's top heading must also be a single H1, and every other
     heading is `##`+.

   Do not assume these; a repo that flips MD013 on will reject the whole doc.

4. **Choose the ADR Status deliberately and confirm it against the repo convention.** The
   decision's implementing code does not exist yet, so `Proposed` vs `Accepted` is a real
   judgment call. This plan chose `Accepted` to mirror ADR-0001 (which was Accepted
   before the enforcement test existed) — but that is a convention claim the reviewer
   should confirm. Read a recent ADR's Status line and match it; do not assume.

5. **Anchor the acceptance criteria on the MACHINE-checked gate and be honest about the
   rest.** The ADR guard test is the only external, machine-checked criterion. Any other
   "acceptance check" the plan lists — "all 8 stages present", "all prompt paths present",
   "fences tagged" — is human-judged. If the plan "verifies" those with a `grep` the
   author themselves wrote (e.g. `grep -c '^### [1-8]\.'` assuming the 8 stage headings
   use a `### N.` prefix), recognize that the heading style is a *plan choice not dictated
   by any test*, so the grep is **self-fulfilling**, not an external gate. State this
   plainly in the plan.

6. **Re-grep every epic-sourced path at implementation time.** The prompt-function line
   numbers were copied from the epic body, not independently grepped against the current
   tree, so they may have drifted since the epic was authored. A doc-only PR will NOT fail
   CI on a stale line number — but the architecture doc is a contract that LATER PRs
   implement against, so a stale path misleads every downstream implementer. Either
   `grep -rn "def get_plan_prompt"` (etc.) to confirm each path before finalizing, OR note
   explicitly in the doc that the paths are epic-sourced and verified-at-implementation.

7. **Update the README index in the SAME change (bidirectional guard).** The guard
   asserts `linked == on_disk`. Adding `docs/adr/0006-*.md` without adding its README
   index link fails `test_readme_index_lists_every_adr`, and vice-versa. Plan the index
   row as part of the same PR, not a follow-up.

### Risks the reviewer/implementer should focus on

- **Stale prompt-function paths.** The `prompts/planning.py:223 get_plan_prompt`-style
  paths are transcribed from the epic without a re-grep. `grep -rn "def get_plan_prompt"`
  each one before finalizing, or the doc must label them epic-sourced.
- **Faithfulness of "verbatim from epic".** Confirm the transcription did not *summarize*
  away a stage's fail-target or budget. "Verbatim" means the stage table's cells match
  the epic body's cells, not a paraphrase.
- **Only ONE criterion is machine-checked.** The `tests/unit/docs` guard is the sole
  external gate. Criterion 2 (8 stages + tags + paths) is human-judged; the plan leans on
  `grep`s the author wrote, not an independent test. Do not read a green self-grep as CI
  confidence.
- **Status choice.** `Accepted` for not-yet-written code mirrors ADR-0001, but confirm
  that is the repo's convention rather than assuming.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Re-deriving the design from the sub-issue title | Tempted to reconstruct the pipeline stages/paths from #1810's title + memory instead of the epic | The approved design lives in the EPIC body (#1809); re-deriving drifts from the signed-off contract and risks a wrong fail-target/budget | Fetch `gh issue view <epic#>` and transcribe the exact paths/tables/diagram verbatim; the sub-issue title is not the spec |
| Trusting `docs/adr/README.md` prose as the ADR spec | Planned the ADR structure from the human-readable index/README description | The ONLY machine-checked gate is `tests/unit/docs/test_adr_records.py`; prose can lag the asserts (e.g. lowercase 'c' in `## Alternatives considered`, list-style `- Status:` not `**Status**:`) | Read the guard test's asserts directly and derive requirements from them |
| Assuming markdownlint would reject long table rows / un-tagged fences | Nearly wrapped the stage table and added languages to every ` ``` ` fence pre-emptively | `.markdownlint.yaml` has `MD013: false` and `MD040: false`, so long rows and ` ```mermaid `/` ```text ` fences already pass; MD025:true only requires a single H1 | Grep `.markdownlint.yaml` for MD013/MD040/MD025 before assuming any lint behavior |
| Treating a self-written grep as an acceptance gate | Listed `grep -c '^### [1-8]\.'` as "verification" that all 8 stages are present | The `### N.` heading style is a plan choice no test enforces, so the grep passes because the author wrote the doc to match it — self-fulfilling, not an external check | Only the ADR guard is machine-checked; label author-written greps as self-fulfilling, not CI confidence |
| Copying epic line numbers as ground truth | Carried `prompts/planning.py:223 get_plan_prompt` etc. straight from the epic into the doc | Epic was authored earlier; the tree may have drifted, and the doc is a contract later PRs implement against, so a stale path misleads implementers | Re-grep each path (`grep -rn "def get_plan_prompt"`) at implementation, or label paths epic-sourced/verify-at-implementation |
| Adding the ADR file without the README index row | Considered landing `0006-*.md` and updating the index later | `test_readme_index_lists_every_adr` asserts `linked == on_disk`; a missing OR stale link fails | Add the README index row in the SAME PR as the ADR file |

## Results & Parameters

### Status of this capture

**PLAN ONLY — unverified.** No ADR file or architecture doc was written, no
`tests/unit/docs/test_adr_records.py` run, no markdownlint run, no CI. Frontmatter
`verification: unverified`. Do not read any part of this skill as `verified-local` or
`verified-ci`.

### The ADR structural-guard contract (ProjectHephaestus)

Derived by READING `tests/unit/docs/test_adr_records.py` (not from prose docs):

```text
filename : ^\d{4}-[a-z0-9-]+\.md$          (e.g. 0006-queue-based-automation-pipeline.md)
title    : ^# ADR-NNNN:                     (NNNN must equal the filename's 4-digit prefix)
metadata : - Status:   and   - Date:        (list-style lines; NOT **Status**:)
sections : ## Context
           ## Decision
           ## Alternatives considered       (lowercase 'c')
           ## Consequences
numbering: contiguous from 0001, unique
index    : README linked-set == on-disk ADR set   (bidirectional)
```

### Markdownlint knobs that make a long-table/diagram doc pass

```text
MD013 (line-length)        : false  -> long table rows & unwrappable lines pass
MD040 (fenced-code-lang)   : false  -> ```mermaid / ```text fences pass untagged
MD025 (single H1)          : true   -> exactly one H1 (the # ADR-NNNN: title)
```

### Epic-vs-sub-issue commands

```bash
gh issue view 1809 --repo HomericIntelligence/ProjectHephaestus   # EPIC — the approved design
gh issue view 1810 --repo HomericIntelligence/ProjectHephaestus   # sub-issue — the deliverable
```

### Uncertain assumptions the reviewer should scrutinize

- Prompt-function line numbers are **epic-sourced, not re-grepped** against the live tree.
- ADR `- Status:` chosen `Accepted` (mirrors ADR-0001, Accepted pre-enforcement-test) —
  confirm against repo convention vs `Proposed` for not-yet-written code.
- The `grep -c '^### [1-8]\.'` stage check is **self-fulfilling** — the heading style is a
  plan choice, not a test-dictated one.

### Expected outcomes (hypothesis)

- A code-free PR: `docs/adr/0006-<slug>.md` + its `docs/adr/README.md` index row + the
  architecture-doc skeleton. `tests/unit/docs/test_adr_records.py` and
  `markdownlint-cli2` should both pass — but this is unconfirmed; CI is the real gate.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectHephaestus | Issue #1810 (first sub-issue of epic #1809) — PLAN for ADR-0006 + architecture-doc skeleton; unverified, no code/tests/CI | Plan-only capture (2026-07-04) |
