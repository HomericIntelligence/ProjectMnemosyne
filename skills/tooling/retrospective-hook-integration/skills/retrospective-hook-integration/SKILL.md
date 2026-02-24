---
name: retrospective-hook-integration
description: "Setup SessionEnd hooks for automatic retrospective prompts in Claude Code. Use when integrating ProjectMnemosyne marketplace."
category: tooling
date: 2025-12-29
---

# Retrospective Hook Integration

Setup SessionEnd hooks to automatically prompt for `/retrospective` when ending Claude Code sessions.

## Overview

| Field | Value |
|-------|-------|
| **Date** | 2025-12-29 |
| **Objective** | Integrate ProjectMnemosyne marketplace with ProjectOdyssey for automatic knowledge capture |
| **Outcome** | Successfully configured SessionEnd hooks and marketplace registration with worktree workflow |
| **Source** | ProjectOdyssey integration |

## When to Use

- Integrating ProjectMnemosyne skills marketplace with another repository
- Setting up `/advise` and `/retrospective` commands in a new project
- Configuring automatic session-end knowledge capture prompts
- Implementing worktree-based workflow to avoid conflicts with other Claude instances

## Verified Workflow

### 1. Register the Marketplace

**Option A: From GitHub URL (Recommended)**

Inside Claude Code session:

```text
/plugin marketplace add https://github.com/HomericIntelligence/ProjectMnemosyne
```

Or from terminal:

```bash
claude plugin marketplace add https://github.com/HomericIntelligence/ProjectMnemosyne
```

**Option B: From Local Directory**

```bash
git clone git@github.com:HomericIntelligence/ProjectMnemosyne.git
```

Then:

```text
/plugin marketplace add /path/to/ProjectMnemosyne
```

### 2. Configure SessionEnd Hook

Create worktree to avoid conflicts:

```bash
cd /path/to/project
git worktree add worktrees/retrospective-hook main -b retrospective-hook
cd worktrees/retrospective-hook
```

Update `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-bash-exec.py"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/retrospective-trigger.py\"",
            "timeout": 120,
            "once": true
          }
        ]
      }
    ]
  }
}
```

### 3. Copy Hook Script

```bash
cp /path/to/ProjectMnemosyne/.claude/hooks/retrospective-trigger.py .claude/hooks/
```

### 4. Commit and Create PR

```bash
git add .claude/settings.json .claude/hooks/retrospective-trigger.py
git commit -m "feat(hooks): add SessionEnd hook for retrospective prompts"
git push -u origin retrospective-hook
gh pr create --title "feat(hooks): add SessionEnd hook" --body "..."
gh pr merge --auto --rebase
```

### 5. Install Skills

After marketplace registration:

```text
/plugin install grpo-external-vllm@ProjectMnemosyne
/plugin install mojo-simd-errors@ProjectMnemosyne
/plugin install github-actions-mojo@ProjectMnemosyne
/plugin install layerwise-gradient-check@ProjectMnemosyne
/plugin install skill-marketplace-design@ProjectMnemosyne
```

## Failed Attempts

| Attempt | Why it Failed | Lesson Learned |
|---------|---------------|----------------|
| Used `claude plugin` in README as in-session command | Wrong syntax - `claude plugin` is terminal CLI, `/plugin` is in-session | Document both syntaxes: terminal (`claude plugin`) vs session (`/plugin`) |
| Tried to access GitHub URL without noting private repo | Repository is private, requires HomericIntelligence org access | Always note access requirements in prerequisites |
| Made changes in main working directory | Conflicts with other Claude instances working on same repo | Always use worktrees for isolated changes |
| Confused `/retrospective` with `/introspective` | Blog used `/retrospective`, user initially mentioned `/introspective` | Verify exact command names from source documentation |
| Initial GitHub URL returned 404 | Private repository, not public access | Use SSH URLs for private repos, clarify access requirements |

## Results & Parameters

### Hook Configuration (v2.1.0+)

```json
{
  "SessionEnd": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/retrospective-trigger.py\"",
          "timeout": 120,
          "once": true
        }
      ]
    }
  ]
}
```

**NEW in v2.1.0**: `once: true` ensures hook runs only once per session, preventing duplicate retrospective prompts.

### Hook Script Parameters

- **Minimum transcript length**: 10 messages
- **Trigger reasons**: `"exit"` or `"clear"` only
- **Timeout**: 120 seconds
- **once**: `true` (v2.1.0+) - Run only once per session
- **Output**: JSON with `systemMessage` field

### Marketplace Registration

```bash
# GitHub URL (private repo)
/plugin marketplace add https://github.com/HomericIntelligence/ProjectMnemosyne

# Local directory
/plugin marketplace add /home/user/ProjectMnemosyne-marketplace
```

### Worktree Pattern

```bash
# Create worktree
git worktree add worktrees/<branch-name> main -b <branch-name>

# Work in worktree
cd worktrees/<branch-name>

# Cleanup after merge
git worktree remove worktrees/<branch-name>
```

## References

- ProjectMnemosyne: https://github.com/HomericIntelligence/ProjectMnemosyne
- Blog post: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
- Claude Code plugin docs: https://code.claude.com/docs/en/discover-plugins
- Claude Code skills docs: https://code.claude.com/docs/en/skills
