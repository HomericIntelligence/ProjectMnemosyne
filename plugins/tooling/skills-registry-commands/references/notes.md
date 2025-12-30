# Skills Registry Commands - Complete Setup

A complete skills registry system for Claude agents, including commands, hooks, validation, and documentation patterns.

## What's Included

```
skills-registry-commands/
├── .claude-plugin/plugin.json
├── skills/
│   ├── advise/SKILL.md              # /advise command
│   ├── retrospective/SKILL.md       # /retrospective command
│   ├── documentation-patterns/SKILL.md  # How to write good skills
│   └── validation-workflow/SKILL.md     # CI/CD setup
├── hooks/
│   ├── retrospective-trigger.py     # SessionEnd hook
│   └── settings.json.example        # Hook configuration
├── scripts/
│   ├── validate_plugins.py          # PR validation
│   └── generate_marketplace.py      # Marketplace generation
└── references/
    └── notes.md                     # This file
```

## Quick Start

### 1. Copy Plugin to Your Project

```bash
cp -r plugins/tooling/skills-registry-commands your-project/plugins/tooling/
```

### 2. Install Hooks

```bash
mkdir -p your-project/.claude/hooks

cp plugins/tooling/skills-registry-commands/hooks/retrospective-trigger.py \
   your-project/.claude/hooks/

cp plugins/tooling/skills-registry-commands/hooks/settings.json.example \
   your-project/.claude/settings.json
```

### 3. Install Scripts

```bash
mkdir -p your-project/scripts

cp plugins/tooling/skills-registry-commands/scripts/*.py \
   your-project/scripts/
```

### 4. Add Commands to CLAUDE.md

```markdown
## Commands

### /advise

Search skills registry for relevant experiments before starting work.

1. Read user's goal/question
2. Read `marketplace.json` to find matching plugins by description/tags
3. For each match, read the plugin's SKILL.md
4. Summarize: what worked, what failed, recommended parameters
5. Always prioritize Failed Attempts - these prevent wasted effort

### /retrospective

Save learnings after a session (auto-creates PR).

1. Read entire conversation history
2. Extract: objective, steps taken, successes, failures, parameters
3. Prompt user for category and skill name
4. Generate plugin from template
5. Create branch: `skill/<category>/<name>`
6. Commit, push, and create PR
```

### 5. Set Up CI/CD (Optional)

Copy workflows from the validation-workflow skill:
- `.github/workflows/validate-plugins.yml`
- `.github/workflows/update-marketplace.yml`

### 6. Initialize Marketplace

```bash
echo '{"version": "1.0.0", "plugins": []}' > marketplace.json

mkdir -p plugins/{training,evaluation,optimization,debugging,architecture,tooling,ci-cd,testing}
```

## Components

| Component | Purpose |
|-----------|---------|
| `/advise` | Search registry before starting work |
| `/retrospective` | Capture learnings after sessions |
| `documentation-patterns` | How to write discoverable skills |
| `validation-workflow` | CI/CD for quality enforcement |
| `retrospective-trigger.py` | Auto-prompt on session end |
| `validate_plugins.py` | PR validation script |
| `generate_marketplace.py` | Marketplace index generator |

## Hook Behavior

The SessionEnd hook:
- Triggers on `/exit` and `/clear`
- Checks if session has meaningful content (>10 messages)
- Prompts: "Would you like to save your learnings?"
- Non-blocking

## Source

Based on: https://huggingface.co/blog/sionic-ai/claude-code-skills-training
