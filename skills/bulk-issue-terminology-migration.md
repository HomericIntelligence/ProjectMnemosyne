---
name: bulk-issue-terminology-migration
description: "Update all GitHub issues across a multi-repo org to remove deprecated terminology references, bulk-create issues from code markers (TODO/FIXME/DEPRECATED/NOTE), and deduplicate noisy issue trackers. Use when: (1) an ADR or architectural decision deprecates a component name that appears in many open issues, (2) doing a mass rename (e.g., ai-maestro → Agamemnon) across 5+ repos with 50+ issues, (3) need to purge all traces of deprecated terminology from issue tracker, (4) systematically filing GitHub issues from code markers (357+ markers in a codebase), (5) issue count has grown 3x+ with duplicate clusters and sprint planning is blocked."
category: tooling
date: 2026-04-05
version: "2.0.0"
user-invocable: false
verification: verified-local
tags: [github, issues, bulk-update, terminology, migration, myrmidon-swarm, dedup, bulk-filing, code-markers]
---
# Skill: Bulk Issue Terminology Migration

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-05 |
| **Objective** | Purge all deprecated "ai-maestro" references from ~80 open issues across 10 HomericIntelligence repos |
| **Outcome** | Success — 5 parallel Sonnet agents updated all issues with context-sensitive mapping. Absorbed bulk-issue-filing + bulk-issue-dedup on 2026-05-03 |
| **Verification** | verified-local (agents ran and reported success; no CI for issue edits) |

**Absorbed:** bulk-issue-filing (v1.0.0), bulk-issue-dedup (v1.0.0) on 2026-05-03

## When to Use

- An ADR or architectural decision deprecates a component and many open issues still reference the old name
- Need to do a mass terminology rename (e.g., `ai-maestro` → `Agamemnon`) across 5+ repos
- Want to purge all traces of deprecated terminology from the issue tracker
- 50+ issues need updating — manual editing is impractical
- You have many TODO/FIXME/DEPRECATED/NOTE markers to track systematically
- You want to systematically address technical debt with GitHub visibility
- You need to create a master tracking issue with child issues
- Issue count has grown 3x+ from organic development (agents repeatedly creating similar issues)
- Sprint planning is blocked by noisy issue list
- ADR or standard has generated 10+ near-identical follow-up issues
- Before classifying issues by complexity, want to remove obvious duplicates first

**Don't use when:**
- Fewer than 10 issues — just do it manually
- Issues need substantive rewrites beyond renaming — use per-issue review instead
- You need to validate each update against current codebase state first

## Verified Workflow

### Quick Reference — Terminology Migration

```bash
# Step 1: Scan all repos for issues matching the deprecated term
for repo in Repo1 Repo2 Repo3; do
  issues=$(gh issue list -R "OrgName/$repo" --state open --json number,title,body --limit 200 \
    --jq '.[] | select(.body != null) | select(.body | test("(?i)deprecated-term")) | {number, title}' 2>/dev/null)
  if [ -n "$issues" ]; then
    echo "=== $repo ===" && echo "$issues"
  fi
done

# Step 2: Edit an issue body via temp file (NEVER use heredoc directly)
TMPFILE=$(mktemp /tmp/issue-body-XXXXXX.md)
cat > "$TMPFILE" << 'HEREDOC'
<new body content with updated terminology>
HEREDOC
gh issue edit <N> -R "OrgName/Repo" --body "$(cat $TMPFILE)"
rm "$TMPFILE"

# Step 3: Update title if it contains deprecated term
gh issue edit <N> -R "OrgName/Repo" --title "<new title>"
```

### Quick Reference — Bulk Filing from Code Markers

```bash
# Find all code markers
grep -rn "TODO\|FIXME\|DEPRECATED\|NOTE" --include="*.mojo" --include="*.py" .

# Count by type
grep -rn "TODO" --include="*.mojo" . | wc -l
grep -rn "FIXME" --include="*.mojo" . | wc -l
grep -rn "DEPRECATED" --include="*.mojo" . | wc -l
grep -rn "NOTE" --include="*.mojo" . | wc -l

# CRITICAL: Verify labels exist before using
gh label list

# Create master tracking issue
gh issue create \
  --title "[Cleanup] Master: Code marker cleanup tracking" \
  --body "$(cat <<'EOF'
## Objective
Track all code marker cleanup issues.

## Scope
- 357+ code markers (TODO, FIXME, DEPRECATED, NOTE)
- Categorized into logical batches

## Child Issues
<!-- Add links as issues are created -->

## Labels
cleanup
EOF
)" \
  --label cleanup
```

### Quick Reference — Bulk Deduplication

```bash
# List all open issues
gh issue list --state open --limit 500 --json number,title \
  --jq '.[] | "\(.number)\t\(.title)"'

# Bulk close a cluster (canonical = lowest number, keep open)
CANONICAL=4101
for issue in 4450 4446 4441 4436 4429; do
  gh issue close "$issue" \
    --comment "Duplicate of #$CANONICAL — closing as part of bulk dedup"
done

# Close subset issues (narrower scope)
gh issue close 3867 \
  --comment "Subset of #3774 — scope is covered by the broader parent issue"
```

---

## Part 1: Terminology Migration Workflow

### Phase 1: Discover Issues

Use `gh issue list --json body` per-repo with a `jq` filter. **Do not use `gh search issues` with a keyword** — the search API matches against repo names and README text too, producing false positives.

```bash
# For each repo, get issues whose BODY contains the deprecated term
gh issue list -R "OrgName/$repo" --state open --json number,title,body --limit 200 \
  --jq '.[] | select(.body != null) | select(.body | test("(?i)old-term")) |
  {number, title, body_snippet: (.body | split("\n") | map(select(test("(?i)old-term"))) | first)}'
```

This gives you exact matches in issue bodies. Run for all repos and collect a full inventory before starting any edits.

### Phase 2: Build Terminology Mapping

Before writing agent prompts, produce an explicit bidirectional mapping table:

| Old Term | New Term | Notes |
| ---------- | ---------- | ------- |
| `ai-maestro` | `ProjectAgamemnon` | In prose |
| `ai-maestro API` | `ProjectAgamemnon REST API` | API references |
| `MAESTRO_URL` | `AGAMEMNON_URL` | Env vars |
| `AIM_HOST` | `AGAMEMNON_URL` | Alternate env var form |
| `MAESTRO_API_KEY` | `AGAMEMNON_API_KEY` | Auth env vars |
| `AIM_API_KEY` | `AGAMEMNON_API_KEY` | Alternate auth env var |
| `MaestroClient` | `AgamemnonClient` | Class names |
| `AsyncMaestroClient` | `AsyncAgamemnonClient` | Async variant |
| `MaestroError` | `AgamemnonError` | Exception classes |
| `MaestroConfig` | `AgamemnonConfig` | Config classes |
| `maestro_client.py` | `agamemnon_client.py` | File names |
| `aimaestro-mesh` | `homeric-mesh` | Network names |
| `maestro-apply` | `agamemnon-apply` | CLI dispatch |
| `maestro_*` metrics | `agamemnon_*` | Prometheus metric prefixes |
| `_aim_*` functions | `_agamemnon_*` | Internal bash function name prefixes (e.g., `_aim_curl` → `_agamemnon_curl`) |
| `aim_*` functions | `agamemnon_*` | Public bash function name prefixes (e.g., `aim_check_connection` → `agamemnon_check_connection`) |
| `AIM_TLS_SKIP_VERIFY` | `AGAMEMNON_TLS_VERIFY` | **Inverted semantics** — SKIP_VERIFY=true becomes TLS_VERIFY=false; value must be logically negated, not just renamed |

> **Note on bash function names:** Discovery scans for env vars and class names can miss internal function name prefixes in shell scripts. When a bash-heavy repo is in scope (e.g., Myrmidons), explicitly include function-prefix patterns (`_aim_`, `aim_`) in the per-repo scan regex.
> **Note on inverted flag names:** When the old and new names have opposite semantic suffixes (SKIP vs non-inverted), mechanical string replacement is **wrong** — the boolean value must be logically negated. Flag these in the mapping table explicitly and instruct agents to handle them with a comment explaining the inversion.

**Flag context-sensitive cases** — terms that look the same but need different treatment depending on the repo. Example: Scylla's `MaestroClient` was a local class targeting Agamemnon's chaos endpoints; it needed renaming too, but the rationale differs from Telemachy's `MaestroClient`.

### Phase 3: Launch Myrmidon Swarm (Parallel Sonnet Agents)

Group repos into batches of ~15-20 issues per agent. Use Sonnet (not Haiku) for the editing step because context-sensitive mapping requires reasoning, not just mechanical substitution.

**Optimal batch grouping:**
- Group repos by domain similarity — agents maintain better context within a domain
- Cap at ~20 issues per agent to stay well within context window
- For repos with 1-3 issues, bundle into a "misc" agent with other small repos

**Agent prompt template** (critical elements):
1. Full terminology mapping table
2. Footer to append to every updated body (e.g., ADR reference)
3. Explicit instruction to use temp file for `gh issue edit --body`
4. List of specific issues with repo + number
5. Sleep 1s between API calls

```
For each issue:
1. gh issue view <N> -R OrgName/Repo --json body,title
2. Apply terminology mapping (context-sensitive)
3. TMPFILE=$(mktemp /tmp/issue-XXXXXX.md)
   cat > "$TMPFILE" << 'HEREDOC'
   <new body>
   HEREDOC
   gh issue edit <N> -R OrgName/Repo --body "$(cat $TMPFILE)"
   rm "$TMPFILE"
4. If title contains deprecated term: gh issue edit <N> -R OrgName/Repo --title "<new title>"
5. sleep 1
```

### Phase 4: Close Obsolete Issues

After edits, identify issues that describe integration with the deprecated component where the new component natively handles that use case. Close with an explanation:

```bash
gh issue close <N> -R "OrgName/Repo" \
  --comment "Closed: this integration is now handled natively by <NewComponent> per <ADR>."
```

### Phase 5: Verify Terminology Migration

```bash
# Re-scan to confirm 0 remaining matches
for repo in Repo1 Repo2; do
  count=$(gh issue list -R "OrgName/$repo" --state open --json body --limit 200 \
    --jq '[.[] | select(.body != null) | select(.body | test("(?i)old-term"))] | length')
  echo "$repo: $count remaining"
done

# Also verify titles
gh search issues "old-term" --owner OrgName --state open --json number,title,repository
```

**Verified working (2026-04-05):** The `gh issue list | jq` post-scan approach was executed after the ADR-006 migration and returned 0 remaining matches across all 10 repos. This confirms the scan correctly reflects live GitHub state with no caching lag. The title scan via `gh search issues` also returned 0 results. This verification step can be trusted as a definitive pass/fail gate.

---

## Part 2: Bulk Filing from Code Markers

### Step 1: Discover All Markers

```bash
# Find all code markers
grep -rn "TODO\|FIXME\|DEPRECATED\|NOTE" --include="*.mojo" --include="*.py" .

# Count by type
grep -rn "TODO" --include="*.mojo" . | wc -l
grep -rn "FIXME" --include="*.mojo" . | wc -l
grep -rn "DEPRECATED" --include="*.mojo" . | wc -l
grep -rn "NOTE" --include="*.mojo" . | wc -l
```

### Step 2: Categorize Markers

Organize markers into batches:

| Batch | Type | Action |
|-------|------|--------|
| DEPRECATED | Files/aliases to delete | File deletion issues |
| Blocked TODOs | Depend on other issues | Create tracking issues |
| Already tracked | Reference existing issues | Skip |
| Templates | Intentional placeholders | Document, don't track |
| NOTEs | Informational | Convert to docstrings or keep |
| Actionable TODOs | Need implementation | Create individual issues |

### Step 3: Check Available Labels

```bash
# CRITICAL: Verify labels exist before using
gh label list

# Common labels to use:
# cleanup, testing, documentation, enhancement, bug
```

### Step 4: Create Master Tracking Issue

```bash
gh issue create \
  --title "[Cleanup] Master: Code marker cleanup tracking" \
  --body "$(cat <<'EOF'
## Objective
Track all code marker cleanup issues.

## Scope
- 357+ code markers (TODO, FIXME, DEPRECATED, NOTE)
- Categorized into logical batches

## Child Issues
<!-- Add links as issues are created -->

## Labels
cleanup
EOF
)" \
  --label cleanup
```

### Step 5: Batch Create Issues

Use heredoc for proper formatting:

```bash
gh issue create \
  --title "[Cleanup] Delete deprecated schedulers.mojo" \
  --body "$(cat <<'EOF'
## Objective
Delete deprecated scheduler file.

## Context
- **File**: `shared/training/schedulers.mojo`
- **Marker**: `DEPRECATED`
- **Original Text**: `# DEPRECATED: Use shared/training/lr_scheduler.mojo instead`

## Deliverables
- [ ] Verify no imports reference this file
- [ ] Delete the file
- [ ] Update any __init__.mojo exports

## Success Criteria
- [ ] File deleted
- [ ] Tests pass
- [ ] Pre-commit passes

## Parent Issue
Part of #<master-issue-number>
EOF
)" \
  --label cleanup
```

### Step 6: Batch Pattern for Multiple Issues

```bash
# Create multiple issues efficiently with a loop
for file in file1.mojo file2.mojo file3.mojo; do
  gh issue create \
    --title "[Cleanup] Delete deprecated ${file}" \
    --body "..." \
    --label cleanup
  sleep 1  # Avoid rate limiting
done
```

---

## Part 3: Bulk Deduplication Workflow

### Step 1: Retrieve all open issues

```bash
gh issue list --state open --limit 500 --json number,title \
  --jq '.[] | "\(.number)\t\(.title)"' > /tmp/issues.txt
wc -l /tmp/issues.txt
```

Use `--limit 500` (or higher) to get all issues in one call.

### Step 2: Identify duplicate clusters

Look for title patterns like:

- `"Audit all X for Y compliance"` repeated 20+ times
- `"Add Y pre-commit hook"` repeated 15+ times
- `"Document X in Y"` repeated 10+ times
- `"Fix X in Y.mojo"` with same underlying issue

Use an agent with the full issue list to reason about clusters:

```
Analyze these N open GitHub issues and identify ALL duplicate clusters.
For each cluster, identify:
1. The canonical (lowest number) issue
2. All duplicates to close
3. Any subset issues (narrower scope than a broader parent)

Output bash commands to close them all with appropriate comments.
```

### Step 3: Close duplicates in batches

For exact duplicates:

```bash
for issue in LIST_OF_DUPLICATES; do
  gh issue close "$issue" \
    --comment "Duplicate of #CANONICAL — closing as part of bulk dedup"
done
```

For subset issues:

```bash
gh issue close SUBSET_NUMBER \
  --comment "Subset of #PARENT — this specific case is covered by the broader parent issue"
```

### Step 4: Verify already-resolved issues

For "stale reference" or "verify X exists" issues, check the actual file state before closing:

```bash
# Example: verify stale count claim
grep "12 func" docs/dev/phases.md

# If not found → issue is already resolved
gh issue close 4435 --comment "Already resolved — file now shows correct count after prior refactor"
```

**Key rule**: Always read the file/config BEFORE assuming an issue is stale. Prior refactoring
may have already fixed it.

### Step 5: Track totals

```bash
# Count remaining open issues
gh issue list --state open --limit 500 --json number --jq 'length'
```

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| `gh search issues "maestro" --owner HomericIntelligence` | Used GitHub search API to find issues | Returns false positives matching repo names, README text, not just issue bodies | Always use `gh issue list --json body \| jq` per-repo scan for body-text matching |
| Heredoc directly in `gh issue edit --body` | `gh issue edit --body "$(cat <<'HEREDOC'\n...\nHEREDOC)"` | Backticks in code blocks inside the body break heredoc quoting; shell expands incorrectly | Always write to a temp file first, then pass `"$(cat $TMPFILE)"` |
| 1 agent per issue | Spawning 80 agents for 80 issues | Excessive agent spawn overhead; hits parallelism limits | Batch 10-20 issues per agent grouped by repo |
| Single agent for all 80 issues | One agent handling all repos | Context window risk; slow (sequential); no fault isolation | Split into 5 parallel agents capped at ~20 issues each |
| Blind string replace | Simple `sed 's/ai-maestro/ProjectAgamemnon/g'` approach | "MaestroClient" in ProjectScylla referred to Scylla's own internal class, needs separate rationale | Use Sonnet agents that reason about context, not mechanical sed |
| Mechanical rename of inverted flags | Renaming `AIM_TLS_SKIP_VERIFY` → `AGAMEMNON_TLS_VERIFY` without adjusting the value | The semantics are inverted: `SKIP_VERIFY=true` means TLS disabled, but `TLS_VERIFY=true` means TLS enabled — mechanical rename reverses the security setting | Flag inverted-semantic pairs in the mapping table explicitly; instruct agents to negate the value and add an explanatory comment |
| Close all duplicates in one loop | Used single bash loop for all 95 issues in dedup session | `gh` rate limiting hit on large batches | Break into smaller batches of 10-20 |
| Auto-detect duplicates via title similarity | Tried fuzzy string matching in Python for cluster detection | Too many false positives (e.g., "audit X" ≠ "add X audit") | Use agent reasoning for cluster detection instead |
| Fix pre-existing lint in same PR | Attempted to fix unrelated markdown violations while closing dedup issues | Scope creep, complex diff | Keep fix PR focused on intended changes only |
| Close "stale reference" without reading file | Assumed issue was stale based on title alone in dedup session | Issue #4435 title said "stale" but phases.md was already correct | Always read the actual file first before closing as resolved |
| Filing issues without checking labels | Tried to apply `deprecated` label during bulk-filing session | `deprecated` label did not exist; `gh` returned error | Always run `gh label list` before bulk filing and use only verified labels |

## Results & Parameters

### Effective Agent Configuration (Terminology Migration)

```yaml
# For a ~80 issue org-wide migration
agents: 5
issues_per_agent: 10-20
model: sonnet  # NOT haiku — context-sensitive mapping requires reasoning
waves: 1  # All agents launch simultaneously (independent repos, no deps)
rate_limit: sleep 1 between API calls
```

### Discovery Command (reusable)

```bash
# Full org scan — outputs JSON inventory ready for agent prompts
for repo in $(gh repo list OrgName --json name --limit 100 --jq '.[].name'); do
  issues=$(gh issue list -R "OrgName/$repo" --state open --json number,title,body --limit 200 \
    --jq '.[] | select(.body != null) | select(.body | test("(?i)DEPRECATED_TERM")) |
    {number, title, repo: "OrgName/'"$repo"'"}' 2>/dev/null)
  [ -n "$issues" ] && echo "$issues"
done
```

### Footer Template (Terminology Migration)

Append to every updated issue body to provide audit trail:

```markdown
---
*Updated per [ADR-NNN](URL) — DEPRECATED_TERM references replaced with current architecture terminology.*
```

### Issue Count Metrics — Terminology Migration (reference session)

| Repo | Issues Found | Notes |
| ------ | ------------- | ------- |
| Odysseus | 5 | Cross-repo audit issues |
| ProjectScylla | 8 | MaestroClient class rename |
| ProjectTelemachy | 21 | Heaviest — MaestroClient + env vars |
| ProjectKeystone | 13 | MaestroClient + metrics |
| ProjectArgus | 13 | Prometheus metric names |
| ProjectHermes | 9 | MAESTRO_URL + env vars |
| Myrmidons | 12 | AIM_HOST + api.sh |
| AchaeanFleet | 4 | aimaestro-mesh network name |
| ProjectProteus | 1 | maestro-apply dispatch |
| ProjectAgamemnon | 1 | ADR reference |
| **Total** | **~80** | 5 agents, ~25 min wall clock |

### Issue Template for Bulk Filing

```markdown
## Objective
[Brief description - what needs to be done]

## Context
- **File**: `[path/to/file.ext]`
- **Line(s)**: [line numbers]
- **Marker**: `[TODO|FIXME|DEPRECATED|NOTE]`
- **Original Text**: `[exact marker content]`

## Deliverables
- [ ] [Specific change 1]
- [ ] [Specific change 2]

## Success Criteria
- [ ] Marker addressed
- [ ] Tests pass
- [ ] Pre-commit passes

## Parent Issue
Part of #[master-issue-number]
```

### Batch Statistics — Bulk Filing (reference session, ProjectOdyssey 2026-01-01)

| Category | Count | Issues Created |
|----------|-------|----------------|
| DEPRECATED files | 7 | #3060-#3066 |
| Blocked TODOs | 32 | #3067-#3069, #3077-#3079 |
| Template placeholders | 30 | #3070, #3080 (tracking only) |
| NOTE cleanup | 36 | #3071-#3076 |
| Actionable TODOs | 50 | #3081-#3094 |
| **Total** | **155** | **36 issues** |

### Dedup Session Results (2026-03-13, ProjectOdyssey)

| Metric | Value |
|--------|-------|
| Starting issue count | 363 |
| Round 1 closed (ADR-009 clusters) | 84 |
| Round 2 closed (other clusters) | 11 |
| Round 3 closed (subsets) | 28 |
| Round 4 closed (already-resolved) | 12 |
| Code fix PR (#4509) | 7 files, 5 issues |
| **Total closed** | **112** |
| Final count | ~250 |

### Canonical identification rule

```
canonical = min(issue_number for issue in cluster)
```

Oldest issue (lowest number) = canonical. This preserves original context/discussion.

### Comment templates (Deduplication)

```
# Exact duplicate
"Duplicate of #CANONICAL — closing as part of bulk dedup"

# Subset issue
"Subset of #PARENT — this specific case is covered by the broader parent issue"

# Already resolved
"Already resolved — verified [what was checked]: [what was found]"
```

### Cluster detection prompt (for agent delegation)

```
Analyze these N open GitHub issues and identify ALL duplicate clusters
and subset relationships. For each cluster:
- Canonical: lowest issue number (keep open)
- Duplicates: list of issue numbers to close
- Subsets: issues that are narrower scope of a broader canonical

Output as bash script with gh issue close commands and appropriate comments.
Total count of issues to close: X
```

### Key Commands Reference

```bash
# Check available labels
gh label list

# Create issue with heredoc
gh issue create --title "..." --body "$(cat <<'EOF'
...
EOF
)" --label cleanup

# View created issues
gh issue list --label cleanup

# Link issues
# Use "Part of #<number>" in body
# Use "Closes #<number>" for PRs
```

### Platform Notes

- GitHub CLI (`gh`) must be authenticated: `gh auth status`
- Rate limiting: Add `sleep 1` between bulk creates/closes
- Labels must exist before use — create with `gh label create` if needed
- Maximum body length is 65536 characters
- Heredoc syntax requires `'EOF'` (quoted) to prevent variable expansion

## Key Insights

- Use `gh issue list --json body | jq` (not `gh search issues`) for body-text matching — search API returns false positives from repo names and README text
- Always use a temp file for `gh issue edit --body` — heredoc inside `$()` breaks on backticks in code blocks
- Use Sonnet (not Haiku) for context-sensitive terminology changes — mechanical sed produces wrong results when the same term has different meanings in different repos
- Flag inverted-semantic pairs in the mapping table (e.g., SKIP_VERIFY → TLS_VERIFY) — the boolean value must be logically negated, not just renamed
- Explicitly include bash function-prefix patterns (`_aim_`, `aim_`) in per-repo scan regex for shell-heavy repos
- For dedup, canonical = lowest issue number (preserves original context/discussion)
- Use agent reasoning for cluster detection rather than fuzzy string matching — fewer false positives
- Always read the actual file before closing "stale reference" issues — prior work may have already resolved it
- Always run `gh label list` before bulk filing — apply only verified labels
- Keep fix PRs focused: don't fix pre-existing lint violations in the same commit as issue management

## See Also

- GitHub CLI docs: https://cli.github.com/manual/gh_issue_create
- Master tracking issue (ProjectOdyssey bulk-filing session): #3059
- ProjectOdyssey: https://github.com/mvillmow/ProjectOdyssey

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence | ADR-006 ai-maestro → Agamemnon migration, 2026-04-05 | ~80 issues across 10 repos |
| ProjectOdyssey | Bulk code marker filing, 2026-01-01 | 357+ markers → 36 issues (PR #3059) |
| ProjectOdyssey | Bulk issue deduplication, 2026-03-13 | 363 → ~250 open issues (112 closed) |

## Changelog

| Version | Date | Changes |
| --------- | ------ | --------- |
| 2.0.0 | 2026-05-03 | Absorbed bulk-issue-filing (v1.0.0) and bulk-issue-dedup (v1.0.0); added Parts 2 & 3 workflow sections; merged FA table to 11 rows; added 2 new VO rows; added Key Insights section |
| 1.1.0 | 2026-04-05 | Added bash function name prefixes (`_aim_*`, `aim_*`) to terminology mapping; added inverted flag semantic warning for `AIM_TLS_SKIP_VERIFY` → `AGAMEMNON_TLS_VERIFY`; added Failed Attempts row for inverted flag mechanical rename; confirmed Phase 5 verification returns accurate 0-remaining results |
| 1.0.0 | 2026-04-05 | Initial skill creation |
