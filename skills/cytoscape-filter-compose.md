---
name: cytoscape-filter-compose
description: Composing multiple Cytoscape.js visibility filters (day, status, team
  trajectory) without mutual state reset. Covers the single-owner pattern, boundary
  edge insertion in DAGs, and avoiding relayout thrash.
category: debugging
date: '2026-03-19'
version: 1.0.0
---
# Cytoscape Filter Composition (Day + Status + Team Trajectory)

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-27 |
| **Category** | debugging |
| **Objective** | Fix 6 bugs introduced by a Cytoscape.js graph with day filter, status filter, and team trajectory that all mutually reset each other's visibility state |
| **Outcome** | ✅ All 163 tests pass; all 6 bugs resolved without regressions |
| **Context** | TitanSchedule — sorting network visualization of volleyball tournament DAGs with Cytoscape.js |

## When to Use

Use this skill when:

- You have multiple Cytoscape.js visibility filters that must compose (AND logic: show only elements passing ALL filters)
- A team/path highlight function calls `clearTrajectory()` internally, wiping prior filter work
- The graph re-runs layout animation on every interaction, including no-ops
- Intermediate/boundary nodes in a DAG appear disconnected (orphan nodes with no edges)
- Day-boundary nodes are missing when filtering to a specific day because they're keyed to the wrong date
- CSS `overflow: auto` on the Cytoscape container conflicts with Tailwind's `overflow-hidden`

## Problem Patterns

### Pattern 1: Mutual filter reset (the core bug)

```
_applyFilters() step 1: clearTrajectory()  → show all
_applyFilters() step 2: hide non-day nodes
_applyFilters() step 3: hide non-status nodes
_applyFilters() step 4: hide edges with hidden endpoints
_applyFilters() step 5: activateTrajectory()
  └─ INTERNALLY calls clearTrajectory()  ← WIPES steps 2-4
  └─ hides non-team elements from full graph (not filtered graph)
```

**Result**: Day/status filters are invisible. Team filter shows full graph then hides non-team elements from the *unfiltered* set.

### Pattern 2: Unnecessary relayout on every call

`_applyFilters()` always called `rerunLayout()` (300ms animation) — even on background clicks or "All Days" when already active. This caused constant animation flicker.

### Pattern 3: Boundary node keyed to wrong date

Intermediate ranking nodes (day boundaries in a DAG) are keyed to date `D` (the day whose matches precede the boundary). When a user selects day `D+1`, the boundary between `D` and `D+1` is missing because it's only registered under `D`, not `D+1`.

### Pattern 4: Orphan boundary nodes (no edges)

In `_build_team_flow_edges()`, boundary markers were only inserted *between* consecutive matches. If all of a team's matches fall on Day 1, the Day 1→Day 2 boundary (which has a phase *after* all Day 1 matches) was never inserted into `result_seq`. The intermediate ranking node existed in the graph but had no edges.

## Verified Workflow

### Fix 1: Single-owner visibility reset (the key fix)

**Rule**: `_applyFilters()` is the sole owner of visibility state. Helper functions (`activateTrajectory`) must NOT reset visibility — they only add additional hiding on top of what `_applyFilters` has already set.

```javascript
// controls.js — _applyFilters()
function _applyFilters(cy) {
  cy.batch(() => {
    // Step 1: reset (owned here, NOT delegated to clearTrajectory)
    cy.elements().removeClass('team-win team-loss');
    cy.elements().style('display', 'element');

    // Steps 2-4: day filter, status filter, edge hiding
    // ...

    // Step 5: team trajectory — layered ON TOP of steps 2-4
    if (_activeTeamId) {
      activateTrajectory(cy, _activeTeamId);  // does NOT reset visibility
    }
  });
}
```

```javascript
// trajectory.js — activateTrajectory()
function activateTrajectory(cy, teamId) {
  // DO NOT call clearTrajectory here
  if (!teamId) return;

  // ... build teamCollection (edges + port nodes + parent match nodes) ...

  // Only hide CURRENTLY VISIBLE elements not in team's path
  // This preserves day/status filter state from steps 2-4
  cy.elements().filter(e => e.visible()).difference(teamCollection).style('display', 'none');

  // win/loss coloring ...
}
```

The critical change: `cy.elements().filter(e => e.visible())` instead of `cy.elements()`. This ensures only elements that survived the day/status filters get hidden by the team filter.

### Fix 2: Conditional relayout

```javascript
// Only relayout when a filter is actually active
if (!showAllDays || _activeTeamId) {
  relayoutVisible();  // compact animation — removes hidden phase columns
} else {
  fitToVisible(40);   // just fit — no animation, no relayout
}
```

`rerunLayout()` (full preset layout animation) is now only triggered by the explicit Reset button, not by `_applyFilters`.

### Fix 3: Assign boundary phase to both adjacent dates

```javascript
// controls.js — _initDayFilter()
const sortedMatchDates = Array.from(_dateToPhases.keys()).sort();
phases.forEach(p => {
  if (p.type === 'ranking_intermediate' && p.date) {
    // Add to preceding day (phase's own date = day whose matches precede it)
    if (!_dateToPhases.has(p.date)) _dateToPhases.set(p.date, new Set());
    _dateToPhases.get(p.date).add(p.phase);
    // Also add to the NEXT date — selecting either day shows the boundary ranking
    const nextDate = sortedMatchDates.find(d => d > p.date);
    if (nextDate && _dateToPhases.has(nextDate)) {
      _dateToPhases.get(nextDate).add(p.phase);
    }
  }
});
```

### Fix 4: Insert boundary markers before first and after last match

```python
# builder.py — _build_team_flow_edges()
if sorted_boundaries:
    result_seq: list = []
    for i, info in enumerate(timeline):
        result_seq.append(info)
        if i < len(timeline) - 1:
            curr_phase = phase_map.get(info.node_id, 0)
            next_phase = phase_map.get(timeline[i + 1].node_id, 0)
            for date_str, boundary_phase in sorted_boundaries:
                if curr_phase < boundary_phase <= next_phase:
                    result_seq.append(("boundary", date_str))

    # NEW: insert boundaries AFTER last match
    if timeline:
        last_phase = phase_map.get(timeline[-1].node_id, 0)
        for date_str, boundary_phase in sorted_boundaries:
            if boundary_phase > last_phase:
                result_seq.append(("boundary", date_str))

    # NEW: insert boundaries BEFORE first match
    if timeline:
        first_phase = phase_map.get(timeline[0].node_id, 0)
        pre_boundaries = []
        for date_str, boundary_phase in sorted_boundaries:
            if boundary_phase < first_phase:
                pre_boundaries.append(("boundary", date_str))
        result_seq = pre_boundaries + result_seq
```

### Fix 5: Edge visibility / CSS overflow

```css
/* styles.css — fix overflow conflict with Tailwind overflow-hidden */
#cy-wrap {
  overflow: hidden;  /* was: auto — CSS specificity was overriding Tailwind */
}
```

```javascript
// graph.js — increase edge opacity for visibility at compact sizes
'opacity': 0.7,  // was 0.5 for base, home, and away edges
```

### Test: Verify no orphan boundary nodes

```python
def test_no_orphan_intermediate_ranking_nodes(self):
    div = make_division_two_days()
    nodes, edges = GraphBuilder(div).build()
    inter_node_ids = {n.id for n in nodes if n.id.startswith("ranking_day_")}
    sources = {e.source for e in edges}
    targets = {e.target for e in edges}
    for node_id in inter_node_ids:
        assert node_id in targets, f"{node_id!r} has no incoming edges (orphan)"
        assert node_id in sources, f"{node_id!r} has no outgoing edges (orphan)"
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Architecture summary

```
_applyFilters() [controls.js]
  owns: visibility reset, day filter, status filter, edge hiding
  calls: activateTrajectory() as final layer (read-only re: prior state)

activateTrajectory() [trajectory.js]
  reads: cy.elements().filter(e => e.visible())  ← respects prior filters
  writes: hide non-team-visible elements, add team-win/team-loss classes
  does NOT: reset visibility, call clearTrajectory

clearTrajectory() [trajectory.js]
  used by: Reset button, canvas background click
  NOT used inside: _applyFilters, activateTrajectory
```

### Key invariants

1. `_applyFilters` is the ONLY function that calls `cy.elements().style('display', 'element')` to reset visibility
2. `activateTrajectory` uses `.filter(e => e.visible())` to scope its hiding to the already-filtered set
3. Boundary phases in a multi-day DAG must be assigned to BOTH adjacent dates in the UI date-to-phases map
4. Boundary markers in `result_seq` must be checked before the first match AND after the last match, not just between adjacent pairs

### Files modified

| File | Change |
|------|--------|
| `web/js/controls.js` | Single-owner reset, dual-date boundary assignment, conditional relayout, inline `_applyTeamHighlight` |
| `web/js/trajectory.js` | Remove `clearTrajectory()` from `activateTrajectory()`, use `.filter(visible)`, clean unused classes |
| `web/js/graph.js` | Edge opacity 0.5→0.7, remove unused `.dimmed`/`.highlighted` selectors |
| `web/css/styles.css` | `#cy-wrap` overflow: auto→hidden |
| `scraper/graph/builder.py` | Insert boundaries before first + after last match, remove dead `sequence` variable |
| `tests/test_graph_builder.py` | Add `test_no_orphan_intermediate_ranking_nodes` |
