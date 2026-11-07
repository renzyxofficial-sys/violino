"""Mixagens embutidas do violino: reverb FDN próprio (5 salas) + EQ, compressão, saturação, largura.

    python mixer.py seco.wav saida.wav --mix cinematic
    python mixer.py seco.wav saida.wav --room concert_hall --wet 0.25

Mixagens ("Mix Style" no plugin): dry (padrão) · lyrical · romantic · baroque · cinematic.
Salas do reverb: room · chamber · concert_hall · scoring_stage · cathedral.

Este arquivo é a referência do algoritmo; o plugin (C++/JUCE) faz o mesmo em tempo real.
Reverb: reflexões iniciais estéreo (linha de atraso com 12 derivações) + difusor de entrada
(4 all-pass) + FDN de 8 linhas com matriz de Householder e filtro de absorção por linha (decai
mais rápido nos agudos: RT60 grave e agudo separados). Processado em blocos menores que o
menor atraso da rede, o que deixa o laço de realimentação vetorizado.
"""
import argparse

import numpy as np
import scipy.signal as sps
import soundfile as sf

ROOMS = {
    #                RT60 grave/agudo (s), pré-delay, tamanho (escala dos atrasos), ER: duração, nível
    "room":          dict(rt_low=0.7, rt_high=0.45, predelay=0.006, size=0.45, er_len=0.025, er_gain=0.55),
    "chamber":       dict(rt_low=1.4, rt_high=0.9, predelay=0.012, size=0.7, er_len=0.04, er_gain=0.45),
    "concert_hall":  dict(rt_low=2.4, rt_high=1.5, predelay=0.022, size=1.0, er_len=0.06, er_gain=0.35),
    "scoring_stage": dict(rt_low=2.0, rt_high=1.6, predelay=0.018, size=1.15, er_len=0.07, er_gain=0.5),
    "cathedral":     dict(rt_low=5.0, rt_high=2.8, predelay=0.035, size=1.6, er_len=0.12, er_gain=0.25),
}

# Cada mixagem, calibrada pelos guias de mixagem de cordas (ModWheel, MusicProductionWiki,
# Stock Music Musician, Audiorecording.me, tailout) e pela prática de gravação barroca:
#   eq        no seco, antes da sala: (tipo, Hz, dB, Q). Mapa do violino: 200–350 corpo,
#             300–500 madeira/caixa, ~1 k nasal, 2,5–4 k aspereza, 8–12 k ar.
#   bus_eq    no bus, depois da sala: presença e ar (senão a cauda dilui o brilho).
#   send      filtro do envio do reverb (passa-altas, passa-baixas): todos os guias filtram
#             150–250 Hz e 5–10 kHz para a sala não embolar nem chiar.
#   predelay  30–40 ms = solista na frente do palco; 0–8 ms = mais longe (igreja).
#   comp      clássico quase nada; cinematográfico 2:1 com ataque 10–30 ms (nunca < 10 ms).
MIX_STYLES = {
    "dry": None,
    # íntimo, cantado, na frente e brilhante: câmara curta, pré-delay longo, menos embolado em
    # 300, presença forte em 1,2 k/3 k, ar aberto, sala pouco filtrada no agudo
    "lyrical": dict(room="chamber", wet=0.26, rt_scale=1.0, predelay=0.036, send=(220, 11000),
                    eq=[("hp", 100, 0, 0.7), ("peak", 300, -1.5, 1.0), ("peak", 1200, 2.0, 1.2)],
                    bus_eq=[("peak", 3200, 4.0, 1.0), ("hshelf", 6500, 5.5, 0.7)],
                    comp=dict(thresh=-22, ratio=2.0, attack=0.03, release=0.2), drive=0.0, width=1.1),
    # sala de concerto grande e quente, mas com brilho sedoso: corpo, presença em 2 k, aspereza
    # só um toque, ar em 11 k, fita, cauda longa e larga
    "romantic": dict(room="concert_hall", wet=0.36, rt_scale=1.1, predelay=0.022, send=(170, 10000),
                     eq=[("hp", 75, 0, 0.7), ("peak", 250, 1.5, 0.8), ("peak", 3400, -0.5, 1.2)],
                     bus_eq=[("peak", 2400, 3.5, 0.9), ("hshelf", 6500, 5.0, 0.7)],
                     comp=None, drive=0.25, width=1.35),
    # igreja, perspectiva distante: cauda longa, pré-delay curto, sem caixa, clareza da tripa
    # (brilho sutil em 4,5 k e 9 k), sem compressão, imagem estreita
    "baroque": dict(room="cathedral", wet=0.38, rt_scale=0.62, predelay=0.006, send=(160, 8000),
                    eq=[("hp", 150, 0, 0.7), ("peak", 320, -3.0, 0.9)],
                    bus_eq=[("peak", 4500, 3.0, 0.9), ("hshelf", 7500, 2.5, 0.7)],
                    comp=None, drive=0.0, width=0.6),
    # scoring stage grande (~3,2 s), solista na frente (35 ms), corpo, presença em 2,5 k com a
    # aspereza de 3,8 k recortada estreita, muito ar (shelf tipo Pultec), bus 2,5:1, fita,
    # estéreo bem aberto e cauda brilhante
    "cinematic": dict(room="scoring_stage", wet=0.42, rt_scale=1.6, predelay=0.035, send=(200, 11000),
                      eq=[("hp", 90, 0, 0.7), ("peak", 250, 1.0, 0.8), ("peak", 3800, -1.0, 2.5)],
                      bus_eq=[("peak", 2800, 3.5, 0.9), ("hshelf", 6000, 6.5, 0.7)],
                      comp=dict(thresh=-22, ratio=2.5, attack=0.02, release=0.12), drive=0.2, width=1.8),
}


# ---------------------------------------------------------------- EQ (biquads RBJ)
def _biquad(kind, f, gain_db, q, sr):
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * f / sr
    cw, sw = np.cos(w), np.sin(w)
    al = sw / (2 * q)
    if kind == "peak":
        b = [1 + al * a, -2 * cw, 1 - al * a]
        aa = [1 + al / a, -2 * cw, 1 - al / a]
    elif kind == "hp":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
        aa = [1 + al, -2 * cw, 1 - al]
    elif kind == "hshelf":
        s = 2 * np.sqrt(a) * al
        b = [a * ((a + 1) + (a - 1) * cw + s), -2 * a * ((a - 1) + (a + 1) * cw),
             a * ((a + 1) + (a - 1) * cw - s)]
        aa = [(a + 1) - (a - 1) * cw + s, 2 * ((a - 1) - (a + 1) * cw), (a + 1) - (a - 1) * cw - s]
    elif kind == "lshelf":
        s = 2 * np.sqrt(a) * al
        b = [a * ((a + 1) - (a - 1) * cw + s), 2 * a * ((a - 1) - (a + 1) * cw),
             a * ((a + 1) - (a - 1) * cw - s)]
        aa = [(a + 1) + (a - 1) * cw + s, -2 * ((a - 1) + (a + 1) * cw), (a + 1) + (a - 1) * cw - s]
    else:
        raise ValueError(kind)
    return np.array(b) / aa[0], np.array(aa) / aa[0]


def eq(x, bands, sr):
    for kind, f, g, q in bands:
        b, a = _biquad(kind, f, g, q, sr)
        x = sps.lfilter(b, a, x, axis=0)
    return x


# ---------------------------------------------------------------- dinâmica e cor
def compress(x, sr, thresh, ratio, attack, release):
    """Compressor RMS estéreo ligado (detector no maior canal), ganho suavizado ataque/release."""
    level = np.max(np.abs(x), axis=1) if x.ndim > 1 else np.abs(x)
    env = np.sqrt(sps.lfilter([1 - np.exp(-1 / (0.01 * sr))], [1, -np.exp(-1 / (0.01 * sr))], level ** 2))
    db = 20 * np.log10(env + 1e-9)
    over = np.maximum(db - thresh, 0)
    target = -over * (1 - 1 / ratio)
    gain = np.empty_like(target)
    ca, cr = np.exp(-1 / (attack * sr)), np.exp(-1 / (release * sr))
    g = 0.0
    for i in range(0, len(target), 64):  # blocos de 64 amostras: o ganho muda devagar
        t = target[i:i + 64].min()
        c = ca if t < g else cr
        g = c * g + (1 - c) * t
        gain[i:i + 64] = g
    makeup = -thresh * (1 - 1 / ratio) * 0.35
    out = x * (10 ** ((gain + makeup) / 20))[:, None] if x.ndim > 1 else x * 10 ** ((gain + makeup) / 20)
    return out


def saturate(x, drive):
    """Saturação suave (tipo válvula/fita): tanh com mistura paralela."""
    if drive <= 0:
        return x
    k = 1 + 4 * drive
    peak = np.abs(x).max() + 1e-9
    y = np.tanh(k * x / peak) / np.tanh(k) * peak
    return (1 - drive) * x + drive * y


# ---------------------------------------------------------------- reverb
def _early(x, sr, length, gain, rng):
    """Reflexões iniciais estéreo: 12 derivações decrescentes, alternando lados."""
    out = np.zeros((len(x) + int(length * sr) + 1, 2))
    times = np.sort(rng.uniform(0.004, length, 12))
    for k, t in enumerate(times):
        d = int(t * sr)
        amp = gain * (1 - t / (length * 1.4)) * rng.uniform(0.6, 1.0)
        side = k % 2
        out[d:d + len(x), side] += amp * x
        out[d:d + len(x), 1 - side] += 0.35 * amp * x  # um pouco no outro lado
    return out


def _allpass(x, d, g):
    """All-pass de Schroeder (difusor): y[n] = -g x[n] + x[n-d] + g y[n-d]."""
    b = np.zeros(d + 1); b[0] = -g; b[d] = 1
    a = np.zeros(d + 1); a[0] = 1; a[d] = -g
    return sps.lfilter(b, a, x)


def fdn_reverb(x, sr, room, rt_scale=1.0, seed=7, predelay=None):
    """Sinal mono -> cauda estéreo (só o molhado)."""
    p = ROOMS[room]
    rng = np.random.default_rng(seed)
    rt_low, rt_high = p["rt_low"] * rt_scale, p["rt_high"] * rt_scale
    pre = int((p["predelay"] if predelay is None else predelay) * sr)
    x = np.concatenate([np.zeros(pre), x])
    er = _early(x, sr, p["er_len"], p["er_gain"], rng)
    diff = x
    for d, g in ((142, 0.7), (107, 0.7), (379, 0.6), (277, 0.6)):
        diff = _allpass(diff, int(d * sr / 48000), g)

    base = np.array([1531, 1777, 2053, 2311, 2591, 2833, 3121, 3413], dtype=float)
    delays = np.maximum((base * p["size"] * sr / 48000).astype(int), 200)
    n_lines, block = len(delays), int(delays.min())
    # absorção por linha (passa-baixas de 1 polo): ganho g0 no grave e gh em 4 kHz, tirados
    # do RT60 de cada faixa. |H(w)|² = g0²(1-a)² / (1 - 2a·cos w + a²) = gh² resolvido para a.
    g0 = 10 ** (-3 * delays / (rt_low * sr))
    gh = 10 ** (-3 * delays / (rt_high * sr))
    r = (gh / g0) ** 2
    c = np.cos(2 * np.pi * 4000 / sr)
    a1 = ((1 - r * c) - np.sqrt(np.maximum((1 - r * c) ** 2 - (1 - r) ** 2, 0))) / np.maximum(1 - r, 1e-9)
    b0 = g0 * (1 - a1)
    house = np.eye(n_lines) - 2.0 / n_lines * np.ones((n_lines, n_lines))  # Householder
    tail = int(rt_low * sr * 1.2)
    total = len(diff) + tail
    src = np.concatenate([diff, np.zeros(tail + block)])
    bufs = [np.zeros(total + d + block) for d in delays]
    states = np.zeros(n_lines)
    out = np.zeros((total + block, 2))
    signs_l = rng.choice([-1, 1], n_lines)
    signs_r = rng.choice([-1, 1], n_lines)
    for s in range(0, total, block):
        e = s + block
        taps = np.stack([bufs[k][s:e] for k in range(n_lines)])  # saída de cada linha (atraso d)
        filt = np.empty_like(taps)
        for k in range(n_lines):
            y, zf = sps.lfilter([b0[k]], [1, -a1[k]], taps[k], zi=[states[k]])
            filt[k], states[k] = y, zf[0]
        mixed = house @ filt
        inj = src[s:e]
        for k in range(n_lines):
            bufs[k][s + delays[k]:e + delays[k]] = mixed[k] + inj * (0.5 if k % 2 else -0.5)
        out[s:e, 0] = signs_l @ filt
        out[s:e, 1] = signs_r @ filt
    out = out[:total] / np.sqrt(n_lines)
    er = er[:total] if len(er) >= total else np.pad(er, ((0, total - len(er)), (0, 0)))
    wet = er + out
    return wet


def width(stereo, amount):
    """Largura M/S: 0 = mono, 1 = original, > 1 = mais aberto."""
    m = (stereo[:, 0] + stereo[:, 1]) / 2
    s = (stereo[:, 0] - stereo[:, 1]) / 2 * amount
    return np.stack([m + s, m - s], axis=1)


# ---------------------------------------------------------------- cadeia
def reverb_mix(y, sr, room, wet, rt_scale=1.0, width_amount=1.0, predelay=None,
               send=(180, 9000)):
    """Seco mono + reverb da sala, estéreo, com o molhado no nível RMS de 'wet'.
    send = (passa-altas, passa-baixas) do envio: a sala não recebe grave nem chiado."""
    hp, lp = send
    feed = sps.sosfilt(sps.butter(2, hp, "highpass", fs=sr, output="sos"), y)
    feed = sps.sosfilt(sps.butter(2, lp, "lowpass", fs=sr, output="sos"), feed)
    tail = width(fdn_reverb(feed, sr, room, rt_scale, predelay=predelay), width_amount)
    dry = np.zeros((len(tail), 2))
    dry[:len(y)] = y[:, None]
    tail *= np.sqrt(np.mean(dry ** 2) / max(np.mean(tail ** 2), 1e-12))
    return (1 - wet) * dry + wet * tail


def apply_mix(y, sr, style="dry"):
    """Áudio mono seco -> estéreo mixado no estilo (dry, lyrical, romantic, baroque, cinematic)."""
    m = MIX_STYLES[style]
    if m is None:
        out = np.stack([y, y], axis=1)
    else:
        x = eq(y, m["eq"], sr)
        if m["comp"]:
            x = compress(x, sr, **m["comp"])
        x = saturate(x, m["drive"])
        out = reverb_mix(x, sr, m["room"], m["wet"], m["rt_scale"], m["width"],
                         m["predelay"], m["send"])
        # brilho e presença no bus (depois da sala), como o "ar" tipo Pultec no bus de cordas:
        # antes do reverb, a cauda (quase toda médios) diluiria o brilho
        out = eq(out, m.get("bus_eq", []), sr)
        # corta a cauda abaixo de -70 dB
        level = np.abs(out).max(axis=1)
        last = np.nonzero(level > level.max() * 10 ** (-70 / 20))[0][-1]
        out = out[:last + 1]
    return out / (np.abs(out).max() + 1e-9) * 0.9


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("entrada")
    p.add_argument("saida")
    p.add_argument("--mix", default="dry", choices=tuple(MIX_STYLES))
    p.add_argument("--room", choices=tuple(ROOMS), help="só reverb, sem o resto da mixagem")
    p.add_argument("--wet", type=float, default=0.25)
    args = p.parse_args()
    y, sr = sf.read(args.entrada)
    y = y.mean(1) if y.ndim > 1 else y
    if args.room:
        out = reverb_mix(y, sr, args.room, args.wet)
        out = out / (np.abs(out).max() + 1e-9) * 0.9
    else:
        out = apply_mix(y, sr, args.mix)
    sf.write(args.saida, out.astype(np.float32), sr)
    print(f"{args.entrada} -> {args.saida} ({args.room or args.mix})")


if __name__ == "__main__":
    main()
