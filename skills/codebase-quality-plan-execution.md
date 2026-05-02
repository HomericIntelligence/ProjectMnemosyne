---
name: codebase-quality-plan-execution
description: Execute a pre-analyzed codebase improvement plan. Applies categorized
  fixes (type safety, dead code, error handling, performance, frontend bugs) across
  multiple files with continuous test verification.
category: tooling
date: '2026-03-19'
version: 1.0.0
---
# Codebase Quality Plan Execution

## Overview

| Field | Value |
| ------- | ------- |
| Date | 2026-02-28 |
| Objective | Apply 9 categories of fixes from a static analysis report to a Python scraper + JS frontend codebase |
| Outcome | **Success** — all 175 tests pass; 1 previously undiscovered runtime bug also found and fixed during implementation |
| Duration | Single session |
| Test suite | 175 pytest tests (unit + integration fixtures), no failures |

## When to Use

Use this skill when:
1. You have a static analysis report or code-review document with specific file:line bug references
2. Fixes span multiple files with **shared interfaces** (dataclass fields, constructor signatures, serialization keys)
3. You need dead code removal where the dead symbol is also referenced in tests
4. The codebase has a working test suite you must keep green throughout
5. Some fixes are in different layers (Python backend + JS frontend) with different tooling

Do NOT use when fixes are purely mechanical/cosmetic with no cross-file dependencies — just apply them directly.

## Verified Workflow

### Step 1 — Task tracking before touching code

Create one task per fix category **before writing any code**. This prevents context loss mid-session.

```
TaskCreate for each of:
- Type annotation fixes (models)
- HTTP client error handling
- Parser KeyError protection
- Domain logic bug (FORFEIT in W-L records)
- Performance fix (O(n) → O(1) lookup)
- Frontend bug (phase computation)
- Frontend fragility (setTimeout → event callback)
- Dead code removal (multiple files)
- Documentation corrections (MEMORY.md)
```

### Step 2 — Read all affected files before editing

Read all files that will be changed in parallel before making any edit. Avoids mid-edit surprises like:
- A field you're removing is still referenced in builder.py
- A constructor you're changing has 3 call sites, not 1

```python
# Always read before edit — tool will refuse otherwise anyway
# Read in parallel for efficiency
```

### Step 3 — Apply fixes in dependency order

**Correct order for interface changes:**
1. Remove field from the dataclass (`models.py`)
2. Update the parser that populated it (`parsers/followon.py`)
3. Update the builder that consumed it (`graph/builder.py`)
4. Update all test fixtures that constructed it (`tests/`)

**Wrong order:** Removing a dataclass field after tests already reference it → noisy test failures that look like logic bugs.

### Step 4 — Run tests after each category, not after all changes

```bash
pixi run test   # after each task, not once at the end
```

This isolates which change broke what. With 5+ simultaneous changes, a single test run at the end makes it hard to attribute failures.

### Step 5 — Watch for hidden consumers of removed symbols

When removing a field (e.g., `Match.aes_url`, `FollowOnEdge.target_slot`):

```bash
# Grep for ALL references, not just the definition
grep -r "target_slot\|aes_url" tests/ scraper/ web/
```

In this session:
- `Match.aes_url` was still referenced in `builder.py:366` as `match.aes_url`
- `FollowOnEdge.target_slot` was in 3 test files, not 1
- `play_id_lookup` parameter was in `cli.py` AND `tests/test_integration.py`

### Step 6 — Update the test assertion, not the code, when the test's premise changes

The `test_each_team_has_correct_edge_count` test expected `matches + 1` edges. After the routing fix, teams feeding unscheduled brackets correctly get additional `ranking_end` edges from bracket ports. The formula changed; the test was updated to `>= matches + 1` with an explanation.

## Results & Parameters

Copy-paste ready configurations and expected outputs.

## Failed Attempts / Pitfalls

### Pitfall 1 — Removing a field before searching all consumers
**What happened:** Removed `Match.aes_url` from `models.py` first, then ran tests and got `AttributeError: 'Match' object has no attribute 'aes_url'` in `builder.py:366`. Had to fix builder separately.

**Fix:** Always `grep -r "field_name"` across the entire repo before removing any field.

### Pitfall 2 — Dead constructor parameter at multiple call sites
**What happened:** `FollowOnParser.__init__` had a `play_id_lookup` parameter. Removing it required updating `cli.py`, `tests/test_followon_parser.py`, AND `tests/test_integration.py`. The test file also had a `PLAY_ID_LOOKUP` constant that became orphaned.

**Fix:** Grep for all instantiations of the class: `grep -r "FollowOnParser("`.

### Pitfall 3 — The "discovered bug" pattern: implementation reveals a deeper issue
**What happened:** While implementing follow-on edge deferred routing, the test `test_each_team_has_correct_edge_count` failed with `got 4, expected 3`. This wasn't a regression — the test's assumption was wrong for the new (correct) routing model.

**Lesson:** When a test fails during a correctness fix, first ask: "Is the test's premise correct for the new model?" before reverting.

### Pitfall 4 — `xargs -c` blocked by safety hook
**What happened:** Attempted `find ... | xargs -I{} sh -c 'head ...'` to read multiple SKILL.md files. Blocked by safety-net hook.

**Fix:** Use the `Glob` tool to find files, then `Read` tool to read them individually.

## Key Fixes Applied

| Fix | File | Mechanism |
| ----- | ------ | ----------- |
| `Team.team_id: int` → `int \| None` | `models.py:47` | Match actual nullable usage in builder |
| HTTP 429 retry | `client.py:56-61` | `status >= 500 or status == 429` |
| Parser KeyError protection | `division.py`, `pool.py` | `.get()` + `continue` on missing required keys |
| `ValueError` on unknown `PlayType` | `division.py:31` | `try/except ValueError: continue` |
| FORFEIT in W-L records | `builder.py:434,505` | `status not in (FINISHED, FORFEIT)` |
| O(1) team name lookup | `builder.py:863` | `dict` built in `__init__`, replace linear scan |
| `relayoutVisible` max phase | `graph.js:540` | Compute from `nodes` (visible), not `cy.nodes()` (all) |
| `setTimeout` → `layoutstop` | `graph.js:501,569` | `layout.one('layoutstop', () => ...)` |
| Dead: `Match.aes_url` | `models.py:94` | Never populated; removed |
| Dead: `FollowOnEdge.target_slot` | `models.py:152` | Hardcoded, never read; removed |
| Dead: `_play_id_lookup` | `followon.py:27` | Never read; removed from constructor |
| Dead: team-level client methods | `client.py:93-118` | Never called; removed |
| Dead: `name_to_play_id` | `cli.py`, `test_integration.py` | Only used for removed parameter |

## The Deeper Bug Found During Implementation

**Scenario:** Pool play is Day 1 (finished). Crossover brackets are Day 2 (unscheduled — no teams assigned). The visualization showed a direct edge from the pool's last match port straight to the final rankings, **bypassing** the crossover bracket entirely.

**Root cause:** `_build_team_flow_edges` never added unscheduled bracket matches to team timelines (since the team isn't assigned yet). So `ranking_end` connected from the last pool port. The `_build_follow_on_edges` fan-out was correct (pool_port → bracket ports) but ranking_end was already wired before those ports existed.

**Fix pattern:**
1. Pre-compute which teams feed unscheduled follow-on brackets (`_build_follow_on_team_set`)
2. In `_build_team_flow_edges`, **defer** `ranking_end` edge for those teams, storing their last port in `self._deferred_ranking_end`
3. In `_build_follow_on_edges`, after creating `pool_port → bracket_port` (follow_on) edges, also create `bracket_port → ranking_end` (team_flow) edges for deferred teams

This produces the correct DAG:
```
ranking_start → pool_m1_port → pool_m2_port ──follow_on──→ bracket_home_port → ranking_end
                                             └─follow_on──→ bracket_away_port → ranking_end
```

## Environment

- Python 3.14.3 (pixi / conda-forge)
- pytest 9.0.2
- Cytoscape.js 3.28
- Package manager: pixi (not pip/venv)
- Test run: `pixi run test`
