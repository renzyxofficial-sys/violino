"""Gera ui/index.html a partir do design aprovado (ui/design/Main.dc.html).

O template do design (holes {{...}}, <sc-if>, <sc-for>) é mantido; as partes que na prévia eram
dados fixos (timeline, frases, medidores, motor) viram dados reais, e os sliders ganham arraste.
Uso: python ui/build_ui.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, "design", "Main.dc.html"), encoding="utf-8").read()

style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
tpl = src[src.index("<div style=\"position: relative; width: 1280px"):src.index("</x-dc>")].rstrip()


def sub(old, new, count=1):
    global tpl
    n = tpl.count(old)
    if n != count:
        raise SystemExit(f"esperava {count}, achei {n}: {old[:80]}")
    tpl = tpl.replace(old, new)


# janela do plugin: sem cantos (o DAW desenha a moldura)
sub("overflow: hidden; border-radius: 26px;", "overflow: hidden; border-radius: 0;")

# ---- timeline real
perf = tpl[tpl.index("  <!-- Performance:"):tpl.index("  <!-- Instrument:")]
tpl = tpl.replace(perf, """  <!-- Performance: timeline edge to edge, under the floating glass -->
  <sc-if value="{{isPerf}}">
    <div class="tabin" style="position: absolute; left: 0; right: 0; top: 0; bottom: 150px;">
      <sc-for list="{{bars}}" as="b">
        <span style="position: absolute; left: {{b.x}}px; top: 112px; height: 290px; width: 1px; background: {{t.grid}};"></span>
        <span style="position: absolute; left: {{b.lx}}px; top: 112px; font-size: 11px; font-weight: 600; color: {{t.secondary}}; pointer-events: none;">{{b.label}}</span>
      </sc-for>
      <sc-for list="{{rticks}}" as="k"><span style="position: absolute; left: {{k.x}}px; top: {{k.top}}px; width: 1px; height: {{k.h}}px; background: {{t.tertiary}}; pointer-events: none;"></span></sc-for>
      <sc-for list="{{regions}}" as="r">
        <div style="position: absolute; left: {{r.x}}px; top: 170px; width: {{r.w}}px; height: 232px; border-radius: 8px; background: {{r.fill}}; box-shadow: {{r.ring}}; pointer-events: none; overflow: hidden;">
          <div style="height: 18px; padding: 0 7px; background: {{r.head}}; opacity: {{r.headOp}}; color: #FFFFFF; font-size: 10px; font-weight: 700; line-height: 18px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{r.label}}</div>
        </div>
        <sc-if value="{{r.wave}}">
          <svg style="position: absolute; left: {{r.x}}px; top: 196px; pointer-events: none;" width="{{r.w}}" height="200" viewBox="0 0 {{r.w}} 200" aria-hidden="true"><path d="{{r.wave}}" fill="{{r.waveFill}}"></path></svg>
        </sc-if>
        <sc-if value="{{r.playing}}">
          <span style="position: absolute; left: {{r.cursorX}}px; top: 170px; width: 1.5px; height: 232px; background: {{t.ok}}; pointer-events: none;"></span>
        </sc-if>
        <sc-if value="{{r.busy}}">
          <span style="position: absolute; left: {{r.lx}}px; top: 392px; width: {{r.barW}}px; height: 3px; border-radius: 2px; background: {{t.track2}};"></span>
          <span style="position: absolute; left: {{r.lx}}px; top: 392px; width: {{r.progW}}px; height: 3px; border-radius: 2px; background: {{t.warn}};"></span>
        </sc-if>
      </sc-for>
      <sc-for list="{{rows}}" as="g"><span style="position: absolute; left: {{G.l}}px; width: {{G.rw}}px; top: {{g.y}}px; height: {{g.h}}px; background: {{g.bg}}; pointer-events: none;"></span></sc-for>
      <sc-for list="{{grid}}" as="g"><span style="position: absolute; left: {{g.x}}px; top: 170px; width: 1px; height: 232px; background: {{g.c}}; pointer-events: none;"></span></sc-for>
      <div data-ruler="1" title="Click: move the cursor · drag up/down: zoom · drag sideways: scroll" style="position: absolute; left: {{G.l}}px; top: 110px; width: {{G.w}}px; height: 26px; cursor: pointer;"></div>
      <sc-if value="{{cyc}}"><span data-cyc="1" title="Cycle range · drag the ends to resize, the middle to move" style="position: absolute; left: {{cyc.x}}px; top: 129px; width: {{cyc.w}}px; height: 7px; border-radius: 3px; background: {{cyc.bg}}; cursor: ew-resize; z-index: 4;"></span></sc-if>
      <div data-roll="1" style="position: absolute; left: {{G.l}}px; top: 170px; width: {{G.rw}}px; height: 232px;"></div>
      <sc-for list="{{notes}}" as="n">
        <span data-cap="{{n.i}}" class="{{n.cls}}" title="{{n.title}}" style="position: absolute; left: {{n.x}}px; top: {{n.y}}px; width: {{n.w}}px; height: {{n.h}}px; border-radius: {{n.r}}px; background: linear-gradient(rgba(255,255,255,0.30), rgba(255,255,255,0) 70%), {{n.art}}; opacity: {{n.op}}; box-shadow: {{n.ring}}; cursor: {{n.cursor}}; overflow: hidden;"><span style="position: absolute; left: 4px; top: 0; font-size: {{n.fs}}px; font-weight: 700; line-height: {{n.h}}px; color: {{n.fg}}; pointer-events: none; white-space: nowrap;">{{n.name}}</span></span>
      </sc-for>
      <sc-for list="{{regions}}" as="r">
        <span data-rhead="{{r.i}}" title="{{r.title}} · double-click to rename" style="position: absolute; left: {{r.x}}px; top: 170px; width: {{r.w}}px; height: 18px; cursor: grab; z-index: 6;"></span>
        <sc-if value="{{r.renaming}}">
          <input data-rename="{{r.i}}" value="{{r.renameVal}}" maxlength="40" style="position: absolute; left: {{r.x}}px; top: 170px; width: {{r.w}}px; height: 18px; box-sizing: border-box; padding: 0 6px; border: 0; border-radius: 8px 8px 0 0; outline: 2px solid {{t.accent}}; background: #FFFFFF; color: #1D1D1F; font-size: 10px; font-weight: 700; z-index: 12;">
        </sc-if>
        <sc-if value="{{r.edges}}">
          <span data-redge="{{r.i}}" data-side="l" title="Drag to trim or extend the start · Alt: stretch time" style="position: absolute; left: {{r.x}}px; top: 188px; width: 7px; height: 214px; cursor: ew-resize; z-index: 6;"></span>
          <span data-redge="{{r.i}}" data-side="r" title="Drag to trim or extend the end · Alt: stretch time" style="position: absolute; left: {{r.rx}}px; top: 170px; width: 7px; height: 232px; margin-left: -7px; cursor: ew-resize; z-index: 6;"></span>
        </sc-if>
      </sc-for>
      <!-- fade in de cada take (estilo FL): sombra acima da curva, alça de duração no topo e alça de formato na curva -->
      <svg style="position: absolute; left: {{G.l}}px; top: 170px; pointer-events: none; overflow: hidden;" width="{{G.rw}}" height="232" viewBox="0 0 {{G.rw}} 232" aria-hidden="true">
        <sc-for list="{{fades}}" as="f">
          <path d="{{f.shade}}" fill="{{fadeShade}}"></path>
          <path d="{{f.line}}" fill="none" stroke="{{fadeLine}}" stroke-width="1.5" stroke-linecap="round"></path>
        </sc-for>
      </svg>
      <sc-for list="{{fades}}" as="f">
        <span data-fade="{{f.i}}" title="{{f.title}}" style="position: absolute; left: {{f.hx}}px; top: 192px; width: 10px; height: 10px; margin-left: -5px; border-radius: 3px; background: #FFFFFF; box-shadow: 0 0 0 0.5px rgba(0,0,0,0.25), 0 1px 4px rgba(0,0,0,0.45); cursor: ew-resize; z-index: 7;"></span>
        <sc-if value="{{f.showT}}">
          <span data-fadet="{{f.i}}" title="Drag up or down to shape the curve · double-click to reset" style="position: absolute; left: {{f.tx}}px; top: {{f.ty}}px; width: 9px; height: 9px; margin: -5px 0 0 -5px; border-radius: 5px; background: rgba(255,255,255,0.18); border: 1.5px solid #FFFFFF; box-shadow: 0 1px 3px rgba(0,0,0,0.4); cursor: ns-resize; z-index: 7;"></span>
        </sc-if>
      </sc-for>
      <sc-if value="{{overview}}">
        <div data-overview="1" title="Overview · drag the window to scroll · drag up/down to zoom · click to jump" style="position: absolute; left: {{G.l}}px; top: 403px; width: {{G.ow}}px; height: 8px; border-radius: 4px; background: {{t.fill}}; cursor: grab; overflow: hidden;">
          <sc-for list="{{overview.blocks}}" as="o"><span style="position: absolute; left: {{o.x}}px; top: 2px; width: {{o.w}}px; height: 4px; border-radius: 2px; background: {{o.c}}; opacity: 0.8; pointer-events: none;"></span></sc-for>
          <span style="position: absolute; left: {{overview.vx}}px; top: 0; width: {{overview.vw}}px; height: 8px; box-sizing: border-box; border-radius: 4px; border: 1.5px solid {{t.text}}; background: rgba(127,127,127,0.18); pointer-events: none;"></span>
        </div>
      </sc-if>
      <!-- velocity (como no Logic): arraste uma haste, ou pinte por cima de várias -->
      <div data-vellane="1" title="Velocity · drag a stem up or down, or drag across stems to draw" style="position: absolute; left: {{G.l}}px; top: 412px; width: {{G.rw}}px; height: 36px; border-radius: 6px; background: {{t.grid}}; cursor: ns-resize;"></div>
      <span style="position: absolute; left: {{G.l6}}px; top: 413px; font-size: 9px; font-weight: 600; color: {{t.tertiary}}; pointer-events: none;">Velocity</span>
      <sc-for list="{{velStems}}" as="v">
        <span data-vstem="1" style="position: absolute; left: {{v.x}}px; top: {{v.top}}px; width: 2px; height: {{v.h}}px; background: {{v.color}}; opacity: {{v.op}}; pointer-events: none;"></span>
        <span data-vstem="1" style="position: absolute; left: {{v.x}}px; top: {{v.hy}}px; width: 7px; height: 7px; margin-left: -2.5px; border-radius: 4px; background: {{v.color}}; opacity: {{v.op}}; pointer-events: none;"></span>
      </sc-for>
      <sc-if value="{{hasNotes}}">
        <span style="position: absolute; left: {{G.l12}}px; top: 630px; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Articulations</span>
        <sc-for list="{{palette}}" as="a">
          <span data-artchip="{{a.i}}" title="Drag onto notes (or click with notes selected)" style="position: absolute; left: {{a.x}}px; top: 648px; width: 66px; height: 22px; border-radius: 11px; background: {{a.bg}}; color: {{a.fg}}; font-size: 11px; font-weight: 600; line-height: 22px; text-align: center; cursor: grab; user-select: none;">{{a.label}}</span>
        </sc-for>
        <span style="position: absolute; left: {{G.l12}}px; top: 680px; font-size: 10px; color: {{t.tertiary}}; white-space: nowrap;">Alt+wheel: note height · Click selects · drag on empty space: box select · right-click: menu · hold Alt: no grid · Ctrl+drag / wheel: velocity · double-click adds · Ctrl+C/V/X/D/Z</span>
        <!-- barra vertical: mover seleção / take / tudo -->
        <div style="position: absolute; left: {{G.mx}}px; top: 176px; width: 38px; display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 4px 0; border-radius: 15px; z-index: 9; color: {{t.text}}; {{t.glass}}">
          <button onClick="{{mv.scopePick}}" title="{{mv.scopeTitle}}" style="width: 32px; height: 20px; padding: 0; border: 0; border-radius: 10px; background: {{t.accentSoft}}; color: {{t.accent}}; font-size: 8px; font-weight: 800; letter-spacing: 0.3px; cursor: pointer;">{{mv.scope}}</button>
          <sc-for list="{{mv.up}}" as="b"><button class="mvb" onClick="{{b.pick}}" title="{{b.title}}" style="opacity: {{mv.op}};">{{b.label}}</button></sc-for>
          <span data-movegrip="1" title="Drag to move: up/down by semitones, left/right in time" style="display: flex; align-items: center; justify-content: center; width: 32px; height: 24px; border-radius: 8px; background: {{t.fill}}; font-size: 9px; font-weight: 700; cursor: move; opacity: {{mv.op}}; user-select: none;">Drag</span>
          <sc-for list="{{mv.down}}" as="b"><button class="mvb" onClick="{{b.pick}}" title="{{b.title}}" style="opacity: {{mv.op}};">{{b.label}}</button></sc-for>
          <span style="width: 16px; height: 0.5px; background: {{t.sep}}; margin: 2px 0;"></span>
          <sc-for list="{{mv.side}}" as="b"><button class="mvb" onClick="{{b.pick}}" title="{{b.title}}" style="opacity: {{mv.op}};">{{b.label}}</button></sc-for>
        </div>
      </sc-if>
      <sc-if value="{{marq}}">
        <span style="position: absolute; left: {{marq.x}}px; top: {{marq.y}}px; width: {{marq.w}}px; height: {{marq.h}}px; border: 1px solid {{t.accent}}; background: {{t.accentSoft}}; border-radius: 2px; pointer-events: none; z-index: 8;"></span>
      </sc-if>
      <sc-if value="{{hasNotes}}">
        <button onClick="{{gridPick}}" title="Grid · Automatic follows the zoom, Snap locks notes to a division, Free has no snap" style="position: absolute; left: {{G.l2}}px; top: 141px; height: 25px; padding: 0 11px; border: 0; border-radius: 12.5px; z-index: 9; font-size: 11px; font-weight: 600; color: {{t.text}}; cursor: pointer; white-space: nowrap; {{t.glass}}">▦ {{gridLabel}} ▾</button>
      </sc-if>
      <sc-if value="{{dragChip}}">
        <span style="position: absolute; left: {{dragChip.x}}px; top: {{dragChip.y}}px; width: 66px; height: 22px; border-radius: 11px; background: {{dragChip.bg}}; color: {{dragChip.fg}}; font-size: 11px; font-weight: 600; line-height: 22px; text-align: center; pointer-events: none; opacity: 0.9; box-shadow: 0 6px 16px rgba(0,0,0,0.4);">{{dragChip.label}}</span>
      </sc-if>
      <sc-if value="{{showPlayhead}}">
        <span style="position: absolute; left: {{playX}}px; top: 112px; height: 292px; width: 1.5px; background: {{t.rec}}; pointer-events: none; box-shadow: 0 0 6px {{t.rec}};"></span>
      </sc-if>
      <!-- barra fixa do take em foco: ouvir, arrastar, render, cortar, apagar -->
      <sc-if value="{{takeBar}}">
        <div style="position: absolute; left: {{G.tc}}px; transform: translateX(-50%); top: 140px; height: 27px; white-space: nowrap; box-sizing: border-box; display: flex; align-items: center; gap: 3px; padding: 0 3px; border-radius: 14px; z-index: 9; color: {{t.text}}; {{t.glass}}">
          <button class="tbb" onClick="{{takeBar.prev}}" title="Previous take" style="min-width: 22px; padding: 0;">‹</button>
          <span style="font-size: 11px; font-weight: 700; white-space: nowrap; font-variant-numeric: tabular-nums;">{{takeBar.title}}</span>
          <button class="tbb" onClick="{{takeBar.next}}" title="Next take" style="min-width: 22px; padding: 0;">›</button>
          <span style="font-size: 10px; font-weight: 600; color: {{takeBar.stColor}}; padding: 0 4px 0 2px; white-space: nowrap;">{{takeBar.st}}</span>
          <span style="width: 0.5px; height: 16px; background: {{t.sep}};"></span>
          <sc-if value="{{takeBar.rendered}}">
            <button class="tbb" onClick="{{takeBar.listen}}" title="Listen to this take here, before using it in your DAW" style="min-width: 66px; background: {{takeBar.listenBg}}; color: {{takeBar.listenFg}};">{{takeBar.listenLabel}}</button>
            <button class="tbb" data-drag="{{takeBar.i}}" title="Drag the rendered audio onto an audio track in your DAW" style="cursor: grab;">⠿ Audio</button>
          </sc-if>
          <button class="tbb" data-dragmidi="{{takeBar.i}}" title="Drag as MIDI (notes only)" style="cursor: grab;">♪ MIDI</button>
          <button class="tbb" data-dragmidi="{{takeBar.i}}" data-dyn="1" title="Drag as MIDI with the dynamics curve (CC1 + CC11)" style="cursor: grab;">♪ + Dyn</button>
          <span style="width: 0.5px; height: 16px; background: {{t.sep}};"></span>
          <button class="tbb" onClick="{{takeBar.doRender}}" title="{{takeBar.renderTitle}}">↻</button>
          <button class="tbb" onClick="{{takeBar.doUnrender}}" title="Remove this render (keep the notes)" style="opacity: {{takeBar.unOp}};">⊘</button>
          <button class="tbb" onClick="{{doSplitTake}}" title="Split the take at the cursor">✂</button>
          <button class="tbb" onClick="{{takeBar.doDelete}}" title="Delete this take (notes and render)" style="color: {{t.rec}};">🗑</button>
        </div>
      </sc-if>
      <sc-if value="{{tip}}">
        <span style="position: absolute; left: {{tip.x}}px; top: {{tip.y}}px; height: 20px; padding: 0 8px; border-radius: 10px; background: rgba(28,28,30,0.88); color: #FFFFFF; font-size: 11px; font-weight: 600; line-height: 20px; white-space: nowrap; pointer-events: none; z-index: 20; font-variant-numeric: tabular-nums;">{{tip.text}}</span>
      </sc-if>
      <sc-if value="{{empty}}">
        <div style="position: absolute; left: {{G.l}}px; right: {{G.r}}px; top: 240px; text-align: center; color: {{t.secondary}};">
          <div style="font-size: 17px; font-weight: 600; color: {{t.text}}; margin-bottom: 6px;">Play something</div>
          <div style="font-size: 13px; line-height: 1.5;">{{emptyHint}}</div>
        </div>
      </sc-if>
      <span style="position: absolute; left: {{G.l12}}px; top: 456px; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Dynamics</span>
      <span style="position: absolute; left: {{G.l84}}px; top: 456px; font-size: 10px; color: {{t.tertiary}};">✎ click and drag to draw</span>
      <button onClick="{{dynClear}}" class="lg-pill" title="Remove everything you drew" style="position: absolute; left: {{G.l212}}px; top: 452px; height: 18px; padding: 0 8px; border: 0; border-radius: 9px; color: {{t.text}}; font-size: 10px; font-weight: 600; cursor: pointer;">Reset</button>
      <div data-dynlane="1" style="position: absolute; left: {{G.l}}px; top: 474px; width: {{G.w}}px; height: 64px; cursor: crosshair; z-index: 5;"></div>
      <svg style="position: absolute; left: {{G.l}}px; top: 474px; pointer-events: none;" width="{{G.w}}" height="64" viewBox="0 0 {{G.w}} 64" aria-hidden="true">
        <polygon points="{{dynArea}}" fill="{{t.accentSoft}}"></polygon>
        <polyline points="{{dynLine}}" fill="none" stroke="{{t.accent}}" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"></polyline>
      </svg>
      <span style="position: absolute; left: {{G.l12}}px; top: 548px; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Articulation</span>
      <sc-for list="{{lane}}" as="c">
        <span title="{{c.title}}" style="position: absolute; left: {{c.x}}px; top: 568px; width: {{c.w}}px; height: 22px; border-radius: 11px; background: {{c.bg}}; color: {{c.fg}}; font-size: 11px; font-weight: 600; line-height: 22px; padding-left: 9px; box-sizing: border-box; overflow: hidden; white-space: nowrap;">{{c.label}}</span>
      </sc-for>
      <sc-if value="{{noSel}}"><span style="position: absolute; left: {{G.l12}}px; top: 606px; font-size: 11px; color: {{t.tertiary}};">{{summary}}</span></sc-if>
      <sc-if value="{{hasSel}}">
        <div style="position: absolute; left: {{G.l2}}px; top: 598px; right: {{G.r}}px; display: flex; align-items: center; gap: 3px; flex-wrap: nowrap; z-index: 8;">
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
      </sc-if>
    </div>
  </sc-if>

""")

# ---- aba Effects: Mix Style + módulos com liga/desliga
fx = tpl[tpl.index("  <!-- Effects: grouped list -->"):tpl.index("  <!-- Keyboard: content layer, bottom -->")]
tpl = tpl.replace(fx, """  <!-- Effects: Mix Style + módulos -->
  <sc-if value="{{isFx}}">
    <div style="position: absolute; left: 280px; right: 234px; top: 124px; bottom: 236px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px; padding-right: 6px;">
      <div style="display: flex; flex-direction: column; gap: 6px;">
        <h2 style="margin: 0 0 2px 12px; font-size: 13px; font-weight: 600;">Mix Style</h2>
        <div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px;">
          <sc-for list="{{mixes}}" as="m">
            <button onClick="{{m.pick}}" aria-pressed="{{m.on}}" style="display: flex; flex-direction: column; align-items: flex-start; gap: 3px; height: 60px; padding: 10px 12px; border: 0; border-radius: 12px; background: {{t.card}}; box-shadow: {{m.ring}}; color: {{t.text}}; text-align: left; cursor: pointer;">
              <span style="font-size: 13px; font-weight: 600;">{{m.label}}</span>
              <span style="font-size: 11px; color: {{t.secondary}};">{{m.hint}}</span>
            </button>
          </sc-for>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; align-items: start;">
        <sc-for list="{{fxModules}}" as="m">
          <div style="border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
            <div style="display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 10px 0 12px;">
              <span style="flex-grow: 1; font-weight: 600;">{{m.label}}</span>
              <sc-if value="{{m.room}}">
                <span onClick="{{nextRoom}}" style="height: 22px; padding: 0 8px; border-radius: 7px; background: {{t.fill}}; font-size: 11px; font-weight: 500; line-height: 22px; cursor: pointer;">{{roomName}}</span>
              </sc-if>
              <button onClick="{{m.toggle}}" aria-pressed="{{m.on}}" aria-label="{{m.label}} on or off" style="position: relative; width: 48px; height: 24px; border: 0; border-radius: 12px; background: {{m.track}}; cursor: pointer; overflow: visible; flex-shrink: 0;">
                <span class="lg-thumb" style="position: absolute; top: 2px; left: {{m.knob}}px; width: 28px; height: 20px; border-radius: 10px;"></span>
              </button>
            </div>
            <div style="opacity: {{m.opacity}}; padding-bottom: 6px;">
              <sc-for list="{{m.sliders}}" as="r">
                <div style="display: flex; align-items: center; gap: 8px; height: 34px; padding: 0 12px; border-top: 0.5px solid {{t.sep}};">
                  <span style="width: 58px; font-size: 12px;">{{r.label}}</span>
                  <div data-slider="{{r.id}}" style="position: relative; flex-grow: 1; height: 20px; cursor: pointer;">
                    <span style="position: absolute; left: 0; right: 0; top: 7px; height: 6px; border-radius: 3px; background: {{t.track2}};"></span>
                    <span style="position: absolute; left: {{r.fillLeft}}%; top: 7px; width: {{r.fillW}}%; height: 6px; border-radius: 3px; background: {{t.accent}};"></span>
                    <span class="lg-thumb" style="position: absolute; left: {{r.pct}}%; top: -1px; width: 30px; height: 22px; margin-left: -15px; border-radius: 11px;"></span>
                  </div>
                  <span style="width: 54px; text-align: right; font-size: 12px; color: {{t.secondary}}; font-variant-numeric: tabular-nums;">{{r.value}}</span>
                </div>
              </sc-for>
            </div>
          </div>
        </sc-for>
      </div>
    </div>
  </sc-if>

""")

# v0.4: troca a aba Effects pela fileira de módulos + editor
fx2 = tpl[tpl.index("  <!-- Effects: Mix Style + módulos -->"):tpl.index("  <!-- Keyboard: content layer, bottom -->")]
tpl = tpl.replace(fx2, """  <!-- Effects: Mix Style, fileira de módulos e o editor do módulo escolhido -->
  <sc-if value="{{isFx}}">
    <div class="tabin" style="position: absolute; left: 280px; top: 124px; width: 766px; height: 580px;">
      <button onClick="{{toggleBypass}}" title="Turn all effects off or on" style="position: absolute; right: 0; top: 0; width: 110px; height: 44px; border: 0; border-radius: 10px; background: {{bypassBg}}; color: {{bypassFg}}; font-size: 12px; font-weight: 700; cursor: pointer;">⏻ {{bypassLabel}}</button>
      <div style="position: absolute; left: 0; top: 0; right: 118px; height: 44px; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;">
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
        <sc-if value="{{sc.canvas}}"><canvas id="rvfx" width="1452" height="360" style="position: absolute; left: 20px; top: 52px; width: 726px; height: 180px; pointer-events: none;"></canvas></sc-if>
        <svg width="766" height="420" viewBox="0 0 766 420" style="position: absolute; left: 0; top: 0;">
          <sc-for list="{{sc.rects}}" as="r"><rect x="{{r.x}}" y="{{r.y}}" width="{{r.w}}" height="{{r.h}}" rx="{{r.rx}}" fill="{{r.fill}}" stroke="{{r.stroke}}" stroke-width="{{r.sw}}"></rect></sc-for>
          <sc-for list="{{sc.paths}}" as="p"><path d="{{p.d}}" fill="{{p.fill}}" stroke="{{p.stroke}}" stroke-width="{{p.w}}" opacity="{{p.o}}" stroke-linecap="round" stroke-linejoin="round"></path></sc-for>
          <sc-for list="{{sc.texts}}" as="x"><text x="{{x.x}}" y="{{x.y}}" fill="{{x.c}}" font-size="{{x.s}}" font-weight="{{x.w}}" text-anchor="{{x.a}}" letter-spacing="{{x.ls}}" style="font-family: Inter, 'Segoe UI', sans-serif;">{{x.t}}</text></sc-for>
          <sc-for list="{{sc.nodes}}" as="n"><circle data-eqnode="{{n.i}}" cx="{{n.x}}" cy="{{n.y}}" r="{{n.r}}" fill="{{n.fill}}" stroke="{{n.stroke}}" stroke-width="2" style="cursor: grab;"></circle></sc-for>
        </svg>
        <sc-for list="{{sc.knobs}}" as="k">
          <div data-knob="{{k.id}}" title="{{k.title}}" style="position: absolute; left: {{k.x}}px; top: {{k.y}}px; width: {{k.size}}px; text-align: center; cursor: ns-resize; user-select: none; opacity: {{k.opacity}};">
            <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.4px; color: {{k.labelColor}}; margin-bottom: 3px; white-space: nowrap; overflow: visible;">{{k.label}}</div>
            <svg width="{{k.size}}" height="{{k.size}}" viewBox="0 0 100 100" style="display: block;"><circle cx="50" cy="50" r="33" fill="{{k.face}}" stroke="{{k.rim}}" stroke-width="2"></circle><path d="{{k.track}}" fill="none" stroke="{{k.trackColor}}" stroke-width="8" stroke-linecap="round"></path><path d="{{k.arc}}" fill="none" stroke="{{k.color}}" stroke-width="8" stroke-linecap="round"></path><line x1="50" y1="50" x2="{{k.px}}" y2="{{k.py}}" stroke="{{k.pointer}}" stroke-width="6" stroke-linecap="round"></line></svg>
            <div style="font-size: 11px; font-weight: 600; color: {{k.valueColor}}; margin-top: 2px; font-variant-numeric: tabular-nums; white-space: nowrap;">{{k.value}}</div>
          </div>
        </sc-for>
        <sc-for list="{{sc.sliders}}" as="s">
          <div data-slider="{{s.id}}" style="position: absolute; left: {{s.x}}px; top: {{s.y}}px; width: {{s.w}}px; height: {{s.h}}px; border-radius: {{s.r}}px; background: {{s.track}}; cursor: pointer; box-shadow: inset 0 1px 3px rgba(0,0,0,0.12);">
            <span style="position: absolute; left: 0; top: 0; bottom: 0; width: {{s.pct}}%; border-radius: {{s.r}}px; background: {{s.fill}};"></span>
            <span class="lg-thumb" style="position: absolute; left: {{s.pct}}%; top: 50%; width: {{s.th}}px; height: {{s.th}}px; margin-left: -{{s.half}}px; margin-top: -{{s.half}}px; border-radius: 50%;"></span>
          </div>
        </sc-for>
        <sc-for list="{{sc.vsliders}}" as="s">
          <div data-vslider="{{s.id}}" style="position: absolute; left: {{s.x}}px; top: {{s.y}}px; width: {{s.w}}px; height: {{s.h}}px; border-radius: {{s.r}}px; background: {{s.track}}; cursor: pointer;">
            <span style="position: absolute; left: 0; right: 0; bottom: 0; height: {{s.pct}}%; border-radius: {{s.r}}px; background: {{s.fill}};"></span>
            <span style="position: absolute; left: 50%; bottom: {{s.pct}}%; width: {{s.tw}}px; height: 10px; margin-left: -{{s.tw2}}px; margin-bottom: -5px; border-radius: 3px; background: #FFFFFF; box-shadow: 0 1px 3px rgba(0,0,0,0.35), 0 0 0 0.5px rgba(0,0,0,0.2);"></span>
          </div>
        </sc-for>
        <sc-for list="{{sc.buttons}}" as="b">
          <button onClick="{{b.pick}}" style="position: absolute; left: {{b.x}}px; top: {{b.y}}px; width: {{b.w}}px; height: {{b.h}}px; border: {{b.border}}; border-radius: {{b.r}}px; background: {{b.bg}}; color: {{b.fg}}; font-size: {{b.fs}}px; font-weight: {{b.fw}}; cursor: pointer; text-align: {{b.align}}; padding: 0 {{b.pad}}px; box-sizing: border-box; white-space: nowrap; overflow: hidden;">{{b.label}}</button>
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

""")

# ---- aba Score
sc_block = """  <!-- Score: partitura numa folha antiga -->
  <sc-if value="{{isScore}}">
    <div class="tabin" style="position: absolute; left: 280px; top: 124px; width: 766px; height: 580px; border-radius: 6px; overflow: hidden; background: url(&quot;data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0.35 0 0 0 0 0.25 0 0 0 0 0.12 0 0 0 0.10 0'/></filter><rect width='300' height='300' filter='url(%23n)'/></svg>&quot;), radial-gradient(ellipse at 50% 40%, #F3E6C8 0%, #E9D6AE 60%, #D9BF8C 100%); box-shadow: 0 8px 30px rgba(0,0,0,0.35), inset 0 0 60px rgba(120,80,30,0.35);">
      <svg width="766" height="580" viewBox="0 0 766 580" style="position: absolute; left: 0; top: 0;">
        <sc-for list="{{scorePaths}}" as="p"><path d="{{p.d}}" fill="{{p.fill}}" stroke="{{p.stroke}}" stroke-width="{{p.w}}" stroke-linecap="round"></path></sc-for>
        <sc-for list="{{scoreTexts}}" as="x"><text x="{{x.x}}" y="{{x.y}}" fill="{{x.c}}" font-size="{{x.s}}" font-weight="{{x.w}}" text-anchor="{{x.a}}" style="font-family: {{x.f}};">{{x.t}}</text></sc-for>
      </svg>
      <div data-score="1" style="position: absolute; left: 0; top: 104px; width: 766px; height: 420px; cursor: {{scoreCursor}};"></div>
      <sc-if value="{{scoreGhost}}"><span style="position: absolute; left: {{scoreGhost.x}}px; top: {{scoreGhost.y}}px; width: 12px; height: 10px; border-radius: 2px; background: rgba(10,132,255,0.35); border: 1.5px solid #0A84FF; pointer-events: none;"></span></sc-if>
      <div aria-label="Score tools" style="position: absolute; left: 14px; top: 12px; display: flex; gap: 3px; align-items: center;">
        <sc-for list="{{scoreTools}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}};">{{b.label}}</button></sc-for>
        <span style="width: 8px;"></span>
        <sc-for list="{{scoreAcc}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}}; font-family: 'Segoe UI Symbol', serif; font-size: 15px;">{{b.label}}</button></sc-for>
      </div>
      <div aria-label="Note values" style="position: absolute; right: 14px; top: 12px; display: flex; gap: 3px; align-items: center;">
        <sc-for list="{{scoreDurs}}" as="b"><button onClick="{{b.pick}}" title="{{b.title}}" class="scb" style="background: {{b.bg}}; color: {{b.fg}}; font-family: 'Segoe UI Symbol', serif; font-size: 15px;">{{b.label}}</button></sc-for>
      </div>
      <button onClick="{{scorePrev}}" aria-label="Previous page" style="position: absolute; left: 14px; bottom: 14px; width: 30px; height: 30px; border-radius: 15px; border: 1px solid rgba(59,42,26,0.35); background: rgba(255,255,255,0.25); color: #3b2a1a; cursor: pointer;">‹</button>
      <div aria-label="Pages" style="position: absolute; left: 56px; right: 56px; bottom: 16px; display: flex; justify-content: center; flex-wrap: wrap; gap: 4px; max-height: 58px; overflow-y: auto;">
        <sc-for list="{{scorePages}}" as="pg"><button onClick="{{pg.pick}}" aria-pressed="{{pg.on}}" title="Page {{pg.label}}" style="min-width: 26px; height: 26px; padding: 0 6px; border-radius: 13px; border: 1px solid rgba(59,42,26,0.35); background: {{pg.bg}}; color: {{pg.fg}}; font-family: Georgia, serif; font-size: 12px; cursor: pointer;">{{pg.label}}</button></sc-for>
      </div>
      <button onClick="{{scoreNext}}" aria-label="Next page" style="position: absolute; right: 14px; bottom: 14px; width: 30px; height: 30px; border-radius: 15px; border: 1px solid rgba(59,42,26,0.35); background: rgba(255,255,255,0.25); color: #3b2a1a; cursor: pointer;">›</button>
    </div>
  </sc-if>

"""
tpl = tpl.replace("  <!-- Keyboard: content layer, bottom -->", sc_block + "  <!-- Keyboard: content layer, bottom -->", 1)

# ---- transporte: cápsula centrada na timeline, com Play/Stop, Lock, Drag All e zoom
TRANSPORT = """  <!-- barra de controle (como a do Ableton): tempo · transporte e posição · captura e render · saída e zoom -->
  <div style="position: absolute; left: 10px; right: 10px; bottom: 164px; height: 46px; box-sizing: border-box; display: flex; align-items: center; justify-content: space-between; padding: 0 6px; border-radius: 23px; color: {{t.text}}; {{t.glass}}">
    <div class="tpg">
      <div title="{{bpmTitle}}" style="display: flex; align-items: center; height: 34px; box-sizing: border-box; padding: 0 4px; border-radius: 17px; background: {{t.fill}};">
        <sc-if value="{{bpmEdit}}"><button class="tpb" onClick="{{bpmDown}}" aria-label="Slower" style="width: 24px; height: 26px; padding: 0; font-size: 14px;">−</button></sc-if>
        <span data-bpmdrag="{{bpmEdit}}" style="min-width: 54px; text-align: center; font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; cursor: {{bpmCursor}}; user-select: none;">{{bpmText}}</span>
        <sc-if value="{{bpmEdit}}"><button class="tpb" onClick="{{bpmUp}}" aria-label="Faster" style="width: 24px; height: 26px; padding: 0; font-size: 14px;">+</button></sc-if>
        <span style="font-size: 10px; font-weight: 700; color: {{t.secondary}}; padding: 0 8px 0 3px;">BPM</span>
      </div>
      <span style="font-size: 12px; font-weight: 600; color: {{t.secondary}}; padding: 0 4px; white-space: nowrap;">4 / 4</span>
      <sc-if value="{{bpmEdit}}"><button onClick="{{toggleMetro}}" class="tpb" aria-label="Metronome" title="Metronome (Standalone): clicks on every beat while playing" style="width: 34px; padding: 0; background: {{metroBg}}; color: {{metroFg}};"><svg width="14" height="15" viewBox="0 0 14 15" aria-hidden="true"><path d="M5 1.5h4l3 12H2z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"></path><path d="M7 10L11 3.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"></path></svg></button></sc-if>
    </div>
    <div class="tpg">
      <button onClick="{{doRewind}}" aria-label="Back to start" title="Back to start" class="tpb" style="width: 34px; padding: 0;"><svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 2.5v9M12 2.5v9L5 7z" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"></path></svg></button>
      <button onClick="{{doPlay}}" aria-label="Play" title="Play from the cursor · press again to pause (Space in the Standalone)" class="tpb" style="width: 34px; padding: 0; background: {{playBg}}; color: {{playFg}};"><svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true"><path d="M4 2.5v9l7.5-4.5z" fill="currentColor"></path></svg></button>
      <button onClick="{{doPause}}" aria-label="Pause" title="Pause (Play continues from here)" class="tpb" style="width: 34px; padding: 0;"><svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 2.5h2.5v9H3.5zM8 2.5h2.5v9H8z" fill="currentColor"></path></svg></button>
      <button onClick="{{doStop}}" aria-label="Stop" title="Stop (back to where play started · twice: to the start)" class="tpb" style="width: 34px; padding: 0;"><svg width="12" height="12" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 3h8v8H3z" fill="currentColor"></path></svg></button>
      <button onClick="{{toggleCycle}}" aria-label="Cycle" title="Cycle: loop the yellow range on the ruler (drag its ends or middle)" class="tpb" style="width: 34px; padding: 0; background: {{cycBg}}; color: {{cycFg}};"><svg width="15" height="13" viewBox="0 0 16 14" aria-hidden="true"><path d="M3 6a4 4 0 014-4h4M13 8a4 4 0 01-4 4H5M9.5 0.5L11.5 2 9.5 3.5M6.5 10.5L4.5 12 6.5 13.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"></path></svg></button>
      <div title="Position: bar . beat . sixteenth" style="display: flex; flex-direction: column; justify-content: center; align-items: center; width: 92px; height: 34px; margin-left: 2px; border-radius: 9px; background: {{t.fill}}; line-height: 1.15;">
        <span style="font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums;">{{posBars}}</span>
        <span style="font-size: 10px; color: {{t.secondary}}; font-variant-numeric: tabular-nums;">{{posTime}}</span>
      </div>
    </div>
    <div class="tpg">
      <button onClick="{{toggleCapture}}" aria-pressed="{{capOn}}" title="Capture what you play (or the DAW plays)" class="tpb" style="gap: 6px; padding: 0 12px 0 10px; background: {{capBg}}; color: {{capFg}};"><span style="width: 10px; height: 10px; border-radius: 5px; background: {{capDot}};"></span>Capture</button>
      <button onClick="{{toggleLock}}" aria-pressed="{{lockOn}}" title="Lock MIDI: keep what is captured, nothing is overwritten" class="tpb" style="gap: 5px; padding: 0 11px; background: {{lockBg}}; color: {{lockFg}};"><svg width="12" height="13" viewBox="0 0 13 14" aria-hidden="true"><path d="{{lockIcon}}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path></svg>Lock</button>
      <div title="Render each phrase automatically when it ends" style="display: flex; align-items: center; gap: 7px; height: 34px; padding: 0 5px 0 11px; box-sizing: border-box; border-radius: 17px; background: {{t.fill}};">
        <span style="font-size: 12px; font-weight: 600;">Autorender</span>
        <button onClick="{{toggleAuto}}" aria-pressed="{{autoOn}}" aria-label="Autorender" style="position: relative; width: 44px; height: 22px; border: 0; border-radius: 11px; background: {{autoTrack}}; cursor: pointer; overflow: visible; padding: 0;">
          <span class="lg-thumb" style="position: absolute; top: 2px; left: {{autoKnob}}px; width: 26px; height: 18px; border-radius: 9px;"></span>
        </button>
      </div>
      <button onClick="{{doRender}}" class="tpb" style="min-width: 84px; padding: 0 16px; background: {{renderBg}}; color: #FFFFFF;">{{renderLabel}}</button>
    </div>
    <div class="tpg">
      <button data-dragall="1" class="tpb lg-icon" title="Drag ALL rendered audio as one WAV onto a track in your DAW" style="padding: 0 11px; cursor: grab; background: {{t.fill}};">⠿ Drag All</button>
      <button onClick="{{doExport}}" class="tpb lg-icon" aria-label="Export WAV" title="Export everything as WAV" style="width: 34px; padding: 0;"><svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 2v8M5 7l3 3 3-3M3 11.5V13h10v-1.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"></path></svg></button>
      <button onClick="{{doClear}}" class="tpb lg-icon" aria-label="Clear captured phrases" title="Clear everything captured (Ctrl+Z brings it back)" style="width: 34px; padding: 0;"><svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.7 9h5.6l.7-9" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"></path></svg></button>
      <span style="width: 0.5px; height: 22px; background: {{t.sep}}; margin: 0 3px;"></span>
      <button onClick="{{doFit}}" class="tpb lg-icon" title="Show everything" style="padding: 0 10px; font-weight: 500;">Fit</button>
      <svg width="13" height="13" viewBox="0 0 14 14" aria-hidden="true" style="color: {{t.secondary}}; flex-shrink: 0;"><circle cx="6" cy="6" r="4.2" fill="none" stroke="currentColor" stroke-width="1.4"></circle><path d="M9.2 9.2L12.5 12.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"></path></svg>
      <span style="position: relative; display: block; width: 80px; height: 22px; margin: 0 14px 0 4px;">
        <span style="position: absolute; left: 0; right: 0; top: 8px; height: 6px; border-radius: 3px; background: {{t.track2}};"></span>
        <span style="position: absolute; left: 0; top: 8px; width: {{zoomPct}}%; height: 6px; border-radius: 3px; background: {{t.accent}};"></span>
        <span class="lg-thumb" style="position: absolute; left: {{zoomPct}}%; top: 0; width: 30px; height: 22px; margin-left: -15px; border-radius: 11px; pointer-events: none;"></span>
        <input id="zoom" onInput="{{setZoom}}" type="range" min="1" max="8" step="0.1" value="{{zoom}}" aria-label="Zoom" style="position: absolute; inset: 0; width: 100%; height: 100%; margin: 0; opacity: 0; cursor: pointer;">
      </span>
    </div>
  </div>
"""
_ti = tpl.index("  <!-- transport: floating glass capsule")
tpl = tpl[:_ti] + TRANSPORT + "</div>"
sub("top: 64px; bottom: 160px; width: 248px;", "top: 64px; bottom: 216px; width: 248px; opacity: {{pOp}}; transform: scale({{pSc}}); pointer-events: {{pPe}}; visibility: {{pVis}}; transition: none;")
sub("top: 64px; bottom: 160px; width: 202px;", "top: 64px; bottom: 216px; width: 202px; opacity: {{pOp}}; transform: scale({{pSc}}); pointer-events: {{pPe}}; visibility: {{pVis}}; transition: none;")
sub('style="position: absolute; left: 268px; right: 222px; top: 64px; height: 44px;', 'style="position: absolute; left: {{G.l}}px; right: {{G.r}}px; top: 64px; height: 44px;')
sub('<button aria-label="Compact view" style="', '<button onClick="{{toggleFocus}}" aria-pressed="{{focusOn}}" title="Focus: hide the side panels and widen the timeline" aria-label="Compact view" style="background: {{focusBg}} !important; ')

sub('<span style="margin: 4px 8px 0; font-size: 11px; color: {{t.secondary}}; line-height: 1.4;">{{qualityHint}}</span>',
    '<span style="margin: 4px 8px 0; font-size: 11px; color: {{t.secondary}}; line-height: 1.4;">{{qualityHint}}</span>'
    '<div style="display: flex; align-items: center; gap: 8px; margin: 6px 8px 0;"><span style="font-size: 12px;">Steps</span>'
    '<div data-slider="renderSteps" style="position: relative; flex-grow: 1; height: 20px; cursor: pointer;">'
    '<span style="position: absolute; left: 0; right: 0; top: 7px; height: 6px; border-radius: 3px; background: {{t.track2}};"></span>'
    '<span style="position: absolute; left: 0; top: 7px; width: {{stepsPct}}%; height: 6px; border-radius: 3px; background: {{t.accent}};"></span>'
    '<span class="lg-thumb" style="position: absolute; left: {{stepsPct}}%; top: -1px; width: 30px; height: 22px; margin-left: -15px; border-radius: 11px;"></span></div>'
    '<span style="width: 22px; text-align: right; font-size: 12px; color: {{t.secondary}}; font-variant-numeric: tabular-nums;">{{stepsText}}</span></div>'
    '<h2 style="margin: 12px 8px 4px; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Sound Presets</h2>'
    '<div style="display: flex; gap: 4px; margin: 0 4px;">'
    '<button onClick="{{mixPick}}" title="Mix preset: room, reverb and tone" style="flex: 1 1 0; min-width: 0; height: 26px; padding: 0 8px; border: 0; border-radius: 8px; background: {{t.accent}}; color: #FFFFFF; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Mix · {{mixName}} ▾</button>'
    '<button onClick="{{stylePick}}" title="Playstyle: how notes are connected, portamento, dynamics and vibrato" style="flex: 1 1 0; min-width: 0; height: 26px; padding: 0 8px; border: 0; border-radius: 8px; background: {{styleBg}}; color: {{styleFg}}; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Style · {{styleName}} ▾</button>'
    '</div>'
    '<sc-if value="{{isShorts}}"><div style="display: flex; gap: 2px; padding: 2px; margin: 8px 4px 0; border-radius: 9px; background: {{t.fill}};"><sc-for list="{{shortModes}}" as="q">'
    '<button onClick="{{q.pick}}" style="flex: 1 1 0; height: 24px; border: 0; border-radius: 7px; background: {{q.bg}}; box-shadow: {{q.shadow}}; color: {{t.text}}; font-size: 11px; font-weight: {{q.weight}}; cursor: pointer;">{{q.label}}</button>'
    '</sc-for></div></sc-if>')


# ---- sliders arrastáveis, teclas clicáveis, controles ligados
sub('<div style="position: relative; flex-grow: 1; height: 20px;">',
    '<div data-slider="{{r.id}}" style="position: relative; flex-grow: 1; height: 20px; cursor: pointer;">', 1)
sub('<img src="./img/violin.webp"', '<img src="violin.webp"')
sub('<span style="font-size: 11px; color: {{t.secondary}};">AI performance · 48 kHz</span>',
    '<span style="font-size: 11px; color: {{t.secondary}};">AI performance · 48 kHz</span>\n        <span style="font-size: 11px; color: {{t.tertiary}};">{{gpuName}}</span>')
sub('<span title="{{k.name}}" style="position: absolute; left: {{k.x}}px; top: 0; width: {{k.w}}px; height: 116px;',
    '<span data-note="{{k.note}}" title="{{k.name}}" style="position: absolute; left: {{k.x}}px; top: 0; width: {{k.w}}px; height: 116px;')
sub('<span style="position: absolute; left: {{k.x}}px; top: 0; width: {{k.w}}px; height: 70px;',
    '<span data-note="{{k.note}}" style="position: absolute; left: {{k.x}}px; top: 0; width: {{k.w}}px; height: 70px;')
sub('<span style="position: absolute; left: {{k.x}}px; top: 98px;', '<span style="pointer-events: none; position: absolute; left: {{k.x}}px; top: 98px;')
sub('<span style="font-size: 11px; color: {{t.secondary}};">Solo · Track 3</span>', '<span style="font-size: 11px; color: {{t.secondary}};">Solo · AI performance</span>')
sub('>[Plugin Name]</span>', '>Violino</span>')
sub('<span style="width: 7px; height: 7px; border-radius: 4px; background: {{t.ok}};"></span>{{engineState}}',
    '<span style="width: 7px; height: 7px; border-radius: 4px; background: {{engineDot}};"></span>{{engineState}}')
sub('<span style="display: flex; align-items: center; gap: 8px; margin: 0 4px; font-weight: 600;"><span style="width: 7px; height: 7px; border-radius: 4px; background: {{t.ok}};"></span>AI Render</span>',
    '<span style="display: flex; align-items: center; gap: 8px; margin: 0 4px; font-weight: 600;"><span style="width: 7px; height: 7px; border-radius: 4px; background: {{nowDot}};"></span>{{nowLabel}}</span>')
sub('>Preview takes over where nothing is rendered yet</span>', '>{{nowHint}}</span>')
sub('height: 64%; border-radius: 3px; background: {{t.meter}};', 'height: {{meterL}}%; border-radius: 3px; background: {{t.meter}};')
sub('height: 58%; border-radius: 3px; background: {{t.meter}};', 'height: {{meterR}}%; border-radius: 3px; background: {{t.meter}};')
sub('<div role="img" aria-label="Output gain 0.0 dB" style="position: relative; width: 6px;',
    '<div data-vslider="output" role="slider" aria-label="Output gain" style="cursor: pointer; position: relative; width: 6px;')
sub('<span style="position: absolute; left: 0; right: 0; top: 34%; bottom: 0; border-radius: 3px; background: {{t.accent}};"></span>',
    '<span style="position: absolute; left: 0; right: 0; top: {{outTop}}%; bottom: 0; border-radius: 3px; background: {{t.accent}};"></span>')
sub('left: -9px; top: 30%; width: 24px; height: 38px;', 'left: -9px; top: {{outTop}}%; width: 24px; height: 38px;')
sub('<span style="text-align: center; font-weight: 600; font-variant-numeric: tabular-nums;">0.0 dB</span>',
    '<span style="text-align: center; font-weight: 600; font-variant-numeric: tabular-nums;">{{outText}}</span>')
sub('>Control Room · 4</button>', '>{{gpuShort}}</button>')
sub('<button aria-label="Undo" style="', '<button onClick="{{doUndo}}" title="Undo (Ctrl+Z)" aria-label="Undo" style="opacity: {{undoOp}}; ')
sub('<button aria-label="Redo" style="', '<button onClick="{{doRedo}}" title="Redo (Ctrl+Shift+Z)" aria-label="Redo" style="opacity: {{redoOp}}; ')
sub('<span style="display: flex; align-items: center; gap: 6px; padding: 0 6px; font-size: 12px; color: {{t.secondary}};">', '<button onClick="{{toggleLib}}" title="Classical library (Mutopia) and Import MIDI" style="height: 44px; padding: 0 16px; border: 0; border-radius: 22px; color: {{t.text}}; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; {{t.glass}}">♫ Library</button><span style="display: flex; align-items: center; gap: 6px; padding: 0 6px; font-size: 12px; color: {{t.secondary}};">')
sub('<button aria-label="Settings"', '<button onClick="{{toggleSettings}}" aria-pressed="{{showSettings}}" aria-label="Settings"')

SETTINGS = '''
  <sc-if value="{{showLib}}">
    <div onClick="{{closeLib}}" style="position: absolute; inset: 0; background: rgba(0,0,0,0.22); z-index: 95;"></div>
    <div role="dialog" aria-label="Classical library" style="z-index: 96; position: absolute; left: 50%; top: 70px; width: 560px; height: 640px; margin-left: -280px; box-sizing: border-box; padding: 16px; border-radius: 20px; display: flex; flex-direction: column; gap: 10px; {{t.glass}}">
      <div style="display: flex; align-items: center; gap: 8px;">
        <h2 style="margin: 0 4px; font-size: 15px; font-weight: 700; flex-grow: 1;">Classical library</h2>
        <button onClick="{{libImportFile}}" style="height: 28px; padding: 0 12px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; font-weight: 600; cursor: pointer;">Import MIDI file…</button>
        <button onClick="{{closeLib}}" aria-label="Close" style="width: 28px; height: 28px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; cursor: pointer;">✕</button>
      </div>
      <input onInput="{{libSearch}}" placeholder="Search composer or piece" style="height: 30px; padding: 0 12px; border: 0; border-radius: 10px; background: {{t.fill}}; color: {{t.text}}; font-size: 13px; outline: none;">
      <div style="display: flex; gap: 4px; flex-wrap: wrap;">
        <sc-for list="{{libStyles}}" as="s"><button onClick="{{s.pick}}" style="height: 24px; padding: 0 11px; border: 0; border-radius: 12px; background: {{s.bg}}; color: {{s.fg}}; font-size: 11px; font-weight: 600; cursor: pointer;">{{s.label}}</button></sc-for>
      </div>
      <div style="flex-grow: 1; overflow-y: auto; border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
        <sc-for list="{{libGroups}}" as="g">
          <div style="position: sticky; top: 0; padding: 7px 12px 4px; font-size: 11px; font-weight: 700; color: {{t.secondary}}; background: {{t.card}};">{{g.name}}</div>
          <sc-for list="{{g.items}}" as="it">
            <div class="libi" onClick="{{it.pick}}" title="Import into the timeline (after what is there) and set the Playstyle"><span style="flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{it.title}}</span><span style="font-size: 10px; color: {{t.secondary}}; white-space: nowrap; padding-left: 10px;">{{it.tag}}</span></div>
          </sc-for>
        </sc-for>
      </div>
      <span style="font-size: 10px; color: {{t.tertiary}}; margin: 0 4px;">{{libCount}}</span>
    </div>
  </sc-if>
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
  </sc-if>
  <!-- Settings: placa de vidro sobre tudo -->
  <sc-if value="{{showSettings}}">
    <div onClick="{{closeSettings}}" style="position: absolute; inset: 0; background: rgba(0,0,0,0.16); z-index: 100;"></div>
    <div role="dialog" aria-label="Settings" style="z-index: 101; position: absolute; right: 64px; top: 64px; width: 380px; box-sizing: border-box; padding: 16px; border-radius: 20px; display: flex; flex-direction: column; gap: 8px; {{t.glass}}">
      <div style="display: flex; align-items: center;">
        <h2 style="margin: 0 4px; font-size: 15px; font-weight: 700; flex-grow: 1;">Settings</h2>
        <button onClick="{{closeSettings}}" aria-label="Close" style="width: 28px; height: 28px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; cursor: pointer;">✕</button>
      </div>
      <h3 style="margin: 6px 4px 0; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Interface</h3>
      <div style="border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
        <div style="display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 12px;">
          <span style="flex-grow: 1;">Scale</span>
          <button onClick="{{scaleDown}}" aria-label="Smaller" style="width: 28px; height: 28px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; font-size: 15px; cursor: pointer;">−</button>
          <span style="width: 48px; text-align: center; font-weight: 600; font-variant-numeric: tabular-nums;">{{scaleText}}</span>
          <button onClick="{{scaleUp}}" aria-label="Larger" style="width: 28px; height: 28px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; font-size: 15px; cursor: pointer;">+</button>
        </div>
        <div style="display: flex; gap: 2px; padding: 2px; margin: 0 10px 10px; border-radius: 9px; background: {{t.fill}};">
          <sc-for list="{{scales}}" as="s">
            <button onClick="{{s.pick}}" style="flex: 1 1 0; height: 24px; border: 0; border-radius: 7px; background: {{s.bg}}; box-shadow: {{s.shadow}}; color: {{t.text}}; font-size: 11px; font-weight: {{s.weight}}; cursor: pointer;">{{s.label}}</button>
          </sc-for>
        </div>
      </div>
      <h3 style="margin: 6px 4px 0; font-size: 11px; font-weight: 600; color: {{t.secondary}};">AI model</h3>
      <div style="border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
        <div style="display: flex; align-items: center; height: 44px; padding: 0 12px;">
          <span style="flex-grow: 1;">Load when the plugin opens</span>
          <button onClick="{{toggleAutoLoad}}" aria-pressed="{{autoLoad}}" aria-label="Load model when the plugin opens" style="position: relative; width: 56px; height: 26px; border: 0; border-radius: 13px; background: {{autoLoadTrack}}; cursor: pointer; overflow: visible;">
            <span class="lg-thumb" style="position: absolute; top: 2px; left: {{autoLoadKnob}}px; width: 34px; height: 22px; border-radius: 11px;"></span>
          </button>
        </div>
        <div style="display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 0 12px; border-top: 0.5px solid {{t.sep}};">
          <span style="flex-grow: 1; display: flex; flex-direction: column;"><span>{{modelStatus}}</span><span style="font-size: 11px; color: {{t.secondary}};">{{gpuName}}</span></span>
          <button onClick="{{toggleModel}}" style="height: 28px; padding: 0 12px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; font-weight: 500; cursor: pointer;">{{modelButton}}</button>
        </div>
      </div>
      <h3 style="margin: 6px 4px 0; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Preview samples</h3>
      <div style="border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
        <div style="display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 0 12px;">
          <span style="flex-grow: 1; display: flex; flex-direction: column;"><span style="color: {{samplesColor}};">{{samplesStatus}}</span><span style="font-size: 11px; color: {{t.secondary}};">Solo violin · VSCO 2 CE (CC0)</span></span>
          <button onClick="{{reloadSamples}}" style="height: 28px; padding: 0 12px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.text}}; font-weight: 500; cursor: pointer;">Reload</button>
        </div>
      </div>
      <h3 style="margin: 6px 4px 0; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Renders</h3>
      <div style="border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
        <div style="display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 0 12px;">
          <span style="flex-grow: 1;">Remove all renders (keep the notes)</span>
          <button onClick="{{unrenderAll}}" style="height: 28px; padding: 0 12px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.rec}}; font-weight: 600; cursor: pointer;">Remove</button>
        </div>
      </div>
      <span style="margin: 4px 4px 0; font-size: 10px; line-height: 1.5; color: {{t.tertiary}}; word-break: break-all;">Models: {{modelDir}}<br>Samples: {{sampleDir}}</span>
    </div>
  </sc-if>
'''
end = tpl.rstrip().rfind("</div>")
tpl = tpl[:end] + SETTINGS + "</div>"

js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()
_libp = os.path.join(HERE, "..", "..", "library", "index.json")
js = "const LIBRARY = " + (open(_libp, encoding="utf-8").read() if os.path.exists(_libp) else "[]") + ";\n" + js
init = "fit();\npaint();\nrequestAnimationFrame(frame);"
assert init in js
js = js.replace(init, open(os.path.join(HERE, "fx.js"), encoding="utf-8").read() + "\n" + open(os.path.join(HERE, "score.js"), encoding="utf-8").read() + "\n" + open(os.path.join(HERE, "edit.js"), encoding="utf-8").read() + "\n" + init)
html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Violino</title>
<style>
html,body{{margin:0;height:100%;overflow:hidden;background:#1E1E1F}}
button{{transition:background-color .18s ease,transform .12s ease,box-shadow .2s ease,color .18s ease,opacity .2s ease}}
button:hover{{filter:brightness(1.08)}}
button:active{{transform:scale(0.96)}}
[data-cap]{{transition:top .24s cubic-bezier(.3,1.35,.5,1),left .2s ease,width .2s ease,box-shadow .25s ease,transform .25s cubic-bezier(.3,1.6,.5,1),opacity .25s ease}}
[data-artchip]{{transition:transform .15s ease,box-shadow .2s ease}}
[data-artchip]:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.3)}}
.lg-pill{{background:linear-gradient(180deg,rgba(255,255,255,0.20),rgba(255,255,255,0.07) 55%,rgba(255,255,255,0.10))!important;-webkit-backdrop-filter:blur(16px) saturate(190%);backdrop-filter:blur(16px) saturate(190%);box-shadow:inset 0 1px 0 rgba(255,255,255,0.50),inset 0 -1px 1px rgba(255,255,255,0.10),inset 0 0 0 0.5px rgba(255,255,255,0.18),0 4px 14px rgba(0,0,0,0.28)}}
.lg-pill:hover{{background:linear-gradient(180deg,rgba(255,255,255,0.28),rgba(255,255,255,0.12) 55%,rgba(255,255,255,0.15))!important}}
button:hover{{transform:translateY(-0.5px)}}
button:active{{transform:translateY(0) scale(0.95)!important;transition-duration:.06s}}
.tbb,.tpb,.mvb{{transition:background-color .18s ease,transform .18s cubic-bezier(.3,1.5,.5,1),box-shadow .2s ease,color .18s ease,opacity .2s ease}}
.tbb:hover,.tpb:hover{{box-shadow:inset 0 1px 0 rgba(255,255,255,0.18)}}
button .lg-thumb{{transition:left .32s cubic-bezier(.3,1.45,.45,1)}}
@keyframes tabIn{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
.tabin{{animation:tabIn .28s cubic-bezier(.2,.8,.2,1) both}}
@keyframes popIn{{from{{opacity:0;transform:translateY(-4px) scale(.97)}}to{{opacity:1;transform:none}}}}
.pmi{{animation:popIn .14s ease-out both}}
[data-overview] span,[data-cyc]{{transition:left .12s ease,width .12s ease}}
.light .lg-pill{{background:rgba(255,255,255,0.78)!important;box-shadow:inset 0 0.5px 0 #fff,0 0 0 0.5px rgba(0,0,0,0.08),0 2px 8px rgba(0,0,0,0.08)}}
.light .lg-pill:hover{{background:#FFFFFF!important}}
.tbb{{height:22px;min-width:26px;padding:0 8px;border:0;border-radius:11px;background:rgba(127,127,127,0.16);color:inherit;font-size:11px;font-weight:600;cursor:pointer;white-space:nowrap;display:flex;align-items:center;justify-content:center}}
.tbb:hover{{background:rgba(127,127,127,0.28)}}
.mvb{{width:32px;height:22px;padding:0;border:0;border-radius:8px;background:transparent;color:inherit;font-size:9px;font-weight:600;cursor:pointer}}
.mvb:hover{{background:rgba(127,127,127,0.2)}}
.tpb{{display:flex;align-items:center;justify-content:center;height:36px;border:0;border-radius:18px;background:transparent;color:inherit;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;box-sizing:border-box;flex-shrink:0}}
.scb{{width:28px;height:28px;padding:0;border-radius:8px;border:1px solid rgba(59,42,26,0.3);cursor:pointer;font-family:Georgia,serif;font-size:14px;line-height:1}}
.scb:hover{{filter:brightness(1.1)}}
.libi{{display:flex;align-items:center;height:30px;padding:0 12px;border-top:0.5px solid rgba(127,127,127,0.18);cursor:pointer;font-size:12px}}
.libi:hover{{background:rgba(10,132,255,0.16)}}
.pmi{{display:flex;align-items:center;height:24px;padding:0 8px 0 4px;border-radius:6px;cursor:pointer;white-space:nowrap}}
.pmi:hover{{background:#0A84FF}}
.tpg{{display:flex;align-items:center;gap:4px}}
#root{{user-select:none;-webkit-user-select:none}}
input{{user-select:text;-webkit-user-select:text}}
.vmove [data-cap]{{transition:box-shadow .25s ease,opacity .25s ease!important}}
[data-vstem]{{transition:top .15s ease,height .15s ease}}
.vmove [data-vstem]{{transition:none}}
@keyframes vbounce{{0%{{transform:translateY(0) scale(1)}}40%{{transform:translateY(-3px) scale(1.06)}}100%{{transform:translateY(-1px) scale(1.04)}}}}
.playing{{animation:vbounce .35s cubic-bezier(.3,1.6,.5,1) forwards}}
#root{{position:absolute;left:0;top:0;transform-origin:0 0}}
::-webkit-scrollbar{{width:8px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:rgba(127,127,127,0.35);border-radius:4px}}::-webkit-scrollbar-button{{display:none}}
{style.strip()}
</style>
</head>
<body>
<div id="root"></div>
<template id="tpl">
{tpl}
</template>
<script>
{js}
</script>
</body>
</html>
"""
open(os.path.join(HERE, "index.html"), "w", encoding="utf-8").write(html)
print("ui/index.html", len(html) // 1024, "KB")
