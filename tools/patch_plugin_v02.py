"""Patch: configurações globais, log dos samples, forma de onda, audição por frase, arrastar para o DAW."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\source")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


# ---------------- EngineService: configurações globais
h = open("EngineService.h", encoding="utf-8").read()
h = rep(h, "    static juce::File pluginDir();   // pasta do binário do plugin (onde ficam as DLLs)\n};",
"""    static juce::File pluginDir();   // pasta do binário do plugin (onde ficam as DLLs)
};

// Configurações de todas as instâncias (dataDir/settings.json): carregar ao abrir, escala da UI
struct Settings
{
    static juce::var get (const juce::String& key, const juce::var& fallback);
    static void set (const juce::String& key, const juce::var& value);
};

void appLog (const juce::String& message);  // dataDir/ui.log""")
open("EngineService.h", "w", encoding="utf-8").write(h)

c = open("EngineService.cpp", encoding="utf-8").read()
c = rep(c, "juce::File Paths::sampleDir() { return dataDir().getChildFile (\"samples\"); }",
"""juce::File Paths::sampleDir() { return dataDir().getChildFile ("samples"); }

static juce::CriticalSection settingsLock;

juce::var Settings::get (const juce::String& key, const juce::var& fallback)
{
    const juce::ScopedLock sl (settingsLock);
    auto v = juce::JSON::parse (Paths::dataDir().getChildFile ("settings.json"));
    return v.hasProperty (key) ? v[juce::Identifier (key)] : fallback;
}

void Settings::set (const juce::String& key, const juce::var& value)
{
    const juce::ScopedLock sl (settingsLock);
    auto file = Paths::dataDir().getChildFile ("settings.json");
    auto v = juce::JSON::parse (file);
    if (! v.isObject()) v = juce::var (new juce::DynamicObject());
    v.getDynamicObject()->setProperty (key, value);
    file.getParentDirectory().createDirectory();
    file.replaceWithText (juce::JSON::toString (v));
}

void appLog (const juce::String& message)
{
    static juce::CriticalSection logLock;
    const juce::ScopedLock sl (logLock);
    auto f = Paths::dataDir().getChildFile ("ui.log");
    if (f.getSize() > (1 << 20)) f.deleteFile();
    f.getParentDirectory().createDirectory();
    f.appendText (juce::Time::getCurrentTime().toString (true, true) + "  " + message + juce::newLine);
}""")
open("EngineService.cpp", "w", encoding="utf-8").write(c)

# ---------------- Processor header
h = open("PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::function<void()> onExportRequested;", """    std::function<void()> onExportRequested;
    std::function<void (const juce::File&)> onDragRequested;  // arrastar a frase para o DAW
    std::function<void()> onScaleChanged;""")
h = rep(h, """    struct Rendered
    {
        std::vector<float> audio;  // 48 kHz
        double accuracy = 0;
    };""", """    struct Rendered
    {
        std::vector<float> audio;  // 48 kHz
        double accuracy = 0;
        juce::Array<juce::var> peaks;  // forma de onda para a UI: pico a cada 50 ms (0..100)
    };""")
h = rep(h, "    std::thread loader;  // carrega os samples do preview sem travar a abertura",
"""    std::thread loader;  // carrega os samples do preview sem travar a abertura
    std::atomic<int> sampleState { 0 };  // 0 parado, 1 carregando, 2 pronto, 3 erro
    juce::String sampleError;
    juce::CriticalSection sampleLock;
    int auditionPhrase = -1;
    void startSampleLoad();
    static juce::Array<juce::var> peaksOf (const std::vector<float>& audio);
    bool writeWav (const juce::File& file, int phrase, juce::String& error);  // phrase -1 = tudo""")
open("PluginProcessor.h", "w", encoding="utf-8").write(h)

# ---------------- Processor cpp
s = open("PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """    loader = std::thread ([this] {
        juce::String err;
        if (! sampler.load (Paths::sampleDir(), err))
            lastError = err;
    });
    startTimerHz (30);
}""", """    startSampleLoad();
    if (bool (Settings::get ("autoLoadModel", true)))
        engine->requestLoad();
    startTimerHz (30);
}

void ViolinoProcessor::startSampleLoad()
{
    if (loader.joinable()) loader.join();
    sampleState = 1;
    loader = std::thread ([this] {
        const double t0 = juce::Time::getMillisecondCounterHiRes();
        const auto dir = Paths::sampleDir();
        appLog ("samples: loading from " + dir.getFullPathName());
        juce::String err;
        const bool ok = sampler.load (dir, err);
        {
            const juce::ScopedLock sl (sampleLock);
            sampleError = err;
        }
        sampleState = ok ? 2 : 3;
        appLog (ok ? "samples: " + juce::String (sampler.sampleCount()) + " loaded in "
                         + juce::String (juce::roundToInt (juce::Time::getMillisecondCounterHiRes() - t0)) + " ms"
                   : "samples error: " + err);
    });
}

juce::Array<juce::var> ViolinoProcessor::peaksOf (const std::vector<float>& audio)
{
    juce::Array<juce::var> out;
    const size_t hop = 2400;  // 50 ms a 48 kHz
    float top = 1e-6f;
    for (auto v : audio) top = std::max (top, std::abs (v));
    for (size_t i = 0; i < audio.size(); i += hop)
    {
        float m = 0;
        for (size_t k = i; k < std::min (audio.size(), i + hop); ++k) m = std::max (m, std::abs (audio[k]));
        out.add (juce::roundToInt (100.0f * m / top));
    }
    return out;
}""")
s = rep(s, """static void debugLog (const juce::String& msg)
{
    Paths::dataDir().getChildFile ("ui.log").appendText (juce::Time::getCurrentTime().toString (true, true) + "  " + msg + juce::newLine);
}
""", "")
s = rep(s, "        if (p0 > (*set)[size_t (a)]->audio.size()) auditionIndex = -1;",
        "        if (p0 > double ((*set)[size_t (a)]->audio.size())) auditionIndex = -1;")
s = rep(s, "        cache[r.id] = { std::move (r.take.audio), r.take.accuracy };",
        "        auto peaks = peaksOf (r.take.audio);\n        cache[r.id] = { std::move (r.take.audio), r.take.accuracy, std::move (peaks) };")
s = rep(s, """                rd.audio.assign ((const float*) mb.getData(), (const float*) mb.getData() + mb.getSize() / sizeof (float));""",
"""                rd.audio.assign ((const float*) mb.getData(), (const float*) mb.getData() + mb.getSize() / sizeof (float));
                rd.peaks = peaksOf (rd.audio);""")
s = rep(s, """    en->setProperty ("samples", sampler.isLoaded());""", """    en->setProperty ("samples", sampleState.load() == 2);
    en->setProperty ("samplesState", sampleState.load());
    en->setProperty ("samplesCount", sampler.sampleCount());
    {
        const juce::ScopedLock sl (sampleLock);
        en->setProperty ("samplesError", sampleError);
    }
    auto* se = new juce::DynamicObject();
    se->setProperty ("autoLoad", Settings::get ("autoLoadModel", true));
    se->setProperty ("scale", Settings::get ("uiScale", 1.0));
    se->setProperty ("sampleDir", Paths::sampleDir().getFullPathName());
    se->setProperty ("modelDir", Paths::modelDir().getFullPathName());
    o->setProperty ("settings", juce::var (se));""")
s = rep(s, """        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open });""", """        juce::var peaks;
        if (auto it = cache.find (p.hash); it != cache.end()) peaks = it->second.peaks;
        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks });""")
s = rep(s, """    o->setProperty ("prefs", uiPrefs);""", """    o->setProperty ("prefs", uiPrefs);
    if (auditionIndex.load() < 0) auditionPhrase = -1;
    o->setProperty ("audition", auditionPhrase);
    o->setProperty ("auditionPos", auditionPhrase >= 0 ? auditionPos.load() / sampleRate : 0.0);""")
s = rep(s, """        int k = int (c["phrase"]), clipIdx = -1, i = 0;
        for (size_t j = 0; j < phrases.size(); ++j)
            if (cache.count (phrases[j].hash)) { if (int (j) == k) clipIdx = i; ++i; }
        auditionPos = 0;
        auditionIndex = clipIdx;""", """        int k = int (c["phrase"]), clipIdx = -1, i = 0;
        if (k == auditionPhrase && auditionIndex.load() >= 0)  // mesmo botão: para
        {
            auditionIndex = -1, auditionPhrase = -1;
            return;
        }
        for (size_t j = 0; j < phrases.size(); ++j)
            if (cache.count (phrases[j].hash)) { if (int (j) == k) clipIdx = i; ++i; }
        auditionPos = 0;
        auditionIndex = clipIdx;
        auditionPhrase = clipIdx >= 0 ? k : -1;""")
s = rep(s, """    else if (cmd == "stopAudition")
        auditionIndex = -1;""", """    else if (cmd == "stopAudition")
        auditionIndex = -1, auditionPhrase = -1;
    else if (cmd == "drag")
    {
        const int k = int (c["phrase"]);
        auto dir = Paths::dataDir().getChildFile ("exports");
        dir.createDirectory();
        auto f = dir.getChildFile ("Violin phrase " + juce::String (k + 1) + " " + juce::Time::getCurrentTime().formatted ("%H%M%S") + ".wav");
        juce::String err;
        if (writeWav (f, k, err) && onDragRequested) onDragRequested (f);
        else if (err.isNotEmpty()) lastError = err;
    }
    else if (cmd == "setting")
    {
        const auto key = c["key"].toString();
        if (key == "uiScale")
        {
            Settings::set (key, juce::jlimit (0.75, 2.0, double (c["value"])));
            if (onScaleChanged) onScaleChanged();
        }
        else if (key == "autoLoadModel")
            Settings::set (key, bool (c["value"]));
    }
    else if (cmd == "reloadSamples")
        startSampleLoad();""")
s = rep(s, """bool ViolinoProcessor::exportWav (const juce::File& file, juce::String& error)
{
    double first = 1e18, last = -1e18;
    for (auto& p : phrases)
        if (auto it = cache.find (p.hash); it != cache.end())""", """bool ViolinoProcessor::exportWav (const juce::File& file, juce::String& error) { return writeWav (file, -1, error); }

bool ViolinoProcessor::writeWav (const juce::File& file, int only, juce::String& error)
{
    double first = 1e18, last = -1e18;
    auto use = [&] (size_t k) { return only < 0 || int (k) == only; };
    for (size_t k = 0; k < phrases.size(); ++k)
        if (auto& p = phrases[k]; ! use (k)) continue;
        else if (auto it = cache.find (p.hash); it != cache.end())""")
s = rep(s, """    std::vector<float> monoOut (size_t ((last - first + tail) * 48000) + 1, 0.f);
    for (auto& p : phrases)
        if (auto it = cache.find (p.hash); it != cache.end())""", """    std::vector<float> monoOut (size_t ((last - first + tail) * 48000) + 1, 0.f);
    for (size_t k = 0; k < phrases.size(); ++k)
        if (auto& p = phrases[k]; ! use (k)) continue;
        else if (auto it = cache.find (p.hash); it != cache.end())""")
open("PluginProcessor.cpp", "w", encoding="utf-8").write(s)

# ---------------- Editor: escala e arrasto
e = open("PluginEditor.cpp", encoding="utf-8").read()
e = rep(e, """    setResizeLimits (800, 588, 1920, 1410);
    setSize (1120, 822);
    proc.onExportRequested = [this] { chooseExportFile(); };""", """    setResizeLimits (840, 617, 2240, 1644);  // 75 % a 200 %
    applyScale();
    proc.onExportRequested = [this] { chooseExportFile(); };
    proc.onScaleChanged = [this] { applyScale(); };
    proc.onDragRequested = [this] (const juce::File& f) {
        // o botão do mouse ainda está pressionado na alça "Drag": começa o arrasto do WAV
        juce::DragAndDropContainer::performExternalDragDropOfFiles ({ f.getFullPathName() }, false, this);
    };""")
e = rep(e, """    proc.onExportRequested = nullptr;
}

void ViolinoEditor::resized() { web.setBounds (getLocalBounds()); }""", """    proc.onExportRequested = nullptr;
    proc.onScaleChanged = nullptr;
    proc.onDragRequested = nullptr;
}

void ViolinoEditor::applyScale()
{
    const double s = juce::jlimit (0.75, 2.0, double (Settings::get ("uiScale", 1.0)));
    scaling = true;
    setSize (juce::roundToInt (kBaseW * s), juce::roundToInt (kBaseH * s));
    scaling = false;
}

void ViolinoEditor::resized()
{
    web.setBounds (getLocalBounds());
    if (! scaling && getWidth() > 0)  // redimensionado pela borda: guarda a escala
        Settings::set ("uiScale", juce::jlimit (0.75, 2.0, getWidth() / double (kBaseW)));
}""")
open("PluginEditor.cpp", "w", encoding="utf-8").write(e)
eh = open("PluginEditor.h", encoding="utf-8").read()
eh = rep(eh, """    void chooseExportFile();
""", """    void chooseExportFile();
    void applyScale();
    static constexpr int kBaseW = 1120, kBaseH = 822;  // 100 %
    bool scaling = false;
""")
open("PluginEditor.h", "w", encoding="utf-8").write(eh)
print("ok")
