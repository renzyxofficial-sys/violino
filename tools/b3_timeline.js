  // ---- timeline: frases, notas, dinâmica e articulação reais
  const phrases = (S && S.phrases) || [], notesIn = (S && S.notes) || [], dynIn = (S && S.dyn) || [];
  const playhead = S ? ((S.playing && !S.internalPlay) ? S.playhead : S.internalPos) || 0 : 0;
  let v0, v1;
  if (phrases.length) { v0 = Math.min(...phrases.map((p) => p[0])) - 0.5; v1 = Math.max(...phrases.map((p) => p[1])) + 1.0; }
  else { v0 = Math.max(0, playhead - 2); v1 = v0 + 20; }
  if (v1 - v0 < 6) v1 = v0 + 6;
  const fullA = v0, fullB = v1;
  L.full = { a: fullA, b: fullB };
  if (L.zoom > 1.01) {
    const span = (v1 - v0) / L.zoom, spT = (fullB - fullA) / (L.zoomT || L.zoom);
    if (L.zoomAt != null) L.zoomAt = Math.min(Math.max(L.zoomAt, fullA + span / 2), fullB - span / 2);
    if (L.atT != null) L.atT = Math.min(Math.max(L.atT, fullA + spT / 2), fullB - spT / 2);
    const c = L.zoomAt ?? (S && S.playing ? playhead : v0 + span / 2);
    v0 = Math.min(Math.max(fullA, c - span / 2), fullB - span); v1 = v0 + span;
  }
  const vk = v0.toFixed(4) + ':' + v1.toFixed(4);
  if (L.vk !== vk) { if (L.vk) markMove(); L.vk = vk; }
  const X = (s) => X0 + (s - v0) / (v1 - v0) * XW;
  const step = [1, 2, 5, 10, 15, 30, 60, 120].find((st) => (v1 - v0) / st <= 9) || 300;
  const bars = [];
  for (let s = Math.ceil(v0 / step) * step; s <= v1; s += step) {
    const x = X(s);
    if (x < 268 || x > X1 + 2) continue;
    bars.push({ x, lx: x + 6, label: Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0') });
  }
  const vis = notesIn.filter((n) => n[1] >= v0 && n[0] <= v1);
  const pitches = ((S && S.cap) || []).filter((c) => c[1] >= v0 && c[0] <= v1).map((c) => c[2]);
  const pLo = pitches.length ? Math.min(...pitches) - 2 : 60, pHi = pitches.length ? Math.max(...pitches) + 2 : 84;
  const Y = (p) => 388 - (p - pLo) / Math.max(1, pHi - pLo) * 230;
  const capIn = (S && S.cap) || [];
  const stateAt = (s0) => { for (const p of phrases) if (s0 >= p[0] - 0.05 && s0 <= p[1] + 0.05) return p[2]; return 0; };
  const artAt = (s0, p0) => { let best = null, bd = 1e9; for (const n of notesIn) { const d = Math.abs(n[0] - s0) + (n[2] === p0 ? 0 : 5); if (d < bd) bd = d, best = n; } return best; };
  const sel = L.sel || new Set();
  // grade: compassos e tempos pelo BPM (mais fina com zoom) e faixas das teclas pretas
  const beat = 60 / ((S && S.bpm) || 120), grid = [];
  const sub = (v1 - v0) / beat > 64 ? 4 : (v1 - v0) / beat < 8 ? 0.25 : 1;
  for (let k = Math.ceil(v0 / (beat * sub)); k * beat * sub <= v1 && grid.length < 400; k++) {
    const tt = k * beat * sub, x = X(tt), bar = Math.abs(tt / (beat * 4) - Math.round(tt / (beat * 4))) < 1e-6;
    if (x >= 268 && x <= X1 + 2) grid.push({ x, c: bar ? (dark ? 'rgba(255,255,255,0.13)' : 'rgba(0,0,0,0.12)') : (dark ? 'rgba(255,255,255,0.045)' : 'rgba(0,0,0,0.045)') });
  }
  const rows = [], rowH = 230 / Math.max(1, pHi - pLo);
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
    const an = artAt(c[0], c[2]), forced = c[3] > 0 ? ART_IDS[c[3]] : null, art = forced || (an ? an[3] : 'auto');
    const st = stateAt(c[0]), w = Math.max(X(s1) - X(s0) - 2, 6), vel = capVel(i);
    const live = S && (S.internalPlay || S.playing) && playhead >= c[0] && playhead < c[1];
    return { i, x: X(s0), y: Y(pp) - 2, w, vel, art: AC[art] || AC.auto, op: st === 1 ? 1 : st === 2 ? 0.85 : 0.62, fg: TXT(art),
      name: w > 24 ? NN[((pp % 12) + 12) % 12] + (Math.floor(pp / 12) - 1) : '', cls: live ? 'playing' : '',
      ring: sel.has(i) ? `0 0 0 2px ${dark ? '#FFFFFF' : '#1D1D1F'}` : live ? `0 0 0 1px #fff, 0 0 14px ${AC[art] || AC.auto}` : `0 1px 2px rgba(0,0,0,${dark ? 0.35 : 0.15})`, cursor: 'grab',
      title: `${NN[((pp % 12) + 12) % 12]}${Math.floor(pp / 12) - 1} · velocity ${Math.round(vel)} · ${ART_NAMES[art] || 'Auto'}${forced ? ' (set by you)' : an ? ': ' + an[5] : ''}` };
  }).filter((n) => n.x + n.w >= 262 && n.x <= X1 + 4);
  L.view = { v0, v1, pLo, pHi };
  // faixa de velocity (como no Logic): uma haste por nota, na cor da articulação
  const velStems = notes.map((n) => { const h = Math.max(2, n.vel / 127 * 30); return { i: n.i, x: n.x + 1, top: 446 - h, h, hy: 443 - h, color: n.art, op: sel.has(n.i) ? 1 : 0.72 }; });
  L.velStems = velStems.map((v) => ({ i: v.i, x: v.x }));
  const palette = ART_IDS.map((id, i) => ({ i, x: 280 + i * 70, label: i === 0 ? 'Auto' : ART_NAMES[id], bg: AC[id], fg: TXT(id) }));
  const dragChip = L.chipDrag && L.chipDrag.moved ? { ...palette[L.chipDrag.i], x: L.chipDrag.x, y: L.chipDrag.y } : null;
  L.noteBoxes = notes.map((n) => ({ i: n.i, x: n.x, y: n.y, w: n.w }));
  const STATE = [['Captured', t.secondary, t.fill], ['Rendered', t.ok, t.okFill], ['Rendering', t.warn, t.warnFill], ['Outdated', t.warn, t.warnFill]];
  const focus = L.focus != null && L.focus < phrases.length ? L.focus : (() => { const k = phraseAt(playhead, 0.05); return k >= 0 ? k : phrases.length - 1; })();
  const fadeOv = L.fadeOv || {}, fades = [];
  const regions = phrases.map((p, i) => ({ p, i })).filter(({ p }) => X(p[1]) + 12 >= 268 && X(p[0]) - 12 <= X1 + 4).map(({ p, i }) => {
    const x = Math.max(268, X(p[0]) - 12), w = Math.max(16, Math.min(X1 + 4, X(p[1]) + 12) - x);
    let [label, color, fill] = STATE[p[2]];
    if (p[4]) { label = 'Capturing'; color = t.rec; fill = t.recFill; }
    if (p[2] === 2) label = p[3] > 0 ? `Rendering · ${Math.round(p[3] * 100)}%` : 'Queued';
    if (p[2] === 1) label = 'Rendered ✓';
    // forma de onda do render (picos a cada 50 ms desde a origem da frase)
    let wave = '';
    const peaks = p[6];
    if (p[2] === 1 && Array.isArray(peaks) && peaks.length) {
      const top = [], bot = [];
      for (let k = 0; k < peaks.length; k++) {
        const px = X(p[5] + k * 0.05) - x;
        if (px < 0 || px > w) continue;
        const amp = peaks[k] / 100 * 95;
        top.push(px.toFixed(1) + ',' + (113 - amp).toFixed(1));
        bot.push(px.toFixed(1) + ',' + (113 + amp).toFixed(1));
      }
      if (top.length > 1) wave = 'M' + top.join('L') + 'L' + bot.reverse().join('L') + 'Z';
    }
    // fade in estilo FL: curva sobre o trecho, alça no topo (duração) e alça no meio da curva (formato)
    const fd = L.fadeDrag && L.fadeDrag.i === i ? L.fadeDrag : null, ov = fadeOv[i] || {};
    const sec = fd && fd.sec != null ? fd.sec : ov.sec ?? (p[7] || 0), ten = fd && fd.ten != null ? fd.ten : ov.ten ?? (p[8] ?? 0.5);
    const xs = X(p[0] - 0.06), xe = X(p[0] - 0.06 + sec), ex = Math.pow(2, 2 * ten), yt = 26, yb = 256;
    let fLine = '', fShade = '';
    if (sec > 0.005) {
      const pts = [];
      for (let k = 0; k <= 32; k++) { const u = k / 32; pts.push((xs + (xe - xs) * u - 268).toFixed(1) + ',' + (yb - Math.pow(u, ex) * (yb - yt)).toFixed(1)); }
      fLine = 'M' + pts.join('L');
      fShade = fLine + `L${(xs - 268).toFixed(1)},${yt}Z`;
    }
    if (!p[4] && xe + 6 >= 268) fades.push({ i, line: fLine, shade: fShade, hx: Math.max(268, sec > 0.005 ? xe : xs + 8), showT: sec > 0.02 && xe - xs > 18,
      tx: (xs + xe) / 2, ty: 140 + yb - Math.pow(0.5, ex) * (yb - yt), title: sec > 0.005 ? `Fade in ${Math.round(sec * 1000)} ms · drag to change · double-click to remove` : 'Drag right to add a fade in' });
    const playingThis = S && S.audition === i;
    return { i, x, w, lx: x + 12, label, color, fill, busy: p[2] === 2 && p[3] > 0, barW: Math.max(20, w - 24), progW: Math.max(2, (w - 24) * p[3]),
      ring: i === focus ? `inset 0 0 0 1.5px ${dark ? 'rgba(10,132,255,0.55)' : 'rgba(0,122,255,0.45)'}` : 'none',
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
    takeBar = { title: `Take ${focus + 1}/${phrases.length}`, st, stColor, rendered, i: focus,
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
    up: [{ label: '⇈', title: 'Up an octave', pick: mvSend(0, 12) }, { label: '▲', title: 'Up a semitone', pick: mvSend(0, 1) }],
    down: [{ label: '▼', title: 'Down a semitone', pick: mvSend(0, -1) }, { label: '⇊', title: 'Down an octave', pick: mvSend(0, -12) }],
    side: [{ label: '◀', title: 'Earlier by 1/16', pick: mvSend(-beat / 4, 0) }, { label: '▶', title: 'Later by 1/16', pick: mvSend(beat / 4, 0) }] };
  // dinâmica: o traço aparece na curva enquanto é desenhado
  const stroke = L.dynPts && L.dynPts.length > 1 ? L.dynPts : L.dynHold;
  let dynSrc = dynIn;
  if (stroke && stroke.length > 1) {
    const sp = [...stroke].sort((a, b) => a[0] - b[0]), a = sp[0][0], b = sp[sp.length - 1][0];
    dynSrc = dynIn.filter((d) => d[0] < a || d[0] > b).concat(sp).sort((p, q) => p[0] - q[0]);
  }
  const dpts = dynSrc.filter((d) => d[0] >= v0 && d[0] <= v1).map((d) => [X(d[0]) - 268, 62 - (d[1] - 20) / 104 * 58]);
  const dynLine = dpts.map((p) => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const dynArea = dpts.length ? `${dpts[0][0].toFixed(1)},64 ${dynLine} ${dpts[dpts.length - 1][0].toFixed(1)},64` : '';
  const lane = vis.map((n) => ({ id: n[3], start: n[0], end: n[1], why: n[5] }));
  lane.sort((p, q) => p.start - q.start);
  const laneOut = [];
  for (let k = 0; k < lane.length; k++) {
    const c = lane[k];
    const x = Math.max(268, X(c.start));
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

