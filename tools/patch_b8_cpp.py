"""Bloco 8 / C++: Playstyle (macro de articulação/dinâmica) e Vibrato extra sobre o render."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")
def rep(s, old, new, n=1):
    c = s.count(old); assert c == n, (c, old[:70]); return s.replace(old, new)
h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    void applyFade (const Phrase& p, std::vector<float>& audio48) const;", """    void applyFade (const Phrase& p, std::vector<float>& audio48) const;
    void applyVibrato (const Phrase& p, std::vector<float>& audio48) const;  // vibrato extra nas notas longas
    double styleVibrato() const;    // quanto o Playstyle soma ao vibrato (%)
    float styleIntensity() const;   // quanto o Playstyle escala a dinâmica""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)
s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """const juce::StringArray kPlayModes { "Legato", "Shorts" };""", """const juce::StringArray kPlayModes { "Legato", "Shorts" };
const juce::StringArray kPlayStyles { "Natural", "Lyrical", "Romantic", "Classical", "Baroque", "Cinematic" };""")
s = rep(s, """    floatP ("intensity", "Dynamics Intensity", 0, 100, 70, "%");""", """    floatP ("intensity", "Dynamics Intensity", 0, 100, 70, "%");
    choiceP ("playStyle", "Playstyle", kPlayStyles, 0);
    floatP ("vibAmount", "Vibrato", 0, 100, 0, "%");
    floatP ("vibRate", "Vibrato Rate", 4, 7.5f, 5.5f, "Hz");""")
# Playstyle muda como as notas são ligadas (legato / portamento) antes do render
s = rep(s, """    s.legatoGap = value ("legatoGap") / 1000.0;
    return s;""", """    s.legatoGap = value ("legatoGap") / 1000.0;
    switch (choice ("playStyle"))
    {
        case 1: s.legatoGap = std::max (s.legatoGap, 0.03), s.portaVelocity = std::min (127, s.portaVelocity + 10); break;  // Lyrical: cantado
        case 2: s.legatoGap = std::max (s.legatoGap, 0.045), s.portaVelocity = std::min (127, s.portaVelocity + 25); break; // Romantic: liga e desliza mais
        case 3: s.legatoGap = std::min (s.legatoGap, 0.01), s.portaVelocity = std::max (1, s.portaVelocity - 15); break;    // Classical: mais limpo
        case 4: s.legatoGap = 0.0, s.portaVelocity = 1; break;                                                               // Baroque: destacado, sem portamento
        case 5: s.legatoGap = std::max (s.legatoGap, 0.05); break;                                                           // Cinematic: tudo ligado
        default: break;
    }
    return s;""")
s = rep(s, """    for (auto* id : { "playMode", "shortsMode", "articMode", "quality", "legatoGap", "portaVel", "takes", "renderSteps" })""",
        """    for (auto* id : { "playMode", "shortsMode", "articMode", "quality", "legatoGap", "portaVel", "takes", "renderSteps", "playStyle" })""")
s = rep(s, """    const float amount = value ("dynFollow") / 100.f, intensity = value ("intensity") / 100.f;
    if (amount <= 0.001f""", """    const float amount = value ("dynFollow") / 100.f, intensity = value ("intensity") / 100.f * styleIntensity();
    if (amount <= 0.001f""")
s = rep(s, """    if (auto it = fadeTension.find (std::llround (p.start * 1000)); it != fadeTension.end()) h = fnv (h, std::llround (it->second * 1000));
    return h;
}""", """    if (auto it = fadeTension.find (std::llround (p.start * 1000)); it != fadeTension.end()) h = fnv (h, std::llround (it->second * 1000));
    h = fnv (fnv (fnv (h, std::llround (value ("vibAmount") * 10)), std::llround (value ("vibRate") * 100)), choice ("playStyle"));
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
}""")
s = rep(s, """            auto shaped = shapeDynamics (p, it->second.audio);""", """            auto shaped = shapeDynamics (p, it->second.audio);
            applyVibrato (p, shaped);""", 2)
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
print("ok")
