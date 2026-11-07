// Edição estilo DAW: grade (Auto / Snap / Free), seleção por caixa, atalhos (Ctrl+C/V/X/A/D/Z), menu do botão
// direito, régua em compassos (arrastar = zoom/rolagem, como no Ableton), visão geral, renomear takes, BPM.
'use strict';

// ------------------------------------------------------------------ grade
const GRID_DIVS = [[4, '1 Bar'], [2, '1/2'], [1, '1/4'], [0.5, '1/8'], [0.25, '1/16'], [0.125, '1/32'], [1 / 3, '1/8T'], [1 / 6, '1/16T']];
function beatSec() { return 60 / ((S && S.bpm) || 120); }
function gridMode() { return L.gridMode || (S && S.prefs && S.prefs.gridMode) || 'auto'; }
function gridDiv() { return L.gridDiv ?? (S && S.prefs && S.prefs.gridDiv) ?? 0.25; }
function autoDiv(span) {  // Automatic: a divisão acompanha o zoom (uma linha a cada ~18 px)
  const px = XW / (span / beatSec());
  for (const d of [0.0625, 0.125, 0.25, 0.5, 1, 2, 4, 8, 16]) if (px * d >= 18) return d;
  return 32;
}
function gridStepBeats() { return gridMode() === 'snap' ? gridDiv() : autoDiv(L.view ? L.view.v1 - L.view.v0 : 10); }
function snapStep() { return gridMode() === 'free' ? 0 : gridStepBeats() * beatSec(); }
function snapT(t) { const g = snapStep(); return g ? Math.round(t / g) * g : t; }
function snapDt(anchor, dt) { return snapStep() ? snapT(anchor + dt) - anchor : dt; }
function divName(d) { const f = GRID_DIVS.find(([v]) => Math.abs(v - d) < 1e-6); return f ? f[1] : d >= 4 ? d / 4 + ' Bars' : '1/' + Math.round(4 / d); }
function setGrid(mode, div) { L.gridMode = mode; send({ cmd: 'pref', key: 'gridMode', value: mode }); if (div != null) { L.gridDiv = div; send({ cmd: 'pref', key: 'gridDiv', value: div }); } dirty = true; }
function gridMenu(x, y) {
  const m = gridMode(), d = gridDiv();
  openMenu(x, y, [
    { label: 'Automatic grid', key: 'follows zoom', check: m === 'auto', pick: () => setGrid('auto') },
    { label: 'Free (no snap)', check: m === 'free', pick: () => setGrid('free') },
    { sep: true }, { head: 'Snap to grid' },
    ...GRID_DIVS.map(([v, name]) => ({ label: name, check: m === 'snap' && Math.abs(d - v) < 1e-6, pick: () => setGrid('snap', v) }))
  ]);
}

// ------------------------------------------------------------------ menu flutuante (contexto, grade)
function openMenu(x, y, items) {
  const h = items.reduce((a, it) => a + (it.sep ? 9 : it.chips ? 52 : 26), 10);
  L.pmenu = { x: Math.max(8, Math.min(x, 1272 - 210)), y: Math.max(8, Math.min(y, 932 - h)), items }; dirty = true;
}
function menuVals(AC, TXT) {
  const m = L.pmenu;
  if (!m) return { pmenu: null, closeMenuP: () => {} };
  const close = () => { L.pmenu = null; dirty = true; };
  return {
    closeMenuP: close,
    pmenu: { x: m.x, y: m.y, items: m.items.map((it) => ({
      sep: !!it.sep, head: it.head || '', isHead: !!it.head, row: !it.sep && !it.head && !it.chips, label: it.label || '', key: it.key || '',
      check: it.check ? '✓' : '', op: it.disabled ? 0.38 : 1,
      pick: () => { if (it.disabled) return; close(); it.pick(); },
      chips: it.chips ? it.chips.map((c) => ({ label: c.label, bg: AC[c.id], fg: TXT(c.id), pick: () => { close(); c.pick(); } })) : null
    })) }
  };
}

// ------------------------------------------------------------------ área de transferência e seleção
function capArr() { return (S && S.cap) || []; }
function takeIds(k = L.focus) {
  const ph = S && S.phrases && S.phrases[k];
  return ph ? capArr().map((c, i) => [c, i]).filter(([c]) => c[0] >= ph[0] - 0.01 && c[0] <= ph[1] + 0.01).map(([, i]) => i) : [];
}
function copyIds(ids) {
  const ns = ids.map((i) => capArr()[i]).filter(Boolean);
  if (!ns.length) return false;
  const t0 = Math.min(...ns.map((c) => c[0])), t1 = Math.max(...ns.map((c) => c[1]));
  L.clip = { len: t1 - t0, notes: ns.map((c) => [c[0] - t0, c[1] - t0, c[2], c[3], c[4] ?? 90]) };
  return true;
}
function copySel() { return L.sel && L.sel.size ? copyIds([...L.sel]) : L.takeSel ? copyIds(takeIds()) : false; }
function delSel() {
  if (L.sel && L.sel.size) { send({ cmd: 'noteDel', ids: [...L.sel] }); L.sel = new Set(); dirty = true; return true; }
  if (L.takeSel && L.focus != null) { send({ cmd: 'deleteTake', phrase: L.focus }); L.takeSel = false; L.focus = null; dirty = true; return true; }
  return false;
}
function cutSel() { if (copySel()) delSel(); }
function pasteRaw(t) { if (L.clip) send({ cmd: 'noteAddMany', notes: L.clip.notes.map((n) => [n[0] + t, n[1] + t, n[2], n[3], n[4]]) }); }
function pasteAtCursor() { pasteRaw(snapT(Math.max(0, (S && S.internalPos) || 0))); }
function dupSel() {
  const ids = L.sel && L.sel.size ? [...L.sel] : L.takeSel ? takeIds() : [];
  if (!copyIds(ids)) return;
  const t0 = Math.min(...ids.map((i) => capArr()[i][0])), g = snapStep(), at = t0 + L.clip.len;
  pasteRaw(g ? Math.ceil(at / g - 1e-6) * g : at);  // logo depois, no próximo ponto da grade
}
// desfazer/refazer: limpa a seleção e tudo que estava segurado na tela (os índices das notas mudam)
function undoRedo(cmd) { send({ cmd }); L.sel = new Set(); L.takeSel = false; releaseHold(); L.velTouched = new Set(); dirty = true; }
function selAll() { L.sel = new Set(capArr().map((_, i) => i)); L.takeSel = false; dirty = true; }

// ------------------------------------------------------------------ menus de contexto
function noteMenu(x, y) {
  const sel = [...(L.sel || [])];
  const tool = (op, arg, extra) => () => send({ cmd: 'noteTool', ids: sel, op, arg, ...(extra || {}) });
  openMenu(x, y, [
    { label: 'Cut', key: 'Ctrl+X', pick: cutSel }, { label: 'Copy', key: 'Ctrl+C', pick: copySel },
    { label: 'Paste at cursor', key: 'Ctrl+V', pick: pasteAtCursor, disabled: !L.clip }, { label: 'Duplicate', key: 'Ctrl+D', pick: dupSel },
    { label: 'Delete', key: 'Del', pick: delSel }, { sep: true },
    { label: 'Quantize to grid', pick: () => send({ cmd: 'noteTool', ids: sel, op: 'quantize', arg: gridMode() === 'free' ? 0.25 : gridStepBeats() }) },
    { label: 'Humanize', pick: tool('humanize', 15) }, { label: 'Legato', pick: tool('legato', 0) },
    { label: 'Split in two', pick: tool('split', 0) }, { label: 'Reverse', pick: tool('reverse', 0) },
    { label: 'Octave up', pick: tool('transpose', 12) }, { label: 'Octave down', pick: tool('transpose', -12) }, { sep: true },
    { chips: ART_IDS.map((id, i) => ({ id, label: i ? ART_NAMES[id] : 'Auto', pick: () => send({ cmd: 'noteArt', ids: sel, art: i }) })) },
    { sep: true }, { label: 'Select all', key: 'Ctrl+A', pick: selAll }
  ]);
}
function takeMenu(x, y, k) {
  const p = S.phrases[k], rendered = p && p[2] === 1;
  L.focus = k; L.takeSel = true; L.sel = new Set();
  openMenu(x, y, [
    { label: 'Rename…', pick: () => startRename(k) },
    { label: rendered ? 'Listen' : 'Listen (render first)', pick: () => send({ cmd: 'audition', phrase: k }), disabled: !rendered },
    { label: rendered ? 'Render again' : 'Render', pick: () => send({ cmd: rendered ? 'reRender' : 'renderPhrase', phrase: k }) },
    { label: 'Remove render', pick: () => send({ cmd: 'unrender', phrase: k }), disabled: !rendered }, { sep: true },
    { label: 'Copy take', key: 'Ctrl+C', pick: () => copyIds(takeIds(k)) }, { label: 'Duplicate take', key: 'Ctrl+D', pick: dupSel },
    { label: 'Paste at cursor', key: 'Ctrl+V', pick: pasteAtCursor, disabled: !L.clip },
    { label: 'Split at cursor', pick: () => send({ cmd: 'splitTake', t: (S && S.internalPos) || 0 }) },
    { label: 'Select notes', pick: () => { L.sel = new Set(takeIds(k)); L.takeSel = false; dirty = true; } }, { sep: true },
    { label: 'Delete take', key: 'Del', pick: () => { send({ cmd: 'deleteTake', phrase: k }); L.focus = null; L.takeSel = false; } }
  ]);
}
function rollMenu(x, y) {
  openMenu(x, y, [
    { label: 'Paste at cursor', key: 'Ctrl+V', pick: pasteAtCursor, disabled: !L.clip },
    { label: 'Select all', key: 'Ctrl+A', pick: selAll },
    { label: 'Undo', key: 'Ctrl+Z', pick: () => undoRedo('undo'), disabled: !(S && S.canUndo) },
    { label: 'Redo', key: 'Ctrl+Shift+Z', pick: () => undoRedo('redo'), disabled: !(S && S.canRedo) }, { sep: true },
    { label: 'Grid…', pick: () => gridMenu(x, y) },
    { label: 'Import MIDI file…', pick: () => send({ cmd: 'importDialog' }) }, { label: 'Classical library…', pick: () => { L.lib = true; dirty = true; } }
  ]);
}
root.addEventListener('contextmenu', (e) => {
  e.preventDefault();
  if (!L.view || !(L.tab ?? (S && S.prefs && S.prefs.tab) ?? 'perf').startsWith('perf')) return;
  const pt = cpt(e), cap = e.target.closest('[data-cap]'), rh = e.target.closest('[data-rhead],[data-redge]');
  if (cap) { const i = +cap.dataset.cap; if (!L.sel || !L.sel.has(i)) L.sel = new Set([i]); L.takeSel = false; noteMenu(pt.x, pt.y); }
  else if (rh) takeMenu(pt.x, pt.y, +(rh.dataset.rhead ?? rh.dataset.redge));
  else if (e.target.closest('[data-roll],[data-vellane],[data-ruler]')) rollMenu(pt.x, pt.y);
});

// ------------------------------------------------------------------ renomear take
function startRename(k) {
  const p = S && S.phrases[k];
  if (!p) return;
  L.rename = { i: k, v: p[9] || 'Take ' + (k + 1) }; dirty = true;
  setTimeout(() => { const el = document.querySelector('[data-rename]'); if (el) { el.focus(); el.select(); } }, 40);
}
function endRename(ok) {
  const el = document.querySelector('[data-rename]'), r = L.rename;
  if (!r) return;
  L.rename = null;
  if (ok && el) { const v = el.value.trim(); send({ cmd: 'takeName', phrase: r.i, name: v === 'Take ' + (r.i + 1) ? '' : v }); }
  dirty = true;
}
root.addEventListener('keydown', (e) => {
  if (!e.target.closest || !e.target.closest('[data-rename]')) return;
  if (e.key === 'Enter') { endRename(true); e.preventDefault(); }
  else if (e.key === 'Escape') { endRename(false); e.preventDefault(); }
  e.stopPropagation();
});
root.addEventListener('focusout', (e) => { if (e.target.closest && e.target.closest('[data-rename]')) endRename(true); });
root.addEventListener('dblclick', (e) => { const rh = e.target.closest('[data-rhead]'); if (rh) { startRename(+rh.dataset.rhead); e.stopPropagation(); } }, true);

// ------------------------------------------------------------------ atalhos
addEventListener('keydown', (e) => {
  if (e.target && /INPUT|TEXTAREA/.test(e.target.tagName)) return;
  const k = e.code, mod = e.ctrlKey || e.metaKey;
  const done = () => { e.preventDefault(); e.stopImmediatePropagation(); dirty = true; };
  if (k === 'Escape') { if (L.pmenu) L.pmenu = null; else { L.sel = new Set(); L.takeSel = false; } return done(); }
  if (mod && k === 'KeyZ') { undoRedo(e.shiftKey ? 'redo' : 'undo'); return done(); }
  if (mod && k === 'KeyY') { undoRedo('redo'); return done(); }
  if (mod && k === 'KeyA') { selAll(); return done(); }
  if (mod && k === 'KeyC') { copySel(); return done(); }
  if (mod && k === 'KeyX') { cutSel(); return done(); }
  if (mod && k === 'KeyV') { pasteAtCursor(); return done(); }
  if (mod && k === 'KeyD') { dupSel(); return done(); }
  if (k === 'Delete' || k === 'Backspace') { delSel(); return done(); }
}, true);

// ------------------------------------------------------------------ Cycle (faixa amarela na régua)
function cycleState() { const c = (S && S.cycle) || [false, 0, 0]; return L.cycOv ? { on: c[0], a: L.cycOv.a, b: L.cycOv.b } : { on: c[0], a: c[1], b: c[2] }; }
function toggleCycle() {
  const c = cycleState();
  if (c.on) { send({ cmd: 'cycle', on: false }); return; }
  if (c.b > c.a + 0.05) { send({ cmd: 'cycle', on: true }); return; }
  // primeira vez: o take em foco (ajustado aos compassos) ou 4 compassos a partir do cursor
  const bar = 4 * beatSec(), ph = S && S.phrases && S.phrases[L.focus ?? -1];
  let a, b;
  if (ph) { a = Math.floor(ph[0] / bar) * bar; b = Math.max(a + bar, Math.ceil(ph[1] / bar) * bar); }
  else { a = Math.floor(((S && S.internalPos) || 0) / bar) * bar; b = a + 4 * bar; }
  send({ cmd: 'cycle', on: true, a, b });
}

// ------------------------------------------------------------------ caixa de seleção, régua, visão geral, BPM
root.addEventListener('pointerdown', (e) => {
  const cy = e.target.closest('[data-cyc]');
  if (cy && L.view && e.button === 0) {
    const r = cy.getBoundingClientRect(), x = e.clientX - r.left, c = cycleState();
    L.cycDrag = { mode: x < 7 ? 'l' : x > r.width - 7 ? 'r' : 'm', t0: timeAt(cpt(e).x), a: c.a, b: c.b };
    cy.setPointerCapture(e.pointerId); e.preventDefault(); e.stopPropagation(); return;
  }
  const bd = e.target.closest('[data-bpmdrag="true"]');
  if (bd) { L.bpmDrag = { y: e.clientY, v0: (S && S.bpm) || 120 }; e.preventDefault(); e.stopPropagation(); return; }
  const ov = e.target.closest('[data-overview]');
  if (ov && L.view && L.full && e.button === 0) {
    ov.setPointerCapture(e.pointerId);
    const r = ov.getBoundingClientRect(), f = (e.clientX - r.left) / r.width, F = L.full, V = L.view;
    const a = (V.v0 - F.a) / (F.b - F.a), b = (V.v1 - F.a) / (F.b - F.a);
    if (L.zoomAt == null) L.zoomAt = (V.v0 + V.v1) / 2;
    if (f < a || f > b) L.atT = F.a + f * (F.b - F.a);  // fora da janela: vai para lá (suave)
    L.ovDrag = { el: ov, x: e.clientX, y: e.clientY, c0: L.atT ?? L.zoomAt, z0: L.zoomT ?? L.zoom ?? 1 };
    dirty = true; e.preventDefault(); e.stopPropagation(); return;
  }
  const ru = e.target.closest('[data-ruler]');
  if (ru && L.view && e.button === 0) {
    const pt = cpt(e);
    L.rulerDrag = { x: e.clientX, y: e.clientY, px: pt.x, t: timeAt(pt.x), z0: L.zoomT ?? L.zoom ?? 1, moved: false };
    ru.setPointerCapture(e.pointerId);
    e.preventDefault(); e.stopPropagation(); return;
  }
  const roll = e.target.closest('[data-roll]');
  if (roll && L.view && e.button === 0 && !e.altKey) {
    const pt = cpt(e), k = phraseAt(timeAt(pt.x));
    if (k >= 0) L.focus = k;
    L.takeSel = false;
    const base = e.shiftKey ? new Set(L.sel || []) : new Set();
    L.sel = new Set(base);
    L.marq = { x0: pt.x, y0: pt.y, x1: pt.x, y1: pt.y, base };
    dirty = true; e.preventDefault(); e.stopPropagation();
  }
}, true);
addEventListener('pointermove', (e) => {
  if (L.cycDrag) {
    const d = L.cycDrag, dt = timeAt(cpt(e).x) - d.t0, g = snapStep() || beatSec() / 4;
    const sn = (t) => Math.max(0, Math.round(t / g) * g);
    let a = d.a, b = d.b;
    if (d.mode === 'l') a = Math.min(sn(d.a + dt), b - g); else if (d.mode === 'r') b = Math.max(sn(d.b + dt), a + g); else { a = sn(d.a + dt); b = a + (d.b - d.a); }
    L.cycOv = { a, b }; send({ cmd: 'cycle', a, b }); dirty = true;
  }
  if (L.bpmDrag) {
    const v = Math.max(20, Math.min(300, L.bpmDrag.v0 + (L.bpmDrag.y - e.clientY) / (e.shiftKey ? 20 : 3)));
    L.bpmLocal = Math.round(v * (e.shiftKey ? 100 : 1)) / (e.shiftKey ? 100 : 1);
    send({ cmd: 'bpm', v: L.bpmLocal }); dirty = true;
  }
  if (L.marq) {
    const pt = cpt(e), m = L.marq;
    m.x1 = pt.x; m.y1 = pt.y;
    const x0 = Math.min(m.x0, m.x1), x1 = Math.max(m.x0, m.x1), y0 = Math.min(m.y0, m.y1), y1 = Math.max(m.y0, m.y1);
    const s = new Set(m.base);
    if (x1 - x0 > 2 || y1 - y0 > 2) for (const b of L.noteBoxes || []) if (b.x <= x1 && b.x + b.w >= x0 && b.y <= y1 && b.y + (b.h || 12) >= y0) s.add(b.i);
    L.sel = s; dirty = true;
  }
  if (L.rulerDrag || L.ovDrag) {
    const d = L.rulerDrag || L.ovDrag, s = cpt(e).s, dx = (e.clientX - d.x) / s, dy = (e.clientY - d.y) / s, F = L.full;
    if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
    if (!d.moved) return;
    if (L.zoomAt == null) L.zoomAt = (L.view.v0 + L.view.v1) / 2;
    const z = Math.max(1, Math.min(64, d.z0 * Math.exp((L.rulerDrag ? dy : -dy) / 70)));  // régua: arrastar para baixo aproxima
    if (L.rulerDrag) {
      const span = (F.b - F.a) / z;
      L.zoom = L.zoomT = z;
      L.zoomAt = L.atT = d.t - (d.px - X0 - XW / 2) / XW * span - dx / XW * span;
    } else {
      L.zoom = L.zoomT = z;
      L.zoomAt = L.atT = d.c0 + dx / G.ow * (F.b - F.a);
    }
    markMove(); dirty = true;
  }
});
addEventListener('pointerup', () => {
  if (L.cycDrag) { L.cycDrag = null; setTimeout(() => { L.cycOv = null; dirty = true; }, 400); }
  if (L.bpmDrag) { L.bpmDrag = null; setTimeout(() => { L.bpmLocal = null; dirty = true; }, 600); }
  if (L.marq) { L.marq = null; dirty = true; }
  if (L.rulerDrag) { if (!L.rulerDrag.moved) send({ cmd: 'seek', t: Math.max(0, L.rulerDrag.t) }); L.rulerDrag = null; }
  if (L.ovDrag) L.ovDrag = null;
});

// valores do template desta parte
function editVals(t, AC, TXT, ctx) {
  const { phrases, v0, v1, fullA, fullB, X, dark } = ctx;
  const m = L.marq;
  const marq = m && (Math.abs(m.x1 - m.x0) > 2 || Math.abs(m.y1 - m.y0) > 2)
    ? { x: Math.min(m.x0, m.x1), y: Math.min(m.y0, m.y1), w: Math.abs(m.x1 - m.x0), h: Math.abs(m.y1 - m.y0) } : null;
  const full = Math.max(1e-6, fullB - fullA);
  const heads = [dark ? '#6E6E73' : '#8E8E93', dark ? '#2FA84F' : '#34C759', t.warn, t.warn];
  const overview = phrases.length ? {
    vx: (v0 - fullA) / full * G.ow, vw: Math.max(10, (v1 - v0) / full * G.ow),
    blocks: phrases.map((p) => ({ x: (p[0] - fullA) / full * G.ow, w: Math.max(2, (p[1] - p[0]) / full * G.ow), c: p[4] ? t.rec : heads[p[2]] }))
  } : null;
  const gm = gridMode();
  const gridLabel = gm === 'free' ? 'Free' : gm === 'snap' ? 'Snap · ' + divName(gridDiv()) : 'Auto · ' + divName(autoDiv(v1 - v0));
  const bpm = L.bpmLocal ?? ((S && S.bpm) || 120), sa = !!(S && S.standalone);
  const setBpm = (v) => { L.bpmLocal = Math.max(20, Math.min(300, Math.round(v))); send({ cmd: 'bpm', v: L.bpmLocal }); dirty = true; setTimeout(() => { L.bpmLocal = null; dirty = true; }, 600); };
  const pos = S ? ((S.playing && !S.internalPlay) ? S.playhead : S.internalPos) || 0 : 0, bs = beatSec(), bar = 4 * bs;
  const posBars = `${Math.floor(pos / bar) + 1}. ${Math.floor((pos % bar) / bs) + 1}. ${Math.floor((pos % bs) / (bs / 4)) + 1}`;
  const posTime = `${Math.floor(pos / 60)}:${(pos % 60).toFixed(1).padStart(4, '0')}`;
  return {
    marq, overview, gridLabel, gridPick: (e) => { const pt = cpt(e); gridMenu(pt.x - 10, pt.y + 16); },
    bpmText: bpm.toFixed(2), bpmEdit: sa, bpmCursor: sa ? 'ns-resize' : 'default',
    bpmTitle: sa ? 'Tempo · drag up or down (Shift: fine), or use − +' : 'Tempo from your DAW',
    bpmUp: () => setBpm(bpm + 1), bpmDown: () => setBpm(bpm - 1), posBars, posTime,
    doPause: () => send({ cmd: 'pause' }), toggleCycle, cycBg: cycleState().on ? '#FFD60A' : 'transparent', cycFg: cycleState().on ? '#1D1D1F' : t.text,
    cyc: (() => { const c = cycleState(); if (!(c.b > c.a + 0.05)) return null; const xa = Math.max(G.l, X(c.a)), xb = Math.min(X1 + 2, X(c.b)); return xb > xa ? { x: xa, w: xb - xa, bg: c.on ? 'rgba(255,214,10,0.85)' : (dark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.15)') } : null; })(), doStop: () => send({ cmd: 'stop' }),
    doUndo: () => undoRedo('undo'), doRedo: () => undoRedo('redo'),
    toggleMetro: () => send({ cmd: 'metro' }), metroBg: S && S.metro ? t.accent : 'transparent', metroFg: S && S.metro ? '#FFFFFF' : t.text,
    undoOp: S && S.canUndo ? 1 : 0.35, redoOp: S && S.canRedo ? 1 : 0.35,
    ...menuVals(AC, TXT), ...libraryVals(t)
  };
}

// ------------------------------------------------------------------ biblioteca de MIDIs clássicos (Mutopia Project)
function libImport(it) {
  send({ cmd: 'importMidi', path: 'lib:' + it.file });
  const k = ['Natural', 'Lyrical', 'Romantic', 'Classical', 'Baroque', 'Cinematic'].indexOf(it.playstyle);
  if (k >= 0) setV('playStyle', k);  // o estilo sugerido para a época da peça
  L.lib = false; dirty = true;
}
function libraryVals(t) {
  if (!L.lib) return { showLib: false, toggleLib: () => { L.lib = true; dirty = true; } };
  const all = typeof LIBRARY !== 'undefined' ? LIBRARY : [], st = L.libStyle || 'All', q = (L.libQ || '').toLowerCase();
  const styles = ['All', ...[...new Set(all.map((x) => x.style))].sort()];
  const list = all.filter((x) => (st === 'All' || x.style === st) && (!q || (x.title + ' ' + x.composer).toLowerCase().includes(q)));
  const groups = [];
  for (const x of list) {
    let g = groups[groups.length - 1];
    if (!g || g.name !== x.composer) groups.push(g = { name: x.composer, items: [] });
    g.items.push({ title: x.title, tag: x.style + ' · ' + x.playstyle, pick: () => libImport(x) });
  }
  return {
    showLib: true, toggleLib: () => { L.lib = false; dirty = true; }, closeLib: () => { L.lib = false; dirty = true; },
    libGroups: groups, libCount: `${list.length} of ${all.length} pieces · Mutopia Project (public domain / CC)`,
    libStyles: styles.map((s) => ({ label: s, pick: () => { L.libStyle = s; dirty = true; }, bg: s === st ? t.accent : t.fill, fg: s === st ? '#FFFFFF' : t.text })),
    libSearch: (e) => { L.libQ = e.target.value; dirty = true; },
    libImportFile: () => { send({ cmd: 'importDialog' }); L.lib = false; dirty = true; }
  };
}
