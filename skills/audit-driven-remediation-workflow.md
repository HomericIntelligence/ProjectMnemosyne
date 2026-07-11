---
name: audit-driven-remediation-workflow
description: "Canonical end-to-end audit-driven remediation workflow: audit pass → severity classification → batch fix planning → PR generation → verification. Use when: (1) running a strict audit across a repo or ecosystem, (2) reconciling audit-finding issue counts against open issues, (3) generating remediation PRs from audit findings, (4) coordinating audit + fix + verification across multiple repos, (5) deciding fix vs accept/suppress for findings, (6) you added a new producer-side signal and must verify every downstream consumer reads it, (7) after landing a bug-pattern fix, grep sibling modules for the same pattern, (8) before declaring an epic complete, run a strict-audit by an independent reviewer agent."
category: tooling
date: 2026-05-25
version: "1.2.0"
user-invocable: false
verification: verified-local
history: audit-driven-remediation-workflow.history
tags: [merged, audit, remediation, ecosystem-audit, strict-audit, repo-hygiene, downstream-consumer-drift, strict-audit-self-review, producer-consumer-pattern, cross-module-duplication, copy-paste-bugs, test-mask, fixture-contract-violation, post-completion-audit, strict-mode-review-discovers-bug]
---

# Audit-Driven Remediation Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Unified end-to-end workflow covering audit pass → finding triage → batch fix → PR → verification, across code quality, repo hygiene, documentation, implementation alignment, and skills marketplace audits |
| **Outcome** | Merged from 14 source skills; verified-local |
| **Scope** | Code quality, repo hygiene, backward-compat removal, doc corpus remediation, implementation alignment, skills deduplication |

## When to Use

- You have a completed audit report (from `/repo-analyze-strict`, an automated scanner, or a manual review) with categorized findings
- You need to create GitHub tracking issues for systematic implementation of audit findings
- You are reconciling count mismatches (agents, skills, workflows) across documentation files
- You need to detect whether a cleanup issue is already implemented before starting work
- You are removing deprecated backward-compatibility code after a field or API migration
- You are validating implementation code against research/design documentation
- You are running parallel Myrmidon fixer agents against a large document corpus (20+ files)
- You need to grade AI architecture research documents for structural/citation compliance
- A skills marketplace has grown past ~500 files and `/advise` is returning too many near-duplicate results
- You added a new producer-side signal (verdict marker, state flag, dispatch event) — audit MUST trace every downstream consumer and confirm the signal is read, not just emitted.
- After landing a bug-pattern fix in one module — grep every sibling module for the same pattern. Bundle-style swarms that touch related code via copy-paste are especially prone to this missed-copy class of bugs.
- After declaring an epic complete — run `/hephaestus:repo-analyze-strict-full` scoped to the session's deliverables. Independent reviewer agents (separate from the implementing model) catch bugs that the implementers and downstream-consumer-drift section both miss.

## Verified Workflow

### Quick Reference

```bash
# 1. Triage: verify each audit finding before acting
grep -rn "<pattern>" <scope>               # confirm findings exist
find . -name "<claimed-missing-file>"      # verify "missing file" claims

# 2. Check labels before issue creation
gh label list --limit 100

# 3. Extract issue number from URL
issue_url=$(gh issue create ...)
issue_num=$(echo "$issue_url" | grep -oP '\d+$')

# 4. Check if cleanup work is already done
git log main..HEAD --oneline               # check prior commits first

# 5. Count on-disk entities for reconciliation
ls .claude/agents/*.md | wc -l
ls skills/*.md | wc -l

# 6. Push one branch at a time (HomericIntelligence limit: 2 refs per push)
git push -u origin branch-1
git push -u origin branch-2

# 7. Enable auto-merge
gh pr merge --auto --rebase <pr-number>
```

### Phase 1 — Triage Audit Findings

**Before writing any code**, categorize each finding:

| Category | Action | Example |
| ---------- | -------- | --------- |
| Quick fix (<5 lines, no design ambiguity) | Fix directly in same PR | Duplicate hook, stale count, missing `.gitignore` entry |
| Pragmatic improvement | Include if safe | Add CI warning annotation instead of removing `continue-on-error` |
| Verify first | Check before acting | "Missing file X" — run `find` before creating it |
| Needs separate PR | Defer with note | 4,000-line script decomposition |
| External blocker | Document only | Mojo compiler limitation |
| Admin setting | Not a code change | Branch protection rule |

**Always verify before implementing.** Audits report false positives:
- "Missing file X" — run `find` or `ls` first
- "Stale count" — count with `ls *.md | wc -l`
- "Unused dependency" — grep for actual usage before removing
- "Silent except" — confirm `grep -n "except.*:" file.py | grep "pass$"`

**Triage decision for issue vs. direct fix**:
- Change is < 5 lines AND no design ambiguity → fix directly in same PR
- Change requires thought/review/architecture → file issue only

### Phase 2 — Create GitHub Tracking Issues

**Check existing labels first:**
```bash
gh label list --limit 100
```
Using non-existent labels causes `gh issue create` to fail. Common missing labels: `tooling`, `tech-debt`, `epic`.

**Check existing infrastructure** before planning:
```bash
grep -A 5 "mypy" .pre-commit-config.yaml
ls -la .env.example CONTRIBUTING.md
grep -A 10 "\[tool.pytest" pyproject.toml
```

**Create first 2–3 issues manually** to verify labels work before batch creation.

**Issue template structure**:
```markdown
## Objective
Brief description (2-3 sentences)

## Deliverables
- [ ] Deliverable 1

## Success Criteria
- Criterion 1

## Priority
HIGH/MEDIUM/LOW — Impact description

## Estimated Effort
X hours

## Verification
```bash
# Commands to verify fix
```

## Context
From [Audit Name] (#ISSUE-NUMBER)
```

**Create tracking/epic issue before batch-creating remaining issues**:
```bash
gh issue create \
  --title "[TRACKING] Audit Remediation: N Issues Across X Phases" \
  --label "epic,tech-debt" \
  --body "$(cat <<'EOF'
## Overview
Brief description

## Phase 1: [Name] (~Xh, Y issues)
- [ ] #400 - Description (effort)
EOF
)"
```

**Batch create remaining issues via script** (sequential, not parallel):
```bash
cat > /tmp/create_issues.sh <<'SCRIPT'
#!/bin/bash
set -e
gh issue create --title "[P1] Full issue title" --label "P1,documentation" \
  --body "$(cat <<'EOF'
## Objective ...
## Deliverables
- [ ] Task 1
EOF
)"
SCRIPT
chmod +x /tmp/create_issues.sh && /tmp/create_issues.sh
```

### Phase 3 — Implement Fixes

**Only implement mechanical fixes in the audit PR**:
```bash
# Update coverage threshold
sed -i 's/fail_under = 70/fail_under = 80/' pyproject.toml
# Remove backup files
find . -name "*.orig" -type f -delete && echo "*.orig" >> .gitignore
```

**Do NOT implement**: complex refactoring, architectural changes, or anything requiring design decisions. Defer those to tracked issues.

**Handle `continue-on-error` pragmatically** — don't just remove it. Semgrep returns non-zero on findings; removing `continue-on-error` breaks SARIF upload. Better: add a warning annotation step downstream.

**For repo hygiene (Pydantic, exception logging)**:
- Replace `to_dict()` with `model_dump()` ONLY when fields map 1:1 (no `Path→str`, `Enum→value`, computed properties, or nested calls)
- Replace silent `except` blocks: use `logger.debug()` for expected fallbacks, `logger.warning()` for unexpected swallowed exceptions

**Docstring false positive** — restructure to remove visual ambiguity:
```python
# BEFORE (line N+1 looks like a fragment to linters)
"""This module provides the Foo class that does X across multiple Y."""

# AFTER (relative clause makes completeness clear)
"""This module provides the Foo class, which does X across multiple Y."""
```

### Phase 4 — Backward-Compatibility Removal

When removing deprecated fields/APIs after a completed migration:

1. **Search exhaustively before removing**:
   ```bash
   grep -rn 'data.get("old_field"' src/
   grep -rn 'old_field.*backward' tests/
   ```

2. **Document all locations** with file:line references before any edit

3. **Remove compatibility shim, preserve new logic**:
   ```python
   # BEFORE
   is_valid = data.get("is_valid", True) is not False
   if data.get("fallback", False) is True:
       is_valid = False
   # AFTER
   is_valid = data.get("is_valid", True) is not False
   ```

4. **Delete tests that ONLY exercised the deprecated path** (not tests that verify new field behavior)

5. **Rename misleading tests** that use the new field but reference the old field name in their function name

6. **Separate PRs**: documentation cleanup (low-risk) vs. code refactoring (needs test verification)

### Phase 5 — Implementation Alignment Validation

When audit reveals doc-implementation drift:

1. **Gather documentation sources**: `docs/research.md`, `docs/design/*.md`, `CLAUDE.md`, `config/**/*.yaml`

2. **Build alignment matrix**:

   | Location | Docs | Implementation | Status |
   | ---------- | ------ | ---------------- | -------- |
   | `file.py:line` | Documented behavior | Actual behavior | aligned/partial/missing |

3. **Prioritize**: Critical (wrong formula/algorithm) → Important (missing feature) → Minor (cosmetic)

4. **Fix with tests first** (TDD): write test → run (should fail) → fix → run (should pass) → full suite

5. **If implementation differs from docs intentionally**: update docs and add rationale

### Phase 6 — Count Reconciliation

When audit finds count mismatches in docs:

```bash
# Count actual on-disk files
ls .claude/agents/*.md | wc -l         # use *.md, not bare ls (excludes dirs)
ls skills/*.md | wc -l

# Find all count claims in docs
grep -rn "42 agents\|37 agents" CLAUDE.md agents/ docs/

# Verify listed entities exist
grep '`.*\.md`' agents/README.md | sed "s/.*\`\(.*\)\.md\`.*/\1/" > /tmp/readme_agents.txt
while read name; do
  [ ! -f ".claude/agents/$name.md" ] && echo "MISSING: $name"
done < /tmp/readme_agents.txt
```

Update ALL docs that claim counts — not just CLAUDE.md. Key files: `CLAUDE.md`, `agents/README.md`, `agents/hierarchy.md`, `docs/dev/skills-architecture.md`.

### Phase 7 — Pre-Work Cleanup Issue Detection

Before implementing any cleanup issue, check if work is already done:

```bash
# Step 1: Check if already implemented in worktree
git log main..HEAD --oneline

# Step 2: Check remote state
git fetch origin $(git branch --show-current)
git log --oneline origin/$(git branch --show-current) -5

# Step 3: Check for existing PR
gh pr list --head $(git branch --show-current)
```

If a PR exists with auto-merge enabled, no further action is needed. Issue line numbers in the issue description are approximate — search by pattern, not line number.

### Phase 8 — Skills Marketplace Deduplication

When marketplace has grown past ~500 files:

```bash
# Cluster by filename prefix (group by first 3 tokens)
ls skills/*.md | sed 's|skills/||;s|\.md||' | \
  python3 -c "
import sys, collections
names = [l.strip() for l in sys.stdin]
clusters = collections.defaultdict(list)
for n in names:
    parts = n.split('-')
    key = '-'.join(parts[:3])
    clusters[key].append(n)
for k, v in sorted(clusters.items(), key=lambda x: -len(x[1])):
    if len(v) > 1:
        print(f'{len(v):3d}  {k}')
        for name in v[:6]:
            print(f'       {name}')
" | head -80

# Test gate — run after every phase
python3 -m pytest tests/ -q --tb=short
python3 scripts/validate_plugins.py
```

**Triage tiers**:
| Tier | Criteria | Action |
| ------ | ---------- | -------- |
| Near-exact | Same workflow, <5% unique content | Delete one immediately |
| High-overlap | Same topic, 20-40% unique content each | Merge unique content, delete absorbed |
| Topic cluster | Related angles, 3+ files | Consolidate into 1-2 canonical files |
| Distinct | Different use cases or audiences | Keep separate |

**Cross-category prefix matches**: weight as `false-match-likely` by default. Require ≥2 strong signals (shared tags ≥2, heading-overlap ≥0.75, or explicit `cross_refs`) before treating as merge candidates.

**Stop rule**: when a continuation pass yields <15% actionable clusters, the corpus is at its de-duplication floor.

### Phase 9 — Document Corpus Parallel Remediation (Myrmidon)

For large document corpora (20+ files, multiple repair classes):

1. **Pre-flight grep** — enumerate ALL defects before launching any agent:
   ```bash
   grep -rn "Critical correction\|corrected from\|previously stated\|Changelog\|Revision history" corpus/*.md
   ```

2. **Conflict partitioning**: classify every file as WATCH (appears in 2+ repair classes) or GO (appears in exactly 1 class). Assign each file to exactly ONE agent. Zero collision risk.

3. **Wave A** — parallel fixer agents (`isolation: "worktree"`, `subagent_type: general-purpose`):
   | Agent | Repair Class |
   | ------- | ------------- |
   | R1 | Arithmetic / numeric corrections |
   | R2 | Terminology normalization |
   | R3 | Structural insertions |
   | R4 | Citation format |
   | R5 | Inline correction-marker stripping |
   | R6 | Corpus-wide scrub (change-note prose) |

   Required constraint in every fixer prompt: "No change-logging of the fix itself. Do NOT add 'updated per remediation' or any meta-commentary."

4. **Wave B** — read-only verifier (`subagent_type: Explore`): re-runs audit rubric + residual grep. Must confirm ALL passes return zero matches.

5. **Wave C** — merge: use narrow `git diff HEAD~N HEAD -- <owned-files>` + `git apply --3way`. Run conflict-marker gate after every apply: `grep -rnE "^<<<<<<<" <files>`.

6. **Mandatory Wave A post-completion verification** — check whether each agent committed to main or worktree:
   ```bash
   AGENT_COMMIT=$(git -C "$WORKTREE" rev-parse HEAD)
   git merge-base --is-ancestor "$AGENT_COMMIT" main && echo "already on main — skip patch"
   ```

### Phase 10 — Verify and Create PR

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Review diff
git diff

# Commit
git add <specific-files>
git commit -m "fix(audit): implement audit findings from #<issue>

Implements HIGH priority fixes:
1. Created N GitHub tracking issues (#X-Y)
2. [Each direct fix]

Refs #<tracking-issue>"

git push -u origin <branch>
gh pr create \
  --title "fix(audit): implement audit findings" \
  --body "Refs #<tracking-issue>

## Not Implemented (Deferred)
- [Finding] — [reason for deferral]

## Test plan
- [x] Pre-commit hooks pass locally
- [ ] CI workflows pass"
gh pr merge --auto --rebase
```

## Downstream-Consumer Drift Audit (added v1.1.0)

When an audit-driven remediation introduces a new producer-side signal (a marker in a comment, a state field, a dispatched event), the remediation is INCOMPLETE until every downstream consumer is verified to read the signal correctly. Producer-side unit tests pass without proving the signal is honored. This is the most common gap a strict audit catches.

### Detection workflow

1. Identify the signal: marker constant, state enum value, event topic, etc.
2. Grep for the signal's contract:
   ```bash
   # If signal is a string marker:
   grep -rn '<marker-substring>' --include='*.py' --include='*.sh' --include='*.ts'
   # If signal is a state field:
   grep -rn 'state\.<field>' --include='*.py'
   # If signal is an event topic:
   grep -rn 'subscribe.*<topic>\|listen.*<topic>' --include='*.py'
   ```
3. For each match outside the producer module, verify the consumer reads + acts on the signal — not just receives it.
4. Add at least one integration test that exercises the producer → consumer flow end-to-end (not mocked at the consumer boundary).

### Real example (2026-05-25)

Producer: `plan_reviewer.py` posts `**Verdict: APPROVED**` markers in GitHub issue comments. Skip-gate `_latest_review_is_final` works correctly in isolation.

Consumer: `implementer.py:583` calls `_has_plan(issue_number)` which only checks for substring `"Implementation Plan"`. It NEVER scans for the verdict marker. A `**Verdict: BLOCK**` plan would still be implemented.

Test coverage gap: 530 automation unit tests pass. None exercise the producer → consumer flow. The bug shipped through self-review.

Strict audit caught this in <10 minutes by reading both files in parallel via `pc-research-reviewer` agents. Cost of the audit: trivial. Cost of the bug landing on main: blocked plans implemented automatically.

See [[debugging-silent-pipeline-stage-via-argparse-required-grep]] for the related "silent-pipeline-stage" pattern when the consumer is silent due to argparse-time failures rather than missing logic.

## Cross-Module Duplication Audit (added v1.2.0)

When an audit-driven remediation fixes a bug pattern in one module, the same pattern is often duplicated in sibling modules — particularly when the original codebase was created by parallel agents in a swarm that copy-pasted helper logic. Fixing only the originally-reported file leaves the duplicates live.

The 2026-05-25 session demonstrated this cleanly: PR #575 fixed `get_repo_slug(...).split("/", 1)` in `plan_reviewer.py:295-296` and closed #574. The IDENTICAL pattern in `review_state.py:87-88` (a sibling module created by Bundle B's #573 in the same swarm) survived untouched. The test fixture for the sibling masked the bug by patching `get_repo_slug` to return a slash-bearing string. The implementer's APPROVED-gate check on the production hot path crashed every issue. Phase 3 of the automation loop was silently broken despite both epics #550 and #576 being CLOSED.

### Detection workflow

1. Identify the buggy pattern: API call, regex, control-flow shape, or string-manipulation chain. Reduce it to a greppable signature.
2. Run the signature-grep across the WHOLE codebase, not just the originally-reported file:
   ```bash
   # If the buggy pattern is "get_repo_slug(...).split('/', 1)":
   grep -rn 'get_repo_slug.*\.split\|get_repo_slug(' --include='*.py'
   # If the buggy pattern is "result = future.result(); future.cancel()":
   grep -rn 'future\.result.*\n.*future\.cancel' --include='*.py'
   ```
3. For each match outside the originally-reported file, classify: same bug, different-but-related bug, or unrelated coincidence. Fix the same-bug instances in the SAME PR (or file as immediate-followup CRITICAL issues if scope blows up).
4. **Audit the test fixtures of sibling files**: a fixture that returns a value satisfying the buggy pattern's expectations (e.g. mocking `get_repo_slug` to return `"owner/name"` instead of `"AchaeanFleet"`) silently masks the production crash. The mock must satisfy the documented CONTRACT of the function, not the buggy code's incidental expectations.

### Real example (2026-05-25, ProjectHephaestus session)

- **Originating fix**: PR #575 fixed `plan_reviewer.py:295-296` (`get_repo_slug → split → unpack` crash). Test added at `test_plan_reviewer.py:test_uses_owner_repo_tuple_from_get_repo_info`. Closed #574.
- **Missed copy**: `review_state.py:87-88` had the identical pattern. The module was created by Bundle B (PR #573) in the same swarm as Bundle A (which created the original buggy `plan_reviewer.py` change in PR #571). Both copies share parentage in the swarm-coordinated effort.
- **Test mask**: `test_review_state.py:160-163` patched `get_repo_slug` to return `"owner/name"` — a slash-containing string that split correctly. The fixture violated the documented contract of `get_repo_slug` (returns short name, no slash). Production crashed; tests passed.
- **Detection**: caught by a `/hephaestus:repo-analyze-strict-full` strict-mode review of the session's deliverables, AFTER the epics were closed. The reviewer traced the call path from `implementer.py:629` (the APPROVED-gate check) outward, not by re-reading the supposedly-fixed `plan_reviewer.py`.
- **Fix**: PR #589 applied the identical `get_repo_info` replacement to `review_state.py:87-91` + corrected the test mock + added a regression test. Closed #588.

## Post-Completion Strict Audit (added v1.2.0)

The audit-driven remediation workflow is INCOMPLETE without a post-merge strict review run by an independent reviewer agent. The implementing model self-anchors on the modules it touched and misses bugs in unmodified-but-related call sites. The 2026-05-25 session had ~12 swarm agents land 12 PRs across 2 epics — none of them caught the `review_state.py` copy until a separate `pc-research-reviewer` agent traced the call path post-merge.

### Mandatory final step

After ALL swarm PRs in an audit-driven remediation epic have landed and the epic is about to be closed:

1. Dispatch `/hephaestus:repo-analyze-strict-full` scoped to the session's deliverables (the diff across all the merged PRs).
2. Use independent reviewer agents (e.g. `pc-research-reviewer`) — NOT the implementing agents.
3. Each reviewer must trace at least one call path that EXERCISES the changed code in production, not just the changed module itself.
4. If a CRITICAL finding emerges, file a follow-up issue + PR before declaring the epic complete.
5. Update the audit-driven-remediation workflow itself (this skill) with the lesson if a new failure mode is discovered.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Using `--json` flag with `gh issue create` | `issue_num=$(gh issue create ... --json number)` | `--json` flag not available in all gh CLI versions | Extract issue number from URL: `echo "$url" \| grep -oP '\d+$'` |
| Assuming all audit findings need implementation | Created tasks for items already implemented | Many items were already done | Check existing infrastructure FIRST before planning |
| Parallel issue creation with unknown labels | Created all issues in parallel with label `tooling` | Label didn't exist; all parallel siblings failed | Always validate labels with `gh label list` first; use sequential shell script for batch ops |
| Trusting CLAUDE.md count as ground truth | Used "42 agents" from CLAUDE.md | CLAUDE.md had 42, hierarchy had 37, disk had 31 — all wrong | Always count with `ls *.md \| wc -l` from disk first |
| Counting `ls .claude/agents/` bare | `ls` of directory includes `templates/` subdirectory | Returns N+1 (dir counted) | Use `ls .claude/agents/*.md` to get only .md files |
| Fix only one doc for count reconciliation | Updated CLAUDE.md count but not hierarchy.md or README.md | Three docs still disagreed | Search ALL docs for count claims before committing |
| Searching worktree for already-removed code | Grepped worktree for a NOTE marker that was already cleaned up | Worktree had the fix; grep returned no results | Check `git log main..HEAD` FIRST — searching for removed code in a fixed worktree gives false "not found" |
| Pushing all branches at once | `git push -u origin branch1 branch2 branch3` | Remote rejected: "Pushes can not update more than 2 branches or tags" | Push HomericIntelligence branches one at a time |
| Adding `# noqa: BLE001` without checking ruff select | Added noqa comment to suppress BLE001 | `BLE` not in ruff select list — comment adds noise; ruff warns about unused ignores | Check `pyproject.toml` select list before adding noqa comments |
| First commit without staging pixi.lock | `git add pyproject.toml && git commit` after pip-audit ran | pip-audit hook stash conflict: hook modifies pixi.lock mid-run; unstaged lock causes stash conflict | Stage `pixi.lock` before committing whenever pip-audit has already run |
| Migrating all to_dict() to model_dump() | Planned to replace 11 methods | 10/11 have Path→str, Enum→value, computed props, or nested calls — model_dump() would produce wrong output | Only migrate when fields map 1:1 to output with no transforms |
| Remove Semgrep continue-on-error outright | Deleted `continue-on-error: true` from security.yml | Breaks SARIF upload — Semgrep exits non-zero when it finds issues | Add warning annotations downstream instead of removing safety mechanisms |
| No triage step before merging skills | Started merging skills immediately without classifying pairs | Wasted time on pairs that turned out to be truly distinct | Always build full triage table first; 30 min of analysis saves hours of rework |
| Removing a field before searching all consumers | Removed field from dataclass first, then ran tests | `AttributeError` in builder.py that still referenced the removed field | Always `grep -r "field_name"` across the entire repo before removing any field |
| Fixer agents with background=true for long corpus passes | Launched corpus fixer agents with `run_in_background=true` | Stream idle timeout ~28 min; connection dropped at ~2M tokens | Use foreground agents for long-running tasks; split large batches into smaller foreground agents |
| Skipping pre-flight grep before launching Wave A agents | Launched fixers without first enumerating all defects | Two agents assigned overlapping files; merge produced conflicts | Always complete pre-flight grep and WATCH/GO partitioning before launching any fixer |
| Annotating change-notes instead of deleting them | Added `<!-- removed per audit -->` comments | Annotation preserves change-history narrative in a different form | Unpublished corpora require hard deletion — no annotation, no changelog, no comment |
| `git apply --3way` assumed safe when it exits 0 | Staged files after `git apply --3way` without checking markers | `--3way` exits 0 even when it writes conflict markers; committed broken markdown | After every `git apply --3way`, run `grep -rnE "^<<<<<<<" <files>` as gate before staging |
| `git commit --amend` without HEAD verification | Ran `--amend` after HEAD had already advanced past target commit | Modified the wrong commit | Before `--amend`, verify HEAD: `git log -1 --pretty=%s` |
| R6 scrub as a standalone agent after WATCH-file agents | Ran corpus-wide scrub as a 7th agent | WATCH-file agents had already opened those files; R6 re-opened unnecessarily | Fold R6 patterns into WATCH-file agent prompts |
| Cross-category prefix2 matches treated as merge candidates | Queued 21 cross-category prefix pairs as merge candidates | 86% were false-match (same prefix, mutually exclusive phases or deliverables) | Require ≥2 strong signals before flagging cross-category prefix matches as merge candidates |
| Single-pass scrub declared corpus clean | One grep pass returned zero matches; declared done | Subsequent passes surfaced bibliography-suffix and semantic-judgment residue | Run multiple scrub passes with expanding pattern lists; "clean under current gate" ≠ "globally clean" |
| Explore agents for fingerprinting waves | Used `subagent_type: Explore` for fingerprinting shards | Explore agents are read-only — cannot call Write tool | Any wave whose output must persist to a file MUST use `general-purpose` or another writable agent type |
| Oversized fingerprinting shards | Used 332-file shards for Wave 1 | Agents hit output limits; 81.8% coverage with silent gaps | Limit fingerprinting shards to ≤103 files; cross-check surviving files vs fingerprinted set after Wave 1 |
| Fixer agents downgrade canonical versions | Dispatched fixer agents to fix content-deficit clusters | Agents rewrote canonical files from scratch, reverting to older versions | Fixer agents must be given explicit version floor constraints; provide pre-fixer commit SHA for recovery |
| Trust the implementer's self-review of "all tests pass" without dispatching a strict audit | Implementer (me) reported `pixi run pytest tests/unit: 2362 passed; ruff clean; manual smoke OK` and treated the work as done. Did NOT dispatch a strict review. | A reviewer agent (`pc-research-reviewer`) scoped to the diff caught 13 findings including 3 CRITICALs. Self-review by the implementing model under-weights "did I solve the user's actual intent" vs "did the code I wrote pass its own tests" | Always run `repo-analyze-strict-full` (or equivalent) scoped to the diff before claiming work is complete. Dispatch as a separate sub-agent — the implementing agent has cognitive bias toward justifying its own choices. |
| Add a producer-side signal (`**Verdict: APPROVED**` marker in plan-reviewer) and verify only the producer's tests pass | Plan-reviewer's `_latest_review_is_final` gate was tested in isolation. 10 new unit tests, all green. PR opened. | The implementer.py phase that runs AFTER plan-reviewer never read the verdict. `_has_plan(issue_number)` only checks for substring `"Implementation Plan"`. A BLOCK plan got implemented. The user's stated workflow was silently broken. | When adding a producer-side signal, grep for EVERY downstream consumer and add an integration test that exercises the full pipeline. Use `grep -rn "<consumer-marker-pattern>" --include='*.py'` to find them. |
| Fix the bug only in the originally-reported file | PR #575 replaced `get_repo_slug(...).split("/", 1)` with `get_repo_info(get_repo_root())` in `plan_reviewer.py:295-296`. Closed #574. | An identical bug pattern in `review_state.py:87-88` (a sibling module created by Bundle B in the same swarm) was not touched. Production crashed on every implementer gate check. The session declared both epics CLOSED while the user's stated workflow was silently broken. | When fixing a bug pattern, grep the WHOLE codebase for the same signature — especially in modules created by sibling agents in the same swarm. The originating fix is necessary but not sufficient. |
| Trust that the swarm's own tests verify end-to-end correctness | The Part 2 swarm ran 5 sub-agent PRs; each agent independently asserted `pixi run pytest tests/unit -q -x` passed. Both epics were marked complete after 2362+ passing tests across all PRs. | The test for `review_state.py` patched `get_repo_slug` to return `"owner/name"` (slash-bearing, splits cleanly) — a contract violation that masked the production crash. Per-PR test passes do not establish system-level correctness when fixtures lie. | Test fixtures must satisfy the documented CONTRACT of the function they mock, not the buggy code's incidental expectations. Audit fixtures for "did this mock return a realistic value?" as part of every PR review. |

## Results & Parameters

### Triage Decision Matrix

```yaml
# Include in batch PR if ALL true:
include_criteria:
  - change_is_under_20_lines: true
  - no_behavior_change_risk: true
  - independently_reversible: true
  - pre_commit_hooks_validate: true

# Defer to separate PR if ANY true:
defer_criteria:
  - requires_large_refactor: true
  - blocked_by_external_tool: true
  - requires_admin_settings: true
  - needs_stakeholder_input: true
```

### Issue Creation Timing Reference

| Activity | Time |
| ---------- | ------ |
| Label validation | 2 min |
| Manual issue creation (first 3) | 5 min |
| Tracking issue creation | 3 min |
| Script generation + execution (~24 issues) | 23 min |
| Verification | 5 min |

### PR Template for Audit Fixes

```markdown
## Summary
- **Fix 1**: [What changed] ([audit section reference])
- **Fix 2**: [What changed] ([audit section reference])

## Not Implemented (Deferred)
- [Finding] — [reason for deferral]

## Test plan
- [x] Pre-commit hooks pass locally
- [ ] CI workflows pass on this PR
```

### Cleanup Issue Detection Commands

```bash
git log main..HEAD --oneline
git fetch origin $(git branch --show-current)
git log --oneline origin/$(git branch --show-current) -5
gh pr list --head $(git branch --show-current)
```

### Exception Logging Level Guide

| Level | When |
| ------- | ------ |
| `logger.debug()` | Expected fallback (disk read failed, version detection, timezone parse) |
| `logger.warning()` | Unexpected swallowed exception that might indicate a bug |
| `logger.error()` | Should not be silently caught; consider re-raising |

### Skills Marketplace CI Check Names

| Check | Command | Threshold |
| ------- | --------- | ----------- |
| Validate Plugins | `python3 scripts/validate_plugins.py` | Must pass (0 errors) |
| Test suite | `python3 -m pytest tests/ -q --tb=short` | All tests green |

### Corpus Scrub — Minimum Pattern List (8 passes)

Run all eight passes after each wave; ALL must return zero before declaring clean.

```bash
# Pass 1: literal-phrase (change-note prose)
grep -rnE "Critical correction|corrected from|previously stated|\[corrected:|CORRECTED:|Changelog|Revision history|Change notes" corpus/*.md

# Pass 2: bibliography-suffix (trailing tokens on citation lines)
grep -rnE "\bADDED\b|ADDED —|missing from original|not cited in original|critical addition\.|added during merge\." corpus/*.md

# Pass 3: semantic-judgment (editorial commentary)
grep -rnEi "understated in the original|material gap|absence from original|— WRONG;|\[Original doc:" corpus/*.md

# Pass 4: authorial-review parentheticals
grep -rnEi "per review|after additions|after review|during review|\(qualified per |\(revised per " corpus/*.md

# Pass 5: frontmatter process-metadata (anchored at line start)
grep -rnE "^## (Status|Merged|Sources):|^## Date:.*\(merged\)" corpus/*.md

# Pass 6: support-doc changelog sections (full corpus scope)
grep -rnE "^## (Changelog|Corrections Applied|Revision history|Change notes)" corpus/*.md support_docs/*.md

# Pass 7: citation verification — dispatch parallel agents to WebFetch each cited arXiv abstract
# Pass 8: arithmetic cross-check — re-derive canonical numbers from prelude formulas
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectScylla | Post-audit hygiene sprint 2026-03-13 — 3 PRs, 1548 tests passing | repo-hygiene-audit-implementation source |
| ProjectScylla | Backward-compat removal 2026-02-13 — 135 lines removed, 65 tests passing | backward-compat-removal source |
| ProjectScylla | Implementation alignment 2026-06-27 — 14 items aligned, 5 gaps fixed, 892 tests passing | implementation-alignment-validation source |
| ProjectOdyssey | Count reconciliation 2026-03-07 — 42→31 agents, 82→58 skills corrected | repo-audit-count-reconciliation source |
| Mnemosyne | Quality audit workflow 2026-03-29 — 24 issues created, HIGH fixes implemented | quality-audit-workflow source |
| Mnemosyne | Strict audit + doc remediation 2026-03-22 — B+ (87%) score | documentation-strict-audit-remediation-workflow source |
| ArchIdeas corpus | 39-file research corpus parallel remediation, 6 repair classes, Apr 2026 | documentation-corpus-myrmidon-parallel-remediation source |
| ArchIdeas corpus | 6-dimension quality rubric applied to 39 documents; all passed after remediation | documentation-architecture-research-quality-rubric source |

## References

- History: [audit-driven-remediation-workflow.history](audit-driven-remediation-workflow.history)
- Kept as concrete worked examples: `audit-driven-remediation`, `ecosystem-audit-remediation`, `multi-domain-audit-remediation`, `repo-audit-triage-fix-and-issue-workflow`, `code-quality-audit-principles`, `architect-review-implementation`
- Refs #1777
