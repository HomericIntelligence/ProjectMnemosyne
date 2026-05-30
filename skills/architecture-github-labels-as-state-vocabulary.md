---
name: architecture-github-labels-as-state-vocabulary
description: "Use mutually-exclusive `state:*` GitHub labels as the single source of truth for per-issue pipeline state instead of parsing free-text comment bodies. Use when: (1) an automated pipeline gates work on a verdict regex-parsed from the latest comment, (2) free-text comment-based state machine is fragile because pre-contract or off-format comments are unparseable and leave issues permanently stuck, (3) you need a gh issue label state vocabulary that the planner, reviewer, and implementer all read identically, (4) a plan-review GO/NOGO gate needs to short-circuit cheaply across 100s of issues without re-parsing every comment every loop iteration, (5) you need to self-heal stuck issues without manual cleanup — backfill a state label from an existing parseable comment on a one-time fallback, (6) two pipeline components share a gate but read it via different signals causing infinite-loop drift (planner skips because plan exists, implementer defers because review unparseable), (7) you want to harden the state-tagging GitHub Action against the Actions injection class while still tagging issues:opened with `state:needs-plan`, (8) you need to provision the 3 labels across an org without races against the first reviewer write."
category: architecture
date: 2026-05-29
version: "1.0.0"
user-invocable: false
verification: verified-local
tags:
  - github-labels
  - state-vocabulary
  - state-machine
  - plan-review
  - go-nogo-gate
  - free-text-fragile
  - structured-state
  - self-healing-backfill
  - actions-injection
  - org-provisioning
  - gh-issue-edit
  - mutually-exclusive-labels
  - source-of-truth
  - shared-gate-divergence
---

# Architecture: GitHub Labels as State Vocabulary (Not Free-Text Comments)

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-29 |
| **Objective** | Replace fragile regex-parsing of free-text comment bodies (e.g. `Verdict: GO/NOGO`) with mutually-exclusive `state:*` GitHub labels as the single source of truth for per-issue pipeline state — eliminates "comment unparseable → issue permanently stuck" and "planner and implementer disagree → infinite loop" failure modes |
| **Outcome** | Pattern executed end-to-end on 2026-05-29 in HomericIntelligence/ProjectHephaestus PR #707; 911 automation tests pass locally, ruff + mypy clean. Three labels (`state:needs-plan`, `state:plan-no-go`, `state:plan-go`) defined, idempotent provisioner CLI shipped, `issues:opened` workflow auto-tags new issues, reviewer applies-and-removes opposites, implementer trusts the terminal label absolutely. One-time comment-scan backfill self-heals legacy issues. |
| **Verification** | verified-local — full automation suite (911 tests) + ruff + mypy clean on the local worktree; CI validation pending on PR #707 ([ProjectHephaestus PR #707](https://github.com/HomericIntelligence/ProjectHephaestus/pull/707)). Updates to be backfilled here once CI is green. |
| **Live observation that motivated this** | 320 "no parseable Verdict" WARNINGs across an org-wide automation run, plus wasteful re-planning of already-approved issues because the latest comment's verdict line had drifted from the regex contract |

## When to Use

- An automated pipeline gates per-issue work on a regex-parsed verdict from the **latest** comment body, and you have observed unparseable comments that permanently block forward progress
- You are building a planner+reviewer+implementer pipeline where **all three components must read the same gate signal** and you want the signal to be cheap to query and impossible to misparse
- You see logs like `Issue #N: no parseable Verdict line in plan-review comment — defaulting to NOGO` more than a handful of times across one loop iteration
- You want a `gh issue list --label state:plan-go` style cheap query to drive ranking, dashboards, or per-state batching
- You need a **state vocabulary** that survives prompt/contract evolution: changing the LLM's verdict-line format must not invalidate already-approved issues
- You are migrating an existing pipeline and need a **one-time fallback** that promotes a parseable verdict from existing comments into a label, so the migration self-heals without manual relabeling
- You suspect a **shared-gate divergence bug** where two pipeline components read different signals: e.g. the planner sees "plan comment exists → skip" while the implementer sees "review unparseable → defer" → the issue cycles forever
- You are wiring an `on: issues: opened` Action that tags new issues with `state:needs-plan` and need to harden it against the GitHub Actions script-injection class
- You need to provision the labels across an org so the first reviewer write doesn't race against a missing label name

**Don't use when:**

- The pipeline state is naturally ephemeral (in-memory only, no persistence across loop iterations) — overkill
- The state machine has more than ~5 states and lots of transitions — labels become noisy; use a JSON state file in the repo or a real DB
- You only need a single boolean and `gh pr review --approve` already encodes it natively
- The repo is a personal scratch project with no org-wide automation — KISS, just leave comments

## Verified Workflow

### Quick Reference

```bash
# ── The 3 mutually-exclusive labels (the entire vocabulary) ──
#
#   state:needs-plan   — set by issues:opened workflow (or no state label = needs-plan)
#   state:plan-no-go   — set per NOGO review iteration
#   state:plan-go      — terminal: implementer trusts this absolutely, never re-plans
#
# Only ONE of the three may be set on an issue at any time.

# ── Reviewer transition (NOGO this iteration) ──
gh issue edit <N> \
    --repo <owner>/<repo> \
    --add-label state:plan-no-go \
    --remove-label state:needs-plan \
    --remove-label state:plan-go

# ── Reviewer transition (GO — terminal) ──
gh issue edit <N> \
    --repo <owner>/<repo> \
    --add-label state:plan-go \
    --remove-label state:needs-plan \
    --remove-label state:plan-no-go

# ── Implementer read (cheap, no comment fetch needed) ──
if gh issue view <N> --json labels --jq '.labels[].name' | grep -qx 'state:plan-go'; then
    proceed_to_implementation
else
    defer
fi

# ── One-time self-healing backfill (run when no state label is set) ──
if no_state_label_present && latest_plan_review_comment_parseable_as_GO; then
    apply state:plan-go   # promote legacy comment verdict → label
elif no_state_label_present && latest_plan_review_comment_parseable_as_NOGO; then
    apply state:plan-no-go
fi
# Subsequent runs short-circuit on the label — no re-parsing.

# ── Org-wide idempotent provisioning ──
for color_pair in "state:needs-plan:fbca04" "state:plan-no-go:d73a4a" "state:plan-go:0e8a16"; do
    name="${color_pair%:*}"; color="${color_pair##*:}"
    gh label create --force "$name" --color "$color" --repo "$ORG/$REPO"
done
```

### Detailed Steps

1. **Define the vocabulary as a small, mutually-exclusive set**:
   - Three labels is the sweet spot for a plan-review gate: one initial state, one rejection state, one terminal acceptance state.
   - Use the `state:` prefix as a namespace to keep them grouped and to make `gh issue list --label state:*` queries trivial.
   - Pick distinct colors so the GitHub UI also tells the story (yellow=needs-plan, red=plan-no-go, green=plan-go).

2. **Pick the source of truth and commit to it**:
   - The label is authoritative. The comment body is documentation.
   - The implementer must read **only** the label. Never re-parse the comment to "double-check".
   - If you find yourself parsing the comment as a tiebreaker, you have re-introduced the bug — go fix the writer instead.

3. **Make every write a single atomic transition**:
   - `gh issue edit --add-label X --remove-label Y --remove-label Z` is one HTTP call.
   - This is the closest to "atomic" you get with the GitHub API; two-step (remove then add) leaves a window where the issue has zero state labels.
   - Always remove **both** opposing labels even if you believe one is absent — `gh issue edit --remove-label` no-ops cleanly on absence.

4. **Ship a tiny idempotent provisioner so the first write doesn't race**:
   - `gh label create --force <name> --color <hex>` creates-or-updates with one call per label per repo.
   - Run it as a setup step in CI, or as a one-shot script over every org repo.
   - `--force` makes it idempotent: re-running is safe and converges on the desired color/name.

5. **Auto-tag new issues with `state:needs-plan` via an `on: issues: opened` workflow**:
   - Keep the workflow tiny: one job, `permissions: contents: read, issues: write`, calls `gh api -X POST /repos/.../issues/<num>/labels`.
   - **Harden against Actions injection (CWE-94)**: consume only server-controlled integers (`github.event.issue.number`), validate they are numeric before use, and use `gh api` against the labels endpoint instead of building shell commands from event data.
   - Never interpolate `github.event.issue.title` or `body` into a shell string — those are attacker-controlled.

6. **Provide a one-time self-healing backfill**:
   - The migration moment is fragile: existing issues have a comment-form verdict but no label.
   - On startup of each pipeline component, **once per issue**: if no state label is set and the latest plan-review comment parses to GO or NOGO, promote that to a label and return.
   - This is the ONLY place the legacy comment-scan path remains. All steady-state reads use the label.
   - Self-heal converges the org without manual cleanup; you can delete the backfill code in a release or two.

7. **Make the planner and implementer read the same signal**:
   - The infinite-loop class of bug comes from two components disagreeing.
   - Both `has_existing_plan` (planner skip-gate) and `is_plan_review_go` (implementer go-gate) must consult the same label set.
   - If a plan exists but the verdict is `state:plan-no-go`, the planner must **re-plan** (not skip), and the implementer must **defer** (not implement). They agree on the signal, not the action.

8. **Treat `state:plan-go` as terminal and never reversible**:
   - Once GO is applied, the implementer trusts it absolutely. No re-review, no re-parse.
   - If a plan turns out wrong post-GO, the recovery path is a new issue, not a `state:plan-no-go` flip back.
   - This invariant is what unlocks the cheap short-circuit: one label read replaces 100+ comment fetches per loop iteration.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 1 | Comment-text-only gate: `is_plan_review_go` regex-scanned the latest plan-review comment for `Verdict: GO/NOGO` | Comments written before the contract existed (or by an agent that drifted off-format) were unparseable and defaulted to NOGO → permanently blocked. 320 "no parseable Verdict" WARNINGs observed on a single org-wide run. | Text formats drift; structured GitHub primitives don't. Use server-validated labels for state. |
| 2 | Plan-existence-only skip: `has_existing_plan` checked only whether a plan comment existed, not its quality | Issues with a plan + unparseable review were both "already planned" (planner skips) and "not yet approved" (implementer defers) → infinite loop, no party will move it forward. | When two pipeline components share a gate, they must read identical signals. Make the source of truth one thing, not two. |
| 3 | Adding `state:review-in-progress` as an intermediate state to "explain" the limbo | Unnecessary churn: the transient state has no consumer, and any failure mid-review leaves issues stuck in the intermediate. Three terminal/transitional states are sufficient. | YAGNI applies to state machines too. Don't add a state unless a real consumer reads it. |
| 4 | Comment-only verdict with a "second-chance" re-parse on the most recent N comments | Doubled the parse-failure surface area (N comments, any of which might be unparseable). Added log noise without raising the success rate, because the failure was in the writer, not the reader. | Don't paper over a contract violation by widening the parser; fix the writer (or move to structured state). |
| 5 | Storing state in a JSON file inside the repo via PR comments to a state branch | Added a PR per state transition; the rate of state changes was higher than the merge bandwidth → state branch fell behind reality; defeated the cheapness goal. | GitHub already has structured per-issue state — labels. Don't reinvent it as a file. |
| 6 | Building the state-tagging workflow to consume `github.event.issue.title` to derive the label | Opened a GitHub Actions injection vector — attacker-controlled title could break out of the shell command. Even with quoting it's fragile. | Only consume server-controlled integers (`issue.number`); validate numeric before use; call `gh api` against typed endpoints rather than shelling commands built from event data. |
| 7 | Manual provisioning of labels per repo via the web UI | Race: the first reviewer write hits "label does not exist" → 404 → reviewer comment-only fallback → the very bug the labels were meant to fix. | Ship the labels via an idempotent `gh label create --force` CLI; provision before the first write. |
| 8 | Skipping the backfill — "we'll just relabel old issues by hand" | Hand-relabeling 100+ org-wide issues is the kind of toil that never finishes; meanwhile the pipeline burns compute re-planning already-approved work. | A one-time, self-healing backfill is essential for migration. It deletes itself a release or two later. |

## Results & Parameters

### The State Vocabulary (Authoritative Specification)

| Label | Color | Set By | Removed By | Meaning | Implementer Action |
|-------|-------|--------|------------|---------|--------------------|
| `state:needs-plan` | yellow `fbca04` | `on:issues:opened` workflow; reviewer (when re-planning required) | reviewer (on first GO/NOGO) | Planner must produce a plan for this issue | Defer; await plan |
| `state:plan-no-go` | red `d73a4a` | reviewer (per NOGO iteration) | reviewer (on subsequent GO or when re-planning required) | Latest plan was rejected; planner must revise | Defer; await re-plan |
| `state:plan-go` | green `0e8a16` | reviewer (on first GO — TERMINAL) | nobody (terminal) | Plan accepted; safe to implement | **Proceed to implementation** |

**Invariants:**

- At most one `state:*` label may be set on an issue at any time.
- Absence of any `state:*` label is treated identically to `state:needs-plan` (eases migration).
- `state:plan-go` is terminal. The reviewer never flips it back. Post-GO recovery is via a new issue.

### Lifecycle Diagram

```
                     issues:opened
                          │
                          ▼
                  ┌────────────────┐
                  │ state:needs-   │◄────────────────┐
                  │     plan       │                 │
                  └───────┬────────┘                 │ (reviewer
                          │ (planner produces plan,  │  requests
                          │  reviewer evaluates)     │  re-plan)
                          ▼                          │
              ┌───────────┴───────────┐              │
              │                       │              │
              ▼                       ▼              │
       ┌──────────────┐        ┌──────────────┐      │
       │ state:plan-  │◄──────►│ state:plan-  │──────┘
       │     go       │  (no   │   no-go      │
       │ (terminal)   │  back) │              │
       └──────┬───────┘        └──────────────┘
              │
              ▼
        implementer
        proceeds
```

### Backfill Decision Logic (One-Time Self-Heal)

```python
def derive_state_label(issue) -> str | None:
    """Compute the desired state label for an issue.

    Steady-state path: labels are authoritative; return None to indicate
    'no change needed'.

    Migration path: when no state label is set, attempt to promote a
    parseable verdict from the latest plan-review comment.
    """
    existing = [lbl for lbl in issue.labels if lbl.startswith("state:")]
    if existing:
        # Labels are authoritative; never override.
        return None

    # No label set — try backfill from existing comments (one-time fallback).
    verdict = parse_latest_plan_review_comment(issue)  # returns "GO" | "NOGO" | None
    if verdict == "GO":
        return "state:plan-go"
    if verdict == "NOGO":
        return "state:plan-no-go"
    # No parseable comment either → treat as needs-plan.
    return "state:needs-plan"
```

### Reviewer Transition Command (Copy-Pasteable)

```bash
# NOGO this iteration:
gh issue edit "$ISSUE_NUM" \
    --repo "$OWNER/$REPO" \
    --add-label state:plan-no-go \
    --remove-label state:needs-plan \
    --remove-label state:plan-go

# GO (terminal):
gh issue edit "$ISSUE_NUM" \
    --repo "$OWNER/$REPO" \
    --add-label state:plan-go \
    --remove-label state:needs-plan \
    --remove-label state:plan-no-go
```

### Org-Wide Provisioning CLI (Idempotent)

```bash
provision_state_labels() {
    local repo="$1"
    gh label create --force --repo "$repo" \
        state:needs-plan --color fbca04 \
        --description "Planner must produce a plan for this issue"
    gh label create --force --repo "$repo" \
        state:plan-no-go --color d73a4a \
        --description "Latest plan was rejected; planner must revise"
    gh label create --force --repo "$repo" \
        state:plan-go --color 0e8a16 \
        --description "Plan accepted (terminal); safe to implement"
}

# Run across every repo in an org:
gh repo list "$ORG" --limit 200 --json nameWithOwner --jq '.[].nameWithOwner' |
    while read -r repo; do
        provision_state_labels "$repo"
    done
```

### Hardened `on: issues: opened` Workflow (Actions-Injection-Safe)

```yaml
name: state-needs-plan-on-open
on:
  issues:
    types: [opened]

permissions:
  contents: read
  issues: write   # least privilege — labels endpoint only

jobs:
  tag:
    runs-on: ubuntu-latest
    steps:
      - name: Tag new issue with state:needs-plan
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # Only consume the server-controlled integer; never the title or body.
          ISSUE_NUM: ${{ github.event.issue.number }}
          REPO: ${{ github.repository }}
        run: |
          # Validate numeric — defend against any future schema drift.
          case "$ISSUE_NUM" in
              ''|*[!0-9]*) echo "ISSUE_NUM not numeric: $ISSUE_NUM" >&2; exit 1 ;;
          esac
          # Call the typed labels endpoint, not a shell-built command.
          gh api -X POST \
              "/repos/$REPO/issues/$ISSUE_NUM/labels" \
              -f "labels[]=state:needs-plan"
```

### Shared-Gate Read (Planner + Implementer Agree)

```python
def get_plan_state(issue) -> str:
    """Read the canonical state label. Absence = needs-plan."""
    for lbl in issue.labels:
        if lbl == "state:plan-go":
            return "go"
        if lbl == "state:plan-no-go":
            return "no-go"
        if lbl == "state:needs-plan":
            return "needs-plan"
    return "needs-plan"  # absence == needs-plan (eases migration)


# Planner uses this:
def should_plan(issue) -> bool:
    return get_plan_state(issue) in {"needs-plan", "no-go"}

# Implementer uses this — same source, opposite question:
def should_implement(issue) -> bool:
    return get_plan_state(issue) == "go"
```

### Why Labels Beat Comment-Text (Comparison Table)

| Property | Free-Text Comment Gate | `state:*` Label Gate |
|----------|------------------------|----------------------|
| Parse failure mode | Silent default to NOGO → permanent block | Structured: either present or absent |
| Query cost across N issues | N comment fetches + N regex runs per loop | One `--label` filter on the list endpoint |
| Contract drift survival | Format change invalidates every prior approval | Label name change is a one-time rename |
| Atomicity of transition | Two writes (delete prior comment + post new) | One `gh issue edit` with add+remove |
| Race during first write | First reviewer hits 404 if label missing | Provisioner runs first, idempotent |
| Observability | grep through 100k log lines for the verdict | `gh issue list --label state:plan-go` |
| Self-heal of existing issues | Manual relabeling of every legacy issue | One-time backfill on startup |
| GitHub Actions injection surface | Tempting to consume `event.title` | Labels are server-side; no shell interpolation |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectHephaestus | PR #707 — `architecture-github-labels-as-state-vocabulary` end-to-end pattern | 911 automation tests pass locally; ruff + mypy clean; auto-merge SQUASH armed. CI in flight at time of writing — flip `verification` to `verified-ci` once green. [PR link](https://github.com/HomericIntelligence/ProjectHephaestus/pull/707) |
| ProjectHephaestus | Live observation that motivated the pattern | 320 "no parseable Verdict" WARNINGs across an org-wide automation run; multiple re-plans of already-approved issues because the latest comment had drifted from the regex contract |
