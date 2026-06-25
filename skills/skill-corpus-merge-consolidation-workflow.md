---
name: skill-corpus-merge-consolidation-workflow
description: "Workflows for maintaining a skills corpus: deduplicating overlapping skills, merging clusters into canonicals, preserving history snapshots, enumerating cluster members from examples, migrating formats (hierarchical→flat, dual-dir→single), and generalizing skills for cross-repo compatibility. Use when: (1) multiple skills share a common prefix and cover redundant content, (2) a merge epic lists only example members and a full member list is needed, (3) a merge PR deletes originals and their content must remain searchable, (4) legacy skills/<category>/<name>/SKILL.md files need migration to flat skills/<name>.md format, (5) skills have hardcoded repo paths that must be generalized, (6) a dual plugins/+skills/ directory must be consolidated, (7) bulk-migrating skills from one project to another, (8) a skill topic is now OBSOLETE and needs a prominent notice, (9) a mass PR drain or consolidation has closed PRs as superseded and you need to audit for silently-dropped unique content, (10) salvaging skill work stranded in a stray or misplaced clone-within-a-repo, (11) before recreating or relocating a skill file, checking whether it was previously consolidated/removed, (12) reconciling an accidental de-consolidation that reintroduced a deliberately-merged standalone skill."
category: tooling
date: 2026-06-15
version: "2.2.0"
user-invocable: false
verification: verified-ci
history: skill-corpus-merge-consolidation-workflow.history
tags: [skill-merge, deduplication, semver, consolidation, history, manifest, enumeration, flat-format, migration, plugin-generalization, corpus-maintenance, salvage-audit, closed-pr, post-drain, stranded-clone, de-consolidation, fix-forward, salvage]
---

# Skill Corpus Merge Consolidation Workflow

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-06-07 |
| **Objective** | Consolidate all skills-corpus maintenance operations: deduplication, cluster merges, history preservation, member enumeration, format migration, and cross-repo generalization |
| **Outcome** | Absorbed 8 narrow skills covering overlapping corpus-maintenance topics |
| **Verification** | verified-ci |
| **History** | [absorbed skills](./skill-corpus-merge-consolidation-workflow.history) |

## When to Use

- Multiple skills share a common prefix (`pr-review-*`, `mojo-test-*`) or cover the same topic
- `/advise` returns redundant or contradictory advice for the same query
- A merge epic provides only 3 representative examples and you need the full member list
- A merge PR deletes originals and their full body must remain searchable via grep or `/advise`
- `find skills/ -type d -mindepth 1` returns results — legacy nested format still present
- Skills have `source: ProjectName` in frontmatter or hardcoded repo-specific paths
- A dual `plugins/` + `skills/` directory structure is causing contributor confusion
- Porting skills from a source repo to ProjectMnemosyne for the first time (bulk migration)
- A skill topic is OBSOLETE (underlying bug/workaround fixed) and needs a prominent notice
- You found skill work stranded in a stray or misplaced clone-within-a-repo (e.g. a worktree
  living inside ANOTHER repo's tree) and need to salvage it safely
- Before recreating or relocating a skill file — check whether it was previously
  consolidated/removed (so you do not silently reintroduce a merged-away standalone)
- Reconciling an accidental de-consolidation: a deliberately-merged standalone skill was
  reintroduced on main and now duplicates guidance held in a bundle

## Verified Workflow

### Quick Reference

```bash
# Detect duplicate clusters by 2-part prefix
ls skills/*.md | grep -v notes.md | grep -v history | sed 's|skills/||;s|\.md$||' | \
  awk -F'-' '{print $1"-"$2}' | sort | uniq -c | sort -rn | head -20

# Enumerate full cluster from marketplace.json (no file reads)
python3 - <<'EOF'
import json, difflib
from collections import defaultdict
with open('marketplace.json') as f:
    skills = json.load(f)
prefix2 = defaultdict(list)
for s in skills:
    parts = s['name'].split('-')
    if len(parts) >= 2: prefix2['-'.join(parts[:2])].append(s['name'])
for k, v in sorted(prefix2.items(), key=lambda x: -len(x[1])):
    if len(v) >= 3: print(len(v), k, v)
EOF

# Skip-missing-safe deletion of absorbed originals
for f in skill-a skill-b skill-c; do
  [ -f "skills/$f.md" ]    && git rm "skills/$f.md"    || echo "skip $f.md"
  [ -f "skills/$f.notes.md" ] && git rm "skills/$f.notes.md" || true
  [ -f "skills/$f.history"   ] && git rm "skills/$f.history"  || true
done

# Detect legacy hierarchical skills
find skills/ -type d -mindepth 1
find skills/ -name "SKILL.md"

# Gate 1a — absorbed-vs-absorbed duplicates (same skill in two clusters)
jq -r '.absorbed_skills[]' /tmp/skill-merge-manifests/*.json | sort | uniq -d

# Gate 1b — canonical-vs-absorbed collision (one cluster's canonical is being
# absorbed/deleted by another cluster). MUST run too, or a canonical gets folded away.
python3 - <<'EOF'
import json, glob
canon, absorbed = {}, {}
for f in glob.glob('/tmp/skill-merge-manifests/*.json'):
    m = json.load(open(f))
    cid = m.get('cluster_id', f)
    canon[m['canonical_name']] = cid
    for a in m.get('absorbed_skills', []):
        absorbed.setdefault(a.replace('.md', ''), []).append(cid)
for name, cid in canon.items():
    if name in absorbed:
        print(f"COLLISION: canonical '{name}' ({cid}) is absorbed by {absorbed[name]}")
EOF

# Validate
python3 scripts/validate_plugins.py
```

### Part A — Deduplication and Cluster Merging

**Phase 1: Identify duplicate clusters**

1. List all skill names, extract 2-part prefixes, count occurrences (see Quick Reference)
2. For large registries (900+), use `marketplace.json` — no need to read 975 files
3. Use `difflib.SequenceMatcher` at >80% threshold to find semantically similar descriptions
4. Manually group by intent for different-named skills covering the same concept

**Phase 2: Enumerate full member list (when epic gives only examples)**

When an issue lists only 3 examples per cluster:

1. Dispatch one Haiku enumeration agent per cluster (isolated, non-bundled)
2. Each agent reads the 3 examples → greps corpus → decides IN or OUT per candidate
3. Agent writes `/tmp/skill-merge-manifests/<cluster_id>.json`:

```json
{
  "cluster_id": "MXX",
  "canonical_name": "kebab-case-canonical-name",
  "absorbed_skills": ["skill-a.md", "skill-b.md"],
  "boundary_notes": "Excludes swarm meta-skills",
  "estimated_loc_after_merge": 420,
  "overflow_warning": false
}
```

4. Gate 1 — cross-cluster duplicate check before any merge launches. Run BOTH halves:

   **Gate 1a (absorbed-vs-absorbed)** — the same skill claimed by two clusters:

   ```bash
   jq -r '.absorbed_skills[]' /tmp/skill-merge-manifests/*.json | sort | uniq -d
   ```

   **Gate 1b (canonical-vs-absorbed)** — a cluster's `canonical_name` appears in ANOTHER
   cluster's `absorbed_skills`. If skipped, one agent deletes/folds a skill that another agent
   is amending as a canonical → wrong-merge + a duplicate PR. This is mandatory:

   ```bash
   python3 - <<'EOF'
   import json, glob
   canon, absorbed = {}, {}
   for f in glob.glob('/tmp/skill-merge-manifests/*.json'):
       m = json.load(open(f))
       cid = m.get('cluster_id', f)
       canon[m['canonical_name']] = cid
       for a in m.get('absorbed_skills', []):
           absorbed.setdefault(a.replace('.md', ''), []).append(cid)
   for name, cid in canon.items():
       if name in absorbed:
           print(f"COLLISION: canonical '{name}' ({cid}) is absorbed by {absorbed[name]}")
   EOF
   ```

   For each collision, decide which cluster keeps the skill as canonical and remove it from the
   other cluster's `absorbed_skills[]` before launching any merge agent.

5. For second-pass sessions (existing canonicals from prior wave), pass the existing-canonicals list to every enumeration agent and require two-bucket output: `clusters[]` (new only) + `absorb_into_canonical[]`

**Protected meta-skills (always exclude from every manifest)**:

```
worktree-parallel-agent-execution
myrmidon-swarm-end-to-end-orchestration-full-workflow
tooling-sub-agent-pr-trust-but-verify
tooling-myrmidon-swarm-prompt-guardrails-reduce-stall-rate
stop-reassess-gate-bulk-transformation
```

**Phase 3: Merge each cluster**

1. Read ALL source skills — extract unique content (deduplicate by lesson/concept, not exact text)
2. Write consolidated skill at `skills/<merged-name>.md` with `version: "1.0.0"`
3. Create `skills/<merged-name>.history` with `## Superseded from <name>` per absorbed skill (see Part B)
4. Delete all source `.md`, `.notes.md`, and `.history` files (skip-missing-safe)
5. Parallel agents: assign non-overlapping files to avoid conflicts; 3 at a time for large batches
6. **Run pre-commit once and re-stage BEFORE the real commit.** The `end-of-file-fixer` hook
   modifies the `.history` file on the first `git commit`, which aborts that commit (leaving the
   branch pushed with no commit / an empty PR number) and forces a manual retry. Sequence the
   merge helper as:

   ```bash
   git add -A skills/
   pre-commit run --files skills/<canonical>.md skills/<canonical>.history  # fixers run once
   git add -A skills/                                                       # re-stage the fixes
   git commit -m "feat: ..."                                                # now succeeds clean
   ```

7. **Do NOT re-dispatch a merge agent for a cluster while an earlier one may still be alive.**
   During error recovery, re-dispatching for the same cluster created a DUPLICATE PR on the same
   branch. Verify cluster progress from git/gh state, NOT from agent/background-task IDs (those
   notification IDs get reshuffled and mislabeled):

   ```bash
   git ls-remote --heads origin "skill/<cluster-branch>"   # already pushed?
   gh pr list --head "skill/<cluster-branch>" --json number,url  # PR already open?
   ```

   Only re-dispatch if BOTH return empty.

**Special case: OBSOLETE topics**

When the underlying topic is no longer applicable (bug fixed at compiler level):

```markdown
## <Topic> Status: OBSOLETE

> **<Topic> has been fixed.** <Brief explanation.>
>
> **Do NOT use this skill to implement <workaround> on new code.**
>
> This skill is preserved for historical reference only.
```

Consolidate to 1 file even if subtopics were well-organized — the OBSOLETE notice is the
dominant content and must not be fragmented across multiple files.

### Part B — History Preservation (Superseded Snapshots)

When a merge PR deletes originals, create `skills/<canonical-name>.history`:

```bash
# Template per absorbed skill
cat >> skills/<canonical-name>.history << 'EOF'
## Superseded from <absorbed-skill-name>

**Original date:** YYYY-MM-DD
**Original version:** X.Y.Z

```yaml
name: <absorbed-skill-name>
description: "..."
category: <category>
date: YYYY-MM-DD
version: "X.Y.Z"
```

`<full body verbatim>`

---
EOF
```

Key invariants:

| Rule | Rationale |
| ------ | ----------- |
| Heading is exactly `## Superseded from <name>` | Enables `grep "Superseded from" skills/*.history` audits |
| Full body verbatim — no summarizing | Content must be recoverable without `git log` |
| `history:` frontmatter references actual filename | Validator rejects mismatches |
| Canonical `description` incorporates all absorbed triggers | `/advise` search continues to surface canonical |
| Canonical `.md` stays under 700 LOC | Reviewers can skim PR diff |

### Part C — Format Migration (Hierarchical → Flat)

When `find skills/ -type d -mindepth 1` returns results:

```bash
# For each legacy skill at skills/<cat>/<name>/skills/<name>/SKILL.md
cp skills/<cat>/<name>/skills/<name>/SKILL.md skills/<name>.md
cp skills/<cat>/<name>/references/notes.md skills/<name>.notes.md   # if present
rm -rf skills/<cat>/<name>/
rmdir skills/<cat>/  # only if empty

# Verify required frontmatter fields after copy
# Add version: "1.0.0" if missing (common in partial migrations)
```

For migration scripts that copy skills between projects:

```python
# Idempotent bulk migration pattern
def migrate_skill(skill_name, source_dir, dest_dir, dry_run=False):
    if skill_already_exists(skill_name, dest_dir):
        return False  # skip
    # Copy SKILL.md + ALL subdirs (scripts/, templates/, hooks/, references/)
    import shutil
    source_dir_path = source_skill_md.parent
    for subdir in sorted(source_dir_path.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith("."):
            continue
        dest = plugin_dir / "references" if subdir.name == "references" \
               else skill_md_dir / subdir.name
        shutil.copytree(subdir, dest, dirs_exist_ok=True)  # dirs_exist_ok for idempotency
```

### Part D — Directory Consolidation (dual plugins/ + skills/)

When both `plugins/<category>/<name>/` and `skills/<name>/` exist:

```bash
for category in plugins/*/; do
  cat_name=$(basename "$category")
  for plugin in "$category"*/; do
    plugin_name=$(basename "$plugin")
    [ "$cat_name/$plugin_name" = "tooling/mnemosyne" ] && continue
    mkdir -p "skills/$cat_name"
    [ -d "skills/$cat_name/$plugin_name" ] && rm -rf "skills/$cat_name/$plugin_name"
    mv "$plugin" "skills/$cat_name/$plugin_name"
  done
  [ "$cat_name" != "tooling" ] && rmdir "$category" 2>/dev/null
done
```

Critical: detect in-place migrations (`target_dir == legacy_dir`) and skip file copies to avoid
`shutil.rmtree` deleting references before copy.

### Part E — Cross-Repo Generalization

```bash
# Find skills with repo-specific source field
grep -r "^source:" skills/ --include="*.md"

# Batch remove source lines
for file in skills/*.md; do
  sed -i '/^source: ProjectName$/d' "$file"
done
```

Replace hardcoded values with placeholders (longest patterns first):

| Placeholder | Replaces |
| ------------- | --------- |
| `<project-root>` | `/home/username/ProjectName/` |
| `<package-manager>` | `pixi run`, `npm run`, etc. |
| `<test-path>` | `tests/shared/core/` |
| `<pr-number>` | Embedded PR numbers in workflow text |

Add "Verified On" table to each generalized skill. Move project-specific details to `references/notes.md`.

### Part F — Post-Drain Closure Audit (Salvage Silently-Dropped Content)

After a mass PR drain closes PRs as "superseded" or folds them into a carrier PR, audit the
closures for silently-dropped unique content. Drain agents operate under time pressure and
**over-close**: approximately 26% of closed-not-merged PRs contain genuinely-lost content.
This audit is a mandatory companion step to every large drain pass.

**When to run**: Immediately after any drain session that closed ≥5 PRs as "superseded" without
merging them.

#### Quick Reference

```bash
# Step 1: Enumerate closed-not-merged PRs in the drain window
gh pr list --state closed \
  --search "closed:>=<ISO-date> -is:merged" \
  --json number,title,headRefName \
  --limit 200

# Step 2: Map each PR to its target skill file (exclude .history files)
gh pr diff <N> --name-only | grep '\.md$' | grep -v '\.history'

# Step 3: Check the current main state of a skill before auditing
git show origin/main:skills/<file>.md | head -5

# Step 4: Verify an ADD-new-skill PR's target actually exists on main
git show origin/main:skills/<file>.md 2>&1 | head -1
# If output starts with "fatal:" — the whole skill is LOST, highest priority salvage

# Step 5: Salvage — one amendment PR per skill-family
git checkout -b fix/salvage-<label> origin/main
# ... edit skills/<file>.md, bump version, append .history entry ...
git add skills/<file>.md skills/<file>.history
git commit -m "fix(salvage): restore dropped content in <skill> from closed PRs"
gh pr create --title "fix(salvage): restore <N> learnings in <skill>" \
  --body "..."
gh pr merge --auto --squash
```

#### Detailed Steps

**Step 1: Enumerate closed-not-merged PRs**

Query the drain window by ISO date. Use `closed:>=<ISO-date>` to bound the search to the
drain session's timeframe. Collect PR numbers, titles, and head branch names.

**Step 2: Map PRs to skill-family clusters**

For each closed PR, identify the single skill file it targets:

```bash
gh pr diff <N> --name-only | grep '\.md$' | grep -v '\.history'
```

Sort PRs by target skill file. PRs naturally cluster into skill-families (a skill targeted
by 14 sibling PRs is a single audit unit). Group before auditing — do NOT audit one PR at
a time in isolation.

**Step 3: Partition audit by skill-family**

Dispatch one analysis agent per skill-family cluster. Each agent:

1. Reads the CURRENT `origin/main` version of the skill file ONCE
2. Reviews every closed PR in its cluster against the current canonical
3. Verdicts each PR: **COVERED** (all unique content already on main), **PARTIAL** (some
   content missing — quote verbatim), or **LOST** (core learning entirely absent)

This partition pattern is far more efficient than one-agent-per-PR (which re-reads the same
canonical N times) and far more accurate (the agent sees exactly what main currently has).

**Step 4: Audit rules**

| Rule | Detail |
| ------ | ------- |
| Judge COVERED by content, NOT version number | A PR's "Phase 19" may land as "Phase 18b" in a carrier that used a lower version number; content match is what counts |
| Highest-risk closure type: ADD-new-skill PRs | If the PR was supposed to create a new skill and was closed as superseded, FIRST verify the target file exists on main (`git show origin/main:skills/<file>.md`). If it doesn't exist — the entire skill is LOST |
| Carriers absorb siblings — always audit siblings | A carrier PR that claims to fold N sibling learnings into one is the #1 source of silent loss; verify each sibling's content is actually present |
| Diff against CURRENT main, not merge-base | Other PRs may have merged between the drain and the audit, updating the canonical |

**Step 5: Salvage**

Group LOST/PARTIAL content by target skill-family. Create one amendment PR per skill (not
one per lost learning — fewer PRs reduces cascade churn). Each PR:

- Restores the missing content into the appropriate section (Failed Attempts, Verified
  Workflow, When to Use)
- Bumps the canonical's version above what is currently on main (MINOR bump)
- Appends a `.history` changelog entry noting what was restored and from which closed PRs
- Validates with `python3 scripts/validate_plugins.py` before pushing
- Arms `gh pr merge --auto --squash`

#### Observed Over-Close Rates

| Drain Session | Closed PRs Audited | Had Dropped Content | Over-Close Rate |
| -------------- | ------------------- | ------------------- | --------------- |
| 2026-06-14 myrmidon-merge-triage | 38 | 10 | 26% |

#### Carrier PR Risk Pattern

A "carrier" PR (one PR absorbing many siblings' content) is the highest-risk closure type.
Example: carrier PR #2346 jumped a skill v1.0.0→v1.9.0 while silently dropping 6 of the
14 sibling learnings it claimed to absorb. Always enumerate and check every sibling a
carrier claims to cover.

### Part G — Salvaging a Stranded Skill + Avoiding Accidental De-Consolidation

Two related hazards arise when skill work gets stranded outside the canonical clone and you
go to recover it: (1) trying to transplant git objects between clones, and (2) silently
REVERSING a prior consolidation by recreating a standalone skill that was deliberately merged
into a bundle.

#### G1 — Salvage skill work stranded in a stray/misplaced clone

A worktree on branch `skill/<name>` was found stranded INSIDE another repo's tree (e.g.
`ProjectHephaestus/build/.worktrees/`), backed by a misplaced second clone. It held
UNCOMMITTED skill work (a v1.3.0 amendment, 2 files) but ZERO unique commits — its branch tip
was already on `origin/main`. KEY INSIGHT: when a branch tip is already on `origin/main`, "the
commit to move" is really just the UNCOMMITTED working-tree delta. Recreate it as a fresh,
properly-based branch — do NOT try to transplant git objects between clones.

Safe salvage workflow:

```bash
# 1. Back up the uncommitted work FIRST, before touching anything.
git -C <stray-worktree> diff > /tmp/salvage-backup.patch
cp -r <stray-worktree>/skills/<changed-files> /tmp/salvage-files/   # full files too

# 2. Do NOT git-checkout branches in the shared canonical clone.
#    Create a fresh worktree off canonical origin/main.
git -C <canonical-clone> fetch origin
git -C <canonical-clone> worktree add /tmp/salvage-wt -b skill/<name>-salvage origin/main

# 3. Re-apply the salvaged files there, validate, commit signed in the CORRECT clone, push, PR.
cp /tmp/salvage-files/* /tmp/salvage-wt/skills/
python3 scripts/validate_plugins.py
git -C /tmp/salvage-wt commit -S -m "..."

# 4. Leave the stray clone UNTOUCHED for the human to remove separately.
#    The backup patch + files are the source of truth.
```

#### G2 — Check for prior consolidation BEFORE recreating any skill file

Reintroducing a deliberately-consolidated standalone skill silently DE-CONSOLIDATES it: it
duplicates the guidance in two places and partially reverses the merge. Worse, if auto-merge
is armed (`--squash`) and CI is instant, the PR can LAND before `gh pr merge --disable-auto`
can run — the de-consolidation is then live on main before you can catch it.

Before recreating/relocating ANY skill file, check whether it was previously consolidated or
removed:

```bash
# A deletion commit referencing "consolidate"/"superseded" is the signal it was merged away.
git log origin/main --oneline -- skills/<name>.md

# Confirm the content now lives in a bundle's history snapshot.
grep -rl "Superseded from <name>" skills/*.history
```

If it WAS consolidated: port the genuinely-new content INTO the bundle instead of recreating
the standalone. Do NOT arm `gh pr merge --auto --squash` on a salvage PR until a human
confirms the shape — instant CI can merge before you can disable auto-merge.

#### G3 — Fix-forward an accidental de-consolidation (never `git revert`)

If a standalone skill was already reintroduced on main (reversing a consolidation), do NOT
`git revert` the skill change. Open ONE follow-up PR that:

1. **Ports only the genuinely-new content into the consolidated bundle.** Verify each item is
   actually ABSENT from the bundle first (`grep` the bundle `.md` + `.history`); bump the
   bundle version MINOR.
2. **`git rm` the reintroduced standalone file(s)** — restoring the consolidation.
3. Validates with `python3 scripts/validate_plugins.py` before pushing.

Real incident: a salvaged v1.3.0 amendment was based on standalone
`squash-only-repo-merge-method-docs`, which an earlier PR (#2200) had DELIBERATELY consolidated
into bundle `github-auto-merge-ci-gating-merge-method`. Recreating the standalone (PR #2546)
reintroduced it on main and duplicated the guidance. It was reconciled in PR #2553: bundle
bumped to v1.4.0 with the genuinely-new content ported in, standalone re-deleted via `git rm`,
`validate_plugins.py` 396/396.

### Semver Rules for Skill Amendments

| Change Type | Bump | When |
| ------------- | ------ | ------ |
| Major (X.0.0) | `1.0.0` → `2.0.0` | Merge skills, rewrite workflow, change core recommendation |
| Minor (0.X.0) | `1.0.0` → `1.1.0` | Add findings, failed attempts, extend workflow |
| Patch (0.0.X) | `1.0.0` → `1.0.1` | Fix typos, formatting, metadata |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Direct merge without enumeration phase | Merge agent given 3 examples and told to discover the rest | Agent stalled or drifted scope — no definitive boundary | Always enumerate first; merge agents need a fixed manifest |
| Single agent enumerating all clusters | One agent iterated all 17 clusters sequentially | Cross-contamination: agent conflated keywords across adjacent clusters | One enumeration agent per cluster, fully isolated |
| Omitting protected meta-skill exclusions | Enumeration agents allowed to include any skill | Cluster absorbed and deleted its own tooling | Hard-code the protected list in every enumeration agent prompt |
| Skipping Gate 1 duplicate check | Manifests shipped directly to merge agents | Same skill appeared in two merge PRs, causing double-deletion | Gate 1 duplicate detection is mandatory before any merge launches |
| Parallel agents in same worktree conflicting | Launched 3 agents to merge 3 groups simultaneously | Worked fine — no conflicts since each agent writes different files | Parallel agents in a shared worktree work when they touch non-overlapping files |
| Major-only version bumps | Always bump X.0.0 for any amendment | Loses information about change scale | Use semver: Major for rewrites/merges, Minor for new findings, Patch for typos |
| Merging by exact text dedup | Deduplicated Failed Attempts by exact row match | Different skills describe the same lesson with different wording | Deduplicate by lesson/concept, not by exact text match |
| Forgetting .notes.md files | Deleted .md but forgot accompanying .notes.md | Orphaned .notes.md files clutter the skills directory | Always delete both .md and .notes.md when removing source skills |
| Summary-only history | Wrote brief summary per absorbed skill instead of full body | Lost ability to recover absorbed content without `git log` | Always paste the full original body verbatim |
| In-place amendment style for merge history | Used diff-only history format | Diffs are meaningless when the entire file is being deleted | Merges record absorbed bodies; amendments record what changed |
| Omitting frontmatter `history:` reference | Created .history but omitted `history:` in canonical .md | Validator rejected with "orphan history file" error | Always add `history:` to canonical frontmatter |
| Deleting with `rm` instead of `git rm` | Used shell `rm` to remove absorbed skill files | Files showed as unstaged deletions; not tracked in commit | Always use `git rm` so deletions are tracked |
| Stopping at 3 sub-skills when topic is OBSOLETE | Organized 12 skills into 3 well-structured sub-skills | When topic declared OBSOLETE, notice was fragmented across 3 files | When a topic is OBSOLETE, consolidate to 1 — notice is the dominant content |
| Assuming deduplication is durable | Merged cluster once, assumed stable | Subsequent `/learn` calls re-created duplicate skills organically | Schedule periodic re-consolidation passes |
| Reading all 975 skill files for detection | Tried to read every `.md` to find duplicates | Extremely slow; times out and wastes context | Use `marketplace.json` (names + descriptions) — no file reads needed for detection |
| Committing directly to main | Made dedup commits on main branch | Bypasses PR review process | Always use a feature branch via git worktree |
| Planning merges without checking file existence | Identified 42 groups, started merging | Many files already merged in prior sessions | Always `ls skills/<name>.md` before attempting to read or merge |
| Running second-pass without existing-canonicals list | Documentation-shard agent proposed clusters already existing as M16/M17 canonicals | 27 members had to be re-routed at gate stage | Always pass existing-canonicals list + require two-bucket output |
| Migration script copying only SKILL.md | `migrate_skill()` only wrote `.claude-plugin/plugin.json` + `SKILL.md` | Subdirs (`scripts/`, `templates/`) were silently dropped | Iterate `source_skill_md.parent` for all subdirs; copy with `shutil.copytree(..., dirs_exist_ok=True)` |
| `shutil.copytree` without `dirs_exist_ok` | Called `copytree(src, dest)` | `FileExistsError` on second migration run | Always use `dirs_exist_ok=True` for idempotent behavior |
| Placing `references/` alongside SKILL.md | `references/` inside `skills/<name>/` | Mnemosyne convention puts `references/` at plugin root | Check plugin layout spec before routing subdirs |
| In-place migration calling `shutil.rmtree` | Deleted refs before copying (src == dest) | Deleted the file being copied | Detect `target_dir == legacy_dir` and skip file copies |
| Assumed SKILL.md needed full rewrite | Expected old format without frontmatter | All 4 legacy files already had YAML frontmatter | Check SKILL.md content before assuming full rewrite needed |
| Forgot `version` field after copying SKILL.md | Copied SKILL.md without checking required fields | 3 of 4 were missing `version: "1.0.0"` and failed validation | Always verify all required frontmatter fields after copy |
| Bulk removing `source:` without checking URL sources | Removed all `^source:` lines | Removed legitimate `source: https://...` references | Keep URL sources; only remove project-name sources (`source: ProjectName`) |
| Gate 1 only checked absorbed-vs-absorbed | Ran only `jq '.absorbed_skills[]' \| sort \| uniq -d` | `markdown-linting-and-build-fixes` was a canonical of one cluster yet listed as an absorbed skill in the mkdocs cluster; the merge folded/deleted it → wrong-merge + a redundant PR that had to be closed and redirected after merge | Gate 1 must ALSO check canonical-vs-absorbed: flag any cluster whose `canonical_name` appears in another cluster's `absorbed_skills` (Gate 1b) |
| Committing before running pre-commit | Let the first `git commit` trigger the hooks | `end-of-file-fixer` modified the `.history` file during commit, aborting it; the branch was pushed with no commit and an empty PR number, forcing a manual retry | Run `pre-commit run --files <canonical>.md <canonical>.history` once, `git add -A skills/` again, THEN commit |
| Re-dispatching merge agent by agent ID during recovery | Re-launched an agent for a cluster believed dead, keyed off the background-task notification ID | Two agents both ran `skill/ruff-specific-rule-fixes`, producing duplicate PRs #2233 + #2234; notification IDs had been reshuffled/mislabeled | Track cluster progress from git/gh state (`git ls-remote --heads`, `gh pr list --head`), never from agent/background-task IDs; only re-dispatch when both are empty |
| Relying on update-marketplace.yml to refresh the index | Expected the workflow to keep `marketplace.json` current post-consolidation | Workflow regenerates the file but FAILS at "Open PR" — org policy blocks GitHub Actions from creating PRs; `marketplace.json` silently went stale | Regenerate manually in a dedicated PR (`python3 scripts/generate_marketplace.py` → commit → PR) as the final reconcile step of every pass |
| Trusting drain-agent close-as-superseded verdicts without a follow-up audit | Accepted every "closed as superseded" and "folded into carrier" decision from the drain pass without reviewing the closed PRs | 10 of 38 closed PRs (26%) had content that was not on main — including 6 learnings silently dropped from a single carrier PR that claimed to absorb 14 siblings | Always run a post-drain closure audit; over-close rates of ~26% are normal under time pressure |
| One-agent-per-closed-PR audit | Dispatched one agent per closed PR to compare it against main | Each agent re-read the same canonical skill file independently — N agents for N PRs targeting one skill all re-fetched the same file, wasting context and producing inconsistent verdicts | Partition the audit by skill-family; one agent per cluster reads the canonical ONCE then checks all N sibling PRs against it |
| Judging COVERED by matching version numbers | Checked if the PR's version number was lower than the current canonical version | A v1.4.0 PR's content can be fully present in a v1.13.0 canonical under renumbered phases and sections — version number comparison produces false "COVERED" verdicts | Judge COVERED by content presence, not by version number comparison |
| Assuming a closed ADD-new-skill PR is safe because a related merged PR exists | Saw that a related PR had merged and concluded the new-skill content was absorbed | The specific target file may not exist on main if the carrier PR used a different filename or dropped the skill creation entirely | Always `git show origin/main:skills/<file>.md` to verify the exact target file exists before concluding an ADD-new-skill closure is covered |
| Transplanting a stranded commit between clones + arming auto-merge on a salvage PR | Tried to move a "stranded" skill commit from a misplaced clone into canonical; armed `gh pr merge --auto --squash` on the salvage PR | The stranded branch tip was already on `origin/main` — the only real delta was the UNCOMMITTED working tree, so there was no git object to transplant; and instant CI fired auto-merge before `gh pr merge --disable-auto` could run, landing the PR before its shape could be reviewed | Back up the uncommitted delta FIRST, recreate as a fresh branch off canonical `origin/main`, and do NOT arm auto-merge on a salvage PR until a human confirms the shape |
| Recreating a consolidated skill as a standalone | Salvaged a v1.3.0 amendment by recreating standalone `squash-only-repo-merge-method-docs` | That skill had been DELIBERATELY consolidated into bundle `github-auto-merge-ci-gating-merge-method` (PR #2200); recreating it silently DE-CONSOLIDATED it, duplicating the guidance in two places and partially reversing the merge (PR #2546) | Before recreating/relocating any skill, check `git log origin/main --oneline -- skills/<name>.md` for a "consolidate"/"superseded" deletion and grep bundle `.history` for "Superseded from <name>"; if consolidated, port new content INTO the bundle and `git rm` the standalone — fix-forward, never `git revert` (reconciled in PR #2553) |

## Results & Parameters

### Deduplication Scale Examples

| Session | Skills Before | Skills After | Net Reduction | Method |
| --------- | -------------- | ------------ | -------------- | -------- |
| test-splitting cluster | 16 | 3 | -13 (-81%) | Prefix grouping |
| mojo-test-* cluster | 10 | 1 | -9 (-90%) | Prefix grouping |
| deprecated-file-cleanup-* | 6 | 1 | -5 (-83%) | Prefix grouping |
| conv2d-gradient-* cluster | 9 | 3 | -6 (-67%) | Topic sub-grouping |
| Large-scale algorithmic pass | 975 | 933 | -42 (-4.3%) | marketplace.json + SequenceMatcher |
| Full-corpus pass (2026-06-07) | 518 | 291 | -227 (-44%) | 50-cluster manifest-first; 10 waves of <=5 worktree swarm agents |

### Algorithmic Detection Parameters

```python
threshold = 0.80  # >80% SequenceMatcher ratio = near-duplicate
prefix_min_cluster_size = 3  # min skills sharing prefix to flag as cluster
cap_absorbed_skills = 100    # overflow_warning: true above this
```

### Bulk Migration Script Parameters

| Parameter | Default | Description |
| ----------- | --------- | ------------- |
| `--dry-run` | false | Show planned actions without creating files |
| `--skill NAME` | all | Migrate only a specific skill by name |
| `--force` | false | Overwrite skills that already exist |
| `--skip-existing` | true | Skip skills already present (idempotency guard) |

### Category Mapping (bulk migration from legacy source)

| Source Category | Mnemosyne Category |
| --- | --- |
| `github`, `worktree`, `agent`, `plan`, `generation` | `tooling` |
| `ci`, `phase` | `ci-cd` |
| `mojo` | `architecture` |
| `doc` | `documentation` |
| `quality`, `review` | `evaluation` |
| `testing` | `testing` |
| `analysis`, `ml` | `optimization` |
| `training` | `training` |

### Validation Commands

```bash
python3 scripts/validate_plugins.py
npx markdownlint-cli2 skills/*.md

# Grep audit for absorbed skills in history files
grep -h "### Superseded from" skills/*.history | sort

# Confirm no legacy nested skills remain
find skills/ -type d -mindepth 1
```

### Reconcile marketplace.json MANUALLY after a consolidation pass

The `update-marketplace.yml` workflow is **broken** and cannot keep `marketplace.json` fresh.
It regenerates the file but FAILS at its "Open PR" step because org policy blocks GitHub Actions
from opening PRs ("GitHub Actions is not permitted to create or approve pull requests"). So after
a consolidation pass, `marketplace.json` goes stale and must be regenerated by hand in its own PR:

```bash
python3 scripts/generate_marketplace.py
git add marketplace.json .claude-plugin/marketplace.json 2>/dev/null
git commit -m "chore: regenerate marketplace.json after consolidation pass"
gh pr create --fill && gh pr merge <#> --auto --squash
```

Do this as a final reconcile step of every consolidation pass — do not rely on the workflow.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectMnemosyne | PR #1040, merged 16 test-splitting skills + added semver | 2026-03-25 |
| ProjectMnemosyne | PR #1075–#1097, six deduplication rounds | 2026-03-27 to 2026-03-28 |
| ProjectMnemosyne | Large-scale algorithmic pass: 975 → 933 skills (-42) | 2026-04-07 |
| ProjectMnemosyne | PR #183, dual plugins/+skills/ → single skills/ (971 files changed) | 2026-02-23 |
| ProjectMnemosyne | PR #326, bulk migration of 4 worktree skills from ProjectOdyssey2 | 2026-03-04 |
| ProjectMnemosyne | PR #1017, migrated last 4 hierarchical skills to flat format | 2026-03-25 |
| ProjectMnemosyne | 20 merge PRs using history-as-superseded-snapshot pattern | 2026-05-18 |
| ProjectMnemosyne | 17-cluster 1100-skill consolidation with manifest-first enumeration | 2026-05-19 |
| ProjectMnemosyne | 2026-06-07 full-corpus pass: 50 clusters, 273 skills -> 50 canonicals, 10 waves of <=5 worktree swarm agents | corpus 518 -> 291 (-227, -44%) |
| ProjectMnemosyne | 2026-06-14 post-drain closure audit: 38 closed PRs audited via 4-agent swarm partitioned by skill-family; 10 had dropped content (26%); salvaged via 5 amendment PRs (#2514-#2518, all merged) | verified-ci |
| ProjectMnemosyne | 2026-06-15 stranded-skill salvage + accidental de-consolidation reconcile: recovered uncommitted v1.3.0 work from a misplaced clone, but recreating standalone `squash-only-repo-merge-method-docs` (PR #2546) de-consolidated it from bundle `github-auto-merge-ci-gating-merge-method`; fixed forward in PR #2553 (bundle → v1.4.0, standalone re-deleted, validate_plugins.py 396/396) | verified-ci |
