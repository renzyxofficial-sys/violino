"""Render identificado só por notas/articulação (qualidade não derruba renders prontos); steps 4..15,
Low 4 · Medium 6 · High 8 (padrão) · Extreme 15 (+8 takes)."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")
def rep(s, old, new, n=1):
    c = s.count(old); assert c == n, (c, old[:70]); return s.replace(old, new)
h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "        uint64_t hash = 0;\n", "        uint64_t hash = 0, content = 0;  // content: só notas/técnicas (antes a qualidade entrava no hash)\n")
h = rep(h, "    void restore (EditSnap s);", "    void restore (EditSnap s);\n    std::vector<uint64_t> legacyHashes (const Phrase& p) const;  // nomes antigos (com qualidade/steps) do mesmo render")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)
s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """        p.hash = fnv (fnv (fnv (h, quality), takes), juce::roundToInt (value ("renderSteps"))) | 1;""",
        """        p.content = h;
        p.hash = fnv (h, 0x5157) | 1;  // trocar a qualidade vale para os próximos renders; os prontos continuam valendo
        juce::ignoreUnused (quality, takes);""")
s = rep(s, """        if (! cache.count (p.hash))
        {
            auto f = cacheFile (p.hash);  // render de uma sessão anterior""", """        if (! cache.count (p.hash))  // render feito antes desta versão: estava guardado com a qualidade no nome
            for (auto old : legacyHashes (p))
            {
                if (auto it = cache.find (old); it != cache.end()) { cache[p.hash] = it->second; clipsChanged = true; break; }
                if (auto of = cacheFile (old); of.existsAsFile()) { of.copyFileTo (cacheFile (p.hash)); break; }
            }
        if (! cache.count (p.hash))
        {
            auto f = cacheFile (p.hash);  // render de uma sessão anterior""")
s = rep(s, """void ViolinoProcessor::restore (EditSnap s0)""", """std::vector<uint64_t> ViolinoProcessor::legacyHashes (const Phrase& p) const
{
    std::vector<uint64_t> out;
    for (int q = 0; q < 4; ++q)
        for (int tk : { juce::roundToInt (value ("takes")), 0 })
            for (int st : { 8, 15, 30, 4, 6, juce::roundToInt (value ("renderSteps")) })
                out.push_back (fnv (fnv (fnv (p.content, q), tk), st) | 1);
    return out;
}

void ViolinoProcessor::restore (EditSnap s0)""")
# refazer/remover render também apaga os nomes antigos (senão o antigo voltaria sozinho)
s = rep(s, """            cache.erase (p.hash), clipCache.erase (p.hash), renderedRegions.erase (p.hash);
            cacheFile (p.hash).deleteFile();""", """            cache.erase (p.hash), clipCache.erase (p.hash), renderedRegions.erase (p.hash);
            cacheFile (p.hash).deleteFile();
            for (auto old : legacyHashes (p)) cache.erase (old), cacheFile (old).deleteFile();""")
s = rep(s, """    l.add (std::make_unique<AudioParameterInt> (ParameterID { "renderSteps", 1 }, "Render Steps", 1, 50, 30));""",
        """    l.add (std::make_unique<AudioParameterInt> (ParameterID { "renderSteps", 1 }, "Render Steps", 4, 15, 8));""")
s = rep(s, "// Low 8 · Medium 15 · High 30 · Extreme 30 (+ 8 takes)", "// Low 4 · Medium 6 · High 8 · Extreme 15 (+ 8 takes)")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
pf = open("engine/Performer.cpp", encoding="utf-8").read()
pf = rep(pf, """        case Quality::low: return { 8, 0 };
        case Quality::medium: return { 15, 0 };
        case Quality::high: return { 30, 0 };
        case Quality::extreme: return { 30, 8 };""", """        case Quality::low: return { 4, 0 };
        case Quality::medium: return { 6, 0 };
        case Quality::high: return { 8, 0 };
        case Quality::extreme: return { 15, 8 };""")
open("engine/Performer.cpp", "w", encoding="utf-8").write(pf)
a = open("ui/app.js", encoding="utf-8").read()
a = rep(a, "const qInfo = [['Low', 'Fastest drafts · 8 steps'], ['Med', 'Quick and clean · 15 steps'], ['High', 'Default · 30 steps'], ['Extreme', 'Best of 8 takes · slowest']];",
        "const qInfo = [['Low', 'Fastest drafts · 4 steps'], ['Med', 'Quick · 6 steps'], ['High', 'Default · 8 steps'], ['Extreme', 'Best of 8 takes · 15 steps']];")
open("ui/app.js", "w", encoding="utf-8").write(a)
print("ok")
