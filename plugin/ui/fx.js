// Aba Effects: fileira de módulos (estilo RC-20) e o editor do módulo escolhido, desenhado num
// "palco" genérico (retângulos, caminhos, textos, nós, knobs, botões, menu) que o template mostra.
'use strict';

const FX = {
  W: 766, H: 420,
  EQ_COLORS: ['#43C463', '#B455E0', '#3D8BFD', '#F2C744', '#F24E4E'],
  EQ_TYPES: ['Low Cut', 'Low Shelf', 'Bell', 'High Shelf', 'High Cut'],
  SAT_TYPES: ['Analog Clip', 'Soft Sine', 'Bass Shaper', 'Medium Curve', 'Hard Curve', 'Sinoid Fold', 'Digital Clip', 'Waveshaper'],
  DIVS: ['1/64', '1/32', '1/16T', '1/16', '1/16D', '1/8T', '1/8', '1/8D', '1/4T', '1/4', '1/4D', '1/2', '1/1'],
  DIV_BEATS: [1 / 16, 1 / 8, 1 / 6, 1 / 4, 3 / 8, 1 / 3, 1 / 2, 3 / 4, 2 / 3, 1, 1.5, 2, 4],
  REV_MODES: ['Concert Hall', 'Bright Hall', 'Plate', 'Room', 'Chamber', 'Random Space', 'Chorus Space', 'Ambience', 'Cathedral'],
  REV_DESC: ['Concert Hall: big, dense hall with chorused modulation and a dark tone',
    'Bright Hall: open hall with extra air and shimmer on top', 'Plate: instant, dense and smooth, no room behind it',
    'Room: small wooden room, strong early reflections', 'Chamber: warm echo chamber, medium size',
    'Random Space: hall with randomized delays, never repeats the same way', 'Chorus Space: lush hall with deep modulation',
    'Ambience: short space that adds body without a tail', 'Cathedral: huge stone space, long and dark'],
  REV_COLORS: ['1970s', '1980s', 'Now'],
  COLOR_DESC: ['1970s: warm and dark, deep wobbly modulation, heavier lows', '1980s: brighter digital sheen, dense early diffusion', 'Now: full bandwidth and air, clean subtle modulation, tight lows']
};

// ------------------------------------------------------------------ geometria
function polar(cx, cy, r, deg) { const a = deg * Math.PI / 180; return [cx + r * Math.sin(a), cy - r * Math.cos(a)]; }
function arc(cx, cy, r, a0, a1) {
  if (Math.abs(a1 - a0) < 0.01) return '';
  const [x0, y0] = polar(cx, cy, r, a0), [x1, y1] = polar(cx, cy, r, a1);
  const large = Math.abs(a1 - a0) > 180 ? 1 : 0, sweep = a1 > a0 ? 1 : 0;
  return `M${x0.toFixed(1)},${y0.toFixed(1)}A${r},${r} 0 ${large} ${sweep} ${x1.toFixed(1)},${y1.toFixed(1)}`;
}
// curvas de saturação (as mesmas do MixFx.cpp)
function satCurve(type, u) {
  switch (type) {
    case 0: return Math.tanh(u);
    case 1: return Math.sin(Math.max(-Math.PI / 2, Math.min(Math.PI / 2, u)));
    case 2: return u > 0 ? u / (1 + u) : u / (1 - 0.6 * u);
    case 3: return 2 / Math.PI * Math.atan(u);
    case 4: { const c = Math.max(-1, Math.min(1, u)); return 1.5 * c - 0.5 * c * c * c; }
    case 5: return Math.sin(u);
    case 6: return Math.max(-1, Math.min(1, u));
    default: { const k = 2.5; return (1 + k) * u / (1 + k * Math.abs(u)); }
  }
}
// resposta de um biquad RBJ em dB (igual ao Biquad::set do C++)
function bandDb(type, f0, g, q, f, sr = 48000) {
  const kinds = ['hp', 'ls', 'pk', 'hs', 'lp'];
  const k = kinds[type], A = Math.pow(10, g / 40), w = 2 * Math.PI * Math.min(f0, sr * 0.45) / sr, cw = Math.cos(w), sw = Math.sin(w), al = sw / (2 * Math.max(q, 0.05));
  let b0, b1, b2, a0, a1, a2;
  if (k === 'pk') { b0 = 1 + al * A; b1 = -2 * cw; b2 = 1 - al * A; a0 = 1 + al / A; a1 = -2 * cw; a2 = 1 - al / A; }
  else if (k === 'hp') { b0 = (1 + cw) / 2; b1 = -(1 + cw); b2 = (1 + cw) / 2; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; }
  else if (k === 'lp') { b0 = (1 - cw) / 2; b1 = 1 - cw; b2 = (1 - cw) / 2; a0 = 1 + al; a1 = -2 * cw; a2 = 1 - al; }
  else {
    const s = 2 * Math.sqrt(A) * al;
    if (k === 'hs') { b0 = A * ((A + 1) + (A - 1) * cw + s); b1 = -2 * A * ((A - 1) + (A + 1) * cw); b2 = A * ((A + 1) + (A - 1) * cw - s); a0 = (A + 1) - (A - 1) * cw + s; a1 = 2 * ((A - 1) - (A + 1) * cw); a2 = (A + 1) - (A - 1) * cw - s; }
    else { b0 = A * ((A + 1) - (A - 1) * cw + s); b1 = 2 * A * ((A - 1) - (A + 1) * cw); b2 = A * ((A + 1) - (A - 1) * cw - s); a0 = (A + 1) + (A - 1) * cw + s; a1 = -2 * ((A - 1) + (A + 1) * cw); a2 = (A + 1) + (A - 1) * cw - s; }
  }
  const ww = 2 * Math.PI * f / sr, c1 = Math.cos(ww), s1 = Math.sin(ww), c2 = Math.cos(2 * ww), s2 = Math.sin(2 * ww);
  const nr = b0 + b1 * c1 + b2 * c2, ni = -(b1 * s1 + b2 * s2), dr = a0 + a1 * c1 + a2 * c2, di = -(a1 * s1 + a2 * s2);
  let db = 10 * Math.log10((nr * nr + ni * ni) / (dr * dr + di * di));
  if (type === 0 || type === 4) db *= 2;  // cortes: duas seções (24 dB/oitava)
  return db;
}

// ------------------------------------------------------------------ peças do palco
function knob(sc, id, label, x, y, size, color, opts = {}) {
  const p = P(id), n = p.n, a = -135 + 270 * n, bip = !!opts.bipolar;
  sc.knobs.push({
    id, label, x, y, size, title: label, value: opts.value ?? p.text,
    track: arc(50, 50, 42, -135, 135), arc: bip ? arc(50, 50, 42, Math.min(0, a), Math.max(0, a)) : arc(50, 50, 42, -135, Math.max(-134.9, a)),
    px: polar(50, 50, 26, a)[0].toFixed(1), py: polar(50, 50, 26, a)[1].toFixed(1),
    opacity: opts.hidden ? 0 : 1,
    color, trackColor: opts.trackColor || 'rgba(255,255,255,0.10)', face: opts.face || 'rgba(255,255,255,0.06)', rim: opts.rim || 'rgba(255,255,255,0.10)',
    pointer: opts.pointer || '#FFFFFF', labelColor: opts.labelColor || 'rgba(255,255,255,0.7)', valueColor: opts.valueColor || '#FFFFFF'
  });
}
function button(sc, label, x, y, w, h, pick, o = {}) {
  sc.buttons.push({ label, x, y, w, h, pick, bg: o.bg || 'rgba(255,255,255,0.08)', fg: o.fg || '#FFFFFF', border: o.border || '0', r: o.r ?? 7,
    fs: o.fs || 12, fw: o.fw || 600, align: o.align || 'center', pad: o.pad ?? 8 });
}
function seg(sc, items, active, x, y, w, h, color, pick) {
  const bw = w / items.length;
  items.forEach((it, i) => button(sc, it, x + i * bw, y, bw - 3, h, () => pick(i),
    { bg: i === active ? color : 'rgba(255,255,255,0.07)', fg: i === active ? '#111' : 'rgba(255,255,255,0.85)', fs: 11 }));
}
function menuButton(sc, label, x, y, w, items, active, pick, o = {}) {
  button(sc, label + '  ▾', x, y, w, 26, () => { const mh = items.length * 29 + 8, my = y + 28 + mh > FX.H - 6 ? Math.max(6, y - mh - 2) : y + 28; L.menu = { x, y: my, w, items: items.map((t, i) => ({ label: t, check: i === active ? '✓ ' : '', pick: () => { L.menu = null; pick(i); } })) }; dirty = true; },
    { align: 'left', bg: o.bg || 'rgba(255,255,255,0.08)', fg: o.fg || '#FFFFFF', fs: 13 });
}
const T = (sc, t, x, y, c, s = 11, w = 600, a = 'start', ls = 0) => sc.texts.push({ t, x, y, c, s, w, a, ls });
const R = (sc, x, y, w, h, fill, stroke = 'none', sw = 0, rx = 10) => sc.rects.push({ x, y, w, h, fill, stroke, sw, rx });
const Pth = (sc, d, stroke, w = 2, fill = 'none', o = 1) => sc.paths.push({ d, stroke, w, fill, o });

// ------------------------------------------------------------------ módulos
const EQX = (f) => 20 + Math.log10(f / 20) / 3 * 726, EQY = (g) => 158 - g / 18 * 128;  // gráfico 30..286
function eqResponse(f) {
  let db = 0;
  for (let b = 1; b <= 5; b++) {
    if (P('eq' + b + 'On').v < 0.5) continue;
    db += bandDb(Math.round(P('eq' + b + 'Type').v), P('eq' + b + 'Freq').v, P('eq' + b + 'Gain').v, P('eq' + b + 'Q').v, f);
  }
  return db;
}
function sceneEq(sc) {
  sc.bg = 'linear-gradient(#1a1922, #121118)';
  for (const f of [50, 100, 200, 500, 1000, 2000, 5000, 10000]) {
    Pth(sc, `M${EQX(f)},26V292`, 'rgba(255,255,255,0.07)', 1);
    T(sc, f >= 1000 ? f / 1000 + 'k' : String(f), EQX(f), 306, 'rgba(255,255,255,0.35)', 10, 500, 'middle');
  }
  for (const g of [-12, -6, 0, 6, 12]) {
    Pth(sc, `M20,${EQY(g)}H746`, g === 0 ? 'rgba(255,255,255,0.14)' : 'rgba(255,255,255,0.06)', 1);
    T(sc, (g > 0 ? '+' : '') + g, 740, EQY(g) - 4, '#F5B83D', 10, 600, 'end');
  }
  const pts = [];
  for (let k = 0; k <= 240; k++) { const f = 20 * Math.pow(1000, k / 240); pts.push([EQX(f), EQY(Math.max(-24, Math.min(24, eqResponse(f))))]); }
  const line = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('');
  Pth(sc, line + `L746,${EQY(0)}L20,${EQY(0)}Z`, 'none', 0, 'rgba(245,184,61,0.10)');
  const sel = L.eqBand || 3;
  // curva da banda escolhida, na cor dela
  {
    const ty = Math.round(P('eq' + sel + 'Type').v), f0 = P('eq' + sel + 'Freq').v, g0 = P('eq' + sel + 'Gain').v, q0 = P('eq' + sel + 'Q').v;
    const bp = [];
    for (let k = 0; k <= 160; k++) { const f = 20 * Math.pow(1000, k / 160); bp.push(EQX(f).toFixed(1) + ',' + EQY(Math.max(-24, Math.min(24, bandDb(ty, f0, g0, q0, f)))).toFixed(1)); }
    Pth(sc, 'M' + bp.join('L'), FX.EQ_COLORS[sel - 1], 1.5, 'none', 0.7);
  }
  Pth(sc, line, '#F5B83D', 2.5);
  for (let b = 1; b <= 5; b++) {
    const on = P('eq' + b + 'On').v > 0.5, ty = Math.round(P('eq' + b + 'Type').v);
    const x = EQX(P('eq' + b + 'Freq').v), y = ty === 0 || ty === 4 ? EQY(0) : EQY(P('eq' + b + 'Gain').v);
    sc.nodes.push({ i: b, x: x.toFixed(1), y: y.toFixed(1), r: b === sel ? 9 : 7, fill: on ? FX.EQ_COLORS[b - 1] : '#3a3a40', stroke: b === sel ? '#FFFFFF' : 'rgba(0,0,0,0.4)' });
  }
  // painel da banda (como o do Pro-Q)
  R(sc, 150, 322, 466, 88, 'rgba(40,38,50,0.92)', 'rgba(255,255,255,0.10)', 1, 14);
  const col = FX.EQ_COLORS[sel - 1], pre = 'eq' + sel, on = P(pre + 'On').v > 0.5;
  button(sc, '⏻', 164, 351, 30, 30, () => setV(pre + 'On', on ? 0 : 1), { bg: on ? col : 'rgba(255,255,255,0.08)', fg: on ? '#111' : '#fff', r: 15, fs: 14 });
  menuButton(sc, FX.EQ_TYPES[Math.round(P(pre + 'Type').v)], 204, 353, 120, FX.EQ_TYPES, Math.round(P(pre + 'Type').v), (i) => setV(pre + 'Type', i));
  knob(sc, pre + 'Freq', 'FREQ', 344, 330, 40, col);
  knob(sc, pre + 'Gain', 'GAIN', 412, 330, 40, col, { bipolar: true });
  knob(sc, pre + 'Q', 'Q', 480, 330, 40, col);
  for (let b = 1; b <= 5; b++) button(sc, '', 534 + (b - 1) * 15, 368, 12, 12, () => { L.eqBand = b; dirty = true; }, { bg: FX.EQ_COLORS[b - 1], r: 7, pad: 0, border: b === sel ? '2px solid #fff' : '0' });
  T(sc, 'BAND ' + sel, 534, 358, 'rgba(255,255,255,0.5)', 9, 700, 'start', 0.5);
  T(sc, 'Drag a node: frequency and gain · scroll on it: Q · double-click a knob: reset', 20, 16, 'rgba(255,255,255,0.35)', 10, 500);
}

function sceneComp(sc) {
  sc.bg = 'linear-gradient(#251416, #170d0f)';
  const red = '#FF5A4E', gx = 30, gy = 40, gs = 300;
  R(sc, gx, gy, gs, gs, 'rgba(0,0,0,0.25)', 'rgba(255,255,255,0.08)', 1, 8);
  const X = (db) => gx + (db + 60) / 60 * gs, Y = (db) => gy + gs - (db + 60) / 60 * gs;
  for (const d of [-48, -36, -24, -12]) { Pth(sc, `M${X(d)},${gy}V${gy + gs}`, 'rgba(255,255,255,0.05)', 1); Pth(sc, `M${gx},${Y(d)}H${gx + gs}`, 'rgba(255,255,255,0.05)', 1); }
  Pth(sc, `M${X(-60)},${Y(-60)}L${X(0)},${Y(0)}`, 'rgba(255,255,255,0.12)', 1);
  const th = P('compThresh').v, ra = P('compRatio').v, mk = P('compMakeup').v;
  const out = (i) => (i < th ? i : th + (i - th) / ra) + mk;
  const pts = [];
  for (let i = -60; i <= 0; i += 1) pts.push(X(i).toFixed(1) + ',' + Y(Math.max(-60, Math.min(0, out(i)))).toFixed(1));
  Pth(sc, 'M' + pts.join('L'), red, 2.5);
  sc.nodes.push({ i: 0, x: X(th).toFixed(1), y: Y(Math.min(0, out(th))).toFixed(1), r: 6, fill: red, stroke: '#fff' });
  T(sc, 'INPUT', gx + gs / 2, gy + gs + 18, 'rgba(255,255,255,0.4)', 10, 700, 'middle', 1);
  // medidor de redução de ganho
  const gr = Math.min(0, (S && S.gr) || 0);
  R(sc, 360, gy, 14, gs, 'rgba(255,255,255,0.06)', 'none', 0, 7);
  R(sc, 360, gy, 14, Math.min(gs, -gr / 24 * gs), red, 'none', 0, 7);
  T(sc, 'GR', 367, gy + gs + 18, 'rgba(255,255,255,0.4)', 10, 700, 'middle', 1);
  T(sc, gr.toFixed(1) + ' dB', 367, gy - 8, '#fff', 11, 600, 'middle');
  const ko = { labelColor: 'rgba(255,190,180,0.8)' };
  knob(sc, 'compThresh', 'THRESHOLD', 420, 50, 74, red, ko);
  knob(sc, 'compRatio', 'RATIO', 530, 50, 74, red, ko);
  knob(sc, 'compMakeup', 'MAKEUP', 640, 50, 74, red, ko);
  knob(sc, 'compAttack', 'ATTACK', 470, 210, 74, red, ko);
  knob(sc, 'compRelease', 'RELEASE', 590, 210, 74, red, ko);
}

function sceneSat(sc) {
  sc.bg = 'linear-gradient(#142224, #0d1618)';
  const teal = '#2FD3D3', bx = 30, by = 60, bw = 330, bh = 270, type = Math.round(P('satType').v);
  menuButton(sc, FX.SAT_TYPES[type], bx, 20, 200, FX.SAT_TYPES, type, (i) => setV('satType', i), { bg: 'rgba(47,211,211,0.18)' });
  R(sc, bx, by, bw, bh, 'rgba(0,0,0,0.3)', 'rgba(47,211,211,0.25)', 1, 6);
  Pth(sc, `M${bx + bw / 2},${by}V${by + bh}M${bx},${by + bh / 2}H${bx + bw}`, 'rgba(255,255,255,0.08)', 1);
  Pth(sc, `M${bx},${by + bh}L${bx + bw},${by}`, 'rgba(255,255,255,0.08)', 1);
  const drive = Math.pow(10, P('satDrive').v / 20), outG = Math.pow(10, P('satOutput').v / 20), mix = P('satMix').v / 100;
  const pts = [];
  for (let k = 0; k <= 200; k++) {
    const x = -1 + 2 * k / 200, y = (1 - mix) * x + mix * satCurve(type, x * drive) * outG;
    pts.push((bx + (x + 1) / 2 * bw).toFixed(1) + ',' + (by + bh / 2 - Math.max(-1.1, Math.min(1.1, y)) * bh / 2 * 0.9).toFixed(1));
  }
  Pth(sc, 'M' + pts.join('L'), teal, 2.5);
  const ko = { labelColor: 'rgba(160,240,240,0.85)', face: 'rgba(47,211,211,0.06)' };
  knob(sc, 'satDrive', 'DRIVE', 420, 110, 80, teal, ko);
  knob(sc, 'satOutput', 'OUTPUT', 530, 110, 80, teal, ko);
  knob(sc, 'satMix', 'DRY/WET', 640, 110, 80, teal, ko);
  T(sc, 'Drive pushes the violin into the curve;', 420, 290, 'rgba(255,255,255,0.4)', 11, 500);
  T(sc, 'Output brings the level back.', 420, 306, 'rgba(255,255,255,0.4)', 11, 500);
}

function sceneChorus(sc) {
  sc.bg = 'linear-gradient(#122329, #0b171b)';
  const c = '#5AC8FA', bx = 30, by = 50, bw = 360, bh = 260;
  R(sc, bx, by, bw, bh, 'rgba(0,0,0,0.25)', 'rgba(90,200,250,0.2)', 1, 8);
  const rate = P('chorusRate').v, depth = P('chorusDepth').v / 100;
  for (const [ph, col] of [[0, c], [0.25, '#BF5AF2']]) {
    const pts = [];
    for (let k = 0; k <= 200; k++) { const t = k / 200 * 2; pts.push((bx + k / 200 * bw).toFixed(1) + ',' + (by + bh / 2 - Math.sin(2 * Math.PI * (t * rate + ph)) * depth * bh * 0.4).toFixed(1)); }
    Pth(sc, 'M' + pts.join('L'), col, 2.2);
  }
  T(sc, 'L', bx + 10, by + 20, c, 11, 700); T(sc, 'R', bx + 26, by + 20, '#BF5AF2', 11, 700);
  knob(sc, 'chorusRate', 'RATE', 440, 110, 80, c);
  knob(sc, 'chorusDepth', 'DEPTH', 550, 110, 80, c);
  knob(sc, 'chorusMix', 'MIX', 660, 110, 80, c);
}

function sceneStereo(sc) {
  sc.bg = 'linear-gradient(#1c1833, #110f22)';
  const c = '#9D8CFF', cx = 220, cy = 210, w = P('stereoWidth').v / 100;
  for (const r of [60, 120, 170]) Pth(sc, arc(cx, cy, r, -90, 90), 'rgba(255,255,255,0.07)', 1);
  Pth(sc, `M${cx},${cy - 180}V${cy + 10}`, 'rgba(255,255,255,0.1)', 1);
  T(sc, 'L', cx - 175, cy + 18, 'rgba(255,255,255,0.4)', 11, 700); T(sc, 'R', cx + 168, cy + 18, 'rgba(255,255,255,0.4)', 11, 700);
  // nuvem do campo estéreo: mais aberta com mais largura
  const spread = 8 + w * 150;
  Pth(sc, `M${cx},${cy}C${cx - spread},${cy - 60} ${cx - spread * 0.6},${cy - 160} ${cx},${cy - 170}C${cx + spread * 0.6},${cy - 160} ${cx + spread},${cy - 60} ${cx},${cy}Z`, c, 2, 'rgba(157,140,255,0.18)');
  knob(sc, 'stereoWidth', 'WIDTH', 470, 90, 130, c);
  T(sc, 'Phase-based widening: the mono sum', 430, 300, 'rgba(255,255,255,0.4)', 11, 500);
  T(sc, 'stays exactly the original violin.', 430, 316, 'rgba(255,255,255,0.4)', 11, 500);
}

function sceneDelay(sc) {
  sc.bg = 'linear-gradient(#211a12, #15110b)';
  const o = '#F5A14A', sync = P('delaySync').v > 0.5, bpm = (S && S.bpm) || 120;
  const msOf = (side) => sync ? FX.DIV_BEATS[Math.round(P('delay' + side + 'Div').v)] * 60000 / bpm : P('delay' + side + 'Ms').v;
  const lMs = msOf('Left'), rMs = msOf('Right'), fb = P('delayFeedback').v / 100;
  // ecos: semicírculos que se abrem a cada repetição (esquerda e direita), como no Echo
  const cx = 383, cy = 330;
  for (const [ms, sideA, sideB] of [[lMs, -90, 0], [rMs, 0, 90]]) {
    const step = Math.max(6, Math.min(60, ms / 12));
    for (let k = 1; k <= 12; k++) {
      const r = 16 + k * step, op = Math.pow(Math.max(fb, 0.05), k - 1);
      if (r > 300 || op < 0.03) break;
      Pth(sc, arc(cx, cy, r, sideA, sideB), o, 2, 'none', op);
    }
  }
  Pth(sc, `M${cx},${cy}V30`, 'rgba(255,255,255,0.12)', 1);
  const ko = { labelColor: 'rgba(255,210,160,0.85)' };
  // Left / Right
  knob(sc, sync ? 'delayLeftDiv' : 'delayLeftMs', 'LEFT', 24, 20, 62, o, { ...ko, value: sync ? FX.DIVS[Math.round(P('delayLeftDiv').v)] : P('delayLeftMs').text });
  knob(sc, sync ? 'delayRightDiv' : 'delayRightMs', 'RIGHT', 108, 20, 62, o, { ...ko, value: sync ? FX.DIVS[Math.round(P('delayRightDiv').v)] : P('delayRightMs').text });
  button(sc, sync ? 'Sync' : 'Time', 24, 122, 146, 24, () => setV('delaySync', sync ? 0 : 1), { bg: sync ? o : 'rgba(255,255,255,0.08)', fg: sync ? '#111' : '#fff' });
  T(sc, 'MODE', 24, 172, 'rgba(255,210,160,0.7)', 10, 700, 'start', 1);
  seg(sc, ['Stereo', 'Ping Pong', 'Mid/Side'], Math.round(P('delayMode').v), 24, 180, 210, 24, o, (i) => setV('delayMode', i));
  T(sc, 'CHARACTER', 24, 228, 'rgba(255,210,160,0.7)', 10, 700, 'start', 1);
  seg(sc, ['Digital', 'Tape', 'Analog'], Math.round(P('delayChar').v), 24, 236, 210, 24, o, (i) => setV('delayChar', i));
  T(sc, 'PRESETS', 24, 284, 'rgba(255,210,160,0.7)', 10, 700, 'start', 1);
  const preset = (vals) => () => { for (const [id, v] of Object.entries(vals)) setV(id, v); };
  button(sc, 'Slapback', 24, 292, 72, 24, preset({ delaySync: 0, delayLeftMs: 110, delayRightMs: 120, delayFeedback: 5, delayMode: 0, delayChar: 1, delayMix: 22 }), { fs: 11 });
  button(sc, 'Dotted 1/8', 100, 292, 74, 24, preset({ delaySync: 1, delayLeftDiv: 7, delayRightDiv: 7, delayFeedback: 35, delayMode: 1, delayMix: 16 }), { fs: 11 });
  button(sc, 'Tape echo', 24, 320, 72, 24, preset({ delaySync: 1, delayLeftDiv: 9, delayRightDiv: 9, delayFeedback: 45, delayMode: 0, delayChar: 1, delayMod: 45, delayMix: 18 }), { fs: 11 });
  button(sc, 'Wide 1/4', 100, 320, 74, 24, preset({ delaySync: 1, delayLeftDiv: 9, delayRightDiv: 7, delayFeedback: 30, delayMode: 0, delayChar: 0, delayMix: 14 }), { fs: 11 });
  // lado direito
  knob(sc, 'delayFeedback', 'FEEDBACK', 610, 20, 62, o, ko);
  knob(sc, 'delayMod', 'MOD', 690, 20, 62, o, ko);
  knob(sc, 'delayHp', 'FILTER HP', 610, 130, 62, o, ko);
  knob(sc, 'delayLp', 'FILTER LP', 690, 130, 62, o, ko);
  knob(sc, 'delayMix', 'DRY/WET', 650, 250, 70, o, ko);
}

// paleta do Reverb pela Color: 1970s quente, 1980s neon, Now grafite limpo
const REV_THEMES = [
  { bg: 'linear-gradient(#13291f, #0a1812)', y: '#E3C15A', o: '#8CC084', r: '#3FA796', text: '#EFE6C4', face: '#06110c', tile: '#11261c' },
  { bg: 'linear-gradient(#1f1040, #0c0720)', y: '#3DE3FF', o: '#FF4FD8', r: '#8A5CFF', text: '#E6DCFF', face: '#0a0618', tile: '#1c0f3a' },
  { bg: 'linear-gradient(#22272d, #14171b)', y: '#E8EEF4', o: '#6FB7FF', r: '#4C8DFF', text: '#DCE6F0', face: '#0e1114', tile: '#1d2228' }
];
function revTheme() { return REV_THEMES[Math.max(0, Math.min(2, Math.round(P('revColor').v)))]; }

// Reverb no estilo ChromaVerb: em cima o gráfico do Damping EQ (quanto cada frequência dura, em % do
// Time) com nós arrastáveis e a "nuvem" do ambiente; embaixo o painel claro com os controles.
const RV = { OR: '#F2683C', GX0: 20, GX1: 746, GY0: 52, GY1: 232, MAX: 2.5 };
const RVX = (f) => RV.GX0 + Math.log10(f / 20) / 3 * (RV.GX1 - RV.GX0);
const RVY = (m) => RV.GY1 - Math.max(0, Math.min(RV.MAX, m)) / RV.MAX * (RV.GY1 - RV.GY0);
function revMult(f) {  // o mesmo desenho do C++: grave × BassMult abaixo do BassFreq, agudo cai no HighShelf acima do HighFreq
  const bm = P('revBassMult').v, bf = P('revBassFreq').v, hf = P('revHighFreq').v, g = Math.pow(10, P('revHighShelf').v / 20);
  const lc = P('revLowCut').v, hc = P('revHighCut').v;
  const s = 1 / (1 + Math.pow(bf / f, 2)), bass = bm + (1 - bm) * s;
  const hi = 1 - (1 - g) / (1 + Math.pow(hf / f, 2));
  const cut = (Math.pow(f / lc, 2) / (1 + Math.pow(f / lc, 2))) / (1 + Math.pow(f / hc, 4));
  return bass * hi * cut;
}
function sceneReverb(sc) {
  const OR = RV.OR, tab = L.revTab || 'main', mode = Math.round(P('revMode').v), dec = P('revDecay').v, m = (S && S.meters) || [0, 0];
  sc.bg = 'linear-gradient(#222226, #141416 60%)';
  // cabeçalho: Damping EQ · modo (como a caixa vermelha do ChromaVerb) · MAIN / DETAILS
  T(sc, 'DAMPING EQ', 20, 27, 'rgba(255,255,255,0.45)', 10, 700, 'start', 1);
  button(sc, '‹', 290, 10, 24, 26, () => setV('revMode', (mode + 8) % 9), { bg: 'transparent', fg: 'rgba(255,255,255,0.6)', fs: 17 });
  button(sc, FX.REV_MODES[mode], 316, 10, 134, 26, () => { L.menu = { x: 316, y: 40, w: 150, items: FX.REV_MODES.map((t, i) => ({ label: t, check: i === mode ? '✓ ' : '', pick: () => { L.menu = null; setV('revMode', i); } })) }; dirty = true; },
    { bg: 'rgba(242,104,60,0.16)', fg: OR, fs: 13, border: '1px solid rgba(242,104,60,0.35)' });
  button(sc, '›', 452, 10, 24, 26, () => setV('revMode', (mode + 1) % 9), { bg: 'transparent', fg: 'rgba(255,255,255,0.6)', fs: 17 });
  for (const [id, label, x, w] of [['main', 'MAIN', 640, 50], ['details', 'DETAILS', 692, 56]])
    button(sc, label, x, 12, w, 22, () => { L.revTab = id; dirty = true; }, { bg: tab === id ? 'rgba(255,255,255,0.14)' : 'transparent', fg: tab === id ? '#FFFFFF' : 'rgba(255,255,255,0.45)', fs: 10, fw: 700, r: 5 });
  // grade: frequência (log) x duração relativa; à direita o tempo real de cada linha
  for (const f of [50, 100, 200, 500, 1000, 2000, 5000, 10000]) {
    Pth(sc, `M${RVX(f).toFixed(1)},${RV.GY0}V${RV.GY1}`, 'rgba(255,255,255,0.06)', 1);
    T(sc, f >= 1000 ? f / 1000 + 'k' : String(f), RVX(f), 248, 'rgba(255,255,255,0.32)', 9, 500, 'middle');
  }
  for (const m of [0.5, 1, 1.5, 2]) {
    Pth(sc, `M${RV.GX0},${RVY(m).toFixed(1)}H${RV.GX1}`, m === 1 ? 'rgba(255,255,255,0.13)' : 'rgba(255,255,255,0.05)', 1);
    T(sc, Math.round(m * 100) + '%', RV.GX0 + 4, RVY(m) - 4, 'rgba(255,255,255,0.3)', 9, 500);
    T(sc, (m * dec).toFixed(1) + ' s', RV.GX1 - 4, RVY(m) - 4, 'rgba(255,255,255,0.3)', 9, 500, 'end');
  }
  sc.canvas = true;  // nuvem animada (rvLoop), embaixo da curva
  // curva do Damping EQ e os nós (arraste: frequência e quanto dura)
  const pts = [];
  for (let k = 0; k <= 200; k++) { const f = 20 * Math.pow(1000, k / 200); pts.push(RVX(f).toFixed(1) + ',' + RVY(revMult(f)).toFixed(1)); }
  Pth(sc, 'M' + pts.join('L') + `L${RV.GX1},${RV.GY1}L${RV.GX0},${RV.GY1}Z`, 'none', 0, 'rgba(242,104,60,0.07)');
  Pth(sc, 'M' + pts.join('L'), OR, 2.5);
  const node = (i, f, mm) => sc.nodes.push({ i, x: RVX(f).toFixed(1), y: RVY(mm).toFixed(1), r: 6, fill: '#2a2a2e', stroke: OR });
  node('rlc', P('revLowCut').v, revMult(P('revLowCut').v * 1.0001));
  node('rbass', P('revBassFreq').v, P('revBassMult').v);
  node('rdamp', P('revHighFreq').v, Math.pow(10, P('revHighShelf').v / 20));
  node('rhc', P('revHighCut').v, revMult(P('revHighCut').v));
  if (P('revFreeze').v > 0.5) T(sc, '❄ FROZEN', 383, 140, 'rgba(255,255,255,0.75)', 13, 700, 'middle', 2);
  // painel claro de baixo
  R(sc, 0, 258, FX.W, FX.H - 258, '#E6E6E9', 'none', 0, 0);
  Pth(sc, `M0,258.5H${FX.W}`, 'rgba(0,0,0,0.12)', 1);
  const ko = { face: '#FFFFFF', rim: 'rgba(0,0,0,0.14)', trackColor: 'rgba(0,0,0,0.10)', pointer: '#3A3A3C', labelColor: '#5A5A60', valueColor: OR };
  const kn = (id, label, x, y, size = 40, o = {}) => knob(sc, id, label, x, y, size, OR, { ...ko, ...o });
  const sep = (x) => Pth(sc, `M${x},270V408`, 'rgba(0,0,0,0.10)', 1);
  if (tab === 'main') {
    kn('revAttack', 'Attack', 24, 266); kn('revSize', 'Size', 92, 266); kn('revEarly', 'Diffusion', 160, 266);
    kn('predelay', 'Pre-Delay', 24, 342); kn('revLate', 'Late', 92, 342); kn('revModDepth', 'Modulation', 160, 342);
    sep(226);
    kn('revDecay', 'Time', 250, 268, 76);
    const fz = P('revFreeze').v > 0.5;
    button(sc, '❄ Freeze', 250, 380, 76, 24, () => setV('revFreeze', fz ? 0 : 1), { bg: fz ? OR : '#FFFFFF', fg: fz ? '#FFFFFF' : '#3A3A3C', r: 12, fs: 11, border: '1px solid rgba(0,0,0,0.12)' });
    sep(348);
    kn('revHighFreq', 'Damping', 372, 266); kn('revDucking', 'Ducking', 372, 342);
    sep(440);
    T(sc, 'WET', 476, 276, '#5A5A60', 10, 700, 'middle', 0.4);
    sc.vsliders.push({ id: 'reverbMix', x: 472, y: 286, w: 8, h: 100, r: 4, track: 'rgba(0,0,0,0.12)', fill: OR, pct: P('reverbMix').n * 100, tw: 22, tw2: 11 });
    T(sc, P('reverbMix').text, 476, 404, OR, 11, 600, 'middle');
    const dbp = (v) => Math.max(0, Math.min(1, (20 * Math.log10(Math.max(v, 1e-6)) + 60) / 60));
    T(sc, 'OUT', 530, 276, '#5A5A60', 10, 700, 'middle', 0.4);
    for (const [k, x] of [[0, 523], [1, 532]]) { R(sc, x, 286, 5, 100, 'rgba(0,0,0,0.10)', 'none', 0, 2); R(sc, x, 286 + 100 * (1 - dbp(m[k])), 5, 100 * dbp(m[k]), OR, 'none', 0, 2); }
    sep(566);
    const col = Math.round(P('revColor').v);
    T(sc, 'COLOR', 656, 276, '#5A5A60', 10, 700, 'middle', 0.4);
    button(sc, '‹', 590, 286, 22, 26, () => setV('revColor', (col + 2) % 3), { bg: 'transparent', fg: '#3A3A3C', fs: 16 });
    button(sc, FX.REV_COLORS[col], 612, 286, 88, 26, () => setV('revColor', (col + 1) % 3), { bg: '#FFFFFF', fg: '#3A3A3C', fs: 12, border: '1px solid rgba(0,0,0,0.12)', r: 6 });
    button(sc, '›', 700, 286, 22, 26, () => setV('revColor', (col + 1) % 3), { bg: 'transparent', fg: '#3A3A3C', fs: 16 });
    button(sc, '🎲 Surprise', 602, 336, 108, 28, () => {
      const r = (a, b) => a + Math.random() * (b - a);
      setV('revMode', Math.floor(r(0, 9))); setV('revColor', Math.floor(r(0, 3)));
      setV('revDecay', r(0.8, 6)); setV('revSize', r(40, 100)); setV('revEarly', r(50, 100)); setV('revLate', r(50, 100));
      setV('revModDepth', r(10, 70)); setV('predelay', r(0, 40)); setV('revHighFreq', r(3000, 10000));
    }, { bg: '#FFFFFF', fg: '#3A3A3C', fs: 12, r: 14, border: '1px solid rgba(0,0,0,0.12)' });
    T(sc, 'Random musical space', 656, 382, '#8A8A90', 10, 500, 'middle');
  } else {
    // DETAILS: os nós do gráfico em knobs, mais a modulação
    const xs = [24, 98, 172, 246, 320, 394];
    [['revLowCut', 'Low Cut'], ['revBassFreq', 'Bass Freq'], ['revBassMult', 'Bass Mult'], ['revHighFreq', 'High Freq'], ['revHighShelf', 'High Shelf'], ['revHighCut', 'High Cut']]
      .forEach(([id, label], k) => kn(id, label, xs[k], 266));
    kn('revModRate', 'Mod Rate', 24, 342); kn('revModDepth', 'Mod Depth', 98, 342); kn('revEarly', 'Early', 172, 342); kn('revLate', 'Late', 246, 342);
    sep(470);
    T(sc, FX.REV_MODES[mode].toUpperCase(), 490, 286, '#3A3A3C', 11, 800, 'start', 0.6);
    const words = FX.REV_DESC[mode].split(': ')[1] || '', cdesc = FX.COLOR_DESC[Math.round(P('revColor').v)];
    wrapText(sc, words, 490, 304, 34, '#5A5A60');
    T(sc, 'COLOR · ' + FX.REV_COLORS[Math.round(P('revColor').v)].toUpperCase(), 490, 352, '#3A3A3C', 11, 800, 'start', 0.6);
    wrapText(sc, cdesc.split(': ')[1] || '', 490, 370, 34, '#5A5A60');
  }
}
// Animação do reverb (como a do ChromaVerb): cada partícula nasce com o nível que sai do plugin, numa
// frequência, e some no tempo real de decaimento daquela frequência (Time × Damping EQ). Freeze segura tudo.
const RVA = { parts: [], lvl: 0, t: 0 };
function rvLoop(now) {
  requestAnimationFrame(rvLoop);
  const cv = document.getElementById('rvfx');
  const dt = Math.min(0.05, ((now - (RVA.t || now)) / 1000)); RVA.t = now;
  if (!cv) { RVA.parts.length = 0; return; }
  const m = (S && S.meters) || [0, 0], target = Math.max(0, Math.min(1, (20 * Math.log10(Math.max(m[0], m[1], 1e-6)) + 54) / 54));
  RVA.lvl += (target - RVA.lvl) * Math.min(1, dt * 14);
  const on = P('reverb').v > 0.5 && P('fxBypass').v < 0.5, frozen = on && P('revFreeze').v > 0.5, dec = P('revDecay').v;
  if (on && !frozen && RVA.lvl > 0.02) {
    let n = RVA.lvl * (0.35 + P('reverbMix').n) * 700 * dt;
    while (n > 0 && RVA.parts.length < 1600) {
      if (n < 1 && Math.random() > n) break;
      n -= 1;
      RVA.parts.push({ u: Math.random(), a: RVA.lvl * (0.55 + 0.45 * Math.random()), age: 0, h: Math.pow(Math.random(), 0.8), j: Math.random() - 0.5 });
    }
  }
  const ctx = cv.getContext('2d');
  ctx.setTransform(2, 0, 0, 2, 0, 0);
  ctx.globalCompositeOperation = 'source-over';
  ctx.clearRect(0, 0, 726, 180);
  ctx.globalCompositeOperation = 'lighter';
  const keep = [];
  for (const p of RVA.parts) {
    const f = 20 * Math.pow(1000, 0.08 + 0.86 * p.u), mult = revMult(f), T = Math.max(0.05, dec * mult);
    if (!frozen) p.age += dt * (on ? 1 : 5);
    const a = p.a * Math.pow(10, -3 * p.age / T);  // -60 dB no tempo de decaimento (RT60)
    if (a < 0.012) continue;
    keep.push(p);
    const top = RVY(mult) - RV.GY0, x = RVX(f) - RV.GX0 + p.j * 7;
    const y = 180 - (180 - top) * Math.min(1, 0.25 + a) * p.h;
    const r = 0.7 + a * 2.4, al = Math.min(0.95, a * 1.6);
    ctx.fillStyle = `hsla(${50 + p.u * 150}, 92%, ${55 + a * 20}%, ${al})`;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 6.2832); ctx.fill();
    if (a > 0.3) { ctx.fillStyle = `hsla(${50 + p.u * 150}, 92%, 60%, ${al * 0.18})`; ctx.beginPath(); ctx.arc(x, y, r * 3.2, 0, 6.2832); ctx.fill(); }
  }
  RVA.parts = keep;
}
requestAnimationFrame(rvLoop);

function wrapText(sc, s, x, y, chars, c) {
  const lines = [''];
  for (const w of s.split(' ')) { if ((lines[lines.length - 1] + ' ' + w).length > chars) lines.push(w); else lines[lines.length - 1] = (lines[lines.length - 1] + ' ' + w).trim(); }
  lines.slice(0, 3).forEach((l, k) => T(sc, l, x, y + k * 14, c, 11, 500));
}

const FX_MODULES = [
  { id: 'eq', label: 'EQ', on: 'eqOn', color: '#F5B83D', bg: '#211d17', scene: sceneEq },
  { id: 'comp', label: 'COMP', on: 'compOn', color: '#FF5A4E', bg: '#241416', scene: sceneComp },
  { id: 'sat', label: 'SATURATE', on: 'satOn', color: '#2FD3D3', bg: '#122123', scene: sceneSat },
  { id: 'chorus', label: 'CHORUS', on: 'chorusOn', color: '#5AC8FA', bg: '#11222a', scene: sceneChorus },
  { id: 'stereo', label: 'STEREO', on: 'stereoOn', color: '#9D8CFF', bg: '#1b1832', scene: sceneStereo },
  { id: 'delay', label: 'DELAY', on: 'delayOn', color: '#F5A14A', bg: '#221a11', scene: sceneDelay },
  { id: 'reverb', label: 'REVERB', on: 'reverb', color: '#8CC084', bg: '#11261c', scene: sceneReverb }
];

// mini visualização de cada módulo (caixa 100 x 52)
function tileViz(id) {
  const pts = [];
  const line = (fn) => { for (let k = 0; k <= 40; k++) { const x = k / 40; pts.push((x * 100).toFixed(1) + ',' + fn(x).toFixed(1)); } return 'M' + pts.join('L'); };
  switch (id) {
    case 'eq': return line((x) => 30 - Math.max(-18, Math.min(18, eqResponse(20 * Math.pow(1000, x)))) * 1.1);
    case 'comp': { const th = P('compThresh').v, ra = P('compRatio').v; return line((x) => { const i = -60 + 60 * x, o = i < th ? i : th + (i - th) / ra; return 48 - (o + 60) / 60 * 42; }); }
    case 'sat': { const ty = Math.round(P('satType').v), d = Math.pow(10, P('satDrive').v / 20); return line((x) => 26 - satCurve(ty, (2 * x - 1) * d) * 20); }
    case 'chorus': return line((x) => 26 - Math.sin(x * Math.PI * 4 * P('chorusRate').v) * 18 * P('chorusDepth').n);
    case 'stereo': { const w = P('stereoWidth').v / 100; return line((x) => 46 - Math.sqrt(Math.max(0, 1 - Math.pow((2 * x - 1) / Math.max(0.15, w), 2))) * 38); }
    case 'delay': { const fb = P('delayFeedback').v / 100; return line((x) => { const k = Math.floor(x * 8), ph = x * 8 - k; return 46 - (ph < 0.12 ? Math.pow(Math.max(fb, 0.1), k) * 40 : 0); }); }
    default: { const dec = P('revDecay').n; return line((x) => 46 - Math.exp(-x / (0.1 + dec * 0.6)) * 40 * (0.75 + 0.25 * Math.sin(x * 90))); }
  }
}

function fxVals(t) {
  const sel = L.fxModule || 'eq';
  const tiles = FX_MODULES.map((m0) => {
    const m = m0.id === 'reverb' ? { ...m0, color: RV.OR, bg: '#231613' } : m0;
    const on = P(m.on).v > 0.5;
    return { label: m.label, color: on ? m.color : 'rgba(255,255,255,0.25)', nameColor: on ? '#FFFFFF' : 'rgba(255,255,255,0.45)', bg: m.bg,
      ring: m.id === sel ? `0 0 0 2px ${m.color}` : '0 0 0 0.5px rgba(255,255,255,0.08)', powerBg: on ? m.color : 'transparent',
      viz: tileViz(m.id), pick: () => { L.fxModule = m.id; L.menu = null; dirty = true; },
      toggle: (e) => { e.stopPropagation(); setV(m.on, on ? 0 : 1); } };
  });
  const sc = { bg: '#151518', rects: [], paths: [], texts: [], nodes: [], knobs: [], buttons: [], sliders: [], vsliders: [], menu: null, canvas: false };
  const mod = FX_MODULES.find((m) => m.id === sel);
  mod.scene(sc);
  if (P(mod.on).v < 0.5) T(sc, 'OFF · click the square on the tile to turn it on', FX.W - 20, mod.id === 'reverb' ? 66 : 18, 'rgba(255,255,255,0.5)', 11, 600, 'end');
  sc.menu = L.menu;
  return { fxTiles: tiles, sc, closeMenu: () => { L.menu = null; dirty = true; } };
}

// ------------------------------------------------------------------ interação: knobs e nós do EQ
let knobDrag = null, nodeDrag = null;
root.addEventListener('pointerdown', (e) => {
  const k = e.target.closest('[data-knob]');
  if (k) { knobDrag = { id: k.dataset.knob, y: e.clientY, n: P(k.dataset.knob).n }; e.preventDefault(); e.stopPropagation(); return; }
  const n = e.target.closest('[data-eqnode]');
  if (n && n.getAttribute('data-eqnode')[0] === 'r') { nodeDrag = { rev: n.getAttribute('data-eqnode'), svg: n.ownerSVGElement }; e.preventDefault(); e.stopPropagation(); return; }
  if (n) {
    const i = +n.getAttribute('data-eqnode');
    if (i > 0) { L.eqBand = i; nodeDrag = { i, svg: n.ownerSVGElement }; dirty = true; }
    else nodeDrag = { comp: true, svg: n.ownerSVGElement };
    e.preventDefault(); e.stopPropagation();
  }
}, true);
addEventListener('pointermove', (e) => {
  if (knobDrag) {
    const fine = e.shiftKey ? 0.2 : 1;
    setN(knobDrag.id, Math.min(1, Math.max(0, knobDrag.n + (knobDrag.y - e.clientY) / 200 * fine)));
  } else if (nodeDrag) {
    const r = nodeDrag.svg.getBoundingClientRect(), s = r.width / FX.W;
    const x = (e.clientX - r.left) / s, y = (e.clientY - r.top) / s;
    if (nodeDrag.comp) { setV('compThresh', Math.max(-40, Math.min(0, -60 + (x - 30) / 300 * 60))); return; }
    if (nodeDrag.rev) {  // nós do Damping EQ do reverb
      const cl = (v, a, b) => Math.max(a, Math.min(b, v));
      const f = 20 * Math.pow(1000, cl((x - RV.GX0) / (RV.GX1 - RV.GX0), 0, 1)), mm = (RV.GY1 - y) / (RV.GY1 - RV.GY0) * RV.MAX;
      if (nodeDrag.rev === 'rlc') setV('revLowCut', cl(f, 10, 1000));
      else if (nodeDrag.rev === 'rhc') setV('revHighCut', cl(f, 1000, 20000));
      else if (nodeDrag.rev === 'rbass') { setV('revBassFreq', cl(f, 50, 1000)); setV('revBassMult', cl(mm, 0.25, 4)); }
      else { setV('revHighFreq', cl(f, 1000, 20000)); setV('revHighShelf', cl(20 * Math.log10(Math.max(mm, 0.063)), -24, 0)); }
      return;
    }
    const b = nodeDrag.i, f = 20 * Math.pow(1000, Math.max(0, Math.min(1, (x - 20) / 726)));
    setV('eq' + b + 'Freq', f);
    const ty = Math.round(P('eq' + b + 'Type').v);
    if (ty !== 0 && ty !== 4) setV('eq' + b + 'Gain', Math.max(-18, Math.min(18, (158 - y) / 128 * 18)));
  }
});
addEventListener('pointerup', () => { knobDrag = null; nodeDrag = null; });
root.addEventListener('dblclick', (e) => {
  const k = e.target.closest('[data-knob]');
  if (k) setN(k.dataset.knob, P(k.dataset.knob).d ?? 0.5);
});
root.addEventListener('wheel', (e) => {
  const n = e.target.closest('[data-eqnode]'), k = e.target.closest('[data-knob]');
  if (n && +n.getAttribute('data-eqnode') > 0) { const id = 'eq' + n.getAttribute('data-eqnode') + 'Q'; setN(id, Math.min(1, Math.max(0, P(id).n - Math.sign(e.deltaY) * 0.03))); e.preventDefault(); }
  else if (k) { setN(k.dataset.knob, Math.min(1, Math.max(0, P(k.dataset.knob).n - Math.sign(e.deltaY) * 0.02))); e.preventDefault(); }
}, { passive: false });
