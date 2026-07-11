---
name: skill-consolidation-nuance-audit-workflow
description: "Use when: (1) a bulk skill consolidation (10+ skills merged into bundles) has just completed and you need to verify no knowledge was lost, (2) a canonical skill was absorbed into a larger bundle and the bundle must preserve all failed attempts, trigger conditions, and copy-paste commands, (3) you need to run a parallel swarm audit across many source→bundle pairs and automatically generate amendment PRs for any detected gaps"
category: tooling
date: '2026-06-07'
version: "1.1.0"
verification: verified-ci
history: skill-consolidation-nuance-audit-workflow.history
tags:
  - audit
  - consolidation
  - nuance
  - knowledge-loss
  - bundle
  - parallel-swarm
  - amendment
  - skills
---

# Skill Consolidation Nuance Audit Workflow

Parallel swarm workflow for detecting and restoring knowledge lost when individual skill files
are bulk-consolidated into larger bundle files.

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Verify no knowledge was lost after a Myrmidon swarm triage merged ~175 satellite skills into canonicals, then a second consolidation wave merged those canonicals into larger bundles |
| **Outcome** | Successful — 134 high/medium items found across all 25 consolidations; 18 amendment PRs created and merged; 1 marketplace regen PR |
| **Scale** | 25 audit agents + 18 amendment agents = 43 total agents; ~15 min for full audit phase |

## When to Use

- After bulk skill consolidation where 10+ skills are merged into a single bundle file
- Before discarding a branch whose work was "absorbed" by main — first verify the bundle
  actually contains the nuance from each source
- When `/advise` quality has degraded after a consolidation wave (missing commands, vague trigger
  conditions, no specific failure modes)
- Any time a consolidation commits says "consolidate N skills into `<bundle>`" and N ≥ 10

### Audit EVERY Bundle — Do Not Size-Threshold

Audit **every** bundle on the merge worklist, not a size-filtered subset. It is tempting to audit
only the "biggest" bundles (8+ skill merges, absorb-into-existing) on the assumption that small
merges are safe. That assumption is wrong:

- In a 50-bundle consolidation, pass 1 audited only the 13 highest-risk bundles and declared the
  merges "sound." A later pass 2 audited the OTHER 37 mid-size bundles (3–7 skills each) and found
  **22 of 36 had genuine body-not-surfaced losses** (one was an already-dissolved canonical,
  excluded). Restricting to the biggest bundles missed ~60% of the real losses, which lived in the
  mid-size merges.
- LESSON: the loss rate is roughly uniform across bundle sizes; size is not a proxy for risk. Audit
  all bundles from the merge worklist.

### Materiality Bar for a "LOST" Finding (keep this — it works)

A finding counts as **LOST** only when it is ALL of:

1. A distinctive command, exact flag/param, named failure mode, or unique Failed-Attempts lesson
2. ABSENT from the canonical body
3. Such that surfacing it would **change what a reader does**

These are explicitly NOT losses:

- Generalization of specific content into a broader statement
- Deduplication of content already present elsewhere in the canonical
- DELIBERATE scope-narrowing during the merge

Because every absorbed body is preserved verbatim in the `.history` `## Superseded from` blocks,
"lost" means "not surfaced in the canonical body" — i.e. **recoverable, not destroyed**. The fix is
always to re-surface from `.history`, never to reconstruct from memory.

## Verified Workflow

### Quick Reference

```bash
# Phase 0: Verify how main removed a source file (was it intentional consolidation?)
git log --diff-filter=D --oneline origin/main -- skills/<source-name>.md

# Phase 1: Audit swarm — one Haiku agent per source→bundle pair
# Each agent emits structured findings JSON
# Schema: {has_lost_nuance: bool, lost_items: [{type, text, severity}], summary: str}

# Phase 2: Amendment swarm — one Sonnet agent per bundle with losses
# Each agent reads bundle + all contributing source files, inserts missing content,
# bumps version, fixes markdownlint, writes to /tmp/amendments/<label>.md

# Phase 3: PR creation — one branch/PR per amended bundle
git checkout -b fix/amend-bundle-<label> origin/main
cp /tmp/amendments/<label>.md skills/<bundle>.md
git add skills/<bundle>.md
git commit -m "fix(skill-merge): restore lost nuance in <bundle> from <N> sources"
gh pr create --title "fix(skill-merge): restore lost nuance in <bundle>" \
  --body "..."
gh pr merge --auto --squash
```

### Detailed Steps

#### Phase 0: Pre-Audit Check

Before declaring a source file "missing from main," confirm HOW main removed it:

```bash
git log --diff-filter=D --oneline origin/main -- skills/<source>.md
```

- If the deletion commit message says `feat(skill-merge): consolidate N skills into <bundle>` →
  the file was intentionally consolidated; check the bundle
- If no deletion commit exists → the file is genuinely absent; that is a separate issue

#### Phase 1: Parallel Audit Swarm

Launch one Haiku agent per source→bundle pair. For each agent:

1. Read the source skill: `git show HEAD:skills/<source>.md` (or `origin/<branch>:skills/...`)
2. Read the destination bundle: `git show origin/main:skills/<bundle>.md`
3. Apply conservative flagging criteria (see Results section)
4. Emit structured JSON findings

**Scale**: 25 agents in parallel runs in approximately 15 minutes.

**Swarm shape (audit→fix loop, refined pass-2 form)**: The audit/fix loop is itself a swarm:

- **Audit phase** — one **read-only Explore agent per bundle**, capped at **≤5 agents per wave**.
  Each agent reads the canonical `.md` plus its `.history`, and emits a per-skill `OK`/`LOST`
  verdict for every contributing skill followed by a single `VERDICT:` line for the bundle.
- **Fix phase** — one **general-purpose amend agent per bundle that has a material loss**. The agent
  restores the nuance into the canonical body (as new Detailed Steps and/or Failed-Attempts rows),
  bumps the version **MINOR**, appends a `.history` changelog entry, and opens an auto-merge PR.
- **Clean bundles get NO PR.** A bundle whose every contributing skill verdicts `OK` produces no
  branch, no amend, no PR — only bundles with at least one material `LOST` are amended.

This refines the earlier "Haiku per pair / Sonnet per bundle" wording: the auditor is now a
read-only Explore agent scoped to one whole bundle (reads canonical + `.history`) rather than one
isolated source→bundle pair, and the amender is a general-purpose agent. Both forms are valid; the
per-bundle read-only Explore form is preferred because it reads the verbatim `.history` body
directly, which is required to tell omission apart from generalization.

### Common Loss Shapes (auditor checklist)

When auditing a bundle, specifically hunt for these recurring loss shapes — they are the ones that
most often vanish from the canonical body while remaining only in `.history`:

- Exception / type mapping tables
- Specific CLI flags (e.g. `--force-with-lease`, a `message=` keyword argument)
- Named failure modes with their reproduction steps
- "Permanent fix" paths dropped in favor of only the reactive/workaround fix
- Pipeline or procedure how-tos collapsed to a single one-line pointer
- ruff / lint rule-specific fix recipes
- "green CI doesn't certify X" cautions

#### Phase 2: Triage Findings

Collect all `{has_lost_nuance, lost_items, summary}` outputs. Prioritize by severity:

- **high**: Specific failure mode with error message is absent from bundle
- **medium**: Copy-paste-ready command missing; trigger condition genuinely uncovered
- **low**: Cosmetic difference; same lesson differently phrased (do NOT amend for low)

#### Phase 3: Amendment Swarm

For each bundle with high/medium items, launch one Sonnet agent:

1. Read the bundle file fully
2. Read all contributing source files for that bundle
3. Insert missing content into the appropriate section (Failed Attempts table, When to Use, etc.)
4. Bump the version field (e.g., `2.0.0` → `2.1.0`)
5. Fix any markdownlint issues (language tags on fences, blank lines around headings/tables)
6. Write the amended file to `/tmp/amendments/<bundle-label>.md`

#### Phase 4: PR Creation and Auto-Merge

For each amended bundle:

```bash
# Create a branch off main
git checkout -b fix/amend-bundle-<label> origin/main

# Copy the amended file
cp /tmp/amendments/<bundle-label>.md skills/<bundle>.md

# Commit (do NOT include marketplace.json — it auto-regenerates on merge)
git add skills/<bundle>.md
git commit -m "fix(skill-merge): restore lost nuance in <bundle> from absorbed sources"

# Push and create PR
git push -u origin fix/amend-bundle-<label>
gh pr create --title "fix(skill-merge): restore lost nuance in <bundle>" \
  --body "$(cat <<'EOF'
## Summary
- Restores N high/medium nuance items lost when <N> source skills were consolidated
- Adds missing failed attempts: <brief list>
- Adds missing trigger conditions: <brief list>

## Test plan
- [ ] validate_plugins.py passes
- [ ] markdownlint passes
- [ ] Content review: all inserted sections match source material
EOF
)"

# Enable auto-merge
gh pr merge --auto --squash
```

**Important**: Do NOT add `marketplace.json` to any amendment PR branch. The auto-update
workflow regenerates it on merge; including it creates a merge conflict on every branch.

**Pre-commit helper (run-once-and-re-stage)**: Before the real commit, have the amend agent run
`pre-commit run --files <skill>.md <skill>.history` ONCE and then re-stage both files. The
end-of-file fixer modifies the `.history` file on its first pass, which aborts the real commit if
not pre-run; running it once and re-staging avoids the abort. (Same lesson as the merge pass.)

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| JS template literal with unescaped shell variable | Used `${GITLEAKS_VERSION}` inside a JS backtick string in a workflow script | The workflow runtime evaluates `${VAR}` inside backtick template literals before executing the JS; the variable is undefined at script parse time, producing `undefined` or an empty string | Escape with `${'$'}{VAR}` when shell variable syntax appears inside JS template literals in workflow files |
| `gh pr merge --squash --admin` on conflicting PR | Used `--admin` flag expecting it to bypass merge conflicts | `--admin` bypasses branch protection rules (required reviews, status checks) but does NOT resolve content conflicts; Git cannot merge two different file contents without human resolution | Resolve the conflict first, then merge; `--admin` is not a force-merge for content conflicts |
| Including marketplace.json in amendment PRs | Let `git add -A` or `git add .` stage the auto-generated `marketplace.json` along with the skill file | Every amendment branch had a different `marketplace.json` state, causing merge conflicts between branches | Stage only the specific skill file by name (`git add skills/<name>.md`); use a follow-up PR to regenerate marketplace.json after all amendments merge |
| Flagging cosmetic differences as "lost nuance" | Audit agents flagged reworded trigger conditions and paraphrased lessons as lost knowledge | This generated false positives and unnecessary amendment work; bundles correctly paraphrased the lesson without losing the substance | Only flag as "lost" when: a specific error message/command is literally absent; a trigger condition covers a genuinely different scenario; do NOT flag reformulations |
| Audited only the 13 largest bundles, then declared the consolidation sound | A first pass covered just the 8+-skill merges and the 5 absorb-into-existing bundles, skipping the 37 mid-size (3–7 skill) bundles | A second pass over the 37 mid-size bundles found 22 of 36 had genuine body-not-surfaced losses — ~60% of the real losses lived in the merges that were skipped | Audit EVERY bundle on the merge worklist; size is not a proxy for risk and the biggest-bundles-only heuristic misses the majority of losses |
| Treated a bundle as clean because the canonical "generalized" the content | Auditor read only the canonical body, saw the topic was covered at a higher level, and verdicted OK | Generalization is fine, but several canonicals had dropped the concrete commands/flags entirely while keeping only the abstract statement — omission was mistaken for generalization | Distinguish generalization from omission by reading the verbatim `.history` `## Superseded from` body, not just the canonical; if a concrete command/flag exists in `.history` but nowhere in the body, it is a LOSS |
| Committed the amend without pre-running pre-commit | Staged the `.md` and `.history` then ran `git commit` directly | The end-of-file fixer hook modified the `.history` file on its first pass and aborted the commit | Run `pre-commit run --files <skill>.md <skill>.history` once, re-stage both files, then commit |

## Results & Parameters

### Audit Agent Output Schema

```json
{
  "has_lost_nuance": true,
  "lost_items": [
    {
      "type": "failed_attempt",
      "text": "Description of missing failure mode with specific error",
      "severity": "high"
    },
    {
      "type": "trigger_condition",
      "text": "Specific use case not covered by any bundle trigger",
      "severity": "medium"
    },
    {
      "type": "command",
      "text": "Copy-paste command or config block",
      "severity": "medium"
    },
    {
      "type": "parameter",
      "text": "Specific parameter value with rationale",
      "severity": "low"
    },
    {
      "type": "lesson",
      "text": "Non-obvious insight",
      "severity": "low"
    }
  ],
  "summary": "3 high, 2 medium, 1 low items. Main gaps: missing error-code failure mode in Failed Attempts; missing --dry-run trigger."
}
```

### Conservative Flagging Criteria

Flag as "lost" ONLY when:

- A specific failure mode with its error message or error code is absent from the bundle
- A copy-paste-ready command, config block, or parameter set is missing entirely
- A trigger condition covers a genuinely different scenario not addressed by the bundle

Do NOT flag:

- Same lesson phrased differently (paraphrase ≠ loss)
- Cosmetic differences in wording or ordering
- Content superseded by better information in the bundle
- Low-severity reformulations

### Scale Reference (2026-06-07 session)

| Phase | Agents | Agent Tier | Duration | Findings |
| ------- | ------- | ---------- | -------- | -------- |
| Audit swarm | 25 | Haiku | ~15 min | 134 high/medium items across all 25 bundles |
| Amendment swarm | 18 | Sonnet | ~20 min | 18 bundle files amended |
| PR creation | 18 | — | ~5 min | 18 PRs created, auto-merge enabled |
| Marketplace regen | 1 | — | ~2 min | PR #2196 |

All 25 audited consolidations had at least one high/medium loss. Bulk consolidation of 10+ skills
into a single bundle almost always loses nuance — particularly the "Failed Attempts" table entries
and copy-paste-ready commands, which are frequently dropped in favor of higher-level prose.

### marketplace.json Conflict Resolution

When an amendment PR has a merge conflict only on `marketplace.json`:

```bash
# Option A: Remove marketplace.json from the branch to unblock merge
git checkout fix/amend-bundle-<label>
git rm --cached marketplace.json
git commit -m "chore: exclude marketplace.json (auto-regenerated on merge)"
git push
# Then merge normally; follow up with a single regen PR

# Option B: If conflict is on the skill file itself, resolve manually first
git checkout origin/main -- marketplace.json
git add marketplace.json
git commit -m "chore: reset marketplace.json to main"
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Mnemosyne | PRs #1791–#1925 second-wave consolidation audit, June 2026 — 25 audit agents, 18 amendment PRs (#2176–#2193), all CI green | verified-ci |
| Mnemosyne | 2026-06-07 two-pass audit of the 50-bundle consolidation: pass 2 covered 36 bundles, found 22 with material losses, all restored via amend swarm | nuance audit pass 2 |

## References

- Related skill: [skill-audit-and-merge.md](skill-audit-and-merge.md) — first-pass deduplication workflow
- CLAUDE.md plugin standards — required frontmatter fields and section requirements
