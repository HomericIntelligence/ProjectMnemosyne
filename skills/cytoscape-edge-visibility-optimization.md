---
name: cytoscape-edge-visibility-optimization
description: Cytoscape.js DAG visualization bug fixes and performance patterns. Covers
  edge-at-baseline-hidden pattern, read-only graph config, day-filter phase boundary
  visibility, and role-complete trajectory highlighting.
category: tooling
date: '2026-03-19'
version: 1.0.0
---
# Cytoscape.js Edge Visibility & DAG Interaction Patterns

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-02-28 |
| Objective | Fix slow rendering + 4 interaction bugs in a Cytoscape.js tournament DAG |
| Outcome | **Success** — all bugs fixed, rendering noticeably faster |
| Codebase | TitanSchedule — Python scraper + Cytoscape.js frontend (CDN, no build tools) |
| Cytoscape version | 3.28 |

## When to Use

Use this skill when:
1. A Cytoscape graph with many edges renders slowly (pan/zoom/layout stutter)
2. Nodes or edges are accidentally draggable/selectable in a read-only visualization
3. A day/phase filter is hiding the correct match columns but leaving start/end ranking columns always visible
4. Node-click trajectory only highlights some team roles (e.g., missing work team)
5. Edge highlight state leaks between clear/reset operations

## Verified Patterns

---

### Pattern 1 — Hide Edges at Baseline, Show on Demand

**Problem:** All edges rendered at all times → layout and pan/zoom are slow with 100+ bezier curves.

**Solution:** Edges default to `display: none`. Only shown when a team is actively selected.

**4-file change — touch every place that resets or shows edges:**

```javascript
// app.js — hide immediately after initGraph
const cytoscapeInstance = initGraph(jsonData);
cytoscapeInstance.edges().style('display', 'none');

// controls.js — _applyFilters Step 3: hide ALL edges, not just endpoint-hidden ones
cy.edges().style('display', 'none');
// (activateTrajectory will show the selected team's edges in step 4)

// controls.js — _clearHighlight: restore edges to hidden, not 'element'
cy.edges().style('display', 'none');

// trajectory.js — activateTrajectory: explicitly show team edges
teamEdges.style('display', 'element');

// trajectory.js — clearTrajectory: nodes → element, edges → none
cy.nodes().style('display', 'element');
cy.edges().style('display', 'none');
```

**Key insight:** `cy.elements().style('display', 'element')` in a reset accidentally re-shows all edges. Every reset path must be audited: `_applyFilters`, `_clearHighlight`, `clearTrajectory`, and the initial load in `app.js`.

**Also update `_applyHighlight` (node-click highlight):**
```javascript
// Before highlighting, hide all edges, then show only team edges
cy.edges().style('display', 'none');
teamEdges.style('display', 'element');
teamEdges.addClass('edge-highlight');
```

---

### Pattern 2 — Read-Only Graph (No Drag, No Select)

**Problem:** Users can grab and move nodes; selection border appears on click.

**Solution:** Two Cytoscape init options — add alongside `userZoomingEnabled`/`userPanningEnabled`:

```javascript
cy = cytoscape({
  userZoomingEnabled: true,
  userPanningEnabled: true,
  boxSelectionEnabled: false,
  autoungrabify: true,     // nodes cannot be grabbed/dragged
  autounselectify: true,   // nodes/edges cannot be selected (no selection border)
  // ...
});
```

`autoungrabify` and `autounselectify` are instance-level options, not per-node styles. They affect all elements.

---

### Pattern 3 — Day Filter: Phase 0 Visibility Rule

**Problem:** Start ranking column (phase 0) always visible regardless of which day is selected — was hardcoded into `visiblePhases`.

**Root cause:**
```javascript
// WRONG — phase 0 always included
const visiblePhases = new Set([0]);
```

**Fix:** Mirror the same conditional used for `maxPhase` (end ranking):
```javascript
const visiblePhases = new Set();
const firstDate = sortedDates[0];
const lastDate = sortedDates[sortedDates.length - 1];

// Phase 0 (start ranking) only when first date selected
if (firstDate && _activeDates.has(firstDate)) {
  visiblePhases.add(0);
}
// End ranking only when last date selected
if (lastDate && _activeDates.has(lastDate)) {
  visiblePhases.add(maxPhase);
}
```

**Mental model:** Phase 0 and `maxPhase` are boundary columns. Show boundary column X only when the adjacent date that "owns" that boundary is selected.

---

### Pattern 4 — Include All Team Roles in Node-Click Trajectory

**Problem:** Clicking a match node highlighted home and away teams' paths but not the work team's path.

**Root cause:**
```javascript
// WRONG — work team filtered out
const teams = (node.data('teams') || []).filter(t => t.role !== 'work');
```

**Fix:** Remove the filter entirely:
```javascript
} else if (type === 'match') {
  const teams = node.data('teams') || [];
  if (teams.length === 0) return;
  clickedTeamIds = teams.map(t => t.id);
}
```

Work teams have `team_flow` edges in the DAG just like home/away teams. The filter was an explicit exclusion that was incorrect for the use case.

---

## Verified Workflow

Steps that worked:
1. Step 1
2. Step 2

## Failed Attempts / Pitfalls

### Pitfall 1 — `cy.elements().style('display', 'element')` in reset re-shows all edges

Any reset that calls `cy.elements().style('display', 'element')` will undo edge hiding. Must split into:
```javascript
cy.nodes().style('display', 'element');
cy.edges().style('display', 'none');
```

Audit every function that resets state: `clearTrajectory`, `_clearHighlight`, `_applyFilters` Step 1.

### Pitfall 2 — `activateTrajectory` assumed edges were already visible

Before the optimization, `activateTrajectory` never explicitly showed edges because they were always visible. After hiding edges at baseline, it must explicitly call `teamEdges.style('display', 'element')`. Easy to miss — the function appeared to work but showed no edges.

### Pitfall 3 — `_applyHighlight` (node-click) is a separate code path from `activateTrajectory` (dropdown)

Both paths need the edge show/hide treatment independently. `_applyHighlight` in `controls.js` collects team edges and highlights them, but is never routed through `activateTrajectory`. Must add `cy.edges().style('display', 'none')` + `teamEdges.style('display', 'element')` there too.

### Pitfall 4 — Cytoscape stylesheet `display: none` vs imperative `.style('display', 'none')`

Cytoscape stylesheet rules (in the `style:` array at init) cannot easily be overridden per-element for `display`. Use imperative `.style()` calls for dynamic show/hide. The stylesheet is best for static visual properties (colors, sizes, opacity).

---

## Results & Parameters

### Cytoscape Init (read-only + performance)
```javascript
cy = cytoscape({
  container: document.getElementById('cy'),
  elements: jsonData.elements,
  userZoomingEnabled: true,
  userPanningEnabled: true,
  boxSelectionEnabled: false,
  autoungrabify: true,       // ← read-only drag
  autounselectify: true,     // ← read-only select
  minZoom: 0.05,
  maxZoom: 3,
  // ...
});
// After init:
cy.edges().style('display', 'none');  // ← baseline hidden
```

### Edge Visibility State Machine
```
Initial load:         edges hidden
Day filter applied:   edges hidden  (activateTrajectory shows team edges if team selected)
Team selected:        team edges visible, all others hidden
Team cleared:         edges hidden
Node clicked:         team edges visible (highlight mode), all others hidden
Node click cleared:   edges hidden
Reset button:         edges hidden
```

## Environment

- Cytoscape.js 3.28 (CDN)
- cytoscape-node-html-label extension (CDN)
- No build tools — plain `<script>` tags
- Files: `web/js/graph.js`, `controls.js`, `trajectory.js`, `app.js`
