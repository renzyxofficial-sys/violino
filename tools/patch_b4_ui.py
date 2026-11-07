"""Bloco 4 / template: barra de controle estilo Ableton, régua em compassos, visão geral, caixa de seleção,
menu flutuante, botão da grade, renomear take, Settings por cima, Undo/Redo, canvas do reverb."""
import os

os.chdir(r"C:\Users\TheoH\violino")
p = 'plugin/ui/build_ui.py'
b = open(p, encoding='utf-8').read()


def rep(old, new, n=1):
    global b
    assert b.count(old) == n, (b.count(old), old[:80])
    b = b.replace(old, new)


i = b.index('TRANSPORT = """'); j = b.index('"""', i + 15)
b = b[:i] + 'TRANSPORT = """' + open('tools/b4_transport.txt', encoding='utf-8').read() + b[j:]
rep("""        <span style="position: absolute; left: {{b.lx}}px; top: 118px; font-size: 11px; font-weight: 500; color: {{t.tertiary}};">{{b.label}}</span>
      </sc-for>""", """        <span style="position: absolute; left: {{b.lx}}px; top: 112px; font-size: 11px; font-weight: 600; color: {{t.secondary}}; pointer-events: none;">{{b.label}}</span>
      </sc-for>
      <sc-for list="{{rticks}}" as="k"><span style="position: absolute; left: {{k.x}}px; top: {{k.top}}px; width: 1px; height: {{k.h}}px; background: {{t.tertiary}}; pointer-events: none;"></span></sc-for>""")
rep("""<div data-ruler="1" title="Click to move the cursor" """, """<div data-ruler="1" title="Click: move the cursor · drag up/down: zoom · drag sideways: scroll" """)
i = b.index('      <sc-if value="{{hscroll}}">'); j = b.index('</sc-if>', i) + 8
b = b[:i] + """      <sc-if value="{{overview}}">
        <div data-overview="1" title="Overview · drag the window to scroll · drag up/down to zoom · click to jump" style="position: absolute; left: 268px; top: 403px; width: 748px; height: 8px; border-radius: 4px; background: {{t.fill}}; cursor: grab; overflow: hidden;">
          <sc-for list="{{overview.blocks}}" as="o"><span style="position: absolute; left: {{o.x}}px; top: 2px; width: {{o.w}}px; height: 4px; border-radius: 2px; background: {{o.c}}; opacity: 0.8; pointer-events: none;"></span></sc-for>
          <span style="position: absolute; left: {{overview.vx}}px; top: 0; width: {{overview.vw}}px; height: 8px; box-sizing: border-box; border-radius: 4px; border: 1.5px solid {{t.text}}; background: rgba(127,127,127,0.18); pointer-events: none;"></span>
        </div>
      </sc-if>""" + b[j:]
rep("""      <sc-for list="{{regions}}" as="r">
        <span data-rhead="{{r.i}}" title="{{r.title}}" style="position: absolute; left: {{r.x}}px; top: 170px; width: {{r.w}}px; height: 18px; cursor: grab; z-index: 6;"></span>""",
    """      <sc-for list="{{regions}}" as="r">
        <span data-rhead="{{r.i}}" title="{{r.title}} · double-click to rename" style="position: absolute; left: {{r.x}}px; top: 170px; width: {{r.w}}px; height: 18px; cursor: grab; z-index: 6;"></span>
        <sc-if value="{{r.renaming}}">
          <input data-rename="{{r.i}}" value="{{r.renameVal}}" maxlength="40" style="position: absolute; left: {{r.x}}px; top: 170px; width: {{r.w}}px; height: 18px; box-sizing: border-box; padding: 0 6px; border: 0; border-radius: 8px 8px 0 0; outline: 2px solid {{t.accent}}; background: #FFFFFF; color: #1D1D1F; font-size: 10px; font-weight: 700; z-index: 12;">
        </sc-if>""")
rep("""      <sc-if value="{{dragChip}}">""", """      <sc-if value="{{marq}}">
        <span style="position: absolute; left: {{marq.x}}px; top: {{marq.y}}px; width: {{marq.w}}px; height: {{marq.h}}px; border: 1px solid {{t.accent}}; background: {{t.accentSoft}}; border-radius: 2px; pointer-events: none; z-index: 8;"></span>
      </sc-if>
      <sc-if value="{{hasNotes}}">
        <button onClick="{{gridPick}}" title="Grid · Automatic follows the zoom, Snap locks notes to a division, Free has no snap" style="position: absolute; left: 270px; top: 141px; height: 25px; padding: 0 11px; border: 0; border-radius: 12.5px; z-index: 9; font-size: 11px; font-weight: 600; color: {{t.text}}; cursor: pointer; white-space: nowrap; {{t.glass}}">▦ {{gridLabel}} ▾</button>
      </sc-if>
      <sc-if value="{{dragChip}}">""")
rep("""<button class="tbb" onClick="{{takeBar.listen}}" title="Listen to this take here, before using it in your DAW" style="background:""",
    """<button class="tbb" onClick="{{takeBar.listen}}" title="Listen to this take here, before using it in your DAW" style="min-width: 66px; background:""")
rep("Click selects (Shift adds) · drag moves · right edge resizes · Alt+drag or wheel on a selected note: velocity · double-click adds · Delete removes",
    "Click selects · drag on empty space: box select · right-click: menu · Alt+drag / wheel on selected: velocity · double-click adds · Ctrl+C/V/X/D/Z")
rep('tpl = tpl[:_ti] + TRANSPORT + "</div>"', '''tpl = tpl[:_ti] + TRANSPORT + "</div>"
sub("top: 64px; bottom: 160px; width: 248px;", "top: 64px; bottom: 216px; width: 248px;")
sub("top: 64px; bottom: 160px; width: 202px;", "top: 64px; bottom: 216px; width: 202px;")''')
rep("""    <div onClick="{{closeSettings}}" style="position: absolute; inset: 0; background: rgba(0,0,0,0.16);"></div>
    <div role="dialog" aria-label="Settings" style="position: absolute;""", """    <div onClick="{{closeSettings}}" style="position: absolute; inset: 0; background: rgba(0,0,0,0.16); z-index: 100;"></div>
    <div role="dialog" aria-label="Settings" style="z-index: 101; position: absolute;""")
rep('sub(\'<button aria-label="Settings"', '''sub('<button aria-label="Undo" style="', '<button onClick="{{doUndo}}" title="Undo (Ctrl+Z)" aria-label="Undo" style="opacity: {{undoOp}}; ')
sub('<button aria-label="Redo" style="', '<button onClick="{{doRedo}}" title="Redo (Ctrl+Shift+Z)" aria-label="Redo" style="opacity: {{redoOp}}; ')
sub('<button aria-label="Settings"''')
MENU = """
  <sc-if value="{{pmenu}}">
    <div onClick="{{closeMenuP}}" style="position: absolute; inset: 0; z-index: 90;"></div>
    <div style="position: absolute; left: {{pmenu.x}}px; top: {{pmenu.y}}px; min-width: 200px; padding: 5px; box-sizing: border-box; border-radius: 10px; z-index: 91; background: rgba(38,38,42,0.94); -webkit-backdrop-filter: blur(20px); backdrop-filter: blur(20px); box-shadow: 0 12px 32px rgba(0,0,0,0.45), 0 0 0 0.5px rgba(255,255,255,0.16); color: #F5F5F7; font-size: 12px;">
      <sc-for list="{{pmenu.items}}" as="it">
        <sc-if value="{{it.sep}}"><div style="height: 0.5px; background: rgba(255,255,255,0.14); margin: 4px 6px;"></div></sc-if>
        <sc-if value="{{it.isHead}}"><div style="padding: 4px 10px 2px; font-size: 10px; font-weight: 700; color: rgba(235,235,245,0.45);">{{it.head}}</div></sc-if>
        <sc-if value="{{it.row}}"><div class="pmi" onClick="{{it.pick}}" style="opacity: {{it.op}};"><span style="width: 14px; color: #0A84FF;">{{it.check}}</span><span style="flex-grow: 1;">{{it.label}}</span><span style="color: rgba(235,235,245,0.42); font-size: 11px; padding-left: 14px;">{{it.key}}</span></div></sc-if>
        <sc-if value="{{it.chips}}"><div style="display: flex; flex-wrap: wrap; gap: 3px; padding: 4px 6px; max-width: 230px;"><sc-for list="{{it.chips}}" as="c"><span onClick="{{c.pick}}" style="height: 18px; padding: 0 7px; border-radius: 9px; background: {{c.bg}}; color: {{c.fg}}; font-size: 10px; font-weight: 600; line-height: 18px; cursor: pointer;">{{c.label}}</span></sc-for></div></sc-if>
      </sc-for>
    </div>
  </sc-if>"""
rep("SETTINGS = '''", "SETTINGS = '''" + MENU)
rep("""        <svg width="766" height="420" viewBox="0 0 766 420" style="position: absolute; left: 0; top: 0;">""",
    """        <sc-if value="{{sc.canvas}}"><canvas id="rvfx" width="1452" height="360" style="position: absolute; left: 20px; top: 52px; width: 726px; height: 180px; pointer-events: none;"></canvas></sc-if>
        <svg width="766" height="420" viewBox="0 0 766 420" style="position: absolute; left: 0; top: 0;">""")
rep(""".vmove [data-cap]{{""", """.pmi{{display:flex;align-items:center;height:24px;padding:0 8px 0 4px;border-radius:6px;cursor:pointer;white-space:nowrap}}
.pmi:hover{{background:#0A84FF}}
.tpg{{display:flex;align-items:center;gap:4px}}
#root{{user-select:none;-webkit-user-select:none}}
input{{user-select:text;-webkit-user-select:text}}
.vmove [data-cap]{{""")
rep("""open(os.path.join(HERE, "score.js"), encoding="utf-8").read() + "\\n" + init)""",
    """open(os.path.join(HERE, "score.js"), encoding="utf-8").read() + "\\n" + open(os.path.join(HERE, "edit.js"), encoding="utf-8").read() + "\\n" + init)""")
open(p, 'w', encoding='utf-8').write(b)
print('ok')
