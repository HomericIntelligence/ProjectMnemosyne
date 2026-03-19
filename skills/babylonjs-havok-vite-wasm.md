---
name: babylonjs-havok-vite-wasm
description: "---"
category: debugging
date: 2026-03-19
version: "1.0.0"
user-invocable: false
---
---
name: babylonjs-havok-vite-wasm
description: "TRIGGER CONDITIONS: When Babylon.js + Havok physics fails to initialize in a Vite dev server — blue/blank screen, WASM MIME type errors, 'incorrect response MIME type: Expected application/wasm', or 'No camera defined' on scene load"
user-invocable: false
category: debugging
date: 2026-03-03
---

# babylonjs-havok-vite-wasm

Fix Havok WASM loading failures in Babylon.js projects using Vite dev server, plus the cascading "No camera defined" render error during async initialization.

## Overview

| Item | Details |
|------|---------|
| Date | 2026-03-03 |
| Objective | Fix blue screen caused by Havok physics WASM failing to load in Vite dev server |
| Outcome | Success |

## When to Use

- Babylon.js + `@babylonjs/havok` project shows a blank/blue screen with no error visible on screen
- DevTools console shows: `wasm streaming compile failed: TypeError: Failed to execute 'compile' on 'WebAssembly': Incorrect response MIME type. Expected 'application/wasm'`
- DevTools console shows: `failed to asynchronously prepare wasm: CompileError: WebAssembly.instantiate(): expected magic word 00 61 73 6d, found 3c 21 44 4f` (HTML being served instead of WASM)
- DevTools console shows: `Uncaught Error: No camera defined` from `scene.render()`
- Project uses Vite 5.x dev server with `@babylonjs/havok` excluded from `optimizeDeps`

## Verified Workflow

### Step 1: Add debug logging to catch silent failures

Before anything else, add `console.log` at every stage of your async `_init()` method so you can see exactly where initialization hangs:

```typescript
private async _init(): Promise<void> {
  console.log('[Scene] _init: starting HavokPhysics load...');
  const havok = await HavokPhysics({ locateFile: (path) => {
    console.log('[Scene] HavokPhysics locateFile:', path);
    return `/${path}`;
  }});
  console.log('[Scene] HavokPhysics loaded');
  // ... rest of init with logs at each stage
}
```

### Step 2: Copy WASM to public/ for static serving

Vite's dev server serves files from `node_modules` via its module resolution pipeline — NOT as static assets. Any request for a file not in `public/` returns Vite's SPA HTML fallback (`<!DOCTYPE html>`), which is why `3c 21 44 4f` appears in the WASM magic bytes check.

```bash
cp node_modules/@babylonjs/havok/lib/esm/HavokPhysics.wasm public/HavokPhysics.wasm
```

The `locateFile` callback in `HavokPhysics()` maps the WASM filename to `/HavokPhysics.wasm`, which Vite serves correctly from `public/`:

```typescript
const havok = await HavokPhysics({
  locateFile: (path: string) => `/${path}`
});
```

### Step 3: Fix "No camera defined" during async init

Babylon.js `Scene.render()` throws if no active camera exists. When you start the render loop in the constructor before `async _init()` completes, the scene tries to render with no camera.

Add a temporary `FreeCamera` immediately in the constructor, dispose it just before your real `CameraManager` takes over:

```typescript
constructor(engine: Engine) {
  this._scene = new Scene(engine);
  // Temporary camera to satisfy scene.render() during async init
  this._tempCam = new FreeCamera('_tempCam', new Vector3(0, 10, 0), this._scene);
  this._tempCam.setTarget(Vector3.Zero());
  engine.runRenderLoop(() => this._scene.render());
  this._init().catch(err => this._showError(err));
}

private async _init(): Promise<void> {
  // ... physics, lighting, systems ...
  this._tempCam.dispose();           // ← dispose before real camera
  this._camera = new CameraManager(this._scene);
}
```

`_tempCam` must be a class field (not a local `const`) since it's accessed across constructor and `_init()`.

### Step 4: Verify in browser

1. Network tab: `/HavokPhysics.wasm` → HTTP 200 with `Content-Type: application/wasm`
2. Console: stage-by-stage logs confirm init completes
3. No "No camera defined" error

## Failed Attempts

| Attempt | Why Failed | Lesson |
|---------|-----------|--------|
| `assetsInclude: ['**/*.wasm']` in `vite.config.ts` | Vite still serves node_modules files through module pipeline, not as static assets. `assetsInclude` only affects bundling, not dev server static serving | Copy WASM to `public/` instead |
| `locateFile: (path) => path` (returning path unchanged) | HavokPhysics resolves relative to its own script URL in node_modules, which Vite serves as HTML. Same MIME error | Must return absolute path `/HavokPhysics.wasm` pointing to `public/` |
| `optimizeDeps.exclude: ['@babylonjs/havok']` alone | Prevents pre-bundling but doesn't fix WASM serving at all | Necessary but insufficient — still need `public/` copy |
| Using `const tempCam` in constructor, referencing in `_init()` | `_init()` is a separate method, can't access constructor locals | Store as class field `private _tempCam!: FreeCamera` |

## Results & Parameters

```typescript
// vite.config.ts — minimal working config
export default defineConfig({
  optimizeDeps: {
    exclude: ['@babylonjs/havok']   // prevent pre-bundling
  }
  // assetsInclude: ['**/*.wasm'] — NOT needed, does not help
})
```

```typescript
// HavokPhysics init — working pattern
const havok = await HavokPhysics({
  locateFile: (path: string) => `/${path}`
});
const plugin = new HavokPlugin(true, havok);
scene.enablePhysics(new Vector3(0, -9.81, 0), plugin);
```

```bash
# Required: copy WASM to public/ before dev server starts
cp node_modules/@babylonjs/havok/lib/esm/HavokPhysics.wasm public/HavokPhysics.wasm
```

## Verified On

| Project | Context | Details |
|---------|---------|---------|
| SoccerGame | Babylon.js 7.x + Havok + Vite 5 soccer game, blue screen on match scene load | [notes.md](references/notes.md) |

## References

- Related skills: none yet
- Babylon.js Havok docs: https://doc.babylonjs.com/features/featuresDeepDive/physics/usingPhysicsEngine
