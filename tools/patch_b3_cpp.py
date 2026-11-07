"""Bloco 3 / C++: velocity por nota (faixa de velocity e Alt/roda), curvatura do fade in (estilo FL)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
# curvatura: expoente 2^(2·tensão); 0,5 = o quadrático de antes
s = rep(s, """    const size_t a = size_t (std::max (0.0, p.start - 0.06 - p.origin) * 48000), n = size_t (it->second * 48000);
    for (size_t i = 0; i < a && i < au.size(); ++i) au[i] = 0;
    for (size_t i = 0; i < n && a + i < au.size(); ++i) au[a + i] *= float (std::pow (double (i) / double (n), 2.0));  // curva exponencial suave""",
        """    const size_t a = size_t (std::max (0.0, p.start - 0.06 - p.origin) * 48000), n = size_t (it->second * 48000);
    auto tn = fadeTension.find (it->first);
    const double ex = std::pow (2.0, 2.0 * (tn == fadeTension.end() ? 0.5 : tn->second));
    for (size_t i = 0; i < a && i < au.size(); ++i) au[i] = 0;
    for (size_t i = 0; i < n && a + i < au.size(); ++i) au[a + i] *= float (std::pow (double (i) / double (n), ex));""")
s = rep(s, """    if (auto it = fades.find (std::llround (p.start * 1000)); it != fades.end()) h = fnv (h, std::llround (it->second * 1000));""",
        """    if (auto it = fades.find (std::llround (p.start * 1000)); it != fades.end()) h = fnv (h, std::llround (it->second * 1000));
    if (auto it = fadeTension.find (std::llround (p.start * 1000)); it != fadeTension.end()) h = fnv (h, std::llround (it->second * 1000));""")
s = rep(s, """        if (k >= 0 && k < (int) phrases.size()) fades[std::llround (phrases[size_t (k)].start * 1000)] = juce::jlimit (0.0, 4.0, double (c["sec"]));
        rebuildClips();""", """        if (k >= 0 && k < (int) phrases.size())
        {
            const auto key = std::llround (phrases[size_t (k)].start * 1000);
            if (c.hasProperty ("sec")) fades[key] = juce::jlimit (0.0, 4.0, double (c["sec"]));
            if (c.hasProperty ("tension")) fadeTension[key] = juce::jlimit (-1.0, 1.0, double (c["tension"]));
        }
        rebuildClips();
    }
    else if (cmd == "noteVel")  // [[índice, velocity], ...]
    {
        if (auto* arr = c["vels"].getArray())
            for (auto& v : *arr)
            {
                const int i = int (v[0]);
                if (i >= 0 && i < (int) notes.size()) notes[size_t (i)].vel = juce::jlimit (1, 127, int (v[1]));
            }
        dirty = true;""")
s = rep(s, """        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks, fd == fades.end() ? 0.0 : fd->second });""",
        """        auto ft = fadeTension.find (std::llround (p.start * 1000));
        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks, fd == fades.end() ? 0.0 : fd->second,
                                         ft == fadeTension.end() ? 0.5 : ft->second });""")
s = rep(s, "splits.clear(), fades.clear(), dynDrawn.clear();", "splits.clear(), fades.clear(), fadeTension.clear(), dynDrawn.clear();")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::map<long long, double> fades;  // fade in por frase (chave: início da frase em ms)",
        """    std::map<long long, double> fades;  // fade in por frase (chave: início da frase em ms)
    std::map<long long, double> fadeTension;  // curvatura do fade (-1..1, 0,5 = quadrática)""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)
print("ok")
