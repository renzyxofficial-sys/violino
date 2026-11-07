# Tools

| Folder | Scripts |
|---|---|
| `build/` | `get_deps.ps1` (JUCE, ONNX Runtime, CMake, VSCO), `export_onnx.py` + `run_export.sh` (VIOLET → ONNX, in WSL), `validate_onnx.py`, `prepare_samples.py` / `scan_samples.py` (preview samples), `get_mutopia.py` (MIDI library), `restart_standalone.ps1`, `publish_github.ps1` |
| `analysis/` | `quality.py` (noise/brightness/level along a render), `env.py` (loudness envelope), `level_sim.py` (Even out simulation), `compare_*.py`, `bench_*.py`, `profile_onnx.py` |
| `ui-test/` | `mk_harness.py` builds `uit/test.html` (the UI with a mock plugin state) for testing in a browser |
