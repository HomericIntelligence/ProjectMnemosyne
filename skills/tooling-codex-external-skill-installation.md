---
name: tooling-codex-external-skill-installation
description: "Install and adapt third-party skills into Codex from a GitHub repository. Use when: (1) importing open-source skills into ~/.codex/skills, (2) external skills lack agents/openai.yaml metadata, (3) imported skills assume Claude-specific slash-command behavior, (4) you want repo-local AGENTS.md instructions to advertise newly installed skills."
category: tooling
date: 2026-04-02
version: "1.0.0"
user-invocable: false
verification: verified-local
tags: [codex, skills, projecthephaestus, install, openai-yaml, agents-md, advise, learn]
---

# Tooling: Codex External Skill Installation

## Overview

| Field | Value |
| ------- | ------- |
| **Date** | 2026-04-02 |
| **Objective** | Import `repo-analyze*`, `advise`, and `learn` from `HomericIntelligence/ProjectHephaestus` into Codex and make them discoverable in both global skill storage and repo-local instructions |
| **Outcome** | Successful locally — 5 skills installed into `~/.codex/skills`, Codex UI metadata added, `advise`/`learn` adapted for Codex, ProjectMnemosyne cache seeded, and repo `AGENTS.md` updated |
| **Verification** | verified-local |
| **Context** | Radiance local setup using Codex + ProjectHephaestus + ProjectMnemosyne |

## When to Use

- Importing skills from a third-party GitHub repo into Codex local skill storage
- External skills ship only `SKILL.md` and need `agents/openai.yaml` metadata to behave like first-class Codex skills
- Imported skills assume Claude Code slash commands, `$ARGUMENTS`, or mandatory sub-agent delegation
- You want the current repository's `AGENTS.md` to explicitly advertise the newly installed skills for future sessions

## Verified Workflow

### Quick Reference

```bash
# Install skill folders from GitHub into Codex
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo HomericIntelligence/ProjectHephaestus \
  --path skills/repo-analyze skills/repo-analyze-quick skills/repo-analyze-strict skills/advise skills/learn \
  --dest ~/.codex/skills

# Generate Codex UI metadata; pass --name to avoid frontmatter parsing dependencies
python3 ~/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py \
  ~/.codex/skills/repo-analyze --name repo-analyze \
  --interface display_name='Repo Analyze' \
  --interface short_description='Comprehensive 15-dimension repository audit' \
  --interface default_prompt='Perform a comprehensive repository audit'

# Seed ProjectMnemosyne cache for advise/learn
mkdir -p ~/.agent-brain
git clone --depth 1 https://github.com/HomericIntelligence/ProjectMnemosyne ~/.agent-brain/ProjectMnemosyne
```

### Detailed Steps

1. **Inspect the source repo before importing**
   - Clone or browse `HomericIntelligence/ProjectHephaestus`.
   - Identify which skills are directly portable and which assume Claude Code behavior.
   - In this session, `repo-analyze`, `repo-analyze-quick`, and `repo-analyze-strict` were directly portable; `advise` and `learn` needed Codex-specific adaptation.

2. **Install the upstream skill directories into `~/.codex/skills`**
   - Use the built-in Codex installer script instead of manual copying:
     ```bash
     python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
       --repo HomericIntelligence/ProjectHephaestus \
       --path skills/repo-analyze skills/repo-analyze-quick skills/repo-analyze-strict skills/advise skills/learn \
       --dest ~/.codex/skills
     ```
   - This creates:
     - `~/.codex/skills/repo-analyze/`
     - `~/.codex/skills/repo-analyze-quick/`
     - `~/.codex/skills/repo-analyze-strict/`
     - `~/.codex/skills/advise/`
     - `~/.codex/skills/learn/`

3. **Add `agents/openai.yaml` metadata for Codex**
   - Some third-party skills only ship `SKILL.md`.
   - Generate `agents/openai.yaml` for each imported skill so they match the shape of native Codex skills.
   - If the local Python environment lacks `PyYAML`, pass `--name <skill-name>` to bypass frontmatter parsing:
     ```bash
     python3 ~/.codex/skills/.system/skill-creator/scripts/generate_openai_yaml.py \
       ~/.codex/skills/advise --name advise \
       --interface display_name='Advise' \
       --interface short_description='Search ProjectMnemosyne for prior learnings' \
       --interface default_prompt='Search prior learnings before starting work'
     ```
   - Normalize each generated file to include:
     ```yaml
     policy:
       allow_implicit_invocation: true
     ```

4. **Patch Claude-centric skills for Codex**
   - Review the imported `SKILL.md` files before using them.
   - Replace Claude-specific assumptions that do not map cleanly to Codex:
     - `$ARGUMENTS` → “triggering request text”
     - `/hephaestus:advise` or `/hephaestus:learn` examples → plain skill usage examples
     - mandatory sub-agent execution in `learn` → optional delegation only when the user explicitly asks for sub-agents
     - `gh repo clone ...` → `git clone ... || gh repo clone ...`
   - Preserve the actual workflow logic; only adapt the interaction model and local tool assumptions.

5. **Seed supporting repos and caches**
   - `advise` and `learn` expect a shared `ProjectMnemosyne` checkout at `~/.agent-brain/ProjectMnemosyne`.
   - Create or update that clone:
     ```bash
     mkdir -p ~/.agent-brain
     if [ ! -d ~/.agent-brain/ProjectMnemosyne/.git ]; then
       git clone --depth 1 https://github.com/HomericIntelligence/ProjectMnemosyne ~/.agent-brain/ProjectMnemosyne
     else
       git -C ~/.agent-brain/ProjectMnemosyne fetch origin
       git -C ~/.agent-brain/ProjectMnemosyne checkout main
       git -C ~/.agent-brain/ProjectMnemosyne pull --ff-only origin main
     fi
     ```

6. **Advertise the skills in the target repo**
   - Update the repo-local `AGENTS.md` so future sessions know these skills exist and when to use them.
   - Add:
     - a short “Recommended ProjectHephaestus flow” section
     - explicit skill table entries for `advise`, `repo-analyze`, `repo-analyze-quick`, `repo-analyze-strict`, and `learn`
   - Example additions:
     ```markdown
     Recommended ProjectHephaestus flow for this repo:
     - Use `$advise` before unfamiliar implementation, debugging, or research-heavy work
     - Use `$repo-analyze-quick` for a fast health check
     - Use `$repo-analyze` for a full repository audit
     - Use `$repo-analyze-strict` when you want a stricter evidence-based review
     - Use `$learn` after finishing meaningful work to capture reusable lessons
     ```

7. **Verify local readiness**
   - Confirm each skill folder has `SKILL.md` and `agents/openai.yaml`.
   - Confirm `ProjectMnemosyne` is on `main`.
   - Restart Codex to pick up the new skills.
   - Verification in this session was local only; restart-dependent discovery was not observed within the same process.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Generating `agents/openai.yaml` without `--name` | Ran `generate_openai_yaml.py` directly against imported skills | Local Python lacked `PyYAML`, so frontmatter parsing failed with `ModuleNotFoundError: No module named 'yaml'` | Pass `--name <skill-name>` to bypass frontmatter parsing when the helper environment is missing `PyYAML` |
| Importing `advise` and `learn` unchanged | Kept upstream `SKILL.md` content exactly as shipped | The docs referenced Claude slash commands, `$ARGUMENTS`, and mandatory sub-agent behavior that do not cleanly match Codex | Treat imported skills as source material; patch interaction-model assumptions while preserving workflow logic |
| Stopping after global installation | Installed skills into `~/.codex/skills` but did not surface them in the repo | Future sessions in the repo would not be nudged toward the new skills, reducing discoverability | Update repo-local `AGENTS.md` after installation so the skills become part of the project’s working conventions |

## Results & Parameters

### Installed Skills

| Skill | Local Path | Notes |
| ------- | ------------ | ------- |
| `repo-analyze` | `~/.codex/skills/repo-analyze` | Direct import + metadata |
| `repo-analyze-quick` | `~/.codex/skills/repo-analyze-quick` | Direct import + metadata |
| `repo-analyze-strict` | `~/.codex/skills/repo-analyze-strict` | Direct import + metadata |
| `advise` | `~/.codex/skills/advise` | Patched for Codex request-text flow and clone fallback |
| `learn` | `~/.codex/skills/learn` | Patched to prefer local worktree execution unless the user explicitly asks for delegation |

### Files Changed Pattern

| Target | Change |
| -------- | -------- |
| `~/.codex/skills/<skill>/SKILL.md` | Imported from GitHub; patch if the skill assumes Claude-only behavior |
| `~/.codex/skills/<skill>/agents/openai.yaml` | Generated or written manually for Codex UI metadata |
| `~/.agent-brain/ProjectMnemosyne` | Seeded or updated to support `advise` / `learn` |
| `<repo>/AGENTS.md` | Added workflow note and skill table entries so the repo advertises the imported skills |

### Verification Commands

```bash
# Verify installed skill shape
find ~/.codex/skills/repo-analyze ~/.codex/skills/advise ~/.codex/skills/learn -maxdepth 3 -type f

# Verify ProjectMnemosyne cache
git -C ~/.agent-brain/ProjectMnemosyne rev-parse --short HEAD
git -C ~/.agent-brain/ProjectMnemosyne branch --show-current

# Verify repo-local AGENTS additions
rg -n "Recommended ProjectHephaestus flow|\\$repo-analyze|\\$advise|\\$learn" AGENTS.md
```

### Expected Outcome

- Imported skills exist under `~/.codex/skills`
- Each imported skill has `agents/openai.yaml`
- `advise` and `learn` point at a valid `~/.agent-brain/ProjectMnemosyne` checkout
- The target repo’s `AGENTS.md` explicitly advertises the imported skills
- After restarting Codex, the skills are available as part of the local skill catalog

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| Radiance | Local Codex setup using ProjectHephaestus skills | Installed 5 skills, added Codex metadata, patched `advise`/`learn`, seeded ProjectMnemosyne, updated repo-local `AGENTS.md` |
