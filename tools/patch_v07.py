"""v0.7: Drag MIDI por frase; transporte interno com cursor (play/pausa, voltar ao início, clicar na régua)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
# play/pausa a partir do cursor; seek; voltar ao início
s = rep(s, """    else if (cmd == "play")
    {
        if (timelinePlay.load()) { timelinePlay = false; return; }
        double first = 1e18;
        for (auto& p : phrases)
            if (cache.count (p.hash)) first = std::min (first, p.origin);
        if (first > 1e17) return;  // nada renderizado ainda
        auditionIndex = -1, auditionPhrase = -1;
        timelinePos = first;
        timelinePlay = true;
    }""", """    else if (cmd == "play" || cmd == "seek" || cmd == "rewind")
    {
        double first = 1e18, last = -1e18;
        for (auto& p : phrases)
            if (auto it = cache.find (p.hash); it != cache.end())
                first = std::min (first, p.origin), last = std::max (last, p.origin + it->second.audio.size() / 48000.0);
        if (cmd == "seek") { timelinePos = std::max (0.0, double (c["t"])); return; }
        if (cmd == "rewind") { timelinePos = first < 1e17 ? first : 0.0; return; }
        if (timelinePlay.load()) { timelinePlay = false; return; }  // pausa: o cursor fica onde parou
        if (first > 1e17) return;  // nada renderizado ainda
        if (timelinePos.load() >= last - 0.05 || timelinePos.load() < first - 30) timelinePos = first;
        auditionIndex = -1, auditionPhrase = -1;
        timelinePlay = true;
    }""")
# Drag MIDI: .mid da frase (notas capturadas, com as edições)
s = rep(s, """    else if (cmd == "setting")""", """    else if (cmd == "dragMidi")
    {
        const int k = int (c["phrase"]);
        if (k < 0 || k >= (int) phrases.size()) return;
        const auto& p = phrases[size_t (k)];
        const double bpm = hostBpm.load(), tps = 960.0 * bpm / 60.0;  // ticks por segundo (960 por semínima)
        juce::MidiMessageSequence seq;
        seq.addEvent (juce::MidiMessage::tempoMetaEvent (juce::roundToInt (60000000.0 / bpm)), 0);
        for (auto i : p.idx)
        {
            if (i >= notes.size()) continue;
            const auto& nt = notes[i];
            const double a = (nt.start - p.start) * tps, b = (nt.end - p.start) * tps;
            seq.addEvent (juce::MidiMessage::noteOn (1, nt.pitch, juce::uint8 (juce::jlimit (1, 127, nt.vel))), a);
            seq.addEvent (juce::MidiMessage::noteOff (1, nt.pitch), std::max (a + 1, b));
        }
        for (auto& cc : ccCurve)
            if (cc.time >= p.start - 0.05 && cc.time <= p.end + 0.3)
                seq.addEvent (juce::MidiMessage::controllerEvent (1, 1, cc.value), std::max (0.0, (cc.time - p.start) * tps));
        seq.updateMatchedPairs();
        juce::MidiFile mf;
        mf.setTicksPerQuarterNote (960);
        mf.addTrack (seq);
        auto dir = Paths::dataDir().getChildFile ("exports");
        dir.createDirectory();
        auto f = dir.getChildFile ("Violin phrase " + juce::String (k + 1) + " " + juce::Time::getCurrentTime().formatted ("%H%M%S") + ".mid");
        if (auto os = f.createOutputStream(); os != nullptr && mf.writeTo (*os))
        {
            os.reset();
            if (onDragRequested) onDragRequested (f);
        }
    }
    else if (cmd == "setting")""")
s = rep(s, """    o->setProperty ("internalPos", timelinePos.load());""", """    o->setProperty ("internalPos", timelinePos.load());
    o->setProperty ("hostTransport", hostTransport.load());""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """            <button data-drag="{{r.i}}" title="Drag this phrase onto an audio track in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{t.fill}}; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">⠿ Drag</button>""",
"""            <button data-drag="{{r.i}}" title="Drag the rendered audio onto an audio track in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{t.fill}}; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">⠿ Audio</button>
            <button data-dragmidi="{{r.i}}" title="Drag this phrase as MIDI onto a MIDI track in your DAW" style="height: 24px; padding: 0 10px; border: 0; border-radius: 12px; background: {{t.fill}}; color: {{t.text}}; font-size: 11px; font-weight: 600; cursor: grab;">♪ MIDI</button>""")
# régua clicável (posiciona o cursor)
b = rep(b, """      <div data-roll="1" style="position: absolute; left: 268px; top: 140px; width: 790px; height: 300px;"></div>""",
        """      <div data-ruler="1" title="Click to move the cursor" style="position: absolute; left: 268px; top: 110px; width: 790px; height: 26px; cursor: pointer;"></div>
      <div data-roll="1" style="position: absolute; left: 268px; top: 140px; width: 790px; height: 300px;"></div>""")
# ⏮ antes do ▶
b = rep(b, """    <button onClick="{{doPlay}}" aria-label="{{playLabel}}" title="{{playLabel}}\"""",
        """    <button onClick="{{doRewind}}" aria-label="Back to start" title="Back to start" style="width: 40px; height: 40px; border: 0; border-radius: 20px; background: {{t.fill}}; color: {{t.text}}; cursor: pointer;"><svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M3 2.5v9M12 2.5v9L5 7z" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"></path></svg></button>
    <button onClick="{{doPlay}}" aria-label="{{playLabel}}" title="{{playLabel}}\"""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)

a = open("ui/app.js", encoding="utf-8").read()
# cursor: com o DAW tocando, o playhead do DAW; senão o cursor interno
a = rep(a, "  const playhead = S ? (S.internalPlay ? S.internalPos : S.playhead) || 0 : 0;",
        "  const playhead = S ? ((S.playing && !S.internalPlay) ? S.playhead : S.internalPos) || 0 : 0;")
a = rep(a, "    doPlay: () => send({ cmd: 'play' }), playLabel: S && S.internalPlay ? 'Stop' : 'Play rendered phrases',",
        "    doPlay: () => send({ cmd: 'play' }), doRewind: () => send({ cmd: 'rewind' }), playLabel: S && S.internalPlay ? 'Pause' : 'Play from the cursor',")
a = rep(a, "    playIcon: S && S.internalPlay ? 'M3 3h8v8H3z' : 'M4 2.5v9l7.5-4.5z',",
        "    playIcon: S && S.internalPlay ? 'M3 2.5h3v9H3zM8 2.5h3v9H8z' : 'M4 2.5v9l7.5-4.5z',")
a = rep(a, """  const d = e.target.closest('[data-drag]');""", """  const dm = e.target.closest('[data-dragmidi]');
  if (dm) { send({ cmd: 'dragMidi', phrase: +dm.dataset.dragmidi }); e.preventDefault(); return; }
  const ru = e.target.closest('[data-ruler]');
  if (ru && L.view) { const rr = ru.getBoundingClientRect(), V = L.view, fx = (e.clientX - rr.left) / rr.width; send({ cmd: 'seek', t: V.v0 + (fx * 790 - 12) / 770 * (V.v1 - V.v0) }); e.preventDefault(); return; }
  const d = e.target.closest('[data-drag]');""")
# os botões da frase cabem: Listen + Audio + MIDI
a = rep(a, "      bx: x + w - 128,", "      bx: x + w - 196,")
a = rep(a, "done: p[2] === 1 && w > 150,", "done: p[2] === 1 && w > 210,")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
