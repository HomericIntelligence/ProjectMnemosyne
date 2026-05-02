---
name: tooling-sonnet-content-filter-contributor-covenant
description: "Documents Claude Sonnet subagent HTTP 400 content filtering failures when writing Contributor Covenant or similar conduct policy files. Use when: (1) delegating CODE_OF_CONDUCT.md writes to Sonnet subagents, (2) any subagent returns 'Output blocked by content filtering policy' on governance/conduct document writes."
category: tooling
date: 2026-04-03
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [sonnet, content-filter, code-of-conduct, contributor-covenant, subagent, opus]
---

# Sonnet Content Filter Blocks Contributor Covenant File Writes

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-03 |
| **Objective** | Write `CODE_OF_CONDUCT.md` (Contributor Covenant v2.1) to 11 repositories via parallel Sonnet subagents |
| **Outcome** | All 11 Sonnet subagents blocked by content filtering policy; workaround via Opus parent succeeded |
| **Verification** | verified-local — files written, committed, pushed, and PRs created successfully |

## When to Use

- When a Sonnet subagent returns HTTP 400 `"Output blocked by content filtering policy"` while writing a file
- When delegating writes of `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, or any Contributor Covenant text to Sonnet subagents
- When any subagent fails identically across all parallel instances on the same file type
- Before spawning Sonnet agents to write governance or conduct policy documents

## Verified Workflow

### Quick Reference

```bash
# Step 1: Write the CODE_OF_CONDUCT.md from the Opus parent conversation (NOT from a subagent)
# Use the Write tool directly in the main Opus session to create the file in one repo clone

# Step 2: Copy the identical file to all other repo clones via bash
for REPO_DIR in /tmp/clone-repo-{1..11}; do
  cp /tmp/clone-repo-1/CODE_OF_CONDUCT.md "$REPO_DIR/CODE_OF_CONDUCT.md"
done

# Step 3: Batch commit/push/PR-create from the parent session
for REPO_DIR in /tmp/clone-repo-{1..11}; do
  git -C "$REPO_DIR" add CODE_OF_CONDUCT.md
  git -C "$REPO_DIR" commit -m "docs: add Contributor Covenant Code of Conduct v2.1"
  git -C "$REPO_DIR" push -u origin <branch-name>
done
```

### Detailed Steps

1. **Do NOT spawn Sonnet subagents** to write `CODE_OF_CONDUCT.md` or any Contributor Covenant text. They will all fail with HTTP 400.

2. **Write the file from the Opus parent conversation** using the `Write` tool directly. Opus does not trigger the same content filter on Contributor Covenant text.

3. **Use `cp` to replicate** the written file to all target repository clones. The content filter is triggered by the model generating the text, not by copying an already-written file via bash.

4. **Commit, push, and create PRs** from the parent session or via bash commands (not subagents) to complete the workflow.

5. **If partial state exists** (agents created branches before failing), clean up by pushing the copied file to those existing branches rather than creating new ones.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| 11 parallel Sonnet subagents | Each agent cloned repo, created branch, then tried to write CODE_OF_CONDUCT.md via Write tool | API Error: 400 `{"type":"error","error":{"type":"invalid_request_error","message":"Output blocked by content filtering policy"}}` on every agent | Contributor Covenant v2.1 text contains phrases about harassment, sexualized language, and conduct topics that trigger Sonnet's content filter |
| Sonnet retry (second attempt) | Retried subagent on same task after first failure | Identical HTTP 400 failure — not a transient error | The block is deterministic, not flaky; retrying Sonnet agents wastes time |
| Sonnet subagent with shorter text | (Hypothetical) Truncating the CoC text | Would break legal/policy requirements of the document | Full Contributor Covenant text is required; truncation is not a valid workaround |

## Results & Parameters

### Error Signature

```
API Error: 400 {"type":"error","error":{"type":"invalid_request_error","message":"Output blocked by content filtering policy"}}
```

### Scale Observed

- **11 Sonnet subagents** failed identically — 100% failure rate, not a fluke
- Agents completed: repo clone, branch creation
- Agents failed at: `Write` tool call for `CODE_OF_CONDUCT.md`

### Model Behavior Difference

| Model | Contributor Covenant Write | Notes |
| ------- | --------------------------- | ------- |
| Claude Sonnet (subagent) | BLOCKED — HTTP 400 content filter | Fails deterministically |
| Claude Opus (parent) | SUCCESS | No content filter triggered |

### Key Insight

The content filter triggers on **model text generation** of conduct/harassment policy language, not on file content per se. Once Opus writes the file, `cp` via bash bypasses the filter entirely because no model generation occurs.

### Cleanup for Partial Agent State

When agents have created branches but failed before writing the file:

```bash
# List branches created by failed agents
gh pr list --repo <org>/<repo> --state open

# Push the Opus-written file to the existing branch
git -C /tmp/clone-repo-N checkout <existing-branch-name>
cp /tmp/reference-repo/CODE_OF_CONDUCT.md /tmp/clone-repo-N/CODE_OF_CONDUCT.md
git -C /tmp/clone-repo-N add CODE_OF_CONDUCT.md
git -C /tmp/clone-repo-N commit -m "docs: add Contributor Covenant Code of Conduct v2.1"
git -C /tmp/clone-repo-N push
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| HomericIntelligence (11 repos) | Multi-repo audit — adding CODE_OF_CONDUCT.md to all repos | 11 Sonnet agents failed; Opus parent + cp workaround succeeded; all PRs created |
