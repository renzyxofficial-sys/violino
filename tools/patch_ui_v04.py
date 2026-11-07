"""UI v0.4: aba Effects nova (fileira de módulos + palco do editor) e fx.js no bundle."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\ui")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:80])
    return s.replace(old, new)


FX = '''  <!-- Effects: Mix Style, fileira de módulos e o editor do módulo escolhido -->
  <sc-if value="{{isFx}}">
    <div style="position: absolute; left: 280px; top: 124px; width: 766px; height: 580px;">
      <div style="position: absolute; left: 0; top: 0; right: 0; height: 44px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;">
        <sc-for list="{{mixes}}" as="m">
          <button onClick="{{m.pick}}" aria-pressed="{{m.on}}" style="display: flex; flex-direction: column; justify-content: center; gap: 1px; border: 0; border-radius: 10px; background: {{t.card}}; box-shadow: {{m.ring}}; color: {{t.text}}; text-align: left; padding: 0 12px; cursor: pointer;">
            <span style="font-size: 12px; font-weight: 600;">{{m.label}}</span>
            <span style="font-size: 10px; color: {{t.secondary}};">{{m.hint}}</span>
          </button>
        </sc-for>
      </div>
      <div style="position: absolute; left: 0; top: 54px; right: 0; height: 96px; display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 8px;">
        <sc-for list="{{fxTiles}}" as="m">
          <div onClick="{{m.pick}}" style="position: relative; border-radius: 12px; background: {{m.bg}}; box-shadow: {{m.ring}}; cursor: pointer; overflow: hidden;">
            <svg width="100%" height="54" viewBox="0 0 100 52" preserveAspectRatio="none" style="display: block; margin-top: 4px;"><path d="{{m.viz}}" fill="none" stroke="{{m.color}}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"></path></svg>
            <span style="position: absolute; left: 10px; bottom: 10px; font-size: 11px; font-weight: 800; letter-spacing: 0.8px; color: {{m.nameColor}};">{{m.label}}</span>
            <button onClick="{{m.toggle}}" aria-label="On or off" style="position: absolute; right: 9px; bottom: 9px; width: 16px; height: 16px; border-radius: 4px; border: 1.5px solid {{m.color}}; background: {{m.powerBg}}; cursor: pointer; padding: 0;"></button>
          </div>
        </sc-for>
      </div>
      <div style="position: absolute; left: 0; top: 160px; width: 766px; height: 420px; border-radius: 14px; background: {{sc.bg}}; overflow: hidden; box-shadow: 0 0 0 0.5px rgba(255,255,255,0.08);">
        <svg width="766" height="420" viewBox="0 0 766 420" style="position: absolute; left: 0; top: 0;">
          <sc-for list="{{sc.rects}}" as="r"><rect x="{{r.x}}" y="{{r.y}}" width="{{r.w}}" height="{{r.h}}" rx="{{r.rx}}" fill="{{r.fill}}" stroke="{{r.stroke}}" stroke-width="{{r.sw}}"></rect></sc-for>
          <sc-for list="{{sc.paths}}" as="p"><path d="{{p.d}}" fill="{{p.fill}}" stroke="{{p.stroke}}" stroke-width="{{p.w}}" opacity="{{p.o}}" stroke-linecap="round" stroke-linejoin="round"></path></sc-for>
          <sc-for list="{{sc.texts}}" as="x"><text x="{{x.x}}" y="{{x.y}}" fill="{{x.c}}" font-size="{{x.s}}" font-weight="{{x.w}}" text-anchor="{{x.a}}" letter-spacing="{{x.ls}}" style="font-family: Inter, 'Segoe UI', sans-serif;">{{x.t}}</text></sc-for>
          <sc-for list="{{sc.nodes}}" as="n"><circle data-eqnode="{{n.i}}" cx="{{n.x}}" cy="{{n.y}}" r="{{n.r}}" fill="{{n.fill}}" stroke="{{n.stroke}}" stroke-width="2" style="cursor: grab;"></circle></sc-for>
        </svg>
        <sc-for list="{{sc.knobs}}" as="k">
          <div data-knob="{{k.id}}" title="{{k.title}}" style="position: absolute; left: {{k.x}}px; top: {{k.y}}px; width: {{k.size}}px; text-align: center; cursor: ns-resize; user-select: none;">
            <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.4px; color: {{k.labelColor}}; margin-bottom: 3px; white-space: nowrap; overflow: visible;">{{k.label}}</div>
            <svg width="{{k.size}}" height="{{k.size}}" viewBox="0 0 100 100" style="display: block;"><circle cx="50" cy="50" r="33" fill="{{k.face}}" stroke="{{k.rim}}" stroke-width="2"></circle><path d="{{k.track}}" fill="none" stroke="{{k.trackColor}}" stroke-width="8" stroke-linecap="round"></path><path d="{{k.arc}}" fill="none" stroke="{{k.color}}" stroke-width="8" stroke-linecap="round"></path><line x1="50" y1="50" x2="{{k.px}}" y2="{{k.py}}" stroke="{{k.pointer}}" stroke-width="6" stroke-linecap="round"></line></svg>
            <div style="font-size: 11px; font-weight: 600; color: {{k.valueColor}}; margin-top: 2px; font-variant-numeric: tabular-nums; white-space: nowrap;">{{k.value}}</div>
          </div>
        </sc-for>
        <sc-for list="{{sc.buttons}}" as="b">
          <button onClick="{{b.pick}}" style="position: absolute; left: {{b.x}}px; top: {{b.y}}px; width: {{b.w}}px; height: {{b.h}}px; border: {{b.border}}; border-radius: {{b.r}}px; background: {{b.bg}}; color: {{b.fg}}; font-size: {{b.fs}}px; font-weight: {{b.fw}}; cursor: pointer; text-align: {{b.align}}; padding: 0 8px; white-space: nowrap; overflow: hidden;">{{b.label}}</button>
        </sc-for>
        <sc-if value="{{sc.menu}}">
          <div onClick="{{closeMenu}}" style="position: absolute; inset: 0;"></div>
          <div style="position: absolute; left: {{sc.menu.x}}px; top: {{sc.menu.y}}px; min-width: {{sc.menu.w}}px; max-height: 360px; overflow-y: auto; padding: 4px; border-radius: 10px; background: #2C2C2E; box-shadow: 0 10px 30px rgba(0,0,0,0.5), 0 0 0 0.5px rgba(255,255,255,0.14);">
            <sc-for list="{{sc.menu.items}}" as="it">
              <div onClick="{{it.pick}}" style="padding: 6px 14px; border-radius: 6px; font-size: 13px; cursor: pointer; color: #F5F5F7; white-space: nowrap;">{{it.check}}{{it.label}}</div>
            </sc-for>
          </div>
        </sc-if>
      </div>
    </div>
  </sc-if>

'''

b = open("build_ui.py", encoding="utf-8").read()
b = rep(b, """# ---- transporte: Play/Stop e Lock MIDI""", '''# v0.4: troca a aba Effects pela fileira de módulos + editor
fx2 = tpl[tpl.index("  <!-- Effects: Mix Style + módulos -->"):tpl.index("  <!-- Keyboard: content layer, bottom -->")]
tpl = tpl.replace(fx2, """''' + FX.replace('"""', '\\"\\"\\"') + '''""")

# ---- transporte: Play/Stop e Lock MIDI''')
# fx.js entra antes da inicialização do app.js (usa P, L, setV... e precisa existir quando paint() roda)
b = rep(b, """js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()""",
"""js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()
init = "fit();\\npaint();\\nrequestAnimationFrame(frame);"
assert init in js
js = js.replace(init, open(os.path.join(HERE, "fx.js"), encoding="utf-8").read() + "\\n" + init)""")
open("build_ui.py", "w", encoding="utf-8").write(b)

a = open("app.js", encoding="utf-8").read()
a = rep(a, "    ...settingsVals(t, seg, en),", "    ...settingsVals(t, seg, en),\n    ...fxVals(t),")
open("app.js", "w", encoding="utf-8").write(a)
print("ok")
