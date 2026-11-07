"""v0.5: aba Score (folha de papel antigo) + score.js no bundle."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\ui")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:80])
    return s.replace(old, new)


PAPER = ("url(&quot;data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'>"
         "<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/>"
         "<feColorMatrix values='0 0 0 0 0.35 0 0 0 0 0.25 0 0 0 0 0.12 0 0 0 0.10 0'/></filter>"
         "<rect width='300' height='300' filter='url(%23n)'/></svg>&quot;), "
         "radial-gradient(ellipse at 50% 40%, #F3E6C8 0%, #E9D6AE 60%, #D9BF8C 100%)")

b = open("build_ui.py", encoding="utf-8").read()
b = rep(b, """# ---- transporte: Play/Stop e Lock MIDI""", '''# ---- aba Score
sc_block = """  <!-- Score: partitura numa folha antiga -->
  <sc-if value="{{isScore}}">
    <div style="position: absolute; left: 280px; top: 124px; width: 766px; height: 580px; border-radius: 6px; overflow: hidden; background: ''' + PAPER + '''; box-shadow: 0 8px 30px rgba(0,0,0,0.35), inset 0 0 60px rgba(120,80,30,0.35);">
      <svg width="766" height="580" viewBox="0 0 766 580" style="position: absolute; left: 0; top: 0;">
        <sc-for list="{{scorePaths}}" as="p"><path d="{{p.d}}" fill="{{p.fill}}" stroke="{{p.stroke}}" stroke-width="{{p.w}}" stroke-linecap="round"></path></sc-for>
        <sc-for list="{{scoreTexts}}" as="x"><text x="{{x.x}}" y="{{x.y}}" fill="{{x.c}}" font-size="{{x.s}}" font-weight="{{x.w}}" text-anchor="{{x.a}}" style="font-family: {{x.f}};">{{x.t}}</text></sc-for>
      </svg>
      <button onClick="{{scorePrev}}" aria-label="Previous page" style="position: absolute; left: 14px; bottom: 14px; width: 30px; height: 30px; border-radius: 15px; border: 1px solid rgba(59,42,26,0.35); background: rgba(255,255,255,0.25); color: #3b2a1a; cursor: pointer;">‹</button>
      <button onClick="{{scoreNext}}" aria-label="Next page" style="position: absolute; right: 14px; bottom: 14px; width: 30px; height: 30px; border-radius: 15px; border: 1px solid rgba(59,42,26,0.35); background: rgba(255,255,255,0.25); color: #3b2a1a; cursor: pointer;">›</button>
    </div>
  </sc-if>

"""
tpl = tpl.replace("  <!-- Keyboard: content layer, bottom -->", sc_block + "  <!-- Keyboard: content layer, bottom -->", 1)

# ---- transporte: Play/Stop e Lock MIDI''')
b = rep(b, """js = js.replace(init, open(os.path.join(HERE, "fx.js"), encoding="utf-8").read() + "\\n" + init)""",
        """js = js.replace(init, open(os.path.join(HERE, "fx.js"), encoding="utf-8").read() + "\\n" + open(os.path.join(HERE, "score.js"), encoding="utf-8").read() + "\\n" + init)""")
open("build_ui.py", "w", encoding="utf-8").write(b)

a = open("app.js", encoding="utf-8").read()
a = rep(a, "  const tabs = [['perf', 'Performance'], ['inst', 'Instrument'], ['fx', 'Effects']].map(",
        "  const tabs = [['perf', 'Performance'], ['inst', 'Instrument'], ['fx', 'Effects'], ['score', 'Score']].map(")
a = rep(a, "    tabs, isPerf: tab === 'perf', isInst: tab === 'inst', isFx: tab === 'fx',",
        "    tabs, isPerf: tab === 'perf', isInst: tab === 'inst', isFx: tab === 'fx', isScore: tab === 'score',")
a = rep(a, "    ...fxVals(t),", "    ...fxVals(t),\n    ...(tab === 'score' ? scoreVals(t) : {}),")
open("app.js", "w", encoding="utf-8").write(a)
print("ok")
