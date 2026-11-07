import os
os.chdir(r"C:\Users\TheoH\violino")
def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)
patch('plugin/ui/app.js', [
    # Ctrl + arrastar na nota = velocity (Alt fica para mover sem grade, como no Ableton)
    ("    if (e.altKey) {  // Alt + arrastar para cima/baixo: velocity", "    if (e.ctrlKey) {  // Ctrl + arrastar para cima/baixo: velocity"),
    ("    nd.dt = snapDt(nd.resize ? nd.a1 : nd.a0, dx / XW * (V.v1 - V.v0)); nd.dp",
     "    nd.dt = e.altKey ? dx / XW * (V.v1 - V.v0) : snapDt(nd.resize ? nd.a1 : nd.a0, dx / XW * (V.v1 - V.v0));  // Alt: sem grade enquanto segura\n    nd.dp"),
    ("md.dt = snapDt(c0 ? c0[0] : 0, (e.clientX - md.x) / pt.s / XW * (V.v1 - V.v0));",
     "md.dt = e.altKey ? (e.clientX - md.x) / pt.s / XW * (V.v1 - V.v0) : snapDt(c0 ? c0[0] : 0, (e.clientX - md.x) / pt.s / XW * (V.v1 - V.v0));"),
    ("    rd.dt = snapDt(rd.mode === 'r' ? rp[1] : rp[0], (e.clientX - rd.x) / pt.s / XW * (V.v1 - V.v0));\n    rd.stretch = rd.stretch || e.altKey;",
     "    const rawDt = (e.clientX - rd.x) / pt.s / XW * (V.v1 - V.v0);\n    rd.dt = e.altKey ? rawDt : snapDt(rd.mode === 'r' ? rp[1] : rp[0], rawDt);\n    rd.stretch = rd.mode !== 'move' && (rd.stretch || e.altKey);"),
    ("    if (nd.moved) { markMove(); dirty = true; }",
     "    if (nd.moved) { if (e.altKey && snapStep()) L.velTip = { x: cpt(e).x + 14, y: cpt(e).y - 22, text: 'Free move (no grid)' }; else if (L.velTip && !L.velDrag) L.velTip = null; markMove(); dirty = true; }"),
])
patch('plugin/ui/app.js', [
    ("      L.dragHold = nd; hold();\n    }\n    L.noteDrag = null; dirty = true;", "      L.dragHold = nd; hold();\n    }\n    L.noteDrag = null; L.velTip = null; dirty = true;"),
])
patch('plugin/ui/edit.js', [
    ("  if (mod && k === 'KeyZ') { send({ cmd: e.shiftKey ? 'redo' : 'undo' }); L.sel = new Set(); return done(); }\n  if (mod && k === 'KeyY') { send({ cmd: 'redo' }); L.sel = new Set(); return done(); }",
     "  if (mod && k === 'KeyZ') { undoRedo(e.shiftKey ? 'redo' : 'undo'); return done(); }\n  if (mod && k === 'KeyY') { undoRedo('redo'); return done(); }"),
    ("    doUndo: () => { send({ cmd: 'undo' }); L.sel = new Set(); }, doRedo: () => { send({ cmd: 'redo' }); L.sel = new Set(); },",
     "    doUndo: () => undoRedo('undo'), doRedo: () => undoRedo('redo'),\n    toggleMetro: () => send({ cmd: 'metro' }), metroBg: S && S.metro ? t.accent : 'transparent', metroFg: S && S.metro ? '#FFFFFF' : t.text,"),
    ("function selAll() {", "// desfazer/refazer: limpa a seleção e tudo que estava segurado na tela (os índices das notas mudam)\nfunction undoRedo(cmd) { send({ cmd }); L.sel = new Set(); L.takeSel = false; releaseHold(); L.velTouched = new Set(); dirty = true; }\nfunction selAll() {"),
    ("    { label: 'Undo', key: 'Ctrl+Z', pick: () => send({ cmd: 'undo' }), disabled: !(S && S.canUndo) },\n    { label: 'Redo', key: 'Ctrl+Shift+Z', pick: () => send({ cmd: 'redo' }), disabled: !(S && S.canRedo) },",
     "    { label: 'Undo', key: 'Ctrl+Z', pick: () => undoRedo('undo'), disabled: !(S && S.canUndo) },\n    { label: 'Redo', key: 'Ctrl+Shift+Z', pick: () => undoRedo('redo'), disabled: !(S && S.canRedo) },"),
])
patch('tools/b4_transport.txt', [
    ("""      <span style="font-size: 12px; font-weight: 600; color: {{t.secondary}}; padding: 0 4px;">4 / 4</span>""",
     """      <span style="font-size: 12px; font-weight: 600; color: {{t.secondary}}; padding: 0 4px;">4 / 4</span>
      <sc-if value="{{bpmEdit}}"><button onClick="{{toggleMetro}}" class="tpb" aria-label="Metronome" title="Metronome (Standalone): clicks on every beat while playing" style="width: 34px; padding: 0; background: {{metroBg}}; color: {{metroFg}};"><svg width="14" height="15" viewBox="0 0 14 15" aria-hidden="true"><path d="M5 1.5h4l3 12H2z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"></path><path d="M7 10L11 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"></path></svg></button></sc-if>"""),
])
b = open('plugin/ui/build_ui.py', encoding='utf-8').read()
i = b.index('TRANSPORT = """'); j = b.index('"""', i + 15)
b = b[:i] + 'TRANSPORT = """' + open('tools/b4_transport.txt', encoding='utf-8').read() + b[j:]
b = b.replace("right-click: menu · Alt+drag / wheel on selected: velocity", "right-click: menu · hold Alt: no grid · Ctrl+drag / wheel: velocity")
open('plugin/ui/build_ui.py', 'w', encoding='utf-8').write(b)
print('ok')
