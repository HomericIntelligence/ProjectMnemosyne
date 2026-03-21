---
name: cytoscape-frontend-rewrite
description: Full rewrite of Cytoscape.js tournament visualization — court-slot packing layout, composable filters, multi-team trajectory, single bottom toolbar
category: architecture
date: 2026-02-27
version: 1.0.0
user-invocable: false
---

# Cytoscape.js Frontend Full Rewrite — Court-Slot Layout + Composable Filters

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-27 |
| **Category** | architecture |
| **Objective** | Full rewrite of 5 frontend files (graph.js, trajectory.js, controls.js, index.html, styles.css) to fix sparse layout, broken filter composition, missing edges, unnecessary relayout, and cluttered multi-row UI |
| **Outcome** | ✅ All 163 Python tests pass; all 5 files rewritten cleanly with no regressions |
| **Context** | TitanSchedule — Cytoscape.js sorting network visualization of volleyball tournament DAGs (48 teams, 240 matches, 3 match dates) |

## When to Use

Use this skill when:

- A Cytoscape.js layout uses `globalRow * ROW_HEIGHT` (fixed row height) and produces huge vertical gaps between match nodes at different times
- You need to pack match nodes by time-slot and court (dense grid) rather than sparse row-based layout
- Multiple layout functions (computePositions, rerunLayout, relayoutVisible) duplicate the same 3-pass algorithm
- A team trajectory filter needs to highlight multiple teams simultaneously (not just one at a time)
- A multi-row control bar (team selector row + status filter row + zoom row + day row) needs collapsing into a single toolbar
- You're removing a filter type (status filter) and need to surgically clean state variables + DOM

## Problem Patterns

### Pattern 1: Sparse layout from `globalRow * ROW_HEIGHT`

Old algorithm:
```
globalRow → rawY = globalRow * 30   // 30px per row = 720px for 24 matches
de-collide: push overlapping nodes down by minimum gap
```
**Problem**: All matches in the same phase got spread across 720px even if only 8 courts are used. `MATCH_H=42`, so 8 courts = 336px — but the layout spreads them to 720px because globalRow jumps.

**Solution**: Court-slot packing — group by time slot, sort by court alphabetically, stack at `courtIdx * MATCH_H`. Each time slot = `numCourts * MATCH_H + SLOT_GAP`.

### Pattern 2: 3x duplicated layout algorithm

`computePositions()`, `rerunLayout()`, and `relayoutVisible()` each had identical 3-pass logic:
1. group by phase
2. sort + de-collide within phase
3. compute port node offsets

**Solution**: Extract `_computePackedPositions(nodes, portNodes, phaseRemap)` as shared helper. All three callers delegate to it.

### Pattern 3: Scalar team ID breaks multi-team highlighting

Old: `_activeTeamId = null | number` — a single team ID. Match click cycled through home/away teams one at a time.

**Problem**: Clicking a match should show both teams' paths simultaneously (e.g., to see which team won and where they went). Single scalar forces user to click twice.

**Solution**: `_activeTeamIds = []` (array). Match click sets `_activeTeamIds = teams.filter(role !== 'work').map(t => t.id)`. `activateTrajectory(cy, teamIds)` uses `Set` membership.

### Pattern 4: Status filter state entangled with filter composition

`_hiddenStatuses` was a global Set tracked alongside `_activeDates`. Removing status filters required:
1. Delete `_hiddenStatuses` variable
2. Delete `_initStatusFilters()` function
3. Remove status filter step from `_applyFilters()` (step 3 of 5 → step 3 of 4)
4. Remove status filter buttons from HTML
5. Remove `.status-filter` CSS
6. Remove `initStatusFilters` call from `initControls`

**Key insight**: Status filter was fully self-contained — no other state depended on it. Removal was clean.

## Verified Workflow

### Step 1: Shared layout helper `_computePackedPositions`

```javascript
/**
 * @param {Array} nodes       - non-port nodes: {id, type, phase, time, court, globalRow}
 * @param {Array} portNodes   - port nodes: {id, parentId, portRole}
 * @param {Map|null} phaseRemap - Map<originalPhase, compactIndex> or null
 * @returns {Object}          - {id: {x, y}}
 */
function _computePackedPositions(nodes, portNodes, phaseRemap) {
  const matchPhases  = {};   // compactPhase -> [{id, time, court}]
  const rankingPhases = {};  // compactPhase -> [{id, globalRow}]

  nodes.forEach(n => {
    const rawPhase = n.phase;
    const compactPhase = phaseRemap ? (phaseRemap.get(rawPhase) ?? rawPhase) : rawPhase;
    if (n.type === 'match') {
      if (!matchPhases[compactPhase]) matchPhases[compactPhase] = [];
      matchPhases[compactPhase].push({ id: n.id, time: n.time || '', court: n.court || '', compactPhase });
    } else {
      if (!rankingPhases[compactPhase]) rankingPhases[compactPhase] = [];
      rankingPhases[compactPhase].push({ id: n.id, globalRow: n.globalRow || 0, compactPhase });
    }
  });

  // Match phases: group by time slot, stack by court
  const phaseHeights = {};
  Object.entries(matchPhases).forEach(([compactPhase, matchNodes]) => {
    const byTime = {};
    matchNodes.forEach(m => { (byTime[m.time] = byTime[m.time] || []).push(m); });
    const sortedTimes = Object.keys(byTime).sort();
    let cumOffset = 0;
    const nodeY = {};
    sortedTimes.forEach(t => {
      const slotMatches = byTime[t].slice().sort((a, b) => a.court.localeCompare(b.court));
      slotMatches.forEach((m, courtIdx) => { nodeY[m.id] = cumOffset + courtIdx * MATCH_H; });
      cumOffset += slotMatches.length * MATCH_H + SLOT_GAP;
    });
    phaseHeights[compactPhase] = Math.max(0, cumOffset - SLOT_GAP);
    matchNodes.forEach(m => {
      const pos = { x: Number(compactPhase) * PHASE_WIDTH, y: nodeY[m.id] || 0 };
      parentPositions[m.id] = pos;  positions[m.id] = pos;
    });
  });

  // Ranking phases: center vertically against max match height
  const maxMatchHeight = Object.values(phaseHeights).reduce((max, h) => Math.max(max, h), 0);
  Object.entries(rankingPhases).forEach(([compactPhase, rankNodes]) => {
    const startY = (maxMatchHeight - rankNodes.length * RANKING_ROW_H) / 2;
    rankNodes.sort((a, b) => a.globalRow - b.globalRow);
    rankNodes.forEach((r, idx) => {
      const pos = { x: Number(compactPhase) * PHASE_WIDTH, y: startY + idx * RANKING_ROW_H };
      parentPositions[r.id] = pos;  positions[r.id] = pos;
    });
  });

  // Port nodes: relative offset from parent
  portNodes.forEach(p => {
    const parentPos = parentPositions[p.parentId];
    if (!parentPos) { positions[p.id] = { x: 0, y: 0 }; return; }
    const yOffset = p.portRole === 'home' ? -PORT_H : p.portRole === 'work' ? PORT_H : 0;
    positions[p.id] = { x: parentPos.x, y: parentPos.y + yOffset };
  });

  return positions;
}
```

**Constants used:**
```javascript
const MATCH_H = 44, PORT_H = 14, MATCH_W = 150, PHASE_WIDTH = 180;
const SLOT_GAP = 10, RANKING_ROW_H = 18, RANKING_W = 110;
```

### Step 2: `relayoutVisible` uses phaseRemap

```javascript
function relayoutVisible() {
  const nodes = [], portNodes = [];
  cy.nodes().forEach(n => {
    if (!n.visible()) return;
    const d = n.data();
    if (d.type === 'port') portNodes.push({ id: n.id(), parentId: d.parentId, portRole: d.portRole });
    else nodes.push({ id: n.id(), type: d.type, phase: d.phase, time: d.time, court: d.court, globalRow: d.globalRow });
  });

  // Compact phases: 0,5,13,14 → 0,1,2,3
  const uniquePhases = [...new Set(nodes.map(n => n.phase))].sort((a, b) => a - b);
  const phaseRemap = new Map();
  uniquePhases.forEach((phase, idx) => phaseRemap.set(phase, idx));

  const allPositions = _computePackedPositions(nodes, portNodes, phaseRemap);
  cy.layout({ name: 'preset', positions: n => allPositions[n.id()] || n.position(),
               fit: false, animate: true, animationDuration: 300 }).run();
  setTimeout(() => fitToVisible(40), 350);
}
```

### Step 3: Multi-team trajectory

```javascript
// trajectory.js
function activateTrajectory(cy, teamIds) {
  if (!teamIds || teamIds.length === 0) return;
  const teamIdSet = new Set(teamIds);
  const teamEdges = cy.edges().filter(e => teamIdSet.has(e.data('teamId')));
  if (!teamEdges.length) return;
  const teamPortNodes = teamEdges.connectedNodes();
  const teamParentNodes = teamPortNodes
    .filter(n => n.data('type') === 'port' && n.data('parentId'))
    .map(n => cy.$id(n.data('parentId')))
    .reduce((acc, col) => acc.union(col), cy.collection());
  const teamCollection = teamEdges.union(teamPortNodes).union(teamParentNodes);
  cy.elements().filter(e => e.visible()).difference(teamCollection).style('display', 'none');
  teamEdges.addClass('edge-highlight');

  // Win/loss per team — skip if BOTH home+away selected for same match
  teamIds.forEach(teamId => {
    teamParentNodes.filter('[type="match"][status="finished"]').forEach(node => {
      const teams = node.data('teams') || [];
      const homeTeam = teams.find(t => t.role === 'home');
      const awayTeam = teams.find(t => t.role === 'away');
      if (homeTeam && awayTeam && teamIdSet.has(homeTeam.id) && teamIdSet.has(awayTeam.id)) return;
      const isHome = homeTeam && homeTeam.id === teamId;
      const isAway = awayTeam && awayTeam.id === teamId;
      if (!isHome && !isAway) return;
      const homeWon = node.data('homeWon');
      if (homeWon == null) return;
      node.addClass((isHome ? homeWon : !homeWon) ? 'team-win' : 'team-loss');
    });
  });
}

function clearTrajectory(cy) {
  cy.elements().removeClass('team-win team-loss edge-highlight');
  cy.elements().style('display', 'element');
}
```

### Step 4: `_initNodeClickHandler` for multi-team

```javascript
cy.on('tap', 'node', function(evt) {
  const node = evt.target;
  const type = node.data('type');
  if (type === 'port') return;

  if (type === 'ranking') {
    const teams = node.data('teams') || [];
    if (!teams.length) return;
    _activeTeamIds = [teams[0].id];
    document.getElementById('team-select').value = String(_activeTeamIds[0]);
  } else if (type === 'match') {
    const teams = (node.data('teams') || []).filter(t => t.role !== 'work');
    if (!teams.length) return;
    _activeTeamIds = teams.map(t => t.id);
    document.getElementById('team-select').value = '';  // multiple teams, clear dropdown
  }
  _applyFilters(cy);
});

cy.on('tap', function(evt) {
  if (evt.target !== cy) return;
  document.getElementById('team-select').value = '';
  _activeTeamIds = [];
  clearTrajectory(cy);
  _applyFilters(cy);
});
```

### Step 5: Single bottom toolbar HTML

```html
<div id="bottom-toolbar" class="bg-white border-t border-gray-200 px-3 flex items-center gap-2 flex-shrink-0" style="height:40px">
  <span class="text-xs font-medium text-gray-500 flex-shrink-0">Day:</span>
  <div id="day-filter-row" class="flex items-center gap-1"></div>
  <div class="w-px h-5 bg-gray-200 flex-shrink-0 mx-1"></div>
  <span class="text-xs font-medium text-gray-500 flex-shrink-0">Team:</span>
  <select id="team-select" class="text-xs border border-gray-300 rounded px-1.5 py-0.5 min-w-32 max-w-48">
    <option value="">All Teams</option>
  </select>
  <div class="ml-auto flex items-center gap-1">
    <button id="zoom-fit"  class="toolbar-btn">Fit</button>
    <button id="zoom-in"   class="toolbar-btn">+</button>
    <button id="zoom-out"  class="toolbar-btn">−</button>
    <button id="relayout"  class="toolbar-btn">Reset</button>
    <div class="w-px h-5 bg-gray-200 flex-shrink-0 mx-1"></div>
    <button id="export-png" class="toolbar-btn-primary">PNG</button>
    <button id="export-svg" class="toolbar-btn-primary">SVG</button>
    <button id="export-pdf" class="toolbar-btn-primary">PDF</button>
    <div class="w-px h-5 bg-gray-200 flex-shrink-0 mx-1"></div>
    <a id="aes-link" href="#" target="_blank" rel="noopener" class="toolbar-btn hidden">AES ↗</a>
  </div>
</div>
```

### Step 6: CSS additions for toolbar

```css
.toolbar-btn {
  background: white; color: #374151; border: 1px solid #d1d5db;
  border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer;
  white-space: nowrap; text-decoration: none; display: inline-flex; align-items: center;
}
.toolbar-btn:hover { background: #f3f4f6; }

.toolbar-btn-primary {
  background: #2563eb; color: white; border: 1px solid #1d4ed8;
  border-radius: 4px; padding: 2px 8px; font-size: 11px; cursor: pointer;
}
.toolbar-btn-primary:hover { background: #1d4ed8; }
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Architecture summary (filter composition invariants — see also: cytoscape-filter-compose)

```
_applyFilters(cy) [controls.js]
  Step 1: cy.elements().removeClass('team-win team-loss edge-highlight')
          cy.elements().style('display', 'element')   ← SOLE reset owner
  Step 2: day filter (hide nodes outside selected phases)
  Step 3: hide edges where source or target is hidden
  Step 4: activateTrajectory(cy, _activeTeamIds)   ← layers on top
  Step 5: relayoutVisible() or fitToVisible(40)

activateTrajectory(cy, teamIds)  [trajectory.js]
  - teamIds: Array<number>  (was scalar)
  - uses Set for O(1) membership
  - cy.elements().filter(e => e.visible()) ← respects prior filters
  - teamEdges.addClass('edge-highlight')
  - win/loss: skip if both home+away in match are in teamIdSet

clearTrajectory(cy)  [trajectory.js]
  - removes: team-win, team-loss, edge-highlight
  - resets: cy.elements().style('display', 'element')
  - called only by: Reset button, canvas background click
```

### New Cytoscape style selectors

```javascript
// ADDED: edge highlight class (opacity override)
{ selector: 'edge.edge-highlight', style: { 'opacity': 1.0, 'width': 2.5 } },

// REMOVED: edge[active = false] selector (display:none approach instead)
// REMOVED: .dimmed / .highlighted selectors
// CHANGED: base edge opacity 0.7 → 0.6
```

### Files rewritten

| File | Key change |
|------|-----------|
| `web/js/graph.js` | Court-slot packing, shared `_computePackedPositions`, new constants |
| `web/js/trajectory.js` | Array teamIds, multi-team coloring, `edge-highlight` class |
| `web/js/controls.js` | `_activeTeamIds[]`, removed status filter, match click → all teams |
| `web/index.html` | Single 40px bottom toolbar, loading/error overlays inside `#cy-wrap` |
| `web/css/styles.css` | Added `.toolbar-btn`/`.toolbar-btn-primary`, updated card widths, removed `.status-filter`/`.trajectory-pulse` |

### Card widths (must match JS constants)

```
MATCH_W = 150  →  .match-card { width: 144px }  (150 - 6px padding)
RANKING_W = 110  →  .ranking-card { max-width: 106px }  (110 - 4px)
```
