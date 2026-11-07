"""Score editável: ferramentas (seleção, lápis, borracha), figuras, ponto, ♯/♭, quadradinho azul do lápis."""
import os
os.chdir(r"C:\Users\TheoH\violino")
p = 'plugin/ui/score.js'
a = open(p, encoding='utf-8').read()


def rep(o, n):
    global a
    assert a.count(o) == 1, (a.count(o), o[:60])
    a = a.replace(o, n)


rep("""  const cap = ((S && S.cap) || []).slice().sort((a, b) => a[0] - b[0]);""",
    """  const cap = ((S && S.cap) || []).map((c, i) => [...c, i]).sort((a, b) => a[0] - b[0]);  // c[5] = índice real (para editar)
  const sel = L.sel || new Set(), drg = L.scDrag && L.scDrag.moved ? L.scDrag : null, blue = '#0A84FF';
  const boxes = [];""")
rep("""  for (const n of cap) {
    const rel = n[0] - t0, barIdx = Math.floor(rel / barLen) - page * perPage;""",
    """  L.scoreGeo = { t0, page, perPage, barLen, q16, barW };
  for (const n0 of cap) {
    // arrastando: as notas selecionadas aparecem já no lugar novo (altura pela pauta, tempo em semicolcheias)
    let n = n0;
    if (drg && sel.has(n0[5])) {
      const [st0, sh0] = STEP[((n0[2] % 12) + 12) % 12], s0 = Math.floor(n0[2] / 12) * 7 + st0;
      n = [n0[0] + drg.d16 * q16, n0[1] + drg.d16 * q16, stepToMidi(s0 + drg.dSteps) + sh0, n0[3], n0[4], n0[5]];
    }
    const col = sel.has(n0[5]) ? blue : ink;
    const rel = n[0] - t0, barIdx = Math.floor(rel / barLen) - page * perPage;""")
rep("""    for (let s = 35; s >= stepNum; s -= 2) paths.push""", """    boxes.push({ i: n0[5], x, y });
    for (let s = 35; s >= stepNum; s -= 2) paths.push""")
rep("""    paths.push(head(x, y, base <= 4, ink));
    if (dot) paths.push({ d: `M${x + 9},${y - 1}a1.6,1.6 0 1,0 0.1,0`, fill: ink, stroke: ink, w: 1 });
    if (sharp) texts.push({ t: '♯', x: x - 15, y: y + 5, s: 15, c: ink,""",
    """    paths.push(head(x, y, base <= 4, col));
    if (dot) paths.push({ d: `M${x + 9},${y - 1}a1.6,1.6 0 1,0 0.1,0`, fill: col, stroke: col, w: 1 });
    if (sharp) texts.push({ t: '♯', x: x - 15, y: y + 5, s: 15, c: col,""")
rep("""V${sy2.toFixed(1)}`, fill: 'none', stroke: ink, w: 1.3 });""", """V${sy2.toFixed(1)}`, fill: 'none', stroke: col, w: 1.3 });""")
rep("""`M${sx},${fy}c6,-4 9,-8 5,-15`, fill: 'none', stroke: ink, w: 1.4 });""", """`M${sx},${fy}c6,-4 9,-8 5,-15`, fill: 'none', stroke: col, w: 1.4 });""")
rep("""  const go = (d) => () => {""", """  L.scoreBoxes = boxes;
  // quadradinho azul do lápis: onde a nota vai entrar
  const tool = L.scoreTool || 'select', dur = L.scoreDur || 4, dotOn = !!L.scoreDot;
  const hv = L.scoreHover && tool === 'pencil' ? L.scoreHover : null;
  const tb = (label, title, on, pick) => ({ label, title, pick, bg: on ? '#3b2a1a' : 'rgba(255,255,255,0.35)', fg: on ? '#F3E6C8' : '#3b2a1a' });
  const scoreTools = [
    tb('↖', 'Select: click a note, drag it up/down (pitch) or sideways (time) · Delete removes', tool === 'select', () => { L.scoreTool = 'select'; dirty = true; }),
    tb('✎', 'Pencil: click on the staff to write a note', tool === 'pencil', () => { L.scoreTool = 'pencil'; dirty = true; }),
    tb('⌫', 'Eraser: click a note to remove it', tool === 'erase', () => { L.scoreTool = 'erase'; dirty = true; })];
  const setDur = (d) => () => { L.scoreDur = d; scoreApplyDur(); dirty = true; };
  const scoreDurs = [[16, '𝅝', 'Whole'], [8, '𝅗𝅥', 'Half'], [4, '♩', 'Quarter'], [2, '♪', 'Eighth'], [1, '𝅘𝅥𝅯', 'Sixteenth']]
    .map(([d, label, name]) => tb(label, name + ' (new notes; also sets the selected notes)', dur === d, setDur(d)));
  scoreDurs.push(tb('·', 'Dotted', dotOn, () => { L.scoreDot = !dotOn; scoreApplyDur(); dirty = true; }));
  const acc = (d) => () => { const ids = [...(L.sel || [])]; if (ids.length) { send({ cmd: 'noteTool', ids, op: 'transpose', arg: d }); const c = S.cap[ids[0]]; if (c) previewNote(c[2] + d); } };
  const scoreAcc = [tb('♯', 'Sharp: selected notes up a semitone', false, acc(1)), tb('♭', 'Flat: selected notes down a semitone', false, acc(-1))];
  const go = (d) => () => {""")
rep("""  return { scorePaths: paths, scoreTexts: texts, scorePrev: go(-1), scoreNext: go(1), scorePages };""",
    """  return { scorePaths: paths, scoreTexts: texts, scorePrev: go(-1), scoreNext: go(1), scorePages, scoreTools, scoreDurs, scoreAcc,
    scoreGhost: hv, scoreCursor: tool === 'pencil' ? 'crosshair' : tool === 'erase' ? 'not-allowed' : 'default' };""")
a += open('tools/b11_score_add.js', encoding='utf-8').read()
open(p, 'w', encoding='utf-8').write(a)

b = open('plugin/ui/build_ui.py', encoding='utf-8').read()
o = '''      <button onClick="{{scorePrev}}" aria-label="Previous page"'''
assert b.count(o) == 1
b = b.replace(o, '''      <div data-score="1" style="position: absolute; left: 0; top: 104px; width: 766px; height: 420px; cursor: {{scoreCursor}};"></div>
      <sc-if value="{{scoreGhost}}"><span style="position: absolute; left: {{scoreGhost.x}}px; top: {{scoreGhost.y}}px; width: 12px; height: 10px; border-radius: 2px; background: rgba(10,132,255,0.35); border: 1.5px solid #0A84FF; pointer-events: none;"></span></sc-if>
      <div aria-label="Score tools" style="position: absolute; right: 14px; top: 12px; display: flex; gap: 3px; align-items: center;">
        <sc-for list="{{scoreTools}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}};">{{b.label}}</button></sc-for>
        <span style="width: 8px;"></span>
        <sc-for list="{{scoreDurs}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}}; font-family: 'Segoe UI Symbol', serif; font-size: 15px;">{{b.label}}</button></sc-for>
        <span style="width: 8px;"></span>
        <sc-for list="{{scoreAcc}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}}; font-family: 'Segoe UI Symbol', serif; font-size: 15px;">{{b.label}}</button></sc-for>
      </div>
''' + o)
o2 = ".pmi{{display:flex;"
assert b.count(o2) == 1
b = b.replace(o2, ".scb{{width:28px;height:28px;padding:0;border-radius:8px;border:1px solid rgba(59,42,26,0.3);cursor:pointer;font-family:Georgia,serif;font-size:14px;line-height:1}}\n.scb:hover{{filter:brightness(1.1)}}\n" + o2)
open('plugin/ui/build_ui.py', 'w', encoding='utf-8').write(b)
print('ok')
