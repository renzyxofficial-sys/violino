"""Biblioteca de MIDIs clássicos: pasta no pacote do plugin, painel com filtros, importar e aplicar o Playstyle sugerido."""
import os
os.chdir(r"C:\Users\TheoH\violino")


def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)


patch('plugin/source/PluginProcessor.cpp', [(
    """        if (! importMidi (juce::File (c["path"].toString()), err)) lastError = err;""",
    """        auto path = c["path"].toString();
        juce::File f (path);
        if (path.startsWith ("lib:"))  // peça da biblioteca: dentro do pacote do plugin (ou dataDir/library)
        {
            const auto rel = path.substring (4);
            for (auto dir : { Paths::pluginDir().getParentDirectory().getChildFile ("Resources/library"),
                              juce::File ("C:\\\\Program Files\\\\Common Files\\\\VST3\\\\Violino.vst3\\\\Contents\\\\Resources\\\\library"),
                              Paths::dataDir().getChildFile ("library") })
                if (dir.getChildFile (rel).existsAsFile()) { f = dir.getChildFile (rel); break; }
        }
        if (! importMidi (f, err)) lastError = err;""")])

js = open('plugin/ui/edit.js', encoding='utf-8').read()
js += r"""
// ------------------------------------------------------------------ biblioteca de MIDIs clássicos (Mutopia Project)
function libImport(it) {
  send({ cmd: 'importMidi', path: 'lib:' + it.file });
  const k = ['Natural', 'Lyrical', 'Romantic', 'Classical', 'Baroque', 'Cinematic'].indexOf(it.playstyle);
  if (k >= 0) setV('playStyle', k);  // o estilo sugerido para a época da peça
  L.lib = false; dirty = true;
}
function libraryVals(t) {
  if (!L.lib) return { showLib: false, toggleLib: () => { L.lib = true; dirty = true; } };
  const all = typeof LIBRARY !== 'undefined' ? LIBRARY : [], st = L.libStyle || 'All', q = (L.libQ || '').toLowerCase();
  const styles = ['All', ...[...new Set(all.map((x) => x.style))].sort()];
  const list = all.filter((x) => (st === 'All' || x.style === st) && (!q || (x.title + ' ' + x.composer).toLowerCase().includes(q)));
  const groups = [];
  for (const x of list) {
    let g = groups[groups.length - 1];
    if (!g || g.name !== x.composer) groups.push(g = { name: x.composer, items: [] });
    g.items.push({ title: x.title, tag: x.style + ' · ' + x.playstyle, pick: () => libImport(x) });
  }
  return {
    showLib: true, toggleLib: () => { L.lib = false; dirty = true; }, closeLib: () => { L.lib = false; dirty = true; },
    libGroups: groups, libCount: `${list.length} of ${all.length} pieces · Mutopia Project (public domain / CC)`,
    libStyles: styles.map((s) => ({ label: s, pick: () => { L.libStyle = s; dirty = true; }, bg: s === st ? t.accent : t.fill, fg: s === st ? '#FFFFFF' : t.text })),
    libSearch: (e) => { L.libQ = e.target.value; dirty = true; },
    libImportFile: () => { send({ cmd: 'importDialog' }); L.lib = false; dirty = true; }
  };
}
"""
js = js.replace("    ...menuVals(AC, TXT)\n  };", "    ...menuVals(AC, TXT), ...libraryVals(t)\n  };")
js = js.replace("""    { label: 'Grid…', pick: () => gridMenu(x, y) }
  ]);""", """    { label: 'Grid…', pick: () => gridMenu(x, y) },
    { label: 'Import MIDI file…', pick: () => send({ cmd: 'importDialog' }) }, { label: 'Classical library…', pick: () => { L.lib = true; dirty = true; } }
  ]);""")
open('plugin/ui/edit.js', 'w', encoding='utf-8').write(js)

b = open('plugin/ui/build_ui.py', encoding='utf-8').read()
LIB = '''
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
  </sc-if>'''
b = b.replace("SETTINGS = '''", "SETTINGS = '''" + LIB, 1)
b = b.replace(""".pmi{{display:flex;""", """.libi{{display:flex;align-items:center;height:30px;padding:0 12px;border-top:0.5px solid rgba(127,127,127,0.18);cursor:pointer;font-size:12px}}
.libi:hover{{background:rgba(10,132,255,0.16)}}
.pmi{{display:flex;""", 1)
# índice da biblioteca embutido no script da UI
b = b.replace('''js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()''', '''js = open(os.path.join(HERE, "app.js"), encoding="utf-8").read()
_libp = os.path.join(HERE, "..", "..", "library", "index.json")
js = "const LIBRARY = " + (open(_libp, encoding="utf-8").read() if os.path.exists(_libp) else "[]") + ";\\n" + js''', 1)
open('plugin/ui/build_ui.py', 'w', encoding='utf-8').write(b)

t = open('tools/b4_transport.txt', encoding='utf-8').read()
o = """      <button data-dragall="1" class="tpb lg-icon\""""
assert t.count(o) == 1
t = t.replace(o, """      <button onClick="{{toggleLib}}" class="tpb lg-icon" title="Classical library (Mutopia) and Import MIDI" style="padding: 0 11px; background: {{t.fill}};">♫ Library</button>
""" + o)
open('tools/b4_transport.txt', 'w', encoding='utf-8').write(t)
b = open('plugin/ui/build_ui.py', encoding='utf-8').read()
i = b.index('TRANSPORT = """'); j = b.index('"""', i + 15)
b = b[:i] + 'TRANSPORT = """' + t + b[j:]
open('plugin/ui/build_ui.py', 'w', encoding='utf-8').write(b)
print('ok')
