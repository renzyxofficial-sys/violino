let keyDown = null;
// área das notas na timeline: x 280..1016 (à direita fica a barra vertical de mover)
const X0 = 280, XW = 736, X1 = X0 + XW;
function cpt(e) { const r = root.getBoundingClientRect(), s = r.width / 1280; return { x: (e.clientX - r.left) / s, y: (e.clientY - r.top) / s, s }; }
function timeAt(px) { const V = L.view; return V.v0 + (px - X0) / XW * (V.v1 - V.v0); }
function phraseAt(tt, pad = 0.3) { const ph = (S && S.phrases) || []; for (let k = 0; k < ph.length; k++) if (tt >= ph[k][0] - pad && tt <= ph[k][1] + pad) return k; return -1; }
// sem transição de posição enquanto a vista anda (zoom, scroll, arraste): as notas acompanham a grade
function markMove() { root.classList.add('vmove'); clearTimeout(L.vmT); L.vmT = setTimeout(() => root.classList.remove('vmove'), 240); }
// valores locais seguram a edição na tela até o estado do plugin trazer a mudança
function sig(s) {
  let h = 0;
  for (const c of (s && s.cap) || []) h += c[0] * 7 + c[1] * 3 + c[2] * 11 + (c[4] || 0) * 13;
  for (const p of (s && s.phrases) || []) h += (p[7] || 0) * 17 + (p[8] ?? 0.5) * 19;
  for (const d of (s && s.dyn) || []) h += d[1] * 0.37;
  return h;
}
function hold() { L.holdSig = sig(S); L.holdN = 12; }
function releaseHold() { L.holdSig = null; L.velOv = {}; L.fadeOv = {}; L.dragHold = null; L.moveHold = null; L.dynHold = null; }
if (backend) backend.addEventListener('state', (s) => { if (L.holdSig != null && (sig(s) !== L.holdSig || --L.holdN <= 0)) releaseHold(); });
function capVel(i) { const c = S && S.cap && S.cap[i]; return L.velOv && L.velOv[i] != null ? L.velOv[i] : c ? (c[4] ?? 90) : 90; }
function commitVel() {
  const o = L.velOv || {}, v = Object.keys(o).map((k) => [+k, Math.round(o[k])]);
  if (v.length) { send({ cmd: 'noteVel', vels: v }); hold(); }
}
function velWheel(i, d, pt) {
  const ids = L.sel && L.sel.has(i) ? [...L.sel] : [i];
  L.velOv = L.velOv || {};
  for (const j of ids) L.velOv[j] = Math.max(1, Math.min(127, capVel(j) + d));
  L.velTip = { x: pt.x + 14, y: pt.y - 22, text: 'Velocity ' + Math.round(L.velOv[ids[0]]) };
  dirty = true;
  clearTimeout(L.velWT);
  L.velWT = setTimeout(() => { commitVel(); L.velTip = null; dirty = true; }, 350);
}
function velFromY(y) { return Math.max(1, Math.min(127, Math.round((446 - y) / 30 * 127))); }
function velPaintAt(pt, fromX) {
  const a = Math.min(fromX, pt.x) - 3, b = Math.max(fromX, pt.x) + 3;
  for (const v of L.velStems || []) if (v.x >= a && v.x <= b) L.velOv[v.i] = velFromY(pt.y);
  L.velTip = { x: pt.x + 14, y: pt.y - 22, text: 'Velocity ' + velFromY(pt.y) };
}
function velLaneDown(e) {
  const pt = cpt(e);
  let hit = null, bd = 7;
  for (const v of L.velStems || []) { const d = Math.abs(v.x - pt.x); if (d < bd) bd = d, hit = v; }
  L.velOv = L.velOv || {};
  if (hit) {  // arrasta a haste (e as outras notas selecionadas junto, como no Logic)
    const ids = L.sel && L.sel.has(hit.i) ? [...L.sel] : [hit.i];
    L.velDrag = { y: e.clientY, ids, base: Object.fromEntries(ids.map((j) => [j, capVel(j)])), lane: true };
  } else { L.velPaint = { lastX: pt.x }; velPaintAt(pt, pt.x); }  // sem haste: pinta as velocities por onde passa
  dirty = true;
}
function focusTake(k) {
  const ph = (S && S.phrases) || [];
  if (!ph.length) return;
  k = Math.max(0, Math.min(ph.length - 1, k));
  L.focus = k;
  if ((L.zoom || 1) > 1.01 && L.view) { if (L.zoomAt == null) L.zoomAt = (L.view.v0 + L.view.v1) / 2; L.atT = (ph[k][0] + ph[k][1]) / 2; }
  dirty = true;
}
root.addEventListener('pointerdown', (e) => {
  const s = e.target.closest('[data-slider],[data-vslider]');
  if (s) { drag = { el: s, id: s.dataset.slider || s.dataset.vslider, vertical: !!s.dataset.vslider }; dragAt(e); e.preventDefault(); return; }
  const chip = e.target.closest('[data-artchip]');
  if (chip) { L.chipDrag = { i: +chip.dataset.artchip, x: 0, y: 0, moved: false }; e.preventDefault(); return; }
  const ft = e.target.closest('[data-fadet]');
  if (ft && L.view) { const i = +ft.dataset.fadet; L.fadeDrag = { i, y: e.clientY, ten0: ((S && S.phrases[i]) || [])[8] ?? 0.5, mode: 't' }; e.preventDefault(); return; }
  const fh = e.target.closest('[data-fade]');
  if (fh && L.view) { const i = +fh.dataset.fade; L.fadeDrag = { i, x: e.clientX, sec0: ((S && S.phrases[i]) || [])[7] || 0, mode: 'len' }; e.preventDefault(); return; }
  const cap = e.target.closest('[data-cap]');
  if (cap) {
    const i = +cap.dataset.cap, r = cap.getBoundingClientRect();
    L.sel = L.sel || new Set();
    if (e.shiftKey) { L.sel.has(i) ? L.sel.delete(i) : L.sel.add(i); }
    else if (!L.sel.has(i)) L.sel = new Set([i]);
    const c = S && S.cap && S.cap[i];
    if (c) { const k = phraseAt(c[0]); if (k >= 0) L.focus = k; }
    if (e.altKey) {  // Alt + arrastar para cima/baixo: velocity
      const ids = L.sel.has(i) ? [...L.sel] : [i];
      L.velOv = L.velOv || {};
      L.velDrag = { y: e.clientY, ids, base: Object.fromEntries(ids.map((j) => [j, capVel(j)])) };
    } else L.noteDrag = { x: e.clientX, y: e.clientY, resize: e.clientX > r.right - 6, ids: new Set(L.sel) };
    dirty = true; e.preventDefault(); return;
  }
  const vl = e.target.closest('[data-vellane]');
  if (vl && L.view) { velLaneDown(e); e.preventDefault(); return; }
  if (e.target.closest('[data-roll]') && e.button === 0 && L.view) {
    const k = phraseAt(timeAt(cpt(e).x));
    if (k >= 0 && k !== L.focus) { L.focus = k; dirty = true; }
    if (!e.shiftKey && L.sel && L.sel.size) { L.sel = new Set(); dirty = true; }
  }
  const hs = e.target.closest('[data-hscroll]');
  if (hs && L.full && L.view) {
    // na alça: arrasta mantendo o ponto onde pegou; fora dela: pula para lá
    const r = hs.getBoundingClientRect(), f = (e.clientX - r.left) / r.width, F = L.full;
    const a = (L.view.v0 - F.a) / (F.b - F.a), b = (L.view.v1 - F.a) / (F.b - F.a);
    L.scrollDrag = { el: hs, off: f >= a && f <= b ? f - (a + b) / 2 : 0 }; scrollTo(e); e.preventDefault(); return;
  }
  if (e.button === 1 && L.view && e.target.closest('[data-roll],[data-cap],[data-ruler],[data-vellane]')) {
    L.pan = { x: e.clientX, at: (L.view.v0 + L.view.v1) / 2, span: L.view.v1 - L.view.v0 };
    e.preventDefault(); return;
  }
  const dl = e.target.closest('[data-dynlane]');
  if (dl && L.view) { L.dynPts = []; L.dynEl = dl; dynAdd(e); e.preventDefault(); return; }
  const vs = e.target.closest('[data-velslider]');
  if (vs && L.sel && L.sel.size) { L.velEl = vs; velAt(e); e.preventDefault(); return; }
  const mg = e.target.closest('[data-movegrip]');
  if (mg) { L.moveDrag = { x: e.clientX, y: e.clientY, ids: new Set(L.moveIds || []), dt: 0, dp: 0 }; e.preventDefault(); return; }
  const dm = e.target.closest('[data-dragmidi]');
  if (dm) { send({ cmd: 'dragMidi', phrase: +dm.dataset.dragmidi, dyn: dm.dataset.dyn === '1' }); e.preventDefault(); return; }
  const da = e.target.closest('[data-dragall]');
  if (da) { send({ cmd: 'dragAll' }); e.preventDefault(); return; }
  const ru = e.target.closest('[data-ruler]');
  if (ru && L.view) { send({ cmd: 'seek', t: Math.max(0, timeAt(cpt(e).x)) }); e.preventDefault(); return; }
  const d = e.target.closest('[data-drag]');
  if (d) { send({ cmd: 'drag', phrase: +d.dataset.drag }); e.preventDefault(); return; }
  const k = e.target.closest('[data-note]');
  if (k) { keyDown = +k.dataset.note; send({ cmd: 'key', note: keyDown, on: true }); e.preventDefault(); }
});
function dynAdd(e) {
  // desenho contínuo: preenche o caminho entre dois eventos do mouse (o traço nunca fica com buracos)
  const r = L.dynEl.getBoundingClientRect(), fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
  const tt = timeAt(268 + fx * 790), cc = Math.max(20, Math.min(124, 20 + (62 - fy * 64) / 58 * 104));
  const last = L.dynPts[L.dynPts.length - 1];
  if (last) {
    const n = Math.min(200, Math.ceil(Math.abs(tt - last[0]) / 0.03));
    for (let k = 1; k < n; k++) L.dynPts.push([last[0] + (tt - last[0]) * k / n, last[1] + (cc - last[1]) * k / n]);
  }
  L.dynPts.push([tt, cc]); dirty = true;
}
function velAt(e) {
  const r = L.velEl.getBoundingClientRect(), v = Math.round(Math.max(1, Math.min(127, (e.clientX - r.left) / r.width * 127)));
  L.velPending = v;
}
function scrollTo(e) {
  const r = L.scrollDrag.el.getBoundingClientRect(), f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width - L.scrollDrag.off));
  L.zoomAt = L.atT = L.full.a + f * (L.full.b - L.full.a); dirty = true;
}
// barra de ferramentas da seleção (estilo Pitch & Time do Ableton)
const SCALES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
function toolVals(capIn) {
  const sel = L.sel ? [...L.sel] : [];
  const tool = (label, title, op, arg, extra) => ({ label, title, pick: () => { send({ cmd: 'noteTool', ids: sel, op, arg, ...(extra || {}) }); if (op === 'transpose' && capIn[sel[0]]) previewNote(capIn[sel[0]][2] + arg); } });
  const root = L.scaleRoot || 0, mode = L.scaleMode || 0;
  const vels = sel.map((i) => capVel(i)), vel = vels.length ? Math.round(vels.reduce((x, y) => x + y, 0) / vels.length) : 90;
  return {
    hasSel: sel.length > 0, noSel: sel.length === 0, selText: sel.length + (sel.length > 1 ? ' notes' : ' note'),
    velPct: vel / 127 * 100, velText: String(vel),
    tools: [tool('−12', 'Octave down', 'transpose', -12), tool('−1', 'Semitone down', 'transpose', -1), tool('+1', 'Semitone up', 'transpose', 1), tool('+12', 'Octave up', 'transpose', 12),
      tool('Q 1/16', 'Quantize to 1/16', 'quantize', 0.25), tool('Q 1/8', 'Quantize to 1/8', 'quantize', 0.5), tool('Humanize', 'Random timing ±15 ms and velocity', 'humanize', 15),
      tool('Legato', 'Each note lasts until the next', 'legato', 0), tool('Reverse', 'Reverse the selection in time', 'reverse', 0),
      tool('×2', 'Twice as long', 'stretch', 2), tool('/2', 'Half as long', 'stretch', 0.5), tool('Split', 'Split each note in two', 'split', 0),
      { label: 'Fit ' + SCALES[root] + (mode ? ' min' : ' maj'), title: 'Move notes to the nearest note of the scale (click again to apply; right-click the key to change it)', pick: () => send({ cmd: 'noteTool', ids: sel, op: 'scale', arg: root, mode }) },
      { label: '⟳ key', title: 'Change the scale key', pick: () => { L.scaleRoot = (root + (mode ? 1 : 0)) % 12; L.scaleMode = mode ? 0 : 1; dirty = true; } },
      { label: 'Delete', title: 'Delete the selected notes', pick: () => { send({ cmd: 'noteDel', ids: sel }); L.sel = new Set(); dirty = true; } }]
  };
}

function previewNote(p) {  // toca a nota para o usuário ouvir a altura
  send({ cmd: 'key', note: p, on: true });
  setTimeout(() => send({ cmd: 'key', note: p, on: false }), 350);
}
function chipMove(e) {
  const r = root.getBoundingClientRect(), s = r.width / 1280;
  L.chipDrag.x = (e.clientX - r.left) / s - 33; L.chipDrag.y = (e.clientY - r.top) / s - 11; L.chipDrag.moved = true; dirty = true;
}
addEventListener('pointermove', (e) => {
  if (drag) dragAt(e);
  if (L.chipDrag) chipMove(e);
  if (L.scrollDrag) scrollTo(e);
  if (L.dynPts && L.dynEl) dynAdd(e);
  if (L.velEl) velAt(e);
  if (L.velDrag) {
    const pt = cpt(e), vd = L.velDrag, d = (vd.y - e.clientY) / pt.s * (vd.lane ? 127 / 30 : 0.8);
    for (const j of vd.ids) L.velOv[j] = Math.max(1, Math.min(127, vd.base[j] + d));
    L.velTip = { x: pt.x + 14, y: pt.y - 22, text: 'Velocity ' + Math.round(L.velOv[vd.ids[0]]) }; dirty = true;
  }
  if (L.velPaint) { const pt = cpt(e); velPaintAt(pt, L.velPaint.lastX); L.velPaint.lastX = pt.x; dirty = true; }
  if (L.fadeDrag) {
    const fd = L.fadeDrag, pt = cpt(e), V = L.view;
    if (fd.mode === 'len') { fd.sec = Math.max(0, Math.min(4, fd.sec0 + (e.clientX - fd.x) / pt.s / XW * (V.v1 - V.v0))); L.fadeTip = { x: pt.x + 14, y: pt.y - 22, text: fd.sec > 0.005 ? 'Fade in ' + Math.round(fd.sec * 1000) + ' ms' : 'No fade' }; }
    else { fd.ten = Math.max(-1, Math.min(1, fd.ten0 + (e.clientY - fd.y) / pt.s / 70)); L.fadeTip = { x: pt.x + 14, y: pt.y - 22, text: 'Curve ' + Math.round(-fd.ten * 100) }; }
    dirty = true;
  }
  if (L.moveDrag) {
    const md = L.moveDrag, pt = cpt(e), V = L.view;
    md.dp = Math.round((md.y - e.clientY) / pt.s / 8); md.dt = (e.clientX - md.x) / pt.s / XW * (V.v1 - V.v0);
    L.velTip = { x: pt.x - 120, y: pt.y - 22, text: (md.dp > 0 ? '+' : '') + md.dp + ' st · ' + (md.dt >= 0 ? '+' : '') + Math.round(md.dt * 1000) + ' ms' };
    markMove(); dirty = true;
  }
  if (L.pan) { const s = cpt(e).s; L.zoomAt = L.atT = L.pan.at - (e.clientX - L.pan.x) / s / XW * L.pan.span; dirty = true; }
  if (L.noteDrag) {
    const nd = L.noteDrag, s = cpt(e).s, V = L.view;
    const dx = (e.clientX - nd.x) / s, dy = (e.clientY - nd.y) / s;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) nd.moved = true;
    nd.dt = dx / XW * (V.v1 - V.v0); nd.dp = Math.round(-dy / (230 / Math.max(1, V.pHi - V.pLo)));
    if (nd.moved) { markMove(); dirty = true; }
  }
});
addEventListener('pointerup', (e) => {
  drag = null;
  L.scrollDrag = null;
  L.pan = null;
  if (L.dynPts && L.dynEl) {
    if (L.dynPts.length > 1) { send({ cmd: 'dynDraw', pts: L.dynPts }); L.dynHold = L.dynPts; hold(); }
    L.dynPts = null; L.dynEl = null; dirty = true;
  }
  if (L.velEl) { if (L.velPending) send({ cmd: 'noteTool', ids: [...L.sel], op: 'velocity', arg: L.velPending }); L.velEl = null; L.velPending = null; }
  if (L.velDrag || L.velPaint) { commitVel(); L.velDrag = null; L.velPaint = null; L.velTip = null; dirty = true; }
  if (L.fadeDrag) {
    const fd = L.fadeDrag;
    L.fadeOv = L.fadeOv || {};
    if (fd.mode === 'len' && fd.sec !== undefined) { send({ cmd: 'fade', phrase: fd.i, sec: fd.sec }); L.fadeOv[fd.i] = { sec: fd.sec }; hold(); }
    if (fd.mode === 't' && fd.ten !== undefined) { send({ cmd: 'fade', phrase: fd.i, tension: fd.ten }); L.fadeOv[fd.i] = { ten: fd.ten }; hold(); }
    L.fadeDrag = null; L.fadeTip = null; dirty = true;
  }
  if (L.moveDrag) {
    const md = L.moveDrag;
    if ((md.dt || md.dp) && md.ids.size) {
      send({ cmd: 'noteEdit', ids: [...md.ids], dt: md.dt, de: 0, dp: md.dp });
      if (md.dp && S && S.cap) { const c = S.cap[[...md.ids][0]]; if (c) previewNote(c[2] + md.dp); }
      L.moveHold = { ids: md.ids, dt: md.dt, dp: md.dp }; hold();
    }
    L.moveDrag = null; L.velTip = null; dirty = true;
  }
  if (L.chipDrag) {
    // acha a nota sob o cursor pelas caixas desenhadas (o chip arrastado não atrapalha)
    const r = root.getBoundingClientRect(), s = r.width / 1280, px = (e.clientX - r.left) / s, py = (e.clientY - r.top) / s;
    const hit = (L.noteBoxes || []).find((b) => px >= b.x - 3 && px <= b.x + b.w + 3 && py >= b.y - 6 && py <= b.y + 16);
    const art = L.chipDrag.i;
    if (hit) send({ cmd: 'noteArt', ids: L.sel && L.sel.has(hit.i) ? [...L.sel] : [hit.i], art });
    else if (!L.chipDrag.moved && L.sel && L.sel.size) send({ cmd: 'noteArt', ids: [...L.sel], art });
    L.chipDrag = null; dirty = true;
  }
  if (L.noteDrag) {
    const nd = L.noteDrag;
    if (nd.moved && (nd.dt || nd.dp)) {
      send(nd.resize ? { cmd: 'noteEdit', ids: [...nd.ids], dt: 0, de: nd.dt || 0, dp: 0 } : { cmd: 'noteEdit', ids: [...nd.ids], dt: nd.dt || 0, de: 0, dp: nd.dp || 0 });
      if (nd.dp && S && S.cap) { const first = [...nd.ids][0], c = S.cap[first]; if (c) previewNote(c[2] + nd.dp); }
      L.dragHold = nd; hold();
    }
    L.noteDrag = null; dirty = true;
  }
  if (keyDown != null) { send({ cmd: 'key', note: keyDown, on: false }); keyDown = null; }
});
// zoom e rolagem suaves: o alvo muda na hora, a vista chega lá em poucos quadros
function animView() {
  let moving = false;
  if (L.zoomT != null) {
    const z = L.zoom || 1, nz = Math.exp(Math.log(z) + (Math.log(L.zoomT) - Math.log(z)) * 0.32);
    if (Math.abs(nz - L.zoomT) < 0.003) L.zoom = L.zoomT; else { L.zoom = nz; moving = true; }
  }
  if (L.atT != null && L.zoomAt != null) {
    const d = L.atT - L.zoomAt;
    if (Math.abs(d) < 1e-4) L.zoomAt = L.atT; else { L.zoomAt += d * 0.32; moving = true; }
  }
  if ((L.zoom || 1) <= 1.001 && (L.zoomT ?? 1) <= 1.001) { L.zoom = 1; L.zoomT = null; L.atT = null; L.zoomAt = null; }
  if (moving) dirty = true;
}

