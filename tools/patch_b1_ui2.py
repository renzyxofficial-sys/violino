"""Bloco 1 / frases e interface: render/remover render/excluir take por frase, remover todos os renders,
Drag All Audio, MIDI com e sem dynamics, nomes das notas, nota inteira na cor da articulação, chips sem
sobreposição, linha vermelha só na timeline, 125 %, fundo gradiente, animações, brilho na nota tocando,
Mix Styles na página principal, botões de vidro."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


# ------------------------------------------------------------------ template
b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """html,body{{margin:0;height:100%;overflow:hidden;background:#1E1E1F}}""", """html,body{{margin:0;height:100%;overflow:hidden;background:#1E1E1F}}
button{{transition:background-color .18s ease,transform .12s ease,box-shadow .2s ease,color .18s ease,opacity .2s ease}}
button:hover{{filter:brightness(1.08)}}
button:active{{transform:scale(0.96)}}
[data-cap]{{transition:top .24s cubic-bezier(.3,1.35,.5,1),left .2s ease,width .2s ease,box-shadow .25s ease,transform .25s cubic-bezier(.3,1.6,.5,1),opacity .25s ease}}
[data-artchip]{{transition:transform .15s ease,box-shadow .2s ease}}
[data-artchip]:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.3)}}
.lg-pill{{background:rgba(255,255,255,0.12)!important;-webkit-backdrop-filter:blur(14px) saturate(180%);backdrop-filter:blur(14px) saturate(180%);box-shadow:inset 0 0.5px 0 rgba(255,255,255,0.45),inset 0 0 0 0.5px rgba(255,255,255,0.16),0 4px 14px rgba(0,0,0,0.28)}}
.lg-pill:hover{{background:rgba(255,255,255,0.2)!important}}
@keyframes vbounce{{0%{{transform:translateY(0) scale(1)}}40%{{transform:translateY(-3px) scale(1.06)}}100%{{transform:translateY(-1px) scale(1.04)}}}}
.playing{{animation:vbounce .35s cubic-bezier(.3,1.6,.5,1) forwards}}""")
# botões da frase (vidro) + ações
b = rep(b, """            <button onClick="{{r.listen}}" title="Listen to this phrase here, before using it in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{r.listenBg}}; color: {{r.listenFg}}; font-size: 11px; font-weight: 600; cursor: pointer;">{{r.listenLabel}}</button>""",
        """            <button class="lg-pill" onClick="{{r.listen}}" title="Listen to this phrase here, before using it in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{r.listenBg}}; color: {{r.listenFg}}; font-size: 11px; font-weight: 600; cursor: pointer;">{{r.listenLabel}}</button>""")
b = rep(b, """style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{t.fill}}; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">⠿ Audio</button>""",
        """class="lg-pill" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">⠿ Audio</button>""")
b = rep(b, """            <button data-dragmidi="{{r.i}}" title="Drag this phrase as MIDI onto a MIDI track in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{t.fill}}; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">♪ MIDI</button>""",
        """            <button data-dragmidi="{{r.i}}" title="Drag as MIDI (notes only)" class="lg-pill" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">♪ MIDI</button>
            <button data-dragmidi="{{r.i}}" data-dyn="1" title="Drag as MIDI with the dynamics curve (CC1 + CC11)" class="lg-pill" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">♪ + Dyn</button>""")
b = rep(b, """        <sc-if value="{{r.playing}}">""", """        <sc-if value="{{r.actions}}">
          <div style="position: absolute; left: {{r.ax}}px; top: 410px; display: flex; gap: 4px; z-index: 6;">
            <button class="lg-pill" onClick="{{r.doRender}}" title="{{r.renderTitle}}" style="height: 22px; min-width: 26px; padding: 0 7px; border: 0; border-radius: 11px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: pointer;">↻</button>
            <button class="lg-pill" onClick="{{r.doUnrender}}" title="Remove this render (keep the notes)" style="height: 22px; min-width: 26px; padding: 0 7px; border: 0; border-radius: 11px; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: pointer;">⊘</button>
            <button class="lg-pill" onClick="{{r.doDelete}}" title="Delete this take (notes and render)" style="height: 22px; min-width: 26px; padding: 0 7px; border: 0; border-radius: 11px; color: {{t.rec}}; font-size: 11px; font-weight: 600; cursor: pointer;">🗑</button>
          </div>
        </sc-if>
        <sc-if value="{{r.playing}}">""")
# notas: cor inteira da articulação, nome, brilho ao tocar
b = rep(b, """        <span data-cap="{{n.i}}" title="{{n.title}}" style="position: absolute; left: {{n.x}}px; top: {{n.y}}px; width: {{n.w}}px; height: 10px; border-radius: 5px; background: {{n.color}}; box-shadow: {{n.ring}}; cursor: {{n.cursor}};"><span style="position: absolute; left: 0; top: 0; bottom: 0; width: 4px; border-radius: 5px 0 0 5px; background: {{n.art}};"></span></span>""",
        """        <span data-cap="{{n.i}}" class="{{n.cls}}" title="{{n.title}}" style="position: absolute; left: {{n.x}}px; top: {{n.y}}px; width: {{n.w}}px; height: 12px; border-radius: 6px; background: {{n.art}}; opacity: {{n.op}}; box-shadow: {{n.ring}}; cursor: {{n.cursor}}; overflow: hidden;"><span style="position: absolute; left: 4px; top: 0; font-size: 8px; font-weight: 700; line-height: 12px; color: {{n.fg}}; pointer-events: none; white-space: nowrap;">{{n.name}}</span></span>""")
# linha vermelha só na área da timeline
b = rep(b, """<span style="position: absolute; left: {{playX}}px; top: 112px; bottom: 0; width: 1.5px; background: {{t.rec}}; pointer-events: none;"></span>""",
        """<span style="position: absolute; left: {{playX}}px; top: 112px; height: 330px; width: 1.5px; background: {{t.rec}}; pointer-events: none; box-shadow: 0 0 6px {{t.rec}};"></span>""")
# transporte: Drag All Audio
b = rep(b, "# ---- sliders arrastáveis, teclas clicáveis, controles ligados", """sub('<span style="width: 0.5px; height: 24px; background: {{t.sep}}; margin: 0 4px;"></span>',
    '<button data-dragall="1" class="lg-icon" title="Drag ALL rendered audio as one WAV onto a track in your DAW" style="height: 40px; padding: 0 10px; border: 0; border-radius: 20px; color: {{t.text}}; font-size: 12px; font-weight: 600; cursor: grab;">⠿ All</button><span style="width: 0.5px; height: 24px; background: {{t.sep}}; margin: 0 4px;"></span>')

# ---- sliders arrastáveis, teclas clicáveis, controles ligados""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

# Mix Styles na página principal (barra lateral) e remover todos os renders (Settings)
b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """    '<sc-if value="{{isShorts}}">""", """    '<h2 style="margin: 12px 8px 4px; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Sound</h2>'
    '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 3px; margin: 0 4px;"><sc-for list="{{mixes}}" as="m">'
    '<button onClick="{{m.pick}}" title="{{m.hint}}" style="height: 24px; border: 0; border-radius: 7px; background: {{m.sideBg}}; color: {{m.sideFg}}; font-size: 11px; font-weight: 600; cursor: pointer;">{{m.label}}</button>'
    '</sc-for></div>'
    '<sc-if value="{{isShorts}}">""")
b = rep(b, """      <span style="margin: 4px 4px 0; font-size: 10px; line-height: 1.5; color: {{t.tertiary}}; word-break: break-all;">Models: {{modelDir}}<br>Samples: {{sampleDir}}</span>""",
        """      <h3 style="margin: 6px 4px 0; font-size: 11px; font-weight: 600; color: {{t.secondary}};">Renders</h3>
      <div style="border-radius: 12px; background: {{t.card}}; box-shadow: {{t.cardShadow}};">
        <div style="display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 0 12px;">
          <span style="flex-grow: 1;">Remove all renders (keep the notes)</span>
          <button onClick="{{unrenderAll}}" style="height: 28px; padding: 0 12px; border: 0; border-radius: 14px; background: {{t.fill}}; color: {{t.rec}}; font-weight: 600; cursor: pointer;">Remove</button>
        </div>
      </div>
      <span style="margin: 4px 4px 0; font-size: 10px; line-height: 1.5; color: {{t.tertiary}}; word-break: break-all;">Models: {{modelDir}}<br>Samples: {{sampleDir}}</span>""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

# ------------------------------------------------------------------ app.js
a = open("ui/app.js", encoding="utf-8").read()
# fundo gradiente estilo Apple nos dois temas
a = rep(a, "    content: '#1E1E1F', card: '#2A2A2C',",
        "    content: 'radial-gradient(1100px 720px at 12% -8%, rgba(88,86,214,0.30), transparent 60%), radial-gradient(900px 640px at 105% 108%, rgba(10,132,255,0.22), transparent 58%), radial-gradient(700px 500px at 60% 40%, rgba(191,90,242,0.08), transparent 70%), #121215', card: '#2A2A2C',")
a = rep(a, "    content: '#F7F7F9', card: '#FFFFFF',",
        "    content: 'radial-gradient(1100px 720px at 10% -10%, rgba(120,130,255,0.20), transparent 60%), radial-gradient(900px 640px at 105% 110%, rgba(255,140,190,0.16), transparent 58%), #F4F4F7', card: '#FFFFFF',")
a = rep(a, "  document.body.style.background = t.content;", "  document.body.style.background = dark ? '#121215' : '#F4F4F7';")
# notas: cor da articulação, nome, brilho/bounce na nota tocando
a = rep(a, """    return { i, x: X(c[0]), y: Y(c[2]) - 1, w: Math.max(X(c[1]) - X(c[0]) - 2, 6), color: noteColor[stateAt(c[0])] || t.noteFuture,
      art: AC[art] || AC.auto, ring: sel.has(i) ? '0 0 0 2px #FFFFFF' : 'none', cursor: 'grab',""",
"""    const st = stateAt(c[0]), w = Math.max(X(c[1]) - X(c[0]) - 2, 6);
    const live = S && (S.internalPlay || S.playing) && playhead >= c[0] && playhead < c[1];
    const NN = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    return { i, x: X(c[0]), y: Y(c[2]) - 2, w, color: noteColor[st] || t.noteFuture,
      art: AC[art] || AC.auto, op: st === 1 ? 1 : st === 2 ? 0.85 : 0.6, fg: TXT(art),
      name: w > 24 ? NN[((c[2] % 12) + 12) % 12] + (Math.floor(c[2] / 12) - 1) : '', cls: live ? 'playing' : '',
      ring: sel.has(i) ? '0 0 0 2px #FFFFFF' : live ? `0 0 0 1px #fff, 0 0 14px ${AC[art] || AC.auto}` : 'none', cursor: 'grab',""")
# chips da faixa Articulation: um por nota, nunca invadindo o próximo
a = rep(a, """  const lane = [];
  for (const n of vis) {
    const last = lane[lane.length - 1];
    if (last && last.id === n[3] && n[0] - last.end < 0.3) { last.end = n[1]; continue; }
    lane.push({ id: n[3], start: n[0], end: n[1], why: n[5] });
  }""", """  const lane = vis.map((n) => ({ id: n[3], start: n[0], end: n[1], why: n[5] }));""")
# frases: ações
a = rep(a, """      playing: playingThis, cursorX: X(p[5] + ((S && S.auditionPos) || 0)) };""",
"""      playing: playingThis, cursorX: X(p[5] + ((S && S.auditionPos) || 0)),
      actions: !p[4] && w > 100, ax: x + 10, renderTitle: p[2] === 1 ? 'Render this phrase again' : 'Render this phrase',
      doRender: () => send({ cmd: p[2] === 1 ? 'reRender' : 'renderPhrase', phrase: i }),
      doUnrender: () => send({ cmd: 'unrender', phrase: i }), doDelete: () => send({ cmd: 'deleteTake', phrase: i }) };""")
a = rep(a, "      bx: x + w - 196,", "      bx: x + w - 262,")
a = rep(a, "done: p[2] === 1 && w > 210,", "done: p[2] === 1 && w > 280,")
# Mix Styles na lateral
a = rep(a, "  const mixes = mixInfo.map(([label, hint], i) => ({ label, hint, on: mix === i, pick: () => setV('mixStyle', i), ring: mix === i ? '0 0 0 2px ' + t.accent : t.cardShadow }));",
        "  const mixes = mixInfo.map(([label, hint], i) => ({ label, hint, on: mix === i, pick: () => setV('mixStyle', i), ring: mix === i ? '0 0 0 2px ' + t.accent : t.cardShadow,\n    sideBg: mix === i ? t.accent : t.fill, sideFg: mix === i ? '#FFFFFF' : t.text }));")
a = rep(a, "    ...settingsVals(t, seg, en),", "    ...settingsVals(t, seg, en),\n    unrenderAll: () => send({ cmd: 'unrenderAll' }),")
# Drag All, MIDI com/sem dyn, prévia da nota ao mover/criar
a = rep(a, """  if (dm) { send({ cmd: 'dragMidi', phrase: +dm.dataset.dragmidi }); e.preventDefault(); return; }""",
        """  if (dm) { send({ cmd: 'dragMidi', phrase: +dm.dataset.dragmidi, dyn: dm.dataset.dyn === '1' }); e.preventDefault(); return; }
  const da = e.target.closest('[data-dragall]');
  if (da) { send({ cmd: 'dragAll' }); e.preventDefault(); return; }""")
a = rep(a, """    if (nd.dt || nd.dp) send(nd.resize ? { cmd: 'noteEdit', ids: [...L.sel], dt: 0, de: nd.dt || 0, dp: 0 } : { cmd: 'noteEdit', ids: [...L.sel], dt: nd.dt || 0, de: 0, dp: nd.dp || 0 });""",
        """    if (nd.dt || nd.dp) send(nd.resize ? { cmd: 'noteEdit', ids: [...L.sel], dt: 0, de: nd.dt || 0, dp: 0 } : { cmd: 'noteEdit', ids: [...L.sel], dt: nd.dt || 0, de: 0, dp: nd.dp || 0 });
    if (nd.dp && S && S.cap) { const first = [...L.sel][0], c = S.cap[first]; if (c) previewNote(c[2] + nd.dp); }""")
a = rep(a, """  send({ cmd: 'noteAdd', s: tt, e: tt + 0.5, p });""", """  send({ cmd: 'noteAdd', s: tt, e: tt + 0.5, p });
  previewNote(p);""")
a = rep(a, """function chipMove(e) {""", """function previewNote(p) {  // toca a nota para o usuário ouvir a altura
  send({ cmd: 'key', note: p, on: true });
  setTimeout(() => send({ cmd: 'key', note: p, on: false }), 350);
}
function chipMove(e) {""")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
