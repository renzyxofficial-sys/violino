"""Bloco 4 / C++: Pause/Stop, desfazer/refazer, colar notas, nome dos takes, BPM do Standalone,
Drag All sem travar (WAV do mix inteiro preparado em segundo plano)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, """        int pass;
        bool open;
    };""", """        int pass;
        bool open;
        juce::String take;  // nome do take (o usuário renomeia; vai junto com as notas)
    };""")
h = rep(h, "    bool writeWav (const juce::File& file, int phrase, juce::String& error);  // phrase -1 = tudo",
        """    bool writeWav (const juce::File& file, int phrase, juce::String& error);  // phrase -1 = tudo
    bool buildMix (int phrase, std::vector<float>& monoOut, juce::String& error) const;  // thread de mensagens
    static bool renderMixFile (std::vector<float> monoOut, const violino::MixSettings& ms, const juce::File& file, juce::String& error);
    uint64_t mixSignature() const;
    juce::File allMixFile (uint64_t sig) const;
    std::thread allThread;
    std::atomic<bool> allBusy { false };
    std::atomic<uint64_t> allReadySig { 0 };
    uint64_t allPendingSig = 0;
    double allPendingSince = 0;
    // desfazer / refazer (edições da timeline)
    struct EditSnap
    {
        std::vector<CapNote> notes;
        std::vector<double> splits;
        std::map<long long, double> fades, fadeTension;
        std::vector<std::pair<double, float>> dynDrawn;
    };
    std::vector<EditSnap> undoStack, redoStack;
    EditSnap snapshot() const { return { notes, splits, fades, fadeTension, dynDrawn }; }
    void restore (EditSnap s);""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)

s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """ViolinoProcessor::~ViolinoProcessor()
{
    stopTimer();""", """ViolinoProcessor::~ViolinoProcessor()
{
    stopTimer();
    if (allThread.joinable()) allThread.join();""")
# BPM: no Standalone o usuário escolhe (o playhead do Standalone diz sempre 120)
s = rep(s, """            if (auto bpm = pos->getBpm(); bpm && *bpm > 20)
                hostBpm = *bpm;""", """            if (auto bpm = pos->getBpm(); bpm && *bpm > 20 && wrapperType != wrapperType_Standalone)
                hostBpm = *bpm;""")
s = rep(s, """    if (bool (Settings::get ("autoLoadModel", true)))""", """    if (wrapperType == wrapperType_Standalone)
        hostBpm = juce::jlimit (20.0, 300.0, double (Settings::get ("standaloneBpm", 120.0)));
    if (bool (Settings::get ("autoLoadModel", true)))""")
# estado: nome do take
s = rep(s, """        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks, fd == fades.end() ? 0.0 : fd->second,
                                         ft == fadeTension.end() ? 0.5 : ft->second });""",
        """        juce::String name;
        for (auto i : p.idx) if (i < notes.size() && notes[i].take.isNotEmpty()) { name = notes[i].take; break; }
        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks, fd == fades.end() ? 0.0 : fd->second,
                                         ft == fadeTension.end() ? 0.5 : ft->second, name });""")
s = rep(s, """    o->setProperty ("standalone", wrapperType == wrapperType_Standalone);""",
        """    o->setProperty ("standalone", wrapperType == wrapperType_Standalone);
    o->setProperty ("canUndo", ! undoStack.empty());
    o->setProperty ("canRedo", ! redoStack.empty());""")
# comandos: desfazer/refazer antes de tudo
s = rep(s, """    const auto cmd = c["cmd"].toString();
    if (cmd == "set")""", """    const auto cmd = c["cmd"].toString();
    static const juce::StringArray kEdits { "noteEdit", "noteDel", "noteAdd", "noteArt", "noteTool", "noteVel", "noteAddMany", "takeResize",
                                            "takeName", "splitTake", "fade", "dynDraw", "dynClear", "deleteTake", "clear" };
    if (kEdits.contains (cmd))
    {
        undoStack.push_back (snapshot());
        if (undoStack.size() > 80) undoStack.erase (undoStack.begin());
        redoStack.clear();
    }
    if (cmd == "undo" || cmd == "redo")
    {
        auto& from = cmd == "undo" ? undoStack : redoStack;
        auto& to = cmd == "undo" ? redoStack : undoStack;
        if (from.empty()) return;
        to.push_back (snapshot());
        auto s0 = std::move (from.back());
        from.pop_back();
        restore (std::move (s0));
        return;
    }
    if (cmd == "noteAddMany")  // colar: [[início, fim, altura, articulação, velocity], ...]
    {
        if (auto* arr = c["notes"].getArray())
            for (auto& v : *arr)
                notes.push_back ({ std::max (0.0, double (v[0])), std::max (double (v[0]) + 0.03, double (v[1])), juce::jlimit (kMinPitch - 24, 108, int (v[2])),
                                   juce::jlimit (1, 127, int (v[4])), Forced (juce::jlimit (0, 9, int (v[3]))), pass, false });
        openNote.clear();
        dirty = true;
        return;
    }
    if (cmd == "takeName")
    {
        const int k = int (c["phrase"]);
        if (k >= 0 && k < (int) phrases.size())
            for (auto i : phrases[size_t (k)].idx)
                if (i < notes.size()) notes[i].take = c["name"].toString().substring (0, 40);
        return;
    }
    if (cmd == "bpm")  // só no Standalone (no DAW o BPM vem do host)
    {
        if (wrapperType == wrapperType_Standalone)
        {
            hostBpm = juce::jlimit (20.0, 300.0, double (c["v"]));
            Settings::set ("standaloneBpm", hostBpm.load());
        }
        return;
    }
    if (cmd == "pause") { timelinePlay = false; return; }  // fica onde parou; Play continua dali
    if (cmd == "stop")
    {
        double first = 1e18;
        for (auto& p : phrases) if (cache.count (p.hash)) first = std::min (first, p.origin);
        // parado: o segundo Stop volta para o começo (como no Ableton)
        if (! timelinePlay.load() && std::abs (timelinePos.load() - playStart) < 1e-6) playStart = first < 1e17 ? first : 0.0;
        timelinePlay = false;
        timelinePos = playStart;
        auditionIndex = -1, auditionPhrase = -1;
        return;
    }
    if (cmd == "set")""")
# Drag All: usa o WAV já pronto (feito em segundo plano); só monta na hora se ainda não houver
s = rep(s, """        auto dir = Paths::dataDir().getChildFile ("exports");
        dir.createDirectory();
        auto f = dir.getChildFile ("Violin all " + juce::Time::getCurrentTime().formatted ("%H%M%S") + ".wav");
        juce::String err;
        if (writeWav (f, -1, err) && onDragRequested) onDragRequested (f);
        else if (err.isNotEmpty()) lastError = err;""", """        const auto sig = mixSignature();
        auto f = allMixFile (sig);
        if (allReadySig.load() == sig && f.existsAsFile()) { if (onDragRequested) onDragRequested (f); return; }
        f.getParentDirectory().createDirectory();
        juce::String err;
        if (writeWav (f, -1, err)) { allReadySig = sig; if (onDragRequested) onDragRequested (f); }
        else if (err.isNotEmpty()) lastError = err;""")
# writeWav dividido: montar (mensagens) + processar/gravar (qualquer thread)
s = rep(s, """bool ViolinoProcessor::writeWav (const juce::File& file, int only, juce::String& error)
{
    double first = 1e18, last = -1e18;""", """bool ViolinoProcessor::writeWav (const juce::File& file, int only, juce::String& error)
{
    std::vector<float> monoOut;
    return buildMix (only, monoOut, error) && renderMixFile (std::move (monoOut), mixSettings(), file, error);
}

uint64_t ViolinoProcessor::mixSignature() const
{
    uint64_t h = 1469598103934665603ull;
    for (auto& p : phrases)
        if (cache.count (p.hash)) h = fnv (fnv (fnv (h, int64_t (p.hash)), int64_t (dynKey (p))), std::llround (p.origin * 1000));
    for (auto* prm : getParameters()) h = fnv (h, std::llround (prm->getValue() * 1e6));
    return h;
}

juce::File ViolinoProcessor::allMixFile (uint64_t sig) const
{
    return Paths::dataDir().getChildFile ("exports").getChildFile ("Violin all " + juce::String::toHexString ((juce::int64) (sig & 0xffffffffffull)) + ".wav");
}

void ViolinoProcessor::restore (EditSnap s0)
{
    notes = std::move (s0.notes), splits = std::move (s0.splits), fades = std::move (s0.fades);
    fadeTension = std::move (s0.fadeTension), dynDrawn = std::move (s0.dynDrawn);
    openNote.clear();
    dirty = true;
}

bool ViolinoProcessor::buildMix (int only, std::vector<float>& monoOut, juce::String& error) const
{
    double first = 1e18, last = -1e18;""")
s = rep(s, """    const double tail = choice ("mixStyle") != 0 || flag ("reverb") ? 5.0 : 0.0;
    std::vector<float> monoOut (size_t ((last - first + tail) * 48000) + 1, 0.f);""",
        """    const double tail = choice ("mixStyle") != 0 || flag ("reverb") ? 5.0 : 0.0;
    monoOut.assign (size_t ((last - first + tail) * 48000) + 1, 0.f);""")
s = rep(s, """            for (size_t i = 0; i < shaped.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += shaped[i];
        }
    MixFx offline;
    offline.prepare (48000);
    offline.set (mixSettings());""", """            for (size_t i = 0; i < shaped.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += shaped[i];
        }
    return true;
}

bool ViolinoProcessor::renderMixFile (std::vector<float> monoOut, const violino::MixSettings& ms, const juce::File& file, juce::String& error)
{
    MixFx offline;
    offline.prepare (48000);
    offline.set (ms);""")
# preparo em segundo plano: 1,5 s depois que o mix parou de mudar, sem render em andamento
s = rep(s, """    bool clipsChanged = false;
    if (dirty)""", """    if (! allBusy.load() && ! engine->status().loading)
    {
        bool anyBusy = false;
        for (auto& p : phrases) anyBusy = anyBusy || (! cache.count (p.hash) && engine->isQueued (p.hash));
        const auto sig = mixSignature();
        const double now = juce::Time::getMillisecondCounterHiRes();
        if (anyBusy || sig == allReadySig.load()) allPendingSig = 0;
        else if (sig != allPendingSig) allPendingSig = sig, allPendingSince = now;
        else if (now - allPendingSince > 1500)
        {
            std::vector<float> mixMono;
            juce::String err;
            allPendingSig = 0;
            if (buildMix (-1, mixMono, err))
            {
                if (allThread.joinable()) allThread.join();
                allBusy = true;
                auto f = allMixFile (sig);
                f.getParentDirectory().createDirectory();
                allThread = std::thread ([this, m = std::move (mixMono), ms = mixSettings(), f, sig]() mutable {
                    juce::String e;
                    if (renderMixFile (std::move (m), ms, f, e)) allReadySig = sig;
                    allBusy = false;
                });
            }
            else allReadySig = sig;  // nada renderizado: não tenta de novo até mudar
        }
    }

    bool clipsChanged = false;
    if (dirty)""")
# estado salvo: nome do take
s = rep(s, """.setProperty ("v", nt.vel, nullptr).setProperty ("f", int (nt.forced), nullptr);""",
        """.setProperty ("v", nt.vel, nullptr).setProperty ("f", int (nt.forced), nullptr).setProperty ("t", nt.take, nullptr);""")
s = rep(s, """            notes.push_back ({ double (v["s"]), double (v["e"]), int (v["p"]), int (v["v"]), Forced (int (v["f"])), 0, false });""",
        """            notes.push_back ({ double (v["s"]), double (v["e"]), int (v["p"]), int (v["v"]), Forced (int (v["f"])), 0, false, v["t"].toString() });""")
if "#include <thread>" not in s:
    s = s.replace("#include", "#include <thread>\n#include", 1)
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
print("ok")
