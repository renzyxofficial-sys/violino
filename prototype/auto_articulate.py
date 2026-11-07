"""Articulação e dinâmica automáticas: MIDI cru de violino -> MIDI pronto para o VIOLET.

    python auto_articulate.py entrada.mid saida.mid                  # tudo automático
    python auto_articulate.py entrada.mid saida.mid --report notas.csv
    python auto_articulate.py entrada.mid saida.mid --overrides notas.csv   # CSV editado

Técnicas, deduzidas de duração, conexão, intervalo e repetição de cada nota (e calibradas
pelo que o VIOLET viu no treino: notas <= 0,15 s nunca são sustain/legato no CSV-TD):
  trilo           alternância rápida de duas notas a 1 ou 2 semitons -> uma nota com trilo
  trêmolo         mesma nota repetida muito rápido -> uma nota com trêmolo
  legato          notas encostadas/sobrepostas (gap <= 10 ms); nota repetida = troca de arco
  portamento      nota ligada tocada com velocity baixa (< 45), como nos violinos da VSL
  sem técnica     notas rápidas (<= 0,25 s) ligadas ou em detaché: o modo "gravação real",
                  que acerta 95–100 % das notas em passagens rápidas
  spiccato        notas curtas e destacadas
  sustain         notas longas separadas
Dinâmica (CC1 e CC11), dois modos:
  auto   (modo "Auto") a velocity de cada arcada define o nível (velocity baixa = dinâmica
         baixa; notas ligadas herdam o nível da arcada, então a velocity baixa do portamento
         não derruba o som) + arco de frase, contorno melódico, messa di voce e diminuendo.
  cc1    (modo "Auto + Dynamics") a dinâmica é a do CC1/CC11 do usuário (mod wheel); a
         velocity só decide ataque e transição.
Padrão: cc1 se o MIDI tem CC1/CC11, senão auto.

O usuário manda: keyswitches (notas < 55) também são mantidos.
O --report lista cada nota com a técnica e o motivo; edite a coluna "tecnica" (nomes
abaixo, ou "auto") e passe o arquivo em --overrides.
"""
import argparse
import csv
from dataclasses import dataclass

import numpy as np
import pretty_midi

TECHNIQUES = {
    "sustain": 36, "tremolo": 37, "trill_major": 38, "trill_minor": 39, "staccato": 40,
    "spiccato": 41, "ricochet": 42, "pizzicato": 43, "harmonic": 44,
    "legato_bow": 48, "legato_slur": 49, "legato_portamento": 50,
    "none": None,  # sem keyswitch -> canal "sem técnica" do VIOLET
}
KS_TO_NAME = {v: k for k, v in TECHNIQUES.items() if v is not None}
LEGATO = {"legato_bow", "legato_slur", "legato_portamento"}
MIN_PITCH = 55          # G3; abaixo disso são keyswitches
MAX_PITCH = 105         # A7: o topo que o VIOLET conhece
MIN_NOTE = 0.06         # notas mais curtas que isto o VIOLET não articula
KS_LEAD = 0.01          # o VIOLET procura o keyswitch em [onset-20 ms, onset+10 ms]
CONNECT_GAP = 0.010     # notas a até 10 ms (ou sobrepostas) são ligadas
OVERLAP = 0.03          # sobreposição de legato, como no dataset do VIOLET
FAST = 0.25             # nota "rápida" (s)
SHORT = 0.15            # abaixo disto o VIOLET só conhece técnicas curtas
TRILL_NOTE = 0.13       # cada nota de um trilo/trêmolo escrito por extenso
PORTA_VEL = 45          # nota ligada com velocity abaixo disto = portamento
CC_FRAME = 0.02


@dataclass
class Note:
    start: float
    end: float
    pitch: int
    vel: int
    tech: str = ""
    reason: str = ""
    user: bool = False  # técnica escolhida pelo usuário (keyswitch no MIDI ou override)

    @property
    def dur(self):
        return self.end - self.start


def read_notes(pm):
    """Notas de violino (monofônicas: em acordes fica a voz de cima) + keyswitches."""
    raw = [n for ins in pm.instruments if not ins.is_drum for n in ins.notes]
    ks = sorted((n.start, n.pitch) for n in raw if n.pitch < MIN_PITCH and n.pitch in KS_TO_NAME)
    notes = sorted((n for n in raw if n.pitch >= MIN_PITCH), key=lambda n: (n.start, -n.pitch))
    mono = []
    for n in notes:
        if mono and n.start - mono[-1].start < 0.03:
            continue  # acorde: mantém a nota mais aguda
        mono.append(Note(n.start, n.end, n.pitch, n.velocity))
    for a, b in zip(mono, mono[1:]):
        b_start = b.start
        if a.end > b_start + OVERLAP * 3:  # sobreposição longa = nota sustentada sob a outra
            a.end = b_start + OVERLAP
    for t, p in ks:  # keyswitch do usuário vale para a nota que começa logo depois
        for n in mono:
            if -0.02 <= n.start - t <= 0.03:
                n.tech, n.reason, n.user = KS_TO_NAME[p], "keyswitch in MIDI", True
                break
    return mono


def collapse_ornaments(notes):
    """Trilos e trêmolos escritos por extenso viram uma nota só com a técnica."""
    out, i = [], 0
    while i < len(notes):
        j = i + 1
        a = notes[i]
        if not a.user and a.dur <= TRILL_NOTE:
            # trêmolo: mesma altura repetida
            while j < len(notes) and notes[j].pitch == a.pitch and notes[j].dur <= TRILL_NOTE \
                    and notes[j].start - notes[j - 1].end <= 0.03:
                j += 1
            if j - i >= 4:
                out.append(Note(a.start, notes[j - 1].end, a.pitch, max(n.vel for n in notes[i:j]),
                                "tremolo", f"{j - i} fast repetitions"))
                i = j
                continue
            # trilo: alterna duas alturas a 1 ou 2 semitons
            j = i + 1
            pair = None
            while j < len(notes) and notes[j].dur <= TRILL_NOTE and notes[j].start - notes[j - 1].end <= 0.03:
                step = abs(notes[j].pitch - notes[j - 1].pitch)
                if step not in (1, 2) or (pair and {notes[j].pitch, notes[j - 1].pitch} != pair):
                    break
                pair = {notes[j].pitch, notes[j - 1].pitch}
                j += 1
            if pair and j - i >= 4:
                # o trilo costuma terminar repetindo a nota real: absorve essas notas
                while j < len(notes) and notes[j].pitch in pair and notes[j].dur <= TRILL_NOTE \
                        and notes[j].start - notes[j - 1].end <= 0.03:
                    j += 1
                low = min(pair)
                tech = "trill_minor" if max(pair) - low == 1 else "trill_major"
                out.append(Note(a.start, notes[j - 1].end, low, max(n.vel for n in notes[i:j]),
                                tech, f"{j - i} notes alternating by {max(pair) - low} semitone(s)"))
                i = j
                continue
        out.append(a)
        i += 1
    return out


def classify(notes):
    """Escolhe a técnica de cada nota que o usuário não fixou."""
    for i, n in enumerate(notes):
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        prev = notes[i - 1] if i > 0 else None
        ioi = (nxt.start - n.start) if nxt else n.dur
        connected_from_prev = prev is not None and n.start - prev.end <= CONNECT_GAP
        if n.user or n.tech:
            continue
        if connected_from_prev:
            if prev.dur <= FAST or n.dur <= FAST:
                n.tech, n.reason = "none", "fast and connected"
            elif n.pitch != prev.pitch and n.vel < PORTA_VEL:
                n.tech, n.reason = "legato_portamento", f"connected with low velocity ({n.vel})"
            elif n.pitch == prev.pitch:
                n.tech, n.reason = "legato_bow", "repeated connected note (bow change)"
            elif prev.tech in ("none", "staccato", "spiccato", "pizzicato", "tremolo"):
                n.tech, n.reason = "sustain", "slur starts after a short note"
            else:
                n.tech, n.reason = "legato_slur", "connected to previous note"
            continue
        articulation = n.dur / max(ioi, 1e-3)
        if n.dur <= SHORT or (n.dur <= 0.4 and articulation < 0.6):
            n.tech = "spiccato"
            n.reason = f"short and detached ({n.dur * 1000:.0f} ms of {ioi * 1000:.0f} ms)"
        elif n.dur <= FAST or ioi <= FAST:
            n.tech, n.reason = "none", "fast detache"
        else:
            n.tech, n.reason = "sustain", "long and separate"
    return notes


def phrases(notes):
    """Índices [início, fim) de cada frase: corta em pausas >= 0,25 s ou a cada ~12 s."""
    out, start = [], 0
    for i in range(1, len(notes)):
        gap = notes[i].start - notes[i - 1].end
        if gap >= 0.25 or notes[i].start - notes[start].start > 12.0:
            out.append((start, i))
            start = i
    out.append((start, len(notes)))
    return out


def dynamics(notes, end):
    """Curva de CC1 (0–127) em quadros de 20 ms."""
    t = np.arange(0.0, end + 1.0, CC_FRAME)
    # nível por arcada: a velocity da nota que começa o arco (80 -> 84, 40 -> 52, 120 -> 116);
    # notas ligadas herdam, para a velocity baixa do portamento não derrubar a dinâmica
    per_note = np.empty(len(notes))
    for i, n in enumerate(notes):
        tied = i > 0 and n.start - notes[i - 1].end <= CONNECT_GAP
        per_note[i] = per_note[i - 1] if tied else 20 + 0.8 * n.vel
    cc = np.full(len(t), per_note[0])
    for a, b in phrases(notes):
        ph = notes[a:b]
        p_start, p_end = ph[0].start, ph[-1].end
        if p_end - p_start <= 0:
            continue
        # ápice: nota aguda e longa
        apex = max(range(len(ph)), key=lambda k: ph[k].pitch + 6 * min(ph[k].dur, 1.5))
        x_apex = np.clip((ph[apex].start + ph[apex].dur / 2 - p_start) / (p_end - p_start), 0.25, 0.85)
        mean_pitch = np.mean([n.pitch for n in ph])
        for k, n in enumerate(ph):
            m = (t >= n.start) & (t < (ph[k + 1].start if k + 1 < len(ph) else n.end + 0.3))
            x = (t[m] - p_start) / (p_end - p_start)
            arc = np.where(x <= x_apex, -0.5 + 1.5 * np.sin(np.pi / 2 * x / x_apex),
                           1.0 - 1.8 * (np.clip(x - x_apex, 0, None) / (1 - x_apex)) ** 1.3)
            contour = np.clip(0.8 * (n.pitch - mean_pitch), -10, 10)
            v = per_note[a + k] + 14 * arc + contour
            if n.dur >= 0.9:  # messa di voce
                y = np.clip((t[m] - n.start) / n.dur, 0, 1)
                v = v + 8 * np.sin(np.pi * y)
            cc[m] = v
        tail = (t >= p_end) & (t < p_end + 0.3)
        cc[tail] = cc[np.searchsorted(t, p_end) - 1] if np.searchsorted(t, p_end) > 0 else cc[tail]
    # suaviza (sigma 80 ms) e limita
    k = np.exp(-0.5 * (np.arange(-12, 13) * CC_FRAME / 0.08) ** 2)
    cc = np.convolve(np.pad(cc, 12, mode="edge"), k / k.sum(), mode="valid")
    return t, np.clip(np.round(cc), 20, 124).astype(int)


def apply_overrides(notes, path):
    rows = {int(r["idx"]): (r.get("technique") or r.get("tecnica") or "").strip()
            for r in csv.DictReader(open(path, encoding="utf-8"))}
    for i, n in enumerate(notes):
        tech = rows.get(i, "auto")
        if tech and tech != "auto":
            if tech not in TECHNIQUES:
                raise SystemExit(f"note {i}: unknown technique '{tech}' (use: {', '.join(TECHNIQUES)}, auto)")
            n.tech, n.reason, n.user = tech, "set by user", True


def write_midi(notes, src_pm, path, dynamics_mode=None):
    """dynamics_mode: "auto" (velocity + frase), "cc1" (do usuário) ou None (detecta)."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=src_pm.estimate_tempo() if len(notes) > 8 else 120)
    ins = pretty_midi.Instrument(program=40, name="Violin")
    for i, n in enumerate(notes):
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        end = n.end
        if nxt and nxt.tech in LEGATO | {"none"} and nxt.start - n.end <= CONNECT_GAP:
            end = max(end, nxt.start + OVERLAP)  # legato do VIOLET = notas sobrepostas
        ins.notes.append(pretty_midi.Note(n.vel, n.pitch, n.start, end))
        ks = TECHNIQUES[n.tech]
        if ks is not None:
            t = max(n.start - KS_LEAD, 0.0)
            ins.notes.append(pretty_midi.Note(100, ks, t, t + 0.05))
    end = max(n.end for n in notes)
    if any(TECHNIQUES[n.tech] is None for n in notes):
        # sem nenhum keyswitch o VIOLET trata tudo como sustain: um keyswitch solto no fim
        # marca o arquivo como anotado, e as notas sem keyswitch ficam "sem técnica"
        ins.notes.append(pretty_midi.Note(100, TECHNIQUES["sustain"], end + 0.5, end + 0.55))
    user_cc = [c for i in src_pm.instruments for c in i.control_changes if c.number in (1, 11)]
    mode = dynamics_mode or ("cc1" if user_cc else "auto")
    if mode == "cc1":
        cc1 = sorted((c for c in user_cc if c.number == 1), key=lambda c: c.time) or \
              sorted(user_cc, key=lambda c: c.time) or [pretty_midi.ControlChange(1, 80, 0.0)]
        for c in cc1:
            ins.control_changes.append(pretty_midi.ControlChange(1, c.value, c.time))
            ins.control_changes.append(pretty_midi.ControlChange(11, c.value, c.time))
        origin = "dynamics from CC1 (Auto + Dynamics)" if user_cc else \
            "Auto + Dynamics without CC1 in the MIDI: dynamics fixed at 80"
    else:
        t, cc = dynamics(notes, end)
        keep = np.r_[True, np.diff(cc) != 0]
        for tt, v in zip(t[keep], cc[keep]):
            ins.control_changes.append(pretty_midi.ControlChange(1, int(v), float(tt)))
            ins.control_changes.append(pretty_midi.ControlChange(11, int(v), float(tt)))
        origin = "automatic dynamics (velocity + phrasing)"
    ins.notes.sort(key=lambda n: (n.start, n.pitch))
    pm.instruments.append(ins)
    pm.write(path)
    return origin


def write_report(notes, path, cc_lookup):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["idx", "start_s", "note", "length_ms", "technique", "reason", "dynamics"])
        for i, n in enumerate(notes):
            w.writerow([i, f"{n.start:.3f}", pretty_midi.note_number_to_name(n.pitch),
                        int(n.dur * 1000), n.tech, n.reason, cc_lookup(n.start, n.end)])


def prepare_for_violet(notes):
    """O que o VIOLET não sabe tocar: fora de G3–A7 (sobe/desce oitava), notas < 60 ms e notas
    repetidas no mesmo instante."""
    out = []
    for n in notes:
        while n.pitch < MIN_PITCH:
            n.pitch += 12
        while n.pitch > MAX_PITCH:
            n.pitch -= 12
        n.end = max(n.end, n.start + MIN_NOTE)
        if out and abs(out[-1].start - n.start) < 0.01 and out[-1].pitch == n.pitch:
            continue
        out.append(n)
    return out


def articulate(entrada, saida, overrides=None, report=None, dynamics_mode=None):
    """MIDI cru -> MIDI do VIOLET. Devolve (notas, origem da dinâmica)."""
    src = pretty_midi.PrettyMIDI(entrada)
    notes = prepare_for_violet(collapse_ornaments(read_notes(src)))
    if overrides:
        apply_overrides(notes, overrides)
    classify(notes)
    origin = write_midi(notes, src, saida, dynamics_mode)
    out = pretty_midi.PrettyMIDI(saida)
    ccs = sorted((c.time, c.value) for c in out.instruments[0].control_changes if c.number == 1)

    times = np.array([tt for tt, _ in ccs]) if ccs else np.zeros(0)
    values = np.array([v for _, v in ccs], dtype=float) if ccs else np.zeros(0)

    def cc_at(a, b):
        """CC1 médio durante a nota (o valor no ataque ainda é a cauda da nota anterior)."""
        if not len(times):
            return ""
        grid = np.linspace(a, b, 20)
        idx = np.clip(np.searchsorted(times, grid, side="right") - 1, 0, len(values) - 1)
        return int(round(values[idx].mean()))

    if report:
        write_report(notes, report, cc_at)
    return notes, origin


def summary(notes):
    counts = {}
    for n in notes:
        counts[n.tech] = counts.get(n.tech, 0) + 1
    return ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1]))


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("entrada")
    p.add_argument("saida")
    p.add_argument("--report", help="CSV com a técnica de cada nota (editável)")
    p.add_argument("--overrides", help="CSV editado (coluna 'tecnica'; 'auto' = automático)")
    p.add_argument("--dinamica", choices=("auto", "cc1"),
                   help="auto = velocity + frase; cc1 = do usuário (padrão: cc1 se houver)")
    args = p.parse_args()
    notes, origin = articulate(args.entrada, args.saida, args.overrides, args.report,
                               args.dinamica)
    print(f"{args.entrada} -> {args.saida}: {len(notes)} notas | {origin} | {summary(notes)}")


if __name__ == "__main__":
    main()
