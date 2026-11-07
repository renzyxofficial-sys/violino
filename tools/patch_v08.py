"""v0.8: grade (compassos/tempos pelo BPM + faixas das teclas pretas), barra de rolagem da timeline,
arrastar a vista com o botão do meio, botão que desliga todos os efeitos."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, '    boolP ("lock", "Lock MIDI", false);', '    boolP ("lock", "Lock MIDI", false);\n    boolP ("fxBypass", "Bypass All Effects", false);')
s = rep(s, "MixSettings ViolinoProcessor::mixSettings() const\n{\n    MixSettings m;",
        "MixSettings ViolinoProcessor::mixSettings() const\n{\n    MixSettings m;\n    if (flag (\"fxBypass\"))  // todos os efeitos desligados de uma vez (só o ganho de saída fica)\n    {\n        m.eqOn = m.compOn = m.satOn = m.chorusOn = m.stereoOn = m.delayOn = m.reverbOn = false;\n        m.outputDb = value (\"output\");\n        return m;\n    }")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """      <div data-ruler="1" title="Click to move the cursor\"""", """      <sc-for list="{{rows}}" as="g"><span style="position: absolute; left: 268px; width: 790px; top: {{g.y}}px; height: {{g.h}}px; background: {{g.bg}}; pointer-events: none;"></span></sc-for>
      <sc-for list="{{grid}}" as="g"><span style="position: absolute; left: {{g.x}}px; top: 140px; width: 1px; height: 300px; background: {{g.c}}; pointer-events: none;"></span></sc-for>
      <sc-if value="{{hscroll}}">
        <div data-hscroll="1" style="position: absolute; left: 268px; top: 444px; width: 790px; height: 8px; border-radius: 4px; background: {{t.fill}}; cursor: pointer;">
          <span style="position: absolute; left: {{hscroll.x}}px; width: {{hscroll.w}}px; top: 0; height: 8px; border-radius: 4px; background: {{t.secondary}};"></span>
        </div>
      </sc-if>
      <div data-ruler="1" title="Click to move the cursor\"""")
b = rep(b, """      <div style="position: absolute; left: 0; top: 0; right: 0; height: 44px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;">""",
        """      <button onClick="{{toggleBypass}}" title="Turn all effects off or on" style="position: absolute; right: 0; top: 0; width: 110px; height: 44px; border: 0; border-radius: 10px; background: {{bypassBg}}; color: {{bypassFg}}; font-size: 12px; font-weight: 700; cursor: pointer;">⏻ {{bypassLabel}}</button>
      <div style="position: absolute; left: 0; top: 0; right: 118px; height: 44px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;">""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

a = open("ui/app.js", encoding="utf-8").read()
# vista: o zoom guarda o centro; a vista inteira fica em L.full para a barra de rolagem
a = rep(a, """  if (L.zoom > 1.01) {
    const span = (v1 - v0) / L.zoom, c = L.zoomAt ?? (S && S.playing ? playhead : v0 + span / 2);
    v0 = Math.max(v0, c - span / 2); v1 = v0 + span;
  }""", """  const fullA = v0, fullB = v1;
  L.full = { a: fullA, b: fullB };
  if (L.zoom > 1.01) {
    const span = (v1 - v0) / L.zoom, c = L.zoomAt ?? (S && S.playing ? playhead : v0 + span / 2);
    v0 = Math.min(Math.max(fullA, c - span / 2), fullB - span); v1 = v0 + span;
  }""")
a = rep(a, "  const notes = capIn.map(", """  // grade: compassos e tempos pelo BPM (mais fina com zoom) e faixas das teclas pretas
  const beat = 60 / ((S && S.bpm) || 120), grid = [];
  const sub = (v1 - v0) / beat > 64 ? 4 : (v1 - v0) / beat < 8 ? 0.25 : 1;
  for (let k = Math.ceil(v0 / (beat * sub)); k * beat * sub <= v1 && grid.length < 400; k++) {
    const tt = k * beat * sub, x = X(tt), bar = Math.abs(tt / (beat * 4) - Math.round(tt / (beat * 4))) < 1e-6;
    if (x >= 268 && x <= 1058) grid.push({ x, c: bar ? (dark ? 'rgba(255,255,255,0.14)' : 'rgba(0,0,0,0.14)') : (dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)') });
  }
  const rows = [], rowH = 270 / Math.max(1, pHi - pLo);
  for (let p = Math.ceil(pLo); p <= pHi; p++)
    if ([1, 3, 6, 8, 10].includes(((p % 12) + 12) % 12)) rows.push({ y: Y(p) - rowH / 2 + 4, h: rowH, bg: dark ? 'rgba(255,255,255,0.025)' : 'rgba(0,0,0,0.03)' });
  const hscroll = L.zoom > 1.01 ? { x: (v0 - fullA) / (fullB - fullA) * 790, w: Math.max(24, (v1 - v0) / (fullB - fullA) * 790) } : null;
  const notes = capIn.map(""")
a = rep(a, "    hasNotes: capIn.length > 0, palette, dragChip,", """    hasNotes: capIn.length > 0, palette, dragChip, grid, rows, hscroll,
    toggleBypass: () => setV('fxBypass', P('fxBypass').v > 0.5 ? 0 : 1), bypassLabel: P('fxBypass').v > 0.5 ? 'FX OFF' : 'FX ON',
    bypassBg: P('fxBypass').v > 0.5 ? t.rec : t.fill, bypassFg: P('fxBypass').v > 0.5 ? '#FFFFFF' : t.text,""")
# barra de rolagem e botão do meio: arrastam a vista
a = rep(a, """  const dm = e.target.closest('[data-dragmidi]');""", """  const hs = e.target.closest('[data-hscroll]');
  if (hs && L.full) { L.scrollDrag = hs; scrollTo(e); e.preventDefault(); return; }
  if (e.button === 1 && L.view && e.target.closest('[data-roll],[data-cap],[data-ruler]')) {
    L.pan = { x: e.clientX, at: (L.view.v0 + L.view.v1) / 2, span: L.view.v1 - L.view.v0 };
    if ((L.zoom || 1) <= 1.01) L.zoom = 1.0001;
    e.preventDefault(); return;
  }
  const dm = e.target.closest('[data-dragmidi]');""")
a = rep(a, """function chipMove(e) {""", """function scrollTo(e) {
  const r = L.scrollDrag.getBoundingClientRect(), f = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
  L.zoomAt = L.full.a + f * (L.full.b - L.full.a); dirty = true;
}
function chipMove(e) {""")
a = rep(a, """  if (L.chipDrag) chipMove(e);""", """  if (L.chipDrag) chipMove(e);
  if (L.scrollDrag) scrollTo(e);
  if (L.pan) { const s = root.getBoundingClientRect().width / 1280; L.zoomAt = L.pan.at - (e.clientX - L.pan.x) / s / 770 * L.pan.span; dirty = true; }""")
a = rep(a, """addEventListener('pointerup', (e) => {
  drag = null;""", """addEventListener('pointerup', (e) => {
  drag = null;
  L.scrollDrag = null;
  L.pan = null;""")
a = rep(a, "addEventListener('pointerdown', grabFocus, true);", "addEventListener('pointerdown', grabFocus, true);\naddEventListener('auxclick', (e) => { if (e.button === 1) e.preventDefault(); });\naddEventListener('mousedown', (e) => { if (e.button === 1) e.preventDefault(); });  // sem a rolagem automática do botão do meio")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
