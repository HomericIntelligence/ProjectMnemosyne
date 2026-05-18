---
name: github-bulk-issue-and-pr-operations
description: "Canonical guide to bulk GitHub issue and PR operations via gh CLI / gh api / GraphQL: rate-limit recovery, batch-create/close/comment, parallel PR remediation waves, mass label edits, idempotent filing with duplicate detection. Use when: (1) creating or closing 20+ issues/PRs in one operation, (2) recovering from primary or secondary rate limits, (3) coordinating parallel-fix swarms via gh CLI, (4) GraphQL bulk operations that span multiple repos, (5) auto-merge / admin-merge mechanics for batches."
category: tooling
date: 2026-05-18
version: "1.0.0"
user-invocable: false
verification: verified-local
history: github-bulk-issue-and-pr-operations.history
tags: [merged, gh-cli, github-api, bulk, graphql, rate-limit, parallel-pr]
---

# GitHub Bulk Issue and PR Operations

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-05-18 |
| **Objective** | Canonical reference for all bulk GitHub operations: issue filing, closure, deduplication, PR auto-merge, rate-limit recovery, comment deduplication, and GraphQL patterns |
| **Outcome** | Consolidated from 33 skills (M6 merge, Epic #1782). Verified patterns across HomericIntelligence ecosystem swarms. |
| **Verification** | verified-local |
| **History** | [changelog](./github-bulk-issue-and-pr-operations.history) |

## When to Use

- Creating or closing 20+ issues or PRs in a single session
- Recovering from GitHub primary rate limits (`Limit reached … resets N:XXpm`) or secondary rate limits (403 BCE2 / `GraphQL: API rate limit already exceeded`)
- Coordinating parallel fix-swarm waves using `gh` CLI with worktree-isolated agents
- Performing GraphQL bulk operations (label edits, issue edits, PR status) across multiple repos
- Arming auto-merge on PRs in HomericIntelligence repos (`--squash` required — rebase disabled org-wide)
- Filing 200+ issues across 10+ repos idempotently without duplicates
- Deduplicating issue backlogs (terminology migrations, stale trackers)
- Implementing wave-based issue triage: ALREADY-DONE detection, DUPLICATE closure, EASY/MEDIUM/HARD classification

## Verified Workflow

### Quick Reference

```bash
# ── Auto-merge (HomericIntelligence org: always --squash) ──────────────────
gh pr merge "$PR" --auto --squash --repo "HomericIntelligence/$REPO"

# ── Portable fallback (non-HI repos) ──────────────────────────────────────
out=$(gh pr merge "$PR" --auto --rebase 2>&1) || true
if echo "$out" | grep -q "rebase merging is not allowed"; then
  gh pr merge "$PR" --auto --squash
fi

# ── Unset shadowed token BEFORE every gh/git-push call ────────────────────
unset GITHUB_TOKEN GH_TOKEN && gh pr create --repo "$ORG/$REPO" ...
unset GITHUB_TOKEN GH_TOKEN && git push -u origin "$BRANCH"

# ── Rate-limit org probe (before dispatching any batch) ────────────────────
TEST=$(gh api repos/$ORG/$REPO/issues --method POST \
  -f title="[TEST] probe" -f body="probe" 2>&1)
echo "$TEST" | grep -q '"number"' && echo CLEAR || echo BLOCKED
# Close the test issue immediately if CLEAR:
NUM=$(echo "$TEST" | python3 -c "import sys,json;print(json.load(sys.stdin)['number'])")
gh issue close "$NUM" --repo "$ORG/$REPO" --reason "not planned"

# ── File issue with body-file (avoids heredoc quoting failures) ────────────
echo "$BODY" > /tmp/issue_body.txt
gh issue create --repo "$ORG/$REPO" \
  --title "$TITLE" --label "$LABEL" --body-file /tmp/issue_body.txt
sleep 3   # between issues; sleep 60 + retry on 403

# ── Count issues without pagination truncation ────────────────────────────
gh issue list --repo "$REPO" --label "$LABEL" \
  --state open --json number --limit 200 --jq 'length'

# ── Find exact-title duplicates ───────────────────────────────────────────
gh issue list --repo "$REPO" --label "$LABEL" \
  --state open --json number,title --limit 200 \
  --jq 'group_by(.title)|map(select(length>1))|.[]|
        "DUPE: #\([.[].number|tostring]|join(", #")) — \(.[0].title)"'

# ── Close duplicate (keep lower-numbered) ────────────────────────────────
gh issue close $DUPE --repo "$REPO" --reason "not planned" \
  --comment "Duplicate of #$CANONICAL — closing"

# ── Bulk-close already-resolved issues ────────────────────────────────────
for N in 101 102 103; do
  gh issue close $N --comment "Already resolved — verified in codebase."
done

# ── ALREADY-DONE grep (exclude worktrees) ────────────────────────────────
grep -rn "pattern" /path/to/repo/ \
  --include="*.py" --include="*.toml" \
  --exclude-dir=".git" --exclude-dir=".worktrees" \
  --exclude-dir=".issue_implementer" --exclude-dir=".claude"

# ── Verify PR numbers after each wave ────────────────────────────────────
gh pr list --author "@me" --state all --limit 50

# ── Correct closing keyword format for bundle PRs ─────────────────────────
# WRONG: "Closes #A, #B, #C"  (only closes #A)
# RIGHT: "Closes #A. Closes #B. Closes #C."  (closes all three)

# ── Edit issue body safely (no heredoc-in-$() quoting failures) ──────────
TMPFILE=$(mktemp /tmp/issue-XXXXXX.md)
cat > "$TMPFILE" << 'HEREDOC'
<new body>
HEREDOC
gh issue edit $N --repo "$ORG/$REPO" --body "$(cat $TMPFILE)"
rm "$TMPFILE"
```

### Phase 0: Pre-flight Checks (Required Before Any Swarm)

Run once before dispatching any batch of agents:

```bash
# 1. Check auto-merge capability
gh repo view --json autoMergeAllowed --jq '.autoMergeAllowed'

# 2. Check for existing open PRs (prior swarm may have already created them)
gh pr list --state open --json number,title,headRefName,mergeStateStatus

# 3. Check pre-commit config exists
ls .pre-commit-config.yaml 2>/dev/null || echo "ABSENT — remove pre-commit steps from agent prompts"

# 4. Check lockfile type
ls package-lock.json 2>/dev/null && echo "use npm ci" || echo "use npm install"
ls pixi.lock 2>/dev/null && echo "pixi.lock present"

# 5. Org API limit probe (see Quick Reference)

# 6. Verify L0 is on main before dispatching worktree agents
git branch --show-current  # Must be 'main'
```

### Phase 1: Issue Classification

Fetch all open issues, then apply these pre-filters **in order** (each earlier filter reduces noise for the next):

1. **DUPLICATE** — Same target file + similar description as another open issue → `gh issue close N --comment "Duplicate of #M"`
2. **ALREADY-DONE** — Change already in codebase (grep with worktree exclusion) → close with verification comment
3. **EASY** — Single-file, mechanical, < 20 lines, no logic change
4. **MEDIUM/HARD** — Defer

```bash
# Fetch for classification
gh issue list --state open --limit 200 --json number,title,labels,body

# EASY signals: "Update", "Fix typo", "Add note", "Document", "Remove stale", "Pin", "Suppress"
# MEDIUM/HARD signals: "evaluate", "investigate", "arm64", cross-repo references

# ALREADY-DONE rate: ~12% of large backlogs; detect with worktree-excluded grep
# EASY queue exhaustion: ~76% of infra-only repos; remaining = MEDIUM/HARD
```

### Phase 2: Wave Execution

**Group issues before dispatching:**

- Issues touching the **same file** → same agent or sequential waves
- `ci.yml` / `CMakeLists.txt` / hot-file issues → **one agent per file per wave**
- Wave size: ≤5 agents optimal for infra repos

**Branch naming (include in every agent prompt as a command):**
```bash
git checkout -B <N>-auto-impl origin/main   # explicit base — never inherited
```

**Agent prompt mandatory elements:**
1. Exact branch name as an imperative command
2. `STOP and report ALREADY-DONE if the issue is already implemented`
3. `STOP and report BLOCKED if the spec requires a design decision`
4. Pre-commit step (only if `.pre-commit-config.yaml` exists)
5. Correct auto-merge: `gh pr merge <PR> --auto --squash` (HomericIntelligence) or portable fallback

**Post-wave ground truth:**
```bash
gh pr list --author "@me" --state all --limit 50   # Never trust agent-reported PR numbers
```

### Phase 3: Rate-Limit Recovery

**Primary REST rate limit** (resets on a schedule):
```bash
# Pattern in stderr: "Limit reached … resets N:XXpm (America/Los_Angeles)"
# Action: sleep until reset, then resume
```

**Secondary rate limit / GraphQL limit** (403 BCE2 or `GraphQL: API rate limit already exceeded`):
```bash
# gh exits non-zero with message on stderr — OR exits 0 with JSON errors array
# Detect both:
if echo "$STDERR" | grep -qE "GraphQL: API rate limit|rate limit already exceeded|BCE2"; then
  sleep 60 && retry
fi
# Also check exit-0 JSON errors:
echo "$STDOUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
if isinstance(d, dict) and any(e.get('type')=='RATE_LIMITED' for e in d.get('errors',[])):
    sys.exit(1)
"
```

**Proactive per-thread throttle** (Python, prevents hitting secondary limits):
```python
import os, threading, time
_GH_THROTTLE = threading.local()

def _gh_throttle_wait() -> None:
    rate = float(os.environ.get("GH_RATE_LIMIT_PER_SEC", "5"))
    if rate <= 0:
        return
    now = time.monotonic()
    last = getattr(_GH_THROTTLE, "last_call", 0.0)
    gap = 1.0 / rate
    if (elapsed := now - last) < gap:
        time.sleep(gap - elapsed)
    _GH_THROTTLE.last_call = time.monotonic()

# Call _gh_throttle_wait() at every gh CLI invocation chokepoint
```

### Phase 4: Auto-Merge Mechanics

**HomericIntelligence org policy** (verified across 11 repos, 2026-05-11): `enablePullRequestAutoMerge` with rebase is disabled org-wide. Always use `--squash`.

```bash
# For HomericIntelligence (no round-trip needed):
gh pr merge "$PR" --auto --squash --repo "HomericIntelligence/$REPO"

# Verify armed:
gh pr view "$PR" --repo "HomericIntelligence/$REPO" \
  --json autoMergeRequest --jq '.autoMergeRequest.mergeMethod'
# Expected: "SQUASH"

# Admin merge when auto-merge is disabled on the repo:
gh pr merge "$PR" --squash --repo "$ORG/$REPO"
```

Note: The web UI may allow manual rebase-merge even when `enablePullRequestAutoMerge` with rebase is disabled — this is a separate setting. Trust `--squash` over any `CLAUDE.md` prescribing `--rebase`.

### Phase 5: Idempotent Issue Filing

```bash
# Sequential filing (never parallel per repo):
for TITLE in "${TITLES[@]}"; do
  BODY_FILE=$(mktemp /tmp/issue_XXXXXX.md)
  echo "$BODY" > "$BODY_FILE"
  gh issue create --repo "$ORG/$REPO" \
    --title "$TITLE" --label "$LABEL" --body-file "$BODY_FILE"
  rm "$BODY_FILE"
  sleep 3
done

# Idempotency check before filing:
COUNT=$(gh issue list --repo "$ORG/$REPO" --label "$LABEL" \
  --state open --json number --limit 200 --jq 'length')
[ "$COUNT" -ge "$EXPECTED" ] && echo "Already filed — skip" && exit 0
```

### Phase 6: Correct Closing Keywords for Bundle PRs

GitHub closes issues only when each issue has its own keyword in the PR body or squash-commit message:

```markdown
# CORRECT (period-separated, one keyword per issue):
**Closes:** Closes #97. Closes #106. Closes #114. Closes #N.

---
<rest of body>
```

Formats that **silently fail** (issues stay open after merge):
- `Closes #A, #B, #C` — only closes #A
- Markdown tables with issue numbers
- Bullet lists: `- Closes #A`

### Phase 7: Token Authentication in Sub-Agents

Each Bash tool call runs in a fresh shell. Any `unset` at the top of a prompt does NOT persist.

```bash
# ALWAYS chain unset before every gh/git-push invocation:
unset GITHUB_TOKEN GH_TOKEN && gh pr create ...
unset GITHUB_TOKEN GH_TOKEN && git push -u origin "$BRANCH"

# Also run once per agent to configure git to use keyring token:
gh auth setup-git
```

Symptom: `Resource not accessible by personal access token` or `403 denied` in agents but not interactively — caused by ambient `GITHUB_TOKEN` (narrow-scope fine-grained PAT) shadowing the keyring `gho_*` OAuth token.

### Phase 8: Idempotent Comment Posting (Dedup Across Restarts)

```python
# Hydrate comment-ID cache from GitHub API on first access per issue:
import re, subprocess, json

STAGE_RE = re.compile(r"## Stage: (\w+)(?:\s+\(iteration (\d+)\))?")
_comment_ids: dict[str, int] = {}
_loaded: set[int] = set()

def _load_existing_comment_ids(issue_number: int) -> None:
    if issue_number in _loaded:
        return
    page = 1
    while True:
        result = subprocess.run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{issue_number}/comments",
             "--paginate", "--jq", ".[] | {id,body: .body[:80]}"],
            capture_output=True, text=True)
        if not result.stdout.strip():
            break
        for line in result.stdout.splitlines():
            item = json.loads(line)
            m = STAGE_RE.search(item["body"])
            if m:
                key = f"{m.group(1)}-{m.group(2) or '0'}"
                _comment_ids[key] = item["id"]
        page += 1
        break  # gh --paginate handles pages automatically
    _loaded.add(issue_number)
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gh pr merge --auto --rebase` on HomericIntelligence repos | Standard rebase auto-merge for all PRs | `enablePullRequestAutoMerge` with rebase is disabled org-wide; GraphQL error fires on every attempt | Use `--auto --squash` for all HomericIntelligence repos; portable fallback for cross-org scripts |
| REST-only rate-limit regex | Detected `"Limit reached … resets"` only | GraphQL calls (gh issue list --json, gh issue view) emit `"GraphQL: API rate limit already exceeded for user ID NNNN"` on stderr, missed by REST regex | Add GraphQL regex; also check exit-0 stdout JSON for `errors[].type == "RATE_LIMITED"` |
| Parallel filer agents per repo | Two agents filing issues to same repo concurrently | Created ~49 exact-title duplicates per repo | One filer agent per repo; use `group_by(.title)` dedup scan after any multi-wave session |
| `gh issue list` without `--limit` | Used default limit for count verification | GitHub defaults to 30 results; repos with 31+ always showed as MISMATCH | Always pass `--limit 200` (or 500 for large repos) when counting |
| `Closes #A, #B, #C` in PR body | Comma-separated closing keywords for bundle PRs | GitHub only closes the first issue in a comma list | Use `Closes #A. Closes #B. Closes #C.` — one keyword per issue |
| Heredoc directly in `gh issue edit --body` | `gh issue edit --body "$(cat <<'HEREDOC'...HEREDOC)"` | Backticks inside code blocks in body break heredoc quoting | Write body to temp file; pass `--body "$(cat $TMPFILE)"` |
| Single `unset GITHUB_TOKEN` at agent prompt top | Unset once, then ran multiple gh commands | Each Bash tool call is a fresh shell; the unset did not persist across calls | Chain `unset GITHUB_TOKEN GH_TOKEN &&` before every gh/git push invocation |
| Parallel agents dispatched while L0 was on non-main branch | Worktree agents inherited L0's current branch as base | Agents silently picked up unrelated commits; GitHub refused rebase: "can't be rebased" | Verify L0 is on `main` before dispatching OR include `git checkout -B <N> origin/main` as step 1 in every agent prompt |
| Grepping for ALREADY-DONE without worktree exclusion | Plain `grep -rn pattern /repo/` | Stale worktrees contain old branch state — false "still present" for issues already fixed in main | Always pass `--exclude-dir=.worktrees --exclude-dir=.issue_implementer --exclude-dir=.claude --exclude-dir=.git` |
| Two agents dispatched to same file in same wave | ci.yml / CMakeLists.txt changes in parallel | Guaranteed merge conflict on same file | Batch ALL same-file issues into ONE agent per wave; use Sonnet for ci.yml / hot-file issues |
| Closing lower-numbered duplicate unconditionally | Assumed lower issue number = canonical | Some child issues referenced the higher Epic number in "Part of #N" | Before closing, grep child bodies for "Part of #" to determine which issue number to keep |
| Trusting agent-reported PR numbers | Accepted agent output ("PR #403") for wave reconciliation | Agents report stale in-flight views; 3/16 waves had wrong PR numbers | Always verify with `gh pr list --author "@me" --state all --limit 50` after every wave |
| Haiku agents for 40+ issue filing batches | Haiku paces faster, sent more requests | Hit GitHub secondary rate limits (403 BCE2) faster than Sonnet | Use Sonnet for large filing batches; Sonnet's natural pace is more rate-limit resilient |
| Two agents touching the same hot file in the same sub-wave | `scripts/apply.sh` modified by agents for issues #187 and #195 | Merge conflict on same function block | Hot-file serialization: at most one agent per hot file per sub-wave |
| `gh search issues "term"` for body-text scanning | Used GitHub search API for issue body matching | Returns false positives from repo names and README text | Use `gh issue list --json body | jq 'select(.body | test("term"))'` per-repo instead |
| Mechanical string replace for terminology migration | `sed 's/old-term/new-term/g'` across all issue bodies | Inverted-semantic flags (SKIP_VERIFY vs TLS_VERIFY) get wrong boolean values; context-specific class renames lost | Use Sonnet agents with explicit terminology mapping table; flag inverted-semantic pairs in mapping |

## Results & Parameters

### Filing Parameters

| Parameter | Value |
| ----------- | ------- |
| Sleep between issues | 3 seconds |
| Sleep on 403 | 60 seconds, retry up to 3× |
| `--limit` for `gh issue list` | 200 (never omit) |
| Agents per repo | 1 (never concurrent) |
| Preferred model for filing | Sonnet (rate-limit resilient) |
| Body delivery | `--body-file /tmp/body.txt` |
| Wave size | ≤5 agents optimal |
| ALREADY-DONE rate | ~12% of large backlogs |
| EASY queue exhaustion | ~76% of infra-only repos |

### Issue Classification Heuristics

```
EASY if ALL of:
  - Title has: "Update", "Document", "Fix typo", "Remove stale", "Add note", "Pin", "Suppress"
  - Body has: single file target
  - Expected diff: < 20 lines
  - No logic/behavior change

DUPLICATE if:
  - Same target file AND same or nearly same description as another open issue
  - Canonical = lowest issue number (preserves original context)

ALREADY-DONE if:
  - Issue says "remove X" → grep for X → not found in main tree (worktrees excluded)
  - Issue says "add Y to Z" → grep for Y in Z → already present

MEDIUM/HARD if:
  - Requires "evaluate"/"investigate"/"design decision"
  - Cross-repo coordination required
  - "arm64", "Phase 6", multi-phase rollout
```

### Haiku Agent Prompt Template (validated at scale)

```
You are implementing GitHub issue #<N> in repo <ORG>/<REPO>.

Issue: <title>
Body: <body>

Steps:
1. Run: unset GITHUB_TOKEN GH_TOKEN && git checkout -B <N>-auto-impl origin/main
2. [implementation steps]
3. Run pre-commit (if .pre-commit-config.yaml exists) and fix any failures
4. Commit: "type(scope): description\n\nCloses #<N>\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
5. Push: unset GITHUB_TOKEN GH_TOKEN && git push -u origin <N>-auto-impl
6. PR: unset GITHUB_TOKEN GH_TOKEN && gh pr create --title "..." --body "Closes #<N>"
7. Merge: unset GITHUB_TOKEN GH_TOKEN && gh pr merge <PR> --auto --squash

STOP and report ALREADY-DONE if the change is already in the codebase.
STOP and report BLOCKED if the spec is unclear or requires a design decision.
```

### Commit Message for Bundle PRs

```
type(scope): brief description

Closes #A. Closes #B. Closes #C.

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Dedup Script Template (Python)

```python
import subprocess, json

def find_dupes(org_repo: str, label: str) -> list[int]:
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", org_repo, "--label", label,
         "--state", "open", "--json", "number,title", "--limit", "200"],
        capture_output=True, text=True)
    issues = json.loads(result.stdout)
    seen: dict[str, int] = {}
    dupes: list[int] = []
    for issue in sorted(issues, key=lambda x: x["number"]):
        t = issue["title"]
        if t in seen:
            dupes.append(issue["number"])  # higher number = duplicate
        else:
            seen[t] = issue["number"]
    return dupes
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence/AchaeanFleet | 235-issue myrmidon swarm, 24+ waves, 91 PRs merged (2026-04-23) | 202 issues closed; EASY queue exhausted at 76%; ci.yml conflict avoidance; Docker inline comment parse errors |
| HomericIntelligence/ProjectKeystone | 180-issue C++20 swarm, 16 waves (2026-04-25) | 7 new failure modes; libssl-dev gap; TSan+concurrentqueue hard blocker; CMakeLists.txt double-agent |
| HomericIntelligence/Myrmidons | shellcheck-warnings swarm ~25 issues (2026-04-24) | Hot-file serialization; 8 existing PRs discovered pre-swarm; all PRs merged CI-green |
| HomericIntelligence/Odysseus | 35-issue triage, 19 resolved (2026-04-23) | Worktree timeout on symlink-heavy repo; Haiku branch naming drift |
| HomericIntelligence (15 repos) | 680-finding audit issue filing (2026-04-28) | Org limit hit once; ~119 duplicates closed; `--limit 200` fix |
| HomericIntelligence/{Argus,Agamemnon,Myrmidons,Hermes,Charybdis} | Ecosystem-wide 5-repo sweep (2026-05-12) | 717 classified, 51 PRs merged, 78 retired in <24h; urllib3 runner-image CVE; coverage delta regression |
| HomericIntelligence (11 repos) | Auto-merge squash verification sweep (2026-05-11) | Rebase disabled org-wide; `--squash` accepted on all 11 repos |
| HomericIntelligence/ProjectHephaestus | GraphQL rate-limit detection (PR #412, 2026-05-15) | Added GRAPHQL_RATE_LIMIT_RE; 2255 unit tests; proactive per-thread throttle PR #404 |

## References

- [gh CLI manual](https://cli.github.com/manual/gh_issue_create)
- [GitHub closing keywords docs](https://docs.github.com/en/issues/tracking-your-work-with-issues/linking-a-pull-request-to-an-issue)
- [batch-low-difficulty-issue-impl history](./github-bulk-issue-and-pr-operations.history)
