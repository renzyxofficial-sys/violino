"""Bloco 2 / UI: barra de ferramentas da seleção (transpose, quantize, humanize, legato, reverse, x2 /2,
split, fit to scale, velocity), split de take no cursor, alça de fade in por trecho, lápis na Dynamics."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\ui")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


b = open("build_ui.py", encoding="utf-8").read()
# fade in: sombra + alça arrastável no começo de cada trecho; ✂ split no cursor
b = rep(b, """        <sc-if value="{{r.actions}}">""", """        <span style="position: absolute; left: {{r.fadeL}}px; top: 172px; width: {{r.fadeW}}px; height: 262px; background: linear-gradient(to right, rgba(0,0,0,0.5), rgba(0,0,0,0)); pointer-events: none;"></span>
        <span data-fade="{{r.i}}" title="Drag to set the fade in of this phrase ({{r.fadeText}})" style="position: absolute; left: {{r.fadeH}}px; top: 168px; width: 12px; height: 12px; margin-left: -6px; border-radius: 6px; background: #FFFFFF; box-shadow: 0 1px 4px rgba(0,0,0,0.5); cursor: ew-resize; z-index: 7;"></span>
        <sc-if value="{{r.actions}}">""")
b = rep(b, """            <button class="lg-pill" onClick="{{r.doDelete}}" title="Delete this take (notes and render)\"""",
        """            <button class="lg-pill" onClick="{{doSplitTake}}" title="Split the take at the cursor" style="height: 22px; min-width: 26px; padding: 0 7px; border: 0; border-radius: 11px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: pointer;">✂</button>
            <button class="lg-pill" onClick="{{r.doDelete}}" title="Delete this take (notes and render)\"""")
# barra de ferramentas da seleção (no lugar da linha de resumo)
b = rep(b, """      <span style="position: absolute; left: 280px; top: 606px; font-size: 11px; color: {{t.tertiary}};">{{summary}}</span>""",
        """      <sc-if value="{{noSel}}"><span style="position: absolute; left: 280px; top: 606px; font-size: 11px; color: {{t.tertiary}};">{{summary}}</span></sc-if>
      <sc-if value="{{hasSel}}">
        <div style="position: absolute; left: 270px; top: 598px; right: 222px; display: flex; align-items: center; gap: 3px; flex-wrap: nowrap; z-index: 8;">
          <span style="font-size: 11px; font-weight: 600; color: {{t.secondary}}; margin-right: 4px; white-space: nowrap;">{{selText}}</span>
          <sc-for list="{{tools}}" as="b">
            <button class="lg-pill" onClick="{{b.pick}}" title="{{b.title}}" style="height: 22px; padding: 0 7px; border: 0; border-radius: 11px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap;">{{b.label}}</button>
          </sc-for>
          <span style="font-size: 11px; color: {{t.secondary}}; margin-left: 6px;">Vel</span>
          <div data-velslider="1" style="position: relative; width: 70px; height: 18px; cursor: pointer;">
            <span style="position: absolute; left: 0; right: 0; top: 6px; height: 6px; border-radius: 3px; background: {{t.track2}};"></span>
            <span style="position: absolute; left: 0; top: 6px; width: {{velPct}}%; height: 6px; border-radius: 3px; background: {{t.accent}};"></span>
          </div>
          <span style="font-size: 11px; color: {{t.secondary}}; width: 22px;">{{velText}}</span>
        </div>
      </sc-if>""")
# lápis na Dynamics
b = rep(b, """      <svg style="position: absolute; left: 268px; top: 474px;" width="790" height="64" viewBox="0 0 790 64" aria-hidden="true">""",
        """      <span style="position: absolute; left: 352px; top: 456px; font-size: 10px; color: {{t.tertiary}};">✎ draw on the curve to change it</span>
      <button onClick="{{dynClear}}" class="lg-pill" title="Remove what you drew" style="position: absolute; left: 520px; top: 452px; height: 18px; padding: 0 8px; border: 0; border-radius: 9px; color: {{t.text}}; font-size: 10px; font-weight: 600; cursor: pointer;">Reset</button>
      <div data-dynlane="1" style="position: absolute; left: 268px; top: 474px; width: 790px; height: 64px; cursor: crosshair; z-index: 5;"></div>
      <svg style="position: absolute; left: 268px; top: 474px; pointer-events: none;" width="790" height="64" viewBox="0 0 790 64" aria-hidden="true">
        <polyline points="{{dynDraft}}" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"></polyline>""")
open("build_ui.py", "w", encoding="utf-8").write(b)

a = open("app.js", encoding="utf-8").read()
a = rep(a, """      doUnrender: () => send({ cmd: 'unrender', phrase: i }), doDelete: () => send({ cmd: 'deleteTake', phrase: i }) };""",
"""      doUnrender: () => send({ cmd: 'unrender', phrase: i }), doDelete: () => send({ cmd: 'deleteTake', phrase: i }),
      fadeL: Math.max(268, X(p[0] - 0.06)), fadeW: Math.max(0, (p[7] || 0) / (v1 - v0) * 770), fadeH: Math.max(268, X(p[0] - 0.06)) + Math.max(0, (p[7] || 0) / (v1 - v0) * 770) + 6,
      fadeText: (p[7] || 0) > 0 ? Math.round((p[7] || 0) * 1000) + ' ms' : 'off' };""")
a = rep(a, "    hasNotes: capIn.length > 0, palette, dragChip, grid, rows, hscroll,", """    hasNotes: capIn.length > 0, palette, dragChip, grid, rows, hscroll,
    ...toolVals(capIn), doSplitTake: () => send({ cmd: 'splitTake', t: (S && S.internalPos) || 0 }),
    dynClear: () => send({ cmd: 'dynClear' }), dynDraft: (L.dynPts || []).map((q) => (X(q[0]) - 268).toFixed(1) + ',' + (62 - (q[1] - 20) / 104 * 58).toFixed(1)).join(' '),""")
a = rep(a, """function previewNote(p) {""", """// barra de ferramentas da seleção (estilo Pitch & Time do Ableton)
const SCALES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
function toolVals(capIn) {
  const sel = L.sel ? [...L.sel] : [];
  const tool = (label, title, op, arg, extra) => ({ label, title, pick: () => { send({ cmd: 'noteTool', ids: sel, op, arg, ...(extra || {}) }); if (op === 'transpose' && capIn[sel[0]]) previewNote(capIn[sel[0]][2] + arg); } });
  const root = L.scaleRoot || 0, mode = L.scaleMode || 0;
  const vels = sel.map((i) => (capIn[i] ? capIn[i][4] : 90)), vel = vels.length ? Math.round(vels.reduce((x, y) => x + y, 0) / vels.length) : 90;
  return {
    hasSel: sel.length > 0, noSel: sel.length === 0, selText: sel.length + (sel.length > 1 ? ' notes' : ' note'),
    velPct: vel / 127 * 100, velText: String(vel),
    tools: [tool('−12', 'Octave down', 'transpose', -12), tool('−1', 'Semitone down', 'transpose', -1), tool('+1', 'Semitone up', 'transpose', 1), tool('+12', 'Octave up', 'transpose', 12),
      tool('Q 1/16', 'Quantize to 1/16', 'quantize', 0.25), tool('Q 1/8', 'Quantize to 1/8', 'quantize', 0.5), tool('Humanize', 'Random timing ±15 ms and velocity', 'humanize', 15),
      tool('Legato', 'Each note lasts until the next', 'legato', 0), tool('Reverse', 'Reverse the selection in time', 'reverse', 0),
      tool('×2', 'Twice as long', 'stretch', 2), tool('÷2', 'Half as long', 'stretch', 0.5), tool('Split', 'Split each note in two', 'split', 0),
      { label: 'Fit ' + SCALES[root] + (mode ? ' min' : ' maj'), title: 'Move notes to the nearest note of the scale (click again to apply; right-click the key to change it)', pick: () => send({ cmd: 'noteTool', ids: sel, op: 'scale', arg: root, mode }) },
      { label: '⟳ key', title: 'Change the scale key', pick: () => { L.scaleRoot = (root + (mode ? 1 : 0)) % 12; L.scaleMode = mode ? 0 : 1; dirty = true; } },
      { label: 'Delete', title: 'Delete the selected notes', pick: () => { send({ cmd: 'noteDel', ids: sel }); L.sel = new Set(); dirty = true; } }]
  };
}

function previewNote(p) {""")
# interações: fade, lápis, velocity
a = rep(a, """  const dm = e.target.closest('[data-dragmidi]');""", """  const fh = e.target.closest('[data-fade]');
  if (fh && L.view) { L.fadeDrag = { i: +fh.dataset.fade, x: e.clientX, sec0: ((S && S.phrases[+fh.dataset.fade]) || [])[7] || 0 }; e.preventDefault(); return; }
  const dl = e.target.closest('[data-dynlane]');
  if (dl && L.view) { L.dynPts = []; L.dynEl = dl; dynAdd(e); e.preventDefault(); return; }
  const vs = e.target.closest('[data-velslider]');
  if (vs && L.sel && L.sel.size) { L.velEl = vs; velAt(e); e.preventDefault(); return; }
  const dm = e.target.closest('[data-dragmidi]');""")
a = rep(a, """function scrollTo(e) {""", """function dynAdd(e) {
  const r = L.dynEl.getBoundingClientRect(), V = L.view, fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
  const tt = V.v0 + (fx * 790 - 12) / 770 * (V.v1 - V.v0), cc = Math.max(20, Math.min(124, 20 + (62 - fy * 64) / 58 * 104));
  L.dynPts.push([tt, cc]); dirty = true;
}
function velAt(e) {
  const r = L.velEl.getBoundingClientRect(), v = Math.round(Math.max(1, Math.min(127, (e.clientX - r.left) / r.width * 127)));
  L.velPending = v;
}
function scrollTo(e) {""")
a = rep(a, """  if (L.scrollDrag) scrollTo(e);""", """  if (L.scrollDrag) scrollTo(e);
  if (L.dynPts && L.dynEl) dynAdd(e);
  if (L.velEl) velAt(e);
  if (L.fadeDrag) { const s = root.getBoundingClientRect().width / 1280, V = L.view; L.fadeDrag.sec = Math.max(0, L.fadeDrag.sec0 + (e.clientX - L.fadeDrag.x) / s / 770 * (V.v1 - V.v0)); }""")
a = rep(a, """  L.scrollDrag = null;
  L.pan = null;""", """  L.scrollDrag = null;
  L.pan = null;
  if (L.dynPts && L.dynEl) { if (L.dynPts.length > 1) send({ cmd: 'dynDraw', pts: L.dynPts }); L.dynPts = null; L.dynEl = null; dirty = true; }
  if (L.velEl) { if (L.velPending) send({ cmd: 'noteTool', ids: [...L.sel], op: 'velocity', arg: L.velPending }); L.velEl = null; L.velPending = null; }
  if (L.fadeDrag) { if (L.fadeDrag.sec !== undefined) send({ cmd: 'fade', phrase: L.fadeDrag.i, sec: L.fadeDrag.sec }); L.fadeDrag = null; }""")
open("app.js", "w", encoding="utf-8").write(a)
print("ok")
