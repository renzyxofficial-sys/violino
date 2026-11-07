
// ------------------------------------------------------------------ edição na pauta
function stepToMidi(step) { const o = Math.floor(step / 7), d = ((step % 7) + 7) % 7; return o * 12 + [0, 2, 4, 5, 7, 9, 11][d]; }
function scoreLocate(x, y) {  // ponto da folha -> sistema, compasso, semicolcheia, grau na pauta
  const G = L.scoreGeo;
  if (!G) return null;
  for (let sy = 0; sy < SC.SYS; sy++) {
    const top = SC.TOP + sy * SC.GAP, bottom = top + 4 * SC.LINE;
    if (y < top - 40 || y > bottom + 40) continue;
    const bx = Math.floor((x - (SC.LEFT + 40)) / G.barW);
    if (bx < 0 || bx >= SC.BARS) return null;
    const pos16 = Math.max(0, Math.min(15, Math.round((x - (SC.LEFT + 40 + bx * G.barW + 12)) / (G.barW - 22) * 16)));
    const step = Math.round(37 + (bottom - y) / (SC.LINE / 2));
    return { sy, bx, pos16, step, gx: SC.LEFT + 40 + bx * G.barW + 12 + Math.min(15, pos16) / 16 * (G.barW - 22), gy: bottom - (step - 37) * (SC.LINE / 2) };
  }
  return null;
}
function scoreDurSec() { const G = L.scoreGeo; return (L.scoreDur || 4) * (L.scoreDot ? 1.5 : 1) * (G ? G.q16 : 0.125); }
function scoreApplyDur() {  // figura escolhida com notas selecionadas: muda a duração delas
  const ids = [...(L.sel || [])], len = scoreDurSec();
  for (const i of ids) { const c = S && S.cap[i]; if (c) send({ cmd: 'noteEdit', ids: [i], dt: 0, de: len - (c[1] - c[0]), dp: 0 }); }
}
function scorePt(e) { const pt = cpt(e); return { x: pt.x - 280, y: pt.y - 124, s: pt.s }; }
function scoreHitNote(x, y) { let best = null, bd = 9; for (const b of L.scoreBoxes || []) { const d = Math.hypot(b.x - x, b.y - y); if (d < bd) bd = d, best = b; } return best; }
root.addEventListener('pointerdown', (e) => {
  const el = e.target.closest('[data-score]');
  if (!el || e.button !== 0) return;
  const { x, y } = scorePt(e), tool = L.scoreTool || 'select', hit = scoreHitNote(x, y);
  e.preventDefault(); e.stopPropagation();
  if (tool === 'erase') { if (hit) { send({ cmd: 'noteDel', ids: [hit.i] }); L.sel = new Set(); dirty = true; } return; }
  if (hit) {
    L.sel = L.sel || new Set();
    if (e.shiftKey) L.sel.has(hit.i) ? L.sel.delete(hit.i) : L.sel.add(hit.i); else if (!L.sel.has(hit.i)) L.sel = new Set([hit.i]);
    L.scDrag = { x: e.clientX, y: e.clientY, dSteps: 0, d16: 0, moved: false };
    const c = S && S.cap[hit.i]; if (c) previewNote(c[2]);
    dirty = true; return;
  }
  L.sel = new Set(); dirty = true;
  if (tool !== 'pencil') return;
  const loc = scoreLocate(x, y), G = L.scoreGeo;
  if (!loc || !G) return;
  const s = G.t0 + (G.page * G.perPage + loc.sy * SC.BARS + loc.bx) * G.barLen + loc.pos16 * G.q16, p = stepToMidi(loc.step);
  send({ cmd: 'noteAdd', s, e: s + scoreDurSec(), p });
  previewNote(p);
}, true);
addEventListener('pointermove', (e) => {
  if (L.scDrag) {
    const d = L.scDrag, G = L.scoreGeo, s = cpt(e).s, dx = (e.clientX - d.x) / s, dy = (e.clientY - d.y) / s;
    if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
    d.dSteps = Math.round(-dy / (SC.LINE / 2)); d.d16 = G ? Math.round(dx / ((G.barW - 22) / 16)) : 0;
    dirty = true; return;
  }
  if ((L.scoreTool || 'select') === 'pencil' && e.target.closest && e.target.closest('[data-score]')) {
    const { x, y } = scorePt(e), loc = scoreLocate(x, y);
    const hv = loc ? { x: loc.gx - 6, y: loc.gy - 5 } : null;
    if (JSON.stringify(hv) !== JSON.stringify(L.scoreHover)) { L.scoreHover = hv; dirty = true; }
  }
});
addEventListener('pointerup', () => {
  const d = L.scDrag;
  if (!d) return;
  L.scDrag = null; dirty = true;
  if (!d.moved || (!d.dSteps && !d.d16)) return;
  const G = L.scoreGeo;
  for (const i of L.sel || []) {
    const c = S && S.cap[i];
    if (!c) continue;
    const [st, sh] = STEP[((c[2] % 12) + 12) % 12], s0 = Math.floor(c[2] / 12) * 7 + st, np = stepToMidi(s0 + d.dSteps) + sh;
    send({ cmd: 'noteEdit', ids: [i], dt: d.d16 * (G ? G.q16 : 0.125), de: 0, dp: np - c[2] });
  }
  const c0 = S && S.cap[[...(L.sel || [])][0]];
  if (c0 && d.dSteps) { const [st, sh] = STEP[((c0[2] % 12) + 12) % 12]; previewNote(stepToMidi(Math.floor(c0[2] / 12) * 7 + st + d.dSteps) + sh); }
});
