"""Prepara os samples do preview (VSCO 2 CE Solo Violin, CC0): mono, cauda cortada, FLAC 16 bits.

Uso: deps\\ortenv\\Scripts\\python.exe tools\\build\\prepare_samples.py <VSCO Solo Violin> <saída>
A nota vem do nome do arquivo, com a convenção de oitava de cada pasta medida (YIN, mediana):
o VSCO mistura convenções (o Arco Vib chama de G3 o MIDI 55, o spic e o trem chamam de A2 o
MIDI 57). Medir arquivo a arquivo falha nos pizzicatos curtos.
Grava <saída>/<articulação>/*.flac e <saída>/samples.json.
"""
import glob
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

KEEP = {"Arco Vib": ("sustain", 8.0), "Trem": ("tremolo", 6.0), "spic": ("spiccato", 1.6),
        "Pizz": ("pizzicato", 2.5)}
FADE = 0.3


def yin_f0(y, sr, fmin=180.0, fmax=2000.0, frame=2048, hop=512):
    out = []
    lo, hi = int(sr / fmax), int(sr / fmin)
    for s in range(0, len(y) - frame - hi, hop):
        x = y[s:s + frame + hi]
        d = np.array([np.sum((x[:frame] - x[t:t + frame]) ** 2) for t in range(hi + 1)])
        cmnd = d[1:] * np.arange(1, hi + 1) / np.maximum(np.cumsum(d[1:]), 1e-12)
        k = lo - 1 + int(np.argmin(cmnd[lo - 1:hi]))  # cmnd[k] é o atraso k + 1
        if cmnd[k] < 0.2:
            out.append(sr / (k + 1))
    return np.median(out) if out else None


NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def name_midi(name):
    m = re.search(r"_([A-G])(#|b)?(-?\d)_", name)
    return 12 * (int(m.group(3)) + 1) + NOTE[m.group(1)] + {"#": 1, "b": -1}.get(m.group(2), 0)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    entries = []
    total = 0
    for folder, (art, keep) in KEEP.items():
        os.makedirs(os.path.join(dst, art), exist_ok=True)
        files = sorted(glob.glob(os.path.join(src, folder, "*.wav")))
        diffs = []
        for f in files:
            y, sr = sf.read(f, always_2d=True)
            f0 = yin_f0(y.mean(axis=1)[int(0.25 * sr):int(min(len(y) / sr, 1.2) * sr)], sr)
            if f0 is not None:
                diffs.append(round(69 + 12 * np.log2(f0 / 440.0)) - name_midi(os.path.basename(f)))
        offset = int(np.median(diffs))
        print(f"{folder}: nome + {offset} semitons")
        for f in files:
            y, sr = sf.read(f, always_2d=True)
            y = y.mean(axis=1)
            name = os.path.basename(f)
            root = name_midi(name) + offset
            layer = 1 if re.search(r"_(f|v2)[_.]", name) else 0
            rr = int(m.group(1)) if (m := re.search(r"rr(\d)", name, re.I)) else 1
            n = min(len(y), int(keep * sr))
            y = y[:n].copy()
            fade = int(FADE * sr)
            if n > fade:
                y[-fade:] *= np.linspace(1, 0, fade) ** 2
            out = f"{root}_{'f' if layer else 'p'}_rr{rr}.flac"
            sf.write(os.path.join(dst, art, out), y.astype(np.float32), sr, subtype="PCM_16")
            total += os.path.getsize(os.path.join(dst, art, out))
            entries.append(dict(art=art, file=f"{art}/{out}", root=root, layer=layer, rr=rr))
    json.dump(dict(sampleRate=44100, samples=entries), open(os.path.join(dst, "samples.json"), "w"), indent=1)
    for art in ("sustain", "tremolo", "spiccato", "pizzicato"):
        roots = sorted({e["root"] for e in entries if e["art"] == art})
        print(f"{art}: {len([e for e in entries if e['art'] == art])} arquivos, notas {roots}")
    print(f"total {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
