# Raw Notes — cytoscape-frontend-rewrite

## Session Context

- **Date**: 2026-02-27
- **Project**: TitanSchedule (tournament sorting network visualization)
- **Stack**: Cytoscape.js 3.28 + cytoscape-node-html-label + Tailwind CSS CDN + jsPDF — no build tools

## Files Modified

```
web/js/graph.js        — full rewrite
web/js/trajectory.js   — full rewrite
web/js/controls.js     — full rewrite
web/index.html         — full rewrite
web/css/styles.css     — full rewrite
```

**NOT touched**: app.js, export.js, tooltips.js, scraper/, tests/, scripts/

## Test Results

```
163 passed in 26.22s  (all Python/scraper tests, no frontend tests)
```

## Design Decisions

### Why court-slot packing vs. de-collision

Old approach: `globalRow * ROW_HEIGHT` (30px) + de-collision push-down. Problem: globalRow has gaps (team #1 = row 0, team #48 = row 47) causing 1400px tall phases even with 8 courts.

New approach: group matches by time, stack by court index. 8 courts = 8 * 44px + 10px gap = 362px. Eliminates the vertical-gap problem completely.

### Why phaseRemap is a Map not Object

In JavaScript, object keys are always strings. `Object.keys(byPhase).map(Number)` is required when the values are used as numbers. Using `Map<number, number>` avoids this implicit conversion and is safer for the shared helper signature.

### Why edge-highlight is a class, not inline style

Using `edge.addClass('edge-highlight')` instead of `edge.style('opacity', 1.0)` means:
1. `cy.elements().removeClass('edge-highlight')` in step 1 of `_applyFilters` cleanly removes it
2. Cytoscape's stylesheet cascade handles specificity correctly
3. The inline style `display: none` from day filter doesn't conflict with the class

### Why clearTrajectory is NOT called inside _applyFilters

`_applyFilters` step 1 directly does `cy.elements().style('display', 'element')` and `cy.elements().removeClass(...)`. Calling `clearTrajectory(cy)` would do the same thing but is unnecessary indirection. The single-owner pattern means the reset is inline, not delegated.

`clearTrajectory` is only called from:
1. Reset button click handler — user explicitly requests full reset
2. Canvas background tap — user clicks away to deselect

### Toolbar ID requirement

`export.js` (unchanged) requires: `export-png`, `export-svg`, `export-pdf`
`app.js` (unchanged) requires: `loading`, `error-banner`, `error-msg`, `event-name`, `division-name`, `scraped-at`, `aes-link`
`controls.js` requires: `day-filter-row`, `team-select`, `zoom-fit`, `zoom-in`, `zoom-out`, `relayout`
`graph.js` requires: `cy`

All verified present in new index.html via `grep -oE 'id="[^"]+"'`.

## Data Contract (unchanged)

- Node types: `ranking` (phases 0/N), `match` (phases 1..N-1), `port` (child of match)
- Port nodes: `data.parentId` (string) — NOT `data.parent` (reserved by Cytoscape compound hierarchy)
- Edges: `type="team_flow"`, `teamId`, `teamName`, `role` ("home"/"away"/"work")
- Match nodes: `teams[]` with `{id, name, role}`, `homeWon` (bool|null), `status`, `time` (ISO), `court` (string)
- Phase metadata: in `metadata.phases[]` with `{phase, type, date}` — types: "match", "ranking_intermediate"
