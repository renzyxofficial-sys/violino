// Aba Score: as notas capturadas em partitura (clave de sol), numa folha de papel antigo.
// Quantiza em semicolcheias pelo BPM do DAW; 4 compassos por sistema, 4 sistemas por página.
'use strict';

const SC = { W: 766, H: 580, SYS: 4, BARS: 4, LEFT: 60, RIGHT: 736, TOP: 118, GAP: 112, LINE: 8 };
// semitom -> (grau diatônico, sustenido)
const STEP = [[0, 0], [0, 1], [1, 0], [1, 1], [2, 0], [3, 0], [3, 1], [4, 0], [4, 1], [5, 0], [5, 1], [6, 0]];
const head = (x, y, filled, ink) => ({ d: `M${(x - 5).toFixed(1)},${y.toFixed(1)}a5,3.6 -22 1,0 10,0a5,3.6 -22 1,0 -10,0Z`, fill: filled ? ink : 'none', stroke: ink, w: filled ? 0 : 1.6 });

function scoreVals(t) {
  const ink = '#3b2a1a', faint = 'rgba(59,42,26,0.45)';
  const paths = [], texts = [];
  const cap = ((S && S.cap) || []).map((c, i) => [...c, i]).sort((a, b) => a[0] - b[0]);  // c[5] = índice real (para editar)
  const sel = L.sel || new Set(), drg = L.scDrag && L.scDrag.moved ? L.scDrag : null, blue = '#0A84FF';
  const boxes = [];
  const bpm = (S && S.bpm) || 120, beat = 60 / bpm, q16 = beat / 4, barLen = beat * 4;
  const t0 = cap.length ? Math.floor(cap[0][0] / barLen) * barLen : 0;
  const lastBar = cap.length ? Math.floor((cap[cap.length - 1][0] - t0) / barLen) : 0;
  const perPage = SC.SYS * SC.BARS, pages = Math.max(1, Math.ceil((lastBar + 1) / perPage));
  const page = Math.min(L.scorePage || 0, pages - 1);
  texts.push({ t: 'Violin', x: SC.W / 2, y: 52, s: 26, c: ink, f: 'Georgia, "Times New Roman", serif', w: 700, a: 'middle' });
  texts.push({ t: cap.length ? 'Captured performance' : 'Capture something to see it here', x: SC.W / 2, y: 76, s: 13, c: faint, f: 'Georgia, serif', w: 400, a: 'middle' });
  texts.push({ t: '♩ = ' + Math.round(bpm), x: SC.LEFT, y: 100, s: 13, c: ink, f: 'Georgia, serif', w: 700, a: 'start' });
  texts.push({ t: `${page + 1} / ${pages}`, x: SC.RIGHT, y: 100, s: 12, c: faint, f: 'Georgia, serif', w: 400, a: 'end' });
  const barW = (SC.RIGHT - SC.LEFT - 40) / SC.BARS;
  for (let sy = 0; sy < SC.SYS; sy++) {
    const top = SC.TOP + sy * SC.GAP, bottom = top + 4 * SC.LINE;
    for (let k = 0; k < 5; k++) paths.push({ d: `M${SC.LEFT},${top + k * SC.LINE}H${SC.RIGHT}`, fill: 'none', stroke: ink, w: 1 });
    texts.push({ t: '𝄞', x: SC.LEFT + 2, y: bottom + 9, s: 52, c: ink, f: '"Segoe UI Symbol", "Noto Music", serif', w: 400, a: 'start' });
    if (sy === 0 && page === 0) {
      texts.push({ t: '4', x: SC.LEFT + 32, y: top + 15, s: 17, c: ink, f: 'Georgia, serif', w: 800, a: 'middle' });
      texts.push({ t: '4', x: SC.LEFT + 32, y: top + 31, s: 17, c: ink, f: 'Georgia, serif', w: 800, a: 'middle' });
    }
    for (let b = 0; b <= SC.BARS; b++) {
      const x = SC.LEFT + 40 + b * barW;
      paths.push({ d: `M${x.toFixed(1)},${top}V${bottom}`, fill: 'none', stroke: ink, w: b === SC.BARS ? 1.6 : 1 });
    }
    texts.push({ t: String(page * perPage + sy * SC.BARS + 1), x: SC.LEFT + 40, y: top - 8, s: 10, c: faint, f: 'Georgia, serif', w: 400, a: 'start' });
  }
  L.scoreGeo = { t0, page, perPage, barLen, q16, barW };
  for (const n0 of cap) {
    // arrastando: as notas selecionadas aparecem já no lugar novo (altura pela pauta, tempo em semicolcheias)
    let n = n0;
    if (drg && sel.has(n0[5])) {
      const [st0, sh0] = STEP[((n0[2] % 12) + 12) % 12], s0 = Math.floor(n0[2] / 12) * 7 + st0;
      n = [n0[0] + drg.d16 * q16, n0[1] + drg.d16 * q16, stepToMidi(s0 + drg.dSteps) + sh0, n0[3], n0[4], n0[5]];
    }
    const col = sel.has(n0[5]) ? blue : ink;
    const rel = n[0] - t0, barIdx = Math.floor(rel / barLen) - page * perPage;
    if (barIdx < 0 || barIdx >= perPage) continue;
    const sy = Math.floor(barIdx / SC.BARS), bx = barIdx % SC.BARS;
    const pos16 = Math.round((rel - Math.floor(rel / barLen) * barLen) / q16);
    const d16 = Math.max(1, Math.min(16, Math.round((n[1] - n[0]) / q16)));
    const top = SC.TOP + sy * SC.GAP, bottom = top + 4 * SC.LINE;
    const x = SC.LEFT + 40 + bx * barW + 12 + Math.min(15, pos16) / 16 * (barW - 22);
    const [st, sharp] = STEP[((n[2] % 12) + 12) % 12];
    const stepNum = Math.floor(n[2] / 12) * 7 + st;      // MIDI 60 = C4 -> grau 35; E4 (linha de baixo) = 37
    const y = bottom - (stepNum - 37) * (SC.LINE / 2);
    // linhas suplementares
    boxes.push({ i: n0[5], x, y });
    for (let s = 35; s >= stepNum; s -= 2) paths.push({ d: `M${x - 9},${bottom - (s - 37) * 4}h18`, fill: 'none', stroke: ink, w: 1 });
    for (let s = 47; s <= stepNum; s += 2) paths.push({ d: `M${x - 9},${bottom - (s - 37) * 4}h18`, fill: 'none', stroke: ink, w: 1 });
    // figura: semibreve 16, mínima 8 (ponto 12), semínima 4 (ponto 6), colcheia 2 (ponto 3), semicolcheia 1
    const kinds = [[16, 16, 0], [12, 8, 1], [8, 8, 0], [6, 4, 1], [4, 4, 0], [3, 2, 1], [2, 2, 0], [1, 1, 0]];
    const [, base, dot] = kinds.reduce((b, k) => (Math.abs(k[0] - d16) < Math.abs(b[0] - d16) ? k : b));
    paths.push(head(x, y, base <= 4, col));
    if (dot) paths.push({ d: `M${x + 9},${y - 1}a1.6,1.6 0 1,0 0.1,0`, fill: col, stroke: col, w: 1 });
    if (sharp) texts.push({ t: '♯', x: x - 15, y: y + 5, s: 15, c: col, f: '"Segoe UI Symbol", serif', w: 400, a: 'middle' });
    if (base < 16) {
      const up = stepNum < 41, sx = up ? x + 4.6 : x - 4.6, sy2 = up ? y - 28 : y + 28;
      paths.push({ d: `M${sx.toFixed(1)},${y.toFixed(1)}V${sy2.toFixed(1)}`, fill: 'none', stroke: col, w: 1.3 });
      const flags = base === 2 ? 1 : base === 1 ? 2 : 0;
      for (let f = 0; f < flags; f++) {
        const fy = sy2 + (up ? f * 6 : -f * 6);
        paths.push({ d: up ? `M${sx},${fy}c6,4 9,8 5,15` : `M${sx},${fy}c6,-4 9,-8 5,-15`, fill: 'none', stroke: col, w: 1.4 });
      }
    }
  }
  L.scoreBoxes = boxes;
  // quadradinho azul do lápis: onde a nota vai entrar
  const tool = L.scoreTool || 'select', dur = L.scoreDur || 4, dotOn = !!L.scoreDot;
  const hv = L.scoreHover && tool === 'pencil' ? L.scoreHover : null;
  const tb = (label, title, on, pick) => ({ label, title, pick, bg: on ? '#3b2a1a' : 'rgba(255,255,255,0.35)', fg: on ? '#F3E6C8' : '#3b2a1a' });
  const scoreTools = [
    tb('↖', 'Select: click a note, drag it up/down (pitch) or sideways (time) · Delete removes', tool === 'select', () => { L.scoreTool = 'select'; dirty = true; }),
    tb('✎', 'Pencil: click on the staff to write a note', tool === 'pencil', () => { L.scoreTool = 'pencil'; dirty = true; }),
    tb('⌫', 'Eraser: click a note to remove it', tool === 'erase', () => { L.scoreTool = 'erase'; dirty = true; })];
  const setDur = (d) => () => { L.scoreDur = d; scoreApplyDur(); dirty = true; };
  const scoreDurs = [[16, '𝅝', 'Whole'], [8, '𝅗𝅥', 'Half'], [4, '♩', 'Quarter'], [2, '♪', 'Eighth'], [1, '𝅘𝅥𝅯', 'Sixteenth']]
    .map(([d, label, name]) => tb(label, name + ' (new notes; also sets the selected notes)', dur === d, setDur(d)));
  scoreDurs.push(tb('·', 'Dotted', dotOn, () => { L.scoreDot = !dotOn; scoreApplyDur(); dirty = true; }));
  const acc = (d) => () => { const ids = [...(L.sel || [])]; if (ids.length) { send({ cmd: 'noteTool', ids, op: 'transpose', arg: d }); const c = S.cap[ids[0]]; if (c) previewNote(c[2] + d); } };
  const scoreAcc = [tb('♯', 'Sharp: selected notes up a semitone', false, acc(1)), tb('♭', 'Flat: selected notes down a semitone', false, acc(-1))];
  const go = (d) => () => { L.scorePage = Math.max(0, Math.min(pages - 1, page + d)); dirty = true; };
  // lista de páginas: um botão por página (a atual em destaque), para ir direto a qualquer uma
  const scorePages = Array.from({ length: pages }, (_, k) => ({ label: String(k + 1), on: k === page,
    bg: k === page ? '#3b2a1a' : 'rgba(255,255,255,0.3)', fg: k === page ? '#F3E6C8' : '#3b2a1a',
    pick: () => { L.scorePage = k; dirty = true; } }));
  return { scorePaths: paths, scoreTexts: texts, scorePrev: go(-1), scoreNext: go(1), scorePages, scoreTools, scoreDurs, scoreAcc,
    scoreGhost: hv, scoreCursor: tool === 'pencil' ? 'crosshair' : tool === 'erase' ? 'not-allowed' : 'default' };
}

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
