---
name: pre-implementation-plan-review-wave
description: "Run a multi-agent pre-implementation review wave (R0/R1) against an Epic
  plan file and its child GitHub issues, catching regressions before implementation
  begins. Use when: (1) a plan file and child issues must be kept consistent, (2) a
  prior review wave (R0) claims fixes but artifacts may not all be updated, (3) you
  need 6 parallel specialist reviews with structured output contracts and idempotent
  GitHub posting."
category: evaluation
date: 2026-04-26
version: "1.0.0"
user-invocable: false
verification: unverified
tags: [review-wave, pre-impl, plan-review, second-opinion, r0, r1, multi-agent-review]
---

# Pre-Implementation Plan Review Wave (R0/R1)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-26 |
| **Objective** | Catch regressions in an Epic plan + child issues before handing off to implementers |
| **Outcome** | R1 wave found R0 fixes applied only to plan file, not to 4 child issue bodies; one wrong-port value introduced by R0 also caught |
| **Verification** | unverified — process/orchestration skill; review ran end-to-end and fixes verified, but no automated test suite |

## When to Use

- A plan file and N child GitHub issues must stay consistent (both are "source of truth" for implementers)
- A prior review wave (R0) says it fixed issues — validate that ALL artifacts were updated, not just the plan file
- You want 6 parallel dimension-specialists (arch / code / security / ux / ops / docs) with a structured output contract
- You need an idempotency guard before posting a GitHub comment (avoid duplicate review waves)
- Port numbers, config values, or library calls in a plan should be verified against upstream source files

## Verified Workflow

> **Warning:** This workflow has not been validated end-to-end by automated CI. Treat as a hypothesis until confirmed by a full implementation run. Verification level: unverified.

### Quick Reference

```bash
# Phase 1 — Scout pass (planning)
gh issue view <EPIC_NUMBER> --json body,comments   # Read epic + R0 comment
# Read plan file and grep for each of the 8 claimed-fixed items
grep -n "8080\|8082\|8085\|hermes_port" infrastructure/ProjectHermes/src/hermes/config.py
# Read every child issue body for regression evidence
for N in 154 164 166 167; do gh issue view $N --json body --jq '.body'; done

# Phase 2 — Idempotency check before posting
gh issue view <EPIC_NUMBER> --json comments \
  --jq '[.comments[] | select(.body | startswith("## Agent-Mesh Review Wave R1"))] | length'

# Phase 3 — Post consolidated R1 comment
gh issue comment <EPIC_NUMBER> --repo HomericIntelligence/<REPO> \
  --body "$(cat <<'ENDBODY'
## Agent-Mesh Review Wave R1
...
ENDBODY
)"

# Phase 4 — Fix child issues in parallel (bulk heredoc edit)
for N in 154 164 166 167; do
  gh issue edit $N --repo HomericIntelligence/<REPO> --body "$(cat <<'ENDBODY'
<corrected full body>
ENDBODY
)"
done

# Phase 5 — Verify fixes
for N in 154 164 166 167; do
  gh issue view $N --json body --jq '.body' | grep "<changed_item>"
done
```

### Detailed Steps

#### Phase 1: Scout Pass (do this before spawning agents)

1. Read the epic issue body and all prior review-wave comments (`gh issue view <N> --json body,comments`).
2. Read the plan file (the single `.md` containing the full implementation blueprint).
3. For each item the R0 summary claims it fixed, grep the plan file directly — do not trust the summary.
4. For every port number, config flag, or library call mentioned in the plan, grep the **upstream source file** (e.g., `config.py`, `docker-compose.yml`) in the relevant submodule.
5. Read each child issue body for the same claimed-fixed text.
6. Record which items are: (a) fixed in plan only, (b) fixed in both, (c) not fixed anywhere.

The scout pass is cheap (minutes) and prevents agents from debating wrong ground truth.

#### Phase 2: Launch 6 Parallel Reviewer Agents

Launch in a single `Agent()` call with shared inputs:

**Agent dimensions**: arch / code / security / ux / ops / docs

**Inputs per agent**:
- Plan file path
- R0 checklist (explicit per-item verification instructions)
- Scope boundaries
- Mandatory output format (enforced upfront — agents that skip the table make synthesis much harder)

**Mandatory output contract** (every agent must follow):

```markdown
## <dim>-review (R1)

**Verdict**: PASS | WARN | FAIL

### R0 Verification

| R0 Item | Plan file | Child issues | Verdict |
|---------|-----------|--------------|---------|
| <item>  | fixed / broken | fixed / broken | resolved / partial / regressed |

### New Findings

- CRIT-<id>: <description>
- WARN-<id>: <description>
- INFO-<id>: <description>

### Confirmed Clean

- <item that was checked and is correct>
```

The three-column R0 table (Plan file / Child issues / Verdict) is the key structural element.
It distinguishes "plan was fixed but issue wasn't" (partial) from "both fixed" (resolved).

#### Phase 3: Synthesis and Idempotency

1. Check that no prior R1 comment exists:
   ```bash
   gh issue view <N> --json comments \
     --jq '[.comments[] | select(.body | startswith("## Agent-Mesh Review Wave R1"))] | length'
   ```
   If result > 0, skip posting (review already ran).

2. Consolidate agent outputs into one comment:
   - R0 verification table (aggregated)
   - New findings with CRIT-/WARN-/INFO- prefix
   - Confirmed clean items

3. Post:
   ```bash
   gh issue comment <N> --repo <OWNER>/<REPO> \
     --body "$(cat <<'ENDBODY'
   ## Agent-Mesh Review Wave R1
   ...
   ENDBODY
   )"
   ```

4. Verify:
   ```bash
   gh issue view <N> --json comments \
     --jq '.comments[-1] | {author, createdAt, length: (.body | length)}'
   ```

#### Phase 4: Fix All Affected Artifacts

When a fix is needed, enumerate **every artifact** that contains the incorrect text:

1. Plan file → Edit tool
2. Each child issue body → `gh issue edit N --body "$(cat <<'ENDBODY' ... ENDBODY)"`
3. Any notes / runbook that references the same value

Fix in parallel where possible. Verify each fix:
```bash
gh issue view <N> --json body --jq '.body' | grep "<expected_value>"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| R0 "fix" that only edits the plan file | R0 author edited `plan.md` but not 4 child issue bodies | Implementers reading issues (not the plan) would re-introduce every regression | A review wave fix pass must enumerate every artifact containing the incorrect text |
| Correcting wrong port with another wrong value | R0 found "8082 is wrong, actual is 8080" but wrote "8082 → 8085" in the resolution | The fix-author guessed instead of re-reading the upstream source | When fixing a port/config, always re-read the actual source file before picking a value |
| `html.WithUnsafe(false)` to disable raw HTML | Plan suggested using `html.WithUnsafe(false)` on goldmark renderer | `html.WithUnsafe()` (no args) ENABLES raw HTML; `WithUnsafe(false)` is a compile error or no-op | Omit the call entirely — goldmark's default is safe (raw HTML disabled) |
| `sandbox="allow-scripts allow-same-origin"` on same-origin iframe | Both flags together on a same-origin iframe allow the framed script to remove the sandbox attribute | When both present, framed script can call `window.parent.document.querySelector('iframe').removeAttribute('sandbox')` | Use `sandbox="allow-scripts allow-popups"` — never combine allow-scripts with allow-same-origin |
| Trusting plan file's claimed port value | Plan claimed Hermes default port is 8085; R0 claimed it corrected to 8082 | Neither value matched the actual source: `hermes_port: int = 8080` in `config.py:25` | Always grep upstream `config.py` / `docker-compose.yml` — never trust a plan's claimed default |

## Results & Parameters

### R0 Verification Table Structure

The three-column split is the key insight for catching partial fixes:

```markdown
| R0 Item | Plan file | Child issues | Verdict |
|---------|-----------|--------------|---------|
| Hermes port 8082→8080 | fixed (8080) | broken (still 8085) | PARTIAL — issue bodies not updated |
| html.WithUnsafe(false) removed | fixed | broken (example still present) | PARTIAL |
| iframe sandbox flags corrected | fixed | fixed | RESOLVED |
```

Verdict key:
- **RESOLVED** — both plan and all child issues corrected
- **PARTIAL** — plan fixed, at least one child issue still broken
- **REGRESSED** — R0 introduced a new wrong value (e.g., corrected one wrong port with another)

### Upstream Source Verification Pattern

Never trust a plan's claimed value for infrastructure defaults. Always verify:

```bash
# Port numbers
grep -n "port\|PORT" infrastructure/<SubModule>/src/<pkg>/config.py
grep -n "port:" infrastructure/<SubModule>/docker-compose.yml

# Library API (e.g., goldmark)
grep -rn "WithUnsafe\|WithSafe" vendor/ go.sum  # or check upstream docs
```

### 6-Agent Launch Pattern

```python
agents = [
    Agent(scope="architecture", inputs=inputs, output_contract=contract),
    Agent(scope="code",         inputs=inputs, output_contract=contract),
    Agent(scope="security",     inputs=inputs, output_contract=contract),
    Agent(scope="ux",           inputs=inputs, output_contract=contract),
    Agent(scope="ops",          inputs=inputs, output_contract=contract),
    Agent(scope="docs",         inputs=inputs, output_contract=contract),
]
# Launch all 6 in a single call — do not launch sequentially
results = run_parallel(agents)
```

Inputs per agent:
- `plan_file_path` (absolute)
- `child_issue_numbers` list
- `r0_checklist` (per-item with explicit verification instructions)
- `output_contract` (the exact markdown structure to emit)

### Idempotency Guard

```bash
COUNT=$(gh issue view <N> --json comments \
  --jq '[.comments[] | select(.body | startswith("## Agent-Mesh Review Wave R1"))] | length')
if [ "$COUNT" -gt 0 ]; then
  echo "R1 already posted — skipping"
  exit 0
fi
```

### Bulk Issue Body Fix (4 issues in parallel)

```bash
# Fetch current body, identify broken section, rebuild full body
gh issue view 154 --json body --jq '.body'  # inspect
gh issue edit 154 --repo HomericIntelligence/<REPO> --body "$(cat <<'ENDBODY'
<full corrected body here>
ENDBODY
)"
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence/Odysseus | Epic #151 Atlas dashboard — R1 wave after R0 partial fixes | 4 child issues (#154, #164, #166, #167) body-edited; wrong Hermes port (8085→8080) corrected |
