---
name: agent-config-and-tier-architecture
description: "Design, validate, and consolidate agent tier configurations in the HomericIntelligence
  agentic hierarchy. Use when: (1) merging redundant junior/senior agent tiers into
  a parent level with overlapping scope, (2) consolidating many review specialists
  with identical tooling into a single general specialist, (3) validating YAML frontmatter
  and configuration correctness before committing agent changes, (4) fixing inconsistent
  root-level field mapping in tier configurations or enhancing resource prompt suffixes,
  (5) routing each pipeline phase to the right Claude model tier via a centralized
  module with env-var overrides, (6) adding REST API client integration wired into
  a Pydantic config hierarchy."
category: architecture
date: 2026-05-19
version: "1.0.0"
user-invocable: false
history: agent-config-and-tier-architecture.history
tags:
  - agent-config
  - tier-consolidation
  - yaml-validation
  - model-selection
  - claude-cli
  - pydantic
  - httpx
  - rest-api
  - prompt-engineering
  - hephaestus
---

# Agent Configuration and Tier Architecture

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Category** | Architecture |
| **Theme** | Design, validate, and consolidate agent tier configurations in the HomericIntelligence hierarchy |
| **Effort** | Low–Medium (30 min per consolidation; 1–2 h for REST integration) |
| **Risk** | Low — config/doc changes only; no runtime logic changes for consolidations |
| **Scope** | Agent config files, hierarchy docs, pipeline model-selection, Pydantic config wiring |

This skill consolidates five related architecture patterns that all operate on agent
YAML/config files and the L0–L5 agent hierarchy:

1. **Tier consolidation** — merge redundant junior/senior tiers into a parent level
2. **Review-agent consolidation** — collapse 10+ structurally-identical review specialists
3. **Config validation** — verify YAML frontmatter before commit or in CI
4. **Resource-prompt consistency** — fix inconsistent root-level field mapping and prompt wording
5. **Per-phase model selection** — route each pipeline phase to the right Claude model tier
6. **REST API config wiring** — add httpx client wired into the Pydantic config hierarchy

## When to Use

1. A lowest-level junior (L5) or redundant senior (L4) tier duplicates its parent scope
   with simpler tasks; the split adds config overhead without meaningful value.
2. Multiple review specialist agents share identical `tools`, `model`, `level`, `phase`,
   and `hooks` YAML — only their review checklists differ.
3. Creating or modifying agent configurations; running CI/CD validation before merge;
   troubleshooting agent loading failures.
4. Some root-level config fields (`tools`, `agents`, `skills`) are not mapped into the
   `resources` dict, or prompt wording is inconsistent between single and multiple resources.
5. A multi-phase Claude-CLI pipeline dies on HTTP 429 because every invocation silently
   inherits the user's default model tier.
6. Adding an HTTP client to a Python project with no existing HTTP dependency, wired
   through a Pydantic config hierarchy as an optional feature.

## Verified Workflow

### Quick Reference

```bash
# Validate all agent configs
python3 tests/agents/validate_configs.py .claude/agents/

# Validate a single agent
./scripts/validate_agent.sh .claude/agents/<agent-name>.md

# Grep for stale references after a tier consolidation
grep -r "<removed-agent-name>" .claude/agents/ agents/ CLAUDE.md

# Operator escape hatch: flip tiers to cheaper model
HEPH_PLANNER_MODEL=claude-haiku-4-5 \
HEPH_IMPLEMENTER_MODEL=claude-haiku-4-5 \
  pixi run python -m hephaestus.automation.implementer
```

```python
# hephaestus/automation/claude_models.py — centralized model selection
import os

OPUS    = "claude-opus-4-7"
SONNET  = "claude-sonnet-4-6"
HAIKU   = "claude-haiku-4-5"

def planner_model()     -> str: return os.environ.get("HEPH_PLANNER_MODEL",     OPUS)
def implementer_model() -> str: return os.environ.get("HEPH_IMPLEMENTER_MODEL", HAIKU)
def reviewer_model()    -> str: return os.environ.get("HEPH_REVIEWER_MODEL",    SONNET)
def advise_model()      -> str: return os.environ.get("HEPH_ADVISE_MODEL",      SONNET)
def learn_model()       -> str: return os.environ.get("HEPH_LEARN_MODEL",       SONNET)
```

### Tier Consolidation (junior or senior into parent)

1. **Read all affected tiers** — specialist (L3), engineer (L4), junior (L5) — to
   understand scope overlap.
2. **Expand the parent config**: absorb junior/senior description, scope items, workflow
   steps, skills, and constraints; set `delegates_to: []`.
3. **Update the coordinator/specialist config**: remove the merged tier from its
   `delegates_to` list.
4. **Delete the merged config file** (`git rm`).
5. **Update documentation files** — search for every reference to the removed agent name:
   - `agents/hierarchy.md`: remove from diagram box; update tier narrative count.
   - `agents/README.md`: remove entry; update agent count in heading.
   - `agents/docs/agent-catalog.md`: remove full section; update total counts; update
     delegation references; update Quick Reference table row.
   - `agents/docs/onboarding.md`: remove list entry; update "N agents" link text.
6. **Verify no stale references**:
   `grep -r "<removed-agent>" .claude/agents/ agents/ CLAUDE.md`
7. **Run agent validation tests**:
   `python3 tests/agents/validate_configs.py .claude/agents/` — must be 0 failures.
8. **Commit atomically** with a `refactor(agents):` conventional commit message.

### Review-Agent Consolidation (many specialists → one general)

1. **Identify structurally identical candidates**: same `tools: Read,Grep,Glob`,
   `model: sonnet`, `level: 3`, `phase: Cleanup`, identical `hooks` blocks.
2. **Create `general-review-specialist.md`** with one `## Scope` section and subsections
   per merged domain; keep read-only hooks blocks.
3. **Delete merged files** — list each explicitly in `git rm` (never use a wildcard
   that could match files to keep).
4. **Update the orchestrator** `delegates_to` list; collapse routing/delegation tables.
5. **Update `agents/hierarchy.md`** counts (Level 3 row + Total row).
6. **Validate and pre-commit**:
   `python3 tests/agents/validate_configs.py .claude/agents/ && pixi run pre-commit run --all-files`

### Config Validation Checklist

Required YAML frontmatter fields for agent configs:

```yaml
---
name: agent-name         # kebab-case identifier
description: "..."       # one-sentence purpose
category: architecture   # classification
level: 0-5               # hierarchy level (integer)
phase: Plan|Test|Implementation|Package|Cleanup
mcp_fallback: none
---
```

Validation covers: YAML syntax, required fields, valid tool names (`Read`, `Write`,
`Bash`, `Grep`, `Glob`), valid agent references in `delegates_to`/`escalates_to`, and
correct directory structure.

| Error | Fix |
| ------- | ----- |
| No YAML frontmatter | Ensure file starts and ends with `---` |
| Invalid phase value | Use: Plan, Test, Implementation, Package, Cleanup |
| Delegation target not found | Verify agent name or create referenced agent |
| Duplicate keys | Remove duplicate entries in frontmatter |
| Wrong level type | Must be integer 0–5, not string |

### Resource-Prompt Consistency Fix

Ensure all root-level config fields are mapped into the `resources` dict
(`src/<pkg>/e2e/tier_manager.py`) and that prompt messages use count-aware wording:

```python
# Map root-level fields (mirror existing mcp_servers handling)
for field in ("tools", "agents", "skills"):
    value = config_data.get(field, {})
    if value:
        resources[field] = value

# Prompt wording
if len(resource_names) > 1:
    prefix = "Maximize usage of the following [type]s to complete this task:"
else:
    prefix = "Use the following [type] to complete this task:"

# tools: {enabled: all}
if tools_spec.get("enabled") == "all":
    suffixes.append("Maximize usage of all available tools to complete this task.")
```

### Per-Phase Model Selection (CLI Automation Pipelines)

1. Map phases to model tiers by token shape:

   | Phase | Token shape | Default tier |
   | ------- | ------------- | -------------- |
   | Planner | Small input, high reasoning | Opus |
   | Implementer | Long mechanical tool-use loop | Haiku |
   | Reviewer / plan-reviewer / PR-reviewer | Middle ground | Sonnet |
   | Advise / learn | Middle ground | Sonnet |

2. Create `<pkg>/automation/claude_models.py` with per-phase **functions** (not constants)
   so env-var lookup happens at call time.
3. Wire `--model <id>` at every site that **creates** a new Claude session.
4. **Do NOT** pass `--model` at sites that **resume** a session (`--resume`); the model
   is locked to the originating session.
5. Add unit tests: default values, env override, reimport stability.
6. Verify with `ruff check`, `mypy`, and `pytest tests/unit`.

### REST API + Pydantic Config Integration (httpx)

1. Add `httpx>=0.27,<1` to both `pixi.toml` and `pyproject.toml`.
2. Create module: `errors.py` → `models.py` → `client.py` → `__init__.py`.
3. `client.py`: context manager, central `_request()` helper, health-check returns `None`
   on failure, other methods raise.
4. Use `import X as X` pattern in `__init__.py` and config re-exports when
   `implicit_reexport=false` in mypy.
5. Wire optional field into config: `maestro: MaestroConfig | None = Field(default=None)`.
6. Mock `httpx.Client` in tests via `unittest.mock.patch`.

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Searching for count updates by number alone | `grep -n "44\|31\|3 L5"` across docs | Multiple unrelated occurrences; hard to target | Search for full count phrases, e.g. "3 junior types" or "44 agents" |
| Assuming hierarchy.md table already correct | Skipped table check because total count looked right | L5 narrative prose ("3 types") can drift from the table count | Always check both the table AND the prose narrative separately |
| Updating catalog Quick Reference table row without context | Tried to remove a row without surrounding rows | `old_string` not unique | Include flanking rows in `old_string` for uniqueness |
| Assuming config file needs deletion | `git rm .claude/agents/junior-implementation-engineer.md` | File already absent (prior consolidation removed it) | Always `ls .claude/agents/junior-*` before config changes |
| Using `Edit` tool without prior `Read` | Edited orchestrator after reading it only via Bash | `Edit` tool requires an explicit `Read` call in conversation history | Always call `Read` explicitly before `Edit`, even if content was seen via Bash |
| Single `git rm` with wildcard on review agents | `git rm .claude/agents/*-review-specialist.md` | Glob matched files to keep (mojo, security, test) | List each file explicitly in `git rm` |
| Running pipeline with no `--model` flag | Every `claude` invocation inherited the user's terminal default (Opus) | One tier's quota exhausted; all phases died HTTP 429 | Always pass `--model` explicitly at session-creating sites |
| Threading model selection through Pydantic options classes | Added model as a CLI flag on each options class | Noise on all options classes; doesn't compose across 9 invocation sites; no operator escape hatch | A module + env vars matches the existing pattern for runtime knobs |
| Placing model helper between import groups | Put tier constants + helper mid-file for visual grouping | `ruff` raised E402 (module-level import not at top) | Helpers go BELOW all imports — non-negotiable with E402 enforcement |
| Passing `--model` at `--resume` sites for symmetry | Passed `--model` at all `claude` invocations uniformly | CLI locks model to originating session; `--model` alongside `--resume` is misleading | Resume sites must deliberately NOT pass `--model`; document as invariant |
| `type: ignore[arg-type]` on valid Pydantic int fields | Added ignores to test calls like `MaestroConfig(timeout_seconds=0)` | Mypy flagged `unused-ignore` — Pydantic validates at runtime, not type level | Don't add `type: ignore` for Pydantic runtime validators on correctly-typed fields |
| Plain import for re-export in strict-mypy project | `from module import MaestroConfig` in `config/models.py` | `implicit_reexport=false` means plain imports are not re-exported | Always use `import X as X` when a symbol must be importable from the importing module |

## Results & Parameters

### Agent Tier Consolidation — count update template

| File | Old value | New value |
| ------ | ----------- | ----------- |
| `agents/hierarchy.md` L5 narrative | "3 types (Impl, Test, Docs)" | "2 types (Impl, Test)" |
| `agents/README.md` Level 5 heading | "(2 agents)" | "(1 agent)" |
| `agents/docs/agent-catalog.md` overview | "44 agents" | "43 agents" |
| `agents/docs/agent-catalog.md` footer | "44 ... 3 L5" | "43 ... 2 L5" |
| `agents/docs/onboarding.md` junior count | "3 junior types" | "2 junior types" |
| `agents/docs/onboarding.md` browse link | "44 agents" | "43 agents" |

### Commit message template (tier consolidation)

```
refactor(agents): consolidate <domain> engineer tiers from 3 to 2

Merge <junior-or-senior>-<domain>-engineer into <domain>-engineer,
consistent with the rationale in #<prior-issue>.

Changes:
- Absorb scope into <domain>-engineer.md; set delegates_to: []
- Remove merged tier from <domain>-specialist delegates_to list
- Delete .claude/agents/<merged>.md
- Update agents/hierarchy.md, README.md, agent-catalog.md, onboarding.md

All agent validation tests pass (0 errors).

Closes #<issue>
```

### Per-phase model constants (copy-paste)

```python
OPUS   = "claude-opus-4-7"
SONNET = "claude-sonnet-4-6"
HAIKU  = "claude-haiku-4-5"

# Env-var overrides: HEPH_PLANNER_MODEL, HEPH_IMPLEMENTER_MODEL,
#                    HEPH_REVIEWER_MODEL, HEPH_ADVISE_MODEL, HEPH_LEARN_MODEL
```

### Resource prompt output reference

| Configuration | Prompt output |
| --------------- | -------- |
| `tools: {enabled: all}` | "Maximize usage of all available tools to complete this task." |
| `tools: {names: [Read, Write]}` | "Maximize usage of the following tools to complete this task:\n- Read\n- Write" |
| `tools: {names: [Read]}` | "Use the following tool to complete this task:\n- Read" |
| `mcp_servers: [fs, git]` | "Maximize usage of the following MCP servers to complete this task:\n- fs\n- git" |
| No resources | "Complete this task using available tools and your best judgment." |

### httpx module layout

```
<pkg>/<module>/
  __init__.py    # Public API re-exports (import X as X pattern)
  errors.py      # BaseError, ConnectionError, APIError(status_code, response_body)
  models.py      # Config(enabled: bool = False), request/response models
  client.py      # Client with context manager + central _request() helper

tests/unit/<module>/
  conftest.py    # Shared fixtures
  test_client.py
  test_models.py
```

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3146 — implementation engineer tier consolidation (3→2 tiers) | 44→42 agents |
| ProjectOdyssey | Issue #3332 — test engineer tier consolidation (junior-only) | 31→30 agents |
| ProjectOdyssey | Issue #3963 — documentation engineer docs-only cleanup (config already absent) | 31→30 agents |
| ProjectOdyssey | Issue #3144 — review specialist consolidation (13→5) | 44→35 agents |
| ProjectScylla | Issue #1504 — AI Maestro REST API integration (httpx + Pydantic wiring) | PR #1548, 4921 tests pass |
| ProjectScylla | PR #127 — resource-prompt consistency fix | 12 unit tests, 82 E2E tests pass |
| ProjectHephaestus | `feat/hephaestus-tidy` — per-phase model selection | 1990 tests pass, ruff + mypy clean |
