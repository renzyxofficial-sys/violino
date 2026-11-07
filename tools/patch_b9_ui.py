import os
os.chdir(r"C:\Users\TheoH\violino")
def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)
patch('plugin/ui/build_ui.py', [(
"""    '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 3px; margin: 0 4px;"><sc-for list="{{mixes}}" as="m">'
    '<button onClick="{{m.pick}}" title="{{m.hint}}" style="height: 24px; border: 0; border-radius: 7px; background: {{m.sideBg}}; color: {{m.sideFg}}; font-size: 11px; font-weight: 600; cursor: pointer;">{{m.label}}</button>'
    '</sc-for></div>'""",
"""    '<div style="display: flex; gap: 4px; margin: 0 4px;">'
    '<button onClick="{{mixPick}}" title="Mix preset: room, reverb and tone" style="flex: 1 1 0; min-width: 0; height: 26px; padding: 0 8px; border: 0; border-radius: 8px; background: {{t.accent}}; color: #FFFFFF; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Mix · {{mixName}} ▾</button>'
    '<button onClick="{{stylePick}}" title="Playstyle: how notes are connected, portamento, dynamics and vibrato" style="flex: 1 1 0; min-width: 0; height: 26px; padding: 0 8px; border: 0; border-radius: 8px; background: {{styleBg}}; color: {{styleFg}}; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">Style · {{styleName}} ▾</button>'
    '</div>'""")])
patch('plugin/ui/app.js', [
    (", slider('playStyle', 'Playstyle', 6), slider('vibAmount', 'Extra vibrato', 7), slider('vibRate', 'Vibrato rate', 8)];",
     ", slider('vibAmount', 'Extra vibrato', 6), slider('vibRate', 'Vibrato rate', 7)];"),
    ("    sideBg: mix === i ? t.accent : t.fill, sideFg: mix === i ? '#FFFFFF' : t.text }));",
     """    sideBg: mix === i ? t.accent : t.fill, sideFg: mix === i ? '#FFFFFF' : t.text }));
  // Sound Presets: Mix (sala, reverb, timbre) e Playstyle (ligado, portamento, dinâmica, vibrato) lado a lado
  const STYLES = [['Natural', 'As played · your Instrument settings'], ['Lyrical', 'Singing · smooth, a little more vibrato'], ['Romantic', 'Slides and wide dynamics · more vibrato'],
    ['Classical', 'Clean and articulate · little portamento'], ['Baroque', 'Detached · no portamento, gentle dynamics'], ['Cinematic', 'Everything connected · big dynamics']];
  const sty = idx('playStyle');
  const menuAt = (e) => { const pt = cpt(e); return [pt.x - 10, pt.y + 16]; };
  const mixPick = (e) => openMenu(...menuAt(e), [{ head: 'Mix preset' }, ...mixInfo.map(([label, hint], i) => ({ label, key: hint, check: mix === i, pick: () => setV('mixStyle', i) }))]);
  const stylePick = (e) => openMenu(...menuAt(e), [{ head: 'Playstyle' }, ...STYLES.map(([label, hint], i) => ({ label, key: hint, check: sty === i, pick: () => setV('playStyle', i) }))]);"""),
    ("    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes, fxModules,",
     "    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes, fxModules, mixPick, stylePick,\n    mixName: mixInfo[mix] ? mixInfo[mix][0] : 'Dry', styleName: STYLES[sty] ? STYLES[sty][0] : 'Natural', styleBg: sty ? t.accent : t.fill, styleFg: sty ? '#FFFFFF' : t.text,"),
])
print('ok')
