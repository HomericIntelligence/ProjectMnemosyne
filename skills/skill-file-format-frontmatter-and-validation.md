---
name: skill-file-format-frontmatter-and-validation
description: "Canonical reference for skill/plugin file format, YAML frontmatter rules, and validation failure fixes. Use when: (1) a skill PR fails CI with 'YAML frontmatter missing' or 'Failed Attempts table missing required columns', (2) fixing frontmatter parsers that use line.partition(':') or split(':',1) and silently truncate colon-containing values, (3) creating a new Claude Code plugin and need to satisfy format requirements or marketplace registration, (4) a skill description or agent field needs the agent routing pattern for Claude Code v2.1.0+, (5) debugging 'plugin has invalid manifest' or 'Unrecognized key(s)' errors after installation."
category: tooling
date: 2026-06-07
version: "1.1.0"
user-invocable: false
history: skill-file-format-frontmatter-and-validation.history
tags: [yaml, frontmatter, validation, markdownlint, md033, failed-attempts, plugin-format, marketplace, agent-field, ci-cd]
---
# Skill File Format, Frontmatter, and Validation

Canonical reference for the skill/plugin file format used in this marketplace: YAML
frontmatter rules, the colon-truncation parser bug, CI validation failure patterns,
the Claude Code plugin/marketplace schema, and the `agent` routing field.

## Overview

| Item | Details |
| ------ | --------- |
| Objective | One reference for skill/plugin file format, frontmatter parsing, and the validation failures that block skill PRs |
| Scope | Frontmatter spec, `partition(":")`/`split(":",1)` colon bug, Failed Attempts column check, MD033 inline-HTML false positive, plugin.json/marketplace.json schema, `agent` field |
| Outcome | Skill and plugin PRs pass `validate_plugins.py` and markdownlint; plugins install without manifest errors |
| Verification | verified-ci |

## When to Use

1. A skill PR fails CI with `SKILL.md missing YAML frontmatter (must start with ---)` or
   `YAML frontmatter missing`.
2. A skill PR fails `validate`/`unit-tests` with `Failed Attempts table missing required columns`.
3. A skill PR fails `markdownlint` with `MD033/no-inline-html` on a `<placeholder>` in prose.
4. A frontmatter parser uses `line.partition(":")` or `line.split(":", 1)` and silently
   truncates values containing colons (URLs, ratios like `3:1`, quoted strings with colons).
5. You are creating a new Claude Code plugin and need to satisfy plugin.json/SKILL.md schema
   or register a marketplace.
6. A plugin install fails with `plugin has invalid manifest` or `Unrecognized key(s) in object`.
7. A skill needs the `agent` routing field (Claude Code v2.1.0+) to direct execution to a
   specialized agent type.

## Verified Workflow

### Quick Reference

```bash
# Validate a skill/plugin file locally before pushing
python3 scripts/validate_plugins.py

# Check markdownlint for MD033 (inline-HTML) issues
pixi run npx markdownlint-cli2 skills/<skill-name>.md
# or
npx markdownlint-cli2 skills/<skill-name>.md
```

**Failed Attempts table — exact required 4-column header:**

```markdown
| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| Attempt 1 | Description | Reason | Takeaway |
```

**Inline HTML fix — wrap angle-bracket placeholders in backticks:**

```markdown
<!-- WRONG — triggers MD033 -->
Addresses #<existing-issue-number>.

<!-- CORRECT — backticks escape the angle brackets -->
Addresses `#<existing-issue-number>`.
```

**Frontmatter parser fix — never split on `:` manually:**

```python
# WRONG — truncates "See https://x.com" into "See https"
key, value = line.split(":", 1)        # or line.partition(":")

# RIGHT — handles colons, quotes, lists, invalid YAML
import yaml
parsed = yaml.safe_load(frontmatter_text)
result = parsed if isinstance(parsed, dict) else {}
```

### Detailed Steps

#### 1. Frontmatter Spec (this marketplace)

Every `skills/<name>.md` must start with `---`, contain a YAML mapping, and close with `---`.
Required fields and the validator's expectations:

```yaml
---
name: skill-name                 # lowercase, kebab-case; regex ^[a-z0-9-]+$ (no . _ uppercase)
description: "Trigger conditions. Use when: (1) ..., (2) ..."  # 20+ chars, specific
category: tooling                # one of the 9 approved categories
date: 2026-06-07                 # YYYY-MM-DD
version: "1.0.0"                 # semantic version
user-invocable: false            # false for internal/sub-skills
tags: [searchable, keywords]     # optional
---
```

Plugin **name** rules enforced by `scripts/validate_plugins.py` (regex `^[a-z0-9-]+$`):
lowercase only, digits and hyphens allowed, **no periods, underscores, or uppercase**. A name
like `claude-code-v2.1-adoption` fails — rename to `claude-code-v21-adoption` (rename
directories and the frontmatter `name`, then regenerate the marketplace).

#### 2. The colon-split parser bug

The single most common frontmatter-parser bug: reading YAML by splitting each line on the
first colon. `description: See https://example.com` becomes key=`description`,
value=`See https` — everything after the first `:` is silently dropped. Same failure for
ratios (`3:1`), URLs with ports (`http://localhost:8080`), and quoted strings with colons.

Find and fix all occurrences:

```bash
grep -rn 'split.*":"\|split.*'\'':'\''\|partition.*":"\|partition.*'\'':'\''' scripts/ tests/
```

Replace the manual loop with `yaml.safe_load()` and widen the return type to
`Dict[str, Any]` (PyYAML returns ints, bools, and lists, not just strings):

```python
import re
import yaml
from typing import Any, Dict

frontmatter: Dict[str, Any] = {}
m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
if not m:
    return frontmatter
try:
    parsed = yaml.safe_load(m.group(1))
except yaml.YAMLError:
    return frontmatter          # {} on invalid YAML, no raise
return parsed if isinstance(parsed, dict) else {}
```

**YAML nuance:** a bare colon followed by a space mid-sentence
(`description: Use when you need to: parse files`) is genuinely *invalid* YAML — PyYAML
raises `ScannerError`. Quote it (`"...need to: parse files"`) or write a URL/ratio form
(`://`, `3:1`) which are valid unquoted. Do not write regression tests for invalid forms.

Regression tests should cover: plain value, URL, URL with port (multi-colon), numeric ratio,
quoted colon, no frontmatter (`{}`), unclosed frontmatter (`{}`), invalid YAML (`{}` no raise).

**Cross-repo test discovery.** When the target script lives in a *sibling* repo (e.g., the
parser being fixed is in `Mnemosyne` but the regression tests are committed in
`ProjectOdyssey`), do not `import` it by package path — it is not installed. Load it directly
with `importlib.util.spec_from_file_location()`, probing multiple candidate locations, and
`pytest.mark.skipif` the whole module when none exist so the suite stays green on machines
without the sibling checkout:

```python
import importlib.util
import os
from pathlib import Path
import pytest

_CANDIDATES = [
    Path.home() / "Mnemosyne" / "scripts" / "migrate_to_skills.py",
    Path(__file__).parent.parent.parent / "build" / str(os.getpid())
        / "Mnemosyne" / "scripts" / "migrate_to_skills.py",
]
_SCRIPT_PATH = next((p for p in _CANDIDATES if p.exists()), None)

pytestmark = pytest.mark.skipif(
    _SCRIPT_PATH is None,
    reason="Sibling-repo script not found; skipping cross-repo regression tests",
)

if _SCRIPT_PATH is not None:
    _spec = importlib.util.spec_from_file_location("migrate_to_skills", _SCRIPT_PATH)
    migrate_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(migrate_module)
```

PID-scoped builds live at `<repo_root>/build/<PID>/`, not under worktree subdirectories — so
when searching for a sibling script check `~/Mnemosyne/` and
`<repo_root>/build/<PID>/Mnemosyne/`, not `.worktrees/issue-XXXX/`.

#### 3. CI validation failure patterns

**Missing frontmatter.** Validator reports the file does not start with `---`. Add the
frontmatter block at the very top of the file. When the same error appears on multiple PRs,
the root cause is usually a file on `main` — fix `main` first, then rebase the PRs so the fix
propagates once instead of being duplicated per branch.

**Diagnosing which check failed.** Pull the failing CI run's log and grep for the validator's
failure marker rather than scrolling the whole log:

```bash
gh run view <run-id> --log | grep "FAIL:"
```

**Rebase mechanics for skill/template PRs.** When rebasing a PR onto a fixed `main`:

```bash
git fetch origin <branch-name>
git checkout <branch-name>
git pull --rebase origin main
git push --force-with-lease       # NEVER plain --force
```

Always use `git push --force-with-lease`, not `git push --force` — `--force-with-lease`
aborts if the remote moved (e.g., a teammate pushed), so it cannot silently clobber others'
work. During the rebase, **template files commonly conflict** when multiple PRs each add a
new optional field to the same template (e.g.,
`templates/experiment-skill/skills/SKILL_NAME/SKILL.md`). For optional-field additions the
correct resolution is to **keep both changes** (union the two field additions), then
`git add <file> && git rebase --continue`.

**Failed Attempts column names.** `validate_plugins.py::validate_failed_attempts_table`
requires all four exact header strings to be present:

```python
if not all(col in header for col in ["Attempt", "What Was Tried", "Why It Failed", "Lesson Learned"]):
    errors.append("Failed Attempts table missing required columns")
```

Common wrong variants and their fixes:

| Wrong column name | Correct column name |
|---|---|
| `Approach` | `Attempt` |
| `Description` | `What Was Tried` |
| `Correct Approach` | `Lesson Learned` |
| 3-column table (any names) | Must be 4 columns with the exact names |

Fix: replace the header with `| Attempt | What Was Tried | Why It Failed | Lesson Learned |`,
make the separator row 4 columns, reformat data rows, re-run the validator.

**MD033 inline-HTML false positive.** markdownlint treats any `<word>` as an HTML tag,
flagging documentation placeholders like `<branch-name>`, `<run-id>`, `<existing-issue-number>`.
Wrap every angle-bracket placeholder in backticks so it is parsed as inline code. This applies
in prose, list items, and table cells.

#### 4. claude-plugin format

For full Claude Code plugins (the `plugins/tooling/mnemosyne` infrastructure, not flat skills):

- Marketplace index lives at exactly `.claude-plugin/marketplace.json` at repo root.
  Root-level `marketplace.json`, `.claude/marketplace.json`, and `plugins/marketplace.json`
  are all invalid.
- Only `plugin.json` goes inside `.claude-plugin/`. `commands/`, `skills/`, `agents/`,
  `hooks/`, `references/` go at the plugin root.
- `plugin.json` schema is **strict** — only `name`, `version`, `description`, `author`,
  `skills` are allowed. `tags`, `category`, `date`, or any other key cause
  `Unrecognized key(s) in object` / `plugin has invalid manifest`. `tags` belong in
  `marketplace.json` only; `category` is derived from directory structure.
- Official SKILL.md frontmatter (the upstream schema) allows only `name` and `description`
  (plus optional `version`, `license`). Custom fields break installation.
- Commands (`commands/`) are user-invocable `/plugin:command`; skills (`skills/`) are
  auto-activated knowledge. Register a marketplace with
  `claude plugin marketplace add <github-url|/abs/local/path>` (local path always works for
  private repos), install with `claude plugin install <name>@<MarketplaceName>`.

Minimal valid `plugin.json`:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Short description. Use when: (1) specific trigger.",
  "author": { "name": "Your Name" },
  "skills": "./skills"
}
```

**Command frontmatter (when authoring a plugin command, not a skill).** Command files in
`commands/` use a different, minimal frontmatter than skills: `description` plus an optional
`allowed-tools` field that scopes which tools the command may invoke. Use the
`Tool(matcher:*)` form to grant a tool a constrained capability:

```yaml
---
description: What this command does
allowed-tools: Bash(git:*), Read, Write
---
```

Here `Bash(git:*)` permits only `git` subcommands through Bash, while `Read` and `Write`
are granted unrestricted. Commands take `name`/`description` triggers like skills, but
`allowed-tools` is command-only — it is not a skill frontmatter field.

#### 5. skills `agent` field (Claude Code v2.1.0+)

The optional `agent` frontmatter field routes a skill to a specialized agent type. Skills
without it run on the default/current agent.

```yaml
---
name: mojo-syntax-validator
description: Validate Mojo code syntax
agent: mojo-specialist        # route to a specialized agent
category: tooling
---
```

Routing conventions: by language (`mojo-*` → `mojo-specialist`, `python-*` →
`python-specialist`), by task type (`gh-*` → `implementation-engineer`/`code-review-orchestrator`,
`quality-*` → `review-specialist`/`security-specialist`, `test-*` → `test-engineer`), and by
complexity (`junior-engineer` / `senior-engineer` / `architect`). Design clear delegation to
avoid circular dependencies. The field is marketplace-portable — it degrades gracefully on
repos with different agent architectures.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| 3-column Failed Attempts table | Used `Approach \| Why It Failed \| Correct Approach` (3 columns, non-standard names) | `validate_plugins.py` checks for all 4 exact header strings; missing `Attempt`, `What Was Tried`, `Lesson Learned` caused rejection | Always use the exact 4-column header `Attempt \| What Was Tried \| Why It Failed \| Lesson Learned` |
| Bare angle-bracket placeholder in prose | Left `#<existing-issue-number>` unescaped in a sentence | markdownlint MD033 parses `<existing-issue-number>` as an HTML element tag and flags it | Wrap every `<placeholder>` in backticks when it appears in prose |
| Test with bare `to: parse` colon | Wrote `description: Use when you need to: parse, validate files` as a regression test | PyYAML raises `ScannerError` — bare colon+space is genuinely invalid YAML (looks like a mapping key) | Only test valid YAML forms; quote mid-sentence colons or use URL/ratio forms |
| Keep `Dict[str, str]` after switching parser | Left return type as `Dict[str, str]` after moving to `yaml.safe_load()` | `yaml.safe_load()` returns `Any` values (int, bool, list), not only strings | Update annotations to `Dict[str, Any]` when migrating from manual parsing to PyYAML |
| Search worktree for sibling repo script | `find` in `.worktrees/issue-XXXX/` for `migrate_to_skills.py` | The script lives in the sibling repo (`Mnemosyne`), not the worktree | For cross-repo fixes check `~/Mnemosyne/` and `<repo_root>/build/<PID>/Mnemosyne/`; load it with `importlib.util.spec_from_file_location()` + `pytest.mark.skipif` |
| Plain `git push --force` after rebase | Used `git push --force` to update a rebased skill PR branch | `--force` overwrites the remote unconditionally and can clobber a teammate's concurrent push | Always `git push --force-with-lease` — it aborts if the remote moved since the last fetch |
| Resolve template conflict by picking one side | On rebase, kept only the current branch's new optional field, dropping `main`'s field | Both PRs were *adding* different optional fields to the same template; choosing one side lost the other's field | For optional-field additions in template files, keep both changes (union), then `git add` + `git rebase --continue` |

## Results & Parameters

### Validator checks (from `scripts/validate_plugins.py`)

```python
# Name: lowercase, digits, hyphens only
NAME_RE = r"^[a-z0-9-]+$"

# Required plugin/skill frontmatter fields
REQUIRED = {"name", "description"}        # plus category/date/version/user-invocable per CLAUDE.md

# Failed Attempts header check — all four required
if not all(col in header for col in ["Attempt", "What Was Tried", "Why It Failed", "Lesson Learned"]):
    errors.append("Failed Attempts table missing required columns")

# Plugin (claude-plugin) manifest: only these keys allowed
REQUIRED_PLUGIN_FIELDS = {"name", "version", "description"}
# category derived from directory; date optional; tags only in marketplace.json
```

### Expected output after fix

```text
$ python3 scripts/validate_plugins.py
Validating skills...
✓ skills/your-skill.md
All skills valid.

$ npx markdownlint-cli2 skills/your-skill.md
skills/your-skill.md: 0 error(s), 0 warning(s)
```

### Fix-strategy decision matrix

| Scenario | Action |
| ---------- | -------- |
| Same error on multiple PRs | Fix on `main` first, then rebase the PRs |
| Plugin name validation error | Rename plugin (dirs + frontmatter), regenerate marketplace |
| Missing frontmatter | Add the `---` frontmatter block at the file start |
| Frontmatter value truncated at a colon | Replace `split(":")`/`partition(":")` with `yaml.safe_load()` |
| Failed Attempts table rejected | Use the exact 4-column header |
| MD033 on a `<placeholder>` | Wrap the placeholder in backticks |
| `Unrecognized key(s)` on install | Remove non-schema keys from plugin.json |
| Same file on multiple branches | Fix each branch independently (no shortcut) |

### Grep to find the colon-split bug

```bash
grep -rn 'split.*":"\|split.*'\'':'\''\|partition.*":"\|partition.*'\'':'\''' scripts/ tests/
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| Mnemosyne | PRs #74, #73, #72, #69, #68 — missing-frontmatter + plugin-name fixes | See history block `yaml-frontmatter-validation` |
| Mnemosyne | PRs #1498, #1516 — Failed Attempts columns + MD033 inline-HTML | See history block `ci-cd-skill-validation-failed-attempts-inline-html` |
| Mnemosyne | Marketplace schema compliance (official plugin format) | See history block `claude-plugin-format` |
| Mnemosyne | Template updates for the `agent` field (Claude Code v2.1.0) | See history block `skills-agent-field` |
| ProjectOdyssey | `validate_configs.py` colon-split fix, 86 tests passing | See history block `frontmatter-colon-split-fix` |

## References

- `scripts/validate_plugins.py` — skill/plugin validator
- `scripts/generate_marketplace.py` — regenerates `marketplace.json`
- [markdownlint MD033 rule](https://github.com/DavidAnson/markdownlint/blob/main/doc/md033.md)
- [Claude Code plugin docs](https://code.claude.com/docs/en/plugins)
- [Claude Code skills docs](https://code.claude.com/docs/en/skills)
