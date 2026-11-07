# Violino

**AI solo violin for your DAW** — a VST3 / Standalone instrument for Windows that turns MIDI into a realistic solo
violin performance with the [VIOLET](https://github.com/User-tian/VIOLET) neural model, running locally on your GPU
(ONNX Runtime + DirectML). No Python or WSL needed to use it.

> Status: **alpha** (v0.22). Personal project, in active development.

## How it works

1. **Capture** — play the keyboard or press play in your DAW; notes are captured into takes on the timeline.
2. **Articulate** — an auto-articulation engine picks a technique per note (sustain, legato, spiccato, staccato,
   portamento, trill…) and builds a dynamics curve. You can override everything by hand.
3. **Render** — each take is rendered by VIOLET (a Diffusion Transformer with rectified flow, generating 48 kHz
   DACVAE latents) in 10 s windows. While a take is not rendered yet, a sample-based preview plays instead.
4. **Mix** — EQ, compressor, saturation, chorus, stereo, delay and a ChromaVerb-style reverb, plus Mix presets.

## Features

- Piano roll with takes as regions (move, trim, extend, stretch), grid Auto/Snap/Free, box select, velocity lane,
  FL-style fade-ins, dynamics pencil, undo/redo, copy/paste, right-click menus, cycle, metronome (Standalone).
- Editable score view (pencil, eraser, note values, accidentals) with page list.
- Classical MIDI library (Mutopia Project, public domain / CC) and MIDI file import.
- Playstyle presets, extra vibrato, Even out leveler, drag audio/MIDI straight into the DAW.

## Repository layout

| Path | What |
|---|---|
| `plugin/source/` | JUCE processor, editor, engine service (render queue), preview sampler |
| `plugin/engine/` | Articulator, VIOLET renderer (ONNX), performer (takes/quality), mix FX |
| `plugin/ui/` | Web UI (WebView2): `build_ui.py` generates `index.html` from the design + `app.js`, `edit.js`, `fx.js`, `score.js` |
| `tools/` | ONNX export, dependency download, sample preparation, library download, analysis and patch scripts |
| `library/` | Classical MIDI library (Mutopia Project) + `index.json` |
| `RETOMAR.md` | Working notes / backlog (Portuguese) |

## Building (Windows)

1. Dependencies: `powershell tools/get_deps.ps1` (JUCE, ONNX Runtime DirectML, CMake, VSCO 2 CE samples).
2. Models: export VIOLET to ONNX with `tools/export_onnx.py` (needs the VIOLET checkpoints, see their repo),
   output in `onnx/`.
3. Preview samples: `python tools/prepare_samples.py`.
4. UI: `python plugin/ui/build_ui.py`.
5. Build: `cmake --build plugin/build --config Release --target Violino_Standalone Violino_VST3`
   (with `deps/cmake/bin` on `PATH`).
6. Install: copy the built `Violino.vst3` to `C:\Program Files\Common Files\VST3\`, with models and samples in
   `Violino.vst3\Contents\Resources\{models,samples,library}`.

## Credits and third-party licenses

See [THIRD_PARTY.md](THIRD_PARTY.md). The license of this project itself is not decided yet.
