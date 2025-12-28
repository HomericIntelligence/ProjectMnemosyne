# ProjectMnemosyne

ProjectMnemosyne is a skills marketplace for the HomericIntelligence agentic ecosystem.
Named after Mnemosyne, the Greek goddess of memory, this repository serves as the
collective memory where team learnings are preserved and made searchable.

## Installation

Register the marketplace and install plugins using Claude Code CLI:

```bash
# Add the marketplace
claude plugin marketplace add HomericIntelligence/ProjectMnemosyne

# Install all plugins
claude plugin install grpo-external-vllm@ProjectMnemosyne
claude plugin install mojo-simd-errors@ProjectMnemosyne
claude plugin install github-actions-mojo@ProjectMnemosyne
claude plugin install layerwise-gradient-check@ProjectMnemosyne
claude plugin install skill-marketplace-design@ProjectMnemosyne
```

Or install from a local clone:

```bash
git clone https://github.com/HomericIntelligence/ProjectMnemosyne
claude plugin marketplace add /path/to/ProjectMnemosyne
claude plugin install <plugin-name>@ProjectMnemosyne
```

Verify installation:

```bash
claude plugin marketplace list
```

## Quick Start

### Search for Knowledge

```text
/advise <your goal or question>
```

Claude will search the marketplace for relevant prior learnings and return:

- What worked in similar situations
- What failed and why (critical!)
- Recommended parameters and configurations

### Save Your Learnings

```text
/retrospective
```

After an experiment or debugging session, capture your learnings as a new skill.
Claude will:

1. Analyze your conversation
2. Extract successes, failures, and parameters
3. Create a PR with a new skill

**Auto-trigger**: On `/exit` or `/clear`, you'll be prompted to save learnings.

## Marketplace Structure

```text
plugins/
├── training/           # ML training experiments
├── evaluation/         # Model evaluation
├── optimization/       # Performance tuning
├── debugging/          # Bug investigation
├── architecture/       # Design decisions
├── tooling/            # Automation tools
├── ci-cd/              # Pipeline configurations
└── testing/            # Test strategies
```

Each skill follows the plugin structure:

```text
plugins/<category>/<name>/
├── .claude-plugin/
│   └── plugin.json         # Metadata and trigger conditions
├── skills/<name>/
│   └── SKILL.md            # Main knowledge document
└── references/
    └── notes.md            # Additional context
```

## Available Skills

| Skill | Category | Description |
|-------|----------|-------------|
| grpo-external-vllm | training | GRPO training with external vLLM server |
| mojo-simd-errors | debugging | Debug SIMD vectorization errors in Mojo |
| github-actions-mojo | ci-cd | GitHub Actions CI setup for Mojo |
| layerwise-gradient-check | testing | Gradient checking for neural networks |
| skill-marketplace-design | architecture | Design patterns for skill marketplaces |

See `marketplace.json` for the complete searchable index.

## Contributing a Skill

### Option 1: Automatic (Recommended)

1. Complete an experiment or debugging session
2. Run `/retrospective`
3. Follow the prompts to categorize and name the skill
4. PR is created automatically

### Option 2: Manual

1. Copy `templates/experiment-skill/` to `plugins/<category>/<name>/`
2. Fill in `plugin.json` with specific trigger conditions
3. Write `SKILL.md` with all required sections
4. **Include "Failed Attempts" table** (required!)
5. Create PR

### Required Sections in SKILL.md

- **Overview table**: Date, objective, outcome
- **When to Use**: Specific trigger conditions
- **Verified Workflow**: Step-by-step that worked
- **Failed Attempts**: What didn't work and why (REQUIRED)
- **Results & Parameters**: Copy-paste ready configs
- **References**: Links to issues, docs

## Validation

All PRs are validated by CI:

- `plugin.json` has required fields
- `SKILL.md` has required sections
- Failed Attempts section is present
- Description is specific (20+ chars)
- Category is valid

Run validation locally:

```bash
python3 scripts/validate_plugins.py plugins/
```

## Ecosystem

| Project | Purpose |
|---------|---------|
| [ProjectOdyssey](https://github.com/HomericIntelligence/ProjectOdyssey) | Training and capability development |
| [ProjectKeystone](https://github.com/HomericIntelligence/ProjectKeystone) | Communication and coordination |
| [ProjectScylla](https://github.com/HomericIntelligence/ProjectScylla) | Testing and optimization |
| **ProjectMnemosyne** | Knowledge, skills, and memory |

## Why Mnemosyne?

Mnemosyne embodies memory, continuity, and the preservation of wisdom. This repository
ensures that learnings compound over time - every experiment, debugging session, and
architectural decision becomes searchable knowledge for the team.

The most valuable section in any skill is **Failed Attempts** - knowing what didn't
work saves more time than knowing what did.
