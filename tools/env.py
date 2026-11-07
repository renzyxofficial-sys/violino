"""Envelope (dB RMS a cada 0,25 s) dos renders mais recentes do cache: mostra onde o VIOLET deixou o som baixo."""
import glob
import os
import sys

import numpy as np

files = sorted(glob.glob('/mnt/c/Users/TheoH/AppData/Local/Violino/cache/*.f32'), key=os.path.getmtime, reverse=True)[:40]
files = sorted(files, key=os.path.getsize, reverse=True)[:int(sys.argv[1]) if len(sys.argv) > 1 else 2]
for f in files:
    x = np.fromfile(f, dtype=np.float32)
    hop = 12000
    db = [20 * np.log10(np.sqrt(np.mean(x[i:i + hop] ** 2)) + 1e-9) for i in range(0, len(x) - hop, hop)]
    print(os.path.basename(f), f"{len(x) / 48000:.1f}s", "peak", f"{20 * np.log10(np.abs(x).max() + 1e-9):.1f} dB")
    print(" ".join(f"{d:.0f}" for d in db))
