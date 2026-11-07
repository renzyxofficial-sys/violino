"""v0.6: Stereo off por padrão; chip de articulação segue o mouse e cai só na nota; Ctrl+roda = zoom;
Play Mode Legato / Shorts (Spiccato, Staccato, Pizzicato); Steps 1..50; rótulo do Zoom livre."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, 'boolP ("stereoOn", "Stereo", true);', 'boolP ("stereoOn", "Stereo", false);')
s = rep(s, 'const juce::StringArray kPlayModes { "Legato", "Poly Legato", "Long Normal" };',
        'const juce::StringArray kPlayModes { "Legato", "Shorts" };\nconst juce::StringArray kShorts { "Spiccato", "Staccato", "Pizzicato" };\nconst Forced kShortForced[] = { Forced::spiccato, Forced::staccato, Forced::pizzicato };')
s = rep(s, '    choiceP ("playMode", "Play Mode", kPlayModes, 0);',
        '    choiceP ("playMode", "Play Mode", kPlayModes, 0);\n    choiceP ("shortsMode", "Shorts Type", kShorts, 0);\n    l.add (std::make_unique<AudioParameterInt> (ParameterID { "renderSteps", 1 }, "Render Steps", 1, 50, 30));')
# Shorts = polifônico sem legato, com a técnica curta escolhida em toda nota que você não fixou
s = rep(s, "    s.play = PlayMode (choice (\"playMode\"));", "    s.play = choice (\"playMode\") == 1 ? PlayMode::longNormal : PlayMode::legato;")
s = rep(s, "    live.play = PlayMode (choice (\"playMode\"));", "    const bool shorts = choice (\"playMode\") == 1;\n    live.play = shorts ? PlayMode::longNormal : PlayMode::legato;")
s = rep(s, "    live.forced = ksPending ? liveForced : paramForced;",
        "    live.forced = ksPending ? liveForced : paramForced;\n    if (shorts && live.forced == Forced::autoMode) live.forced = kShortForced[juce::jlimit (0, 2, choice (\"shortsMode\"))];")
s = rep(s, "            in.push_back ({ notes[i].start - p.origin, notes[i].end - p.origin, notes[i].pitch, notes[i].vel, Tech::automatic, notes[i].forced });",
        "            in.push_back ({ notes[i].start - p.origin, notes[i].end - p.origin, notes[i].pitch, notes[i].vel, Tech::automatic,\n                            notes[i].forced == Forced::autoMode && choice (\"playMode\") == 1 ? kShortForced[juce::jlimit (0, 2, choice (\"shortsMode\"))] : notes[i].forced });")
# Steps no hash e no job; os botões de qualidade ajustam os steps
s = rep(s, '    for (auto* id : { "playMode", "articMode", "quality", "legatoGap", "portaVel", "takes" })',
        '    for (auto* id : { "playMode", "shortsMode", "articMode", "quality", "legatoGap", "portaVel", "takes", "renderSteps" })')
s = rep(s, "        p.hash = fnv (fnv (h, quality), takes) | 1;", "        p.hash = fnv (fnv (fnv (h, quality), takes), juce::roundToInt (value (\"renderSteps\"))) | 1;")
s = rep(s, "    job.takes = juce::roundToInt (value (\"takes\"));", "    job.takes = juce::roundToInt (value (\"takes\"));\n    job.steps = juce::roundToInt (value (\"renderSteps\"));")
s = rep(s, """        if (c["id"].toString() == "revMode")""", """        if (c["id"].toString() == "quality")  // Low 8 · Medium 15 · High 30 · Extreme 30 (+ 8 takes)
            setParam ("renderSteps", float (qualityInfo (Quality (choice ("quality"))).steps));
        if (c["id"].toString() == "revMode")""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

e = open("source/EngineService.h", encoding="utf-8").read()
e = rep(e, "        int takes = 0;\n    };", "        int takes = 0;\n        int steps = 0;  // 0 = o do nível de qualidade\n    };")
open("source/EngineService.h", "w", encoding="utf-8").write(e)
e = open("source/EngineService.cpp", encoding="utf-8").read()
e = rep(e, "                                               job.takes);", "                                               job.takes, job.steps);")
open("source/EngineService.cpp", "w", encoding="utf-8").write(e)
p = open("engine/Performer.h", encoding="utf-8").read()
p = rep(p, "                  const std::function<bool (float)>& progress, int takesOverride = 0);",
        "                  const std::function<bool (float)>& progress, int takesOverride = 0, int stepsOverride = 0);")
open("engine/Performer.h", "w", encoding="utf-8").write(p)
p = open("engine/Performer.cpp", encoding="utf-8").read()
p = rep(p, "                         const std::function<bool (float)>& progress, int takesOverride)\n{\n    auto info = qualityInfo (q);",
        "                         const std::function<bool (float)>& progress, int takesOverride, int stepsOverride)\n{\n    auto info = qualityInfo (q);\n    if (stepsOverride > 0) info.steps = std::clamp (stepsOverride, 1, 50);")
open("engine/Performer.cpp", "w", encoding="utf-8").write(p)
r = open("engine/VioletRenderer.cpp", encoding="utf-8").read()
r = rep(r, "    std::vector<float> sigmas (size_t (std::max (steps, 2)));", "    std::vector<float> sigmas (size_t (std::max (steps, 1) + 1));  // N passos = N+1 sigmas de 1 a 0")
r = rep(r, "    const int evalsPerWindow = 2 * int (sigmas.size() - 1) - 1;", "    const int evalsPerWindow = std::max (1, 2 * int (sigmas.size() - 1) - 1);")
open("engine/VioletRenderer.cpp", "w", encoding="utf-8").write(r)

b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """sub('<span style="position: relative; display: block; width: 110px; height: 24px; margin: 0 12px 0 4px;">', '<span style="position: relative; display: block; width: 80px; height: 24px; margin: 0 12px 0 4px;">')""",
        """sub('<span style="position: relative; display: block; width: 110px; height: 24px; margin: 0 12px 0 4px;">', '<span style="position: relative; display: block; width: 80px; height: 24px; margin: 0 14px 0 24px;">')
sub('<span style="margin: 4px 8px 0; font-size: 11px; color: {{t.secondary}}; line-height: 1.4;">{{qualityHint}}</span>',
    '<span style="margin: 4px 8px 0; font-size: 11px; color: {{t.secondary}}; line-height: 1.4;">{{qualityHint}}</span>'
    '<div style="display: flex; align-items: center; gap: 8px; margin: 6px 8px 0;"><span style="font-size: 12px;">Steps</span>'
    '<div data-slider="renderSteps" style="position: relative; flex-grow: 1; height: 20px; cursor: pointer;">'
    '<span style="position: absolute; left: 0; right: 0; top: 7px; height: 6px; border-radius: 3px; background: {{t.track2}};"></span>'
    '<span style="position: absolute; left: 0; top: 7px; width: {{stepsPct}}%; height: 6px; border-radius: 3px; background: {{t.accent}};"></span>'
    '<span class="lg-thumb" style="position: absolute; left: {{stepsPct}}%; top: -1px; width: 30px; height: 22px; margin-left: -15px; border-radius: 11px;"></span></div>'
    '<span style="width: 22px; text-align: right; font-size: 12px; color: {{t.secondary}}; font-variant-numeric: tabular-nums;">{{stepsText}}</span></div>'
    '<sc-if value="{{isShorts}}"><div style="display: flex; gap: 2px; padding: 2px; margin: 8px 4px 0; border-radius: 9px; background: {{t.fill}};"><sc-for list="{{shortModes}}" as="q">'
    '<button onClick="{{q.pick}}" style="flex: 1 1 0; height: 24px; border: 0; border-radius: 7px; background: {{q.bg}}; box-shadow: {{q.shadow}}; color: {{t.text}}; font-size: 11px; font-weight: {{q.weight}}; cursor: pointer;">{{q.label}}</button>'
    '</sc-for></div></sc-if>')""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

a = open("ui/app.js", encoding="utf-8").read()
a = rep(a, """  const playModes = [
    ['Legato', 'M1 10c3-6 5-6 8 0s5 6 8 0'],
    ['Poly Legato', 'M1 5c3-4 5-4 8 0s5 4 8 0M1 11c3-4 5-4 8 0s5 4 8 0'],
    ['Long Normal', 'M2 7h4M8 7h4M14 7h3']
  ]""", """  const playModes = [
    ['Legato', 'M1 10c3-6 5-6 8 0s5 6 8 0'],
    ['Shorts', 'M2 7h2M7 7h2M12 7h2M16 7h1']
  ]""")
a = rep(a, "  const am = idx('articMode');", """  const shortIdx = idx('shortsMode');
  const shortModes = ['Spiccato', 'Staccato', 'Pizzicato'].map((label, i) => ({ label, pick: () => setV('shortsMode', i), ...seg(shortIdx === i) }));
  const am = idx('articMode');""")
a = rep(a, "    playModes, articModes, qualities, qualityHint: qInfo[q][1], artics,",
        "    playModes, articModes, qualities, qualityHint: qInfo[q][1], artics, shortModes, isShorts: play === 1,\n    stepsPct: P('renderSteps').n * 100, stepsText: String(Math.round(P('renderSteps').v)),")
# chip segue o mouse (a posição do arraste vem por último) e cai só na nota sob o cursor
a = rep(a, "  const dragChip = L.chipDrag ? { ...L.chipDrag, ...palette[L.chipDrag.i] } : null;",
        "  const dragChip = L.chipDrag && L.chipDrag.moved ? { ...palette[L.chipDrag.i], x: L.chipDrag.x, y: L.chipDrag.y } : null;\n  L.noteBoxes = notes.map((n) => ({ i: n.i, x: n.x, y: n.y, w: n.w }));")
a = rep(a, """    const el = document.elementFromPoint(e.clientX, e.clientY), cap = el && el.closest && el.closest('[data-cap]');
    const art = L.chipDrag.i;
    if (cap) { const i = +cap.dataset.cap; const ids = L.sel && L.sel.has(i) ? [...L.sel] : [i]; send({ cmd: 'noteArt', ids, art }); }
    else if (L.sel && L.sel.size) send({ cmd: 'noteArt', ids: [...L.sel], art });""", """    // acha a nota sob o cursor pelas caixas desenhadas (o chip arrastado não atrapalha)
    const r = root.getBoundingClientRect(), s = r.width / 1280, px = (e.clientX - r.left) / s, py = (e.clientY - r.top) / s;
    const hit = (L.noteBoxes || []).find((b) => px >= b.x - 3 && px <= b.x + b.w + 3 && py >= b.y - 6 && py <= b.y + 16);
    const art = L.chipDrag.i;
    if (hit) send({ cmd: 'noteArt', ids: L.sel && L.sel.has(hit.i) ? [...L.sel] : [hit.i], art });
    else if (!L.chipDrag.moved && L.sel && L.sel.size) send({ cmd: 'noteArt', ids: [...L.sel], art });""")
a = rep(a, "  if (chip) { L.chipDrag = { i: +chip.dataset.artchip, x: 0, y: 0, moved: false }; chipMove(e); e.preventDefault(); return; }",
        "  if (chip) { L.chipDrag = { i: +chip.dataset.artchip, x: 0, y: 0, moved: false }; e.preventDefault(); return; }")
# Ctrl + roda = zoom no MIDI, centrado no mouse
a = rep(a, """  if (L.zoom > 1.01) {
    const span = (v1 - v0) / L.zoom, c = S && S.playing ? playhead : v0 + span / 2;""", """  if (L.zoom > 1.01) {
    const span = (v1 - v0) / L.zoom, c = L.zoomAt ?? (S && S.playing ? playhead : v0 + span / 2);""")
a = rep(a, """root.addEventListener('dblclick', (e) => {
  if (!e.target.closest('[data-roll]') || !L.view) return;""", """root.addEventListener('wheel', (e) => {
  if (!e.ctrlKey || !L.view || !e.target.closest('[data-roll],[data-cap]')) return;
  const r = root.getBoundingClientRect(), s = r.width / 1280, px = (e.clientX - r.left) / s, V = L.view;
  L.zoomAt = V.v0 + (px - 280) / 770 * (V.v1 - V.v0);
  L.zoom = Math.max(1, Math.min(32, (L.zoom || 1) * (e.deltaY < 0 ? 1.25 : 0.8)));
  dirty = true; e.preventDefault();
}, { passive: false });
root.addEventListener('dblclick', (e) => {
  if (!e.target.closest('[data-roll]') || !L.view) return;""")
a = rep(a, "    doFit: () => { L.zoom = 1; dirty = true; }, zoom: L.zoom, zoomPct: (L.zoom - 1) / 7 * 100,",
        "    doFit: () => { L.zoom = 1; L.zoomAt = null; dirty = true; }, zoom: Math.min(8, L.zoom), zoomPct: Math.min(100, (L.zoom - 1) / 7 * 100),")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
