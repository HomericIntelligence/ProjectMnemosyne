# CLAUDE.md

This file provides guidance to Claude Code when working with ProjectMnemosyne.

## Project Overview

ProjectMnemosyne is a skills marketplace for the HomericIntelligence agentic ecosystem. It stores,
organizes, and shares learnings from experiments, debugging sessions, and development work.

**Purpose**: Capture team knowledge so Claude can `/advise` before starting work and prevent
repeated mistakes.

**Ecosystem**: Works with ProjectOdyssey (training), ProjectKeystone (coordination), and
ProjectScylla (testing).

## Commands

### /advise

Search the skills registry before starting work.

**When to use**: At session start, before experiments, when debugging unfamiliar errors.

**Workflow**:

1. Read user's goal/question
2. Search `marketplace.json` for related plugins
3. Read matching SKILL.md files
4. Return: what worked, what failed, recommended parameters

**Example**:

```text
User: /advise training a model with GRPO
Claude: Found 2 related skills...
- training/grpo-external-vllm: Use external vLLM server for GRPO training
  - Key finding: vllm_skip_weight_sync errors require separate GPU setup
  - Recommended: batch_size=4, learning_rate=1e-5
```

### /retrospective

Save learnings after a session (auto-creates PR).

**When to use**: After experiments, debugging sessions, or implementing new patterns.

**Workflow**:

1. Read entire conversation history
2. Extract: objective, steps taken, successes, failures, parameters
3. Prompt user for category and skill name
4. Generate plugin from template:
   - `plugin.json` with metadata
   - `SKILL.md` with 7-section format
   - `references/notes.md` with raw details
5. Create branch: `skill/<category>/<name>`
6. Commit and push
7. Create PR with summary

**Auto-trigger**: UserPromptSubmit hook reminds about retrospective when you type session-ending keywords.

## Plugin Standards

### Required Structure

```text
plugins/<category>/<name>/
├── .claude-plugin/
│   └── plugin.json           # Metadata with trigger conditions
├── skills/<name>/
│   └── SKILL.md              # Main knowledge document
└── references/
    └── notes.md              # Additional context
```

### Required Fields

**plugin.json**:

- `name`: Lowercase, kebab-case identifier
- `description`: Trigger conditions with specific use cases
- `category`: One of 8 approved categories
- `date`: Creation date (YYYY-MM-DD)
- `tags`: Searchable keywords

**SKILL.md**:

- YAML frontmatter (name, description, category, date)
  - `user-invocable`: Set to `false` for internal/sub-skills (declutters slash command menu)
  - Set to `true` only for skills users should directly invoke
- Overview table (date, objective, outcome)
- When to Use (trigger conditions)
- Verified Workflow (what worked)
- **Failed Attempts table (REQUIRED)**
- Results & Parameters (copy-paste ready)

### Categories

| Category | Description |
|----------|-------------|
| `training` | ML training experiments and hyperparameters |
| `evaluation` | Model evaluation and metrics |
| `optimization` | Performance tuning and speedups |
| `debugging` | Bug investigation and fixes |
| `architecture` | Design decisions and patterns |
| `tooling` | Automation and developer tools |
| `ci-cd` | Pipeline configurations and CI fixes |
| `testing` | Test strategies and patterns |

### Quality Rules

1. **Specific descriptions**: Include trigger conditions, not vague summaries
2. **Failures required**: Document what didn't work and why
3. **Copy-paste ready**: Parameters and configs should work immediately
4. **No duplication**: Link to external docs instead of copying

### Cross-Repository Compatibility

Skills should be generic enough to work across multiple repositories:

1. **No `source:` in frontmatter**: Remove repository-specific source fields
2. **Use placeholders**: Replace hardcoded paths with `<project-root>`, `<test-path>`, `<package-manager>`
3. **Add "Verified On" section**: Document where the skill was validated with a table:
   ```markdown
   ## Verified On

   | Project | Context | Details |
   |---------|---------|---------|
   | ProjectName | PR #XXX context | [notes.md](../references/notes.md) |
   ```
4. **Move specifics to references**: Put project-specific commands, paths, and code in `references/notes.md`
5. **Generic workflows**: Write workflows that can be adapted to any repository structure

**Optional plugin.json fields for cross-repo support**:
- `requires.tools`: Array of tool requirements (e.g., `[{"name": "mojo", "version": ">=0.25.0"}]`)
- `requires.languages`: Programming languages this skill applies to
- `verified_on`: Array of projects where the skill was validated

## Hooks Configuration

The project uses Claude Code hooks for automatic retrospective prompts.

**Important**: SessionEnd hooks CANNOT display messages to users (Claude Code limitation).
This project uses UserPromptSubmit hooks instead.

**UserPromptSubmit Hook**: Triggers when user types session-ending keywords (exit, quit,
clear, done, finished, etc.) to remind about `/retrospective`.

See `.claude/settings.json` for configuration and
`plugins/tooling/skills-registry-commands/hooks/settings.json.example` for reference.

## Contributing a Skill

1. Run `/retrospective` after a valuable session
2. Or manually create from `templates/experiment-skill/`
3. Fill all required sections, especially Failed Attempts
4. PR will be validated by CI before merge
5. `marketplace.json` auto-updates on merge

## References

- [ProjectOdyssey](https://github.com/HomericIntelligence/ProjectOdyssey) - Training platform
- [ProjectKeystone](https://github.com/HomericIntelligence/ProjectKeystone) - Coordination
- [ProjectScylla](https://github.com/HomericIntelligence/ProjectScylla) - Testing
