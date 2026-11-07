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
  const OR = RV.OR, tab = L.revTab || 'main', mode = Math.round(P('revMode').v), dec = P('revDecay').v;
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
  // nuvem do ambiente: pontos coloridos por frequência que sobem até a curva e respiram com o nível
  const m = (S && S.meters) || [0, 0], lvl = Math.max(0, Math.min(1, (20 * Math.log10(Math.max(m[0], m[1], 1e-6)) + 60) / 60));
  const energy = (0.35 + 0.65 * lvl) * (P('reverb').v > 0.5 ? 1 : 0.4) * (0.4 + 0.6 * P('reverbMix').n);
  let seed = lvl > 0.05 ? Math.floor(Date.now() / 120) : 7;
  const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
  const bins = Array.from({ length: 6 }, () => []);
  for (let k = 0; k < 240; k++) {
    const u = rnd(), f = 20 * Math.pow(1000, 0.1 + 0.82 * u), top = RVY(revMult(f));
    const y = RV.GY1 - Math.pow(rnd(), 0.7) * (RV.GY1 - top) * energy, x = RVX(f) + (rnd() - 0.5) * 6;
    bins[Math.min(5, Math.floor(u * 6))].push(`M${(x - 1.3).toFixed(1)},${y.toFixed(1)}a1.3,1.3 0 1,0 2.6,0a1.3,1.3 0 1,0 -2.6,0`);
  }
  bins.forEach((b, i) => { if (b.length) Pth(sc, b.join(''), 'none', 0, `hsl(${52 + i * 26}, 88%, 58%)`, 0.75); });
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
function wrapText(sc, s, x, y, chars, c) {
  const lines = [''];
  for (const w of s.split(' ')) { if ((lines[lines.length - 1] + ' ' + w).length > chars) lines.push(w); else lines[lines.length - 1] = (lines[lines.length - 1] + ' ' + w).trim(); }
  lines.slice(0, 3).forEach((l, k) => T(sc, l, x, y + k * 14, c, 11, 500));
}

