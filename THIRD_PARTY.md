# Third-party components

| Component | Used for | License |
|---|---|---|
| [VIOLET](https://github.com/User-tian/VIOLET) (code and checkpoints) | Neural violin synthesis (DiT + fine-tuned DACVAE decoder), exported to ONNX | Code: MIT. Checkpoints: see the authors' Hugging Face page |
| [JUCE 8](https://juce.com) | Plugin framework (VST3 / Standalone, WebView2 UI) | AGPLv3 or commercial — **must be resolved before any public release** |
| [ONNX Runtime + DirectML](https://onnxruntime.ai) | GPU inference on Windows | MIT |
| [VSCO 2 Community Edition](https://github.com/sgossner/VSCO-2-CE) | Solo violin samples for the realtime preview | CC0 |
| [Mutopia Project](https://www.mutopiaproject.org) | Classical MIDI library (`library/`) | Public domain / Creative Commons per piece (see `library/index.json`) |

Research references (not bundled): MOSA / MOSA-VPT datasets (Academia Sinica), Dreamtonics Instrument X (feature
research only), TokenSynth (separate evaluation in `tokensynth_test/`).
