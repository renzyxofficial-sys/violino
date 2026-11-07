"""Precisão de notas de um render contra o MIDI: pitch no miolo de cada nota (pYIN).

Uso: python note_accuracy.py pasta_wavs pasta_midis [--shift]
Para cada X_long.wav procura X.mid. Uma nota conta como certa se a mediana do f0 entre
25% e 75% da sua duração fica a menos de 50 cents da altura escrita. --shift testa
deslocamentos de ±200 ms (render atrasado/adiantado em relação ao MIDI).
"""
import glob
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import librosa
import numpy as np
import pretty_midi

HOP, SR = 80, 16000


def pitch_track(wav):
    y, _ = librosa.load(wav, sr=SR)
    f0, voiced, _ = librosa.pyin(y, fmin=180, fmax=1600, sr=SR, hop_length=HOP, frame_length=1024)
    return np.arange(len(f0)) * HOP / SR, f0, voiced


def score(track, notes, shift=0.0):
    t, f0, voiced = track
    ok, errs = 0, []
    for n in notes:
        d = n.end - n.start
        m = (t >= n.start + shift + 0.25 * d) & (t <= n.start + shift + 0.75 * d) & voiced
        if not m.any():
            errs.append(np.nan)
            continue
        c = 1200 * np.log2(np.median(f0[m]) / librosa.midi_to_hz(n.pitch))
        errs.append(c)
        ok += abs(c) < 50
    return ok / len(notes), np.nanmedian(np.abs(errs))


def main():
    wav_dir, mid_dir = sys.argv[1], sys.argv[2]
    for w in sorted(glob.glob(os.path.join(wav_dir, "*_long.wav"))):
        name = os.path.basename(w).replace("_long.wav", ".mid")
        notes = [n for n in pretty_midi.PrettyMIDI(os.path.join(mid_dir, name)).instruments[0].notes
                 if n.pitch >= 55]
        track = pitch_track(w)
        a, e = score(track, notes)
        line = f"{name:34s} notas certas {a:5.0%} | erro mediano {e:5.1f} cents"
        if "--shift" in sys.argv:
            best = max(((score(track, notes, s)[0], s) for s in np.arange(-0.2, 0.201, 0.01)))
            line += f" | melhor deslocamento {best[1] * 1000:+4.0f} ms -> {best[0]:5.0%}"
        print(line)


if __name__ == "__main__":
    main()
