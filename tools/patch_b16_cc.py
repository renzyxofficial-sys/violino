"""CC1 no VIOLET: a curva de dinâmica entra como condicionamento do modelo (como no treino e na avaliação dos autores),
em vez de só subir/baixar o volume depois. Parâmetro "modelDyn" (ligado por padrão)."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")


def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)


patch('engine/VioletRenderer.h', [(
    """    std::vector<float> render (const std::vector<VNote>& notes, int steps, uint64_t seed,
                               const std::function<bool (float)>& progress);""",
    """    // cc25: CC1 (0..1) a 25 Hz desde o início do render; vazio = sem condicionamento de dinâmica
    std::vector<float> render (const std::vector<VNote>& notes, int steps, uint64_t seed,
                               const std::function<bool (float)>& progress, const std::vector<float>& cc25 = {});""")])
patch('engine/VioletRenderer.cpp', [
    ("    void runCond (bool techPresent)", "    void runCond (bool techPresent, bool ccPresent)"),
    ("        float techKeep = techPresent ? 1.0f : 0.0f, ccKeep = 0.0f;  // w_tech = 1, w_cc = 0",
     "        float techKeep = techPresent ? 1.0f : 0.0f, ccKeep = ccPresent ? 1.0f : 0.0f;  // w_tech = 1; CC1 quando há curva"),
    ("""std::vector<float> VioletRenderer::render (const std::vector<VNote>& notes, int steps, uint64_t seed,
                                           const std::function<bool (float)>& progress)""",
     """std::vector<float> VioletRenderer::render (const std::vector<VNote>& notes, int steps, uint64_t seed,
                                           const std::function<bool (float)>& progress, const std::vector<float>& cc25)"""),
    ("        m.runCond (techPresent);", """        if (! cc25.empty())  // a fatia da curva de dinâmica desta janela (mesma taxa dos quadros: 25 Hz)
            for (int f = 0; f < kFrames; ++f)
                m.ccTokens[size_t (f)] = cc25[size_t (std::min (positions[w] + f, int (cc25.size()) - 1))];
        m.runCond (techPresent, ! cc25.empty());"""),
])
patch('engine/Performer.h', [(
    """                  const std::function<bool (float)>& progress, int takesOverride = 0, int stepsOverride = 0);""",
    """                  const std::function<bool (float)>& progress, int takesOverride = 0, int stepsOverride = 0,
                  const std::vector<float>& cc25 = {});""")])
patch('engine/Performer.cpp', [
    ("""                         const std::function<bool (float)>& progress, int takesOverride, int stepsOverride)""",
     """                         const std::function<bool (float)>& progress, int takesOverride, int stepsOverride,
                         const std::vector<float>& cc25)"""),
    ("        auto audio = renderer.render (notes, info.steps, seed + uint64_t (k) * 7919, sub);",
     "        auto audio = renderer.render (notes, info.steps, seed + uint64_t (k) * 7919, sub, cc25);"),
])
patch('source/EngineService.h', [("        int steps = 0;  // 0 = o do nível de qualidade",
                                  "        int steps = 0;  // 0 = o do nível de qualidade\n        std::vector<float> cc25;  // dinâmica para o modelo (CC1 0..1, 25 Hz)")])
patch('source/EngineService.cpp', [("                                               job.takes, job.steps);",
                                    "                                               job.takes, job.steps, job.cc25);")])
patch('source/PluginProcessor.cpp', [
    ("""    choiceP ("playStyle", "Playstyle", kPlayStyles, 0);""",
     """    choiceP ("playStyle", "Playstyle", kPlayStyles, 0);
    boolP ("modelDyn", "Model Dynamics", true);  // a curva de dinâmica vai para o VIOLET (CC1)"""),
    ("""    job.steps = juce::roundToInt (value ("renderSteps"));""",
     """    job.steps = juce::roundToInt (value ("renderSteps"));
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
    }"""),
])
print('ok')
