"""v0.5: dinâmica. Captura CC1; curva alvo por frase (CC1 no Auto + Dynamics, articulador no Auto);
o render segue a curva (ganho + brilho, quanto = Dynamics follow); o preview usa a mesma curva."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()

# parâmetro
s = rep(s, """    floatP ("legatoGap", "Legato Gap", 0, 60, 10, "ms");""", """    floatP ("legatoGap", "Legato Gap", 0, 60, 10, "ms");
    floatP ("dynFollow", "Dynamics Follow", 0, 100, 60, "%");""")

# CC1 vai para a captura
s = rep(s, """        else if (m.isController() && m.getControllerNumber() == 1)
            sampler.setModWheel (m.getControllerValue()), modWheel = m.getControllerValue();""",
"""        else if (m.isController() && m.getControllerNumber() == 1)
        {
            sampler.setModWheel (m.getControllerValue()), modWheel = m.getControllerValue();
            pushEvent ({ Event::cc, uint8_t (m.getControllerValue()), 0, false, isPlaying, t });
        }""")
s = rep(s, """            case Event::forced:
                setParam ("articulation", float (e.a));  // keyswitch = clicar no botão
                break;""", """            case Event::forced:
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
            }""")
s = rep(s, """            case Event::transportStart:
                ++pass, passActive = true, passHasNotes = false, passStart = e.time;""", """            case Event::transportStart:
                ++pass, passActive = true, passHasNotes = false, passStart = e.time, ccPassTime = -1;""")

# curva alvo de cada frase (em CC 0..127, tempos absolutos)
s = rep(s, """        p.art = articulate (in, as);""", """        p.art = articulate (in, as);
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
            p.target.push_back ({ t, v });
        }""")

# render segue a curva alvo: ganho + brilho
s = rep(s, """void ViolinoProcessor::rebuildClips()
{""", """std::vector<float> ViolinoProcessor::shapeDynamics (const Phrase& p, const std::vector<float>& audio) const
{
    const float amount = value ("dynFollow") / 100.f, intensity = value ("intensity") / 100.f;
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
{""")
s = rep(s, """        auto& clip = clipCache[p.hash];
        if (! clip || std::abs (clip->origin - p.origin) > 1e-6)
        {""", """        auto& clip = clipCache[p.hash];
        if (! clip || std::abs (clip->origin - p.origin) > 1e-6 || clip->dynKey != dynKey (p))
        {""")
s = rep(s, """            c->origin = p.origin, c->first = p.start, c->last = p.end;
            const double ratio = 48000.0 / sampleRate;
            c->audio.resize (size_t (double (it->second.audio.size()) / ratio));
            juce::LagrangeInterpolator interp;
            interp.process (ratio, it->second.audio.data(), c->audio.data(), int (c->audio.size()));""",
"""            c->origin = p.origin, c->first = p.start, c->last = p.end, c->dynKey = dynKey (p);
            const auto shaped = shapeDynamics (p, it->second.audio);
            it->second.peaks = peaksOf (shaped);
            const double ratio = 48000.0 / sampleRate;
            c->audio.resize (size_t (double (shaped.size()) / ratio));
            juce::LagrangeInterpolator interp;
            interp.process (ratio, shaped.data(), c->audio.data(), int (c->audio.size()));""")
s = rep(s, """    retired.push_back (clips.load());
    clips.store (next);""", """    // curvas das frases ainda sem render: o preview toca com a mesma dinâmica que o render vai ter
    auto dyn = std::make_shared<DynSet>();
    for (auto& p : phrases)
        if (! cache.count (p.hash) && ! p.target.empty())
            dyn->push_back (std::make_shared<const std::vector<std::pair<double, float>>> (p.target));
    retiredDyn.push_back (dynCurves.load());
    dynCurves.store (dyn);
    if (retiredDyn.size() > 8) retiredDyn.erase (retiredDyn.begin());
    retired.push_back (clips.load());
    clips.store (next);""")
s = rep(s, """juce::File ViolinoProcessor::cacheFile (uint64_t hash) const""", """uint64_t ViolinoProcessor::dynKey (const Phrase& p) const
{
    uint64_t h = fnv (fnv (1469598103934665603ull, std::llround (value ("dynFollow") * 10)), std::llround (value ("intensity") * 10));
    for (size_t k = 0; k < p.target.size(); k += 5) h = fnv (h, std::llround (p.target[k].second));
    return h;
}

juce::File ViolinoProcessor::cacheFile (uint64_t hash) const""")
# dynFollow/intensity mudando: reconstrói os clips (sem re-render)
s = rep(s, """    if (sh != settingsHash) settingsHash = sh, dirty = true;""", """    if (sh != settingsHash) settingsHash = sh, dirty = true;
    const uint64_t dk = fnv (fnv (7, std::llround (value ("dynFollow") * 10)), std::llround (value ("intensity") * 10));
    const bool dynChanged = dk != dynSettings;
    dynSettings = dk;""")
s = rep(s, """    if (clipsChanged) rebuildClips();""", """    if (clipsChanged || dynChanged) rebuildClips();""")
# preview: nota do DAW numa frase sem render toca com a dinâmica da curva
s = rep(s, """            if (! matched)
                sampler.noteOn (p < kMinPitch""", """            int vel = m.getVelocity();
            if (! matched && isPlaying && hasHost && choice ("articMode") == 0)
                if (auto d = dynCurves.load())
                    for (auto& curve : *d)
                        if (! curve->empty() && t >= curve->front().first && t <= curve->back().first)
                        {
                            auto it = std::upper_bound (curve->begin(), curve->end(), t, [] (double x, auto& c) { return x < c.first; });
                            const float cc = (it - 1)->second;
                            vel = juce::jlimit (1, 127, juce::roundToInt ((cc - 20.f) / 0.8f));  // inverso de 20 + 0.8 vel
                            break;
                        }
            if (! matched)
                sampler.noteOn (p < kMinPitch""")
s = rep(s, ", m.getVelocity(), liveT0 + at / sampleRate);", ", vel, liveT0 + at / sampleRate);")
# export usa o áudio com a dinâmica aplicada
s = rep(s, """            size_t at = size_t ((p.origin - first) * 48000);
            for (size_t i = 0; i < it->second.audio.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += it->second.audio[i];""",
"""            size_t at = size_t ((p.origin - first) * 48000);
            const auto shaped = shapeDynamics (p, it->second.audio);
            for (size_t i = 0; i < shaped.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += shaped[i];""")
# UI: curva da faixa Dynamics = curva alvo
s = rep(s, """        for (size_t i = 0; i < p.art.dynTimes.size(); i += 5)  // 10 Hz para a UI
            if (p.art.dynTimes[i] + p.origin >= p.start - 0.1 && p.art.dynTimes[i] + p.origin <= p.end + 0.3)
                dyn.add (juce::Array<juce::var> { p.art.dynTimes[i] + p.origin, p.art.dynValues[i] });""",
"""        for (size_t i = 0; i < p.target.size(); i += 5)  // 10 Hz para a UI
            if (p.target[i].first >= p.start - 0.1 && p.target[i].first <= p.end + 0.3)
                dyn.add (juce::Array<juce::var> { p.target[i].first, p.target[i].second });""")
# estado: salva o CC1 capturado
s = rep(s, """    tree.appendChild (capt, nullptr);""", """    juce::String cc;
    for (auto& c : ccCurve) cc << juce::String (c.time, 4) << ":" << c.value << " ";
    capt.setProperty ("cc1", cc, nullptr);
    tree.appendChild (capt, nullptr);""")
s = rep(s, """        if (prefs.isNotEmpty()) uiPrefs = juce::JSON::parse (prefs);""", """        if (prefs.isNotEmpty()) uiPrefs = juce::JSON::parse (prefs);
        ccCurve.clear();
        for (auto& tok : juce::StringArray::fromTokens (capt.getProperty ("cc1").toString(), " ", ""))
            if (tok.contains (":")) ccCurve.push_back ({ tok.upToFirstOccurrenceOf (":", false, false).getDoubleValue(), tok.fromFirstOccurrenceOf (":", false, false).getIntValue(), 0 });""")
s = rep(s, """        notes.clear(), openNote.clear(), renderedRegions.clear();""", """        notes.clear(), openNote.clear(), renderedRegions.clear(), ccCurve.clear();""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "        enum Type : uint8_t { noteOn, noteOff, forced, transportStart, transportStop } type;",
        "        enum Type : uint8_t { noteOn, noteOff, forced, transportStart, transportStop, cc } type;")
h = rep(h, "        std::vector<std::pair<double, int>> starts;  // (início, altura) das notas tocadas",
        "        std::vector<std::pair<double, int>> starts;  // (início, altura) das notas tocadas\n        std::vector<std::pair<double, float>> target; // dinâmica pedida (CC 0..127) a cada 20 ms, tempo absoluto")
h = rep(h, "        double origin = 0, first = 0, last = 0;\n        std::vector<float> audio;                 // na taxa do host",
        "        double origin = 0, first = 0, last = 0;\n        uint64_t dynKey = 0;\n        std::vector<float> audio;                 // na taxa do host (já com a dinâmica aplicada)")
h = rep(h, "    using ClipSet = std::vector<std::shared_ptr<const Clip>>;", """    using ClipSet = std::vector<std::shared_ptr<const Clip>>;
    using DynSet = std::vector<std::shared_ptr<const std::vector<std::pair<double, float>>>>;
    struct CcPoint
    {
        double time;
        int value, pass;
    };
    std::vector<float> shapeDynamics (const Phrase& p, const std::vector<float>& audio48) const;
    uint64_t dynKey (const Phrase& p) const;""")
h = rep(h, "    std::vector<std::shared_ptr<const ClipSet>> retired;  // libera fora da thread de áudio",
        """    std::vector<std::shared_ptr<const ClipSet>> retired;  // libera fora da thread de áudio
    std::atomic<std::shared_ptr<const DynSet>> dynCurves;
    std::vector<std::shared_ptr<const DynSet>> retiredDyn;
    std::vector<CcPoint> ccCurve;  // CC1 capturado (Auto + Dynamics)
    double ccPassTime = -1;
    uint64_t dynSettings = 0;""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)

a = open("ui/app.js", encoding="utf-8").read()
a = rep(a, """slider('portaVel', 'Portamento velocity', 3, '< ' + Math.round(P('portaVel').v)), slider('takes', 'Takes per phrase', 4, takesN ? String(takesN) : 'Auto')];""",
"""slider('portaVel', 'Portamento velocity', 3, '< ' + Math.round(P('portaVel').v)), slider('takes', 'Takes per phrase', 4, takesN ? String(takesN) : 'Auto'),
    slider('dynFollow', 'Dynamics follow', 5)];""")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
