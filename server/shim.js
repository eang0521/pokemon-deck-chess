// The game scripts were written for the browser and attach themselves to `window`; on Workers that is the global.
globalThis.window = globalThis;
