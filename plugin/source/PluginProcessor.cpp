#include <thread>
#include "PluginProcessor.h"
#include "PluginEditor.h"

using namespace violino;

namespace
{
const juce::StringArray kPlayModes { "Legato", "Shorts" };
const juce::StringArray kPlayStyles { "Natural", "Lyrical", "Romantic", "Classical", "Baroque", "Cinematic" };
const juce::StringArray kShorts { "Spiccato", "Staccato", "Pizzicato" };
const Forced kShortForced[] = { Forced::spiccato, Forced::staccato, Forced::pizzicato };
const juce::StringArray kArticModes { "Auto", "Auto + Dynamics", "Manual" };
const juce::StringArray kArticulations { "Auto", "Sustain", "Legato", "Spiccato", "Staccato", "Pizzicato", "Tremolo", "Trill", "Portamento", "Harmonic" };
const juce::StringArray kQualities { "Low", "Medium", "High", "Extreme" };
const juce::StringArray kMixStyles { "Dry", "Lyrical", "Romantic", "Baroque", "Cinematic" };
const juce::StringArray kEqTypes { "Low Cut", "Low Shelf", "Bell", "High Shelf", "High Cut" };
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
};

constexpr double kPhraseGap = 2.0;   // frase = notas sem pausa >= 2 s
constexpr double kLeadIn = 0.5;      // o render começa meio segundo antes da 1ª nota
constexpr double kMatch = 0.03;      // nota igual à capturada se começa a menos de 30 ms

// keyswitches: só teclas brancas, C1 = 36 (Auto, Sustain, Legato, Spiccato, Staccato, Pizz, Tremolo, Trill, Porta, Harmonic)
int keyswitchIndex (int pitch)
{
    static const int keys[] = { 36, 38, 40, 41, 43, 45, 47, 48, 50, 52 };
    for (int i = 0; i < 10; ++i)
        if (keys[i] == pitch) return i;
    return -1;
}

const char* uiArt (Tech t)
{
    switch (t)
    {
        case Tech::sustain: return "sustain";
        case Tech::legatoBow: case Tech::legatoSlur: return "legato";
        case Tech::legatoPortamento: return "portamento";
        case Tech::spiccato: case Tech::ricochet: return "spiccato";
        case Tech::staccato: return "staccato";
        case Tech::pizzicato: return "pizzicato";
        case Tech::tremolo: return "tremolo";
        case Tech::trillMajor: case Tech::trillMinor: return "trill";
        case Tech::harmonic: return "harmonic";
        default: return "auto";  // "none": modo natural (passagens rápidas)
    }
}

uint64_t fnv (uint64_t h, int64_t v)
{
    for (int i = 0; i < 8; ++i) h = (h ^ uint64_t ((v >> (8 * i)) & 0xff)) * 1099511628211ull;
    return h;
}

juce::AudioProcessorValueTreeState::ParameterLayout layout()
{
    using namespace juce;
    AudioProcessorValueTreeState::ParameterLayout l;
    auto choiceP = [&] (const char* id, const char* name, const StringArray& c, int def) { l.add (std::make_unique<AudioParameterChoice> (ParameterID { id, 1 }, name, c, def)); };
    auto boolP = [&] (const char* id, const char* name, bool def) { l.add (std::make_unique<AudioParameterBool> (ParameterID { id, 1 }, name, def)); };
    auto floatP = [&] (const char* id, const char* name, float lo, float hi, float def, const char* unit) {
        l.add (std::make_unique<AudioParameterFloat> (ParameterID { id, 1 }, name, NormalisableRange<float> (lo, hi), def, AudioParameterFloatAttributes().withLabel (unit)));
    };
    choiceP ("playMode", "Play Mode", kPlayModes, 0);
    choiceP ("shortsMode", "Shorts Type", kShorts, 0);
    l.add (std::make_unique<AudioParameterInt> (ParameterID { "renderSteps", 1 }, "Render Steps", 4, 50, 30));
    choiceP ("articMode", "Articulation Mode", kArticModes, 0);
    choiceP ("articulation", "Articulation", kArticulations, 0);
    choiceP ("quality", "Render Quality", kQualities, 2);
    choiceP ("mixStyle", "Mix Style", kMixStyles, 0);
    auto logP = [&] (const char* id, const char* name, float lo, float hi, float def, float centre, const char* unit) {
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
    boolP ("stereoOn", "Stereo", false);
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
    boolP ("revFreeze", "Reverb Freeze", false);
    floatP ("revDucking", "Reverb Ducking", 0, 100, 0, "%");
    floatP ("output", "Output", -24, 12, 0, "dB");
    boolP ("lock", "Lock MIDI", false);
    boolP ("fxBypass", "Bypass All Effects", false);
    boolP ("capture", "Capture", true);
    boolP ("autorender", "Autorender", true);
    floatP ("intensity", "Dynamics Intensity", 0, 100, 70, "%");
    choiceP ("playStyle", "Playstyle", kPlayStyles, 0);
    boolP ("modelDyn", "Model Dynamics", false);  // experimental: a curva de dinâmica vai para o VIOLET (CC1); a avaliação oficial usa w_cc = 0
    floatP ("vibAmount", "Vibrato", 0, 100, 0, "%");
    floatP ("evenOut", "Even Out", 0, 100, 90, "%");  // nivela notas longas (mais baixas no VIOLET) com os ataques
    floatP ("vibRate", "Vibrato Rate", 4, 7.5f, 5.5f, "Hz");
    floatP ("level", "Preview Level", -24, 12, 0, "dB");
    floatP ("legatoGap", "Legato Gap", 0, 60, 10, "ms");
    floatP ("dynFollow", "Dynamics Follow", 0, 100, 60, "%");
    floatP ("portaVel", "Portamento Velocity", 1, 127, 45, "");
    floatP ("takes", "Takes per Phrase", 0, 8, 0, "");
    return l;
}
} // namespace

ViolinoProcessor::ViolinoProcessor()
    : AudioProcessor (BusesProperties().withOutput ("Output", juce::AudioChannelSet::stereo(), true)),
      params (*this, nullptr, "Violino", layout())
{
    clips.store (std::make_shared<const ClipSet>());
    startSampleLoad();
    if (wrapperType == wrapperType_Standalone)
        hostBpm = juce::jlimit (20.0, 300.0, double (Settings::get ("standaloneBpm", 120.0))), metroOn = bool (Settings::get ("metronome", false));
    if (bool (Settings::get ("autoLoadModel", true)))
        engine->requestLoad();
    startTimerHz (30);
}

void ViolinoProcessor::startSampleLoad()
{
    sampleState = 1;  // carrega no próximo tique do timer (thread de mensagens; ~0,2 s)
}

void ViolinoProcessor::loadSamplesNow()
{
    {
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
    }
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
}

ViolinoProcessor::~ViolinoProcessor()
{
    stopTimer();
    if (allThread.joinable()) allThread.join();
    engine->cancelOwner (this);
}

bool ViolinoProcessor::isBusesLayoutSupported (const BusesLayout& l) const
{
    return l.getMainOutputChannelSet() == juce::AudioChannelSet::stereo() || l.getMainOutputChannelSet() == juce::AudioChannelSet::mono();
}

void ViolinoProcessor::prepareToPlay (double sr, int blockSize)
{
    sampleRate = sr;
    sampler.prepare (sr);
    fx.prepare (sr);
    fx.set (mixSettings());
    uiMidi.reset (sr);
    mono.setSize (1, std::max (blockSize, 64) * 2);
    juce::MessageManager::callAsync ([this] { clipCache.clear(); rebuildClips(); });
}

int ViolinoProcessor::choice (const char* id) const { return juce::roundToInt (params.getRawParameterValue (id)->load()); }
float ViolinoProcessor::value (const char* id) const { return params.getRawParameterValue (id)->load(); }
bool ViolinoProcessor::flag (const char* id) const { return params.getRawParameterValue (id)->load() > 0.5f; }

void ViolinoProcessor::setParam (const char* id, float plain)
{
    if (auto* p = params.getParameter (id))
        p->setValueNotifyingHost (p->convertTo0to1 (plain));
}

ArticSettings ViolinoProcessor::articSettings() const
{
    ArticSettings s;
    s.mode = ArticMode (choice ("articMode"));
    s.play = choice ("playMode") == 1 ? PlayMode::longNormal : PlayMode::legato;
    s.portaVelocity = juce::roundToInt (value ("portaVel"));
    s.legatoGap = value ("legatoGap") / 1000.0;
    switch (choice ("playStyle"))
    {
        case 1: s.legatoGap = std::max (s.legatoGap, 0.03), s.portaVelocity = std::min (127, s.portaVelocity + 10); break;  // Lyrical: cantado
        case 2: s.legatoGap = std::max (s.legatoGap, 0.045), s.portaVelocity = std::min (127, s.portaVelocity + 25); break; // Romantic: liga e desliza mais
        case 3: s.legatoGap = std::min (s.legatoGap, 0.01), s.portaVelocity = std::max (1, s.portaVelocity - 15); break;    // Classical: mais limpo
        case 4: s.legatoGap = 0.0, s.portaVelocity = 1; break;                                                               // Baroque: destacado, sem portamento
        case 5: s.legatoGap = std::max (s.legatoGap, 0.05); break;                                                           // Cinematic: tudo ligado
        default: break;
    }
    return s;
}

MixSettings ViolinoProcessor::mixSettings() const
{
    MixSettings m;
    if (flag ("fxBypass"))  // todos os efeitos desligados de uma vez (só o ganho de saída fica)
    {
        m.eqOn = m.compOn = m.satOn = m.chorusOn = m.stereoOn = m.delayOn = m.reverbOn = false;
        m.outputDb = value ("output");
        return m;
    }
    m.style = MixStyle (choice ("mixStyle"));
    m.reverbOn = flag ("reverb");
    m.revColor = choice ("revColor");
    m.reverbMix = value ("reverbMix") / 100.f;
    m.predelayMs = value ("predelay");
    m.revDecay = value ("revDecay"), m.revHighFreq = value ("revHighFreq"), m.revHighShelf = value ("revHighShelf");
    m.revBassFreq = value ("revBassFreq"), m.revBassMult = value ("revBassMult"), m.revSize = value ("revSize") / 100.f;
    m.revAttack = value ("revAttack") / 100.f, m.revEarly = value ("revEarly") / 100.f, m.revLate = value ("revLate") / 100.f;
    m.revModRate = value ("revModRate"), m.revModDepth = value ("revModDepth") / 100.f;
    m.revHighCut = value ("revHighCut"), m.revLowCut = value ("revLowCut");
    m.revFreeze = flag ("revFreeze"), m.revDucking = value ("revDucking") / 100.f;
    m.eqOn = flag ("eqOn");
    for (int b = 0; b < 5; ++b)
    {
        const juce::String p = "eq" + juce::String (b + 1);
        auto v = [&] (const char* suffix) { return params.getRawParameterValue (p + suffix)->load(); };
        m.eq[size_t (b)] = { v ("On") > 0.5f, juce::roundToInt (v ("Type")), v ("Freq"), v ("Gain"), v ("Q") };
    }
    m.compOn = flag ("compOn"), m.compThresh = value ("compThresh"), m.compRatio = value ("compRatio");
    m.compAttackMs = value ("compAttack"), m.compReleaseMs = value ("compRelease"), m.compMakeup = value ("compMakeup");
    m.satOn = flag ("satOn"), m.satType = choice ("satType"), m.satDriveDb = value ("satDrive");
    m.satOutputDb = value ("satOutput"), m.satMix = value ("satMix") / 100.f;
    m.chorusOn = flag ("chorusOn"), m.chorusRate = value ("chorusRate"), m.chorusDepth = value ("chorusDepth") / 100.f, m.chorusMix = value ("chorusMix") / 100.f;
    m.delayOn = flag ("delayOn"), m.delayMode = choice ("delayMode"), m.delayChar = choice ("delayChar");
    const double bpm = hostBpm.load();
    if (flag ("delaySync"))
    {
        m.delayLeftMs = float (kDivBeats[choice ("delayLeftDiv")] * 60000.0 / bpm);
        m.delayRightMs = float (kDivBeats[choice ("delayRightDiv")] * 60000.0 / bpm);
    }
    else
        m.delayLeftMs = value ("delayLeftMs"), m.delayRightMs = value ("delayRightMs");
    m.delayFeedback = value ("delayFeedback") / 100.f, m.delayHp = value ("delayHp"), m.delayLp = value ("delayLp");
    m.delayMod = value ("delayMod") / 100.f, m.delayMix = value ("delayMix") / 100.f;
    m.stereoOn = flag ("stereoOn"), m.stereoWidth = value ("stereoWidth") / 100.f;
    m.outputDb = value ("output");
    return m;
}

void ViolinoProcessor::pushEvent (const Event& e)
{
    const auto scope = fifo.write (1);
    if (scope.blockSize1 > 0) events[size_t (scope.startIndex1)] = e;
    else if (scope.blockSize2 > 0) events[size_t (scope.startIndex2)] = e;
}

bool ViolinoProcessor::matchesClip (const ClipSet& set, double t, int pitch) const
{
    for (auto& c : set)
    {
        if (t < c->first - 0.1 || t > c->last + 0.1) continue;
        auto it = std::lower_bound (c->notes.begin(), c->notes.end(), std::pair<double, int> { t - kMatch, -1 });
        for (; it != c->notes.end() && it->first <= t + kMatch; ++it)
            if (it->second == pitch) return true;
    }
    return false;
}

// ------------------------------------------------------------------ áudio
void ViolinoProcessor::processBlock (juce::AudioBuffer<float>& buffer, juce::MidiBuffer& midi)
{
    juce::ScopedNoDenormals noDenormals;
    const int n = buffer.getNumSamples();
    if (mono.getNumSamples() < n) mono.setSize (1, n, false, false, true);  // raro: bloco maior que o anunciado
    mono.clear();
    auto* out = mono.getWritePointer (0);

    // tempo: playhead do DAW; sem transporte (Standalone) um relógio interno contínuo
    bool hasHost = false, isPlaying = false;
    double t0 = internalClock;
    long long hostSmp = 0;
    bool hostSmpOk = false;
    if (auto* ph = getPlayHead())
        if (auto pos = ph->getPosition())
        {
            if (auto bpm = pos->getBpm(); bpm && *bpm > 20 && wrapperType != wrapperType_Standalone)
                hostBpm = *bpm;
            if (auto ts = pos->getTimeInSeconds())
                hasHost = true, isPlaying = pos->getIsPlaying(), t0 = *ts;
            if (auto smp = pos->getTimeInSamples()) hostSmp = *smp, hostSmpOk = true;  // posição exata (sem arredondar segundos)
        }
    if (wrapperType == wrapperType_Standalone)  // o playhead do Standalone nunca dá play: relógio próprio
        hasHost = false, t0 = internalClock;
    if (! hasHost)
        isPlaying = true;
    if (timelinePlay.load() && ! (hasHost && isPlaying))
    {
        double tp = timelinePos.load();
        const double ca = cycleA.load(), cb = cycleB.load();
        if (cycleOn.load() && cb > ca + 0.05 && tp >= cb)  // Cycle: volta para o começo do trecho
        {
            tp = ca + std::fmod (tp - ca, cb - ca);
            timelinePos = tp;
            sampler.allNotesOff();
        }
        if (wrapperType == wrapperType_Standalone) t0 = tp;  // gravar no Standalone: as notas caem na posição da timeline
    }
    const double liveT0 = liveClock;  // relógio do preview: sempre anda, mesmo com o DAW parado
    liveClock += n / sampleRate;
    internalClock += n / sampleRate;
    if (isPlaying != wasPlaying || (isPlaying && std::abs (t0 - lastBlockTime) > 0.5))  // play/stop ou salto (loop)
    {
        if (wasPlaying && ! isPlaying) pushEvent ({ Event::transportStop, 0, 0, false, false, t0 });
        if (isPlaying) pushEvent ({ Event::transportStart, 0, 0, false, false, t0 });
        if (! isPlaying) sampler.allNotesOff();
    }
    wasPlaying = isPlaying;
    lastBlockTime = t0 + n / sampleRate;
    playheadSec = t0;
    playing = isPlaying;
    hostTransport = hasHost;

    PreviewSampler::Live live;
    const bool shorts = choice ("playMode") == 1;
    live.play = shorts ? PlayMode::longNormal : PlayMode::legato;
    const auto paramForced = Forced (choice ("articulation"));
    if (ksPending && (paramForced == liveForced || paramForced != lastParamForced)) ksPending = false;
    lastParamForced = paramForced;
    live.forced = ksPending ? liveForced : paramForced;
    if (shorts && live.forced == Forced::autoMode) live.forced = kShortForced[juce::jlimit (0, 2, choice ("shortsMode"))];
    const bool allAuto = choice ("articMode") == 0;
    if (allAuto) live.forced = Forced::autoMode;  // modo Auto: o preview também decide sozinho
    live.dynamicsFromCc = choice ("articMode") != 0;
    live.portaVelocity = juce::roundToInt (value ("portaVel"));
    live.intensity = value ("intensity") / 100.f;
    live.levelDb = value ("level");
    sampler.setLive (live);

    uiMidi.removeNextBlockOfMessages (midi, n);
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
                const bool held = pressed[size_t (q.pitch / 64)].load() & (1ull << (q.pitch % 64));  // o usuário está tocando essa tecla
                if (q.start >= tlStart && q.start < te && ! held)
                {
                    if (q.forced != Forced::autoMode && ! allAuto) { auto l2 = live; l2.forced = q.forced; sampler.setLive (l2); }  // a articulação marcada na nota
                    sampler.noteOn (pp, q.vel, liveT0 + (q.start - tlStart));
                    if (q.forced != Forced::autoMode && ! allAuto) sampler.setLive (live);
                }
                if (q.end >= tlStart && q.end < te && ! held) sampler.noteOff (pp, liveT0 + (q.end - tlStart));
            }
    }
    if (wasTimeline && ! tl) sampler.allNotesOff();  // Pause / Stop: nada fica soando
    wasTimeline = tl;
    int pos = 0;
    for (const auto meta : midi)
    {
        const auto& m = meta.getMessage();
        const int at = juce::jlimit (0, n, meta.samplePosition);
        if (at > pos) sampler.render (out + pos, at - pos), pos = at;
        const double t = t0 + at / sampleRate;
        if (m.isNoteOn())
        {
            const int p = m.getNoteNumber();
            if (int ks = keyswitchIndex (p); ks >= 0)
            {
                liveForced = Forced (ks), ksPending = true;
                live.forced = liveForced;
                sampler.setLive (live);
                pushEvent ({ Event::forced, uint8_t (ks), 0, false, false, t });
                continue;
            }
            const bool matched = isPlaying && hasHost && matchesClip (*set, t, p);  // já renderizada: toca o render
            mutedNote[size_t (p)] = matched;
            int vel = m.getVelocity();
            if (! matched && isPlaying && hasHost && choice ("articMode") == 0)
                if (auto d = dynCurves.load())
                    for (auto& curve : *d)
                        if (! curve->empty() && t >= curve->front().first && t <= curve->back().first)
                        {
                            auto it = std::upper_bound (curve->begin(), curve->end(), t, [] (double x, auto& c) { return x < c.first; });
                            const float cc = (it - 1)->second;
                            vel = juce::jlimit (45, 120, juce::roundToInt ((cc - 20.f) / 0.8f));  // inverso de 20 + 0.8 vel, sem extremos
                            break;
                        }
            if (! matched)
                sampler.noteOn (p < kMinPitch ? p + 12 * ((kMinPitch - p + 11) / 12) : p, vel, liveT0 + at / sampleRate);
            pressed[size_t (p / 64)] |= (1ull << (p % 64));
            pushEvent ({ Event::noteOn, uint8_t (p), uint8_t (m.getVelocity()), matched, isPlaying, t });
        }
        else if (m.isNoteOff())
        {
            const int p = m.getNoteNumber();
            if (keyswitchIndex (p) >= 0) continue;
            if (! mutedNote[size_t (p)])
                sampler.noteOff (p < kMinPitch ? p + 12 * ((kMinPitch - p + 11) / 12) : p, liveT0 + at / sampleRate);
            pressed[size_t (p / 64)] &= ~(1ull << (p % 64));
            pushEvent ({ Event::noteOff, uint8_t (p), 0, false, isPlaying, t });
        }
        else if (m.isController() && m.getControllerNumber() == 1)
        {
            sampler.setModWheel (m.getControllerValue()), modWheel = m.getControllerValue();
            pushEvent ({ Event::cc, uint8_t (m.getControllerValue()), 0, false, isPlaying, t });
        }
        else if (m.isPitchWheel())
            sampler.setPitchBend ((m.getPitchWheelValue() - 8192) / 8192.0f * 2.0f), pitchWheel = m.getPitchWheelValue();
        else if (m.isAllNotesOff() || m.isAllSoundOff())
            sampler.allNotesOff();
    }
    if (pos < n) sampler.render (out + pos, n - pos);

    // render da IA alinhado ao playhead (ou audição de uma frase clicada na timeline)
    bool audible = false;
    auto mixClip = [&] (const Clip& c, double startIndex) {
        for (int i = 0; i < n; ++i)
        {
            long long k = (long long) std::floor (startIndex) + i;
            if (k >= 0 && k < (long long) c.audio.size()) out[i] += c.audio[size_t (k)], audible = true;
        }
    };
    if (int a = auditionIndex.load(); a >= 0 && a < (int) set->size())
    {
        double p0 = auditionPos.load();
        mixClip (*(*set)[size_t (a)], p0);
        auditionPos = p0 + n;
        if (p0 > double ((*set)[size_t (a)]->audio.size())) auditionIndex = -1;
    }
    else if (timelinePlay.load() && ! (isPlaying && hasHost))
    {
        const double tp = timelinePos.load();
        double lastEnd = 0;
        if (auto pv = previewNotes.load())
            for (auto& q : *pv) lastEnd = std::max (lastEnd, q.end + 0.5);
        for (auto& c : *set)
        {
            lastEnd = std::max (lastEnd, c->origin + c->audio.size() / sampleRate);
            if (tp + n / sampleRate >= c->origin && tp < c->origin + c->audio.size() / sampleRate)
                mixClip (*c, (tp - c->origin) * sampleRate);
        }
        timelinePos = tp + n / sampleRate;
        if (tp > lastEnd && wrapperType != wrapperType_Standalone && ! cycleOn.load()) timelinePlay = false;  // no Standalone roda livre (para gravar)
    }
    else if (isPlaying && hasHost)
        for (auto& c : *set)
            if (t0 + n / sampleRate >= c->origin && t0 < c->origin + c->audio.size() / sampleRate)
                // índice pela posição em amostras do DAW: segundos convertidos arredondavam diferente a cada bloco,
                // pulando/repetindo 1 amostra centenas de vezes por segundo (o "chiado" só com o play do DAW)
                mixClip (*c, hostSmpOk ? double (hostSmp) - std::round (c->origin * sampleRate) : std::round ((t0 - c->origin) * sampleRate));
    renderAudible = audible;

    fx.set (mixSettings());
    buffer.clear();
    if (buffer.getNumChannels() >= 2)
        fx.process (out, buffer.getWritePointer (0), buffer.getWritePointer (1), n);
    else
    {
        juce::HeapBlock<float> r { size_t (n) };  // mono: raro (só se o host pedir)
        fx.process (out, buffer.getWritePointer (0), r.get(), n);
    }
    if (tl && metroOn.load() && wrapperType == wrapperType_Standalone)
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
    meterL = std::max (meterL.load() * 0.85f, buffer.getMagnitude (0, 0, n));
    meterR = std::max (meterR.load() * 0.85f, buffer.getMagnitude (std::min (1, buffer.getNumChannels() - 1), 0, n));
}

// ------------------------------------------------------------------ captura (mensagens)

void ViolinoProcessor::drainEvents()
{
    const bool capture = flag ("capture") && ! flag ("lock");  // Lock MIDI: o que foi gravado não muda
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
    }
    auto handle = [&] (const Event& e) {
        switch (e.type)
        {
            case Event::transportStart:
                ++pass, passActive = true, passHasNotes = false, passStart = e.time, ccPassTime = -1;
                break;
            case Event::transportStop:
                passActive = false;
                for (auto& [p, i] : openNote) notes[i].open = false;
                openNote.clear();
                dirty = true;
                break;
            case Event::forced:
                setParam ("articulation", float (e.a));  // keyswitch = clicar no botão
                break;
            case Event::cc:
            {
                if (! capture || ! e.capturable) break;
                // a captura segue o playhead também no CC1: o trecho tocado de novo substitui o antigo
                const double from = ccPassTime < 0 ? passStart : ccPassTime;
                ccCurve.erase (std::remove_if (ccCurve.begin(), ccCurve.end(), [&] (auto& c) { return c.pass != pass && c.time > from - 1e-6 && c.time <= e.time; }), ccCurve.end());
                auto at = std::lower_bound (ccCurve.begin(), ccCurve.end(), e.time, [] (auto& c, double t) { return c.time < t; });
                ccCurve.insert (at, { e.time, e.a, pass });
                ccPassTime = e.time;
                dirty = true;
                break;
            }
            case Event::noteOn:
            {
                if (! capture || ! e.capturable) break;  // DAW parado: só preview
                passHasNotes = true;
                // já capturada (o DAW tocou a mesma nota de novo)? só marca como vista
                for (size_t i = 0; i < notes.size(); ++i)
                    if (notes[i].pitch == e.a && std::abs (notes[i].start - e.time) < kMatch)
                    {
                        notes[i].pass = pass;
                        openNote[e.a] = i;
                        return;
                    }
                notes.push_back ({ e.time, e.time + 0.1, e.a, e.b, Forced (choice ("articulation")), pass, true });
                openNote[e.a] = notes.size() - 1;
                dirty = true;
                break;
            }
            case Event::noteOff:
            {
                auto it = openNote.find (e.a);
                if (it == openNote.end()) break;
                auto& nt = notes[it->second];
                if (nt.open || std::abs (nt.end - e.time) > kMatch)
                    nt.end = std::max (e.time, nt.start + 0.02), dirty = true;
                nt.open = false;
                openNote.erase (it);
                break;
            }
        }
    };
    for (int i = 0; i < scope.blockSize1; ++i) handle (events[size_t (scope.startIndex1 + i)]);
    for (int i = 0; i < scope.blockSize2; ++i) handle (events[size_t (scope.startIndex2 + i)]);

    // note-off perdido (ou tecla solta sem evento): nota aberta sem tecla pressionada é fechada agora
    for (auto it = openNote.begin(); it != openNote.end();)
    {
        const int p = it->first;
        if (! (pressed[size_t (p / 64)].load() & (1ull << (p % 64))) && it->second < notes.size())
        {
            auto& nt = notes[it->second];
            if (nt.open) nt.end = std::max (nt.start + 0.05, playheadSec.load()), nt.open = false, dirty = true;
            it = openNote.erase (it);
        }
        else ++it;
    }
    // a captura segue o playhead: o que foi capturado antes neste trecho e não voltou a tocar, sai
    if (capture && passActive && passHasNotes && hostTransport)
    {
        const double upTo = playheadSec.load() - 0.3;
        size_t before = notes.size();
        std::vector<CapNote> kept;
        for (auto& nt : notes)
            if (nt.pass == pass || nt.open || nt.start < passStart + 0.01 || nt.start > upTo)
                kept.push_back (nt);
        if (kept.size() != before)
        {
            notes = std::move (kept);
            openNote.clear();
            for (size_t i = 0; i < notes.size(); ++i)
                if (notes[i].open) openNote[notes[i].pitch] = i;
            dirty = true;
        }
    }
}

void ViolinoProcessor::rebuildPhrases()
{
    // ordena mantendo os índices das notas abertas
    std::vector<size_t> order (notes.size());
    for (size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::sort (order.begin(), order.end(), [&] (size_t a, size_t b) { return notes[a].start < notes[b].start; });
    std::vector<CapNote> sorted;
    for (auto i : order) sorted.push_back (notes[i]);
    notes = std::move (sorted);
    openNote.clear();
    for (size_t i = 0; i < notes.size(); ++i)
        if (notes[i].open) openNote[notes[i].pitch] = i;

    const auto as = articSettings();
    const int quality = choice ("quality"), takes = juce::roundToInt (value ("takes"));
    phrases.clear();
    for (size_t i = 0; i < notes.size(); ++i)
    {
        const bool cut = ! phrases.empty() && std::any_of (splits.begin(), splits.end(), [&] (double t) { return t > phrases.back().start && t <= notes[i].start; });
        if (phrases.empty() || notes[i].start - phrases.back().end >= kPhraseGap || cut)
        {
            phrases.emplace_back();
            phrases.back().start = notes[i].start;
        }
        auto& p = phrases.back();
        p.idx.push_back (i);
        p.end = std::max (p.end, notes[i].end);
        p.open = p.open || notes[i].open;
    }
    for (auto& p : phrases)
    {
        p.origin = p.start - kLeadIn;
        p.starts.clear();
        for (auto i : p.idx) p.starts.push_back ({ notes[i].start, notes[i].pitch });
        std::sort (p.starts.begin(), p.starts.end());
        std::vector<InNote> in;
        for (auto i : p.idx)
            in.push_back ({ notes[i].start - p.origin, notes[i].end - p.origin, notes[i].pitch, notes[i].vel, Tech::automatic,
                            choice ("articMode") == 0 ? Forced::autoMode  // modo Auto: o algoritmo decide tudo (a marcação fica guardada para os outros modos)
                            : notes[i].forced == Forced::autoMode && choice ("playMode") == 1 ? kShortForced[juce::jlimit (0, 2, choice ("shortsMode"))] : notes[i].forced });
        p.art = articulate (in, as);
        p.target.clear();
        const bool fromCc = as.mode != ArticMode::autoMode && ! ccCurve.empty();
        for (size_t k = 0; k < p.art.dynTimes.size(); ++k)
        {
            const double t = p.art.dynTimes[k] + p.origin;
            float v = p.art.dynValues[k];
            if (fromCc)
            {
                auto it = std::upper_bound (ccCurve.begin(), ccCurve.end(), t, [] (double x, auto& c) { return x < c.time; });
                v = it == ccCurve.begin() ? float (ccCurve.front().value) : float ((it - 1)->value);
            }
            if (! dynDrawn.empty() && t >= dynDrawn.front().first && t <= dynDrawn.back().first)
            {
                auto it = std::lower_bound (dynDrawn.begin(), dynDrawn.end(), std::pair<double, float> { t, -1.f });
                if (it != dynDrawn.end() && it != dynDrawn.begin() && it->first - (it - 1)->first < 0.5)  // dentro de um traço
                {
                    const auto& a0 = *(it - 1); const auto& a1 = *it;
                    v = a0.second + float ((t - a0.first) / std::max (1e-6, a1.first - a0.first)) * (a1.second - a0.second);
                }
            }
            p.target.push_back ({ t, v });
        }
        // uma linha por voz: o VIOLET toca uma nota por vez, então cordas duplas viram duas renders somadas
        p.voices.clear();
        for (int v = 0; v < 2; ++v)
        {
            std::vector<ArtNote> voice;
            for (auto& a : p.art.notes) if (a.voice == v) voice.push_back (a);
            if (! voice.empty())
                p.voices.push_back (toViolet (voice, as.play == PlayMode::longNormal ? -1.0 : as.legatoGap));
        }
        int fast = 0;
        for (auto& a : p.art.notes) fast += a.dur() <= kFast ? 1 : 0;
        p.fastShare = p.art.notes.empty() ? 0 : double (fast) / double (p.art.notes.size());
        uint64_t h = 1469598103934665603ull;
        for (auto& voice : p.voices)
        {
            h = fnv (h, 7777);
            for (auto& v : voice)
                h = fnv (fnv (fnv (fnv (h, std::llround (v.start * 1000)), std::llround (v.end * 1000)), v.pitch), v.tech);
        }
        p.content = h;
        p.hash = fnv (h, 0x5157) | 1;  // trocar a qualidade vale para os próximos renders; os prontos continuam valendo
        juce::ignoreUnused (quality, takes);
    }
}

void ViolinoProcessor::applyFade (const Phrase& p, std::vector<float>& au) const
{
    auto it = fades.find (std::llround (p.start * 1000));
    if (it == fades.end() || it->second <= 0.001) return;
    const size_t a = size_t (std::max (0.0, p.start - 0.06 - p.origin) * 48000), n = size_t (it->second * 48000);
    auto tn = fadeTension.find (it->first);
    const double ex = std::pow (2.0, 2.0 * (tn == fadeTension.end() ? 0.5 : tn->second));
    for (size_t i = 0; i < a && i < au.size(); ++i) au[i] = 0;
    for (size_t i = 0; i < n && a + i < au.size(); ++i) au[a + i] *= float (std::pow (double (i) / double (n), ex));
}

uint64_t ViolinoProcessor::dynKey (const Phrase& p) const
{
    uint64_t h = fnv (fnv (1469598103934665603ull, std::llround (value ("dynFollow") * 10)), std::llround (value ("intensity") * 10));
    for (size_t k = 0; k < p.target.size(); k += 5) h = fnv (h, std::llround (p.target[k].second));
    if (auto it = fades.find (std::llround (p.start * 1000)); it != fades.end()) h = fnv (h, std::llround (it->second * 1000));
    if (auto it = fadeTension.find (std::llround (p.start * 1000)); it != fadeTension.end()) h = fnv (h, std::llround (it->second * 1000));
    h = fnv (fnv (fnv (h, std::llround (value ("vibAmount") * 10)), std::llround (value ("vibRate") * 100)), choice ("playStyle"));
    h = fnv (h, std::llround (value ("evenOut") * 10));
    return h;
}

double ViolinoProcessor::styleVibrato() const
{
    static const double add[] = { 0, 15, 30, 5, 0, 12 };
    return add[juce::jlimit (0, 5, choice ("playStyle"))];
}

float ViolinoProcessor::styleIntensity() const
{
    static const float k[] = { 1.f, 1.1f, 1.25f, 0.9f, 0.75f, 1.3f };
    return k[juce::jlimit (0, 5, choice ("playStyle"))];
}

void ViolinoProcessor::applyVibrato (const Phrase& p, std::vector<float>& au) const
{
    // o VIOLET já canta com vibrato próprio; aqui só se SOMA vibrato (linha de atraso modulada), nas notas
    // longas, entrando devagar como um violinista: começa 0,22 s depois do ataque e cresce em 0,4 s
    const double amt = std::min (1.3, (value ("vibAmount") + styleVibrato()) / 100.0);
    if (amt <= 0.001 || au.size() < 4800) return;
    const double sr = 48000, rate = value ("vibRate"), cents = 30.0 * amt;
    const double A = (std::pow (2.0, cents / 1200.0) - 1.0) / (juce::MathConstants<double>::twoPi * rate) * sr;  // amplitude do atraso
    std::vector<float> env (au.size(), 0.f);
    for (auto& a : p.art.notes)
    {
        if (a.dur() < 0.35) continue;
        const double s0 = a.start + 0.22, e0 = a.end;
        for (size_t i = size_t (std::max (0.0, s0 * sr)); i < au.size() && i < size_t (e0 * sr); ++i)
        {
            const double t = i / sr;
            env[i] = std::max (env[i], float (std::min (1.0, (t - s0) / 0.4) * std::min (1.0, (e0 - t) / 0.08)));
        }
    }
    std::vector<float> out (au.size());
    const double w = juce::MathConstants<double>::twoPi * rate / sr;
    for (size_t n = 0; n < au.size(); ++n)
    {
        const double pos = double (n) - env[n] * A * std::sin (w * double (n));
        const auto i0 = (long long) std::floor (pos);
        const float fr = float (pos - double (i0));
        out[n] = i0 >= 0 && i0 + 1 < (long long) au.size() ? au[size_t (i0)] + fr * (au[size_t (i0 + 1)] - au[size_t (i0)]) : au[n];
    }
    au.swap (out);
}

juce::File ViolinoProcessor::cacheFile (uint64_t hash) const
{
    return Paths::dataDir().getChildFile ("cache").getChildFile (juce::String::toHexString ((juce::int64) hash) + ".f32");
}

void ViolinoProcessor::submit (const Phrase& p)
{
    if (p.voices.empty() || cache.count (p.hash) || engine->isQueued (p.hash))
        return;
    EngineService::Job job;
    job.id = p.hash, job.owner = this, job.voices = p.voices;
    job.quality = Quality (choice ("quality"));
    job.fastShare = p.fastShare;
    job.takes = juce::roundToInt (value ("takes"));
    job.steps = juce::roundToInt (value ("renderSteps"));
    if (flag ("modelDyn") && ! p.target.empty())  // CC1 para o modelo: a curva da frase a 25 Hz, desde a origem do render
    {
        const double len = p.end - p.origin + 2.0;
        for (int k = 0; k < int (len * 25.0); ++k)
        {
            const double t = p.origin + k / 25.0;
            auto it = std::upper_bound (p.target.begin(), p.target.end(), t, [] (double x, auto& c) { return x < c.first; });
            const float cc = it == p.target.begin() ? p.target.front().second : (it - 1)->second;
            job.cc25.push_back (juce::jlimit (0.f, 1.f, cc / 127.f));
        }
    }
    engine->submit (std::move (job));
}

std::vector<float> ViolinoProcessor::levelNotes (const Phrase& p, const std::vector<float>& audio) const
{
    // nivelador lento (como um LA-2A): o VIOLET deixa trechos ligados/longos 10-20 dB abaixo dos ataques curtos
    // (medido nos renders). Envelope de 300 ms aproximado da mediana da frase; silêncio e cauda não sobem.
    const float even = value ("evenOut") / 100.f;
    juce::ignoreUnused (p);
    if (even <= 0.001f || audio.size() < 48000) return audio;
    const size_t hop = 480, win = 14400, nf = audio.size() / hop;  // quadros de 10 ms, janela de 300 ms
    std::vector<double> pre (audio.size() + 1, 0.0);
    for (size_t i = 0; i < audio.size(); ++i) pre[i + 1] = pre[i] + double (audio[i]) * audio[i];
    std::vector<float> env (nf);
    for (size_t f = 0; f < nf; ++f)
    {
        const size_t c = f * hop, a = c > win / 2 ? c - win / 2 : 0, b = std::min (audio.size(), c + win / 2);
        env[f] = float (10 * std::log10 ((pre[b] - pre[a]) / double (std::max<size_t> (1, b - a)) + 1e-12));
    }
    std::vector<float> on;
    for (auto e : env) if (e > -60) on.push_back (e);
    if (on.size() < 10) return audio;
    std::nth_element (on.begin(), on.begin() + long (on.size() * 6 / 10), on.end());
    const float ref = on[on.size() * 6 / 10];  // um pouco acima da mediana: o alvo é o corpo da frase
    std::vector<float> g (nf, 0.f);
    for (size_t f = 0; f < nf; ++f)
        if (env[f] > ref - 35)  // abaixo disso é silêncio/cauda: não sobe ruído
            g[f] = std::clamp ((ref - env[f]) * even, -8.f, 10.f);  // até +10 dB: mais que isso sobe o ruído dos trechos baixos
    for (int pass = 0; pass < 2; ++pass)  // suaviza ~120 ms nos dois sentidos (sem bombear)
    {
        float y = g.empty() ? 0.f : g[0];
        for (size_t f = 0; f < nf; ++f) y += 0.08f * (g[f] - y), g[f] = y;
        y = g.empty() ? 0.f : g[nf - 1];
        for (size_t f = nf; f-- > 0;) y += 0.08f * (g[f] - y), g[f] = y;
    }
    std::vector<float> out (audio.size());
    for (size_t i = 0; i < audio.size(); ++i)
    {
        const double fp = double (i) / hop;
        const size_t f0 = std::min (nf - 1, size_t (fp)), f1 = std::min (nf - 1, f0 + 1);
        const float db = g[f0] + float (fp - double (f0)) * (g[f1] - g[f0]);
        out[i] = audio[i] * std::pow (10.f, db / 20.f);
    }
    return out;
}

std::vector<float> ViolinoProcessor::shapeDynamics (const Phrase& p, const std::vector<float>& audio) const
{
    const float amount = value ("dynFollow") / 100.f, intensity = value ("intensity") / 100.f * styleIntensity();
    if (amount <= 0.001f || p.target.size() < 4 || audio.size() < 48000)
        return audio;
    // volume medido do render (RMS de 50 ms a cada 10 ms) e a curva pedida, os dois em dB relativos à mediana
    const size_t hop = 480, win = 2400, nf = audio.size() / hop;
    std::vector<float> meas (nf), want (nf);
    std::vector<char> active (nf, 0);
    for (size_t f = 0; f < nf; ++f)
    {
        double e = 0;
        const size_t a = f * hop, b = std::min (audio.size(), a + win);
        for (size_t i = a; i < b; ++i) e += double (audio[i]) * audio[i];
        meas[f] = float (10 * std::log10 (e / double (std::max<size_t> (1, b - a)) + 1e-12));
        const double t = p.origin + double (f * hop) / 48000.0;
        auto it = std::upper_bound (p.target.begin(), p.target.end(), t, [] (double x, auto& c) { return x < c.first; });
        const float cc = it == p.target.begin() ? p.target.front().second : (it - 1)->second;
        want[f] = (cc - 64.f) / 64.f * 12.f * (0.4f + 0.6f * intensity);  // CC -> dB (±12 com intensidade máxima)
        for (auto& s : p.starts)
            if (t >= s.first - 0.02) active[f] = 1;
        if (t > p.end + 0.2) active[f] = 0;
    }
    auto median = [&] (const std::vector<float>& v) {
        std::vector<float> on;
        for (size_t f = 0; f < nf; ++f) if (active[f] && meas[f] > -70) on.push_back (v[f]);
        if (on.empty()) return 0.f;
        std::nth_element (on.begin(), on.begin() + long (on.size() / 2), on.end());
        return on[on.size() / 2];
    };
    const float mm = median (meas), mw = median (want);
    // ganho por quadro, suavizado (~150 ms) para não bombear entre notas
    std::vector<float> g (nf, 0.f);
    for (size_t f = 0; f < nf; ++f)
        if (active[f] && meas[f] > mm - 30)
            g[f] = std::clamp (amount * ((want[f] - mw) - (meas[f] - mm)), -12.f, 12.f);
    for (int pass2 = 0; pass2 < 2; ++pass2)
    {
        float y = 0;
        for (size_t f = 0; f < nf; ++f) y += 0.07f * (g[f] - y), g[f] = y;
        y = 0;
        for (size_t f = nf; f-- > 0;) y += 0.07f * (g[f] - y), g[f] = y;
    }
    // aplica: ganho interpolado + shelf de agudos dinâmico (mais forte = mais brilhante)
    std::vector<float> out (audio.size());
    violino::Biquad shelf;
    for (size_t a = 0; a < audio.size(); a += 256)
    {
        const size_t f = std::min (nf - 1, a / hop);
        shelf.set (violino::Biquad::highShelf, 3000, 0.35 * g[f], 0.7, 48000);
        for (size_t i = a; i < std::min (audio.size(), a + 256); ++i)
        {
            const float ff = float (i) / float (hop), fr = ff - std::floor (ff);
            const size_t f0 = std::min (nf - 1, size_t (ff)), f1 = std::min (nf - 1, f0 + 1);
            const float gd = g[f0] + fr * (g[f1] - g[f0]);
            out[i] = shelf.process (audio[i]) * std::pow (10.f, gd / 20.f);
        }
    }
    return out;
}

void ViolinoProcessor::rebuildClips()
{
    auto next = std::make_shared<ClipSet>();
    for (auto& p : phrases)
    {
        auto it = cache.find (p.hash);
        if (it == cache.end()) continue;
        auto& clip = clipCache[p.hash];
        if (! clip || std::abs (clip->origin - p.origin) > 1e-6 || clip->dynKey != dynKey (p))
        {
            auto c = std::make_shared<Clip>();
            c->origin = p.origin, c->first = p.start, c->last = p.end, c->dynKey = dynKey (p);
            auto shaped = shapeDynamics (p, levelNotes (p, it->second.audio));
            applyVibrato (p, shaped);
            applyFade (p, shaped);
            it->second.peaks = peaksOf (shaped);
            const double ratio = 48000.0 / sampleRate;
            c->audio.resize (size_t (double (shaped.size()) / ratio));
            juce::WindowedSincInterpolator interp;  // 48 kHz -> taxa do DAW sem espelhar agudos (Lagrange gerava chiado)
            interp.process (ratio, shaped.data(), c->audio.data(), int (c->audio.size()));
            c->notes = p.starts;
            clip = c;
        }
        next->push_back (clip);
    }
    // curvas das frases ainda sem render: o preview toca com a mesma dinâmica que o render vai ter
    auto dyn = std::make_shared<DynSet>();
    for (auto& p : phrases)
        if (! cache.count (p.hash) && ! p.target.empty())
            dyn->push_back (std::make_shared<const std::vector<std::pair<double, float>>> (p.target));
    retiredDyn.push_back (dynCurves.load());
    dynCurves.store (dyn);
    if (retiredDyn.size() > 8) retiredDyn.erase (retiredDyn.begin());
    {
        auto pv = std::make_shared<std::vector<PNote>>();
        for (auto& p : phrases)
            if (! cache.count (p.hash))
                for (auto i : p.idx)
                    if (i < notes.size() && ! notes[i].open)  // a nota ainda segurada não entra (o fim dela não existe ainda)
                        pv->push_back ({ notes[i].start, notes[i].end, notes[i].pitch, notes[i].vel, notes[i].forced });
        retiredPreview.push_back (previewNotes.load());
        previewNotes.store (pv);
        if (retiredPreview.size() > 8) retiredPreview.erase (retiredPreview.begin());
    }
    retired.push_back (clips.load());
    clips.store (next);
    if (retired.size() > 8) retired.erase (retired.begin());
}

void ViolinoProcessor::timerCallback()
{
    const double tStart = juce::Time::getMillisecondCounterHiRes();
    struct Lap { double t0; ~Lap() { const double d = juce::Time::getMillisecondCounterHiRes() - t0; if (d > 40) appLog ("slow tick: " + juce::String (juce::roundToInt (d)) + " ms"); } } lap { tStart };
    if (sampleState.load() == 1) loadSamplesNow();
    drainEvents();
    // mudar modo/qualidade muda o hash das frases (re-render só do que mudou)
    uint64_t sh = 1469598103934665603ull;
    for (auto* id : { "playMode", "shortsMode", "articMode", "quality", "legatoGap", "portaVel", "takes", "renderSteps", "playStyle" })
        sh = fnv (sh, std::llround (value (id) * 1000));
    if (sh != settingsHash) settingsHash = sh, dirty = true;
    const uint64_t dk = fnv (std::llround (value ("evenOut") * 10), 0) ^ fnv (fnv (fnv (fnv (7, std::llround (value ("dynFollow") * 10)), std::llround (value ("intensity") * 10)), std::llround (value ("vibAmount") * 10)), std::llround (value ("vibRate") * 100));
    const bool dynChanged = dk != dynSettings;
    dynSettings = dk;

    if (! allBusy.load() && ! engine->status().loading)
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
    if (dirty)
    {
        rebuildPhrases();
        dirty = false;
        clipsChanged = true;
    }
    EngineService::Result r;
    while (engine->popResult (this, r))
    {
        if (r.error.isNotEmpty())
        {
            if (r.error != "cancelled") lastError = r.error;
            continue;
        }
        lastError = {};
        for (auto& p : phrases)
            if (p.hash == r.id && ! p.starts.empty())
            {
                const double first = p.starts.front().first - p.origin;  // 1º ataque, em segundos do áudio
                const size_t z = size_t (std::max (0.0, first - 0.06) * 48000), fade = 1920;  // 40 ms
                auto& au = r.take.audio;
                for (size_t i = 0; i < std::min (z, au.size()); ++i) au[i] = 0;
                for (size_t i = 0; i < fade && z + i < au.size(); ++i)
                    au[z + i] *= float (0.5 - 0.5 * std::cos (3.14159265358979 * double (i) / double (fade)));
            }
        auto f = cacheFile (r.id);
        f.getParentDirectory().createDirectory();
        f.replaceWithData (r.take.audio.data(), r.take.audio.size() * sizeof (float));
        // cache limitado: acima de 1,5 GB apaga os renders mais antigos até 1 GB
        {
            juce::Array<juce::File> files = f.getParentDirectory().findChildFiles (juce::File::findFiles, false, "*.f32");
            juce::int64 total = 0;
            for (auto& x : files) total += x.getSize();
            if (total > (juce::int64) 1536 << 20)
            {
                std::sort (files.begin(), files.end(), [] (const juce::File& a, const juce::File& b) { return a.getLastModificationTime() < b.getLastModificationTime(); });
                for (auto& x : files)
                {
                    if (total < (juce::int64) 1024 << 20) break;
                    total -= x.getSize();
                    x.deleteFile();
                }
            }
        }
        auto peaks = peaksOf (r.take.audio);
        cache[r.id] = { std::move (r.take.audio), r.take.accuracy, std::move (peaks) };
        clipsChanged = true;
    }
    for (auto& p : phrases)
    {
        if (! cache.count (p.hash))  // render feito antes desta versão: estava guardado com a qualidade no nome
            for (auto old : legacyHashes (p))
            {
                if (auto it = cache.find (old); it != cache.end()) { cache[p.hash] = it->second; clipsChanged = true; break; }
                if (auto of = cacheFile (old); of.existsAsFile()) { of.copyFileTo (cacheFile (p.hash)); break; }
            }
        if (! cache.count (p.hash))
        {
            auto f = cacheFile (p.hash);  // render de uma sessão anterior
            if (f.existsAsFile())
            {
                juce::MemoryBlock mb;
                f.loadFileAsData (mb);
                Rendered rd;
                rd.audio.assign ((const float*) mb.getData(), (const float*) mb.getData() + mb.getSize() / sizeof (float));
                rd.peaks = peaksOf (rd.audio);
                cache[p.hash] = std::move (rd);
                clipsChanged = true;
            }
        }
        if (cache.count (p.hash)) renderedRegions[p.hash] = { p.start, p.end };
    }
    if (clipsChanged || dynChanged) rebuildClips();

    // Autorender: frase completa = o playhead passou 2 s do fim, ou o transporte parou
    if (flag ("autorender"))
    {
        const double now = playheadSec.load();
        for (auto& p : phrases)
            if (! p.open && ! stopped.count (p.hash) && (! playing.load() || now > p.end + kPhraseGap || now < p.start - 0.5))
                submit (p);
    }
}

// ------------------------------------------------------------------ interface
juce::var ViolinoProcessor::buildUiState()
{
    auto* o = new juce::DynamicObject();
    juce::var state (o);

    auto* pv = new juce::DynamicObject();
    for (auto* p : getParameters())
        if (auto* rp = dynamic_cast<juce::RangedAudioParameter*> (p))
        {
            auto* e = new juce::DynamicObject();
            e->setProperty ("n", rp->getValue());
            e->setProperty ("d", rp->getDefaultValue());
            e->setProperty ("v", rp->convertFrom0to1 (rp->getValue()));
            const float plain = rp->convertFrom0to1 (rp->getValue());
            juce::String text = dynamic_cast<juce::AudioParameterFloat*> (rp) != nullptr
                                    ? (rp->getLabel() == "dB" || rp->getLabel() == ":1" ? juce::String (plain, 1)
                                       : rp->getLabel() == "Hz" ? (plain < 10 ? juce::String (plain, 2) : plain >= 1000 ? juce::String (plain / 1000, plain >= 10000 ? 1 : 2) + "k" : juce::String (juce::roundToInt (plain)))
                                       : rp->getLabel() == "s" || rp->getLabel() == "x" ? juce::String (plain, 2) : rp->getLabel().isEmpty() ? juce::String (plain, 2) : juce::String (juce::roundToInt (plain)))
                                    : rp->getCurrentValueAsText();
            if (rp->getLabel() == "dB" && plain > 0.05f) text = "+" + text;
            e->setProperty ("text", text + (rp->getLabel() == ":1" ? ":1" : rp->getLabel().isNotEmpty() ? " " + rp->getLabel() : juce::String()));
            pv->setProperty (rp->getParameterID(), juce::var (e));
        }
    o->setProperty ("params", juce::var (pv));

    auto st = engine->status();
    auto* en = new juce::DynamicObject();
    en->setProperty ("loaded", st.loaded);
    en->setProperty ("loading", st.loading);
    en->setProperty ("error", lastError.isNotEmpty() ? lastError : st.error);
    en->setProperty ("gpu", st.gpu);
    en->setProperty ("used", double (st.usedBytes) / (1 << 30));
    en->setProperty ("total", double (st.totalBytes) / (1 << 30));
    en->setProperty ("queued", st.queued);
    en->setProperty ("samples", sampleState.load() == 2);
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
    o->setProperty ("settings", juce::var (se));
    o->setProperty ("engine", juce::var (en));

    // frases, notas (com a técnica decidida) e dinâmica
    juce::Array<juce::var> ph, nt, dyn;
    int rendered = 0;
    for (size_t k = 0; k < phrases.size(); ++k)
    {
        auto& p = phrases[k];
        int state = 0;  // 0 captured, 1 rendered, 2 queued/rendering, 3 outdated
        double prog = 0;
        if (cache.count (p.hash)) state = 1, ++rendered;
        else if (engine->isQueued (p.hash)) state = 2, prog = st.current == p.hash ? st.progress : 0;
        else
            for (auto& [h, reg] : renderedRegions)
                if (h != p.hash && reg.first < p.end && reg.second > p.start) { state = 3; break; }
        juce::var peaks;
        if (auto it = cache.find (p.hash); it != cache.end()) peaks = it->second.peaks;
        auto fd = fades.find (std::llround (p.start * 1000));
        auto ft = fadeTension.find (std::llround (p.start * 1000));
        juce::String name;
        for (auto i : p.idx) if (i < notes.size() && notes[i].take.isNotEmpty()) { name = notes[i].take; break; }
        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks, fd == fades.end() ? 0.0 : fd->second,
                                         ft == fadeTension.end() ? 0.5 : ft->second, name });
        for (auto& a : p.art.notes)
            nt.add (juce::Array<juce::var> { a.start + p.origin, a.end + p.origin, a.pitch, uiArt (a.tech), state, juce::String (a.reason) });
        for (size_t i = 0; i < p.target.size(); i += 5)  // 10 Hz para a UI
            if (p.target[i].first >= p.start - 0.1 && p.target[i].first <= p.end + 0.3)
                dyn.add (juce::Array<juce::var> { p.target[i].first, p.target[i].second });
    }
    o->setProperty ("phrases", ph);
    juce::Array<juce::var> cap;  // notas capturadas (editáveis), na ordem de notes
    for (auto& nt : notes)
        cap.add (juce::Array<juce::var> { nt.start, nt.end, nt.pitch, int (nt.forced), nt.vel });
    o->setProperty ("cap", cap);
    o->setProperty ("notes", nt);
    o->setProperty ("dyn", dyn);
    o->setProperty ("rendered", rendered);
    bool busy = false;
    for (auto& p : phrases) busy = busy || (! cache.count (p.hash) && engine->isQueued (p.hash));
    o->setProperty ("busy", busy);
    o->setProperty ("playhead", playheadSec.load());
    o->setProperty ("playing", playing.load() && hostTransport.load());
    o->setProperty ("renderAudible", renderAudible.load());
    juce::Array<juce::var> keys;
    for (int p = 0; p < 128; ++p)
        if (pressed[size_t (p / 64)].load() & (1ull << (p % 64))) keys.add (p);
    o->setProperty ("keys", keys);
    o->setProperty ("mod", modWheel.load());
    o->setProperty ("bend", pitchWheel.load());
    o->setProperty ("meters", juce::Array<juce::var> { meterL.load(), meterR.load() });
    o->setProperty ("gr", fx.gainReductionDb());
    o->setProperty ("bpm", hostBpm.load());
    o->setProperty ("prefs", uiPrefs);
    if (auditionIndex.load() < 0) auditionPhrase = -1;
    o->setProperty ("audition", auditionPhrase);
    o->setProperty ("internalPlay", timelinePlay.load());
    o->setProperty ("internalPos", timelinePos.load());
    o->setProperty ("hostTransport", hostTransport.load());
    o->setProperty ("standalone", wrapperType == wrapperType_Standalone);
    o->setProperty ("canUndo", ! undoStack.empty());
    o->setProperty ("metro", metroOn.load());
    o->setProperty ("cycle", juce::Array<juce::var> { cycleOn.load(), cycleA.load(), cycleB.load() });
    o->setProperty ("canRedo", ! redoStack.empty());
    o->setProperty ("auditionPos", auditionPhrase >= 0 ? auditionPos.load() / sampleRate : 0.0);
    return state;
}

void ViolinoProcessor::handleUiCommand (const juce::var& c)
{
    // cada edição é um passo de desfazer, mas só se mudou algo de verdade (clique sem efeito não conta)
    static const juce::StringArray kEdits { "noteEdit", "noteDel", "noteAdd", "noteArt", "noteTool", "noteVel", "noteAddMany", "takeResize",
                                            "takeName", "splitTake", "fade", "dynDraw", "dynClear", "deleteTake", "clear", "importMidi" };
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
{
    const auto cmd = c["cmd"].toString();
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
    if (cmd == "cycle")  // {on, a, b}: liga/desliga e (opcional) o trecho
    {
        if (c.hasProperty ("a") && c.hasProperty ("b") && double (c["b"]) > double (c["a"]) + 0.05)
            cycleA = std::max (0.0, double (c["a"])), cycleB = double (c["b"]);
        if (c.hasProperty ("on")) cycleOn = bool (c["on"]);
        return;
    }
    if (cmd == "metro") { metroOn = ! metroOn.load(); Settings::set ("metronome", metroOn.load()); return; }
    if (cmd == "pause") { timelinePlay = false; return; }  // fica onde parou; Play continua dali
    if (cmd == "stop")
    {
        double first = 1e18;
        for (auto& p : phrases) first = std::min (first, p.origin);
        // parado: o segundo Stop volta para o começo (como no Ableton)
        if (! timelinePlay.load() && std::abs (timelinePos.load() - playStart) < 1e-6) playStart = first < 1e17 ? first : 0.0;
        timelinePlay = false;
        timelinePos = playStart;
        auditionIndex = -1, auditionPhrase = -1;
        return;
    }
    if (cmd == "set")
    {
        if (auto* p = params.getParameter (c["id"].toString()))
        {
            if (c.hasProperty ("n")) p->setValueNotifyingHost (juce::jlimit (0.0f, 1.0f, float (c["n"])));
            else p->setValueNotifyingHost (p->convertTo0to1 (float (c["v"])));
        }
        if (c["id"].toString() == "quality")  // Low 8 · Medium 15 · High 30 · Extreme 30 (+ 8 takes)
            setParam ("renderSteps", float (qualityInfo (Quality (choice ("quality"))).steps));
        if (c["id"].toString() == "revMode")
        {
            const char* ids[] = { "revDecay", "revSize", "revAttack", "revEarly", "revLate", "revHighFreq", "revHighShelf",
                                  "revBassMult", "revModRate", "revModDepth", "revHighCut", "predelay" };
            const auto& pr = kRevPresets[juce::jlimit (0, 8, choice ("revMode"))];
            for (int k = 0; k < 12; ++k) setParam (ids[k], pr[k]);
        }
        // botão de articulação clicado: vale para todas as notas capturadas e as próximas
        if (c["id"].toString() == "articulation")
        {
            for (auto& nt : notes) nt.forced = Forced (choice ("articulation"));
            dirty = true;
        }
    }
    else if (cmd == "pref")
    {
        if (auto* d = uiPrefs.getDynamicObject()) d->setProperty (c["key"].toString(), c["value"]);
    }
    else if (cmd == "render")
    {
        if (dirty) rebuildPhrases(), dirty = false;
        stopped.clear();
        for (auto& p : phrases) submit (p);
    }
    else if (cmd == "noteEdit" || cmd == "noteDel" || cmd == "noteAdd" || cmd == "noteArt")
    {
        // edição na timeline: índices das notas capturadas (ordem do último estado enviado)
        std::vector<int> ids;
        if (auto* a = c["ids"].getArray()) for (auto& v : *a) ids.push_back (int (v));
        auto valid = [&] (int i) { return i >= 0 && i < (int) notes.size(); };
        if (cmd == "noteEdit")
        {
            const double dt = double (c["dt"]), de = double (c["de"]);
            const int dp = int (c["dp"]);
            for (int i : ids)
                if (valid (i))
                {
                    auto& nt = notes[size_t (i)];
                    nt.start = std::max (0.0, nt.start + dt);
                    nt.end = std::max (nt.start + 0.03, nt.end + dt + de);
                    nt.pitch = juce::jlimit (kMinPitch - 24, 108, nt.pitch + dp);
                }
        }
        else if (cmd == "noteDel")
        {
            std::sort (ids.rbegin(), ids.rend());
            for (int i : ids)
                if (valid (i)) notes.erase (notes.begin() + i);
        }
        else if (cmd == "noteAdd")
            notes.push_back ({ double (c["s"]), double (c["e"]), int (c["p"]), 90, Forced (choice ("articulation")), pass, false });
        else
            for (int i : ids)
                if (valid (i)) notes[size_t (i)].forced = Forced (juce::jlimit (0, 9, int (c["art"])));
        openNote.clear();
        dirty = true;
    }
    else if (cmd == "renderPhrase" || cmd == "reRender" || cmd == "unrender" || cmd == "deleteTake" || cmd == "unrenderAll")
    {
        const int k = int (c["phrase"]);
        auto unrender = [&] (const Phrase& p) {
            cache.erase (p.hash), clipCache.erase (p.hash), renderedRegions.erase (p.hash);
            cacheFile (p.hash).deleteFile();
            for (auto old : legacyHashes (p)) cache.erase (old), cacheFile (old).deleteFile();
            stopped.insert (p.hash);  // não volta sozinho pelo Autorender: o usuário escolhe quando refazer
        };
        if (cmd == "unrenderAll")
            for (auto& p : phrases) unrender (p);
        else if (k >= 0 && k < (int) phrases.size())
        {
            auto& p = phrases[size_t (k)];
            if (cmd == "reRender") unrender (p);
            if (cmd == "renderPhrase" || cmd == "reRender") { stopped.erase (p.hash); submit (p); }
            else if (cmd == "unrender") unrender (p);
            else
            {
                auto idx = p.idx;
                std::sort (idx.rbegin(), idx.rend());
                for (auto i : idx) if (i < notes.size()) notes.erase (notes.begin() + long (i));
                openNote.clear();
                dirty = true;
            }
        }
        rebuildClips();
    }
    else if (cmd == "noteTool")
    {
        std::vector<int> ids;
        if (auto* arr = c["ids"].getArray()) for (auto& v : *arr) ids.push_back (int (v));
        std::vector<CapNote*> sel;
        for (int i : ids) if (i >= 0 && i < (int) notes.size()) sel.push_back (&notes[size_t (i)]);
        if (sel.empty()) return;
        const auto op = c["op"].toString();
        const double arg = double (c["arg"]), beat = 60.0 / hostBpm.load();
        double t0 = 1e18, t1 = -1e18;
        for (auto* n : sel) t0 = std::min (t0, n->start), t1 = std::max (t1, n->end);
        juce::Random rnd;
        std::vector<CapNote> added;
        for (auto* n : sel)
        {
            if (op == "transpose") n->pitch = juce::jlimit (kMinPitch - 24, 108, n->pitch + int (arg));
            else if (op == "velocity") n->vel = juce::jlimit (1, 127, int (arg));
            else if (op == "quantize")  // arg = grade em semínimas (0.25 = 1/16); força 100 %
            {
                const double g = beat * arg, len = n->end - n->start;
                n->start = std::round (n->start / g) * g;
                n->end = n->start + std::max (g, std::round (len / g) * g);
            }
            else if (op == "humanize")  // arg = ms máximo; velocity ±8
            {
                const double d = (rnd.nextDouble() * 2 - 1) * arg / 1000.0;
                n->start = std::max (0.0, n->start + d), n->end += d;
                n->vel = juce::jlimit (1, 127, n->vel + rnd.nextInt (17) - 8);
            }
            else if (op == "stretch")
            {
                n->start = t0 + (n->start - t0) * arg, n->end = t0 + (n->end - t0) * arg;
            }
            else if (op == "reverse")
            {
                const double s0 = t0 + (t1 - n->end), e0 = t0 + (t1 - n->start);
                n->start = s0, n->end = e0;
            }
            else if (op == "split")  // divide cada nota no meio
            {
                const double m = 0.5 * (n->start + n->end);
                added.push_back (*n);
                added.back().start = m;
                n->end = m;
            }
            else if (op == "scale")  // arg = tônica (0..11); c["mode"] 0 maior, 1 menor
            {
                static const int major[] = { 0, 2, 4, 5, 7, 9, 11 }, minor[] = { 0, 2, 3, 5, 7, 8, 10 };
                const int* sc = int (c["mode"]) == 1 ? minor : major;
                int best = n->pitch, bd = 99;
                for (int p = n->pitch - 2; p <= n->pitch + 2; ++p)
                    for (int k = 0; k < 7; ++k)
                        if ((((p - int (arg)) % 12) + 12) % 12 == sc[k] && std::abs (p - n->pitch) < bd) bd = std::abs (p - n->pitch), best = p;
                n->pitch = best;
            }
        }
        if (op == "legato")  // cada nota vai até a próxima
        {
            std::sort (sel.begin(), sel.end(), [] (auto* x, auto* y) { return x->start < y->start; });
            for (size_t k = 0; k + 1 < sel.size(); ++k) sel[k]->end = std::max (sel[k]->start + 0.03, sel[k + 1]->start);
        }
        for (auto& n : added) notes.push_back (n);
        openNote.clear();
        dirty = true;
    }
    else if (cmd == "splitTake")
    {
        splits.push_back (double (c["t"]));
        dirty = true;
    }
    else if (cmd == "fade")
    {
        const int k = int (c["phrase"]);
        if (k >= 0 && k < (int) phrases.size())
        {
            const auto key = std::llround (phrases[size_t (k)].start * 1000);
            if (c.hasProperty ("sec")) fades[key] = juce::jlimit (0.0, 4.0, double (c["sec"]));
            if (c.hasProperty ("tension")) fadeTension[key] = juce::jlimit (-1.0, 1.0, double (c["tension"]));
        }
        rebuildClips();
    }
    else if (cmd == "takeResize")  // bordas da região: corta/estende; stretch = estica o tempo das notas
    {
        const int k = int (c["phrase"]);
        if (k >= 0 && k < (int) phrases.size())
        {
            const auto& p = phrases[size_t (k)];
            const double a0 = p.start, a1 = p.end, b0 = std::max (0.0, double (c["start"])), b1 = double (c["end"]);
            const bool stretch = bool (c["stretch"]);
            std::vector<size_t> del;
            size_t first = SIZE_MAX, last = SIZE_MAX;
            for (auto i : p.idx)
            {
                if (i >= notes.size()) continue;
                auto& nt = notes[i];
                if (stretch)
                {
                    auto map = [&] (double t) { return b0 + (t - a0) / std::max (1e-6, a1 - a0) * (b1 - b0); };
                    nt.start = map (nt.start), nt.end = std::max (nt.start + 0.03, map (nt.end));
                    continue;
                }
                if (nt.start >= b1 - 0.02 || nt.end <= b0 + 0.02) { del.push_back (i); continue; }
                nt.start = std::max (nt.start, b0), nt.end = std::min (nt.end, b1);
                if (first == SIZE_MAX || nt.start < notes[first].start) first = i;
                if (last == SIZE_MAX || nt.end > notes[last].end) last = i;
            }
            if (! stretch && first != SIZE_MAX && b0 < a0) notes[first].start = b0;  // estender: a primeira nota começa antes
            if (! stretch && last != SIZE_MAX && b1 > a1) notes[last].end = b1;      // estender: a última nota dura mais
            std::sort (del.rbegin(), del.rend());
            for (auto i : del) notes.erase (notes.begin() + long (i));
            openNote.clear();
            dirty = true;
        }
    }
    else if (cmd == "noteVel")  // [[índice, velocity], ...]
    {
        if (auto* arr = c["vels"].getArray())
            for (auto& v : *arr)
            {
                const int i = int (v[0]);
                if (i >= 0 && i < (int) notes.size()) notes[size_t (i)].vel = juce::jlimit (1, 127, int (v[1]));
            }
        dirty = true;
    }
    else if (cmd == "dynDraw")
    {
        std::vector<std::pair<double, float>> pts;
        if (auto* arr = c["pts"].getArray())
            for (auto& v : *arr) pts.push_back ({ double (v[0]), float (double (v[1])) });
        if (pts.size() >= 2)
        {
            std::sort (pts.begin(), pts.end());
            const double a0 = pts.front().first, a1 = pts.back().first;
            dynDrawn.erase (std::remove_if (dynDrawn.begin(), dynDrawn.end(), [&] (auto& d) { return d.first >= a0 && d.first <= a1; }), dynDrawn.end());
            dynDrawn.insert (dynDrawn.end(), pts.begin(), pts.end());
            std::sort (dynDrawn.begin(), dynDrawn.end());
            dirty = true;
        }
    }
    else if (cmd == "dynClear")
    {
        dynDrawn.clear();
        dirty = true;
    }
    else if (cmd == "dragAll")
    {
        const auto sig = mixSignature();
        auto f = allMixFile (sig);
        if (allReadySig.load() == sig && f.existsAsFile()) { if (onDragRequested) onDragRequested (f); return; }
        f.getParentDirectory().createDirectory();
        juce::String err;
        if (writeWav (f, -1, err)) { allReadySig = sig; if (onDragRequested) onDragRequested (f); }
        else if (err.isNotEmpty()) lastError = err;
    }
    else if (cmd == "stopRender")
    {
        // para o que está na fila e o render em andamento; o Autorender não reenvia essas frases
        for (auto& p : phrases)
            if (! cache.count (p.hash)) stopped.insert (p.hash);
        engine->cancelOwner (this);
    }
    else if (cmd == "clear")
    {
        if (flag ("lock")) return;
        engine->cancelOwner (this);
        notes.clear(), openNote.clear(), renderedRegions.clear(), ccCurve.clear(), splits.clear(), fades.clear(), fadeTension.clear(), dynDrawn.clear();
        dirty = true;
    }
    else if (cmd == "model")
    {
        if (engine->status().loaded) engine->requestUnload();
        else engine->requestLoad();
    }
    else if (cmd == "key")
    {
        auto m = bool (c["on"]) ? juce::MidiMessage::noteOn (1, int (c["note"]), juce::uint8 (100))
                                : juce::MidiMessage::noteOff (1, int (c["note"]));
        m.setTimeStamp (juce::Time::getMillisecondCounterHiRes() * 0.001);
        uiMidi.addMessageToQueue (m);
    }
    else if (cmd == "audition")
    {
        int k = int (c["phrase"]), clipIdx = -1, i = 0;
        if (k == auditionPhrase && auditionIndex.load() >= 0)  // mesmo botão: para
        {
            auditionIndex = -1, auditionPhrase = -1;
            return;
        }
        for (size_t j = 0; j < phrases.size(); ++j)
            if (cache.count (phrases[j].hash)) { if (int (j) == k) clipIdx = i; ++i; }
        auditionPos = 0;
        auditionIndex = clipIdx;
        auditionPhrase = clipIdx >= 0 ? k : -1;
    }
    else if (cmd == "log")
        Paths::dataDir().getChildFile ("ui.log").appendText (juce::Time::getCurrentTime().toString (true, true) + "  " + c["msg"].toString() + juce::newLine);
    else if (cmd == "stopAudition")
        auditionIndex = -1, auditionPhrase = -1;
    else if (cmd == "play" || cmd == "seek" || cmd == "rewind")
    {
        double first = 1e18, last = -1e18;
        for (auto& p : phrases)
        {
            first = std::min (first, p.origin), last = std::max (last, p.end + 0.5);
            if (auto it = cache.find (p.hash); it != cache.end()) last = std::max (last, p.origin + it->second.audio.size() / 48000.0);
        }
        if (cmd == "seek") { timelinePos = playStart = std::max (0.0, double (c["t"])); return; }
        if (cmd == "rewind") { timelinePos = playStart = first < 1e17 ? first : 0.0; return; }
        if (timelinePlay.load()) { timelinePlay = false; return; }  // Play (ou Espaço) de novo = pausa; continua dali
        if (wrapperType != wrapperType_Standalone)  // no plugin, só tem sentido onde há o que tocar
        {
            if (first > 1e17) return;
            if (timelinePos.load() >= last - 0.05 || timelinePos.load() < first - 30) timelinePos = first;
        }
        if (cycleOn.load() && cycleB.load() > cycleA.load() + 0.05 && (timelinePos.load() < cycleA.load() || timelinePos.load() >= cycleB.load()))
            timelinePos = cycleA.load();
        playStart = timelinePos.load();
        auditionIndex = -1, auditionPhrase = -1;
        timelinePlay = true;
    }
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
    else if (cmd == "dragMidi")
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
        if (bool (c["dyn"]))
        {
            int last = -1;
            for (auto& [tt, v] : p.target)
            {
                const int cv = juce::jlimit (0, 127, juce::roundToInt (v));
                if (std::abs (cv - last) < 1 || tt < p.start - 0.05 || tt > p.end + 0.3) continue;
                last = cv;
                const double tk = std::max (0.0, (tt - p.start) * tps);
                seq.addEvent (juce::MidiMessage::controllerEvent (1, 1, cv), tk);
                seq.addEvent (juce::MidiMessage::controllerEvent (1, 11, cv), tk);
            }
        }
        seq.updateMatchedPairs();
        juce::MidiFile mf;
        mf.setTicksPerQuarterNote (960);
        mf.addTrack (seq);
        auto dir = Paths::dataDir().getChildFile ("exports");
        dir.createDirectory();
        auto f = dir.getChildFile ("Violin phrase " + juce::String (k + 1) + (bool (c["dyn"]) ? " dyn " : " ") + juce::Time::getCurrentTime().formatted ("%H%M%S") + ".mid");
        if (auto os = f.createOutputStream(); os != nullptr && mf.writeTo (*os))
        {
            os.reset();
            if (onDragRequested) onDragRequested (f);
        }
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
        startSampleLoad();
    else if (cmd == "export")
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
        auto path = c["path"].toString();
        juce::File f (path);
        if (path.startsWith ("lib:"))  // peça da biblioteca: dentro do pacote do plugin (ou dataDir/library)
        {
            const auto rel = path.substring (4);
            for (auto dir : { Paths::pluginDir().getParentDirectory().getChildFile ("Resources/library"),
                              juce::File ("C:\\Program Files\\Common Files\\VST3\\Violino.vst3\\Contents\\Resources\\library"),
                              Paths::dataDir().getChildFile ("library") })
                if (dir.getChildFile (rel).existsAsFile()) { f = dir.getChildFile (rel); break; }
        }
        if (! importMidi (f, err)) lastError = err;
    }
}

bool ViolinoProcessor::exportWav (const juce::File& file, juce::String& error) { return writeWav (file, -1, error); }

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
}

bool ViolinoProcessor::writeWav (const juce::File& file, int only, juce::String& error)
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

std::vector<uint64_t> ViolinoProcessor::legacyHashes (const Phrase& p) const
{
    std::vector<uint64_t> out;
    for (int q = 0; q < 4; ++q)
        for (int tk : { juce::roundToInt (value ("takes")), 0 })
            for (int st : { 8, 15, 30, 4, 6, juce::roundToInt (value ("renderSteps")) })
                out.push_back (fnv (fnv (fnv (p.content, q), tk), st) | 1);
    return out;
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
    double first = 1e18, last = -1e18;
    auto use = [&] (size_t k) { return only < 0 || int (k) == only; };
    for (size_t k = 0; k < phrases.size(); ++k)
        if (auto& p = phrases[k]; ! use (k)) continue;
        else if (auto it = cache.find (p.hash); it != cache.end())
            first = std::min (first, p.origin), last = std::max (last, p.origin + it->second.audio.size() / 48000.0);
    if (last < first)
    {
        error = "Nothing rendered yet";
        return false;
    }
    const double tail = choice ("mixStyle") != 0 || flag ("reverb") ? 5.0 : 0.0;
    monoOut.assign (size_t ((last - first + tail) * 48000) + 1, 0.f);
    for (size_t k = 0; k < phrases.size(); ++k)
        if (auto& p = phrases[k]; ! use (k)) continue;
        else if (auto it = cache.find (p.hash); it != cache.end())
        {
            size_t at = size_t ((p.origin - first) * 48000);
            auto shaped = shapeDynamics (p, levelNotes (p, it->second.audio));
            applyVibrato (p, shaped);
            applyFade (p, shaped);
            for (size_t i = 0; i < shaped.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += shaped[i];
        }
    return true;
}

bool ViolinoProcessor::renderMixFile (std::vector<float> monoOut, const violino::MixSettings& ms, const juce::File& file, juce::String& error)
{
    MixFx offline;
    offline.prepare (48000);
    offline.set (ms);
    juce::AudioBuffer<float> buf (2, int (monoOut.size()));
    offline.process (monoOut.data(), buf.getWritePointer (0), buf.getWritePointer (1), int (monoOut.size()));
    file.deleteFile();
    juce::WavAudioFormat wav;
    std::unique_ptr<juce::OutputStream> os (file.createOutputStream().release());
    if (os == nullptr)
    {
        error = "Cannot write " + file.getFullPathName();
        return false;
    }
    std::unique_ptr<juce::AudioFormatWriter> w (wav.createWriterFor (os.get(), 48000, 2, 24, {}, 0));
    if (w == nullptr)
    {
        error = "Cannot create WAV writer";
        return false;
    }
    os.release();
    w->writeFromAudioSampleBuffer (buf, 0, buf.getNumSamples());
    return true;
}

// ------------------------------------------------------------------ estado
void ViolinoProcessor::getStateInformation (juce::MemoryBlock& dest)
{
    auto tree = params.copyState();
    juce::ValueTree capt ("Captured");
    for (auto& nt : notes)
    {
        juce::ValueTree v ("Note");
        v.setProperty ("s", nt.start, nullptr).setProperty ("e", nt.end, nullptr).setProperty ("p", nt.pitch, nullptr)
            .setProperty ("v", nt.vel, nullptr).setProperty ("f", int (nt.forced), nullptr).setProperty ("t", nt.take, nullptr);
        capt.appendChild (v, nullptr);
    }
    juce::String cc;
    for (auto& c : ccCurve) cc << juce::String (c.time, 4) << ":" << c.value << " ";
    capt.setProperty ("cc1", cc, nullptr);
    tree.appendChild (capt, nullptr);
    tree.setProperty ("prefs", juce::JSON::toString (uiPrefs, true), nullptr);
    if (auto xml = tree.createXml()) copyXmlToBinary (*xml, dest);
}

void ViolinoProcessor::setStateInformation (const void* data, int size)
{
    auto xml = getXmlFromBinary (data, size);
    if (xml == nullptr) return;
    auto tree = juce::ValueTree::fromXml (*xml);
    auto capt = tree.getChildWithName ("Captured");
    auto prefs = tree.getProperty ("prefs").toString();
    tree.removeChild (capt, nullptr);
    params.replaceState (tree);
    juce::MessageManager::callAsync ([this, capt, prefs] {
        notes.clear();
        for (auto v : capt)
            notes.push_back ({ double (v["s"]), double (v["e"]), int (v["p"]), int (v["v"]), Forced (int (v["f"])), 0, false, v["t"].toString() });
        if (prefs.isNotEmpty()) uiPrefs = juce::JSON::parse (prefs);
        ccCurve.clear();
        for (auto& tok : juce::StringArray::fromTokens (capt.getProperty ("cc1").toString(), " ", ""))
            if (tok.contains (":")) ccCurve.push_back ({ tok.upToFirstOccurrenceOf (":", false, false).getDoubleValue(), tok.fromFirstOccurrenceOf (":", false, false).getIntValue(), 0 });
        dirty = true;
    });
}

juce::AudioProcessorEditor* ViolinoProcessor::createEditor() { return new ViolinoEditor (*this); }

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter() { return new ViolinoProcessor(); }
