"""Bloco 6 / C++: Play do Standalone roda livre (grava na posição da timeline), Play de novo = pausa, Cycle."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")
def rep(s, old, new, n=1):
    c = s.count(old); assert c == n, (c, old[:70]); return s.replace(old, new)
h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    std::atomic<bool> metroOn { false };", """    std::atomic<bool> metroOn { false };
    std::atomic<bool> cycleOn { false };          // Cycle: o Play interno volta de cycleB para cycleA
    std::atomic<double> cycleA { 0 }, cycleB { 0 };""")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)
s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """    if (! hasHost)
        isPlaying = true;
    const double liveT0 = liveClock;""", """    if (! hasHost)
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
    const double liveT0 = liveClock;""")
s = rep(s, """        if (tp > lastEnd) timelinePlay = false;""", """        if (tp > lastEnd && wrapperType != wrapperType_Standalone && ! cycleOn.load()) timelinePlay = false;  // no Standalone roda livre (para gravar)""")
s = rep(s, """        if (timelinePlay.load()) { timelinePlay = false; timelinePos = playStart; return; }  // parar volta para onde o play começou
        if (first > 1e17) return;  // nada capturado ainda
        if (timelinePos.load() >= last - 0.05 || timelinePos.load() < first - 30) timelinePos = first;""",
"""        if (timelinePlay.load()) { timelinePlay = false; return; }  // Play (ou Espaço) de novo = pausa; continua dali
        if (wrapperType != wrapperType_Standalone)  // no plugin, só tem sentido onde há o que tocar
        {
            if (first > 1e17) return;
            if (timelinePos.load() >= last - 0.05 || timelinePos.load() < first - 30) timelinePos = first;
        }
        if (cycleOn.load() && cycleB.load() > cycleA.load() + 0.05 && (timelinePos.load() < cycleA.load() || timelinePos.load() >= cycleB.load()))
            timelinePos = cycleA.load();""")
s = rep(s, """    if (cmd == "metro") {""", """    if (cmd == "cycle")  // {on, a, b}: liga/desliga e (opcional) o trecho
    {
        if (c.hasProperty ("a") && c.hasProperty ("b") && double (c["b"]) > double (c["a"]) + 0.05)
            cycleA = std::max (0.0, double (c["a"])), cycleB = double (c["b"]);
        if (c.hasProperty ("on")) cycleOn = bool (c["on"]);
        return;
    }
    if (cmd == "metro") {""")
s = rep(s, """    o->setProperty ("metro", metroOn.load());""", """    o->setProperty ("metro", metroOn.load());
    o->setProperty ("cycle", juce::Array<juce::var> { cycleOn.load(), cycleA.load(), cycleB.load() });""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
print("ok")
