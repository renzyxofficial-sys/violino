"""Processador: parâmetros dos efeitos v2 (EQ 5 bandas, Saturator, Echo, VintageVerb), BPM e presets."""
import os
import re

os.chdir(r"C:\Users\TheoH\violino\plugin\source")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("PluginProcessor.cpp", encoding="utf-8").read()
start = s.index('    boolP ("reverb", "Reverb", false);')
end = s.index('    floatP ("output", "Output", -24, 12, 0, "dB");')
s = s[:start] + '''    auto logP = [&] (const char* id, const char* name, float lo, float hi, float def, float centre, const char* unit) {
        NormalisableRange<float> r (lo, hi);
        r.setSkewForCentre (centre);
        l.add (std::make_unique<AudioParameterFloat> (ParameterID { id, 1 }, name, r, def, AudioParameterFloatAttributes().withLabel (unit)));
    };
    // EQ paramétrico (5 bandas, estilo Pro-Q)
    boolP ("eqOn", "EQ", true);
    const int eqType[] = { 0, 1, 2, 2, 3 };
    const float eqFreq[] = { 60, 180, 900, 3500, 10000 };
    for (int b = 1; b <= 5; ++b)
    {
        const auto p = "eq" + String (b);
        l.add (std::make_unique<AudioParameterBool> (ParameterID { p + "On", 1 }, "EQ " + String (b) + " On", b != 1));
        l.add (std::make_unique<AudioParameterChoice> (ParameterID { p + "Type", 1 }, "EQ " + String (b) + " Type", kEqTypes, eqType[b - 1]));
        NormalisableRange<float> fr (20, 20000);
        fr.setSkewForCentre (1000);
        l.add (std::make_unique<AudioParameterFloat> (ParameterID { p + "Freq", 1 }, "EQ " + String (b) + " Freq", fr, eqFreq[b - 1], AudioParameterFloatAttributes().withLabel ("Hz")));
        l.add (std::make_unique<AudioParameterFloat> (ParameterID { p + "Gain", 1 }, "EQ " + String (b) + " Gain", NormalisableRange<float> (-18, 18), 0.0f, AudioParameterFloatAttributes().withLabel ("dB")));
        NormalisableRange<float> qr (0.1f, 10);
        qr.setSkewForCentre (1);
        l.add (std::make_unique<AudioParameterFloat> (ParameterID { p + "Q", 1 }, "EQ " + String (b) + " Q", qr, 0.71f, AudioParameterFloatAttributes().withLabel ("")));
    }
    boolP ("compOn", "Compressor", false);
    floatP ("compThresh", "Comp Threshold", -40, 0, -18, "dB");
    floatP ("compRatio", "Comp Ratio", 1, 10, 3, ":1");
    floatP ("compAttack", "Comp Attack", 1, 100, 15, "ms");
    floatP ("compRelease", "Comp Release", 20, 500, 150, "ms");
    floatP ("compMakeup", "Comp Makeup", 0, 12, 3, "dB");
    // Saturation (estilo Saturator)
    boolP ("satOn", "Saturation", false);
    choiceP ("satType", "Saturation Type", kSatTypes, 0);
    floatP ("satDrive", "Saturation Drive", 0, 36, 6, "dB");
    floatP ("satOutput", "Saturation Output", -24, 6, 0, "dB");
    floatP ("satMix", "Saturation Dry/Wet", 0, 100, 100, "%");
    boolP ("chorusOn", "Chorus", false);
    floatP ("chorusRate", "Chorus Rate", 0.1f, 3, 0.6f, "Hz");
    floatP ("chorusDepth", "Chorus Depth", 0, 100, 30, "%");
    floatP ("chorusMix", "Chorus Mix", 0, 100, 25, "%");
    boolP ("stereoOn", "Stereo", true);
    floatP ("stereoWidth", "Stereo Width", 0, 100, 50, "%");
    // Delay (estilo Echo)
    boolP ("delayOn", "Delay", false);
    choiceP ("delayMode", "Delay Mode", kDelayModes, 1);
    choiceP ("delayChar", "Delay Character", kDelayChars, 0);
    boolP ("delaySync", "Delay Sync", true);
    choiceP ("delayLeftDiv", "Delay Left (sync)", kDivNames, 9);
    choiceP ("delayRightDiv", "Delay Right (sync)", kDivNames, 7);
    logP ("delayLeftMs", "Delay Left", 1, 2000, 375, 300, "ms");
    logP ("delayRightMs", "Delay Right", 1, 2000, 250, 300, "ms");
    floatP ("delayFeedback", "Delay Feedback", 0, 100, 40, "%");
    logP ("delayHp", "Delay Filter HP", 20, 2000, 50, 200, "Hz");
    logP ("delayLp", "Delay Filter LP", 1000, 20000, 5000, 5000, "Hz");
    floatP ("delayMod", "Delay Modulation", 0, 100, 20, "%");
    floatP ("delayMix", "Delay Dry/Wet", 0, 100, 14, "%");
    // Reverb (inspirado no VintageVerb)
    boolP ("reverb", "Reverb", false);
    choiceP ("revMode", "Reverb Mode", kRevModes, 0);
    choiceP ("revColor", "Reverb Color", kRevColors, 0);
    floatP ("reverbMix", "Reverb Mix", 0, 100, 30, "%");
    floatP ("predelay", "Reverb Predelay", 0, 200, 20, "ms");
    logP ("revDecay", "Reverb Decay", 0.2f, 20, 3.5f, 3, "s");
    logP ("revHighFreq", "Damping HighFreq", 1000, 20000, 6000, 5000, "Hz");
    floatP ("revHighShelf", "Damping HighShelf", -24, 0, -6, "dB");
    logP ("revBassFreq", "Damping BassFreq", 50, 1000, 300, 250, "Hz");
    floatP ("revBassMult", "Damping BassMult", 0.25f, 4, 1.3f, "x");
    floatP ("revSize", "Reverb Size", 0, 100, 100, "%");
    floatP ("revAttack", "Reverb Attack", 0, 100, 50, "%");
    floatP ("revEarly", "Diffusion Early", 0, 100, 80, "%");
    floatP ("revLate", "Diffusion Late", 0, 100, 90, "%");
    floatP ("revModRate", "Mod Rate", 0.1f, 5, 2.5f, "Hz");
    floatP ("revModDepth", "Mod Depth", 0, 100, 38, "%");
    logP ("revHighCut", "Reverb HighCut", 1000, 20000, 8000, 5000, "Hz");
    logP ("revLowCut", "Reverb LowCut", 10, 1000, 10, 100, "Hz");
''' + s[end:]
s = rep(s, "const juce::StringArray kRooms { \"Room\", \"Chamber\", \"Concert Hall\", \"Scoring Stage\", \"Cathedral\" };",
"""const juce::StringArray kEqTypes { "Low Cut", "Low Shelf", "Bell", "High Shelf", "High Cut" };
const juce::StringArray kSatTypes { "Analog Clip", "Soft Sine", "Bass Shaper", "Medium Curve", "Hard Curve", "Sinoid Fold", "Digital Clip", "Waveshaper" };
const juce::StringArray kDelayModes { "Stereo", "Ping Pong", "Mid/Side" };
const juce::StringArray kDelayChars { "Digital", "Tape", "Analog" };
const juce::StringArray kDivNames { "1/64", "1/32", "1/16T", "1/16", "1/16D", "1/8T", "1/8", "1/8D", "1/4T", "1/4", "1/4D", "1/2", "1/1" };
const double kDivBeats[] = { 1.0 / 16, 1.0 / 8, 1.0 / 6, 1.0 / 4, 3.0 / 8, 1.0 / 3, 1.0 / 2, 3.0 / 4, 2.0 / 3, 1, 1.5, 2, 4 };
const juce::StringArray kRevModes { "Concert Hall", "Bright Hall", "Plate", "Room", "Chamber", "Random Space", "Chorus Space", "Ambience", "Cathedral" };
const juce::StringArray kRevColors { "1970s", "1980s", "Now" };
// modo do reverb = preset: decay, size, attack, early, late, highFreq, highShelf, bassMult, modRate, modDepth, highCut, predelay
const float kRevPresets[9][12] = {
    { 3.5f, 100, 50, 80, 90, 6000, -6, 1.3f, 2.5f, 38, 8000, 20 },   // Concert Hall
    { 3.0f, 95, 45, 80, 90, 10000, -3, 1.1f, 2.0f, 30, 14000, 20 },  // Bright Hall
    { 2.2f, 60, 10, 100, 100, 9000, -4, 1.0f, 1.2f, 20, 12000, 0 },  // Plate
    { 0.8f, 40, 70, 70, 60, 7000, -6, 1.1f, 0.8f, 15, 10000, 5 },    // Room
    { 1.5f, 60, 60, 80, 80, 7000, -5, 1.2f, 1.0f, 20, 10000, 10 },   // Chamber
    { 2.5f, 85, 40, 60, 70, 7500, -6, 1.2f, 3.5f, 60, 9000, 15 },    // Random Space
    { 2.8f, 90, 45, 80, 90, 7000, -6, 1.2f, 4.0f, 80, 9000, 15 },    // Chorus Space
    { 0.6f, 50, 80, 90, 50, 9000, -3, 1.0f, 1.0f, 15, 12000, 0 },    // Ambience
    { 6.0f, 100, 40, 80, 100, 5000, -8, 1.6f, 1.5f, 30, 7000, 30 },  // Cathedral
};""")
s = rep(s, """    m.reverbOn = flag ("reverb");
    m.room = Room (choice ("room"));
    m.reverbMix = value ("reverbMix") / 100.f;
    m.decay = value ("decay") / 100.f;
    m.predelayMs = value ("predelay");
    m.eqOn = flag ("eqOn");
    m.eqLow = value ("eqLow"), m.eqMid = value ("eqMid"), m.eqHigh = value ("eqHigh"), m.eqAir = value ("eqAir");""",
"""    m.reverbOn = flag ("reverb");
    m.revColor = choice ("revColor");
    m.reverbMix = value ("reverbMix") / 100.f;
    m.predelayMs = value ("predelay");
    m.revDecay = value ("revDecay"), m.revHighFreq = value ("revHighFreq"), m.revHighShelf = value ("revHighShelf");
    m.revBassFreq = value ("revBassFreq"), m.revBassMult = value ("revBassMult"), m.revSize = value ("revSize") / 100.f;
    m.revAttack = value ("revAttack") / 100.f, m.revEarly = value ("revEarly") / 100.f, m.revLate = value ("revLate") / 100.f;
    m.revModRate = value ("revModRate"), m.revModDepth = value ("revModDepth") / 100.f;
    m.revHighCut = value ("revHighCut"), m.revLowCut = value ("revLowCut");
    m.eqOn = flag ("eqOn");
    for (int b = 0; b < 5; ++b)
    {
        const juce::String p = "eq" + juce::String (b + 1);
        auto v = [&] (const char* suffix) { return params.getRawParameterValue (p + suffix)->load(); };
        m.eq[size_t (b)] = { v ("On") > 0.5f, juce::roundToInt (v ("Type")), v ("Freq"), v ("Gain"), v ("Q") };
    }""")
s = rep(s, """    m.satOn = flag ("satOn"), m.satDrive = value ("satDrive") / 100.f;""",
        """    m.satOn = flag ("satOn"), m.satType = choice ("satType"), m.satDriveDb = value ("satDrive");
    m.satOutputDb = value ("satOutput"), m.satMix = value ("satMix") / 100.f;""")
s = rep(s, """    m.delayOn = flag ("delayOn"), m.delayMs = value ("delayTime"), m.delayFeedback = value ("delayFeedback") / 100.f, m.delayMix = value ("delayMix") / 100.f;""",
"""    m.delayOn = flag ("delayOn"), m.delayMode = choice ("delayMode"), m.delayChar = choice ("delayChar");
    const double bpm = hostBpm.load();
    if (flag ("delaySync"))
    {
        m.delayLeftMs = float (kDivBeats[choice ("delayLeftDiv")] * 60000.0 / bpm);
        m.delayRightMs = float (kDivBeats[choice ("delayRightDiv")] * 60000.0 / bpm);
    }
    else
        m.delayLeftMs = value ("delayLeftMs"), m.delayRightMs = value ("delayRightMs");
    m.delayFeedback = value ("delayFeedback") / 100.f, m.delayHp = value ("delayHp"), m.delayLp = value ("delayLp");
    m.delayMod = value ("delayMod") / 100.f, m.delayMix = value ("delayMix") / 100.f;""")
# BPM do host
s = rep(s, """            if (auto ts = pos->getTimeInSeconds())""", """            if (auto bpm = pos->getBpm(); bpm && *bpm > 20)
                hostBpm = *bpm;
            if (auto ts = pos->getTimeInSeconds())""")
# modo do reverb aplica o preset
s = rep(s, """        // botão de articulação clicado: vale para todas as notas capturadas e as próximas""", """        if (c["id"].toString() == "revMode")
        {
            const char* ids[] = { "revDecay", "revSize", "revAttack", "revEarly", "revLate", "revHighFreq", "revHighShelf",
                                  "revBassMult", "revModRate", "revModDepth", "revHighCut", "predelay" };
            const auto& pr = kRevPresets[juce::jlimit (0, 8, choice ("revMode"))];
            for (int k = 0; k < 12; ++k) setParam (ids[k], pr[k]);
        }
        // botão de articulação clicado: vale para todas as notas capturadas e as próximas""")
# estado: redução de ganho do compressor, BPM e padrão de cada parâmetro (duplo clique volta)
s = rep(s, """            e->setProperty ("n", rp->getValue());""", """            e->setProperty ("n", rp->getValue());
            e->setProperty ("d", rp->getDefaultValue());""")
s = rep(s, """    o->setProperty ("meters", juce::Array<juce::var> { meterL.load(), meterR.load() });""",
"""    o->setProperty ("meters", juce::Array<juce::var> { meterL.load(), meterR.load() });
    o->setProperty ("gr", fx.gainReductionDb());
    o->setProperty ("bpm", hostBpm.load());""")
# texto de Hz/s/x
s = rep(s, """                                       : rp->getLabel() == "Hz" ? juce::String (plain, 2) : juce::String (juce::roundToInt (plain)))""",
"""                                       : rp->getLabel() == "Hz" ? (plain < 10 ? juce::String (plain, 2) : plain >= 1000 ? juce::String (plain / 1000, plain >= 10000 ? 1 : 2) + "k" : juce::String (juce::roundToInt (plain)))
                                       : rp->getLabel() == "s" || rp->getLabel() == "x" ? juce::String (plain, 2) : rp->getLabel().isEmpty() ? juce::String (plain, 2) : juce::String (juce::roundToInt (plain)))""")
open("PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::atomic<bool> timelinePlay { false };", "    std::atomic<double> hostBpm { 120 };\n    std::atomic<bool> timelinePlay { false };")
open("PluginProcessor.h", "w", encoding="utf-8").write(h)
print("ok")
