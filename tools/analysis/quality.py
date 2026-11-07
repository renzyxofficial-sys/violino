"""Qualidade ao longo do render mais recente: nível, brilho (centróide), ruído (planicidade espectral) e
'aspereza' de alta frequência, a cada 0,5 s; marca as emendas das janelas do VIOLET (a cada 5 s)."""
import glob
import os

import numpy as np

f = max([g for g in glob.glob('/mnt/c/Users/TheoH/AppData/Local/Violino/cache/*.f32') if os.path.getsize(g) > 20 * 48000 * 4], key=os.path.getmtime)
x = np.fromfile(f, dtype=np.float32).astype(np.float64)
sr, hop = 48000, 24000
print(os.path.basename(f), f"{len(x) / sr:.1f}s")
print(" t(s)  dB   centroid  flat   hf%   | janela")
for i in range(0, len(x) - hop, hop):
    s = x[i:i + hop] * np.hanning(hop)
    S = np.abs(np.fft.rfft(s)) + 1e-12
    fr = np.fft.rfftfreq(hop, 1 / sr)
    band = (fr > 150) & (fr < 16000)
    db = 20 * np.log10(np.sqrt(np.mean(x[i:i + hop] ** 2)) + 1e-9)
    if db < -55:
        continue
    cen = np.sum(fr[band] * S[band]) / np.sum(S[band])
    flat = np.exp(np.mean(np.log(S[band]))) / np.mean(S[band])
    hf = np.sum(S[fr > 8000] ** 2) / np.sum(S[band] ** 2) * 100
    t = i / sr
    seam = " <- emenda" if abs((t + 0.25) % 5.0 - 0) < 0.3 or abs((t + 0.25) % 5.0 - 5) < 0.3 else ""
    print(f"{t:5.1f} {db:5.0f} {cen:8.0f} {flat:6.3f} {hf:5.1f}{seam}")
