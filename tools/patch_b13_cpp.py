"""Importar arquivo MIDI (botão, menu e biblioteca): escolhe a trilha do violino, coloca depois do que já existe."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old); assert c == n, (c, old[:70]); return s.replace(old, new)


h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::function<void()> onExportRequested;", """    std::function<void()> onExportRequested;
    std::function<void()> onImportRequested;  // Import MIDI: o editor abre o seletor de arquivo
    bool importMidi (const juce::File& file, juce::String& error);""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)

s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """static const juce::StringArray kEdits { "noteEdit", "noteDel", "noteAdd", "noteArt", "noteTool", "noteVel", "noteAddMany", "takeResize",
                                            "takeName", "splitTake", "fade", "dynDraw", "dynClear", "deleteTake", "clear" };""",
        """static const juce::StringArray kEdits { "noteEdit", "noteDel", "noteAdd", "noteArt", "noteTool", "noteVel", "noteAddMany", "takeResize",
                                            "takeName", "splitTake", "fade", "dynDraw", "dynClear", "deleteTake", "clear", "importMidi" };""")
s = rep(s, """    else if (cmd == "export")
    {
        if (onExportRequested) onExportRequested();
    }""", """    else if (cmd == "export")
    {
        if (onExportRequested) onExportRequested();
    }
    else if (cmd == "importDialog")
    {
        if (onImportRequested) onImportRequested();
    }
    else if (cmd == "importMidi")  // {path}: arquivo da biblioteca
    {
        juce::String err;
        if (! importMidi (juce::File (c["path"].toString()), err)) lastError = err;
    }""")
s = rep(s, """bool ViolinoProcessor::exportWav (const juce::File& file, juce::String& error) { return writeWav (file, -1, error); }""",
        """bool ViolinoProcessor::exportWav (const juce::File& file, juce::String& error) { return writeWav (file, -1, error); }

bool ViolinoProcessor::importMidi (const juce::File& file, juce::String& error)
{
    juce::FileInputStream in (file);
    juce::MidiFile mf;
    if (! in.openedOk() || ! mf.readFrom (in)) { error = "Cannot read " + file.getFileName(); return false; }
    // tempo do arquivo (o primeiro): no Standalone vira o BPM da timeline
    double bpm = 0;
    for (int t = 0; t < mf.getNumTracks() && bpm <= 0; ++t)
        for (auto* ev : *mf.getTrack (t))
            if (ev->message.isTempoMetaEvent()) { bpm = 60.0 / ev->message.getTempoSecondsPerQuarterNote(); break; }
    mf.convertTimestampTicksToSeconds();
    // a trilha do violino: a que tem "violin" no nome; senão a com mais notas na região do violino
    int best = -1;
    double bestScore = -1;
    for (int t = 0; t < mf.getNumTracks(); ++t)
    {
        auto* tr = mf.getTrack (t);
        juce::String name;
        int count = 0, inRange = 0;
        for (auto* ev : *tr)
        {
            if (ev->message.isTrackNameEvent()) name = ev->message.getTextFromTextMetaEvent();
            if (ev->message.isNoteOn()) ++count, inRange += ev->message.getNoteNumber() >= 55 ? 1 : 0;
        }
        if (count == 0) continue;
        const double sc = inRange + 0.2 * (count - inRange) + (name.containsIgnoreCase ("violin") || name.containsIgnoreCase ("violino") ? 1e6 : 0);
        if (sc > bestScore) bestScore = sc, best = t;
    }
    if (best < 0) { error = "No notes in " + file.getFileName(); return false; }
    juce::MidiMessageSequence seq (*mf.getTrack (best));
    seq.updateMatchedPairs();
    double first = 1e18;
    for (auto* ev : seq) if (ev->message.isNoteOn()) first = std::min (first, ev->message.getTimeStamp());
    double at = 0;  // depois do que já existe, com 2 s de folga (vira um take novo)
    for (auto& nt : notes) at = std::max (at, nt.end + 2.0);
    int added = 0;
    for (auto* ev : seq)
    {
        if (! ev->message.isNoteOn() || ev->noteOffObject == nullptr || added >= 6000) continue;
        const double s0 = ev->message.getTimeStamp() - first + at, e0 = ev->noteOffObject->message.getTimeStamp() - first + at;
        int p = ev->message.getNoteNumber();
        while (p < 55) p += 12;  // abaixo do Sol grave do violino: sobe oitavas
        notes.push_back ({ s0, std::max (s0 + 0.03, e0), juce::jlimit (55, 108, p), juce::jlimit (1, 127, int (ev->message.getVelocity())), Forced::autoMode, pass, false,
                           file.getFileNameWithoutExtension().substring (0, 40) });
        ++added;
    }
    if (wrapperType == wrapperType_Standalone && bpm > 20 && bpm < 300) { hostBpm = bpm; Settings::set ("standaloneBpm", bpm); }
    timelinePos = playStart = at;
    openNote.clear();
    dirty = true;
    return added > 0;
}""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

e = open("source/PluginEditor.cpp", encoding="utf-8").read()
e = rep(e, "    proc.onExportRequested = [this] { chooseExportFile(); };", """    proc.onExportRequested = [this] { chooseExportFile(); };
    proc.onImportRequested = [this] {
        chooser = std::make_unique<juce::FileChooser> ("Import MIDI", juce::File::getSpecialLocation (juce::File::userMusicDirectory), "*.mid;*.midi");
        chooser->launchAsync (juce::FileBrowserComponent::openMode | juce::FileBrowserComponent::canSelectFiles, [this] (const juce::FileChooser& fc) {
            auto f = fc.getResult();
            if (f == juce::File {}) return;
            juce::var c (new juce::DynamicObject());
            c.getDynamicObject()->setProperty ("cmd", "importMidi");
            c.getDynamicObject()->setProperty ("path", f.getFullPathName());
            proc.handleUiCommand (c);  // passa pelo desfazer como qualquer edição
        });
    };""")
e = rep(e, "    proc.onExportRequested = nullptr;", "    proc.onExportRequested = nullptr;\n    proc.onImportRequested = nullptr;")
open("source/PluginEditor.cpp", "w", encoding="utf-8").write(e)
print("ok")
