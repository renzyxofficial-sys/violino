"""v0.5: preview com relógio próprio (bug do spiccato com o DAW parado), keyswitch x botão, Stop do render."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
# relógio do preview: nunca para (com o DAW parado o tempo do playhead congela e tudo parecia "rápido")
s = rep(s, "    internalClock += n / sampleRate;", "    const double liveT0 = liveClock;  // relógio do preview: sempre anda, mesmo com o DAW parado\n    liveClock += n / sampleRate;\n    internalClock += n / sampleRate;")
s = rep(s, "                sampler.noteOn (p < kMinPitch ? p + 12 * ((kMinPitch - p + 11) / 12) : p, m.getVelocity(), t);",
        "                sampler.noteOn (p < kMinPitch ? p + 12 * ((kMinPitch - p + 11) / 12) : p, m.getVelocity(), liveT0 + at / sampleRate);")
s = rep(s, "                sampler.noteOff (p < kMinPitch ? p + 12 * ((kMinPitch - p + 11) / 12) : p, t);",
        "                sampler.noteOff (p < kMinPitch ? p + 12 * ((kMinPitch - p + 11) / 12) : p, liveT0 + at / sampleRate);")
# keyswitch vale até o parâmetro chegar; se o usuário mudar o botão depois, o botão manda
s = rep(s, "    if (ksPending && paramForced == liveForced) ksPending = false;",
        "    if (ksPending && (paramForced == liveForced || paramForced != lastParamForced)) ksPending = false;\n    lastParamForced = paramForced;")
# Stop do render
s = rep(s, """    else if (cmd == "clear")
    {""", """    else if (cmd == "stopRender")
    {
        // para o que está na fila e o render em andamento; o Autorender não reenvia essas frases
        for (auto& p : phrases)
            if (! cache.count (p.hash)) stopped.insert (p.hash);
        engine->cancelOwner (this);
    }
    else if (cmd == "clear")
    {""")
s = rep(s, """        if (dirty) rebuildPhrases(), dirty = false;
        for (auto& p : phrases) submit (p);""", """        if (dirty) rebuildPhrases(), dirty = false;
        stopped.clear();
        for (auto& p : phrases) submit (p);""")
s = rep(s, """            if (! p.open && (! playing.load() || now > p.end + kPhraseGap || now < p.start - 0.5))
                submit (p);""", """            if (! p.open && ! stopped.count (p.hash) && (! playing.load() || now > p.end + kPhraseGap || now < p.start - 0.5))
                submit (p);""")
s = rep(s, """    o->setProperty ("rendered", rendered);""", """    o->setProperty ("rendered", rendered);
    bool busy = false;
    for (auto& p : phrases) busy = busy || (! cache.count (p.hash) && engine->isQueued (p.hash));
    o->setProperty ("busy", busy);""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    bool ksPending = false;", "    bool ksPending = false;\n    violino::Forced lastParamForced = violino::Forced::autoMode;\n    double liveClock = 0;\n    std::set<uint64_t> stopped;  // frases paradas pelo usuário (Stop): o Autorender não reenvia")
h = rep(h, "#include <map>", "#include <map>\n#include <set>")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)

# UI: Render vira Stop enquanto renderiza
a = open("ui/app.js", encoding="utf-8").read()
a = rep(a, "    doRender: () => send({ cmd: 'render' }),", "    doRender: () => send({ cmd: S && S.busy ? 'stopRender' : 'render' }), renderLabel: S && S.busy ? '■ Stop' : 'Render',\n    renderBg: S && S.busy ? t.rec : t.accent,")
open("ui/app.js", "w", encoding="utf-8").write(a)
b = open("ui/build_ui.py", encoding="utf-8").read()
b = rep(b, """sub('<button style="height: 40px; padding: 0 22px; border: 0; border-radius: 20px; background: {{t.accent}};',
    '<button onClick="{{doRender}}" style="height: 40px; padding: 0 22px; border: 0; border-radius: 20px; background: {{t.accent}};')""",
"""sub('<button style="height: 40px; padding: 0 22px; border: 0; border-radius: 20px; background: {{t.accent}};',
    '<button onClick="{{doRender}}" style="height: 40px; padding: 0 22px; border: 0; border-radius: 20px; background: {{renderBg}};')
sub('font-size: 13px; font-weight: 600; cursor: pointer;">Render</button>', 'font-size: 13px; font-weight: 600; cursor: pointer; min-width: 92px;">{{renderLabel}}</button>')""")
open("ui/build_ui.py", "w", encoding="utf-8").write(b)
print("ok")
