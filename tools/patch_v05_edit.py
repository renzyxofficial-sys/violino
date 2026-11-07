"""v0.5: edição de MIDI na timeline (selecionar, mover, redimensionar, criar, apagar) e paleta de
articulações para arrastar nas notas. Só a frase editada muda de hash (re-render só dela)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """    else if (cmd == "stopRender")""", """    else if (cmd == "noteEdit" || cmd == "noteDel" || cmd == "noteAdd" || cmd == "noteArt")
    {
        // edição na timeline: índices das notas capturadas (ordem do último estado enviado)
        std::vector<int> ids;
        if (auto* a = c["ids"].getArray()) for (auto& v : *a) ids.push_back (int (v));
        auto valid = [&] (int i) { return i >= 0 && i < (int) notes.size(); };
        if (cmd == "noteEdit")
        {
            const double dt = double (c["dt"]), de = double (c["de"]);
            const int dp = int (c["dp"]);
            for (int i : ids)
                if (valid (i))
                {
                    auto& nt = notes[size_t (i)];
                    nt.start = std::max (0.0, nt.start + dt);
                    nt.end = std::max (nt.start + 0.03, nt.end + dt + de);
                    nt.pitch = juce::jlimit (kMinPitch - 24, 108, nt.pitch + dp);
                }
        }
        else if (cmd == "noteDel")
        {
            std::sort (ids.rbegin(), ids.rend());
            for (int i : ids)
                if (valid (i)) notes.erase (notes.begin() + i);
        }
        else if (cmd == "noteAdd")
            notes.push_back ({ double (c["s"]), double (c["e"]), int (c["p"]), 90, Forced (choice ("articulation")), pass, false });
        else
            for (int i : ids)
                if (valid (i)) notes[size_t (i)].forced = Forced (juce::jlimit (0, 9, int (c["art"])));
        openNote.clear();
        dirty = true;
    }
    else if (cmd == "stopRender")""")
s = rep(s, """    o->setProperty ("phrases", ph);""", """    o->setProperty ("phrases", ph);
    juce::Array<juce::var> cap;  // notas capturadas (editáveis), na ordem de notes
    for (auto& nt : notes)
        cap.add (juce::Array<juce::var> { nt.start, nt.end, nt.pitch, int (nt.forced) });
    o->setProperty ("cap", cap);""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """      <sc-for list="{{notes}}" as="n">
        <span title="{{n.title}}" style="position: absolute; left: {{n.x}}px; top: {{n.y}}px; width: {{n.w}}px; height: 8px; border-radius: 4px; background: {{n.color}};"></span>
      </sc-for>""", """      <div data-roll="1" style="position: absolute; left: 268px; top: 140px; width: 790px; height: 300px;"></div>
      <sc-for list="{{notes}}" as="n">
        <span data-cap="{{n.i}}" title="{{n.title}}" style="position: absolute; left: {{n.x}}px; top: {{n.y}}px; width: {{n.w}}px; height: 10px; border-radius: 5px; background: {{n.color}}; box-shadow: {{n.ring}}; cursor: {{n.cursor}};"><span style="position: absolute; left: 0; top: 0; bottom: 0; width: 4px; border-radius: 5px 0 0 5px; background: {{n.art}};"></span></span>
      </sc-for>
      <sc-if value="{{hasNotes}}">
        <span style="position: absolute; left: 280px; top: 630px; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Articulations</span>
        <sc-for list="{{palette}}" as="a">
          <span data-artchip="{{a.i}}" title="Drag onto notes (or click with notes selected)" style="position: absolute; left: {{a.x}}px; top: 648px; width: 66px; height: 22px; border-radius: 11px; background: {{a.bg}}; color: {{a.fg}}; font-size: 11px; font-weight: 600; line-height: 22px; text-align: center; cursor: grab; user-select: none;">{{a.label}}</span>
        </sc-for>
        <span style="position: absolute; left: 280px; top: 680px; font-size: 10px; color: {{t.tertiary}};">Click a note to select (Shift adds) · drag to move · drag its right edge to resize · double-click empty space to add · Delete removes</span>
      </sc-if>
      <sc-if value="{{dragChip}}">
        <span style="position: absolute; left: {{dragChip.x}}px; top: {{dragChip.y}}px; width: 66px; height: 22px; border-radius: 11px; background: {{dragChip.bg}}; color: {{dragChip.fg}}; font-size: 11px; font-weight: 600; line-height: 22px; text-align: center; pointer-events: none; opacity: 0.9; box-shadow: 0 6px 16px rgba(0,0,0,0.4);">{{dragChip.label}}</span>
      </sc-if>""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

a = open("ui/app.js", encoding="utf-8").read()
# notas da timeline = notas capturadas (editáveis), com a cor do estado da frase e a da articulação
a = rep(a, """  const noteColor = [t.noteFuture, t.noteDone, t.noteNew, t.noteOld];
  const notes = vis.map((n) => ({ x: X(n[0]), y: Y(n[2]), w: Math.max(X(n[1]) - X(n[0]) - 2, 5), color: noteColor[n[4]] || t.noteFuture,
    title: `${ART_NAMES[n[3]]}: ${n[5]}` }));""", """  const noteColor = [t.noteFuture, t.noteDone, t.noteNew, t.noteOld];
  const capIn = (S && S.cap) || [];
  const stateAt = (s0) => { for (const p of phrases) if (s0 >= p[0] - 0.05 && s0 <= p[1] + 0.05) return p[2]; return 0; };
  const artAt = (s0, p0) => { let best = null, bd = 1e9; for (const n of notesIn) { const d = Math.abs(n[0] - s0) + (n[2] === p0 ? 0 : 5); if (d < bd) bd = d, best = n; } return best; };
  const sel = L.sel || new Set();
  const notes = capIn.map((c, i) => ({ c, i })).filter(({ c }) => c[1] >= v0 && c[0] <= v1).map(({ c, i }) => {
    const an = artAt(c[0], c[2]), forced = c[3] > 0 ? ART_IDS[c[3]] : null, art = forced || (an ? an[3] : 'auto');
    return { i, x: X(c[0]), y: Y(c[2]) - 1, w: Math.max(X(c[1]) - X(c[0]) - 2, 6), color: noteColor[stateAt(c[0])] || t.noteFuture,
      art: AC[art] || AC.auto, ring: sel.has(i) ? '0 0 0 2px #FFFFFF' : 'none', cursor: 'grab',
      title: `${ART_NAMES[art] || 'Auto'}${forced ? ' (set by you)' : an ? ': ' + an[5] : ''}` };
  });
  L.view = { v0, v1, pLo, pHi };
  const palette = ART_IDS.map((id, i) => ({ i, x: 280 + i * 70, label: i === 0 ? 'Auto' : ART_NAMES[id], bg: AC[id], fg: TXT(id) }));
  const dragChip = L.chipDrag ? { ...L.chipDrag, ...palette[L.chipDrag.i] } : null;""")
a = rep(a, """    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes, fxModules,""",
        """    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes, fxModules,
    hasNotes: capIn.length > 0, palette, dragChip,""")
a = rep(a, """    const pitches = vis.map((n) => n[2]);""", """    const pitches = ((S && S.cap) || []).filter((c) => c[1] >= v0 && c[0] <= v1).map((c) => c[2]);""")
# interação: editar notas e arrastar articulações
a = rep(a, """  const d = e.target.closest('[data-drag]');""", """  const chip = e.target.closest('[data-artchip]');
  if (chip) { L.chipDrag = { i: +chip.dataset.artchip, x: 0, y: 0, moved: false }; chipMove(e); e.preventDefault(); return; }
  const cap = e.target.closest('[data-cap]');
  if (cap) {
    const i = +cap.dataset.cap, r = cap.getBoundingClientRect();
    L.sel = L.sel || new Set();
    if (e.shiftKey) { L.sel.has(i) ? L.sel.delete(i) : L.sel.add(i); }
    else if (!L.sel.has(i)) L.sel = new Set([i]);
    L.noteDrag = { x: e.clientX, y: e.clientY, resize: e.clientX > r.right - 6, scale: r.width / Math.max(1, +cap.style.width.replace('px', '')) };
    dirty = true; e.preventDefault(); return;
  }
  if (e.target.closest('[data-roll]') && !e.shiftKey) { if (L.sel && L.sel.size) { L.sel = new Set(); dirty = true; } }
  const d = e.target.closest('[data-drag]');""")
a = rep(a, """addEventListener('pointermove', (e) => { if (drag) dragAt(e); });""", """function chipMove(e) {
  const r = root.getBoundingClientRect(), s = r.width / 1280;
  L.chipDrag.x = (e.clientX - r.left) / s - 33; L.chipDrag.y = (e.clientY - r.top) / s - 11; L.chipDrag.moved = true; dirty = true;
}
addEventListener('pointermove', (e) => {
  if (drag) dragAt(e);
  if (L.chipDrag) chipMove(e);
  if (L.noteDrag) {
    const nd = L.noteDrag, s = root.getBoundingClientRect().width / 1280, V = L.view;
    const dx = (e.clientX - nd.x) / s, dy = (e.clientY - nd.y) / s;
    nd.dt = dx / 770 * (V.v1 - V.v0); nd.dp = Math.round(-dy / (270 / Math.max(1, V.pHi - V.pLo)));
  }
});""")
a = rep(a, """addEventListener('pointerup', () => {
  drag = null;""", """addEventListener('pointerup', (e) => {
  drag = null;
  if (L.chipDrag) {
    const el = document.elementFromPoint(e.clientX, e.clientY), cap = el && el.closest && el.closest('[data-cap]');
    const art = L.chipDrag.i;
    if (cap) { const i = +cap.dataset.cap; const ids = L.sel && L.sel.has(i) ? [...L.sel] : [i]; send({ cmd: 'noteArt', ids, art }); }
    else if (L.sel && L.sel.size) send({ cmd: 'noteArt', ids: [...L.sel], art });
    L.chipDrag = null; dirty = true;
  }
  if (L.noteDrag) {
    const nd = L.noteDrag;
    if (nd.dt || nd.dp) send(nd.resize ? { cmd: 'noteEdit', ids: [...L.sel], dt: 0, de: nd.dt || 0, dp: 0 } : { cmd: 'noteEdit', ids: [...L.sel], dt: nd.dt || 0, de: 0, dp: nd.dp || 0 });
    L.noteDrag = null;
  }""")
a = rep(a, """fit();
paint();""", """root.addEventListener('dblclick', (e) => {
  if (!e.target.closest('[data-roll]') || !L.view) return;
  const r = e.target.closest('[data-roll]').getBoundingClientRect(), V = L.view;
  const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
  const tt = V.v0 + ((fx * 790 + 268) - 280) / 770 * (V.v1 - V.v0);
  const p = Math.round(V.pLo + (428 - (140 + fy * 300)) / 270 * (V.pHi - V.pLo));
  send({ cmd: 'noteAdd', s: tt, e: tt + 0.5, p });
});
addEventListener('keydown', (e) => {
  if ((e.key === 'Delete' || e.key === 'Backspace') && L.sel && L.sel.size) { send({ cmd: 'noteDel', ids: [...L.sel] }); L.sel = new Set(); dirty = true; }
});

fit();
paint();""")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
