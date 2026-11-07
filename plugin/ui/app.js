// Interface do Violino: template do design (holes {{...}}, <sc-if>, <sc-for>) renderizado com o
// estado real do plugin. Atualiza o DOM por diferença (morph) para não reiniciar as animações.
'use strict';

// ------------------------------------------------------------------ mini runtime do template
const TPL = document.getElementById('tpl').content;
const HOLE = /\{\{\s*([^}]+?)\s*\}\}/g;

function lookup(scope, path) {
  let v = scope;
  for (const k of path.split('.')) { if (v == null) return undefined; v = v[k]; }
  return v;
}
function interp(str, scope) {
  return str.replace(HOLE, (_, p) => { const v = lookup(scope, p); return v == null ? '' : String(v); });
}
function holeValue(str, scope) {
  const m = /^\{\{\s*([^}]+?)\s*\}\}$/.exec(str.trim());
  return m ? lookup(scope, m[1]) : str;
}
function build(node, scope, parent) {
  if (node.nodeType === 3) { parent.appendChild(document.createTextNode(interp(node.nodeValue, scope))); return; }
  if (node.nodeType !== 1) return;
  const tag = node.localName;
  if (tag === 'sc-if') {
    if (holeValue(node.getAttribute('value'), scope)) for (const c of node.childNodes) build(c, scope, parent);
    return;
  }
  if (tag === 'sc-for') {
    const list = holeValue(node.getAttribute('list'), scope) || [];
    const as = node.getAttribute('as');
    for (const item of list) {
      const s = Object.create(scope); s[as] = item;
      for (const c of node.childNodes) build(c, s, parent);
    }
    return;
  }
  const el = document.createElementNS(node.namespaceURI, tag);
  for (const a of node.attributes) {
    if (a.name.startsWith('hint-')) continue;
    if (a.name.startsWith('on')) { (el.__h ||= {})[a.name.slice(2)] = holeValue(a.value, scope); continue; }
    el.setAttribute(a.name, interp(a.value, scope));
  }
  for (const c of node.childNodes) build(c, scope, el);
  parent.appendChild(el);
}
function listen(el) {
  for (const type of Object.keys(el.__h || {})) {
    (el.__on ||= {});
    if (!el.__on[type]) { el.__on[type] = true; el.addEventListener(type, (e) => { const f = el.__h && el.__h[type]; if (typeof f === 'function') f(e); }); }
  }
}
function adopt(el) { if (el.nodeType !== 1) return; listen(el); for (const c of el.children) adopt(c); }
function morph(a, b) {
  if (a.nodeType !== b.nodeType || a.nodeName !== b.nodeName) { adopt(b); a.replaceWith(b); return; }
  if (a.nodeType === 3) { if (a.nodeValue !== b.nodeValue) a.nodeValue = b.nodeValue; return; }
  for (const at of [...a.attributes]) if (!b.hasAttribute(at.name)) a.removeAttribute(at.name);
  for (const at of b.attributes) if (a.getAttribute(at.name) !== at.value) a.setAttribute(at.name, at.value);
  a.__h = b.__h; listen(a);
  const ac = a.childNodes, bc = [...b.childNodes];
  for (let i = 0; i < bc.length; i++) {
    if (i < ac.length) morph(ac[i], bc[i]); else { if (bc[i].nodeType === 1) adopt(bc[i]); a.appendChild(bc[i]); }
  }
  while (ac.length > bc.length) a.removeChild(a.lastChild);
}
const root = document.getElementById('root');
function paint() {
  const frag = document.createElement('div');
  for (const c of TPL.childNodes) build(c, vals(), frag);
  const next = frag.firstElementChild;
  if (!root.firstElementChild) { adopt(next); root.appendChild(next); } else morph(root.firstElementChild, next);
  // troca de aba: o morph reaproveita o contêiner, então a animação de entrada é reiniciada à mão
  const tabNow = L.tab ?? (S && S.prefs && S.prefs.tab) ?? 'perf';
  if (L.lastTab !== tabNow) {
    L.lastTab = tabNow;
    const el = root.querySelector('.tabin');
    if (el) { el.style.animation = 'none'; void el.offsetWidth; el.style.animation = ''; }
  }
}

// ------------------------------------------------------------------ ponte com o C++
const backend = window.__JUCE__ && window.__JUCE__.backend;
function send(cmd) { if (backend) backend.emitEvent('cmd', cmd); }
let S = null;          // último estado do plugin
const L = { tab: null, dark: null, zoom: 1, viewFit: true }; // estado local da UI
let dirty = true;
if (backend) backend.addEventListener('state', (s) => { S = s; dirty = true; });
function frame() {
  animView();
  if (dirty) { dirty = false; try { paint(); } catch (e) { report(e); } }
  requestAnimationFrame(frame);
}
let reported = 0;
function report(e) { if (reported++ < 5) send({ cmd: 'log', msg: String(e && e.stack || e) }); }
addEventListener('error', (e) => report(e.error || e.message));

function P(id) { return (S && S.params && S.params[id]) || { n: 0, v: 0, text: '' }; }
function setN(id, n) { if (S && S.params[id]) S.params[id].n = n; send({ cmd: 'set', id, n }); dirty = true; }
function setV(id, v) { if (S && S.params[id]) S.params[id].v = v; send({ cmd: 'set', id, v }); dirty = true; }
function pref(key, value) { L[key] = value; send({ cmd: 'pref', key, value }); dirty = true; }

// escala a tela 1280x940 para a janela
function fit() { const s = Math.min(innerWidth / 1280, innerHeight / 940); root.style.transform = `scale(${s})`; }
addEventListener('resize', fit);

// sliders (arraste horizontal e o fader vertical) e teclado
let drag = null;
function dragAt(e) {
  const r = drag.el.getBoundingClientRect();
  const n = drag.vertical ? 1 - (e.clientY - r.top) / r.height : (e.clientX - r.left) / r.width;
  setN(drag.id, Math.min(1, Math.max(0, n)));
}
let keyDown = null;
// área das notas na timeline: x 280..1016 (à direita fica a barra vertical de mover)
let X0 = 280, XW = 736, X1 = X0 + XW;
// geometria da timeline: normal (entre os painéis) ou foco (largura toda, painéis escondidos)
const G = { l: 268, w: 790 };
function setGeo(k) {  // k: 0 = normal, 1 = foco (valores no meio durante a animação)
  k = +k; G.l = 268 + (22 - 268) * k; G.w = 790 + (1236 - 790) * k;
  X0 = G.l + 12; XW = G.w - 54; X1 = X0 + XW;
  Object.assign(G, { l2: G.l + 2, l6: G.l + 6, l12: G.l + 12, l84: G.l + 84, l212: G.l + 212, rw: G.w - 38, ow: G.w - 42,
    mx: G.l + G.w - 37, tc: G.l + (G.w - 38) / 2, r: 1280 - G.l - G.w });
}
setGeo(false);
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
function setVel(j, v) { L.velOv = L.velOv || {}; L.velOv[j] = Math.max(1, Math.min(127, v)); (L.velTouched ||= new Set()).add(j); }
function commitVel() {  // só as notas mexidas neste gesto
  const o = L.velOv || {}, v = [...(L.velTouched || [])].map((k) => [k, Math.round(o[k])]);
  L.velTouched = new Set();
  if (v.length) { send({ cmd: 'noteVel', vels: v }); hold(); }
}
function velWheel(i, d, pt) {
  const ids = L.sel && L.sel.has(i) ? [...L.sel] : [i];
  L.velOv = L.velOv || {};
  for (const j of ids) setVel(j, capVel(j) + d);
  L.velTip = { x: pt.x + 14, y: pt.y - 22, text: 'Velocity ' + Math.round(L.velOv[ids[0]]) };
  dirty = true;
  clearTimeout(L.velWT);
  L.velWT = setTimeout(() => { commitVel(); L.velTip = null; dirty = true; }, 350);
}
function velFromY(y) { return Math.max(1, Math.min(127, Math.round((446 - y) / 30 * 127))); }
function velPaintAt(pt, fromX) {
  const a = Math.min(fromX, pt.x) - 3, b = Math.max(fromX, pt.x) + 3;
  for (const v of L.velStems || []) if (v.x >= a && v.x <= b) setVel(v.i, velFromY(pt.y));
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
  const rh = e.target.closest('[data-rhead],[data-redge]');
  if (rh && L.view) {
    const i = +(rh.dataset.rhead ?? rh.dataset.redge), ph = (S && S.phrases) || [];
    L.focus = i; L.takeSel = true; L.sel = new Set();
    const mode = rh.dataset.redge != null ? rh.dataset.side : 'move';
    const ids = mode === 'move' && ph[i] ? ((S && S.cap) || []).map((c, j) => [c, j]).filter(([c]) => c[0] >= ph[i][0] - 0.01 && c[0] <= ph[i][1] + 0.01).map(([, j]) => j) : [];
    L.regDrag = { i, mode, x: e.clientX, stretch: e.altKey, ids: new Set(ids) };
    dirty = true; e.preventDefault(); return;
  }
  const cap = e.target.closest('[data-cap]');
  if (cap) {
    const i = +cap.dataset.cap, r = cap.getBoundingClientRect();
    L.sel = L.sel || new Set();
    if (e.shiftKey) { L.sel.has(i) ? L.sel.delete(i) : L.sel.add(i); }
    else if (!L.sel.has(i)) L.sel = new Set([i]);
    const c = S && S.cap && S.cap[i];
    if (c) { const k = phraseAt(c[0]); if (k >= 0) L.focus = k; }
    if (e.ctrlKey) {  // Ctrl + arrastar para cima/baixo: velocity
      const ids = L.sel.has(i) ? [...L.sel] : [i];
      L.velOv = L.velOv || {};
      L.velDrag = { y: e.clientY, ids, base: Object.fromEntries(ids.map((j) => [j, capVel(j)])) };
    } else L.noteDrag = { x: e.clientX, y: e.clientY, resize: e.clientX > r.right - 6, ids: new Set(L.sel), a0: c ? c[0] : 0, a1: c ? c[1] : 0 };
    L.takeSel = false;
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
  const tt = timeAt(G.l + fx * G.w), cc = Math.max(20, Math.min(124, 20 + (62 - fy * 64) / 58 * 104));
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
    for (const j of vd.ids) setVel(j, vd.base[j] + d);
    L.velTip = { x: pt.x + 14, y: pt.y - 22, text: 'Velocity ' + Math.round(L.velOv[vd.ids[0]]) }; dirty = true;
  }
  if (L.velPaint) { const pt = cpt(e); velPaintAt(pt, L.velPaint.lastX); L.velPaint.lastX = pt.x; dirty = true; }
  if (L.fadeDrag) {
    const fd = L.fadeDrag, pt = cpt(e), V = L.view;
    if (fd.mode === 'len') { fd.sec = Math.max(0, Math.min(4, fd.sec0 + (e.clientX - fd.x) / pt.s / XW * (V.v1 - V.v0))); L.fadeTip = { x: pt.x + 14, y: pt.y - 22, text: fd.sec > 0.005 ? 'Fade in ' + Math.round(fd.sec * 1000) + ' ms' : 'No fade' }; }
    else { fd.ten = Math.max(-1, Math.min(1, fd.ten0 + (e.clientY - fd.y) / pt.s / 70)); L.fadeTip = { x: pt.x + 14, y: pt.y - 22, text: 'Curve ' + Math.round(-fd.ten * 100) }; }
    dirty = true;
  }
  if (L.moveDrag && !L.moveDrag.fromReg) {
    const md = L.moveDrag, pt = cpt(e), V = L.view, c0 = capArr()[[...md.ids][0]];
    md.dp = Math.round((md.y - e.clientY) / pt.s / 8); md.dt = e.altKey ? (e.clientX - md.x) / pt.s / XW * (V.v1 - V.v0) : snapDt(c0 ? c0[0] : 0, (e.clientX - md.x) / pt.s / XW * (V.v1 - V.v0));
    L.velTip = { x: pt.x - 120, y: pt.y - 22, text: (md.dp > 0 ? '+' : '') + md.dp + ' st · ' + (md.dt >= 0 ? '+' : '') + Math.round(md.dt * 1000) + ' ms' };
    markMove(); dirty = true;
  }
  if (L.regDrag) {
    const rd = L.regDrag, pt = cpt(e), V = L.view;
    const rp = (S && S.phrases[rd.i]) || [0, 0];
    const rawDt = (e.clientX - rd.x) / pt.s / XW * (V.v1 - V.v0);
    rd.dt = e.altKey ? rawDt : snapDt(rd.mode === 'r' ? rp[1] : rp[0], rawDt);
    rd.stretch = rd.mode !== 'move' && (rd.stretch || e.altKey);
    if (rd.mode === 'move') L.moveDrag = { ids: rd.ids, dt: rd.dt, dp: 0, fromReg: true };
    L.velTip = { x: pt.x + 14, y: pt.y - 22, text: rd.mode === 'move' ? (rd.dt >= 0 ? '+' : '') + Math.round(rd.dt * 1000) + ' ms' : (rd.stretch ? 'Stretch ' : rd.dt * (rd.mode === 'r' ? 1 : -1) > 0 ? 'Extend ' : 'Trim ') + Math.abs(Math.round(rd.dt * 1000)) + ' ms' };
    markMove(); dirty = true;
  }
  if (L.pan) { const s = cpt(e).s; L.zoomAt = L.atT = L.pan.at - (e.clientX - L.pan.x) / s / XW * L.pan.span; dirty = true; }
  if (L.noteDrag) {
    const nd = L.noteDrag, s = cpt(e).s, V = L.view;
    const dx = (e.clientX - nd.x) / s, dy = (e.clientY - nd.y) / s;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) nd.moved = true;
    nd.dt = e.altKey ? dx / XW * (V.v1 - V.v0) : snapDt(nd.resize ? nd.a1 : nd.a0, dx / XW * (V.v1 - V.v0));  // Alt: sem grade enquanto segura
    nd.dp = Math.round(-dy / (200 / Math.max(1, V.pHi - V.pLo)));
    if (nd.moved) { if (e.altKey && snapStep()) L.velTip = { x: cpt(e).x + 14, y: cpt(e).y - 22, text: 'Free move (no grid)' }; else if (L.velTip && !L.velDrag) L.velTip = null; markMove(); dirty = true; }
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
  if (L.regDrag) {
    const rd = L.regDrag, p = S && S.phrases[rd.i];
    if (p && rd.dt && Math.abs(rd.dt) > 0.005) {
      if (rd.mode === 'move') { send({ cmd: 'noteEdit', ids: [...rd.ids], dt: rd.dt, de: 0, dp: 0 }); L.moveHold = { ids: rd.ids, dt: rd.dt, dp: 0 }; }
      else send({ cmd: 'takeResize', phrase: rd.i, start: rd.mode === 'l' ? Math.min(p[1] - 0.05, p[0] + rd.dt) : p[0], end: rd.mode === 'r' ? Math.max(p[0] + 0.05, p[1] + rd.dt) : p[1], stretch: !!rd.stretch });
      hold();
    }
    L.regDrag = null; L.moveDrag = null; L.velTip = null; dirty = true;
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
    const hit = (L.noteBoxes || []).find((b) => px >= b.x - 3 && px <= b.x + b.w + 3 && py >= b.y - 6 && py <= b.y + (b.h || 12) + 4);
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
    L.noteDrag = null; L.velTip = null; dirty = true;
  }
  if (keyDown != null) { send({ cmd: 'key', note: keyDown, on: false }); keyDown = null; }
});
// zoom e rolagem suaves: o alvo muda na hora, a vista chega lá em poucos quadros
function animView() {
  // passo pelo tempo real (não por quadro): mesma velocidade a 30 ou 144 fps
  const now = performance.now(), k = 1 - Math.exp(-Math.min(100, now - (L.animT || now)) / 55);
  L.animT = now;
  let moving = false;
  if (L.zoomT != null) {
    const z = L.zoom || 1, nz = Math.exp(Math.log(z) + (Math.log(L.zoomT) - Math.log(z)) * k);
    if (Math.abs(nz - L.zoomT) < 0.003) L.zoom = L.zoomT; else { L.zoom = nz; moving = true; }
  }
  if (L.atT != null && L.zoomAt != null) {
    const d = L.atT - L.zoomAt;
    if (Math.abs(d) < 1e-4) L.zoomAt = L.atT; else { L.zoomAt += d * k; moving = true; }
  }
  if ((L.zoom || 1) <= 1.001 && (L.zoomT ?? 1) <= 1.001) { L.zoom = 1; L.zoomT = null; L.atT = null; L.zoomAt = null; }
  if (moving) dirty = true;
}

// ------------------------------------------------------------------ valores do template
const ROOMS = ['Room', 'Chamber', 'Concert Hall', 'Scoring Stage', 'Cathedral'];
const ART_IDS = ['auto', 'sustain', 'legato', 'spiccato', 'staccato', 'pizzicato', 'tremolo', 'trill', 'portamento', 'harmonic'];
const ART_NAMES = { auto: 'Natural', sustain: 'Sustain', legato: 'Legato', spiccato: 'Spiccato', staccato: 'Staccato', pizzicato: 'Pizz',
  tremolo: 'Tremolo', trill: 'Trill', portamento: 'Portamento', harmonic: 'Harmonic' };

function vals() {
  const prefs = (S && S.prefs) || {};
  const dark = L.dark ?? prefs.dark ?? matchMedia('(prefers-color-scheme: dark)').matches;
  const tab = L.tab ?? prefs.tab ?? 'perf';
  const wide = !!(L.focusMode ?? prefs.focusMode) && tab === 'perf';  // modo foco: só a Performance
  { const now = performance.now(), k = 1 - Math.exp(-Math.min(80, now - (L.geoTime || now)) / 70); L.geoTime = now;
    L.geoK = L.geoK == null ? (wide ? 1 : 0) : L.geoK + ((wide ? 1 : 0) - L.geoK) * k;
    if (Math.abs(L.geoK - (wide ? 1 : 0)) < 0.002) L.geoK = wide ? 1 : 0; else { dirty = true; markMove(); } }
  setGeo(L.geoK);
  const t = dark ? {
    content: 'radial-gradient(1100px 720px at 12% -8%, rgba(88,86,214,0.30), transparent 60%), radial-gradient(900px 640px at 105% 108%, rgba(10,132,255,0.22), transparent 58%), radial-gradient(700px 500px at 60% 40%, rgba(191,90,242,0.08), transparent 70%), #121215', card: '#2A2A2C', cardShadow: '0 0 0 0.5px rgba(255,255,255,0.06)', kbArea: '#18181A',
    text: '#F5F5F7', secondary: 'rgba(235,235,245,0.6)', tertiary: 'rgba(235,235,245,0.3)',
    sep: 'rgba(255,255,255,0.10)', grid: 'rgba(255,255,255,0.05)', fill: 'rgba(255,255,255,0.10)', fill2: 'rgba(255,255,255,0.16)',
    track2: 'rgba(255,255,255,0.14)', segOn: 'rgba(255,255,255,0.24)', segShadow: '0 1px 2px rgba(0,0,0,0.35)',
    accent: '#0A84FF', accentSoft: 'rgba(10,132,255,0.16)', ok: '#30D158', okFill: 'rgba(48,209,88,0.08)',
    warn: '#FF9F0A', warnFill: 'rgba(255,159,10,0.08)', rec: '#FF453A', recFill: 'rgba(255,69,58,0.07)', green: '#30D158', off: 'rgba(120,120,128,0.32)',
    noteDone: '#0A84FF', noteNew: '#64D2FF', noteFuture: 'rgba(10,132,255,0.35)', noteOld: 'rgba(255,159,10,0.6)', meter: 'linear-gradient(#FF453A, #FFD60A 22%, #30D158 50%)',
    keyBed: '#000000', keyWhite: '#E5E5EA', keyDim: '#48484A', keyBlack: '#1C1C1E', keyBlackDim: '#3A3A3C', keyPress: '#0A84FF', labelOn: '#8E8E93',
    glass: 'background: rgba(40,40,44,0.58); backdrop-filter: blur(24px) saturate(180%); -webkit-backdrop-filter: blur(24px) saturate(180%); box-shadow: inset 0 0.5px 0 rgba(255,255,255,0.22), inset 0 0 0 0.5px rgba(255,255,255,0.08), 0 8px 28px rgba(0,0,0,0.45);'
  } : {
    content: 'radial-gradient(1100px 720px at 10% -10%, rgba(120,140,255,0.22), transparent 60%), radial-gradient(900px 640px at 105% 110%, rgba(90,200,250,0.16), transparent 58%), radial-gradient(700px 500px at 60% 40%, rgba(191,90,242,0.06), transparent 70%), #F2F2F7', card: '#FFFFFF', cardShadow: '0 0 0 0.5px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.04)', kbArea: '#EEEEF1',
    text: '#1D1D1F', secondary: 'rgba(60,60,67,0.6)', tertiary: 'rgba(60,60,67,0.3)',
    sep: 'rgba(60,60,67,0.18)', grid: 'rgba(0,0,0,0.045)', fill: 'rgba(120,120,128,0.12)', fill2: 'rgba(120,120,128,0.2)',
    track2: 'rgba(120,120,128,0.2)', segOn: '#FFFFFF', segShadow: '0 1px 2px rgba(0,0,0,0.12), 0 0 0 0.5px rgba(0,0,0,0.04)',
    accent: '#007AFF', accentSoft: 'rgba(0,122,255,0.10)', ok: '#28A745', okFill: 'rgba(52,199,89,0.08)',
    warn: '#C26B00', warnFill: 'rgba(255,149,0,0.09)', rec: '#E5352B', recFill: 'rgba(255,59,48,0.06)', green: '#34C759', off: 'rgba(120,120,128,0.16)',
    noteDone: '#007AFF', noteNew: '#32ADE6', noteFuture: 'rgba(0,122,255,0.3)', noteOld: 'rgba(255,149,0,0.6)', meter: 'linear-gradient(#FF3B30, #FFCC00 22%, #34C759 50%)',
    keyBed: '#C7C7CC', keyWhite: '#FFFFFF', keyDim: '#E9E9EE', keyBlack: '#1D1D1F', keyBlackDim: '#8E8E93', keyPress: '#007AFF', labelOn: '#8E8E93',
    glass: 'background: rgba(255,255,255,0.62); backdrop-filter: blur(24px) saturate(180%); -webkit-backdrop-filter: blur(24px) saturate(180%); box-shadow: inset 0 0.5px 0 rgba(255,255,255,0.95), inset 0 0 0 0.5px rgba(255,255,255,0.6), 0 0 0 0.5px rgba(0,0,0,0.06), 0 6px 24px rgba(0,0,0,0.10);'
  };
  document.body.style.background = dark ? '#121215' : '#F2F2F7';
  document.body.classList.toggle('light', !dark);
  const row = (on) => ({ bg: on ? t.fill2 : 'transparent', weight: on ? 600 : 400 });
  const seg = (on) => ({ bg: on ? t.segOn : 'transparent', shadow: on ? t.segShadow : 'none', weight: on ? 600 : 500 });
  const idx = (id) => Math.round(P(id).v);

  const tabs = [['perf', 'Performance'], ['inst', 'Instrument'], ['fx', 'Effects'], ['score', 'Score']].map(([id, label]) => (
    { label, on: tab === id, pick: () => pref('tab', id), ...seg(tab === id) }));

  const play = idx('playMode');
  const playModes = [
    ['Legato', 'M1 10c3-6 5-6 8 0s5 6 8 0'],
    ['Shorts', 'M2 7h2M7 7h2M12 7h2M16 7h1']
  ].map(([label, icon], i) => ({ label, icon, on: play === i, pick: () => setV('playMode', i), ...row(play === i), iconColor: play === i ? t.accent : t.secondary }));

  const shortIdx = idx('shortsMode');
  const shortModes = ['Spiccato', 'Staccato', 'Pizzicato'].map((label, i) => ({ label, pick: () => setV('shortsMode', i), ...seg(shortIdx === i) }));
  const am = idx('articMode');
  const articModes = [
    ['Auto', 'Articulation and dynamics detected'],
    ['Auto + Dynamics', 'You ride dynamics on the mod wheel'],
    ['Manual', 'Keyswitches only']
  ].map(([label, hint], i) => ({ label, hint, on: am === i, pick: () => setV('articMode', i), ...row(am === i) }));

  const q = idx('quality');
  const qInfo = [['Low', 'Fast drafts · 8 steps'], ['Med', 'Quick · 15 steps'], ['High', 'Default · 30 steps (official)'], ['Extreme', 'Best of 8 takes · 30 steps']];
  const qualities = qInfo.map(([label], i) => ({ label, on: q === i, pick: () => setV('quality', i), ...seg(q === i) }));

  const AC = dark
    ? { auto: '#98989D', sustain: '#0A84FF', legato: '#64D2FF', spiccato: '#FF9F0A', staccato: '#FFD60A',
        pizzicato: '#30D158', tremolo: '#BF5AF2', trill: '#FF375F', portamento: '#FF453A', harmonic: '#5E5CE6' }
    : { auto: '#8E8E93', sustain: '#007AFF', legato: '#32ADE6', spiccato: '#FF9500', staccato: '#FFCC00',
        pizzicato: '#34C759', tremolo: '#AF52DE', trill: '#FF2D55', portamento: '#FF3B30', harmonic: '#5856D6' };
  const TXT = (id) => (id === 'harmonic' ? '#FFFFFF' : '#000000');
  const art = idx('articulation');
  const artics = [['Auto', 'C1'], ['Sustain', 'D1'], ['Legato', 'E1'], ['Spiccato', 'F1'], ['Staccato', 'G1'], ['Pizz', 'A1'],
    ['Tremolo', 'B1'], ['Trill', 'C2'], ['Porta', 'D2'], ['Harmonic', 'E2']].map(([label, key], i) => {
    const id = ART_IDS[i], on = art === i;
    return { label, key, on, pick: () => setV('articulation', i), bg: on ? AC[id] : 'transparent', fg: on ? TXT(id) : t.text, dot: on ? TXT(id) : AC[id], weight: on ? 600 : 500 };
  });

  // ---- timeline: frases, notas, dinâmica e articulação reais
  const phrases = (S && S.phrases) || [], notesIn = (S && S.notes) || [], dynIn = (S && S.dyn) || [];
  const playhead = S ? ((S.playing && !S.internalPlay) ? S.playhead : S.internalPos) || 0 : 0;
  let v0, v1;
  if (phrases.length) { v0 = Math.min(...phrases.map((p) => p[0])) - 0.5; v1 = Math.max(...phrases.map((p) => p[1])) + 1.0; }
  else { v0 = Math.max(0, playhead - 2); v1 = v0 + 20; }
  if (v1 - v0 < 6) v1 = v0 + 6;
  if (S && S.internalPlay && playhead > v1 - 1) v1 = playhead + 4;  // tocando além do último take: a timeline cresce junto
  const fullA = v0, fullB = v1;
  L.full = { a: fullA, b: fullB };
  if (L.zoom > 1.01) {
    const span = (v1 - v0) / L.zoom, spT = (fullB - fullA) / (L.zoomT || L.zoom);
    if (L.zoomAt != null) L.zoomAt = Math.min(Math.max(L.zoomAt, fullA + span / 2), fullB - span / 2);
    if (L.atT != null) L.atT = Math.min(Math.max(L.atT, fullA + spT / 2), fullB - spT / 2);
    const c = L.zoomAt ?? (S && (S.playing || S.internalPlay) ? playhead : v0 + span / 2);
    v0 = Math.min(Math.max(fullA, c - span / 2), fullB - span); v1 = v0 + span;
  }
  const vk = v0.toFixed(4) + ':' + v1.toFixed(4);
  if (L.vk !== vk) { if (L.vk) markMove(); L.vk = vk; }
  const X = (s) => X0 + (s - v0) / (v1 - v0) * XW;
  // régua em compassos (4/4 no BPM do DAW ou do Standalone), números espaçados conforme o zoom
  const beat = 60 / ((S && S.bpm) || 120), barSec = 4 * beat, pxBar = XW * barSec / (v1 - v0);
  const every = [1, 2, 4, 8, 16, 32, 64].find((k) => pxBar * k >= 42) || 128;
  const bars = [], rticks = [];
  for (let b = Math.max(0, Math.ceil(v0 / barSec / every) * every); b * barSec <= v1; b += every) {
    const x = X(b * barSec);
    if (x >= G.l && x <= X1 + 2) bars.push({ x, lx: x + 4, label: String(b + 1) });
  }
  const tickBeats = pxBar / 4 >= 9 ? 1 : pxBar >= 9 ? 4 : 0;
  if (tickBeats) for (let k = Math.max(0, Math.ceil(v0 / (beat * tickBeats))); k * beat * tickBeats <= v1 && rticks.length < 300; k++) {
    const x = X(k * beat * tickBeats);
    if (x >= G.l && x <= X1 + 2) { const h = k % (4 / tickBeats) === 0 ? 9 : 5; rticks.push({ x, h, top: 136 - h }); }
  }
  const vis = notesIn.filter((n) => n[1] >= v0 && n[0] <= v1);
  const pitches = ((S && S.cap) || []).filter((c) => c[1] >= v0 && c[0] <= v1).map((c) => c[2]);
  let pLo = pitches.length ? Math.min(...pitches) - 2 : 60, pHi = pitches.length ? Math.max(...pitches) + 2 : 84;
  const vz = Math.max(1, L.vzoom || 1);
  if (vz > 1.01) {  // zoom vertical: só uma janela das alturas, centrada onde o usuário deixou
    const span = Math.max(4, (pHi - pLo) / vz), c = Math.min(Math.max(L.vcenter ?? (pLo + pHi) / 2, pLo + span / 2), pHi - span / 2);
    L.vcenter = c; pLo = c - span / 2; pHi = c + span / 2;
  }
  const noteH = Math.round(Math.max(12, Math.min(28, 200 / Math.max(1, pHi - pLo) * 0.85)));
  const Y = (p) => 388 - (p - pLo) / Math.max(1, pHi - pLo) * 200;
  const capIn = (S && S.cap) || [];
  const stateAt = (s0) => { for (const p of phrases) if (s0 >= p[0] - 0.05 && s0 <= p[1] + 0.05) return p[2]; return 0; };
  const artAt = (s0, p0) => { let best = null, bd = 1e9; for (const n of notesIn) { const d = Math.abs(n[0] - s0) + (n[2] === p0 ? 0 : 5); if (d < bd) bd = d, best = n; } return best; };
  const sel = L.sel || new Set();
  // grade: compassos e tempos pelo BPM (mais fina com zoom) e faixas das teclas pretas
  const grid = [], sub = gridMode() === 'snap' ? gridDiv() : autoDiv(v1 - v0);
  for (let k = Math.max(0, Math.ceil(v0 / (beat * sub))); k * beat * sub <= v1 && grid.length < 400; k++) {
    const tt = k * beat * sub, x = X(tt), onBeat = (q) => Math.abs(tt / (beat * q) - Math.round(tt / (beat * q))) < 1e-6;
    const c = onBeat(4) ? (dark ? 'rgba(255,255,255,0.14)' : 'rgba(0,0,0,0.13)') : onBeat(1) ? (dark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)') : (dark ? 'rgba(255,255,255,0.035)' : 'rgba(0,0,0,0.035)');
    if (x >= G.l && x <= X1 + 2) grid.push({ x, c });
  }
  const rows = [], rowH = 200 / Math.max(1, pHi - pLo);
  for (let p = Math.ceil(pLo); p <= pHi; p++)
    if ([1, 3, 6, 8, 10].includes(((p % 12) + 12) % 12)) rows.push({ y: Y(p) - rowH / 2 + 4, h: rowH, bg: dark ? 'rgba(255,255,255,0.025)' : 'rgba(0,0,0,0.028)' });
  const hscroll = L.zoom > 1.01 ? { x: (v0 - fullA) / (fullB - fullA) * 748, w: Math.max(24, (v1 - v0) / (fullB - fullA) * 748) } : null;
  // nota sendo arrastada (ou recém-solta) aparece já no lugar novo
  const nd = L.noteDrag && L.noteDrag.moved ? L.noteDrag : L.dragHold, md = L.moveDrag || L.moveHold;
  const NN = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const notes = capIn.map((c, i) => ({ c, i })).filter(({ c }) => c[1] >= v0 - 2 && c[0] <= v1 + 2).map(({ c, i }) => {
    let s0 = c[0], s1 = c[1], pp = c[2];
    if (nd && nd.ids && nd.ids.has(i)) { if (nd.resize) s1 = Math.max(s0 + 0.03, s1 + (nd.dt || 0)); else { s0 += nd.dt || 0; s1 += nd.dt || 0; pp += nd.dp || 0; } }
    if (md && md.ids.has(i)) { s0 += md.dt || 0; s1 += md.dt || 0; pp += md.dp || 0; }
    const an = artAt(c[0], c[2]), forced = c[3] > 0 && am !== 0 ? ART_IDS[c[3]] : null, art = forced || (an ? an[3] : 'auto');  // modo Auto: tudo automático
    const st = stateAt(c[0]), w = Math.max(X(s1) - X(s0) - 2, 6), vel = capVel(i);
    const live = S && (S.internalPlay || S.playing) && playhead >= c[0] && playhead < c[1];
    return { i, x: X(s0), y: Y(pp) + 4 - noteH / 2, h: noteH, r: noteH / 2, fs: noteH > 16 ? 10 : 8, w, vel, art: AC[art] || AC.auto, op: st === 1 ? 1 : st === 2 ? 0.85 : 0.62, fg: TXT(art),
      name: w > 24 ? NN[((pp % 12) + 12) % 12] + (Math.floor(pp / 12) - 1) : '', cls: live ? 'playing' : '',
      ring: sel.has(i) ? `0 0 0 2px ${dark ? '#FFFFFF' : '#1D1D1F'}` : live ? `0 0 0 1px #fff, 0 0 14px ${AC[art] || AC.auto}` : `0 1px 2px rgba(0,0,0,${dark ? 0.35 : 0.15})`, cursor: 'grab',
      title: `${NN[((pp % 12) + 12) % 12]}${Math.floor(pp / 12) - 1} · velocity ${Math.round(vel)} · ${ART_NAMES[art] || 'Auto'}${forced ? ' (set by you)' : an ? ': ' + an[5] : ''}` };
  }).filter((n) => n.x + n.w >= G.l - 6 && n.x <= X1 + 4 && n.y > 172 && n.y < 400);
  L.view = { v0, v1, pLo, pHi };
  // faixa de velocity (como no Logic): uma haste por nota, na cor da articulação
  const velStems = notes.map((n) => { const h = Math.max(2, n.vel / 127 * 30); return { i: n.i, x: n.x + 1, top: 446 - h, h, hy: 443 - h, color: n.art, op: sel.has(n.i) ? 1 : 0.72 }; });
  L.velStems = velStems.map((v) => ({ i: v.i, x: v.x }));
  const palette = ART_IDS.map((id, i) => ({ i, x: G.l + 12 + i * 70, label: i === 0 ? 'Auto' : ART_NAMES[id], bg: AC[id], fg: TXT(id) }));
  const dragChip = L.chipDrag && L.chipDrag.moved ? { ...palette[L.chipDrag.i], x: L.chipDrag.x, y: L.chipDrag.y } : null;
  L.noteBoxes = notes.map((n) => ({ i: n.i, x: n.x, y: n.y, w: n.w, h: n.h }));
  const STATE = [['Captured', t.secondary, t.fill], ['Rendered', t.ok, t.okFill], ['Rendering', t.warn, t.warnFill], ['Outdated', t.warn, t.warnFill]];
  const focus = L.focus != null && L.focus < phrases.length ? L.focus : (() => { const k = phraseAt(playhead, 0.05); return k >= 0 ? k : phrases.length - 1; })();
  const fadeOv = L.fadeOv || {}, fades = [];
  const rd = L.regDrag;
  const regions = phrases.map((p, i) => ({ p, i })).filter(({ p }) => X(p[1]) + 12 >= G.l && X(p[0]) - 12 <= X1 + 4).map(({ p, i }) => {
    let s0 = p[0], s1 = p[1];
    if (rd && rd.i === i && rd.dt != null) {
      if (rd.mode === 'l') s0 = Math.min(s1 - 0.05, Math.max(0, s0 + rd.dt));
      else if (rd.mode === 'r') s1 = Math.max(s0 + 0.05, s1 + rd.dt);
      else { s0 += rd.dt; s1 += rd.dt; }
    }
    const x = Math.max(G.l, X(s0) - 12), w = Math.max(16, Math.min(X1 + 4, X(s1) + 12) - x);
    let [label, color, fill] = STATE[p[2]];
    if (p[4]) { label = 'Capturing'; color = t.rec; fill = t.recFill; }
    if (p[2] === 2) label = p[3] > 0 ? `Rendering · ${Math.round(p[3] * 100)}%` : 'Queued';
    if (p[2] === 1) label = 'Rendered ✓';
    const head = p[4] ? t.rec : [dark ? '#6E6E73' : '#8E8E93', dark ? '#2FA84F' : '#34C759', t.warn, t.warn][p[2]];
    // forma de onda do render (picos a cada 50 ms desde a origem da frase)
    let wave = '';
    const peaks = p[6];
    if (p[2] === 1 && Array.isArray(peaks) && peaks.length) {
      const top = [], bot = [];
      for (let k = 0; k < peaks.length; k++) {
        const px = X(p[5] + k * 0.05) - x;
        if (px < 0 || px > w) continue;
        const amp = peaks[k] / 100 * 85;
        top.push(px.toFixed(1) + ',' + (100 - amp).toFixed(1));
        bot.push(px.toFixed(1) + ',' + (100 + amp).toFixed(1));
      }
      if (top.length > 1) wave = 'M' + top.join('L') + 'L' + bot.reverse().join('L') + 'Z';
    }
    // fade in estilo FL: curva sobre o trecho, alça no topo (duração) e alça no meio da curva (formato)
    const fd = L.fadeDrag && L.fadeDrag.i === i ? L.fadeDrag : null, ov = fadeOv[i] || {};
    const sec = fd && fd.sec != null ? fd.sec : ov.sec ?? (p[7] || 0), ten = fd && fd.ten != null ? fd.ten : ov.ten ?? (p[8] ?? 0.5);
    const xs = X(p[0] - 0.06), xe = X(p[0] - 0.06 + sec), ex = Math.pow(2, 2 * ten), yt = 24, yb = 226;
    let fLine = '', fShade = '';
    if (sec > 0.005) {
      const pts = [];
      for (let k = 0; k <= 32; k++) { const u = k / 32; pts.push((xs + (xe - xs) * u - G.l).toFixed(1) + ',' + (yb - Math.pow(u, ex) * (yb - yt)).toFixed(1)); }
      fLine = 'M' + pts.join('L');
      fShade = fLine + `L${(xs - G.l).toFixed(1)},${yt}Z`;
    }
    if (!p[4] && xe + 6 >= G.l) fades.push({ i, line: fLine, shade: fShade, hx: Math.max(G.l, sec > 0.005 ? xe : xs + 8), showT: sec > 0.02 && xe - xs > 18,
      tx: (xs + xe) / 2, ty: 170 + yb - Math.pow(0.5, ex) * (yb - yt), title: sec > 0.005 ? `Fade in ${Math.round(sec * 1000)} ms · drag to change · double-click to remove` : 'Drag right to add a fade in' });
    const playingThis = S && S.audition === i;
    const tname = p[9] || `Take ${i + 1}`;
    const name = w > 120 ? `${tname} · ${label}` : w > 44 ? tname : w > 22 ? String(i + 1) : '';
    return { i, x, w, lx: x + 12, label: name, head, headOp: i === focus ? 1 : 0.78, renaming: !!(L.rename && L.rename.i === i), renameVal: L.rename && L.rename.i === i ? L.rename.v : '', rx: x + w, edges: !p[4], hw: Math.max(0, w - 16),
      title: `Take ${i + 1} · ${label} · drag to move · drag an edge to trim or extend (Alt: stretch time)`, color, fill, busy: p[2] === 2 && p[3] > 0, barW: Math.max(20, w - 24), progW: Math.max(2, (w - 24) * p[3]),
      ring: i === focus && L.takeSel ? `inset 0 0 0 2px ${t.accent}` : i === focus ? `inset 0 0 0 1.5px ${dark ? 'rgba(255,255,255,0.75)' : 'rgba(0,0,0,0.45)'}` : `inset 0 0 0 0.5px ${dark ? 'rgba(255,255,255,0.10)' : 'rgba(0,0,0,0.10)'}`,
      wave, waveFill: dark ? 'rgba(48,209,88,0.16)' : 'rgba(40,167,69,0.14)',
      playing: playingThis, cursorX: X(p[5] + ((S && S.auditionPos) || 0)) };
  });
  // barra fixa do take em foco (não some quando a vista rola)
  let takeBar = null;
  if (phrases.length && focus >= 0) {
    const p = phrases[focus], playingThis = S && S.audition === focus, rendered = p[2] === 1;
    let [st, stColor] = STATE[p[2]];
    if (p[4]) st = 'Capturing', stColor = t.rec;
    if (p[2] === 2) st = p[3] > 0 ? `Rendering ${Math.round(p[3] * 100)}%` : 'Queued';
    if (rendered) st = 'Rendered ✓';
    takeBar = { title: (p[9] ? p[9] + ' · ' : 'Take ') + `${focus + 1}/${phrases.length}`, st, stColor, rendered, i: focus,
      prev: () => focusTake(focus - 1), next: () => focusTake(focus + 1),
      listen: () => send({ cmd: 'audition', phrase: focus }), listenLabel: playingThis ? '■ Stop' : '▶ Listen',
      listenBg: playingThis ? t.ok : t.fill, listenFg: playingThis ? '#FFFFFF' : t.text,
      renderTitle: rendered ? 'Render this take again' : 'Render this take', doRender: () => send({ cmd: rendered ? 'reRender' : 'renderPhrase', phrase: focus }),
      doUnrender: () => { if (rendered) send({ cmd: 'unrender', phrase: focus }); }, unOp: rendered ? 1 : 0.35,
      doDelete: () => { send({ cmd: 'deleteTake', phrase: focus }); L.focus = null; L.sel = new Set(); dirty = true; } };
  }
  // barra vertical: move a seleção, o take em foco ou todas as notas
  const scope = L.moveScope || 'take', fp = phrases[focus];
  const moveIds = scope === 'all' ? capIn.map((_, i) => i) : scope === 'sel' ? [...sel]
    : fp ? capIn.map((c, i) => [c, i]).filter(([c]) => c[0] >= fp[0] - 0.01 && c[0] <= fp[1] + 0.01).map(([, i]) => i) : [];
  L.moveIds = moveIds;
  const mvSend = (dt, dp) => () => {
    if (!moveIds.length) return;
    send({ cmd: 'noteEdit', ids: moveIds, dt, de: 0, dp });
    if (dp && capIn[moveIds[0]]) previewNote(capIn[moveIds[0]][2] + dp);
    L.moveHold = { ids: new Set(moveIds), dt, dp }; hold(); dirty = true;
  };
  const SCOPES = { sel: ['SEL', 'selected notes'], take: ['TAKE', 'the take in the bar above'], all: ['ALL', 'every note'] };
  const mv = { scope: SCOPES[scope][0], op: moveIds.length ? 1 : 0.35,
    scopeTitle: `Moves ${SCOPES[scope][1]} · click to switch (selection / take / all)`,
    scopePick: () => { L.moveScope = { sel: 'take', take: 'all', all: 'sel' }[scope]; dirty = true; },
    up: [{ label: 'Oct+', title: 'Up an octave', pick: mvSend(0, 12) }, { label: 'Up', title: 'Up a semitone', pick: mvSend(0, 1) }],
    down: [{ label: 'Down', title: 'Down a semitone', pick: mvSend(0, -1) }, { label: 'Oct−', title: 'Down an octave', pick: mvSend(0, -12) }],
    side: [{ label: 'Left', title: 'Earlier by one grid step', pick: mvSend(-(snapStep() || beat / 4), 0) }, { label: 'Right', title: 'Later by one grid step', pick: mvSend(snapStep() || beat / 4, 0) }] };
  // dinâmica: o traço aparece na curva enquanto é desenhado
  const stroke = L.dynPts && L.dynPts.length > 1 ? L.dynPts : L.dynHold;
  let dynSrc = dynIn;
  if (stroke && stroke.length > 1) {
    const sp = [...stroke].sort((a, b) => a[0] - b[0]), a = sp[0][0], b = sp[sp.length - 1][0];
    dynSrc = dynIn.filter((d) => d[0] < a || d[0] > b).concat(sp).sort((p, q) => p[0] - q[0]);
  }
  const dpts = dynSrc.filter((d) => d[0] >= v0 && d[0] <= v1).map((d) => [X(d[0]) - G.l, 62 - (d[1] - 20) / 104 * 58]);
  const dynLine = dpts.map((p) => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const dynArea = dpts.length ? `${dpts[0][0].toFixed(1)},64 ${dynLine} ${dpts[dpts.length - 1][0].toFixed(1)},64` : '';
  const lane = vis.map((n) => ({ id: n[3], start: n[0], end: n[1], why: n[5] }));
  lane.sort((p, q) => p.start - q.start);
  const laneOut = [];
  for (let k = 0; k < lane.length; k++) {
    const c = lane[k];
    const x = Math.max(G.l, X(c.start));
    if (x > X1) continue;
    const nextX = k + 1 < lane.length ? X(lane[k + 1].start) : X1 + 4;
    const w = Math.max(6, Math.min(Math.max(X(c.end) - x, 10), nextX - x - 2, X1 + 4 - x));  // nunca invade o próximo
    laneOut.push({ x, w, label: w > 52 ? ART_NAMES[c.id] : '', bg: AC[c.id], fg: TXT(c.id), title: `${ART_NAMES[c.id]}: ${c.why}` });
  }
  const tip = L.velTip || L.fadeTip;
  const rendered = (S && S.rendered) || 0;
  const summary = phrases.length
    ? `${phrases.length} phrase${phrases.length > 1 ? 's' : ''} captured · ${rendered} rendered · capture follows the playhead`
    : '';

  // ---- sliders
  const slider = (id, label, i, value) => ({ id, label, pct: P(id).n * 100, value: value ?? P(id).text, sep: i ? '0.5px solid ' + t.sep : 'none' });
  const takesN = Math.round(P('takes').v);
  const instSliders = [slider('intensity', 'Dynamics intensity', 0), slider('level', 'Preview level', 1), slider('legatoGap', 'Legato gap', 2),
    slider('portaVel', 'Portamento velocity', 3, '< ' + Math.round(P('portaVel').v)), slider('takes', 'Takes per phrase', 4, takesN ? String(takesN) : 'Auto'),
    slider('dynFollow', 'Dynamics follow', 5), slider('vibAmount', 'Extra vibrato', 6), slider('vibRate', 'Vibrato rate', 7),
    slider('evenOut', 'Even out (long notes vs attacks)', 8), slider('modelDyn', 'Model dynamics (CC1, experimental)', 9, P('modelDyn').v > 0.5 ? 'On' : 'Off')];
  const eqSliders = [['eqLow', 'Low'], ['eqMid', 'Mid'], ['eqHigh', 'High'], ['eqAir', 'Air']].map(([id, label], i) => {
    const pct = P(id).n * 100;
    return { id, label, pct, value: P(id).text, sep: i ? '0.5px solid ' + t.sep : 'none', fill: Math.abs(pct - 50), shift: pct < 50 ? -(50 - pct) : 0 };
  });
  const revSliders = [slider('reverbMix', 'Mix', 0), slider('decay', 'Decay', 1), slider('predelay', 'Pre-delay', 2)];
  const fs = (id, label, bipolar) => {
    const pct = P(id).n * 100;
    return { id, label, pct, value: P(id).text, fillLeft: bipolar ? Math.min(50, pct) : 0, fillW: bipolar ? Math.abs(pct - 50) : pct };
  };
  const fxMod = (label, onId, sliders, extra) => {
    const on = P(onId).v > 0.5;
    return { label, on, toggle: () => setV(onId, on ? 0 : 1), track: on ? t.green : t.off, knob: on ? 18 : 2, opacity: on ? 1 : 0.5, sliders, ...extra };
  };
  const fxModules = [
    fxMod('Equalizer', 'eqOn', [fs('eqLow', 'Low', true), fs('eqMid', 'Mid', true), fs('eqHigh', 'High', true), fs('eqAir', 'Air', true)]),
    fxMod('Compressor', 'compOn', [fs('compThresh', 'Threshold'), fs('compRatio', 'Ratio'), fs('compAttack', 'Attack'), fs('compRelease', 'Release'), fs('compMakeup', 'Makeup')]),
    fxMod('Stereo', 'stereoOn', [fs('stereoWidth', 'Width')]),
    fxMod('Saturation', 'satOn', [fs('satDrive', 'Drive')]),
    fxMod('Chorus', 'chorusOn', [fs('chorusRate', 'Rate'), fs('chorusDepth', 'Depth'), fs('chorusMix', 'Mix')]),
    fxMod('Delay', 'delayOn', [fs('delayTime', 'Time'), fs('delayFeedback', 'Feedback'), fs('delayMix', 'Mix')]),
    fxMod('Reverb', 'reverb', [fs('reverbMix', 'Mix'), fs('decay', 'Decay'), fs('predelay', 'Pre-delay')], { room: true })
  ];
  const revOn = P('reverb').v > 0.5;
  const mix = idx('mixStyle');
  const mixInfo = [['Dry', 'Your own reverb'], ['Lyrical', 'Chamber · close'], ['Romantic', 'Concert hall · warm'], ['Baroque', 'Church · distant'], ['Cinematic', 'Scoring stage · wide']];
  const mixes = mixInfo.map(([label, hint], i) => ({ label, hint, on: mix === i, pick: () => setV('mixStyle', i), ring: mix === i ? '0 0 0 2px ' + t.accent : t.cardShadow,
    sideBg: mix === i ? t.accent : t.fill, sideFg: mix === i ? '#FFFFFF' : t.text }));
  // Sound Presets: Mix (sala, reverb, timbre) e Playstyle (ligado, portamento, dinâmica, vibrato) lado a lado
  const STYLES = [['Natural', 'As played · your Instrument settings'], ['Lyrical', 'Singing · smooth, a little more vibrato'], ['Romantic', 'Slides and wide dynamics · more vibrato'],
    ['Classical', 'Clean and articulate · little portamento'], ['Baroque', 'Detached · no portamento, gentle dynamics'], ['Cinematic', 'Everything connected · big dynamics']];
  const sty = idx('playStyle');
  const menuAt = (e) => { const r = root.getBoundingClientRect(), s = r.width / 1280, b = e.target.closest('button').getBoundingClientRect(); return [(b.left - r.left) / s, (b.bottom - r.top) / s + 4]; };  // logo abaixo do botão
  const mixPick = (e) => openMenu(...menuAt(e), [{ head: 'Mix preset' }, ...mixInfo.map(([label, hint], i) => ({ label, key: hint, check: mix === i, pick: () => setV('mixStyle', i) }))]);
  const stylePick = (e) => openMenu(...menuAt(e), [{ head: 'Playstyle' }, ...STYLES.map(([label, hint], i) => ({ label, key: hint, check: sty === i, pick: () => setV('playStyle', i) }))]);

  // ---- teclado
  const KS = { 36: 'auto', 38: 'sustain', 40: 'legato', 41: 'spiccato', 43: 'staccato', 45: 'pizzicato', 47: 'tremolo', 48: 'trill', 50: 'portamento', 52: 'harmonic' };
  const NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const WK = 1172 / 52, pressed = new Set((S && S.keys) || []);
  const whites = [], blacks = [], whiteLabels = [];
  let wi = 0;
  for (let n = 21; n <= 108; n++) {
    const isBlack = [1, 3, 6, 8, 10].includes(n % 12);
    const name = NAMES[n % 12] + (Math.floor(n / 12) - 2);
    const inRange = n >= 55 && n <= 105;
    if (!isBlack) {
      const ks = KS[n];
      whites.push({ note: n, x: wi * WK, w: WK - 1, bg: pressed.has(n) ? t.keyPress : ks ? AC[ks] : inRange ? t.keyWhite : t.keyDim, name: ks ? name + ' · ' + ks : name });
      if (n % 12 === 0) whiteLabels.push({ x: wi * WK, w: WK - 1, name, fg: ks ? TXT(ks) : inRange ? t.labelOn : t.secondary });
      wi++;
    } else {
      blacks.push({ note: n, x: wi * WK - WK * 0.31, w: WK * 0.62, bg: pressed.has(n) ? t.keyPress : inRange ? t.keyBlack : t.keyBlackDim });
    }
  }
  const bend = S ? S.bend : 8192, mod = S ? S.mod : 0;
  const wheels = [{ label: 'Pitch', pos: 4 + (1 - bend / 16383) * 74 }, { label: 'Mod', pos: 4 + (1 - mod / 127) * 74 }];

  // ---- motor, saída
  const en = (S && S.engine) || {};
  const busy = phrases.some((p) => p[2] === 2);
  let engineState = 'Engine ready', engineDot = t.ok;
  if (!S) engineState = 'Connecting…', engineDot = t.secondary;
  else if (en.samplesState === 3) engineState = 'Samples error: ' + (en.samplesError || 'unknown'), engineDot = t.rec;
  else if (!en.samples) engineState = 'Loading samples…', engineDot = t.warn;
  else if (en.loading) engineState = 'Loading model…', engineDot = t.warn;
  else if (en.error) engineState = 'Engine error: ' + en.error, engineDot = t.rec;
  else if (busy) engineState = 'Rendering' + (en.queued ? ` · ${en.queued} queued` : ''), engineDot = t.warn;
  else if (!en.loaded) engineState = 'Model unloaded · loads on render', engineDot = t.secondary;
  const total = en.total || 0, used = en.used || 0;
  const toPct = (lin) => Math.max(0, Math.min(100, (20 * Math.log10(Math.max(lin, 1e-6)) + 60) / 60 * 100));
  const meters = (S && S.meters) || [0, 0];
  const capOn = P('capture').v > 0.5, autoOn = P('autorender').v > 0.5;
  const audible = S && S.renderAudible;
  return {
    t, dark, light: !dark, toggleTheme: () => pref('dark', !dark), G, pOp: 1 - L.geoK, pSc: 1 - 0.04 * L.geoK, pPe: L.geoK > 0.5 ? 'none' : 'auto', pVis: L.geoK > 0.99 ? 'hidden' : 'visible',
    toggleFocus: () => pref('focusMode', !(L.focusMode ?? prefs.focusMode)), focusOn: wide, focusBg: wide ? t.accentSoft : 'transparent',
    tabs, isPerf: tab === 'perf', isInst: tab === 'inst', isFx: tab === 'fx', isScore: tab === 'score',
    playModes, articModes, qualities, qualityHint: qInfo[q][1], artics, shortModes, isShorts: play === 1,
    stepsPct: P('renderSteps').n * 100, stepsText: String(Math.round(P('renderSteps').v)),
    bars, regions, notes, showPlayhead: S && playhead >= v0 && playhead <= v1, playX: X(playhead),
    empty: !phrases.length, emptyHint: S && S.playing ? 'Capturing: press play in your DAW with a MIDI clip, or play your keyboard.' : 'Press play in your DAW (Capture is on) or play the keyboard below. Each phrase renders with AI when it ends.',
    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes, fxModules, mixPick, stylePick,
    mixName: mixInfo[mix] ? mixInfo[mix][0] : 'Dry', styleName: STYLES[sty] ? STYLES[sty][0] : 'Natural', styleBg: sty ? t.accent : t.fill, styleFg: sty ? '#FFFFFF' : t.text,
    hasNotes: capIn.length > 0, palette, dragChip, grid, rows, hscroll, velStems, takeBar, mv, fades, tip,
    ...toolVals(capIn), doSplitTake: () => send({ cmd: 'splitTake', t: (S && S.internalPos) || 0 }),
    dynClear: () => send({ cmd: 'dynClear' }), fadeShade: dark ? 'rgba(0,0,0,0.34)' : 'rgba(0,0,0,0.10)', fadeLine: dark ? 'rgba(255,255,255,0.9)' : 'rgba(29,29,31,0.75)',
    toggleBypass: () => setV('fxBypass', P('fxBypass').v > 0.5 ? 0 : 1), bypassLabel: P('fxBypass').v > 0.5 ? 'FX OFF' : 'FX ON',
    bypassBg: P('fxBypass').v > 0.5 ? t.rec : t.fill, bypassFg: P('fxBypass').v > 0.5 ? '#FFFFFF' : t.text,
    doPlay: () => send({ cmd: 'play' }), doRewind: () => send({ cmd: 'rewind' }), playLabel: S && S.internalPlay ? 'Stop (back to where play started)' : 'Play from the cursor',
    playIcon: S && S.internalPlay ? 'M3 3h8v8H3z' : 'M4 2.5v9l7.5-4.5z',
    playBg: S && S.internalPlay ? t.ok : t.fill, playFg: S && S.internalPlay ? '#FFFFFF' : t.text,
    lockOn: P('lock').v > 0.5, toggleLock: () => setV('lock', P('lock').v > 0.5 ? 0 : 1),
    lockBg: P('lock').v > 0.5 ? 'rgba(255,149,0,0.18)' : t.fill, lockFg: P('lock').v > 0.5 ? t.warn : t.text,
    lockIcon: P('lock').v > 0.5 ? 'M3.5 6.5V4.5a3 3 0 016 0v2M2 6.5h9v6H2z' : 'M3.5 6.5V4.5a3 3 0 015.6-1.5M2 6.5h9v6H2z',
    revOn, toggleReverb: () => setV('reverb', revOn ? 0 : 1), revTrack: revOn ? t.green : t.off, revKnob: revOn ? 20 : 2,
    roomName: ROOMS[idx('room')], nextRoom: () => setV('room', (idx('room') + 1) % 5),
    whites, blacks, whiteLabels, wheels,
    capOn, toggleCapture: () => setV('capture', capOn ? 0 : 1), capBg: capOn ? 'rgba(255,59,48,0.14)' : t.fill,
    capFg: capOn ? t.rec : t.text, capDot: capOn ? t.rec : t.secondary,
    autoOn, toggleAuto: () => setV('autorender', autoOn ? 0 : 1), autoTrack: autoOn ? t.green : t.off, autoKnob: autoOn ? 16 : 2,
    engineState, engineDot, gpuName: en.gpu || '', gpuShort: en.gpu ? en.gpu.replace(/NVIDIA GeForce |AMD Radeon /, '') : 'GPU',
    vram: en.loaded ? `${used.toFixed(1)} of ${total.toFixed(0)} GB` : `0 of ${total.toFixed(0)} GB`, vramPct: total ? used / total * 100 : 0,
    modelButton: en.loaded ? 'Unload Model' : (en.loading ? 'Loading…' : 'Load Model'), toggleModel: () => send({ cmd: 'model' }),
    nowLabel: audible ? 'AI Render' : 'Preview', nowDot: audible ? t.ok : t.accent,
    nowHint: audible ? 'Playing the rendered performance' : 'Preview takes over where nothing is rendered yet',
    meterL: toPct(meters[0]), meterR: toPct(meters[1]), outTop: (1 - P('output').n) * 88, outText: P('output').text,
    doRender: () => send({ cmd: S && S.busy ? 'stopRender' : 'render' }), renderLabel: S && S.busy ? '■ Stop' : 'Render',
    renderBg: S && S.busy ? t.rec : t.accent, doClear: () => send({ cmd: 'clear' }), doExport: () => send({ cmd: 'export' }),
    doFit: () => { L.zoomT = 1; L.vzoom = 1; L.vcenter = null; dirty = true; }, zoom: Math.min(8, L.zoom), zoomPct: Math.min(100, (L.zoom - 1) / 7 * 100),
    ...settingsVals(t, seg, en),
    unrenderAll: () => send({ cmd: 'unrenderAll' }),
    ...fxVals(t), rticks, ...editVals(t, AC, TXT, { phrases, v0, v1, fullA, fullB, X, dark }),
    ...(tab === 'score' ? scoreVals(t) : {}),
    setZoom: (e) => { const z = +e.target.value; if (L.zoomAt == null && L.view) L.zoomAt = (L.view.v0 + L.view.v1) / 2; L.zoom = L.zoomT = z; dirty = true; }
  };
}

// ---- painel Settings
function settingsVals(t, seg, en) {
  const st = (S && S.settings) || {};
  const scale = L.scale ?? st.scale ?? 1;
  const setScale = (v) => { v = Math.round(Math.min(2, Math.max(0.75, v)) * 20) / 20; L.scale = v; send({ cmd: 'setting', key: 'uiScale', value: v }); dirty = true; };
  const autoLoad = L.autoLoad ?? (st.autoLoad !== false);
  const ss = en.samplesState;
  return {
    showSettings: !!L.settings, toggleSettings: () => { L.settings = !L.settings; dirty = true; }, closeSettings: () => { L.settings = false; dirty = true; },
    scaleText: Math.round(scale * 100) + '%', scaleDown: () => setScale(scale - 0.05), scaleUp: () => setScale(scale + 0.05),
    scales: [0.75, 1, 1.25, 1.5, 1.75, 2].map((v) => ({ label: v * 100 + '%', pick: () => setScale(v), ...seg(Math.abs(scale - v) < 0.01) })),
    autoLoad, toggleAutoLoad: () => { L.autoLoad = !autoLoad; send({ cmd: 'setting', key: 'autoLoadModel', value: !autoLoad }); dirty = true; },
    autoLoadTrack: autoLoad ? t.green : t.off, autoLoadKnob: autoLoad ? 20 : 2,
    modelStatus: en.loading ? 'Loading model…' : en.loaded ? 'Model loaded' : 'Model not loaded',
    samplesStatus: ss === 2 ? `Loaded · ${en.samplesCount} samples` : ss === 3 ? 'Error: ' + (en.samplesError || 'unknown') : 'Loading…',
    samplesColor: ss === 3 ? t.rec : t.text, reloadSamples: () => send({ cmd: 'reloadSamples' }),
    modelDir: st.modelDir || '', sampleDir: st.sampleDir || ''
  };
}

root.addEventListener('wheel', (e) => {
  if (!L.view || !L.full || !e.target.closest('[data-roll],[data-cap],[data-ruler],[data-vellane],[data-dynlane],[data-hscroll]')) return;
  const pt = cpt(e), V = L.view;
  const cap = e.target.closest('[data-cap]');
  // roda numa nota selecionada (ou com Alt): velocity
  if (cap && !e.ctrlKey && (e.altKey || (L.sel && L.sel.has(+cap.dataset.cap)))) { velWheel(+cap.dataset.cap, e.deltaY < 0 ? 4 : -4, pt); e.preventDefault(); return; }
  if (e.altKey && !cap) {  // Alt + roda fora das notas: altura das notas (zoom vertical); Shift + roda: rola na vertical
    L.vzoom = Math.max(1, Math.min(6, (L.vzoom || 1) * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    dirty = true; e.preventDefault(); return;
  }
  if (e.shiftKey && !e.ctrlKey && (L.vzoom || 1) > 1.01) { L.vcenter = (L.vcenter ?? 72) + (e.deltaY < 0 ? 1 : -1); dirty = true; e.preventDefault(); return; }
  if (L.zoomAt == null) L.zoomAt = (V.v0 + V.v1) / 2;
  if (e.ctrlKey) {  // Ctrl + roda: zoom em volta do cursor
    const tCur = timeAt(pt.x), z1 = Math.max(1, Math.min(64, (L.zoomT ?? L.zoom ?? 1) * (e.deltaY < 0 ? 1.25 : 0.8)));
    L.zoomT = z1; L.atT = tCur - (pt.x - X0 - XW / 2) / XW * ((L.full.b - L.full.a) / z1);
  } else if ((L.zoomT ?? L.zoom ?? 1) > 1.01) {  // roda: rola na horizontal
    const d = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    L.atT = (L.atT ?? L.zoomAt) + Math.sign(d) * Math.min(120, Math.abs(d)) / XW * (V.v1 - V.v0) * 0.8;
  } else return;
  dirty = true; e.preventDefault();
}, { passive: false });
root.addEventListener('dblclick', (e) => {
  const fh = e.target.closest('[data-fade]');
  if (fh) { send({ cmd: 'fade', phrase: +fh.dataset.fade, sec: 0 }); return; }  // duplo clique na alça: sem fade
  const ft = e.target.closest('[data-fadet]');
  if (ft) { send({ cmd: 'fade', phrase: +ft.dataset.fadet, tension: 0.5 }); return; }  // curva padrão
  if (!e.target.closest('[data-roll]') || !L.view) return;
  const pt = cpt(e), V = L.view, tt = snapT(timeAt(pt.x)), len = snapStep() ? Math.max(snapStep(), beatSec() / 2) : 0.5;
  const p = Math.round(V.pLo + (392 - pt.y) / 200 * (V.pHi - V.pLo));
  send({ cmd: 'noteAdd', s: tt, e: tt + len, p });
  previewNote(p);
});
addEventListener('keydown', (e) => {
  // Espaço: play / parar (parar volta para onde o play começou, como no DAW)
  if (e.code === 'Space' && S && S.standalone && !e.repeat && !(e.target && /INPUT|TEXTAREA/.test(e.target.tagName))) { send({ cmd: 'play' }); e.preventDefault(); return; }
});

// foco do teclado (para o Espaço): ao abrir e a cada clique, mesmo nos controles que cancelam o clique padrão
document.body.tabIndex = -1;
const grabFocus = () => { if (document.activeElement !== document.body) document.body.focus({ preventScroll: true }); window.focus(); };
addEventListener('pointerdown', grabFocus, true);
addEventListener('auxclick', (e) => { if (e.button === 1) e.preventDefault(); });
addEventListener('mousedown', (e) => { if (e.button === 1) e.preventDefault(); });  // sem a rolagem automática do botão do meio
addEventListener('load', grabFocus);
setTimeout(grabFocus, 300);

fit();
paint();
requestAnimationFrame(frame);
