---
name: merged-project-specialized-reviewer
description: "Create a project-specialized read-only reviewer subagent by merging an existing general-review-specialist agent with WebFetch/WebSearch/Bash capabilities and project-pinned context (gate thresholds, dependency SHAs, friction inventory, citation-discipline rules). Use when: (1) a project has artifacts that cite primary sources (papers, model cards, API specs) and citation correctness matters, (2) the project has pinned thresholds/SHAs/invariants that must not drift across documents, (3) a generic reviewer would either miss project-specific drift or re-derive context every invocation, (4) you want read-only review with WebFetch capability rather than the standard Read/Grep/Glob-only specialist."
category: evaluation
date: 2026-05-12
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [reviewer, subagent, agent-merge, project-pinned-context, webfetch, citation-verification, read-only, agent-extension]
---

# Merged Project-Specialized Reviewer

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-12 |
| **Objective** | Define a repeatable pattern for producing a project-specialized read-only reviewer subagent that fuses a general-review-specialist's breadth with WebFetch/WebSearch capability and project-pinned context (gate thresholds, dependency SHAs, friction-inventory rows, citation-discipline rules), so the reviewer can audit cross-claim drift without re-deriving project context every invocation. |
| **Outcome** | Successful on Predictive-Coding-in-Mojo Phase 0 scoping (mvillmow/Random): the merged reviewer caught a finding that two earlier reviewers (one citation-focused, one code-focused) missed — namely that the cited 26.21% SOTA number from ASGE is on VGG11, but the same paper has a 51.58% result on ResNet18-CHx4, so the project's 51.5% stretch goal is already exceeded by the same paper in a different architecture family. The earlier reviewers verified the citation but lacked the gate-threshold pin in context. |
| **Verification** | verified-local (used in one session against one project; pattern not yet validated across additional projects). |

## When to Use

- Project has artifacts that cite primary sources (research papers, model cards, API docs at specific URLs) and citation correctness matters.
- Project has pinned thresholds, SHAs, or other invariants that must not drift across documents (gate thresholds, pinned dependency commits, friction-inventory rows).
- A general-purpose reviewer would either miss project-specific drift (no pinned context) or re-derive the project context every invocation (slow + inconsistent).
- You want read-only review with WebFetch capability — the standard ProjectOdyssey general-review-specialist is read-only Read/Grep/Glob only.
- Cross-claim audits are needed where verifying a citation is necessary but not sufficient — e.g., the cited number is real but doesn't apply at the architectural scope claimed.

## When NOT to Use

- Pure code review where CI / typechecking covers correctness — use the standard reviewer.
- Project has no primary-source citations — the WebFetch capability adds nothing.
- Project pins change frequently — the agent definition needs updating every time, which defeats the purpose.

## Verified Workflow

### Quick Reference

```bash
# 1. Pick a base reviewer agent definition (e.g., HomericIntelligence/ProjectOdyssey
#    general-review-specialist.md — read-only Sonnet, Read/Grep/Glob, 10-dimension breadth).
# 2. Write merged agent to ~/.claude/agents/<project>-reviewer.md with:
#    - tools: Read, Grep, Glob, WebFetch, WebSearch, Bash
#    - model: sonnet
#    - Authority section forbidding mutating Bash commands
#    - Project-pinned context section (gates, SHAs, friction inventory)
#    - Output-format pin (sections + per-finding structure + confidence scoring)
# 3. Invoke via a registered WebFetch-capable reviewer (since the new agent
#    is not in the current session's harness registry):
#      Agent(subagent_type="feature-dev:code-reviewer",
#            prompt="Operate as <name> per ~/.claude/agents/<name>.md. Read it first.")
```

### Detailed Steps

1. **Pick a base reviewer agent.** Start from a project's existing read-only general-review-specialist (e.g., the `general-review-specialist.md` from HomericIntelligence/ProjectOdyssey — read-only Sonnet with `Read,Grep,Glob` and a 10-dimension code-review breadth scope). The base provides the structural review-quality conventions (output format, severity tiers, evidence requirements).

2. **ADD capability tools.** Append `WebFetch` and `WebSearch` to the `tools:` frontmatter — these are essential for primary-source citation verification and for resolving any URL referenced in artifacts under review. Append `Bash`, but in the agent's Authority section explicitly enumerate the read-only subset (`gh issue view`, `gh issue list`, `git log`, `git show`, `git diff`, `curl -sL` against verified-safe URLs, `jq` over their output) and explicitly forbid mutating commands (`gh issue create`, `git commit`, `git push`, file edits via shell redirection). The Bash tool itself does not differentiate; the gate is enforced via the system prompt.

3. **DROP irrelevant references.** Remove orchestrator hand-off references, sibling-agent name-drops, or repository-path assumptions from the base agent that don't apply to your project. The merged agent should stand alone for the new project.

4. **ADD project-pinned context section.** At the bottom of the system prompt, add a `## Project pins (load-bearing context)` section enumerating: gate thresholds (with units and architecture/dataset scope), pinned dependency SHAs (e.g., `ProjectOdyssey SHA e3e0de83`), friction-inventory rows (a compact table of known issues the reviewer should treat as priors), and project-specific citation-discipline rules (cite-format requirements, what counts as an unsourced claim). The pins are stated as authoritative — the reviewer audits against them rather than re-deriving them.

5. **Pin the output format.** Mandate four sections in the report: `## Critical findings`, `## High-confidence concerns`, `## Worth checking before <next-milestone>`, `## Verdict`. Per-finding structure: title with confidence score (0-100), `file:line` evidence, fetched URL or quoted text, suggested fix in one sentence. This makes triage mechanical for the orchestrator.

6. **Pin confidence-scoring thresholds.** Each finding carries a 0-100 confidence score. Below 70: report as "Worth checking" rather than "Critical." Above 95: include the literal fetched evidence so the orchestrator can verify the verification. This bounds false-positive critical findings.

7. **Install the merged agent at user scope.** Write the file to `~/.claude/agents/<project>-reviewer.md`.

8. **Work around the harness registry limitation.** User-scoped agents written after harness startup are NOT discoverable in the current session's agent registry — only in the next session. To use the merged agent in the same session, invoke a registered WebFetch-capable reviewer (e.g., `feature-dev:code-reviewer`) and instruct it to operate as the merged agent: `"You are operating as <name> per ~/.claude/agents/<name>.md. Read that file first; it pins the project conventions you'll need."` This is functionally equivalent for ad-hoc use.

9. **Validate by checking for cross-claim drift.** A successful merged reviewer will catch findings that connect two pieces of pinned context — for example, "the cited SOTA number is on architecture A, but the gate threshold is exceeded by the same paper on architecture B." A reviewer without the pins cannot make this connection even if it verifies each citation individually.

## Recommended merged-agent file structure

Paste at `~/.claude/agents/<project>-reviewer.md`:

```markdown
---
name: <project>-reviewer
description: "Project-specialized read-only reviewer for the <project> project. Reviews <artifact types>. Verifies <verification dimensions>. Use for any review of artifacts produced under <project-path>/."
tools: Read, Grep, Glob, WebFetch, WebSearch, Bash
model: sonnet
---

# <Project> Reviewer

## Identity
Read-only review specialist for the <project>. Consolidates <base agent>'s
N-dimension breadth with citation-correctness audit capability (WebFetch) needed
for <project>'s research-document deliverables.

## Authority
**Read-only.** Bash is permitted only for the read-only subset (`gh issue view`,
`gh issue list`, `git log`, `git show`, `git diff`, `curl -sL` against verified-safe
URLs for citation pages, `jq` on the output of these). **Never** invoke mutating
commands.

## Scope
[Per artifact type the project produces, list what to check]

## Citation discipline (project convention)
[Cite-format rules, what counts as an unsourced claim, etc.]

## Project pins (load-bearing context)
- Gate thresholds: <numbers with units and architecture/dataset scope>
- Pinned SHAs: <values>
- Friction inventory: <table or summary>

## Output format
Markdown report. Sections: `## Critical findings` / `## High-confidence concerns` /
`## Worth checking before <next-milestone>` / `## Verdict`.
Per-finding structure: title with confidence 0-100, file:line evidence, URL or
quoted text, suggested fix in one sentence.

## Notes for the orchestrator
- No fixes from me; I report, you decide.
- No batched re-reviews; each pass of fixes gets its own invocation.
- Hard-stop on fabrication: a fabricated citation blocks until corrected.
```

## Recommended invocation pattern (when agent not yet in harness registry)

```python
Agent(
    description="Reviewer review of <artifact>",
    subagent_type="feature-dev:code-reviewer",  # or any registered WebFetch-capable reviewer
    prompt="""You are operating as `<project-reviewer-name>` per
`~/.claude/agents/<project-reviewer-name>.md`. Read that file first; it pins
the project conventions you'll need.

[The actual review prompt follows.]"""
)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Bare ProjectOdyssey general-review-specialist for citation review | Used the upstream agent unmodified | Tools list is `Read,Grep,Glob` only — no WebFetch, can't verify arXiv IDs against the live abs page | Citation-correctness review needs WebFetch; the base agent must be extended, not used as-is |
| Generic feature-dev:code-reviewer for citation review | Has WebFetch but no project pins | Reviewer verified citations are real but missed the architecture-scoping issue with the SOTA gate threshold (couldn't connect "26.21% is VGG11" to "51.5% stretch goal already exceeded by same paper's ResNet18-CHx4") | Project pins (gate thresholds, SHAs) must be in the reviewer's system prompt for cross-claim audits to work |
| Direct invocation of user-scoped agent in same session | Wrote agent to `~/.claude/agents/<name>.md`, then tried `subagent_type: "<name>"` | Harness's agent registry is fixed for the session; agents added mid-session aren't discoverable | Use a registered agent + "operate as X per ~/.claude/agents/<name>.md" prompt as a workaround until next session |

## Results & Parameters

### Key insights

1. **The merge pattern.** Start from a base reviewer agent definition (e.g., `general-review-specialist.md`). ADD `WebFetch`, `WebSearch`, `Bash` (gated to read-only subset). DROP orchestrator hand-off references that don't apply. ADD a project-pinned context section at the bottom — gate thresholds, dependency SHAs, friction-inventory rows, citation-discipline rules. The agent file goes to `~/.claude/agents/<name>.md` for user-scoped install.

2. **Why the pinned context is load-bearing.** Without pins, even a WebFetch-capable reviewer can verify each citation individually but cannot detect cross-claim drift. With pins, the reviewer connects "the cited number is on architecture A" to "the gate threshold is exceeded by the same paper on architecture B" — a finding no individually-correct citation check would surface.

3. **Bash gated by system prompt, not by tool.** The Bash tool itself doesn't differentiate read-only from mutating commands. The gate must be in the agent's Authority section: enumerate the allowed read-only subset; explicitly forbid mutating commands; rely on the model's instruction-following discipline. Findings include suggested fixes; the orchestrator decides whether to apply them.

4. **Output format pinned for triageability.** Mandate the four sections (Critical / High-confidence / Worth checking / Verdict) and the per-finding structure (title + confidence 0-100, file:line evidence, URL or quoted text, one-sentence fix). This makes the orchestrator's triage step mechanical rather than judgement-heavy.

5. **Confidence-scoring thresholds.** Below 70: "Worth checking" not "Critical." Above 95: include the literal fetched evidence so the orchestrator can verify the verification. Bounds false-positive critical findings.

6. **Harness registry limitation.** User-scoped agents at `~/.claude/agents/<name>.md` written after harness startup are NOT discoverable in the current session — only in the next. Workaround: invoke a registered agent with a prompt that says "operate as <name> per ~/.claude/agents/<name>.md; read that file first."

### Concrete example: pc-research-reviewer

The session that produced this skill created `~/.claude/agents/pc-research-reviewer.md` with:

- Base: HomericIntelligence/ProjectOdyssey `general-review-specialist`
- Added tools: `WebFetch`, `WebSearch`, `Bash` (read-only subset)
- Project pins:
  - Gate thresholds: ASGE 26.21% (VGG11) and 51.5% stretch goal
  - ProjectOdyssey SHA: `e3e0de83`
  - Friction inventory: known Phase 0 issues (table)
  - Citation discipline: every numeric claim must cite a primary source with arXiv ID + page/section

The merged reviewer caught the architecture-scoping finding that two earlier reviewers missed: the 51.5% stretch goal was already exceeded by ASGE's 51.58% result on ResNet18-CHx4 (same paper, different architecture family) — a connection only possible with both the gate threshold and the citation in the reviewer's pinned context.

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| mvillmow/Random | Predictive-Coding-in-Mojo Phase 0 scoping; merged ProjectOdyssey general-review-specialist + WebFetch + project pins (ASGE 26.21%/51.5% gate thresholds, ProjectOdyssey SHA `e3e0de83`, friction inventory) | Agent at `~/.claude/agents/pc-research-reviewer.md`; caught the ASGE VGG11/ResNet18-CHx4 architecture-scoping finding that two prior reviewers missed |
