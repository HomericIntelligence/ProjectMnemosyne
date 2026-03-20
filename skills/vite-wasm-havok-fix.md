---
name: vite-wasm-havok-fix
description: "Skill: vite-wasm-havok-fix"
category: debugging
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
# Skill: vite-wasm-havok-fix

## Overview

| Field | Value |
|-------|-------|
| Date | 2026-03-03 |
| Objective | Fix blue screen after clicking Start caused by Havok WASM 404 in Vite dev server |
| Outcome | Success — game renders field, players, ball after fix |
| Category | debugging |
| Project | Soccer Stars (Babylon.js 5v5 browser game) |

---

## When to Use

Trigger conditions for this fix:

- Babylon.js + Havok physics project using Vite
- Game shows only `clearColor` background (e.g. blue/sky screen) after scene transition
- Console shows a 404 for `HavokPhysics.wasm` or similar `.wasm` file
- `HavokPhysics()` promise never resolves (or rejects silently) because all subsequent setup is inside `await HavokPhysics()`
- `@babylonjs/havok` is listed in `optimizeDeps.include` in `vite.config.ts`

---

## Root Cause

Vite's `optimizeDeps.include` pre-bundles listed packages into `node_modules/.vite/deps/`. The Havok Emscripten module resolves `HavokPhysics.wasm` **relative to its own script's URL** (`import.meta.url`). When pre-bundled, the script lives in `.vite/deps/` but the `.wasm` file was never copied there — resulting in a `fetch()` 404. Since `HavokPhysics()` is the very first `await` in `_init()`, everything downstream (lights, field, players, HUD) never runs, leaving only the scene's `clearColor`.

---

## Verified Workflow

### Step 1 — Fix `vite.config.ts`

Move `@babylonjs/havok` from `include` to `exclude`. Also remove any unused packages (e.g. `yuka`) from `include`.

```ts
// vite.config.ts
optimizeDeps: {
  include: ['@babylonjs/core', '@babylonjs/gui'],
  exclude: ['@babylonjs/havok']
}
```

`exclude` tells Vite to serve the raw ESM from `node_modules/@babylonjs/havok/` where `HavokPhysics.wasm` lives alongside the JS — so the relative `fetch()` resolves correctly.

### Step 2 — Add visible loading/error UI in the scene

Silent `console.error` failures produce a confusing blank screen. Replace with on-screen feedback:

```ts
// In constructor
private _loadingUI!: AdvancedDynamicTexture;
private _loadingText!: TextBlock;

constructor(...) {
  // ...scene setup...
  this._showLoadingUI();
  engine.runRenderLoop(() => this._scene.render());
  this._init().catch((err) => {
    console.error(err);
    this._showErrorUI(err instanceof Error ? err.message : String(err));
  });
}

private _showLoadingUI(): void {
  this._loadingUI = AdvancedDynamicTexture.CreateFullscreenUI('loadingUI', true, this._scene);
  this._loadingText = new TextBlock('loadingText', 'Loading physics...');
  this._loadingText.color = 'white';
  this._loadingText.fontSize = 32;
  this._loadingUI.addControl(this._loadingText);
}

private _hideLoadingUI(): void {
  this._loadingUI.dispose();
}

private _showErrorUI(message: string): void {
  if (this._loadingUI) {
    this._loadingText.text = `Error: ${message}`;
    this._loadingText.color = 'red';
    this._loadingText.fontSize = 24;
  }
}
```

Call `this._hideLoadingUI()` immediately after `await HavokPhysics()` succeeds.

### Step 3 — Verify

```bash
npx tsc --noEmit    # must be clean
npm run dev         # click Start → game renders
# check browser console: no 404 for .wasm
npx vite build      # must succeed
```

---

## Failed Attempts

| Attempt | What Was Tried | Why It Failed | Lesson Learned |
|---------|----------------|---------------|----------------|
| N/A | Direct approach worked | N/A | Solution was straightforward |
## Results & Parameters

### Working `vite.config.ts`

```ts
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 3000,
    open: true
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  },
  optimizeDeps: {
    include: ['@babylonjs/core', '@babylonjs/gui'],
    exclude: ['@babylonjs/havok']
  }
})
```

### Key imports for loading UI

```ts
import { AdvancedDynamicTexture, TextBlock } from '@babylonjs/gui';
```

Note: `AdvancedDynamicTexture` does not have an `isDisposed` property in Babylon.js 7.x — guard with a plain truthiness check (`if (this._loadingUI)`) instead.

### Build output confirmation

- `dist/assets/HavokPhysics-*.wasm` appears in build output (confirms WASM is bundled)
- Bundle size: ~5.7MB JS + ~2.1MB WASM (expected for Babylon.js)
