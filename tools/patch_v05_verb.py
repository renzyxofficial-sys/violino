"""v0.5: Reverb com Freeze e Ducking (DSP + parâmetros) e o painel novo no estilo da referência."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


# ---- DSP
h = open("engine/MixFx.h", encoding="utf-8").read()
h = rep(h, "    float revSize = 1, revAttack = 0.5f, revEarly = 1, revLate = 1, revModRate = 2.5f, revModDepth = 0.38f, revHighCut = 8000, revLowCut = 10;",
        "    float revSize = 1, revAttack = 0.5f, revEarly = 1, revLate = 1, revModRate = 2.5f, revModDepth = 0.38f, revHighCut = 8000, revLowCut = 10;\n    bool revFreeze = false;\n    float revDucking = 0;")
h = rep(h, "    float dlyLpState[2] = { 0, 0 };", "    float dlyLpState[2] = { 0, 0 };\n    double duckEnv = 0;")
open("engine/MixFx.h", "w", encoding="utf-8").write(h)
c = open("engine/MixFx.cpp", encoding="utf-8").read()
c = rep(c, "        p.modRate = cur.revModRate, p.modDepth = std::min (1.0, cur.revModDepth * colorMod[col]);",
        "        p.modRate = cur.revModRate, p.modDepth = std::min (1.0, cur.revModDepth * colorMod[col]);\n        if (cur.revFreeze)  // Freeze: cauda infinita, sem entrada nova\n            p.decay = 600, p.bassMult = 1, p.highShelfDb = 0;")
c = rep(c, """            userVerb.process (userSendLp[0].process (userSendHp[0].process (send)), tl, tr);
            l = (1 - cur.reverbMix) * l + cur.reverbMix * tl * userTail;
            r = (1 - cur.reverbMix) * r + cur.reverbMix * tr * userTail;""", """            userVerb.process (cur.revFreeze ? 0.0f : userSendLp[0].process (userSendHp[0].process (send)), tl, tr);
            // Ducking: o molhado abaixa enquanto o violino toca e volta nas pausas
            duckEnv = std::max (double (std::abs (send)), duckEnv * 0.9996);
            const float duck = 1.0f - cur.revDucking * float (std::min (1.0, duckEnv * 6.0));
            const float w = cur.reverbMix * duck * (cur.revFreeze ? 1.0f : userTail) * (cur.revFreeze ? userTail : 1.0f);
            l = (1 - cur.reverbMix) * l + w * tl;
            r = (1 - cur.reverbMix) * r + w * tr;""")
open("engine/MixFx.cpp", "w", encoding="utf-8").write(c)

s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """    logP ("revLowCut", "Reverb LowCut", 10, 1000, 10, 100, "Hz");""", """    logP ("revLowCut", "Reverb LowCut", 10, 1000, 10, 100, "Hz");
    boolP ("revFreeze", "Reverb Freeze", false);
    floatP ("revDucking", "Reverb Ducking", 0, 100, 0, "%");""")
s = rep(s, """    m.revHighCut = value ("revHighCut"), m.revLowCut = value ("revLowCut");""", """    m.revHighCut = value ("revHighCut"), m.revLowCut = value ("revLowCut");
    m.revFreeze = flag ("revFreeze"), m.revDucking = value ("revDucking") / 100.f;""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

# ---- UI: sliders no palco
b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """        <sc-for list="{{sc.buttons}}" as="b">""", """        <sc-for list="{{sc.sliders}}" as="s">
          <div data-slider="{{s.id}}" style="position: absolute; left: {{s.x}}px; top: {{s.y}}px; width: {{s.w}}px; height: {{s.h}}px; border-radius: {{s.r}}px; background: {{s.track}}; cursor: pointer; box-shadow: inset 0 1px 3px rgba(0,0,0,0.12);">
            <span style="position: absolute; left: 0; top: 0; bottom: 0; width: {{s.pct}}%; border-radius: {{s.r}}px; background: {{s.fill}};"></span>
            <span class="lg-thumb" style="position: absolute; left: {{s.pct}}%; top: 50%; width: {{s.th}}px; height: {{s.th}}px; margin-left: -{{s.half}}px; margin-top: -{{s.half}}px; border-radius: 50%;"></span>
          </div>
        </sc-for>
        <sc-for list="{{sc.buttons}}" as="b">""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

f = open("ui/fx.js", encoding="utf-8").read()
start = f.index("function sceneReverb(sc) {")
end = f.index("const FX_MODULES = [")
f = f[:start] + r'''function sceneReverb(sc) {
  // painel claro com textura (estilo da referência) e as funções completas do reverb
  const th = revTheme(), blue = th.o === '#8CC084' ? '#6F8FD8' : th.o;
  sc.bg = 'radial-gradient(circle at 28% 18%, #F7F7F9 0%, #E6E6EA 55%, #D9D9DF 100%)';
  const ink = '#232329', soft = '#6b6b75';
  const ko = { face: '#F8F8FA', rim: 'rgba(0,0,0,0.10)', trackColor: 'rgba(0,0,0,0.08)', pointer: ink, labelColor: ink, valueColor: soft };
  const kn = (id, label, x, y, size = 46) => knob(sc, id, label, x, y, size, blue, ko);
  // cabeçalho e modo
  T(sc, 'REVERB', 28, 44, ink, 26, 900, 'start', 3);
  T(sc, 'mode', 290, 30, ink, 15, 700, 'middle');
  const mode = Math.round(P('revMode').v);
  button(sc, '‹', 196, 40, 24, 24, () => setV('revMode', (mode + 8) % 9), { bg: 'transparent', fg: ink, fs: 18 });
  button(sc, FX.REV_MODES[mode], 222, 40, 136, 24, () => { L.menu = { x: 222, y: 66, w: 150, items: FX.REV_MODES.map((t, i) => ({ label: t, check: i === mode ? '✓ ' : '', pick: () => { L.menu = null; setV('revMode', i); } })) }; dirty = true; }, { bg: 'transparent', fg: ink, fs: 13 });
  button(sc, '›', 360, 40, 24, 24, () => setV('revMode', (mode + 1) % 9), { bg: 'transparent', fg: ink, fs: 18 });
  // donut central: cresce com o Size, achata com o Decay
  const cx = 290, cy = 196, size = 0.55 + 0.45 * P('revSize').n, dec = P('revDecay').n;
  const R0 = 92 * size, ry = R0 * (0.78 + 0.22 * (1 - dec));
  const ell = (rx, ryy, ox = 0, oy = 0) => `M${cx + ox - rx},${cy + oy}a${rx},${ryy} 0 1,0 ${2 * rx},0a${rx},${ryy} 0 1,0 ${-2 * rx},0`;
  sc.paths.push({ d: ell(R0 + 6, ry + 10, 6, 14), stroke: 'none', w: 0, fill: 'rgba(0,0,0,0.10)', o: 1 });
  sc.paths.push({ d: ell(R0, ry), stroke: 'none', w: 0, fill: blue, o: 1 });
  sc.paths.push({ d: ell(R0 * 0.82, ry * 0.8, -R0 * 0.1, -ry * 0.12), stroke: 'none', w: 0, fill: 'rgba(255,255,255,0.22)', o: 1 });
  sc.paths.push({ d: ell(R0 * 0.3, ry * 0.3, R0 * 0.05, ry * 0.05), stroke: 'none', w: 0, fill: 'rgba(0,0,0,0.18)', o: 1 });
  sc.paths.push({ d: ell(R0 * 0.26, ry * 0.26, R0 * 0.04, ry * 0.03), stroke: 'none', w: 0, fill: '#E3E3E8', o: 1 });
  if (P('revFreeze').v > 0.5) T(sc, '❄', cx, cy + 8, '#FFFFFF', 30, 700, 'middle');
  // dimension / character
  T(sc, 'dimension', 92, 90, ink, 15, 700, 'middle');
  kn('revDecay', 'Time', 24, 100); kn('revSize', 'Size', 96, 100);
  kn('predelay', 'Pre-Delay', 24, 186); kn('revAttack', 'Attack', 96, 186);
  T(sc, 'character', 488, 90, ink, 15, 700, 'middle');
  kn('revEarly', 'Diffusion', 420, 100); kn('revLate', 'Late', 492, 100);
  kn('revHighFreq', 'Damping', 420, 186); kn('revModDepth', 'Modulation', 492, 186);
  // embaixo: Ducking, Freeze, Mix, saída
  kn('revDucking', 'Ducking', 24, 300, 42);
  const fz = P('revFreeze').v > 0.5;
  button(sc, '❄', 96, 318, 40, 40, () => setV('revFreeze', fz ? 0 : 1), { bg: fz ? blue : '#F8F8FA', fg: fz ? '#fff' : ink, r: 20, fs: 18, border: '1px solid rgba(0,0,0,0.1)' });
  T(sc, 'Freeze', 116, 376, ink, 11, 600, 'middle');
  const mixN = P('reverbMix').n;
  sc.sliders.push({ id: 'reverbMix', x: 170, y: 324, w: 240, h: 30, r: 15, track: 'rgba(0,0,0,0.07)', fill: blue, pct: mixN * 100, th: 30, half: 15 });
  T(sc, 'Mix · ' + P('reverbMix').text, 290, 376, ink, 11, 600, 'middle');
  const m = (S && S.meters) || [0, 0], dbp = (v) => Math.max(0, Math.min(1, (20 * Math.log10(Math.max(v, 1e-6)) + 60) / 60));
  for (const [k, x] of [[0, 452], [1, 460]]) { R(sc, x, 300, 5, 70, 'rgba(0,0,0,0.08)', 'none', 0, 2); R(sc, x, 300 + 70 * (1 - dbp(m[k])), 5, 70 * dbp(m[k]), blue, 'none', 0, 2); }
  T(sc, 'Output', 458, 386, ink, 11, 600, 'middle');
  // coluna colorida: filter, damping, color
  R(sc, 560, 0, 206, 420, blue, 'none', 0, 0);
  const wk = { face: '#F8F8FA', rim: 'rgba(0,0,0,0.12)', trackColor: 'rgba(255,255,255,0.25)', pointer: ink, labelColor: '#FFFFFF', valueColor: 'rgba(255,255,255,0.85)' };
  T(sc, 'filter', 663, 30, '#FFFFFF', 15, 700, 'middle');
  knob(sc, 'revHighCut', 'High Cut', 584, 40, 44, '#FFFFFF', wk); knob(sc, 'revLowCut', 'Low Cut', 680, 40, 44, '#FFFFFF', wk);
  T(sc, 'damping', 663, 138, '#FFFFFF', 15, 700, 'middle');
  knob(sc, 'revHighShelf', 'HighShelf', 570, 148, 40, '#FFFFFF', wk); knob(sc, 'revBassFreq', 'BassFreq', 640, 148, 40, '#FFFFFF', wk);
  knob(sc, 'revBassMult', 'BassMult', 708, 148, 40, '#FFFFFF', wk);
  T(sc, 'color', 663, 250, '#FFFFFF', 15, 700, 'middle');
  const col = Math.round(P('revColor').v);
  button(sc, '‹', 584, 260, 24, 24, () => setV('revColor', (col + 2) % 3), { bg: 'transparent', fg: '#fff', fs: 18 });
  button(sc, FX.REV_COLORS[col], 610, 260, 106, 24, () => setV('revColor', (col + 1) % 3), { bg: 'rgba(255,255,255,0.18)', fg: '#fff', fs: 13 });
  button(sc, '›', 718, 260, 24, 24, () => setV('revColor', (col + 1) % 3), { bg: 'transparent', fg: '#fff', fs: 18 });
  knob(sc, 'revModRate', 'Mod Rate', 600, 300, 40, '#FFFFFF', wk);
  // Surprise: sorteia um reverb musical
  button(sc, '🎲', 690, 312, 40, 40, () => {
    const r = (a, b) => a + Math.random() * (b - a);
    setV('revMode', Math.floor(r(0, 9))); setV('revColor', Math.floor(r(0, 3)));
    setV('revDecay', r(0.8, 6)); setV('revSize', r(40, 100)); setV('revEarly', r(50, 100)); setV('revLate', r(50, 100));
    setV('revModDepth', r(10, 70)); setV('predelay', r(0, 40)); setV('revHighFreq', r(3000, 10000));
  }, { bg: 'rgba(0,0,0,0.25)', fg: '#fff', r: 20, fs: 18 });
  T(sc, 'Surprise', 710, 370, '#FFFFFF', 11, 600, 'middle');
  T(sc, FX.REV_DESC[mode], 24, 408, soft, 11, 600);
}

''' + f[end:]
f = rep(f, "  const sc = { bg: '#151518', rects: [], paths: [], texts: [], nodes: [], knobs: [], buttons: [], menu: null };",
        "  const sc = { bg: '#151518', rects: [], paths: [], texts: [], nodes: [], knobs: [], buttons: [], sliders: [], menu: null };")
f = rep(f, "  if (P(mod.on).v < 0.5) T(sc, 'OFF · click the square on the tile to turn it on', FX.W - 16, 18, 'rgba(255,255,255,0.5)', 11, 600, 'end');",
        "  if (P(mod.on).v < 0.5) T(sc, 'OFF · click the square on the tile to turn it on', mod.id === 'reverb' ? 548 : FX.W - 16, 18, mod.id === 'reverb' ? '#6b6b75' : 'rgba(255,255,255,0.5)', 11, 600, 'end');")
# tile do reverb: azul do painel novo
f = rep(f, "    const m = m0.id === 'reverb' ? { ...m0, color: revTheme().o, bg: revTheme().tile } : m0;",
        "    const m = m0.id === 'reverb' ? { ...m0, color: '#8FB0F0', bg: '#1d2436' } : m0;")
open("ui/fx.js", "w", encoding="utf-8").write(f)
print("ok")
