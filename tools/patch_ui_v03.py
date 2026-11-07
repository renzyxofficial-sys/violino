"""UI v0.3: aba Effects com módulos (EQ, Compressor, Saturation, Chorus, Delay, Stereo, Reverb),
Play/Stop e Lock MIDI no transporte, chips de articulação sem sobreposição, playhead do Play interno."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\ui")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:80])
    return s.replace(old, new)


b = open("build_ui.py", encoding="utf-8").read()
b = rep(b, """# ---- sliders arrastáveis, teclas clicáveis, controles ligados""", '''# ---- aba Effects: Mix Style + módulos com liga/desliga
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

# ---- transporte: Play/Stop e Lock MIDI
sub(\'\'\'    <button onClick="{{toggleCapture}}" aria-pressed="{{capOn}}"\'\'\', \'\'\'    <button onClick="{{doPlay}}" aria-label="{{playLabel}}" title="{{playLabel}}" style="width: 40px; height: 40px; border: 0; border-radius: 20px; background: {{playBg}}; color: {{playFg}}; cursor: pointer;"><svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="{{playIcon}}" fill="currentColor"></path></svg></button>
    <button onClick="{{toggleCapture}}" aria-pressed="{{capOn}}"\'\'\')
sub(\'\'\'      <span style="width: 12px; height: 12px; border-radius: 6px; background: {{capDot}};"></span>Capture
    </button>\'\'\', \'\'\'      <span style="width: 12px; height: 12px; border-radius: 6px; background: {{capDot}};"></span>Capture
    </button>
    <button onClick="{{toggleLock}}" aria-pressed="{{lockOn}}" title="Lock MIDI: keep what is captured, nothing is overwritten" style="display: flex; align-items: center; gap: 6px; height: 40px; padding: 0 12px; border: 0; border-radius: 20px; background: {{lockBg}}; color: {{lockFg}}; font-size: 13px; font-weight: 600; cursor: pointer;"><svg width="13" height="14" viewBox="0 0 13 14" aria-hidden="true"><path d="{{lockIcon}}" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path></svg>Lock</button>\'\'\')
sub(\'<span style="position: relative; display: block; width: 110px; height: 24px; margin: 0 12px 0 4px;">\', \'<span style="position: relative; display: block; width: 80px; height: 24px; margin: 0 12px 0 4px;">\')

# ---- sliders arrastáveis, teclas clicáveis, controles ligados''')
# a troca dos 3 sliders agora só vale para a aba Instrument (os de Effects já vêm com data-slider)
b = rep(b, """sub('<div style="position: relative; flex-grow: 1; height: 20px;">',
    '<div data-slider="{{r.id}}" style="position: relative; flex-grow: 1; height: 20px; cursor: pointer;">', 3)""",
"""sub('<div style="position: relative; flex-grow: 1; height: 20px;">',
    '<div data-slider="{{r.id}}" style="position: relative; flex-grow: 1; height: 20px; cursor: pointer;">', 1)""")
b = rep(b, """sub(\"\"\"              <span style="display: flex; align-items: center; gap: 6px; height: 24px; padding: 0 10px; border-radius: 7px; background: {{t.fill}}; font-weight: 500;">{{roomName}}\"\"\",
    \"\"\"              <span onClick="{{nextRoom}}" style="display: flex; align-items: center; gap: 6px; height: 24px; padding: 0 10px; border-radius: 7px; background: {{t.fill}}; font-weight: 500; cursor: pointer;">{{roomName}}\"\"\")
""", "")
open("build_ui.py", "w", encoding="utf-8").write(b)

a = open("app.js", encoding="utf-8").read()
# chips de articulação: um por trecho de mesma técnica, sem se sobrepor
a = rep(a, """  const laneOut = lane.map((c) => {
    const x = Math.max(268, X(c.start)), w = Math.max(22, Math.min(1058, X(c.end)) - x - 3);
    return { x, w, label: w > 46 ? ART_NAMES[c.id] : '', bg: AC[c.id], fg: TXT(c.id), title: `${ART_NAMES[c.id]}: ${c.why}` };
  });""", """  const laneOut = [];
  for (let k = 0; k < lane.length; k++) {
    const c = lane[k];
    const x = Math.max(268, X(c.start));
    const nextX = k + 1 < lane.length ? X(lane[k + 1].start) : 1058;
    const w = Math.max(6, Math.min(Math.max(X(c.end) - x, 10), nextX - x - 2));  // nunca invade o próximo
    laneOut.push({ x, w, label: w > 52 ? ART_NAMES[c.id] : '', bg: AC[c.id], fg: TXT(c.id), title: `${ART_NAMES[c.id]}: ${c.why}` });
  }""")
a = rep(a, """    lane.push({ id: n[3], start: n[0], end: n[1], why: n[5] });""", """    lane.push({ id: n[3], start: n[0], end: n[1], why: n[5] });
  }
  lane.sort((p, q) => p.start - q.start);
  for (let k = 0; k < 0; k++) {""")
# playhead do Play interno
a = rep(a, """  const playhead = (S && S.playhead) || 0;""", """  const playhead = S ? (S.internalPlay ? S.internalPos : S.playhead) || 0 : 0;""")
# valores novos
a = rep(a, """  const revSliders = [slider('reverbMix', 'Mix', 0), slider('decay', 'Decay', 1), slider('predelay', 'Pre-delay', 2)];""",
"""  const revSliders = [slider('reverbMix', 'Mix', 0), slider('decay', 'Decay', 1), slider('predelay', 'Pre-delay', 2)];
  const fs = (id, label, bipolar) => {
    const pct = P(id).n * 100;
    return { id, label, pct, value: P(id).text, fillLeft: bipolar ? Math.min(50, pct) : 0, fillW: bipolar ? Math.abs(pct - 50) : pct };
  };
  const mod = (label, onId, sliders, extra) => {
    const on = P(onId).v > 0.5;
    return { label, on, toggle: () => setV(onId, on ? 0 : 1), track: on ? t.green : t.off, knob: on ? 18 : 2, opacity: on ? 1 : 0.5, sliders, ...extra };
  };
  const fxModules = [
    mod('Equalizer', 'eqOn', [fs('eqLow', 'Low', true), fs('eqMid', 'Mid', true), fs('eqHigh', 'High', true), fs('eqAir', 'Air', true)]),
    mod('Compressor', 'compOn', [fs('compThresh', 'Threshold'), fs('compRatio', 'Ratio'), fs('compAttack', 'Attack'), fs('compRelease', 'Release'), fs('compMakeup', 'Makeup')]),
    mod('Stereo', 'stereoOn', [fs('stereoWidth', 'Width')]),
    mod('Saturation', 'satOn', [fs('satDrive', 'Drive')]),
    mod('Chorus', 'chorusOn', [fs('chorusRate', 'Rate'), fs('chorusDepth', 'Depth'), fs('chorusMix', 'Mix')]),
    mod('Delay', 'delayOn', [fs('delayTime', 'Time'), fs('delayFeedback', 'Feedback'), fs('delayMix', 'Mix')]),
    mod('Reverb', 'reverb', [fs('reverbMix', 'Mix'), fs('decay', 'Decay'), fs('predelay', 'Pre-delay')], { room: true })
  ];""")
a = rep(a, """    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes,""",
"""    dynLine, dynArea, lane: laneOut, summary, instSliders, eqSliders, revSliders, mixes, fxModules,
    doPlay: () => send({ cmd: 'play' }), playLabel: S && S.internalPlay ? 'Stop' : 'Play rendered phrases',
    playIcon: S && S.internalPlay ? 'M3 3h8v8H3z' : 'M4 2.5v9l7.5-4.5z',
    playBg: S && S.internalPlay ? t.ok : t.fill, playFg: S && S.internalPlay ? '#FFFFFF' : t.text,
    lockOn: P('lock').v > 0.5, toggleLock: () => setV('lock', P('lock').v > 0.5 ? 0 : 1),
    lockBg: P('lock').v > 0.5 ? 'rgba(255,149,0,0.18)' : t.fill, lockFg: P('lock').v > 0.5 ? t.warn : t.text,
    lockIcon: P('lock').v > 0.5 ? 'M3.5 6.5V4.5a3 3 0 016 0v2M2 6.5h9v6H2z' : 'M3.5 6.5V4.5a3 3 0 015.6-1.5M2 6.5h9v6H2z',""")
open("app.js", "w", encoding="utf-8").write(a)
print("ok")
