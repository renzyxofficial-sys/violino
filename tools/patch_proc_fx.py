"""Processador: parâmetros dos efeitos novos, Lock MIDI, Play/Stop interno."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\source")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """    floatP ("eqLow", "EQ Low", -12, 12, 0, "dB");""", """    boolP ("eqOn", "EQ", true);
    floatP ("eqLow", "EQ Low", -12, 12, 0, "dB");""")
s = rep(s, """    floatP ("output", "Output", -24, 12, 0, "dB");""", """    boolP ("compOn", "Compressor", false);
    floatP ("compThresh", "Comp Threshold", -40, 0, -18, "dB");
    floatP ("compRatio", "Comp Ratio", 1, 10, 3, ":1");
    floatP ("compAttack", "Comp Attack", 1, 100, 15, "ms");
    floatP ("compRelease", "Comp Release", 20, 500, 150, "ms");
    floatP ("compMakeup", "Comp Makeup", 0, 12, 3, "dB");
    boolP ("satOn", "Saturation", false);
    floatP ("satDrive", "Saturation Drive", 0, 100, 30, "%");
    boolP ("chorusOn", "Chorus", false);
    floatP ("chorusRate", "Chorus Rate", 0.1f, 3, 0.6f, "Hz");
    floatP ("chorusDepth", "Chorus Depth", 0, 100, 30, "%");
    floatP ("chorusMix", "Chorus Mix", 0, 100, 25, "%");
    boolP ("delayOn", "Delay", false);
    floatP ("delayTime", "Delay Time", 20, 1000, 320, "ms");
    floatP ("delayFeedback", "Delay Feedback", 0, 90, 25, "%");
    floatP ("delayMix", "Delay Mix", 0, 100, 18, "%");
    boolP ("stereoOn", "Stereo", true);
    floatP ("stereoWidth", "Stereo Width", 0, 100, 50, "%");
    floatP ("output", "Output", -24, 12, 0, "dB");
    boolP ("lock", "Lock MIDI", false);""")
s = rep(s, """    m.eqLow = value ("eqLow"), m.eqMid = value ("eqMid"), m.eqHigh = value ("eqHigh"), m.eqAir = value ("eqAir");""",
"""    m.eqOn = flag ("eqOn");
    m.eqLow = value ("eqLow"), m.eqMid = value ("eqMid"), m.eqHigh = value ("eqHigh"), m.eqAir = value ("eqAir");
    m.compOn = flag ("compOn"), m.compThresh = value ("compThresh"), m.compRatio = value ("compRatio");
    m.compAttackMs = value ("compAttack"), m.compReleaseMs = value ("compRelease"), m.compMakeup = value ("compMakeup");
    m.satOn = flag ("satOn"), m.satDrive = value ("satDrive") / 100.f;
    m.chorusOn = flag ("chorusOn"), m.chorusRate = value ("chorusRate"), m.chorusDepth = value ("chorusDepth") / 100.f, m.chorusMix = value ("chorusMix") / 100.f;
    m.delayOn = flag ("delayOn"), m.delayMs = value ("delayTime"), m.delayFeedback = value ("delayFeedback") / 100.f, m.delayMix = value ("delayMix") / 100.f;
    m.stereoOn = flag ("stereoOn"), m.stereoWidth = value ("stereoWidth") / 100.f;""")
# Lock MIDI: nada entra nem sai da captura
s = rep(s, """    const bool capture = flag ("capture");
    const auto scope = fifo.read (fifo.getNumReady());""", """    const bool capture = flag ("capture") && ! flag ("lock");  // Lock MIDI: o que foi gravado não muda
    const auto scope = fifo.read (fifo.getNumReady());""")
s = rep(s, """    else if (cmd == "clear")
    {""", """    else if (cmd == "clear")
    {
        if (flag ("lock")) return;""")
# texto dos parâmetros: Hz com 2 casas, razão com 1
s = rep(s, """                                    ? (rp->getLabel() == "dB" ? juce::String (plain, 1) : juce::String (juce::roundToInt (plain)))""",
"""                                    ? (rp->getLabel() == "dB" || rp->getLabel() == ":1" ? juce::String (plain, 1)
                                       : rp->getLabel() == "Hz" ? juce::String (plain, 2) : juce::String (juce::roundToInt (plain)))""")
s = rep(s, """            e->setProperty ("text", text + (rp->getLabel().isNotEmpty() ? " " + rp->getLabel() : juce::String()));""",
"""            e->setProperty ("text", text + (rp->getLabel() == ":1" ? ":1" : rp->getLabel().isNotEmpty() ? " " + rp->getLabel() : juce::String()));""")
# Play/Stop interno: toca as frases renderizadas em sequência (sem o DAW)
s = rep(s, """    else if (isPlaying && hasHost)
        for (auto& c : *set)""", """    else if (timelinePlay.load() && ! (isPlaying && hasHost))
    {
        const double tp = timelinePos.load();
        double lastEnd = 0;
        for (auto& c : *set)
        {
            lastEnd = std::max (lastEnd, c->origin + c->audio.size() / sampleRate);
            if (tp + n / sampleRate >= c->origin && tp < c->origin + c->audio.size() / sampleRate)
                mixClip (*c, (tp - c->origin) * sampleRate);
        }
        timelinePos = tp + n / sampleRate;
        if (tp > lastEnd) timelinePlay = false;
    }
    else if (isPlaying && hasHost)
        for (auto& c : *set)""")
s = rep(s, """    else if (cmd == "stopAudition")
        auditionIndex = -1, auditionPhrase = -1;""", """    else if (cmd == "stopAudition")
        auditionIndex = -1, auditionPhrase = -1;
    else if (cmd == "play")
    {
        if (timelinePlay.load()) { timelinePlay = false; return; }
        double first = 1e18;
        for (auto& p : phrases)
            if (cache.count (p.hash)) first = std::min (first, p.origin);
        if (first > 1e17) return;  // nada renderizado ainda
        auditionIndex = -1, auditionPhrase = -1;
        timelinePos = first;
        timelinePlay = true;
    }""")
s = rep(s, """    o->setProperty ("audition", auditionPhrase);""", """    o->setProperty ("audition", auditionPhrase);
    o->setProperty ("internalPlay", timelinePlay.load());
    o->setProperty ("internalPos", timelinePos.load());""")
open("PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::atomic<double> auditionPos { 0 };", "    std::atomic<double> auditionPos { 0 };\n    std::atomic<bool> timelinePlay { false };  // Play interno (sem o DAW)\n    std::atomic<double> timelinePos { 0 };")
open("PluginProcessor.h", "w", encoding="utf-8").write(h)
print("ok")
