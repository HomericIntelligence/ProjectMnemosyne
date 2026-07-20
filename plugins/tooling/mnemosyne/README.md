# plugins/tooling/mnemosyne — Command Infrastructure

This directory is **not a skill** and is **not a relic**. It is the command infrastructure
that powers the `/advise` and `/learn` slash commands used across the HomericIntelligence
ecosystem.

## Why it lives in `plugins/`, not `skills/`

Mnemosyne v2.0.0 migrated all *skills* to flat `.md` files under `skills/`.
However, this directory predates and is exempt from that migration because it contains:

| Sub-directory | Purpose |
|---------------|---------|
| `skills/advise/` | SKILL.md for the `/advise` command |
| `skills/learn/` | SKILL.md for the `/learn` command |
| `skills/documentation-patterns/` | Documentation authoring guidance |
| `skills/validation-workflow/` | CI/pre-commit validation guidance |
| `hooks/` | Example hook configurations (`settings.json.example`) |
| `references/` | Session notes, experiment logs, troubleshooting guides |
| `.claude-plugin/plugin.json` | Plugin manifest loaded by the Claude Code harness |

## What the `plugin.json` says about commands

As of v2.0.0, the `/advise` and `/learn` *command implementations* have moved to the
`hephaestus` plugin in [ProjectHephaestus](https://github.com/HomericIntelligence/ProjectHephaestus).
The SKILL.md files here document their behaviour and remain the authoritative reference.

## For contributors

- Do **not** convert this directory to the flat-file format — the harness expects the
  nested layout for plugin manifests.
- Do **not** add new skills here. New skills belong in `skills/<name>.md`.
- See `AGENTS.md` → *Plugin Standards* for the full rationale and the exception note.
