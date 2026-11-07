import os
os.chdir(r"C:\Users\TheoH\violino")
def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)
patch('plugin/ui/app.js', [
    ("  if (v1 - v0 < 6) v1 = v0 + 6;\n  const fullA = v0, fullB = v1;",
     "  if (v1 - v0 < 6) v1 = v0 + 6;\n  if (S && S.internalPlay && playhead > v1 - 1) v1 = playhead + 4;  // tocando além do último take: a timeline cresce junto\n  const fullA = v0, fullB = v1;"),
    ("    const c = L.zoomAt ?? (S && S.playing ? playhead : v0 + span / 2);",
     "    const c = L.zoomAt ?? (S && (S.playing || S.internalPlay) ? playhead : v0 + span / 2);"),
])
patch('plugin/ui/edit.js', [
    ("// ------------------------------------------------------------------ caixa de seleção, régua, visão geral, BPM",
     """// ------------------------------------------------------------------ Cycle (faixa amarela na régua)
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

// ------------------------------------------------------------------ caixa de seleção, régua, visão geral, BPM"""),
    ("  const bd = e.target.closest('[data-bpmdrag=\"true\"]');",
     """  const cy = e.target.closest('[data-cyc]');
  if (cy && L.view && e.button === 0) {
    const r = cy.getBoundingClientRect(), x = e.clientX - r.left, c = cycleState();
    L.cycDrag = { mode: x < 7 ? 'l' : x > r.width - 7 ? 'r' : 'm', t0: timeAt(cpt(e).x), a: c.a, b: c.b };
    cy.setPointerCapture(e.pointerId); e.preventDefault(); e.stopPropagation(); return;
  }
  const bd = e.target.closest('[data-bpmdrag="true"]');"""),
    ("addEventListener('pointermove', (e) => {\n  if (L.bpmDrag) {",
     """addEventListener('pointermove', (e) => {
  if (L.cycDrag) {
    const d = L.cycDrag, dt = timeAt(cpt(e).x) - d.t0, g = snapStep() || beatSec() / 4;
    const sn = (t) => Math.max(0, Math.round(t / g) * g);
    let a = d.a, b = d.b;
    if (d.mode === 'l') a = Math.min(sn(d.a + dt), b - g); else if (d.mode === 'r') b = Math.max(sn(d.b + dt), a + g); else { a = sn(d.a + dt); b = a + (d.b - d.a); }
    L.cycOv = { a, b }; send({ cmd: 'cycle', a, b }); dirty = true;
  }
  if (L.bpmDrag) {"""),
    ("addEventListener('pointerup', () => {\n", "addEventListener('pointerup', () => {\n  if (L.cycDrag) { L.cycDrag = null; setTimeout(() => { L.cycOv = null; dirty = true; }, 400); }\n"),
    ("    doPause: () => send({ cmd: 'pause' }),",
     """    doPause: () => send({ cmd: 'pause' }), toggleCycle, cycBg: cycleState().on ? '#FFD60A' : 'transparent', cycFg: cycleState().on ? '#1D1D1F' : t.text,
    cyc: (() => { const c = cycleState(); if (!(c.b > c.a + 0.05)) return null; const xa = Math.max(268, X(c.a)), xb = Math.min(X1 + 2, X(c.b)); return xb > xa ? { x: xa, w: xb - xa, bg: c.on ? 'rgba(255,214,10,0.85)' : (dark ? 'rgba(255,255,255,0.18)' : 'rgba(0,0,0,0.15)') } : null; })(),"""),
])
patch('tools/b4_transport.txt', [
    ("""title="Stop (back to where play started · twice: to the start)" class="tpb" style="width: 34px; padding: 0;"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3h8v8H3z" fill="currentColor"></path></svg></button>""",
     """title="Stop (back to where play started · twice: to the start)" class="tpb" style="width: 34px; padding: 0;"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3h8v8H3z" fill="currentColor"></path></svg></button>
      <button onClick="{{toggleCycle}}" aria-label="Cycle" title="Cycle: loop the yellow range on the ruler (drag its ends or middle)" class="tpb" style="width: 34px; padding: 0; background: {{cycBg}}; color: {{cycFg}};"><svg width="15" height="13" viewBox="0 0 16 14" aria-hidden="true"><path d="M3 6a4 4 0 014-4h4M13 8a4 4 0 01-4 4H5M9.5 0.5L11.5 2 9.5 3.5M6.5 10.5L4.5 12 6.5 13.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"></path></svg></button>"""),
    ('aria-label="Play" title="Play from the cursor (Space in the Standalone)"', 'aria-label="Play" title="Play from the cursor · press again to pause (Space in the Standalone)"'),
])
b = open('plugin/ui/build_ui.py', encoding='utf-8').read()
i = b.index('TRANSPORT = """'); j = b.index('"""', i + 15)
b = b[:i] + 'TRANSPORT = """' + open('tools/b4_transport.txt', encoding='utf-8').read() + b[j:]
o = """<div data-ruler="1" title="Click: move the cursor · drag up/down: zoom · drag sideways: scroll" """
assert b.count(o) == 1
k = b.index(o); e = b.index('</div>', k) + 6
b = b[:e] + """
      <sc-if value="{{cyc}}"><span data-cyc="1" title="Cycle range · drag the ends to resize, the middle to move" style="position: absolute; left: {{cyc.x}}px; top: 129px; width: {{cyc.w}}px; height: 7px; border-radius: 3px; background: {{cyc.bg}}; cursor: ew-resize; z-index: 4;"></span></sc-if>""" + b[e:]
open('plugin/ui/build_ui.py', 'w', encoding='utf-8').write(b)
print('ok')
