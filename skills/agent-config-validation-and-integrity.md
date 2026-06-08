---
name: agent-config-validation-and-integrity
description: "Design, validate, and maintain agent configuration integrity in the HomericIntelligence agentic hierarchy. Use when: (1) consolidating redundant junior/senior agent tiers or multiple specialist agents into a parent tier with overlapping scope, (2) adding CI validation that delegates_to frontmatter fields map to real .md files (referential integrity), (3) fixing stale cross-references in agent configs or docs after specialist consolidation deletes agent files, (4) validating YAML frontmatter correctness before committing agent configuration changes, (5) routing pipeline phases to the correct Claude model tier via centralized module with env-var overrides."
category: architecture
date: 2026-06-07
version: "1.1.0"
user-invocable: false
history: agent-config-validation-and-integrity.history
tags:
  - agent-config
  - tier-consolidation
  - yaml-validation
  - referential-integrity
  - delegates-to
  - stale-crossrefs
  - model-selection
  - claude-cli
  - pydantic
  - hephaestus
---

# Agent Configuration Validation and Integrity

## Overview

| Attribute | Value |
| ----------- | ------- |
| **Category** | Architecture |
| **Theme** | Design, validate, and maintain agent configuration integrity across the HomericIntelligence L0–L5 hierarchy |
| **Verification** | verified-ci |
| **Effort** | Low–Medium (30 min per consolidation; 1–2 h for REST/CI integration) |
| **Risk** | Low — config/doc/validator changes only; no agent runtime logic changes |
| **Scope** | Agent config files, hierarchy docs, config validators, pipeline model-selection |

This skill covers the full HomericIntelligence agent-config lifecycle —
**design → validate integrity → fix staleness** — by consolidating three related
patterns that all operate on agent YAML/config files:

1. **Tier and specialist consolidation** — merge redundant junior/senior tiers or many
   structurally-identical review specialists into a single parent/general agent.
2. **Referential integrity validation** — CI check that every `delegates_to` name maps to
   a real `.md` file, plus general YAML frontmatter validation before commit.
3. **Stale cross-reference cleanup** — fix dangling agent references in configs and docs
   after consolidation deletes agent files.

It also covers per-phase Claude model-tier selection for CLI automation pipelines, a
runtime knob frequently wired alongside agent-tier design.

## When to Use

1. A lowest-level junior (L5) or redundant senior (L4) tier duplicates its parent scope
   with simpler tasks; the split adds config overhead without meaningful value.
2. Multiple review specialist agents share identical `tools`, `model`, `level`, `phase`,
   and `hooks` YAML — only their review checklists differ.
3. You want CI to automatically block PRs that introduce stale `delegates_to` references
   (an agent name pointing to a deleted/renamed `.md` file).
4. Creating or modifying agent configurations; running CI/CD validation before merge;
   troubleshooting agent loading failures or YAML frontmatter correctness.
5. A consolidation PR deleted agent files but left stale `Coordinates With` links or
   agent-name references in remaining configs, `agents/` docs, or tracking docs.
6. A multi-phase Claude-CLI pipeline dies on HTTP 429 because every invocation silently
   inherits the user's default model tier.

## Verified Workflow

### Quick Reference

```bash
# Validate all agent configs (structure, fields, delegation refs)
python3 tests/agents/validate_configs.py .claude/agents/

# Validate a single agent
./scripts/validate_agent.sh .claude/agents/<agent-name>.md

# Grep for stale references after a tier/specialist consolidation
grep -r "<removed-agent-name>" .claude/agents/ agents/ docs/ CLAUDE.md --include="*.md"

# Operator escape hatch: flip pipeline tiers to a cheaper model
HEPH_PLANNER_MODEL=claude-haiku-4-5 \
HEPH_IMPLEMENTER_MODEL=claude-haiku-4-5 \
  pixi run python -m hephaestus.automation.implementer
```

```python
# Referential integrity: delegates_to must map to a real agent .md file.
# In AgentConfigValidator.__init__ (build known-agents set ONCE):
self.existing_agents: set = (
    {f.stem for f in agents_dir.glob("*.md")}
    if agents_dir.exists()
    else set()
)

# In _validate_frontmatter, before `return errors, warnings, frontmatter`:
if "delegates_to" in frontmatter:
    raw = frontmatter["delegates_to"].strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if inner:
            names = [n.strip() for n in inner.split(",") if n.strip()]
            for name in names:
                if name not in self.existing_agents:
                    errors.append(
                        f"delegates_to references non-existent agent: '{name}'"
                        f" (no .claude/agents/{name}.md)"
                    )
    else:
        errors.append(f"delegates_to must be a YAML inline list, got: '{raw}'")
```

```python
# hephaestus/automation/claude_models.py — centralized per-phase model selection
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

### Detailed Steps

#### A. Agent Tier-Config Design and Consolidation

**Tier consolidation (junior or senior into parent):**

1. **Read all affected tiers** — specialist (L3), engineer (L4), junior (L5) — to
   understand scope overlap.
2. **Expand the parent config**: absorb junior/senior description, scope items, workflow
   steps, skills, and constraints; set `delegates_to: []`.
3. **Update the coordinator/specialist config**: remove the merged tier from its
   `delegates_to` list.
4. **Delete the merged config file** (`git rm` — list each file explicitly, never a
   wildcard that could match files to keep).
5. **Update documentation files** — search for every reference to the removed agent name:
   - `agents/hierarchy.md`: remove from diagram box; update tier narrative AND table count.
   - `agents/README.md`: remove entry; update agent count in heading.
   - `agents/docs/agent-catalog.md`: remove full section; update totals; update delegation
     references; update Quick Reference table row (include flanking rows for uniqueness).
   - `agents/docs/onboarding.md`: remove list entry; update "N agents" link text.
6. **Verify no stale references** (see section C below).
7. **Run agent validation tests**:
   `python3 tests/agents/validate_configs.py .claude/agents/` — must be 0 failures.
8. **Commit atomically** with a `refactor(agents):` conventional commit message.

**Review-agent consolidation (many specialists → one general):**

1. Identify structurally identical candidates: same `tools: Read,Grep,Glob`,
   `model: sonnet`, `level: 3`, `phase: Cleanup`, identical `hooks` blocks.
2. Create `general-review-specialist.md` with one `## Scope` section and subsections per
   merged domain; keep read-only hooks blocks.
3. Delete merged files (explicit list in `git rm`).
4. Update the orchestrator `delegates_to` list; collapse routing/delegation tables.
5. Update `agents/hierarchy.md` counts (Level 3 row + Total row).
6. Validate and pre-commit:
   `python3 tests/agents/validate_configs.py .claude/agents/ && pixi run pre-commit run --all-files`

**Per-phase model selection (CLI automation pipelines):**

1. Map phases to model tiers by token shape (Planner → Opus, Implementer → Haiku,
   Reviewer/advise/learn → Sonnet).
2. Create `<pkg>/automation/claude_models.py` with per-phase **functions** (not constants)
   so env-var lookup happens at call time.
3. Wire `--model <id>` at every site that **creates** a new Claude session.
4. **Do NOT** pass `--model` at sites that **resume** a session (`--resume`); the model is
   locked to the originating session.
5. Add unit tests (defaults, env override, reimport stability); verify with `ruff`, `mypy`,
   `pytest tests/unit`.

#### B. delegates_to File-Existence Check (referential integrity in CI)

1. **Build known-agents set in `__init__`** — add the `existing_agents` glob (see Quick
   Reference). It captures all `.md` file stems once, before validation runs.
2. **Add the `delegates_to` check in `_validate_frontmatter`** (see Quick Reference).
   Inline list `[a, b, c]` is the project convention; empty `[]` is valid; the error
   message includes the expected filename to make fixing obvious. Use `errors.append`
   (hard error that fails CI), not `warnings.append`.
3. **Fix any stale references caught** by running the validator:
   `python3 tests/agents/validate_configs.py .claude/agents/`. For each
   `delegates_to references non-existent agent: '<name>'`, remove `<name>` from the
   relevant agent's `delegates_to`.
   Concrete example caught in production — `security-specialist.md`:
   - Before: `delegates_to: [implementation-engineer, senior-implementation-engineer, test-engineer]`
   - After:  `delegates_to: [implementation-engineer, test-engineer]`
     (`senior-implementation-engineer.md` no longer exists.)
4. **Write pytest tests** in `tests/agents/test_validate_delegates_to.py` covering: init
   populates set (and empty/nonexistent dir), valid lists (`[]`, single, multiple, spaces
   around commas), invalid refs → error + message + `is_valid=False`, non-list value →
   error, and the integration regression guard:

```python
def test_all_agent_delegates_to_references_exist(self) -> None:
    agents_dir = self._find_agents_dir()
    validator = AgentConfigValidator(agents_dir)
    results = validator.validate_all()
    stale_errors = [
        f"{result.file_path.name}: {error}"
        for result in results
        for error in result.errors
        if "delegates_to references non-existent agent" in error
    ]
    assert stale_errors == [], (
        "Stale delegates_to references found:\n"
        + "\n".join(f"  {e}" for e in stale_errors)
    )
```

#### C. Stale Agent Cross-Reference Cleanup (after consolidation deletes files)

1. **Identify stale links** from PR review feedback or grep:
   `grep -r "deleted-specialist-name" .claude/agents/`
2. **Read each flagged file** around the `Coordinates With` section to confirm exact text.
3. **Apply parallel edits** (independent files can be updated simultaneously):
   - Replace `[Deleted Specialist](./deleted-specialist.md)` with
     `[General Review Specialist](./general-review-specialist.md)`.
   - Merge descriptions from both deleted lines into one concise line.
   - Keep line length under 120 chars (markdownlint MD013).
4. **Search the FULL repo, not just `.claude/agents/`** — tracking/status docs in
   `docs/dev/` (e.g. `agent-claude4-update-status.md`) also list agents by name:
   `grep -rn "deleted-agent-a\|deleted-agent-b" --include="*.md"`
5. **Update count labels too** (e.g. "Review Specialists (10):" → "Review Specialists (4):"),
   keep surviving agents, replace deleted bullets with the consolidated agent.
6. **Validate and re-grep**:
   `python3 tests/agents/validate_configs.py .claude/agents/` (0 errors = passing; note
   `validate_configs.py` checks structure, NOT link targets — always grep too), then
   `grep -r "deleted-agent-name" --include="*.md"` to confirm zero remaining references.
7. **Commit** referencing the consolidation issue.

#### D. Resource-Prompt Consistency Fix

Ensure all root-level config fields are mapped into the `resources` dict
(`src/<pkg>/e2e/tier_manager.py`) and that prompt messages use count-aware wording:

```python
# Map root-level fields (mirror existing mcp_servers handling)
for field in ("tools", "agents", "skills"):
    value = config_data.get(field, {})
    if value:
        resources[field] = value

# Prompt wording — count-aware (singular vs plural)
if len(resource_names) > 1:
    prefix = "Maximize usage of the following [type]s to complete this task:"
else:
    prefix = "Use the following [type] to complete this task:"

# tools: {enabled: all} suffix logic
if tools_spec.get("enabled") == "all":
    suffixes.append("Maximize usage of all available tools to complete this task.")
```

Resource-prompt output reference:

| Configuration | Prompt output |
| --------------- | -------- |
| `tools: {enabled: all}` | "Maximize usage of all available tools to complete this task." |
| `tools: {names: [Read, Write]}` | "Maximize usage of the following tools to complete this task:\n- Read\n- Write" |
| `tools: {names: [Read]}` | "Use the following tool to complete this task:\n- Read" |
| `mcp_servers: [fs, git]` | "Maximize usage of the following MCP servers to complete this task:\n- fs\n- git" |
| No resources | "Complete this task using available tools and your best judgment." |

#### E. REST API + Pydantic Config Integration (httpx)

1. Add `httpx>=0.27,<1` to **both** `pixi.toml` and `pyproject.toml`.
2. Create the module in this order: `errors.py` → `models.py` → `client.py` → `__init__.py`.
3. `client.py`: context manager, central `_request()` helper; health-check returns `None`
   on failure while other operations raise.
4. Use the `import X as X` pattern in `__init__.py` and config re-exports when
   `implicit_reexport=false` in mypy (a plain `from module import X` is NOT re-exported).
5. Wire the optional field into the config hierarchy:
   `maestro: MaestroConfig | None = Field(default=None)`.
6. Mock `httpx.Client` in tests via `unittest.mock.patch`.

httpx module layout:

```text
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

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
| --------- | ---------------- | --------------- | ---------------- |
| Searching for count updates by number alone | `grep -n "44\|31\|3 L5"` across docs | Multiple unrelated occurrences; hard to target | Search full count phrases, e.g. "3 junior types" or "44 agents" |
| Assuming hierarchy.md table already correct | Skipped table check because total looked right | L5 narrative prose ("3 types") can drift from the table count | Check both the table AND the prose narrative separately |
| Updating catalog Quick Reference row without context | Removed a row without surrounding rows | `old_string` not unique | Include flanking rows in `old_string` for uniqueness |
| Assuming config file needs deletion | `git rm .claude/agents/junior-implementation-engineer.md` | File already absent (prior consolidation removed it) | Always `ls .claude/agents/junior-*` before config changes |
| Using `Edit` without prior `Read` | Edited orchestrator after reading it only via Bash | `Edit` requires an explicit `Read` in conversation history | Always call `Read` before `Edit`, even if seen via Bash |
| Single `git rm` with wildcard on review agents | `git rm .claude/agents/*-review-specialist.md` | Glob matched files to keep (mojo, security, test) | List each file explicitly in `git rm` |
| Lazy `delegates_to` lookup per validation | Re-glob the agents directory on each `_validate_frontmatter` call | Slow for large dirs; misses the single-pass design | Build the known-agents set once in `__init__` |
| Storing full paths instead of stems | `existing_agents = {f for f in agents_dir.glob("*.md")}` | Comparison against frontmatter string names always fails | Store stems (`f.stem`), not `Path` objects |
| Warning instead of error for stale refs | Treated missing refs as warnings | Warnings don't fail CI; stale refs are bugs, not style | Use `errors.append(...)`, not `warnings.append(...)` |
| Separate `_validate_delegates_to` method | Factored format check into its own method | Required passing `frontmatter` dict as extra arg; added complexity | Inline the check where `frontmatter` is already available |
| Searching only `.claude/agents/` for stale refs | Grep scoped to `.claude/agents/*.md` | Tracking docs in `docs/dev/` were missed | Search the full repo recursively across all `*.md` |
| Replacing agent names without reading context | Applied sed-style bulk replace | Count labels ("Review Specialists (10)") also need updating | Read surrounding context first; update counts too |
| Merging two lines into continuation indent | `- [General...] - Suggests...\n  untested code paths` | Markdownlint may reject indented list continuation | Shorten the description to one line under 120 chars |
| Running `just pre-commit-all` / `npx markdownlint-cli2` | Invoked `just` / `npx` directly | Not installed / not in PATH outside pixi env | Fall back to `pre-commit run --all-files` or `pixi run npx ...` |
| Running pipeline with no `--model` flag | Every `claude` invocation inherited terminal default (Opus) | One tier's quota exhausted; all phases died HTTP 429 | Always pass `--model` explicitly at session-creating sites |
| Passing `--model` at `--resume` sites for symmetry | Passed `--model` uniformly at all invocations | CLI locks model to the originating session | Resume sites must NOT pass `--model`; document as invariant |
| Placing model helper between import groups | Put tier constants + helper mid-file | `ruff` raised E402 (import not at top) | Helpers go BELOW all imports — non-negotiable with E402 |
| `type: ignore[arg-type]` on valid Pydantic int fields | Added ignores to test calls like `MaestroConfig(timeout_seconds=0)` | Mypy flagged `unused-ignore` — Pydantic validates at runtime, not type level | Don't add `type: ignore` for Pydantic runtime validators on correctly-typed fields |
| Plain import for re-export in strict-mypy project | `from module import MaestroConfig` in `config/models.py` | `implicit_reexport=false` means plain imports are not re-exported | Use `import X as X` when a symbol must be importable from the importing module |

## Results & Parameters

### Tier consolidation — count update template

| File | Old value | New value |
| ------ | ----------- | ----------- |
| `agents/hierarchy.md` L5 narrative | "3 types (Impl, Test, Docs)" | "2 types (Impl, Test)" |
| `agents/README.md` Level 5 heading | "(2 agents)" | "(1 agent)" |
| `agents/docs/agent-catalog.md` overview | "44 agents" | "43 agents" |
| `agents/docs/onboarding.md` junior count | "3 junior types" | "2 junior types" |

### Commit message template (tier consolidation)

```text
refactor(agents): consolidate <domain> engineer tiers from 3 to 2

Merge <junior-or-senior>-<domain>-engineer into <domain>-engineer.

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

### delegates_to validator — test results and files changed

```text
54 passed in 0.14s   # full agent test suite incl. 16 new delegates_to tests
```

| File | Change |
| ------ | -------- |
| `tests/agents/validate_configs.py` | Added `existing_agents` set to `__init__`; `delegates_to` check in `_validate_frontmatter` |
| `.claude/agents/security-specialist.md` | Removed stale `senior-implementation-engineer` from `delegates_to` |
| `tests/agents/test_validate_delegates_to.py` | 16 new pytest tests (new file) |

### Stale cross-ref cleanup — environment notes

- Markdownlint MD013 enforces 120-char max; count chars before committing merged bullets.
- `mojo-format` pre-commit hook fails on hosts with GLIBC < 2.32; skip with
  `SKIP=mojo-format` or rely on it auto-skipping when only `.md` files are staged.
- `validate_configs.py` reports pre-existing warnings (missing recommended sections);
  zero **errors** = passing.

## Verified On

| Project | Context | Details |
| --------- | --------- | --------- |
| ProjectOdyssey | Issue #3146 — implementation engineer tier consolidation (3→2 tiers) | 44→42 agents |
| ProjectOdyssey | Issue #3332 — test engineer tier consolidation (junior-only) | 31→30 agents |
| ProjectOdyssey | Issue #3963 — documentation engineer docs-only cleanup (config already absent) | 31→30 agents |
| ProjectOdyssey | Issue #3144 / PR #3319 — review specialist consolidation (13→5) + stale cross-ref fix | 44→35 agents; 35/35 validate pass |
| ProjectOdyssey | Issue #3965 / PR #4843 — delegates_to file-existence CI check | 54 tests pass; 1 stale ref fixed |
| ProjectScylla | Issue #1504 — AI Maestro REST API integration (httpx + Pydantic wiring) | PR #1548, 4921 tests pass |
| ProjectScylla | PR #127 — resource-prompt consistency fix | 12 unit + 82 E2E tests pass |
| ProjectHephaestus | `feat/hephaestus-tidy` — per-phase model selection | 1990 tests pass, ruff + mypy clean |
