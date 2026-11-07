"""v0.5: edição de MIDI na timeline (selecionar, mover, redimensionar, criar, apagar) e paleta de
articulações para arrastar nas notas. Só a frase editada muda de hash (re-render só dela)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


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
a = rep(a, """  const pitches = vis.map((n) => n[2]);""", """  const pitches = ((S && S.cap) || []).filter((c) => c[1] >= v0 && c[0] <= v1).map((c) => c[2]);""")
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
