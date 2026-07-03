---
name: review-coordination-parallel-serial-subagent-dispatch
description: "Use when: (1) coordinating multiple sub-agents to fix GitHub PR review inline comments in parallel, (2) a PR has 3+ review threads and you need to avoid file collisions and race conditions, (3) you want to dispatch agents by difficulty tier (simple→Haiku, medium→Sonnet, hard→Opus), (4) review threads touch the same file and must be fixed sequentially to avoid concurrent edits, (5) review threads touch different files and can be fixed in parallel for speed, (6) you need to group review threads by file, sort by difficulty, and dispatch with model-tier routing, (7) fixing a PR review requires invoking /hephaestus:advise per sub-agent for domain knowledge before applying fixes, (8) after sub-agent fixes, you need to coordinate formatting, compilation, and commit creation, (9) sub-agent replies must be aggregated with thread_id and one-liner summaries for verification."
category: ci-cd
date: 2026-07-03
version: "1.0.0"
user-invocable: false
history: null
tags:
  - github-pr-review
  - parallel-dispatch
  - serial-coordination
  - file-grouping
  - model-tier
  - sub-agent
  - haiku
  - sonnet
  - opus
  - review-thread
  - inline-comment
  - fix-coordination
  - domain-knowledge
  - hephaestus-advise
  - thread-aggregation
  - file-collision
  - same-file-serialization
  - different-file-parallelization
  - difficulty-based-routing
  - backward-pass
  - ml-implementation
---

# Review Coordination: Parallel-Serial Sub-Agent Dispatch

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2026-07-03 |
| **Objective** | Coordinate multiple specialized sub-agents to fix GitHub PR review inline comments in parallel, avoiding file collisions through file-based serialization, routing tasks to model tiers by difficulty, and aggregating results for verification. |
| **Outcome** | Verified on PR #5538 (issue #5515): four critical backward-pass bugs fixed in ResNet-18 CIFAR-10 training implementation. Package compiled with `--Werror`, all fixes passed human review, commit cb3deb5c landed clean. |
| **Verification** | verified-local |
| **Version** | 1.0.0 |

## When to Use

- A PR has 3+ inline review comments that need fixes
- Review threads are independent and touch different files (parallelize)
- Review threads are in the same file (serialize to avoid concurrent edits)
- You need to avoid race conditions on same-file edits by multiple agents
- Sub-agents need domain knowledge (`/hephaestus:advise`) before fixing code
- You want to route tasks by difficulty: simple fixes → Haiku, medium → Sonnet, hard → Opus
- Fixes require compilation or formatting verification after applying changes
- You need aggregated results (thread_id, one-liner, verification) before committing

## Verified Workflow

### Phase 1: Parse Review Threads

Read the PR review threads and extract:
- `thread_id`: GitHub comment ID
- `file`: path to file being reviewed
- `line`: line number (if applicable)
- `comment_text`: the review feedback
- `difficulty`: estimate (simple/medium/hard) based on:
  - Simple: data type change, off-by-one fix, variable rename (15 min, Haiku)
  - Medium: logic fix requiring test understanding, API change (45 min, Sonnet)
  - Hard: architectural change, deletion of large blocks, refactoring (2+ hours, Opus)

**Extraction Pattern**:
```bash
# Read PR review threads
gh pr view <pr-number> --json reviews

# Parse output to extract thread_id, file, line, comment_text, difficulty
# Group by file
```

### Phase 2: Group by File and Detect Serialization Requirement

**Grouping Rules**:
1. Group all threads by `file`
2. If a file has >1 thread:
   - Mark for **sequential dispatch** (same sub-agent or chained sub-agents)
   - Threads in same file must be fixed by the same agent in a single run to avoid edit race conditions
3. If each thread has a unique file:
   - Mark for **parallel dispatch** (different agents, independent execution)

**Result Structure**:
```json
{
  "sequential_groups": [
    {
      "file": "src/resnet18_impl.mojo",
      "threads": [
        {"thread_id": "c1", "line": 120, "difficulty": "simple"},
        {"thread_id": "c2", "line": 240, "difficulty": "hard"}
      ]
    }
  ],
  "parallel_groups": [
    {
      "file": "src/backward.mojo",
      "threads": [{"thread_id": "c3", "line": 50, "difficulty": "medium"}]
    }
  ]
}
```

### Phase 3: Route by Difficulty and Create Dispatch Plan

**Difficulty Tiers**:
- **Simple (Haiku)**: off-by-one, type change, variable rename, small logic fix (≤1 file, ≤50 lines)
- **Medium (Sonnet)**: logic fix, API change, feature addition (≤3 files, ≤200 lines)
- **Hard (Opus)**: architectural refactoring, deletion of major blocks (>3 files or >200 lines)

**Dispatch Rules**:
1. **Sequential groups**: Always dispatch to ONE agent (create a composite prompt with all threads for that file)
2. **Parallel groups**: Dispatch different files to different agents (by difficulty tier)
3. **Async execution**: Launch all agents in parallel (Bash `run_in_background: true`)
4. **Wait for all to complete**: Collect results before formatting/compiling

**Dispatch Prompt Template**:
```
You are fixing GitHub PR review comments. Your task:

1. Invoke /hephaestus:advise to search team knowledge for domain context on [DOMAIN]
2. Read the file(s) at [PATHS]
3. For each review thread below:
   - Thread #[THREAD_ID]: [COMMENT_TEXT]
   - Apply the fix on line [LINE]
   - Verify the fix makes sense in context
4. Reply with:
   - thread_id: [THREAD_ID]
   - summary: [ONE-LINER: what you fixed]
   - verification: [BRIEF CONFIRM IT COMPILES/PASSES TEST]
```

### Phase 4: Invoke Sub-Agents

**For Sequential Groups** (same file):
```bash
# Create ONE agent dispatch with all threads for this file
# Prompt includes: /hephaestus:advise + all threads in one call
Agent(
  description: "Fix [N] review comments in [filename]",
  prompt: "Domain: [context]. Threads: [all thread IDs for this file]. ...",
  run_in_background: true
)
```

**For Parallel Groups** (different files):
```bash
# Create N independent agent dispatches
Agent(description: "Fix review comment [thread_id] in [filename]", ...)  # Haiku/simple
Agent(description: "Fix review comment [thread_id] in [filename]", ...)  # Sonnet/medium
Agent(description: "Fix review comment [thread_id] in [filename]", ...)  # Opus/hard
# All run in parallel
```

### Phase 5: Aggregate Results

After all agents complete, collect results in a table:

| Thread ID | File | Summary | Verification | Status |
|-----------|------|---------|--------------|--------|
| c1 | backward.mojo | Changed `fwd.gap` → `fwd.s4b2_cache.block_out` for correct gradient shape | Compiles ✓ | Fixed |
| c2 | backward.mojo | Changed `fwd.relu1_out` → `fwd.bn1_pre_relu` for correct ReLU mask | Compiles ✓ | Fixed |
| c3 | train.mojo | Changed integer labels `(4,)` → one-hot labels `(4, 10)` for cross_entropy | Tests pass ✓ | Fixed |
| c4 | backward.mojo | Deleted 48-line BN stats revert block that froze running mean/var | Compiles ✓ | Fixed |

### Phase 6: Verify, Format, and Commit

1. **Verify compilation**: `pixi run mojo build` or `just build`
2. **Verify formatting**: `mojo format --check` (should be clean)
3. **Verify tests**: If applicable, run relevant test suite
4. **Commit**:
   ```bash
   git add <files>
   git commit -m "$(cat <<'EOF'
   fix(module): Address [N] critical review comments

   - Thread c1: [fix summary]
   - Thread c2: [fix summary]
   - Thread c3: [fix summary]
   - Thread c4: [fix summary]

   All fixes verified to compile with --Werror.

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

## Real Example: PR #5538 (ResNet-18 Backward Pass)

### Parsed Threads

| Thread ID | File | Line | Comment | Difficulty |
|-----------|------|------|---------|------------|
| c1 | resnet18_backward.mojo | 120 | avgpool2d_backward receives output instead of input; should use `fwd.s4b2_cache.block_out` not `fwd.gap` | Simple |
| c2 | resnet18_backward.mojo | 240 | relu_backward masks on output; should mask on input `fwd.bn1_pre_relu` not `fwd.relu1_out` | Simple |
| c3 | resnet18_impl.mojo | 380 | cross_entropy requires logits.shape() == targets.shape(); tests pass one-hot labels `(4, 10)` not integers `(4,)` | Medium |
| c4 | resnet18_backward.mojo | 500 | Deferred BN write-back block reverts running stats to pre-forward snapshots; delete 48 lines | Hard |

### Grouping

**Sequential Group 1** (resnet18_backward.mojo):
- c1, c2, c4 all in same file → dispatch ONE agent for all three

**Parallel Group 1** (resnet18_impl.mojo):
- c3 in different file → dispatch separate agent

### Dispatch

```
Agent 1 (Opus, hard + simple = Hard group):
  "Fix 3 review comments in resnet18_backward.mojo: avgpool2d input tensor (c1), relu mask input (c2), deferred BN deletion (c4)"

Agent 2 (Sonnet, medium):
  "Fix 1 review comment in resnet18_impl.mojo: test label one-hot conversion (c3)"
```

### Results

| Thread ID | File | Summary | Verification |
|-----------|------|---------|--------------|
| c1 | resnet18_backward.mojo | Changed `fwd.gap` → `fwd.s4b2_cache.block_out` | `mojo build` ✓ |
| c2 | resnet18_backward.mojo | Changed `fwd.relu1_out` → `fwd.bn1_pre_relu` | `mojo build` ✓ |
| c3 | resnet18_impl.mojo | One-hot label conversion from integers `(4,)` to `(4, 10)` | `mojo test` ✓ |
| c4 | resnet18_backward.mojo | Deleted 48-line stats revert block | `mojo build` ✓ |

**Commit**: cb3deb5c ✓

## Failed Attempts (Anti-Patterns)

| Attempt | Problem | Why Failed | Resolution |
|---------|---------|-----------|------------|
| Dispatch all 4 threads in parallel without grouping | Multiple agents edited same file (`resnet18_backward.mojo`) concurrently | Race condition: agents #1 and #4 both tried to edit lines 120 and 500, rebase conflicts on second push | Group by file first; serialize same-file edits |
| Dispatch one sub-agent per thread, all in parallel | Agent #1 fixed c1, agent #2 fixed c2 with no knowledge of c1's context; agent #4 didn't know c1/c2 were already done | Agents conflicted on same file; incorrect fixes due to missing context of sibling fixes | Prompt each agent with ALL threads for its file in one call |
| Haiku sub-agent attempted hard-difficulty (48-line deletion) | Haiku couldn't understand context; deleted wrong lines | Manual rework needed; wasted cycle | Tier by difficulty: Opus for >50-line refactoring |
| Prompt didn't invoke `/hephaestus:advise` | Sub-agents guessed at domain concepts; thread c4 (BN stats) fix was incorrect | Without understanding running-mean EMA semantics, agent couldn't justify deletion | Add `/hephaestus:advise [domain]` as first instruction in every dispatch |
| Aggregated results without verification step | Assumed all fixes compiled | One fix introduced a compile error that blocked CI | Add explicit "verify compilation" step before commit |

## Results & Parameters

### Model Tier Thresholds

```json
{
  "haiku": {
    "max_files": 1,
    "max_lines": 50,
    "max_threads": 1,
    "examples": ["variable rename", "type fix", "off-by-one", "import reorder"]
  },
  "sonnet": {
    "max_files": 3,
    "max_lines": 200,
    "max_threads": 2,
    "examples": ["API change", "logic fix with tests", "feature addition"]
  },
  "opus": {
    "max_files": "unlimited",
    "max_lines": "unlimited",
    "max_threads": "unlimited",
    "examples": ["architectural refactor", "major deletion", ">200 line rewrites"]
  }
}
```

### Thread Aggregation Format

Each sub-agent returns:
```json
{
  "thread_id": "c1",
  "file": "backward.mojo",
  "summary": "Changed `fwd.gap` → `fwd.s4b2_cache.block_out` for correct gradient dimensions",
  "verification": "Compiles with mojo build --Werror",
  "status": "fixed"
}
```

Orchestrator aggregates all into:
```json
{
  "fixed_threads": [
    {"thread_id": "c1", "file": "backward.mojo", "summary": "..."},
    {"thread_id": "c2", "file": "backward.mojo", "summary": "..."},
    {"thread_id": "c3", "file": "impl.mojo", "summary": "..."},
    {"thread_id": "c4", "file": "backward.mojo", "summary": "..."}
  ],
  "verification": {
    "compilation": "All fixes verified with mojo build --Werror",
    "formatting": "Code clean (mojo format)",
    "tests": "All tests passing"
  },
  "commit": "cb3deb5c"
}
```

## Key Insights

1. **File Grouping First**: Always group review threads by file before dispatching agents. Same-file threads must be handled by the same agent in one prompt to avoid edit races.

2. **Parallel When Safe**: Different files → different agents in parallel (speed up). Same file → same agent sequentially (correctness).

3. **Model Tier by Difficulty**: Simple fixes (Haiku) vs. medium logic (Sonnet) vs. hard refactoring (Opus). Mismatched tiers waste tokens or produce incorrect code.

4. **Domain Knowledge**: Every sub-agent's first instruction must be `/hephaestus:advise [domain]` to ground context before applying fixes.

5. **Aggregation Before Commit**: Collect all results in a single table, verify compilation/tests, then create one atomic commit.

6. **One-Liner Summaries**: Thread_id + one-liner enables quick spot-checking of what was fixed and why.

---

**See Also**:
- `parallel-agent-swarm-dispatch-patterns.md` — general swarm coordination patterns
- `pr-review-loop-orchestration-agent-patterns.md` — LLM reviewer loops and thread resolution contracts
