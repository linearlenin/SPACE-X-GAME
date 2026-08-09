---
name: AudioWorklet migration (pygbag)
about: Request upstream migration from ScriptProcessorNode to AudioWorkletNode to avoid deprecation warnings and improve audio performance
---

**Summary**

pygbag (used in this project) currently causes browser console deprecation warnings due to use of the ScriptProcessorNode API, which has been deprecated in favor of AudioWorkletNode. This produces browser console noise and could break in future browser versions.

**Why this matters**

- ScriptProcessorNode is deprecated and will eventually be removed from browsers.
- AudioWorklet provides lower-latency, more robust audio processing on the main thread and is the modern recommended approach.
- Switching would remove noisy console warnings and future-proof the pygbag runtime.

**Suggested change**

- Replace ScriptProcessorNode usage with AudioWorkletNode in the audio initialization/path of the runtime (pythons.js / wasm audio glue).
- Provide a fallback to ScriptProcessorNode for browsers that do not support AudioWorkletNode (optional) or feature-detect and log a single informational message.

**Patch idea**

1. Add an audio worklet script (e.g., audio-processor.js) implementing the processing logic.
2. Register the worklet via audioContext.audioWorklet.addModule(url).
3. Create an AudioWorkletNode and connect it into the graph.
4. Remove the ScriptProcessorNode-based path or fall back when addModule fails.

**Additional notes**

If you'd like, I can prepare a PR with a concrete patch that implements the AudioWorkletNode path with graceful fallback to ScriptProcessorNode for compatibility. Please advise on preferred API shape and how you'd like to receive the PR.
