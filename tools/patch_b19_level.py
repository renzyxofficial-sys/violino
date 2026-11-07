"""Nivelamento por nota: o VIOLET faz sustain/legato mais baixo que ataques curtos; antes de seguir a curva de
dinâmica, cada nota é aproximada da mediana da frase (Even out, padrão 70%)."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")


def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == n_count(a, o), (p, a.count(o), o[:70])
        a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)


def n_count(a, o):
    return a.count(o) if a.count(o) >= 1 else -1


h = open("source/PluginProcessor.h", encoding="utf-8").read()
o = "    void applyVibrato (const Phrase& p, std::vector<float>& audio48) const;  // vibrato extra nas notas longas"
assert h.count(o) == 1
h = h.replace(o, o + "\n    std::vector<float> levelNotes (const Phrase& p, const std::vector<float>& audio48) const;  // nota a nota perto da mediana")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)

s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
o = """    floatP ("vibAmount", "Vibrato", 0, 100, 0, "%");"""
assert s.count(o) == 1
s = s.replace(o, o + """
    floatP ("evenOut", "Even Out", 0, 100, 70, "%");  // nivela notas longas (mais baixas no VIOLET) com os ataques""")
o = """            auto shaped = shapeDynamics (p, it->second.audio);"""
assert s.count(o) == 2
s = s.replace(o, """            auto shaped = shapeDynamics (p, levelNotes (p, it->second.audio));""")
o = """    h = fnv (fnv (fnv (h, std::llround (value ("vibAmount") * 10)), std::llround (value ("vibRate") * 100)), choice ("playStyle"));"""
assert s.count(o) == 1
s = s.replace(o, o + """
    h = fnv (h, std::llround (value ("evenOut") * 10));""")
o = """    const uint64_t dk = fnv (fnv (fnv (fnv (7,"""
assert s.count(o) == 1
s = s.replace(o, """    const uint64_t dk = fnv (std::llround (value ("evenOut") * 10), 0) ^ fnv (fnv (fnv (fnv (7,""")
o = """std::vector<float> ViolinoProcessor::shapeDynamics (const Phrase& p, const std::vector<float>& audio) const
{"""
assert s.count(o) == 1
s = s.replace(o, """std::vector<float> ViolinoProcessor::levelNotes (const Phrase& p, const std::vector<float>& audio) const
{
    const float even = value ("evenOut") / 100.f;
    if (even <= 0.001f || p.art.notes.size() < 2 || audio.size() < 4800) return audio;
    // trechos de cada nota (do ataque até o próximo ataque), em amostras desde a origem do render
    std::vector<double> on;
    for (auto& a : p.art.notes) on.push_back (a.start);
    std::sort (on.begin(), on.end());
    on.erase (std::unique (on.begin(), on.end(), [] (double x, double y) { return std::abs (x - y) < 0.03; }), on.end());
    const double sr = 48000;
    std::vector<float> segDb (on.size(), -200.f);
    for (size_t k = 0; k < on.size(); ++k)
    {
        const size_t a = size_t (std::max (0.0, on[k] * sr)), b = std::min (audio.size(), size_t ((k + 1 < on.size() ? on[k + 1] : on[k] + 1.5) * sr));
        if (b <= a + 480) continue;
        double e = 0;
        for (size_t i = a; i < b; ++i) e += double (audio[i]) * audio[i];
        segDb[k] = float (10 * std::log10 (e / double (b - a) + 1e-12));
    }
    std::vector<float> ok;
    for (auto d : segDb) if (d > -60) ok.push_back (d);
    if (ok.size() < 2) return audio;
    std::nth_element (ok.begin(), ok.begin() + long (ok.size() / 2), ok.end());
    const float med = ok[ok.size() / 2];
    // ganho por nota (sobe até +9 dB, desce até -6 dB) e transição de 60 ms entre notas
    std::vector<float> gain (on.size(), 1.f);
    for (size_t k = 0; k < on.size(); ++k)
        if (segDb[k] > -60) gain[k] = std::pow (10.f, std::clamp ((med - segDb[k]) * even, -6.f, 9.f) / 20.f);
    std::vector<float> out (audio.size());
    const double fade = 0.06 * sr;
    size_t k = 0;
    for (size_t i = 0; i < audio.size(); ++i)
    {
        while (k + 1 < on.size() && i >= size_t (on[k + 1] * sr)) ++k;
        float g = gain[k];
        if (k > 0)  // logo depois do ataque: sai do ganho da nota anterior
        {
            const double into = double (i) - on[k] * sr;
            if (into < fade) g = gain[k - 1] + float (std::max (0.0, into) / fade) * (gain[k] - gain[k - 1]);
        }
        if (i < size_t (on[0] * sr)) g = gain[0];
        out[i] = audio[i] * g;
    }
    return out;
}

std::vector<float> ViolinoProcessor::shapeDynamics (const Phrase& p, const std::vector<float>& audio) const
{""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

a = open("ui/app.js", encoding="utf-8").read()
o = "    slider('modelDyn', 'Model dynamics (CC1, experimental)', 8, P('modelDyn').v > 0.5 ? 'On' : 'Off')];"
assert a.count(o) == 1
a = a.replace(o, "    slider('evenOut', 'Even out (long notes vs attacks)', 8), slider('modelDyn', 'Model dynamics (CC1, experimental)', 9, P('modelDyn').v > 0.5 ? 'On' : 'Off')];")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
