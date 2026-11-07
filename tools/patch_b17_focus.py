"""Modo foco: o botão "Compact view" do topo esconde os painéis laterais (Play Mode / Now Playing) e a timeline
ocupa a largura toda. A geometria da timeline sai de números fixos para G (l = esquerda, w = largura)."""
import os
import re
os.chdir(r"C:\Users\TheoH\violino\plugin\ui")

a = open('app.js', encoding='utf-8').read()


def rep(s, o, n, c=1):
    assert s.count(o) == c, (s.count(o), o[:70])
    return s.replace(o, n)


a = rep(a, "const X0 = 280, XW = 736, X1 = X0 + XW;",
        """let X0 = 280, XW = 736, X1 = X0 + XW;
// geometria da timeline: normal (entre os painéis) ou foco (largura toda, painéis escondidos)
const G = { l: 268, w: 790 };
function setGeo(focus) {
  G.l = focus ? 22 : 268; G.w = focus ? 1236 : 790;
  X0 = G.l + 12; XW = G.w - 54; X1 = X0 + XW;
  Object.assign(G, { l2: G.l + 2, l6: G.l + 6, l12: G.l + 12, l84: G.l + 84, l212: G.l + 212, rw: G.w - 38, ow: G.w - 42,
    mx: G.l + G.w - 37, tc: G.l + (G.w - 38) / 2, r: 1280 - G.l - G.w });
}
setGeo(false);""")
a = rep(a, "const tt = timeAt(268 + fx * 790)", "const tt = timeAt(G.l + fx * G.w)")
for line_pat in ["if (x >= 268 && x <= X1 + 2) bars.push", "if (x >= 268 && x <= X1 + 2) { const h", "if (x >= 268 && x <= X1 + 2) grid.push"]:
    a = rep(a, line_pat, line_pat.replace("268", "G.l"))
a = rep(a, "filter(({ p }) => X(p[1]) + 12 >= 268 &&", "filter(({ p }) => X(p[1]) + 12 >= G.l &&")
a = rep(a, "const x = Math.max(268, X(s0) - 12)", "const x = Math.max(G.l, X(s0) - 12)")
a = rep(a, "pts.push((xs + (xe - xs) * u - 268).toFixed(1)", "pts.push((xs + (xe - xs) * u - G.l).toFixed(1)")
a = rep(a, "fShade = fLine + `L${(xs - 268).toFixed(1)},${yt}Z`;", "fShade = fLine + `L${(xs - G.l).toFixed(1)},${yt}Z`;")
a = rep(a, "if (!p[4] && xe + 6 >= 268) fades.push({ i, line: fLine, shade: fShade, hx: Math.max(268,", "if (!p[4] && xe + 6 >= G.l) fades.push({ i, line: fLine, shade: fShade, hx: Math.max(G.l,")
a = rep(a, "map((d) => [X(d[0]) - 268, 62", "map((d) => [X(d[0]) - G.l, 62")
a = rep(a, "    const x = Math.max(268, X(c.start));", "    const x = Math.max(G.l, X(c.start));")
a = rep(a, "x: 280 + i * 70, label: i === 0", "x: G.l + 12 + i * 70, label: i === 0")
a = rep(a, """  const tab = L.tab ?? prefs.tab ?? 'perf';""", """  const tab = L.tab ?? prefs.tab ?? 'perf';
  const focus = !!(L.focusMode ?? prefs.focus) && tab === 'perf';  // só a Performance usa o modo foco
  setGeo(focus);""")
a = rep(a, "    t, dark, light: !dark, toggleTheme: () => pref('dark', !dark),",
        """    t, dark, light: !dark, toggleTheme: () => pref('dark', !dark), G, panelsShow: focus ? 'none' : 'flex',
    toggleFocus: () => pref('focusMode', !(L.focusMode ?? prefs.focus)), focusOn: focus, focusBg: focus ? t.accentSoft : 'transparent',""")
open('app.js', 'w', encoding='utf-8').write(a)

e = open('edit.js', encoding='utf-8').read()
e = rep(e, "L.zoomAt = L.atT = d.c0 + dx / 748 * (F.b - F.a);", "L.zoomAt = L.atT = d.c0 + dx / G.ow * (F.b - F.a);")
e = rep(e, "    vx: (v0 - fullA) / full * 748, vw: Math.max(10, (v1 - v0) / full * 748),", "    vx: (v0 - fullA) / full * G.ow, vw: Math.max(10, (v1 - v0) / full * G.ow),")
e = rep(e, "blocks: phrases.map((p) => ({ x: (p[0] - fullA) / full * 748, w: Math.max(2, (p[1] - p[0]) / full * 748),",
        "blocks: phrases.map((p) => ({ x: (p[0] - fullA) / full * G.ow, w: Math.max(2, (p[1] - p[0]) / full * G.ow),")
e = rep(e, "const xa = Math.max(268, X(c.a))", "const xa = Math.max(G.l, X(c.a))")
open('edit.js', 'w', encoding='utf-8').write(e)

b = open('build_ui.py', encoding='utf-8').read()
i = b.index('tpl = tpl.replace(perf, """'); j = b.index('# ---- aba Effects: Mix Style')
blk = b[i:j]
for num, hole in [('268', 'G.l'), ('280', 'G.l12'), ('790', 'G.w'), ('752', 'G.rw'), ('748', 'G.ow'), ('1021', 'G.mx'), ('644', 'G.tc'),
                  ('274', 'G.l6'), ('270', 'G.l2'), ('352', 'G.l84'), ('480', 'G.l212')]:
    blk = re.sub(r'(?<![\d.])' + num + r'px', '{{' + hole + '}}px', blk)
blk = blk.replace('right: 222px', 'right: {{G.r}}px')
blk = blk.replace('width="790" height="64" viewBox="0 0 790 64"', 'width="{{G.w}}" height="64" viewBox="0 0 {{G.w}} 64"')
blk = blk.replace('width="752" height="232" viewBox="0 0 752 232"', 'width="{{G.rw}}" height="232" viewBox="0 0 {{G.rw}} 232"')
b = b[:i] + blk + b[j:]
# painéis laterais e barra de articulações acompanham; o botão "Compact view" liga o modo foco
b = b.replace('''sub("top: 64px; bottom: 160px; width: 248px;", "top: 64px; bottom: 216px; width: 248px;")''',
              '''sub("top: 64px; bottom: 160px; width: 248px;", "top: 64px; bottom: 216px; width: 248px; display: {{panelsShow}};")''', 1)
b = b.replace('''sub("top: 64px; bottom: 160px; width: 202px;", "top: 64px; bottom: 216px; width: 202px;")''',
              '''sub("top: 64px; bottom: 160px; width: 202px;", "top: 64px; bottom: 216px; width: 202px; display: {{panelsShow}};")
sub('style="position: absolute; left: 268px; right: 222px; top: 64px; height: 44px;', 'style="position: absolute; left: {{G.l}}px; right: {{G.r}}px; top: 64px; height: 44px;')
sub('<button aria-label="Compact view" style="', '<button onClick="{{toggleFocus}}" aria-pressed="{{focusOn}}" title="Focus: hide the side panels and widen the timeline" aria-label="Compact view" style="background: {{focusBg}} !important; ')''', 1)
open('build_ui.py', 'w', encoding='utf-8').write(b)
print('ok')
