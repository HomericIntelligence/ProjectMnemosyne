---
name: skill-merge-manifest-enumeration-from-cluster-examples
description: "Use when consolidating many narrow skills into canonical ones using cluster examples. Triggers: (1) issue body lists 3 example members per cluster but NOT the full member list, (2) merge agents stall or drift scope because they lack a definitive skill list, (3) running bulk skill consolidation across 10+ clusters, (4) running a *second-pass* consolidation after an earlier merge wave produced canonicals — agents must be told about them or they will propose duplicates, (5) building a swarm where each sub-agent should choose between 'new cluster' and 'absorb into existing'."
category: tooling
date: 2026-05-19
version: "2.0.0"
user-invocable: false
verification: verified-local
history: skill-merge-manifest-enumeration-from-cluster-examples.history
tags: [skill-merge, consolidation, manifest, enumeration, cluster, swarm, bulk, second-pass, absorb-into-canonical]
---

# Skill-Merge Manifest Enumeration from Cluster Examples

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-05-18 |
| **Objective** | Reliably enumerate every skill belonging to each merge cluster when the issue body only provides 3 example members |
| **Outcome** | Successful — decoupled enumeration from merge, eliminating stall and scope-drift in a 17-cluster, 1100-skill consolidation |
| **Verification** | verified-local |
| **History** | [v1.0.0 → v2.0.0](skill-merge-manifest-enumeration-from-cluster-examples.history) |

## When to Use

- Issue body lists only 3 example members per cluster, not the full member list
- Merge agents stall mid-run because they cannot determine which skills belong to the cluster
- Scope errors occur (agent merges wrong skills or misses members) during bulk consolidation
- Running a large-scale skill consolidation with 10+ clusters in parallel
- A "catch-all" cluster exists that may absorb irrelevant skills
- You need cross-cluster duplicate detection before shipping merge PRs

## Verified Workflow

### Quick Reference

```bash
# Gate 0 — enumerate each cluster in parallel (one Haiku agent per cluster)
# Each agent writes: /tmp/skill-merge-manifests/<cluster_id>.json

# Gate 1 — detect cross-cluster duplicates after all manifests are written
jq -r '.absorbed_skills[]' /tmp/skill-merge-manifests/*.json | sort | uniq -d

# Gate 2 — merge agents read their manifest as single source of truth
MANIFEST=$(cat /tmp/skill-merge-manifests/<cluster_id>.json)
```

```json
{
  "cluster_id": "M07",
  "canonical_name": "tooling-myrmidon-swarm-full-workflow",
  "absorbed_skills": ["skill-a.md", "skill-b.md"],
  "keep_as_examples": ["skill-a.md"],
  "boundary_notes": "Excludes swarm-orchestration meta-skills (see excluded list)",
  "estimated_loc_after_merge": 420,
  "overflow_warning": false
}
```

### Detailed Steps

1. **Dispatch one Haiku enumeration agent per cluster** — do not bundle clusters; isolation
   prevents cross-contamination.

2. **Each enumeration agent follows this exact sequence:**
   a. Read the 3 example members from the issue to learn the keyword surface
   b. Grep the full skills corpus for those keywords
   c. Read each candidate match and decide IN or OUT
   d. Write the manifest JSON file to `/tmp/skill-merge-manifests/<cluster_id>.json`

3. **Enumeration agent must EXCLUDE protected meta-skills** — before writing the manifest,
   filter out any skill whose filename matches the protected list (see Results & Parameters).
   Failure to exclude leaves the swarm able to delete its own foundation mid-run.

4. **Gate 1 — cross-cluster duplicate detection** (mandatory, runs after all manifests written):

   ```bash
   jq -r '.absorbed_skills[]' /tmp/skill-merge-manifests/*.json | sort | uniq -d
   ```

   For each duplicate, reassign it to the most-specific cluster by updating that cluster's
   manifest JSON before launching merge agents.

5. **For the "catch-all suspect" cluster** — instruct the enumerator to apply EXTRA strict
   inclusion criteria. Document the rejection rate in `boundary_notes`.

6. **Launch merge agents** — each merge agent reads only its cluster manifest and merges
   exactly the `absorbed_skills[]` list. No guessing, no re-enumeration.

7. **Per-PR markdownlint discipline** — before pushing each merge PR:
   - Escape `\|` inside backtick code-spans in table cells (avoids MD056)
   - Escape `\#` at the start of lines referencing PR numbers (avoids MD018)

## Second-Pass Variant

When a prior merge wave has already produced canonicals (e.g., M1–M17), enumeration agents
in the next pass must be told about those canonicals or they will propose new clusters that
duplicate existing ones.

### Prompt Addendum (inject into every second-pass enumeration agent)

```text
EXISTING CANONICALS (DO NOT propose new clusters with these names):
- <name1> — <one-line theme>
- <name2> — <one-line theme>
...

For each input skill, choose ONE of:
  (a) absorb_into_canonical: <name> — if the skill clearly belongs in an existing canonical
  (b) new_cluster_candidate — if the skill is narrow AND not covered by any existing canonical

Output two arrays in your JSON: `clusters[]` (new only) AND `absorb_into_canonical[]`.
```

### JSON Output Schema Additions

Second-pass manifests extend the base schema with an `absorb_into_canonical` array:

```json
"absorb_into_canonical": [
  {"name":"<skill>","canonical":"<one-of-existing>","why":"<one-line>"}
]
```

The `clusters[]` array contains **only genuinely new** clusters whose names do not match any
existing canonical. The orchestrator gate must validate this constraint before launching any
merge agents — reject any `clusters[]` entry whose `canonical_name` matches an existing
canonical and re-route its members into `absorb_into_canonical[]` automatically.

### Gate Stage Validation (second-pass)

```bash
# Check no proposed cluster name collides with an existing canonical
EXISTING_CANONICALS=("canonical-name-1" "canonical-name-2")  # fill from prior wave
jq -r '.clusters[].canonical_name' /tmp/skill-merge-manifests/*.json | while read name; do
  for existing in "${EXISTING_CANONICALS[@]}"; do
    if [[ "$name" == "$existing" ]]; then
      echo "COLLISION: $name already exists — re-route to absorb_into_canonical"
    fi
  done
done
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Direct merge without enumeration phase | Merge agent given 3 examples and told to discover the rest | Agent stalled or drifted scope — it had no definitive boundary | Always enumerate first; merge agents need a fixed manifest |
| Single agent enumerating all clusters | One agent iterated all 17 clusters sequentially | Cross-contamination: agent conflated keywords across adjacent clusters | One enumeration agent per cluster, fully isolated |
| Omitting protected meta-skill exclusions | Enumeration agents allowed to include any skill | Cluster owning "swarm orchestration" absorbed and deleted its own tooling | Hard-code the protected list in every enumeration agent prompt |
| Skipping Gate 1 duplicate check | Manifests shipped directly to merge agents | Same skill appeared in two merge PRs, causing conflicts and double-deletion | Gate 1 duplicate detection is mandatory before any merge launches |
| Trusting catch-all cluster to self-bound | No extra strictness instruction for catch-all | Catch-all absorbed 82 candidates; most were wrong cluster | For catch-all clusters, instruct enumerator to be EXTRA strict |
| Overflow above 100 skills per manifest | No cap enforced | Merge agent timeout / PR too large to review | Cap at 100; set `overflow_warning: true` and split into sub-PRs |
| Running second-pass clustering without supplying the existing-canonicals list | Documentation-shard agent proposed C1=`academic-paper-validation-and-publication` and C2=`stale-documentation-audits-and-sync` as NEW clusters — both were already canonicals from M16/M17. 27 members had to be re-routed at the gate stage | Always pass the existing-canonicals list + 1-line themes as agent input; require a two-bucket output (clusters[] + absorb_into_canonical[]); validate at gate stage that no proposed cluster name matches an existing canonical | |

## Results & Parameters

### Manifest Schema

```json
{
  "cluster_id": "<MXX>",
  "canonical_name": "<kebab-case-canonical-skill-name>",
  "absorbed_skills": ["<skill-filename-1.md>", "<skill-filename-2.md>"],
  "keep_as_examples": ["<one-or-two-representative-members.md>"],
  "boundary_notes": "<free text — what is explicitly excluded and why>",
  "estimated_loc_after_merge": 350,
  "overflow_warning": false
}
```

Cap `absorbed_skills` at 100 entries. If a cluster exceeds 100, set `overflow_warning: true`
and split into sub-clusters before launching merge agents.

### Protected Meta-Skills (always exclude from every cluster manifest)

These skills are swarm infrastructure — absorbing them into a canonical merge skill
breaks the agents running the merge itself:

```
worktree-parallel-agent-execution
myrmidon-swarm-end-to-end-orchestration-full-workflow
tooling-sub-agent-pr-trust-but-verify
tooling-myrmidon-swarm-prompt-guardrails-reduce-stall-rate
stop-reassess-gate-bulk-transformation
```

Add these as a fixed exclusion list in every enumeration agent prompt.

### Catch-All Cluster Prompt Addendum

> You are enumerating cluster \<ID\> which is designated a CATCH-ALL. Apply EXTRA strict
> inclusion criteria. A skill belongs here ONLY if it genuinely fits no other cluster.
> Err heavily toward OUT. Document your rejection count in `boundary_notes`.

### Gate 1 Command

```bash
# After all enumeration agents complete:
mkdir -p /tmp/skill-merge-manifests
jq -r '.absorbed_skills[]' /tmp/skill-merge-manifests/*.json \
  | sort | uniq -d \
  > /tmp/skill-merge-manifests/duplicates.txt
cat /tmp/skill-merge-manifests/duplicates.txt
# For each duplicate, manually edit the less-specific cluster's manifest to remove it
```

### Markdownlint Rules (per-PR, before push)

| Violation | Pattern | Fix |
|-----------|---------|-----|
| MD056 | Pipe `\|` inside backtick code-span in table cell | Escape as `\\\|` |
| MD018 | `\#` at start of line (PR number references) | Escape as `\\\#` |

### Observed Scale

| Metric | Value |
|--------|-------|
| Clusters | 17 |
| Total skills in corpus | ~1100 |
| Enumeration agents dispatched | 17 (Haiku tier) |
| Stall rate after change | ~0% |
| Scope errors after change | ~0% |
| Catch-all rejection rate | 65 of 82 candidates rejected |

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectMnemosyne | 17-cluster, 1100-skill consolidation session | Manifest-first enumeration decoupled from merge phase |
