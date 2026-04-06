---
name: bulk-issue-terminology-migration
description: "Update all GitHub issues across a multi-repo org to remove deprecated terminology references. Use when: (1) an ADR or architectural decision deprecates a component name that appears in many open issues, (2) doing a mass rename (e.g., ai-maestro → Agamemnon) across 5+ repos with 50+ issues, (3) need to purge all traces of deprecated terminology from issue tracker."
category: tooling
date: 2026-04-05
version: "1.1.0"
user-invocable: false
verification: verified-local
tags: [github, issues, bulk-update, terminology, migration, myrmidon-swarm]
---
# Skill: Bulk Issue Terminology Migration

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-04-05 |
| **Objective** | Purge all deprecated "ai-maestro" references from ~80 open issues across 10 HomericIntelligence repos |
| **Outcome** | Success — 5 parallel Sonnet agents updated all issues with context-sensitive mapping |
| **Verification** | verified-local (agents ran and reported success; no CI for issue edits) |

## When to Use

- An ADR or architectural decision deprecates a component and many open issues still reference the old name
- Need to do a mass terminology rename (e.g., `ai-maestro` → `Agamemnon`) across 5+ repos
- Want to purge all traces of deprecated terminology from the issue tracker
- 50+ issues need updating — manual editing is impractical

**Don't use when:**
- Fewer than 10 issues — just do it manually
- Issues need substantive rewrites beyond renaming — use per-issue review instead
- You need to validate each update against current codebase state first

## Verified Workflow

### Quick Reference

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
|----------|----------|-------|
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

### Phase 5: Verify

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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| `gh search issues "maestro" --owner HomericIntelligence` | Used GitHub search API to find issues | Returns false positives matching repo names, README text, not just issue bodies | Always use `gh issue list --json body \| jq` per-repo scan for body-text matching |
| Heredoc directly in `gh issue edit --body` | `gh issue edit --body "$(cat <<'HEREDOC'\n...\nHEREDOC)"` | Backticks in code blocks inside the body break heredoc quoting; shell expands incorrectly | Always write to a temp file first, then pass `"$(cat $TMPFILE)"` |
| 1 agent per issue | Spawning 80 agents for 80 issues | Excessive agent spawn overhead; hits parallelism limits | Batch 10-20 issues per agent grouped by repo |
| Single agent for all 80 issues | One agent handling all repos | Context window risk; slow (sequential); no fault isolation | Split into 5 parallel agents capped at ~20 issues each |
| Blind string replace | Simple `sed 's/ai-maestro/ProjectAgamemnon/g'` approach | "MaestroClient" in ProjectScylla referred to Scylla's own internal class, needs separate rationale | Use Sonnet agents that reason about context, not mechanical sed |
| Mechanical rename of inverted flags | Renaming `AIM_TLS_SKIP_VERIFY` → `AGAMEMNON_TLS_VERIFY` without adjusting the value | The semantics are inverted: `SKIP_VERIFY=true` means TLS disabled, but `TLS_VERIFY=true` means TLS enabled — mechanical rename reverses the security setting | Flag inverted-semantic pairs in the mapping table explicitly; instruct agents to negate the value and add an explanatory comment |

## Results & Parameters

### Effective Agent Configuration

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

### Footer Template

Append to every updated issue body to provide audit trail:

```markdown
---
*Updated per [ADR-NNN](URL) — DEPRECATED_TERM references replaced with current architecture terminology.*
```

### Issue Count Metrics (reference session)

| Repo | Issues Found | Notes |
|------|-------------|-------|
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

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| HomericIntelligence | ADR-006 ai-maestro → Agamemnon migration, 2026-04-05 | ~80 issues across 10 repos |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.1.0 | 2026-04-05 | Added bash function name prefixes (`_aim_*`, `aim_*`) to terminology mapping; added inverted flag semantic warning for `AIM_TLS_SKIP_VERIFY` → `AGAMEMNON_TLS_VERIFY`; added Failed Attempts row for inverted flag mechanical rename; confirmed Phase 5 verification returns accurate 0-remaining results |
| 1.0.0 | 2026-04-05 | Initial skill creation |
