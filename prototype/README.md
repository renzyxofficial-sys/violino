# Prototype (Python, command line)

The first version of Violino, before the plugin: a command-line pipeline that runs inside WSL with the VIOLET
Python environment.

| File | What |
|---|---|
| `violino.py` | MIDI → WAV in one command: auto-articulation, VIOLET render, best-of-N seeds |
| `violino.bat` | Windows wrapper that calls `violino.py` in WSL |
| `auto_articulate.py` | Auto articulation + dynamics (the C++ `Articulator` in the plugin is a port of this) |
| `mixer.py` | Built-in mixes (FDN reverb, EQ, compression, width) — origin of the plugin's Mix presets |
| `note_accuracy.py` | Pitch accuracy of a render against its MIDI (pYIN) |

Kept for reference and offline experiments; the plugin does not depend on it.
