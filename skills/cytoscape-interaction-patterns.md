---
name: cytoscape-interaction-patterns
description: Patterns for separating node-click highlight (visual dimming) from filter-based
  hiding in Cytoscape.js, and for working around cytoscape-node-html-label HTML overlay
  persistence. Use when node click should be visual-only (not hide nodes), or when
  HTML overlay cards remain visible after their Cytoscape node is hidden.
category: architecture
date: 2026-02-28
version: 1.0.0
user-invocable: false
---
# Cytoscape.js Interaction Patterns — Highlight vs Filter + HTML Overlay Fixes

## Overview

| Attribute | Value |
|-----------|-------|
| **Date** | 2026-02-28 |
| **Category** | architecture |
| **Objective** | Fix 5 bugs in a Cytoscape.js tournament visualization: (1) node click hides nodes instead of dimming, (2) team dropdown doesn't compact layout, (3) day filter shows end ranking on wrong days, (4) HTML overlay cards persist after their node is hidden, (5) node click + day filter interaction corrupts state |
| **Outcome** | ✅ All 5 bugs fixed, 163 Python tests passing, no regressions |
| **Context** | TitanSchedule — Cytoscape.js sorting network visualization of volleyball tournament DAGs. Uses `cytoscape-node-html-label@1.2.2` for rich match/ranking card overlays. Related prior skills: `cytoscape-frontend-rewrite`, `cytoscape-filter-compose`. |

## When to Use

Use this skill when:

- Node click in Cytoscape triggers `activateTrajectory()` (which hides elements) but you want click to be a visual-only highlight (dim others, keep everything visible)
- `cytoscape-node-html-label` HTML overlays (`.match-card`, `.ranking-card` divs) remain visible on screen even after their Cytoscape node's `display` is set to `'none'`
- A terminal/end-ranking phase column appears when the user filters to non-final days
- Filtering to a team via dropdown should compact the layout but doesn't
- Clicking a node sets filter state that then interferes when a day-filter button is later clicked

## Root Causes

### Bug 1+5: Node click conflates highlight with filter

The original `_initNodeClickHandler` set `_activeTeamIds` and called `_applyFilters()`, which invoked `activateTrajectory()` → `display:none` on non-team nodes. This meant:
- Node click hid all other nodes (not a visual-only dim)
- Clicking a day button after clicking a node showed only that team's matches for that day (state corruption)

### Bug 4: `cytoscape-node-html-label@1.2.2` doesn't hide overlays on `display:none`

Known GitHub Issue #14 (unfixed). When Cytoscape sets a node to `display: 'none'` (via day filter), the corresponding HTML `<div>` overlay remains rendered on the canvas. The extension does not check node visibility before rendering.

### Bug 3: `maxPhase` always visible regardless of date selection

The original code always put `maxPhase` (end ranking column) in `visiblePhases`, so it showed even when filtering to Day 1. End rankings should only appear when the tournament's final date is selected.

### Bug 2: Team trajectory doesn't compact layout

Step 5 of `_applyFilters` checked `if (!showAllDays)` to trigger `relayoutVisible()`. Team-only filter (`showAllDays=true, hasTeam=true`) fell through to the "preserve viewport" branch.

## Verified Workflow

### Pattern 1: `_highlightState` global shared by graph.js card builders

```javascript
// graph.js — module global (add after _courtColorMap)
let _highlightState = { active: false, teamIds: new Set() };
```

Both `buildMatchCardHTML` and `buildRankingCardHTML` read this to add inline `opacity:0.15` to non-team card divs. This gives visual dimming without any Cytoscape `display` changes.

```javascript
// buildMatchCardHTML — replace single courtStyle with styleParts array
const courtColor = _courtColorMap ? _courtColorMap.get(data.court) : null;
const styleParts = [];
if (courtColor) {
  styleParts.push(`background:${courtColor.bg}`, `border-color:${courtColor.border}`);
}
if (_highlightState.active) {
  const isTeamNode = teams.some(t => t.role !== 'work' && _highlightState.teamIds.has(t.id));
  if (!isTeamNode) styleParts.push('opacity:0.15');
}
const styleAttr = styleParts.length > 0 ? ` style="${styleParts.join(';')}"` : '';
let html = `<div class="match-card"${styleAttr}>`;

// buildRankingCardHTML — add dimStyle before let html
let dimStyle = '';
if (_highlightState.active) {
  const nodeTeams = data.teams || [];
  const isTeamNode = nodeTeams.some(t => _highlightState.teamIds.has(t.id));
  if (!isTeamNode) dimStyle = ' style="opacity:0.15"';
}
let html = `<div class="ranking-card"${dimStyle}>`;
```

### Pattern 2: Cytoscape dimmed CSS classes (for canvas-rendered edges/shapes)

Add to the Cytoscape `style` array after `node.team-loss`:

```javascript
{ selector: 'node.dimmed', style: { 'opacity': 0.15 } },
{ selector: 'edge.dimmed', style: { 'opacity': 0.08 } },
```

### Pattern 3: `node:hidden` template as last entry (Bug 4 workaround)

`cytoscape-node-html-label` iterates templates with `.slice().reverse()` — last entry wins. Add a catch-all `node:hidden` template that returns empty string as the **final** entry in the `nodeHtmlLabel` array:

```javascript
cy.nodeHtmlLabel([
  {
    query: 'node[type="match"]',
    halign: 'center', valign: 'center',
    tpl: function(data) { return buildMatchCardHTML(data); },
  },
  {
    query: 'node[type="ranking"]',
    halign: 'center', valign: 'center',
    tpl: function(data) { return buildRankingCardHTML(data); },
  },
  // MUST BE LAST — extension checks in reverse; this clears overlays for hidden nodes
  {
    query: 'node:hidden',
    halign: 'center', valign: 'center',
    tpl: function() { return ''; },
  },
]);
```

**Why last**: The extension calls `templates.slice().reverse()` and returns the first match. If `node:hidden` were first in the array, it would be last to be checked and never win.

### Pattern 4: Force HTML overlay re-render by nudging node data

`cytoscape-node-html-label` only re-renders a card when node data changes. After updating `_highlightState`, force a re-render by touching a dummy property:

```javascript
// Trigger re-render of all visible non-port nodes
cy.nodes().filter(n => n.visible() && n.data('type') !== 'port').forEach(n => {
  n.data('_hl', Date.now());
});

// On clear: reset to 0
cy.nodes().filter(n => n.visible() && n.data('type') !== 'port').forEach(n => {
  n.data('_hl', 0);
});
```

Any data change triggers the template function to re-run, picking up the new `_highlightState`.

### Pattern 5: `_applyHighlight` vs `_applyFilters` separation (controls.js)

```javascript
// Module state
let _highlightedTeamIds = [];   // node-click highlight only
// _activeTeamIds remains for dropdown/filter use

function _applyHighlight(cy, teamIds) {
  _clearHighlight(cy);
  _highlightedTeamIds = teamIds;
  _highlightState.active = true;
  _highlightState.teamIds = new Set(teamIds);

  const teamIdSet = new Set(teamIds);
  const teamEdges = cy.edges().filter(e => teamIdSet.has(e.data('teamId')));
  if (teamEdges.length === 0) {
    _highlightedTeamIds = [];
    _highlightState.active = false;
    _highlightState.teamIds = new Set();
    return;
  }

  const teamPortNodes = teamEdges.connectedNodes();
  const teamParentNodes = teamPortNodes
    .filter(n => n.data('type') === 'port' && n.data('parentId'))
    .map(n => cy.$id(n.data('parentId')))
    .reduce((acc, col) => acc.union(col), cy.collection());
  const teamCollection = teamEdges.union(teamPortNodes).union(teamParentNodes);

  // Dim non-team visible elements (no hiding)
  cy.elements().filter(e => e.visible()).difference(teamCollection).addClass('dimmed');
  teamEdges.addClass('edge-highlight');

  // Win/loss coloring (same logic as activateTrajectory)
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

  // Force HTML overlay re-render
  cy.nodes().filter(n => n.visible() && n.data('type') !== 'port').forEach(n => {
    n.data('_hl', Date.now());
  });
}

function _clearHighlight(cy) {
  _highlightedTeamIds = [];
  _highlightState.active = false;
  _highlightState.teamIds = new Set();
  cy.elements().removeClass('dimmed team-win team-loss edge-highlight');
  cy.nodes().filter(n => n.visible() && n.data('type') !== 'port').forEach(n => {
    n.data('_hl', 0);
  });
}
```

### Pattern 6: Node click handler — highlight-only, toggle support

```javascript
function _initNodeClickHandler(cy) {
  cy.on('tap', 'node', function(evt) {
    const node = evt.target;
    const type = node.data('type');
    if (type === 'port') return;

    let clickedTeamIds = [];
    if (type === 'ranking') {
      const teams = node.data('teams') || [];
      if (teams.length === 0) return;
      clickedTeamIds = [teams[0].id];
    } else if (type === 'match') {
      const teams = (node.data('teams') || []).filter(t => t.role !== 'work');
      if (teams.length === 0) return;
      clickedTeamIds = teams.map(t => t.id);
    }

    // Toggle: clicking same node again clears highlight
    const alreadyHighlighted =
      _highlightedTeamIds.length === clickedTeamIds.length &&
      clickedTeamIds.every(id => _highlightedTeamIds.includes(id));

    if (alreadyHighlighted) {
      _clearHighlight(cy);
    } else {
      _applyHighlight(cy, clickedTeamIds);
    }
    // NOTE: does NOT touch _activeTeamIds or the team dropdown
  });

  // Background click: clear highlight only, do NOT clear filters
  cy.on('tap', function(evt) {
    if (evt.target !== cy) return;
    _clearHighlight(cy);
  });
}
```

### Pattern 7: `_applyFilters` — fix maxPhase visibility (Bug 3)

Replace always-visible `maxPhase` with conditional on last date:

```javascript
// Old (wrong): always shows end ranking
const visiblePhases = new Set([0, maxPhase]);

// New: end ranking only when last tournament date is selected
const visiblePhases = new Set([0]);
const sortedDates = Array.from(_dateToPhases.keys()).sort();
const lastDate = sortedDates[sortedDates.length - 1];
if (lastDate && _activeDates.has(lastDate)) {
  visiblePhases.add(maxPhase);
}
```

### Pattern 8: Compact layout for team filter too (Bug 2)

```javascript
// Old: only compact on day filter
if (!showAllDays) { relayoutVisible(); _positionsCompacted = true; }

// New: compact on day filter OR team filter
if (!showAllDays || hasTeam) { relayoutVisible(); _positionsCompacted = true; }
```

### Pattern 9: `_clearHighlight` before every `_applyFilters` call (Bug 5)

Every UI control that calls `_applyFilters` must first call `_clearHighlight`:

```javascript
// All button
_clearHighlight(cy);
_applyFilters(cy);

// Date buttons
_clearHighlight(cy);
_applyFilters(cy);

// Team dropdown change
_clearHighlight(cy);
_applyFilters(cy);

// Reset button
_highlightedTeamIds = [];
_clearHighlight(cy);
clearTrajectory(cy);
_applyFilters(cy);
```

Also: `_applyFilters` Step 1 must include `dimmed` in its class reset:
```javascript
cy.elements().removeClass('team-win team-loss edge-highlight dimmed');
```

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### State architecture summary

```
controls.js state:
  _activeTeamIds[]      → set by team dropdown; drives activateTrajectory (display:none)
  _activeDates Set      → set by day buttons; drives phase visibility (display:none)
  _highlightedTeamIds[] → set by node click; drives _applyHighlight (opacity dimming)
  _positionsCompacted   → true when relayoutVisible() has run

graph.js state:
  _highlightState       → { active: bool, teamIds: Set } — shared with tpl functions
  _courtColorMap        → court → {bg, border} — unchanged

Interaction contract:
  node click     → _applyHighlight (visual only, no display:none)
  background tap → _clearHighlight only (preserves _activeDates, _activeTeamIds)
  day buttons    → _clearHighlight, then _applyFilters
  team dropdown  → _clearHighlight, then _applyFilters
  reset button   → _highlightedTeamIds=[], _clearHighlight, clearTrajectory, _applyFilters
```

### `_applyFilters` corrected Step 5

```javascript
// Was: if (!showAllDays)
// Now: compact on day filter OR team filter
if (!showAllDays || hasTeam) {
  relayoutVisible();
  _positionsCompacted = true;
} else if (_positionsCompacted) {
  rerunLayout();
  _positionsCompacted = false;
}
```

### `_applyFilters` corrected Step 2 (end ranking visibility)

```javascript
const maxPhase = Math.max(...cy.nodes().map(n => n.data('phase')));
const visiblePhases = new Set([0]);  // start ranking always visible
const sortedDates = Array.from(_dateToPhases.keys()).sort();
const lastDate = sortedDates[sortedDates.length - 1];
if (lastDate && _activeDates.has(lastDate)) {
  visiblePhases.add(maxPhase);  // end ranking only on last date
}
// then add phases for each _activeDates entry...
```

### Files modified

| File | Changes |
|------|---------|
| `web/js/graph.js` | `_highlightState` global; `buildMatchCardHTML` styleParts; `buildRankingCardHTML` dimStyle; `node.dimmed`/`edge.dimmed` CSS; `node:hidden` template (last) |
| `web/js/controls.js` | `_highlightedTeamIds`; `_applyHighlight`; `_clearHighlight`; rewritten `_initNodeClickHandler`; `_applyFilters` Step 1 (`dimmed`), Step 2 (maxPhase conditional), Step 5 (`hasTeam`); `_clearHighlight` before every `_applyFilters` |

### CSS additions to Cytoscape style array

```javascript
{ selector: 'node.dimmed', style: { 'opacity': 0.15 } },
{ selector: 'edge.dimmed', style: { 'opacity': 0.08 } },
// Place these AFTER team-win/team-loss, BEFORE :selected
```

## References

- `cytoscape-node-html-label` GitHub Issue #14 — HTML overlays not hidden on `display:none`
- Related skills: `cytoscape-frontend-rewrite` (layout), `cytoscape-filter-compose` (filter composition)
- `cytoscape-node-html-label` template matching order: `.slice().reverse()` — last entry = highest priority
