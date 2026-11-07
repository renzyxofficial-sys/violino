"""Bloco 2 / C++: ferramentas de nota, split de take, fade in por trecho, dinâmica desenhada,
portamento/legato manual com janela maior, trilo sempre junta (menos notas fixadas)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


a = open("engine/Articulator.cpp", encoding="utf-8").read()
# legato/portamento marcados à mão: ligam com a nota anterior se ela estiver a até 1 s (antes: 0,25 s)
a = rep(a, "        bool near = prev && n.start - prev->end < kFast;  // perto o bastante para ligar",
        "        bool near = prev && n.start - prev->end < (f == Forced::legato || f == Forced::portamento ? 1.0 : kFast);  // marcado à mão: liga até 1 s")
# trilo/trêmolo por extenso juntam sempre, exceto notas que o usuário fixou
a = rep(a, "        if (! a.user && a.dur() <= kTrillNote)", "        if (! a.user && a.forced == Forced::autoMode && a.dur() <= kTrillNote)")
a = rep(a, """        bool anyForced = std::any_of (voice.begin(), voice.end(), [] (auto& n) { return n.forced != Forced::autoMode; });
        auto notes = prepareForViolet (s.mode == ArticMode::manual || anyForced ? voice : collapseOrnaments (voice));""",
        """        auto notes = prepareForViolet (s.mode == ArticMode::manual ? voice : collapseOrnaments (voice));""")
open("engine/Articulator.cpp", "w", encoding="utf-8").write(a)

s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
# frase também quebra nos pontos de split do usuário
s = rep(s, """        if (phrases.empty() || notes[i].start - phrases.back().end >= kPhraseGap)""",
        """        const bool cut = ! phrases.empty() && std::any_of (splits.begin(), splits.end(), [&] (double t) { return t > phrases.back().start && t <= notes[i].start; });
        if (phrases.empty() || notes[i].start - phrases.back().end >= kPhraseGap || cut)""")
# curva alvo: a dinâmica desenhada pelo usuário manda onde existe
s = rep(s, """            p.target.push_back ({ t, v });""", """            if (! dynDrawn.empty() && t >= dynDrawn.front().first && t <= dynDrawn.back().first)
            {
                auto it = std::lower_bound (dynDrawn.begin(), dynDrawn.end(), std::pair<double, float> { t, -1.f });
                if (it != dynDrawn.end() && it != dynDrawn.begin() && it->first - (it - 1)->first < 0.5)  // dentro de um traço
                {
                    const auto& a0 = *(it - 1); const auto& a1 = *it;
                    v = a0.second + float ((t - a0.first) / std::max (1e-6, a1.first - a0.first)) * (a1.second - a0.second);
                }
            }
            p.target.push_back ({ t, v });""")
# fade in por trecho no clip e no export
s = rep(s, """            const auto shaped = shapeDynamics (p, it->second.audio);
            it->second.peaks = peaksOf (shaped);""", """            auto shaped = shapeDynamics (p, it->second.audio);
            applyFade (p, shaped);
            it->second.peaks = peaksOf (shaped);""")
s = rep(s, """            const auto shaped = shapeDynamics (p, it->second.audio);
            for (size_t i = 0; i < shaped.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += shaped[i];""",
        """            auto shaped = shapeDynamics (p, it->second.audio);
            applyFade (p, shaped);
            for (size_t i = 0; i < shaped.size() && at + i < monoOut.size(); ++i) monoOut[at + i] += shaped[i];""")
s = rep(s, """uint64_t ViolinoProcessor::dynKey (const Phrase& p) const
{""", """void ViolinoProcessor::applyFade (const Phrase& p, std::vector<float>& au) const
{
    auto it = fades.find (std::llround (p.start * 1000));
    if (it == fades.end() || it->second <= 0.001) return;
    const size_t a = size_t (std::max (0.0, p.start - 0.06 - p.origin) * 48000), n = size_t (it->second * 48000);
    for (size_t i = 0; i < a && i < au.size(); ++i) au[i] = 0;
    for (size_t i = 0; i < n && a + i < au.size(); ++i) au[a + i] *= float (std::pow (double (i) / double (n), 2.0));  // curva exponencial suave
}

uint64_t ViolinoProcessor::dynKey (const Phrase& p) const
{""")
s = rep(s, """    for (size_t k = 0; k < p.target.size(); k += 5) h = fnv (h, std::llround (p.target[k].second));
    return h;""", """    for (size_t k = 0; k < p.target.size(); k += 5) h = fnv (h, std::llround (p.target[k].second));
    if (auto it = fades.find (std::llround (p.start * 1000)); it != fades.end()) h = fnv (h, std::llround (it->second * 1000));
    return h;""")
# comandos
s = rep(s, """    else if (cmd == "dragAll")""", """    else if (cmd == "noteTool")
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
        if (k >= 0 && k < (int) phrases.size()) fades[std::llround (phrases[size_t (k)].start * 1000)] = juce::jlimit (0.0, 4.0, double (c["sec"]));
        rebuildClips();
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
    else if (cmd == "dragAll")""")
# estado: velocity e fade por frase para a UI
s = rep(s, """        cap.add (juce::Array<juce::var> { nt.start, nt.end, nt.pitch, int (nt.forced) });""",
        """        cap.add (juce::Array<juce::var> { nt.start, nt.end, nt.pitch, int (nt.forced), nt.vel });""")
s = rep(s, """        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks });""",
        """        auto fd = fades.find (std::llround (p.start * 1000));
        ph.add (juce::Array<juce::var> { p.start, p.end, state, prog, p.open, p.origin, peaks, fd == fades.end() ? 0.0 : fd->second });""")
s = rep(s, """        notes.clear(), openNote.clear(), renderedRegions.clear(), ccCurve.clear();""",
        """        notes.clear(), openNote.clear(), renderedRegions.clear(), ccCurve.clear(), splits.clear(), fades.clear(), dynDrawn.clear();""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::vector<CcPoint> ccCurve;  // CC1 capturado (Auto + Dynamics)",
        """    std::vector<CcPoint> ccCurve;  // CC1 capturado (Auto + Dynamics)
    std::vector<double> splits;    // pontos de split de take (o usuário corta uma frase em duas)
    std::map<long long, double> fades;  // fade in por frase (chave: início da frase em ms)
    std::vector<std::pair<double, float>> dynDrawn;  // dinâmica desenhada com o lápis (tempo, CC)
    void applyFade (const Phrase& p, std::vector<float>& audio48) const;""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)
print("ok")
