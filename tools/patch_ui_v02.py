"""UI v0.2: painel Settings (escala 75–200 %, carregar ao abrir, samples), forma de onda nas frases,
Listen/Stop e alça Drag. Edita ui/build_ui.py (template) e ui/app.js (valores)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\ui")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:80])
    return s.replace(old, new)


b = open("build_ui.py", encoding="utf-8").read()
# frase: forma de onda, botões Listen/Drag, cursor da audição
b = rep(b, """        <span style="position: absolute; left: {{r.lx}}px; top: 150px; font-size: 11px; font-weight: 600; color: {{r.color}}; white-space: nowrap; pointer-events: none;">{{r.label}}</span>""",
"""        <span style="position: absolute; left: {{r.lx}}px; top: 150px; font-size: 11px; font-weight: 600; color: {{r.color}}; white-space: nowrap; pointer-events: none;">{{r.label}}</span>
        <sc-if value="{{r.wave}}">
          <svg style="position: absolute; left: {{r.x}}px; top: 170px; pointer-events: none;" width="{{r.w}}" height="260" viewBox="0 0 {{r.w}} 260" aria-hidden="true"><path d="{{r.wave}}" fill="{{r.waveFill}}"></path></svg>
        </sc-if>
        <sc-if value="{{r.done}}">
          <div style="position: absolute; left: {{r.bx}}px; top: 144px; display: flex; gap: 4px;">
            <button onClick="{{r.listen}}" title="Listen to this phrase here, before using it in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{r.listenBg}}; color: {{r.listenFg}}; font-size: 11px; font-weight: 600; cursor: pointer;">{{r.listenLabel}}</button>
            <button data-drag="{{r.i}}" title="Drag this phrase onto an audio track in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{t.fill}}; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">⠿ Drag</button>
          </div>
        </sc-if>
        <sc-if value="{{r.playing}}">
          <span style="position: absolute; left: {{r.cursorX}}px; top: 140px; width: 1.5px; height: 300px; background: {{t.ok}}; pointer-events: none;"></span>
        </sc-if>""")
b = rep(b, """sub('>Fit</button>', ' onClick="{{doFit}}">Fit</button>'.replace(' onClick', '', 0) if False else '>Fit</button>')\n""", "", 0) if False else b
# engrenagem abre o painel
b = rep(b, """js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()""", """sub('<button aria-label="Settings"', '<button onClick="{{toggleSettings}}" aria-pressed="{{showSettings}}" aria-label="Settings"')

SETTINGS = '''
  <!-- Settings: placa de vidro sobre tudo -->
  <sc-if value="{{showSettings}}">
    <div onClick="{{closeSettings}}" style="position: absolute; inset: 0; background: rgba(0,0,0,0.16);"></div>
    <div role="dialog" aria-label="Settings" style="position: absolute; right: 64px; top: 64px; width: 380px; box-sizing: border-box; padding: 16px; border-radius: 20px; display: flex; flex-direction: column; gap: 8px; {{t.glass}}">
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
      <span style="margin: 4px 4px 0; font-size: 10px; line-height: 1.5; color: {{t.tertiary}}; word-break: break-all;">Models: {{modelDir}}<br>Samples: {{sampleDir}}</span>
    </div>
  </sc-if>
'''
end = tpl.rstrip().rfind("</div>")
tpl = tpl[:end] + SETTINGS + "</div>"

js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()""")
open("build_ui.py", "w", encoding="utf-8").write(b)

a = open("app.js", encoding="utf-8").read()
# alça Drag: começa o arrasto no C++ enquanto o botão está pressionado
a = rep(a, """  const k = e.target.closest('[data-note]');""", """  const d = e.target.closest('[data-drag]');
  if (d) { send({ cmd: 'drag', phrase: +d.dataset.drag }); e.preventDefault(); return; }
  const k = e.target.closest('[data-note]');""")
a = rep(a, """    return { x, w, lx: x + 12, label, color, fill, busy: p[2] === 2 && p[3] > 0, barW: Math.max(20, w - 24), progW: Math.max(2, (w - 24) * p[3]),
      cursor: p[2] === 1 ? 'pointer' : 'default', title: p[2] === 1 ? 'Click to listen to this phrase' : '',
      pick: () => { if (p[2] === 1) send({ cmd: 'audition', phrase: i }); } };""", """    // forma de onda do render (picos a cada 50 ms desde a origem da frase)
    let wave = '';
    const peaks = p[6];
    if (p[2] === 1 && Array.isArray(peaks) && peaks.length) {
      const top = [], bot = [];
      for (let k = 0; k < peaks.length; k++) {
        const px = X(p[5] + k * 0.05) - x;
        if (px < 0 || px > w) continue;
        const amp = peaks[k] / 100 * 110;
        top.push(px.toFixed(1) + ',' + (130 - amp).toFixed(1));
        bot.push(px.toFixed(1) + ',' + (130 + amp).toFixed(1));
      }
      if (top.length > 1) wave = 'M' + top.join('L') + 'L' + bot.reverse().join('L') + 'Z';
    }
    const playingThis = S && S.audition === i;
    return { i, x, w, lx: x + 12, label, color, fill, busy: p[2] === 2 && p[3] > 0, barW: Math.max(20, w - 24), progW: Math.max(2, (w - 24) * p[3]),
      cursor: p[2] === 1 ? 'pointer' : 'default', title: p[2] === 1 ? 'Click to listen to this phrase' : '',
      pick: () => { if (p[2] === 1) send({ cmd: 'audition', phrase: i }); },
      wave, waveFill: dark ? 'rgba(48,209,88,0.16)' : 'rgba(40,167,69,0.14)', done: p[2] === 1 && w > 150,
      bx: x + w - 128, listen: () => send({ cmd: 'audition', phrase: i }), listenLabel: playingThis ? '■ Stop' : '▶ Listen',
      listenBg: playingThis ? t.ok : t.fill, listenFg: playingThis ? '#FFFFFF' : t.text,
      playing: playingThis, cursorX: X(p[5] + ((S && S.auditionPos) || 0)) };""")
a = rep(a, """  else if (!en.samples) engineState = 'Loading samples…', engineDot = t.warn;""", """  else if (en.samplesState === 3) engineState = 'Samples error: ' + (en.samplesError || 'unknown'), engineDot = t.rec;
  else if (!en.samples) engineState = 'Loading samples…', engineDot = t.warn;""")
a = rep(a, """    doFit: () => { L.zoom = 1; dirty = true; }, zoom: L.zoom, zoomPct: (L.zoom - 1) / 7 * 100,""", """    doFit: () => { L.zoom = 1; dirty = true; }, zoom: L.zoom, zoomPct: (L.zoom - 1) / 7 * 100,
    ...settingsVals(t, seg, en),""")
a = rep(a, """fit();
paint();""", """// ---- painel Settings
function settingsVals(t, seg, en) {
  const st = (S && S.settings) || {};
  const scale = L.scale ?? st.scale ?? 1;
  const setScale = (v) => { v = Math.round(Math.min(2, Math.max(0.75, v)) * 20) / 20; L.scale = v; send({ cmd: 'setting', key: 'uiScale', value: v }); dirty = true; };
  const autoLoad = L.autoLoad ?? (st.autoLoad !== false);
  const ss = en.samplesState;
  return {
    showSettings: !!L.settings, toggleSettings: () => { L.settings = !L.settings; dirty = true; }, closeSettings: () => { L.settings = false; dirty = true; },
    scaleText: Math.round(scale * 100) + '%', scaleDown: () => setScale(scale - 0.05), scaleUp: () => setScale(scale + 0.05),
    scales: [0.75, 1, 1.25, 1.5, 1.75, 2].map((v) => ({ label: v * 100 + '%', pick: () => setScale(v), ...seg(Math.abs(scale - v) < 0.01) })),
    autoLoad, toggleAutoLoad: () => { L.autoLoad = !autoLoad; send({ cmd: 'setting', key: 'autoLoadModel', value: !autoLoad }); dirty = true; },
    autoLoadTrack: autoLoad ? t.green : t.off, autoLoadKnob: autoLoad ? 20 : 2,
    modelStatus: en.loading ? 'Loading model…' : en.loaded ? 'Model loaded' : 'Model not loaded',
    samplesStatus: ss === 2 ? `Loaded · ${en.samplesCount} samples` : ss === 3 ? 'Error: ' + (en.samplesError || 'unknown') : 'Loading…',
    samplesColor: ss === 3 ? t.rec : t.text, reloadSamples: () => send({ cmd: 'reloadSamples' }),
    modelDir: st.modelDir || '', sampleDir: st.sampleDir || ''
  };
}

fit();
paint();""")
open("app.js", "w", encoding="utf-8").write(a)
print("ok")
