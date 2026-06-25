---
name: architecture-agents-md-contract-from-codebase
description: "How to PLAN adding an AGENTS.md agent-behavior contract to a repo by DERIVING every rule from the real codebase + CLAUDE.md invariants instead of writing generic boilerplate, and how to surface the planning risks honestly. Use when: (1) planning/adding an AGENTS.md agent-behavior contract (scope-in/out, permitted/prohibited actions, --dangerously-skip-permissions policy, escalation, verification commands) to a repo; (2) deriving the permitted-tools / off-limits / escalation set from real pipeline/harness source (e.g. the --allowedTools flag in the runner) PLUS CLAUDE.md invariants (ADRs append-only, configs canonical, submodule pins matter) rather than aspiration; (3) wiring the new doc into an EXISTING markdownlint CI gate (extend the fixed file list, do not add a new job) and confirming .markdownlint.json disables the rules it would trip BEFORE claiming green; (4) adding a doc-to-source drift guard (a grep tying the documented tool contract to the runner code so they cannot silently diverge); (5) reusing an in-ecosystem sibling AGENTS.md as the structural template and scoping the new one so two AGENTS.md files do not diverge."
category: architecture
date: 2026-06-20
version: "1.0.0"
user-invocable: false
verification: unverified
tags:
  - agents-md
  - agent-behavior-contract
  - planning
  - derive-from-codebase
  - claude-md-invariants
  - permitted-tools
  - dangerously-skip-permissions
  - markdownlint
  - ci-gate
  - drift-guard
  - line-number-drift
  - meta-repo
  - unverified-assumptions
---

# Planning an AGENTS.md Agent-Behavior Contract Derived From the Codebase

> **Warning:** This workflow has not been validated end-to-end. Treat as a hypothesis until CI confirms.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-20 |
| **Objective** | Capture the planning meta-skill surfaced while planning Odysseus issue #186 ("add a root AGENTS.md"): how to plan an AGENTS.md agent-behavior-contract doc so every rule is grounded in real pipeline code + CLAUDE.md invariants, wired into the existing CI gate, and protected by a doc-to-source drift guard — and how to surface the planning risks honestly. |
| **Outcome** | Plan produced only. Nothing was written, no doc was created, no markdownlint or CI run was executed. The durable value is the *planning pattern* plus the explicit risk inventory. |
| **Verification** | unverified — PLANNING artifact. No file was written, no lint/CI ran. Every cited line number and "will pass markdownlint" claim is an assumption, not a confirmation. |
| **Category** | architecture / planning |
| **Related Issues** | Odysseus #186 |

The win is not "write an AGENTS.md." It is: **derive the contract from what the
code actually does, attach it to the enforcement that already exists, and guard it
against drift — then be loud about the assumptions you never ran.**

---

## When to Use

Use this skill when:

1. You are **planning or adding an `AGENTS.md`** agent-behavior contract to a repo
   (scope in/out, permitted vs prohibited actions, `--dangerously-skip-permissions`
   policy, coordination, escalation, verification commands).
2. You need to **derive the permitted-tools / off-limits / escalation set from real
   source** — the runner/harness `--allowedTools` flag and the danger-flag invocation,
   plus the repo's `CLAUDE.md` invariants — rather than writing generic boilerplate.
3. You want to **wire the doc into an existing markdownlint CI gate** instead of adding
   a new CI job, and must confirm the disabled-rules config covers it.
4. You want to **add a drift guard** tying the documented tool contract to the code.
5. A **sibling `AGENTS.md` already exists in the ecosystem** and you want to reuse its
   structure without letting the two contracts diverge.

Do NOT use this as a record of executed work — it is a plan with open assumptions.

---

## Verified Workflow

> **Warning:** This section is a **Proposed Workflow**, not a verified one. It was
> *not* executed: no AGENTS.md was written, `markdownlint` was never run against the
> draft, and CI never confirmed it. Every line number cited below is from a grep
> snapshot and WILL drift — re-grep by content, never trust the numbers.

### Quick Reference

```text
1. Glob **/AGENTS.md  → reuse the in-ecosystem sibling's section structure.
2. Derive each rule from source:
     permitted tools + danger flag  ← runner's --allowedTools / --dangerously-skip-permissions
     off-limits set                 ← CLAUDE.md invariants (ADRs append-only, configs canonical, pins matter)
   Re-grep by CONTENT, not by the line numbers in the plan.
3. Extend the EXISTING markdownlint file list (one line) — do NOT add a CI job.
4. Confirm .markdownlint.json disables the rules the doc trips (MD013/022/032/040/060…)
   AND actually RUN markdownlint on the draft (MD041/MD024/MD033 are NOT disabled).
5. Add a drift guard: grep the documented tool string against the runner source.
6. Cross-reference the doc (CLAUDE.md banner, README bullet) WITHOUT disturbing
   the project-instructions structure the harness relies on.
7. Scope the new AGENTS.md to its own repo so it does not duplicate a sibling's rules.
```

1. **Find the in-ecosystem template first.** `Glob **/AGENTS.md` — if a sibling exists
   (here `provisioning/Myrmidons/AGENTS.md`), reuse its section set (Scope in/out table,
   Permitted/Prohibited Actions, `--dangerously-skip-permissions` Policy, Coordination,
   Escalation, Verification Commands). Reusing keeps sibling docs consistent; do not
   invent a brand-new structure.

2. **Ground every rule in real code, not aspiration.** The permitted toolset and the
   danger flag come *verbatim* from the pipeline source — the runner's invocation line
   (e.g. `--dangerously-skip-permissions` and `--allowedTools Bash,Read,Write,Edit,Glob,Grep`
   in `e2e/claude-myrmidon.py`). git/gh permitted actions come from the same runner's
   git/gh calls. The **off-limits** set is derived from `CLAUDE.md` invariants: ADRs are
   append-only, `configs/` is canonical, submodule pins matter, ai-maestro removed per
   ADR-006. **Re-grep each fact by content** — the plan's cited line numbers are a
   snapshot and drift.

3. **Wire the doc into the EXISTING enforcement gate.** CI lints a fixed file list
   (e.g. `markdownlint docs/architecture.md docs/adr/*.md` in `.github/workflows/ci.yml`).
   **Extend that one line** to include the new file. Do **not** add a new markdownlint
   job — that duplicates the gate.

4. **Prove the lint passes — do not assume it.** Confirm the root `.markdownlint.json`
   disables the rules the new doc would trip (MD013 line-length, MD022/MD032 blank-line,
   MD040 fenced-lang, MD060 table). But MD041 (first-line-h1), MD024 (duplicate heading),
   MD033 (inline HTML) are typically **NOT** disabled — so actually **run** markdownlint
   against the drafted content before claiming green. This is the single biggest
   "looks done but isn't" risk.

5. **Add a drift guard between the doc and its source of truth.** A verification grep
   (e.g. `grep -q "Bash,Read,Write,Edit,Glob,Grep" e2e/claude-myrmidon.py`) ties the
   documented contract to the runner code so they cannot silently diverge — the
   executable-convention-guard pattern applied to a doc.

6. **Make it discoverable via the existing cross-ref convention.** Add a banner line in
   `CLAUDE.md`, a bullet in `README.md` / `docs/README.md`. When editing `CLAUDE.md`,
   do not disturb the `## Key Principles` / section structure the harness loads as
   authoritative project instructions. Confirm any relative link resolves
   (e.g. `docs/README.md` → `../AGENTS.md` only works if `docs/README.md` is one level deep).

7. **Scope the new AGENTS.md to its own repo.** With two `AGENTS.md` files now present
   (root + sibling), explicitly scope the root one to the meta-repo and do NOT duplicate
   the sibling's submodule-specific rules — divergence is the long-term failure mode.

### Most uncertain assumptions / risks (the honest part a reviewer must see)

- **Unverified line numbers.** The plan cites exact lines (the runner's `--allowedTools`
  and danger-flag lines, the git/gh call sites, `ci.yml`'s markdownlint line, a `README.md`
  bullet line) from grep snapshots, not a fresh full read. Line numbers drift — re-grep by
  content.
- **markdownlint pass is ASSUMED, not run.** The plan asserts the doc passes because of
  the disabled-rules config, but lint was never executed. MD041/MD024/MD033 are not
  disabled and could still fire. Biggest hidden risk.
- **CLAUDE.md edit collides with project-instructions.** `CLAUDE.md` is loaded as
  authoritative instructions; a banner must not disturb its structure.
- **Two AGENTS.md files now exist** (root + sibling) — contract-divergence risk; scope
  each one explicitly.
- **Relative-link resolution** (`../AGENTS.md` from `docs/README.md`) depends on the doc
  being exactly one directory deep — confirm before asserting the link works.

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| ------- | -------------- | ------------- | -------------- |
| Trusting grep line numbers as stable | Citing exact lines (`claude-myrmidon.py:258/259`, `ci.yml:30`, `README.md:36`) from grep snapshots in the plan | Line numbers drift as files change; the cited line may no longer be the right one | Re-grep by CONTENT, not by remembered numbers — anchor every fact to a string match |
| Asserting markdownlint passes from the disabled-rules config alone | Concluding the new AGENTS.md is lint-green because `.markdownlint.json` disables MD013/022/032/040/060 | MD041/MD024/MD033 are NOT disabled and never actually ran; "config disables some rules" ≠ "this file passes" | RUN `markdownlint` against the drafted content before claiming green |
| Adding a new CI markdownlint job | Proposing a separate markdownlint job/step for the new doc | Duplicates the gate that already lints a fixed file list; two gates drift | Extend the EXISTING fixed file-list line by one filename instead of adding a job |

---

## Results & Parameters

The plan produced a single root `AGENTS.md` whose contract is **derived**, not invented:

| Contract element | Derived from |
| ---------------- | ------------ |
| Section structure | sibling `provisioning/Myrmidons/AGENTS.md` (reuse, don't reinvent) |
| Permitted tools + `--dangerously-skip-permissions` | runner invocation in `e2e/claude-myrmidon.py` (`--allowedTools Bash,Read,Write,Edit,Glob,Grep`) |
| Permitted git/gh actions | the runner's own git/gh call sites |
| Off-limits / prohibited set | `CLAUDE.md` invariants: ADRs append-only, `configs/` canonical, submodule pins matter, ai-maestro removed per ADR-006 |
| Enforcement | extend the existing `markdownlint` fixed file list in `.github/workflows/ci.yml` (one line) |
| Drift guard | `grep -q "Bash,Read,Write,Edit,Glob,Grep" e2e/claude-myrmidon.py` |
| Discoverability | banner in `CLAUDE.md`, bullet in `README.md` / `docs/README.md` |

All of the above are **proposed**. No file was written, no lint or CI ran. The line
numbers and the markdownlint-green claim are assumptions (see Risks).

---

## Verified On

| Project | Context | Details |
| ------- | ------- | ------- |
| Odysseus | Issue #186 planning ("add a root AGENTS.md") | Planning-only; **unverified** — plan never executed, no AGENTS.md written, `markdownlint`/CI never run. All cited line numbers and the lint-pass claim are assumptions. |
