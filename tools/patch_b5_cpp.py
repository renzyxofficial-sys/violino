"""Bloco 5 / C++: Play interno toca o preview das notas sem render (e funciona sem nada renderizado),
metrônomo (só Standalone), desfazer só com mudança real + captura como passo próprio."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    void handleUiCommand (const juce::var& cmd);", """    void handleUiCommand (const juce::var& cmd);
    void handleUiCommandImpl (const juce::var& cmd);""")
h = rep(h, "    void restore (EditSnap s);", """    void restore (EditSnap s);
    static bool sameSnap (const EditSnap& a, const EditSnap& b);
    void pushUndo (EditSnap s);
    double lastCaptureEdit = 0;
    // Play interno: notas sem render tocam no preview; metrônomo do Standalone
    struct PNote { double start, end; int pitch, vel; };
    std::atomic<std::shared_ptr<const std::vector<PNote>>> previewNotes;
    std::vector<std::shared_ptr<const std::vector<PNote>>> retiredPreview;
    bool wasTimeline = false;
    std::atomic<bool> metroOn { false };
    long long metroBeat = 0;
    int metroLeft = 0, metroT = 0;
    bool metroAccent = false;""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)

s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
# ---- desfazer: só quando a edição mudou algo; a captura vira um passo próprio
s = rep(s, """    const auto cmd = c["cmd"].toString();
    static const juce::StringArray kEdits { "noteEdit", "noteDel", "noteAdd", "noteArt", "noteTool", "noteVel", "noteAddMany", "takeResize",
                                            "takeName", "splitTake", "fade", "dynDraw", "dynClear", "deleteTake", "clear" };
    if (kEdits.contains (cmd))
    {
        undoStack.push_back (snapshot());
        if (undoStack.size() > 80) undoStack.erase (undoStack.begin());
        redoStack.clear();
    }
    if (cmd == "undo" || cmd == "redo")""", """    const auto cmd = c["cmd"].toString();
    if (cmd == "undo" || cmd == "redo")""")
s = rep(s, """void ViolinoProcessor::handleUiCommand (const juce::var& c)
{""", """void ViolinoProcessor::handleUiCommand (const juce::var& c)
{
    // cada edição é um passo de desfazer, mas só se mudou algo de verdade (clique sem efeito não conta)
    static const juce::StringArray kEdits { "noteEdit", "noteDel", "noteAdd", "noteArt", "noteTool", "noteVel", "noteAddMany", "takeResize",
                                            "takeName", "splitTake", "fade", "dynDraw", "dynClear", "deleteTake", "clear" };
    if (! kEdits.contains (c["cmd"].toString())) { handleUiCommandImpl (c); return; }
    auto before = snapshot();
    handleUiCommandImpl (c);
    if (! sameSnap (before, snapshot())) pushUndo (std::move (before));
}

bool ViolinoProcessor::sameSnap (const EditSnap& a, const EditSnap& b)
{
    if (a.notes.size() != b.notes.size() || a.splits != b.splits || a.fades != b.fades || a.fadeTension != b.fadeTension || a.dynDrawn != b.dynDrawn)
        return false;
    for (size_t i = 0; i < a.notes.size(); ++i)
    {
        const auto &x = a.notes[i], &y = b.notes[i];
        if (x.start != y.start || x.end != y.end || x.pitch != y.pitch || x.vel != y.vel || x.forced != y.forced || x.take != y.take) return false;
    }
    return true;
}

void ViolinoProcessor::pushUndo (EditSnap s0)
{
    undoStack.push_back (std::move (s0));
    if (undoStack.size() > 80) undoStack.erase (undoStack.begin());
    redoStack.clear();
}

void ViolinoProcessor::handleUiCommandImpl (const juce::var& c)
{""")
s = rep(s, """    const bool capture = flag ("capture") && ! flag ("lock");  // Lock MIDI: o que foi gravado não muda
    const auto scope = fifo.read (fifo.getNumReady());""", """    const bool capture = flag ("capture") && ! flag ("lock");  // Lock MIDI: o que foi gravado não muda
    const auto scope = fifo.read (fifo.getNumReady());
    if (capture)  // o que se toca vira um passo de desfazer (uma "gravação"): nova se passou 1,5 s sem tocar
    {
        bool played = false;
        for (int i = 0; i < scope.blockSize1; ++i) played = played || (events[size_t (scope.startIndex1 + i)].type == Event::noteOn && events[size_t (scope.startIndex1 + i)].capturable);
        for (int i = 0; i < scope.blockSize2; ++i) played = played || (events[size_t (scope.startIndex2 + i)].type == Event::noteOn && events[size_t (scope.startIndex2 + i)].capturable);
        if (played)
        {
            const double now = juce::Time::getMillisecondCounterHiRes();
            if (now - lastCaptureEdit > 1500) pushUndo (snapshot());
            lastCaptureEdit = now;
        }
    }""")
# ---- notas do preview para o Play interno (as que ainda não têm render)
s = rep(s, """    retired.push_back (clips.load());
    clips.store (next);""", """    {
        auto pv = std::make_shared<std::vector<PNote>>();
        for (auto& p : phrases)
            if (! cache.count (p.hash))
                for (auto i : p.idx)
                    if (i < notes.size()) pv->push_back ({ notes[i].start, notes[i].end, notes[i].pitch, notes[i].vel });
        retiredPreview.push_back (previewNotes.load());
        previewNotes.store (pv);
        if (retiredPreview.size() > 8) retiredPreview.erase (retiredPreview.begin());
    }
    retired.push_back (clips.load());
    clips.store (next);""")
s = rep(s, """    uiMidi.removeNextBlockOfMessages (midi, n);
    auto set = clips.load();""", """    uiMidi.removeNextBlockOfMessages (midi, n);
    auto set = clips.load();
    // Play interno: o que ainda não foi renderizado toca no preview, sincronizado com a timeline
    const bool tl = timelinePlay.load() && auditionIndex.load() < 0 && ! (isPlaying && hasHost);
    const double tlStart = timelinePos.load();
    if (tl)
    {
        const double te = tlStart + n / sampleRate;
        if (! wasTimeline) metroBeat = (long long) std::ceil (tlStart / (60.0 / hostBpm.load()) - 1e-9) - 1;
        if (auto pv = previewNotes.load())
            for (auto& q : *pv)
            {
                const int pp = q.pitch < kMinPitch ? q.pitch + 12 * ((kMinPitch - q.pitch + 11) / 12) : q.pitch;
                if (q.start >= tlStart && q.start < te) sampler.noteOn (pp, q.vel, liveT0 + (q.start - tlStart));
                if (q.end >= tlStart && q.end < te) sampler.noteOff (pp, liveT0 + (q.end - tlStart));
            }
    }
    if (wasTimeline && ! tl) sampler.allNotesOff();  // Pause / Stop: nada fica soando
    wasTimeline = tl;""")
s = rep(s, """        double lastEnd = 0;
        for (auto& c : *set)
        {""", """        double lastEnd = 0;
        if (auto pv = previewNotes.load())
            for (auto& q : *pv) lastEnd = std::max (lastEnd, q.end + 0.5);
        for (auto& c : *set)
        {""")
# metrônomo depois dos efeitos (o clique não vai para o reverb)
s = rep(s, """    meterL = std::max (meterL.load() * 0.85f, buffer.getMagnitude (0, 0, n));""", """    if (tl && metroOn.load() && wrapperType == wrapperType_Standalone)
    {
        const double beat = 60.0 / hostBpm.load();
        for (int i = 0; i < n; ++i)
        {
            const auto k = (long long) std::floor ((tlStart + i / sampleRate) / beat + 1e-9);
            if (k != metroBeat) metroBeat = k, metroLeft = int (0.05 * sampleRate), metroT = 0, metroAccent = k % 4 == 0;
            if (metroLeft <= 0) continue;
            const double tt = metroT / sampleRate;
            const float v = float (std::sin (6.283185307 * (metroAccent ? 1760.0 : 1100.0) * tt) * std::exp (-tt * 80.0) * (metroAccent ? 0.36 : 0.26));
            for (int ch = 0; ch < buffer.getNumChannels(); ++ch) buffer.addSample (ch, i, v);
            ++metroT, --metroLeft;
        }
    }
    meterL = std::max (meterL.load() * 0.85f, buffer.getMagnitude (0, 0, n));""")
# Play funciona mesmo sem nada renderizado (o preview toca); Stop/rewind usam o começo da 1ª frase
s = rep(s, """        double first = 1e18, last = -1e18;
        for (auto& p : phrases)
            if (auto it = cache.find (p.hash); it != cache.end())
                first = std::min (first, p.origin), last = std::max (last, p.origin + it->second.audio.size() / 48000.0);
        if (cmd == "seek")""", """        double first = 1e18, last = -1e18;
        for (auto& p : phrases)
        {
            first = std::min (first, p.origin), last = std::max (last, p.end + 0.5);
            if (auto it = cache.find (p.hash); it != cache.end()) last = std::max (last, p.origin + it->second.audio.size() / 48000.0);
        }
        if (cmd == "seek")""")
s = rep(s, """        if (first > 1e17) return;  // nada renderizado ainda""", """        if (first > 1e17) return;  // nada capturado ainda""")
s = rep(s, """        double first = 1e18;
        for (auto& p : phrases) if (cache.count (p.hash)) first = std::min (first, p.origin);""", """        double first = 1e18;
        for (auto& p : phrases) first = std::min (first, p.origin);""")
# metrônomo: comando e estado
s = rep(s, """    if (cmd == "pause") { timelinePlay = false; return; }""", """    if (cmd == "metro") { metroOn = ! metroOn.load(); Settings::set ("metronome", metroOn.load()); return; }
    if (cmd == "pause") { timelinePlay = false; return; }""")
s = rep(s, """    o->setProperty ("canUndo", ! undoStack.empty());""", """    o->setProperty ("canUndo", ! undoStack.empty());
    o->setProperty ("metro", metroOn.load());""")
s = rep(s, """        hostBpm = juce::jlimit (20.0, 300.0, double (Settings::get ("standaloneBpm", 120.0)));""",
        """        hostBpm = juce::jlimit (20.0, 300.0, double (Settings::get ("standaloneBpm", 120.0))), metroOn = bool (Settings::get ("metronome", false));""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
print("ok")
