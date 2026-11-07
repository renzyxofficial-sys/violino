"""MIDI de violino -> áudio, num comando: técnicas e dinâmica automáticas, VIOLET, melhor semente.

Uso (no WSL, conda `violet`; do Windows use violino.bat):
    python violino.py frase.mid frase.wav
    python violino.py frase.mid frase.wav --overrides frase_tecnicas.csv   # suas técnicas
    python violino.py frase.mid frase.wav --candidatos 6

Etapas:
  1. auto_articulate: técnica por nota + CC1 (mantém keyswitches/CC1 que já estão no MIDI).
     Grava frase_tecnicas.csv ao lado da saída: edite a coluna "tecnica" e rode com --overrides.
  2. VIOLET renderiza N candidatos (sementes diferentes). N automático: 4 se a peça tem
     muitas notas rápidas (onde a semente pesa), senão 1.
  3. Escolhe o candidato com mais notas certas dentro de um atraso tocável (-20…+40 ms) e
     compensa esse atraso, para o áudio cair no tempo do MIDI.
  4. Grava frase.wav seco por padrão (o reverb fica a cargo do DAW). --mix lyrical | romantic |
     baroque | cinematic aplica a mixagem embutida (mixer.py) e grava também frase_seco.wav.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

import numpy as np
import pretty_midi
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import auto_articulate  # noqa: E402
import mixer  # noqa: E402
import note_accuracy  # noqa: E402

VIOLET = os.path.expanduser(os.environ.get("VIOLET_DIR", "~/VIOLET"))
CKPT = os.path.join(VIOLET, "checkpoints")
LAGS = np.arange(-0.02, 0.041, 0.01)  # atrasos aceitos ao escolher o candidato
FAST_SHARE = 0.2                       # fração de notas rápidas a partir da qual N = 4
# Níveis de qualidade. Medido (bench_violet.py): 15 passos ≈ 30 (0,6 dB) e 60 ≈ 30 (0,2 dB),
# mas trocar a semente muda até 6 dB (o som pode sair 7 dB mais escuro). Por isso o Extreme
# gasta o tempo extra em mais candidatos, e não em mais passos.
QUALITY = {  # candidates None = 1 take, ou 4 se houver muitas notas rápidas
    "low": dict(steps=8, candidates=None),
    "medium": dict(steps=15, candidates=None),
    "high": dict(steps=30, candidates=None),
    "extreme": dict(steps=30, candidates=8),
}
AIR_TARGET = -37.0  # energia relativa > 8 kHz de um violino gravado (dB); critério de desempate


def wsl_path(path):
    """C:\\pasta\\x.mid -> /mnt/c/pasta/x.mid (quando chamado do Windows pelo violino.bat)."""
    if path and len(path) > 2 and path[1] == ":" and path[2] in "\\/":
        return f"/mnt/{path[0].lower()}/" + path[3:].replace("\\", "/")
    return path


def render_violet(midi_dir, out_dir, steps):
    # os dois overrides: sampler_steps sozinho não muda a tabela de tempos (fica em 30)
    cmd = [sys.executable, "src/eval.py", "data=eval_midi", f"data.data_dir={midi_dir}",
           "+trainer.precision=32", "++long_audio.enabled=true",
           f"++long_audio.output_dir={out_dir}", "++long_audio.max_batch_windows=2",
           f"model.ema_ckpt_path={CKPT}/pretrained_checkpoint/ema_snapshots/ema_prof_99515",
           f"encoder.finetuned_ckpt={CKPT}/dacvae_ft/weights.pth", "logger=csv",
           f"sampler_steps={steps}", f"model.noise_scheduler.num_steps={steps}"]
    env = dict(os.environ, PROJECT_ROOT=VIOLET)
    r = subprocess.run(cmd, cwd=VIOLET, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-15:])
        raise SystemExit(f"o VIOLET falhou:\n{tail}")


def air_level(wav):
    """Energia acima de 8 kHz relativa ao total (dB): mede se o take saiu abafado."""
    y, sr = sf.read(wav)
    y = y.mean(1) if y.ndim > 1 else y
    spec = np.abs(np.fft.rfft(y)) ** 2
    freqs = np.fft.rfftfreq(len(y), 1 / sr)
    return 10 * np.log10(spec[(freqs > 8000) & (freqs < 16000)].sum() / (spec.sum() + 1e-12) + 1e-12)


def pick_best(out_dir, names, notes):
    """Ordena os candidatos: notas certas no tempo (em faixas de 2 %), depois brilho mais
    perto de um violino gravado, depois menor atraso."""
    results = []
    for name in names:
        wav = os.path.join(out_dir, f"{name}_long.wav")
        track = note_accuracy.pitch_track(wav)
        acc, lag = max((note_accuracy.score(track, notes, s)[0], -abs(s), s) for s in LAGS)[::2]
        air = air_level(wav)
        results.append(dict(key=(round(acc * 50) / 50, -abs(air - AIR_TARGET), -abs(lag)),
                            acc=acc, lag=lag, air=air, wav=wav))
    results.sort(key=lambda r: r["key"], reverse=True)
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("entrada")
    p.add_argument("saida")
    p.add_argument("--overrides", help="CSV de técnicas editado (coluna 'tecnica')")
    p.add_argument("--qualidade", default="high", choices=tuple(QUALITY),
                   help="low 8 passos · medium 15 · high 30 · extreme 30 + melhor de 8 takes")
    p.add_argument("--candidatos", default="auto", help="número de sementes (padrão: do nível)")
    p.add_argument("--dinamica", choices=("auto", "cc1"),
                   help="auto = velocity + frase (modo Auto); cc1 = mod wheel (Auto + Dynamics)")
    p.add_argument("--mix", default="dry",
                   choices=("dry", "lyrical", "romantic", "baroque", "cinematic"),
                   help="mixagem embutida (padrão: dry = seco, para o reverb do DAW)")
    p.add_argument("--manter", action="store_true", help="guarda todos os candidatos")
    args = p.parse_args()
    args.entrada, args.saida = wsl_path(args.entrada), wsl_path(args.saida)
    args.overrides = wsl_path(args.overrides)

    t0 = time.time()
    base = os.path.splitext(args.saida)[0]
    report = base + "_tecnicas.csv"
    work = tempfile.mkdtemp(prefix="violino_")
    midi_dir, out_dir = os.path.join(work, "in"), os.path.join(work, "out")
    os.makedirs(midi_dir)
    os.makedirs(out_dir)

    take = os.path.join(work, "take.mid")
    notes, origin = auto_articulate.articulate(args.entrada, take, args.overrides, report,
                                               args.dinamica)
    fast = np.mean([n.dur <= auto_articulate.FAST for n in notes])
    level = QUALITY[args.qualidade]
    if args.candidatos != "auto":
        n_cand = int(args.candidatos)
    else:
        n_cand = level["candidates"] or (4 if fast >= FAST_SHARE else 1)
    print(f"[1/3] {len(notes)} notas | {origin} | {auto_articulate.summary(notes)}")
    print(f"      técnicas em {report}")

    names = [f"take{k + 1}" for k in range(n_cand)]
    for name in names:
        shutil.copy(take, os.path.join(midi_dir, name + ".mid"))
    print(f"[2/3] VIOLET ({args.qualidade}: {level['steps']} passos): {n_cand} candidato(s) "
          f"({fast:.0%} de notas rápidas)...", flush=True)
    render_violet(midi_dir, out_dir, level["steps"])

    played = [n for n in pretty_midi.PrettyMIDI(take).instruments[0].notes
              if n.pitch >= auto_articulate.MIN_PITCH]
    ranked = pick_best(out_dir, names, played)
    best = ranked[0]
    acc, lag = best["acc"], best["lag"]
    for r in ranked:
        mark = "->" if r is best else "  "
        print(f"      {mark} {os.path.basename(r['wav'])[:-9]}: {r['acc']:.0%} das notas certas, "
              f"atraso {r['lag'] * 1000:+.0f} ms, ar {r['air']:.1f} dB")

    y, sr = sf.read(best["wav"])
    y = y.mean(1) if y.ndim > 1 else y
    if lag > 0:
        y = y[int(round(lag * sr)):]  # compensa o atraso: o áudio cai no tempo do MIDI
    out = mixer.apply_mix(y, sr, args.mix)
    sf.write(args.saida, out.astype(np.float32), sr)
    written = [args.saida]
    if args.mix != "dry":
        dry = base + "_seco.wav"
        sf.write(dry, mixer.apply_mix(y, sr, "dry").astype(np.float32), sr)
        written.append(dry + " (seco)")
    if args.manter:
        for r in ranked:
            shutil.copy(r["wav"], f"{base}_{os.path.basename(r['wav'])[:-9]}.wav")
    shutil.rmtree(work, ignore_errors=True)
    fx = f"mix {args.mix}" if args.mix != "dry" else "seco"
    print(f"[3/3] {' e '.join(written)} | {fx} | {acc:.0%} das notas certas | "
          f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
