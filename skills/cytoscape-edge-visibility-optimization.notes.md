# Session Notes — Cytoscape Edge Visibility Optimization

## Project

TitanSchedule — tournament DAG visualization. Cytoscape.js 3.28, CDN-only, no build tools.
Graph: ranking nodes (start/intermediate/end) + match nodes + port nodes + team_flow/follow_on edges.

## Bugs Fixed (in order discovered)

### Bug 1: Start ranking column always visible on day filter
- File: `web/js/controls.js` `_applyFilters`
- Line: `const visiblePhases = new Set([0]);` — phase 0 hardcoded
- Fix: conditional on `_activeDates.has(firstDate)`, mirroring maxPhase logic

### Bug 2: Work team excluded from node-click trajectory
- File: `web/js/controls.js` `_initNodeClickHandler`
- Line: `.filter(t => t.role !== 'work')` — explicit exclusion
- Fix: remove filter entirely

### Bug 3: Nodes and edges draggable/selectable
- File: `web/js/graph.js` `initGraph`
- Fix: `autoungrabify: true, autounselectify: true` in cytoscape() options

### Bug 4: Slow rendering from always-visible edges
- Root: `cy.elements().style('display', 'element')` in resets + edges never hidden
- Fix: 4-file change to hide edges at baseline

## Files Changed for Edge Visibility

| File | Change |
| ------ | -------- |
| `web/js/app.js` | `cytoscapeInstance.edges().style('display', 'none')` after initGraph |
| `web/js/controls.js` `_applyFilters` | Step 3: `cy.edges().style('display', 'none')` (was: hide only endpoint-hidden edges) |
| `web/js/controls.js` `_applyHighlight` | `cy.edges().style('display', 'none')` + `teamEdges.style('display', 'element')` |
| `web/js/controls.js` `_clearHighlight` | `cy.edges().style('display', 'none')` after removeClass |
| `web/js/trajectory.js` `activateTrajectory` | `teamEdges.style('display', 'element')` added; node hide changed from `cy.elements()` to `cy.nodes()` |
| `web/js/trajectory.js` `clearTrajectory` | Split: `cy.nodes().style('display', 'element')` + `cy.edges().style('display', 'none')` |

## Also Fixed in Same Session (separate SKILL)

DAG routing bug: unscheduled follow-on bracket matches were bypassed. Teams went directly from last pool port to ranking_end, skipping the crossover bracket. Fix used deferred `ranking_end` edge pattern — see `codebase-quality-plan-execution` skill.
