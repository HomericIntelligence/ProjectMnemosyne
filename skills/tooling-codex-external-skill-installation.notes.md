# Raw Notes: Tooling Codex External Skill Installation (2026-04-02)

## Session Summary

Goal: integrate `repo-analyze*`, `advise`, and `learn` from `HomericIntelligence/ProjectHephaestus`
into Codex, then make them discoverable in the `Radiance` repo.

## What Was Done

1. Read Codex `skill-installer` and `skill-creator` system skills to match local conventions.
2. Cloned `ProjectHephaestus` and inspected:
   - `skills/repo-analyze/SKILL.md`
   - `skills/repo-analyze-quick/SKILL.md`
   - `skills/repo-analyze-strict/SKILL.md`
   - `skills/advise/SKILL.md`
   - `skills/learn/SKILL.md`
3. Verified `ProjectMnemosyne` exists publicly and matches `advise` / `learn` expectations.
4. Installed 5 skill directories into `~/.codex/skills` using:
   - `install-skill-from-github.py --repo HomericIntelligence/ProjectHephaestus ...`
5. Patched imported skills:
   - `advise`: request-text parsing, `git clone || gh repo clone`, Codex-oriented wording
   - `learn`: removed mandatory sub-agent assumption, retained worktree isolation, switched co-author lines to Codex
6. Generated `agents/openai.yaml` for all 5 imported skills.
7. Added `policy.allow_implicit_invocation: true` to each generated metadata file.
8. Seeded `~/.agent-brain/ProjectMnemosyne`.
9. Updated `Radiance/AGENTS.md` to explicitly list and recommend the new skills.

## Notable Command Output

- `generate_openai_yaml.py` initially failed:
  - `ModuleNotFoundError: No module named 'yaml'`
- Re-running with explicit `--name` succeeded for all 5 skills.

## Local Paths

- Codex skills:
  - `~/.codex/skills/repo-analyze`
  - `~/.codex/skills/repo-analyze-quick`
  - `~/.codex/skills/repo-analyze-strict`
  - `~/.codex/skills/advise`
  - `~/.codex/skills/learn`
- Knowledge base cache:
  - `~/.agent-brain/ProjectMnemosyne`
- Repo-local documentation:
  - `/Users/mvillmow/Projects/Radiance/AGENTS.md`

## Why This Skill Exists

Existing skills covered:
- Claude plugin migration between marketplaces
- third-party skill porting into a Claude plugin

This session was different:
- local Codex install, not Claude plugin enablement
- explicit `agents/openai.yaml` generation for Codex
- adapting imported skills from Claude assumptions to Codex behavior
- repo-local `AGENTS.md` advertisement after install
