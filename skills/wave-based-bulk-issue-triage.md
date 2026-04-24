---
name: wave-based-bulk-issue-triage
description: "Fix 5+ independent GitHub issues in parallel waves using Task isolation:worktree.\
  \ No manual worktree setup \u2014 Claude Code auto-manages isolation. Also covers\
  \ bulk gh issue create via myrmidon swarm (plain Agent calls, no worktrees needed).\
  \ Includes pre-fix classification phase using parallel Explore agents."
category: architecture
date: 2026-04-23
version: 1.3.0
user-invocable: false
verification: verified-local
history: wave-based-bulk-issue-triage.history
---
# Skill: Wave-Based Bulk Issue Triage

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-22 |
| **Objective** | Fix 8 GitHub issues (2 waves × 4 PRs) — simple fixes + test additions |
| **Outcome** | ✅ Success — 8 PRs created in parallel, auto-merge enabled |
| **Key Innovation** | `Task(isolation="worktree")` — zero manual worktree management |

## When to Use

Use this skill when:

1. **Backlog of 5+ independent issues** to clear in one session
2. **Issues fall into categories** — e.g., simple doc/config fixes vs. test additions
3. **Issues modify different files** — no shared file conflicts
4. **Want maximum parallelism** with minimal orchestration overhead
5. **Filing 10+ GitHub issues from an audit or walkthrough report** — use myrmidon swarm (plain Agent calls, no worktrees needed)
6. **Large backlog (20+ issues) requiring classification first** — run parallel Explore agents before fix waves

**Don't use when:**
- Issues depend on each other (use sequential PRs)
- Any issue touches 20+ files (exclude from wave, file separately)
- Issues share modified files (risk of merge conflicts)

## Verified Workflow

### Phase 0: Pre-Classification (NEW — for 20+ issue backlogs)

Before running fix waves on a large backlog, classify all issues using **3 parallel Explore agents** — one per batch of ~22 issues. Do this before any fix work.

**Pre-classification exclusions**: Always skip epic/tracking issues (labeled `epic`), blocked issues (labeled `blocked`), and audit summary issues before dispatching classifier agents.

**Dispatcher prompt per classifier agent:**

```
You are classifying GitHub issues for bulk triage.

Run 1: gh issue list --repo ORG/REPO --state open --limit 100 --json number,title,labels
       to get the full list, then for each issue in your assigned range:

Run 2: gh issue view <N> --repo ORG/REPO

Classify each issue LOW / MEDIUM / HIGH / N/A:
- LOW: single-file change, <50 lines, no architectural impact
- MEDIUM: 2-5 files, module interaction understanding required
- HIGH: 6+ files, architectural decisions, or blocked by other work
- N/A: epic/tracking/blocked issues — skip entirely

Return a markdown table:
| #N | Title | LOW/MEDIUM/HIGH/N/A | one-sentence rationale |

Your batch: issues #NNNN through #MMMM
```

Launch all 3 classifier agents in a single message (parallel), wait for all 3 to return, then collate the tables before proceeding to fix waves.

**Why Explore not Haiku**: Classification requires reading issue context and judging scope — it is not mechanical enough for Haiku. Use Explore (Sonnet-class) agents.

### Phase 1: Triage & Wave Planning

Group classified LOW issues by **fix type** for maximum parallelism and minimum CI queue time:

```
Wave A — Documentation-only fixes (fastest, no compilation):
  - Markdown corrections, broken links, outdated paths
  - Comment and docstring updates

Wave B — Config/cleanup fixes (YAML, Dockerfile, pixi.toml changes):
  - Dependency version bumps
  - CI workflow corrections
  - Configuration file cleanups

Wave C — Simple code fixes (single-file, import removal, small bugs):
  - Unused import removal
  - Single-function bugfixes
  - Type annotation fixes

Wave D — Test additions and minor enhancements:
  - New test classes for untested methods
  - Integration test roundtrips
  - Multi-method test coverage

Excluded — Too complex for bulk:
  - MEDIUM or HIGH complexity issues (fix individually)
  - 20+ file changes
  - Cross-repo changes
  - Architectural refactors
```

**Key decision:** Run waves in A → B → C → D order. Wave A PRs often merge before Wave D even starts, minimizing CI queue contention.

### Phase 2: Launch Parallel Agents (One Wave at a Time)

Use `Task` tool with `isolation: "worktree"` — **no manual worktree setup needed**:

```python
# Launch all Wave A agents in parallel (single message, multiple Task calls)
Task(
    subagent_type="Bash",
    model="haiku",            # ← CRITICAL: use Haiku for mechanical tasks to prevent plan-mode stalling
    isolation="worktree",     # ← Claude Code auto-creates isolated worktree
    description="Fix #NNN brief-description",
    prompt="""
IMPORTANT: DO NOT PLAN. EXECUTE IMMEDIATELY.

1. Run: cat path/to/file
2. Run: [make the specific edit]
3. Run: pre-commit run --files <changed-files>
4. Run: pixi run python -m pytest <specific-test-file> -q --no-cov
5. Run: git checkout -b NNN-slug
6. Run: git add path/to/changed/file
7. Run: git commit -m "type(scope): description (Closes #NNN)"
8. Run: git push -u origin NNN-slug
9. Run: gh pr create --title "..." --body "Closes #NNN"
10. Run: gh pr merge --auto --rebase
    """
)
```

**Agent Plan-Mode Avoidance**: Agents with `isolation="worktree"` often stop to present plans
instead of executing. To prevent this:

1. Use `model="haiku"` for mechanical fixes — Haiku over-plans far less than Sonnet
2. Phrase every step as an explicit `Run:` command, never as a description
3. Start the prompt with `IMPORTANT: DO NOT PLAN. EXECUTE IMMEDIATELY.`
4. For stubborn cases: rewrite the entire prompt in imperative command form with no "Steps:", no
   "Plan:", only numbered `Run:` commands

What does NOT work:
- Repeating "complete all steps end-to-end" — agents ignore it
- "Do NOT stop and ask for help" — same agents still stop
- SendMessage continuation is not available in isolation=worktree — each agent launch is independent

Wait for Wave A to complete, then launch Wave B agents the same way.

### Phase 3: Verify

After all agents return:

```bash
gh pr list --author "@me" --state open
```

**CRITICAL — Always verify PR numbers from `gh pr list`, never from agent output**: Two parallel agents working in the same repo can both report creating "PR #120" when they actually created different PRs. The agent-reported number is stale. Use `gh pr list` as the ground truth after every wave.

Check each PR has:
- ✅ Auto-merge enabled
- ✅ CI queued or passing

### Prompt Template for Bash Agent (Imperative Form — Required for Haiku)

```
IMPORTANT: DO NOT PLAN. EXECUTE IMMEDIATELY.

1. Run: cat path/to/file
2. Run: [exact edit — e.g., "remove line 42", "change X to Y"]
3. Run: pre-commit run --files path/to/changed/file
4. Run: pixi run python -m pytest tests/path/to/test.py -q --no-cov
5. Run: git checkout -b NNN-slug
6. Run: git add path/to/changed/file
7. Run: git commit -m "type(scope): description (Closes #NNN)"
8. Run: git push -u origin NNN-slug
9. Run: gh pr create --title "type(scope): description" --body "Closes #NNN"
10. Run: gh pr merge --auto --rebase

Never use git add -A or git add .
Never use --no-verify
```

**Why imperative form**: Descriptive step phrasing ("Make the fix", "Run the tests") triggers
planning behavior in isolated agents. Explicit `Run:` commands with concrete shell invocations
bypass the planning reflex.

## Overview

| Field | Value |
|-------|-------|
| **Date** | YYYY-MM-DD |
| **Objective** | Skill objective |
| **Outcome** | Success/Operational |

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked for code-fix waves | N/A | Solution was straightforward |
| Body quoting (2026-04-06) | Single-quoted `--body '...'` strings with apostrophes/single quotes embedded | Shell interprets `'` inside `'...'` as end of string, breaking the command | Use `--body-file /tmp/issue-body.md` for any body containing single quotes or apostrophes |
| Plan-mode text (2026-04-11) | Adding "complete all steps end-to-end" and "Do NOT stop and ask for help" to Sonnet agents with `isolation="worktree"` | Agents ignored these instructions and still paused to present plans | Use Haiku model + imperative `Run:` command form; Haiku over-plans far less than Sonnet |
| Descriptive step phrasing (2026-04-11) | Writing agent prompts with "Steps:", descriptive phrases like "Make the fix", "Run the tests" | Context-heavy descriptive prompts trigger Sonnet's planning reflex — agents present a plan and stop | Rewrite prompts as explicit `Run: <shell command>` lines with no "Steps:" or "Plan:" sections |
| PR number collision from parallel agents (2026-04-23) | Two parallel agents working in HomericIntelligence/Odysseus both reported creating "PR #120" — treated as the ground-truth PR number | Agents report their own in-flight view of PR creation results; when two agents race to create PRs in the same repo the numbers can collide or be stale in the agent's output | Always run `gh pr list --author "@me" --state all` after each wave to get ground-truth PR numbers — never trust agent-reported PR numbers |
## Results & Parameters

### Myrmidon Swarm Pattern for Bulk Issue Filing (2026-04-06)

When filing 10+ `gh issue create` calls (e.g., from a walkthrough or audit report), use the **myrmidon swarm** (plain Agent calls) instead of `Task(isolation="worktree")`. No file modifications means no worktrees needed.

**Pattern:**

```
Wave 1 (≤5 Haiku agents in parallel):
  Agent 1: gh issue create --repo ORG/REPO --title "..." --label "..." --body-file /tmp/issue-1.md
  Agent 2: gh issue create --repo ORG/REPO --title "..." --label "..." --body-file /tmp/issue-2.md
  ...

Wave 2 (≤5 Haiku agents):
  ...

Wave 3 (remainder):
  ...
```

**Rules:**
1. Each agent gets exactly one `gh issue create` command
2. Multi-line or apostrophe-containing bodies: write to a temp file first, then pass `--body-file /tmp/issue-N.md`
3. Labels: pass multiple `--label` flags (one per label), **not** comma-separated in a single flag
4. Wave limit: **≤5 agents per wave** to prevent GitHub API rate limiting
5. Model tier: **Haiku** — fully-specified `gh issue create` calls require no design decisions
6. No worktrees needed since no repository files are modified

**Verified performance:** 11 issues filed in ~30 seconds total (3 waves: 5+5+1 agents) on HomericIntelligence/Odysseus (issues #99–109, 2026-04-06).

#### Body-File Pattern for Complex Issue Bodies

```bash
# In each agent's prompt:
cat > /tmp/issue-body.md << 'EOF'
## Summary
...content with 'single quotes' and apostrophes freely...

## Steps to Reproduce
...
EOF
gh issue create \
  --repo ORG/REPO \
  --title "Issue title" \
  --label "bug" \
  --label "priority:high" \
  --body-file /tmp/issue-body.md
```

### Session Results (2026-04-11) — ProjectOdyssey 66-Issue Classification + 28-Issue Fix

**Context**: 66 GitHub issues classified using 3 parallel Explore agents (~22 issues each),
followed by 28 LOW-complexity issues fixed across 4 fix-type waves.

| Wave | Fix Type | Issues Fixed | PRs Created |
|------|----------|--------------|-------------|
| A | Documentation-only | 7 | 7 |
| B | Config/cleanup | 8 | 8 |
| C | Simple code fixes | 8 | 8 |
| D | Test additions | 5 | 5 |

**Total**: 66 issues classified, 28 fixed, 28 PRs created, ~3 hours wall clock

**CI Note**: All 19 of the first-batch PRs failed CI with `mojo: error: execution crashed` in
`libKGENCompilerRTShared.so`. This is the known Mojo 0.26.x JIT flake — zero real code errors
across all 28 PRs. Pattern: if **all** jobs fail with the same `execution crashed` pattern, it
is a JIT flake, not a code error. Retry CI or wait for re-run.

### CI JIT Crash Identification Heuristic (Reconfirmed 2026-04-11)

When triaging CI failures after bulk PRs:

1. Check if **all** failing jobs show the same `mojo: error: execution crashed` message
2. Check if the crash is in `libKGENCompilerRTShared.so` (the Mojo JIT runtime library)
3. If both are true: it is a JIT flake, not a code error — re-run CI, do not investigate code

```
# Flake pattern (safe to re-run):
mojo: error: execution crashed
  in libKGENCompilerRTShared.so

# Real error pattern (investigate code):
error: use of uninitialized variable
error: cannot implicitly convert
FAILED: tests/...
```

**Verified**: 19/28 PRs on ProjectOdyssey showed this exact pattern on 2026-04-11, with zero
actual code defects. All fixed in subsequent CI re-runs.

### Session Results (2026-02-22)

| Wave | Issue | Fix Type | PR | Tests Added |
|------|-------|----------|----|-------------|
| 6a | #930 | Add test method to existing class | #1051 | 1 |
| 6b | #959 | Update 3 phantom doc paths | #1052 | 0 |
| 6c | #920 | 1-char .gitignore fix | #1053 | 0 |
| 6d | #1042 | New filter_audit.py script + pixi.toml update | #1055 | 0 |
| 7a | #985 | 8 tests for _move_to_failed + _commit_test_config | #1056 | 8 |
| 7b | #986 | 5 tests for _run_subtest_in_process_safe | #1057 | 5 |
| 7c | #987 | 6 tests for CursesUI._refresh_display | #1058 | 6 |
| 7d | #898 | 3 integration tests for --update roundtrip | #1059 | 3 |

**Total**: 8 PRs, 23 new tests, ~2 minutes wall clock per wave

### Wave Sizing Guidelines

| Wave Size | Agents | Expected Duration |
|-----------|--------|-------------------|
| 2-3 issues | 2-3 parallel | ~1-2 min |
| 4-5 issues | 4-5 parallel | ~2-5 min |
| 6+ issues | Split into sub-waves | Varies |

### Issue Complexity Thresholds

| Category | Fits in Wave? | Notes |
|----------|--------------|-------|
| 1-char config fix | ✅ Yes | Simplest possible |
| Add 1 test method | ✅ Yes | 15-30 lines |
| Add new test class (5-8 tests) | ✅ Yes | Wave B material |
| Update 2-3 doc files | ✅ Yes | Quick |
| New script + config update | ✅ Yes | borderline, but ok |
| 20+ file changes | ❌ No | Exclude, file separate issue |
| Cross-repo changes | ❌ No | Exclude, handle manually |

### Exclusion Criteria (Skip for Now)

Add a comment in the plan when excluding:
```
### Excluded from Wave N
- **#NNN** (brief reason) — [specific reason]. Skip for now.
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| ProjectScylla | Wave 6+7, PRs #1051-#1059 | [notes.md](references/notes.md) |
| HomericIntelligence/Odysseus | Bulk issue filing, issues #99-#109 (2026-04-06) | 11 issues, 3 waves (5+5+1 Haiku agents), ~30s total |
| HomericIntelligence/ProjectOdyssey | 66-issue classification + 28-issue fix (2026-04-11) | 3 parallel Explore classifiers, 4 fix-type waves, 28 PRs created |
| HomericIntelligence/Odysseus | 35-issue triage, 19 resolved (2026-04-23) | Meta-repo with 12 submodule symlinks; parallel agents reported colliding PR numbers — verified with `gh pr list` after each wave |
