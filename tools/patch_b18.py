"""Modo Auto = VIOLET decide (todas as notas no canal 'sem técnica'); CC1 do modelo vira opção (desligado, como na
avaliação oficial w_cc = 0); animação do modo foco; Alt + roda fora das notas = altura das notas (zoom vertical)."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")


def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)


patch('engine/Articulator.cpp', [
    ("""        auto notes = prepareForViolet (s.mode == ArticMode::manual ? voice : collapseOrnaments (voice));
        applyForced (notes);
        classify (notes, s);""",
     """        if (s.mode == ArticMode::autoMode)  // Auto: o VIOLET decide o arco sozinho (canal "sem técnica", como na gravação real)
        {
            auto notes = prepareForViolet (voice);
            for (auto& n : notes) n.tech = Tech::none, n.reason = "Auto: VIOLET decides the bowing";
            out.notes.insert (out.notes.end(), notes.begin(), notes.end());
            continue;
        }
        auto notes = prepareForViolet (s.mode == ArticMode::manual ? voice : collapseOrnaments (voice));
        applyForced (notes);
        classify (notes, s);"""),
])
patch('source/PluginProcessor.cpp', [
    ("""    boolP ("modelDyn", "Model Dynamics", true);  // a curva de dinâmica vai para o VIOLET (CC1)""",
     """    boolP ("modelDyn", "Model Dynamics", false);  // experimental: a curva de dinâmica vai para o VIOLET (CC1); a avaliação oficial usa w_cc = 0"""),
])
patch('ui/app.js', [
    ("    slider('dynFollow', 'Dynamics follow', 5), slider('vibAmount', 'Extra vibrato', 6), slider('vibRate', 'Vibrato rate', 7)];",
     "    slider('dynFollow', 'Dynamics follow', 5), slider('vibAmount', 'Extra vibrato', 6), slider('vibRate', 'Vibrato rate', 7),\n    slider('modelDyn', 'Model dynamics (CC1, experimental)', 8, P('modelDyn').v > 0.5 ? 'On' : 'Off')];"),
    # modo foco animado: a geometria anda até o alvo (e os painéis somem com escala e transparência)
    ("""  const wide = !!(L.focusMode ?? prefs.focusMode) && tab === 'perf';  // modo foco: só a Performance
  setGeo(wide);""",
     """  const wide = !!(L.focusMode ?? prefs.focusMode) && tab === 'perf';  // modo foco: só a Performance
  { const now = performance.now(), k = 1 - Math.exp(-Math.min(80, now - (L.geoTime || now)) / 70); L.geoTime = now;
    L.geoK = L.geoK == null ? (wide ? 1 : 0) : L.geoK + ((wide ? 1 : 0) - L.geoK) * k;
    if (Math.abs(L.geoK - (wide ? 1 : 0)) < 0.002) L.geoK = wide ? 1 : 0; else dirty = true; }
  setGeo(L.geoK);"""),
    ("panelsShow: wide ? 'hidden' : 'visible',", "pOp: 1 - L.geoK, pSc: 1 - 0.04 * L.geoK, pPe: L.geoK > 0.5 ? 'none' : 'auto', pVis: L.geoK > 0.99 ? 'hidden' : 'visible',"),
    ("""function setGeo(focus) {
  G.l = focus ? 22 : 268; G.w = focus ? 1236 : 790;""", """function setGeo(k) {  // k: 0 = normal, 1 = foco (valores no meio durante a animação)
  k = +k; G.l = 268 + (22 - 268) * k; G.w = 790 + (1236 - 790) * k;"""),
    # zoom vertical (Alt + roda fora das notas): faixa de alturas menor = notas mais altas
    ("""  const pLo = pitches.length ? Math.min(...pitches) - 2 : 60, pHi = pitches.length ? Math.max(...pitches) + 2 : 84;""",
     """  let pLo = pitches.length ? Math.min(...pitches) - 2 : 60, pHi = pitches.length ? Math.max(...pitches) + 2 : 84;
  const vz = Math.max(1, L.vzoom || 1);
  if (vz > 1.01) {  // zoom vertical: só uma janela das alturas, centrada onde o usuário deixou
    const span = Math.max(4, (pHi - pLo) / vz), c = Math.min(Math.max(L.vcenter ?? (pLo + pHi) / 2, pLo + span / 2), pHi - span / 2);
    L.vcenter = c; pLo = c - span / 2; pHi = c + span / 2;
  }
  const noteH = Math.round(Math.max(12, Math.min(28, 200 / Math.max(1, pHi - pLo) * 0.85)));"""),
    ("""    return { i, x: X(s0), y: Y(pp) - 2, w, vel,""", """    return { i, x: X(s0), y: Y(pp) + 4 - noteH / 2, h: noteH, r: noteH / 2, fs: noteH > 16 ? 10 : 8, w, vel,"""),
    ("""  }).filter((n) => n.x + n.w >= 262 && n.x <= X1 + 4);""", """  }).filter((n) => n.x + n.w >= G.l - 6 && n.x <= X1 + 4 && n.y > 172 && n.y < 400);"""),
    ("""  L.noteBoxes = notes.map((n) => ({ i: n.i, x: n.x, y: n.y, w: n.w }));""", """  L.noteBoxes = notes.map((n) => ({ i: n.i, x: n.x, y: n.y, w: n.w, h: n.h }));"""),
    ("""const hit = (L.noteBoxes || []).find((b) => px >= b.x - 3 && px <= b.x + b.w + 3 && py >= b.y - 6 && py <= b.y + 16);""",
     """const hit = (L.noteBoxes || []).find((b) => px >= b.x - 3 && px <= b.x + b.w + 3 && py >= b.y - 6 && py <= b.y + (b.h || 12) + 4);"""),
    ("""  if (L.zoomAt == null) L.zoomAt = (V.v0 + V.v1) / 2;
  if (e.ctrlKey) {  // Ctrl + roda: zoom em volta do cursor""",
     """  if (e.altKey && !cap) {  // Alt + roda fora das notas: altura das notas (zoom vertical); Shift + roda: rola na vertical
    L.vzoom = Math.max(1, Math.min(6, (L.vzoom || 1) * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    dirty = true; e.preventDefault(); return;
  }
  if (e.shiftKey && !e.ctrlKey && (L.vzoom || 1) > 1.01) { L.vcenter = (L.vcenter ?? 72) + (e.deltaY < 0 ? 1 : -1); dirty = true; e.preventDefault(); return; }
  if (L.zoomAt == null) L.zoomAt = (V.v0 + V.v1) / 2;
  if (e.ctrlKey) {  // Ctrl + roda: zoom em volta do cursor"""),
    ("    doFit: () => { L.zoomT = 1; dirty = true; },", "    doFit: () => { L.zoomT = 1; L.vzoom = 1; L.vcenter = null; dirty = true; },"),
])
patch('ui/edit.js', [("b.y <= y1 && b.y + 12 >= y0) s.add(b.i);", "b.y <= y1 && b.y + (b.h || 12) >= y0) s.add(b.i);")])
b = open('ui/build_ui.py', encoding='utf-8').read()
o = '''height: 12px; border-radius: 6px; background: linear-gradient(rgba(255,255,255,0.30), rgba(255,255,255,0) 70%), {{n.art}}; opacity: {{n.op}}; box-shadow: {{n.ring}}; cursor: {{n.cursor}}; overflow: hidden;"><span style="position: absolute; left: 4px; top: 0; font-size: 8px; font-weight: 700; line-height: 12px;'''
assert b.count(o) == 1
b = b.replace(o, '''height: {{n.h}}px; border-radius: {{n.r}}px; background: linear-gradient(rgba(255,255,255,0.30), rgba(255,255,255,0) 70%), {{n.art}}; opacity: {{n.op}}; box-shadow: {{n.ring}}; cursor: {{n.cursor}}; overflow: hidden;"><span style="position: absolute; left: 4px; top: 0; font-size: {{n.fs}}px; font-weight: 700; line-height: {{n.h}}px;''')
assert b.count('visibility: {{panelsShow}};') == 2
b = b.replace('visibility: {{panelsShow}};', 'opacity: {{pOp}}; transform: scale({{pSc}}); pointer-events: {{pPe}}; visibility: {{pVis}}; transition: none;')
b = b.replace('Click selects · drag on empty space: box select', 'Alt+wheel: note height · Click selects · drag on empty space: box select', 1)
open('ui/build_ui.py', 'w', encoding='utf-8').write(b)
print('ok')
