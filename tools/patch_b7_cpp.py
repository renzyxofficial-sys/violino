"""Bloco 7 / C++: Play do Standalone não corta a nota que o usuário segura (era o 'só staccato')."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")
def rep(s, old, new, n=1):
    c = s.count(old); assert c == n, (c, old[:70]); return s.replace(old, new)
h = open("source/PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "    struct PNote { double start, end; int pitch, vel; };", "    struct PNote { double start, end; int pitch, vel; violino::Forced forced; };")
open("source/PluginProcessor.h", "w", encoding="utf-8").write(h)
s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """                    if (i < notes.size()) pv->push_back ({ notes[i].start, notes[i].end, notes[i].pitch, notes[i].vel });""",
        """                    if (i < notes.size() && ! notes[i].open)  // a nota ainda segurada não entra (o fim dela não existe ainda)
                        pv->push_back ({ notes[i].start, notes[i].end, notes[i].pitch, notes[i].vel, notes[i].forced });""")
s = rep(s, """                if (q.start >= tlStart && q.start < te) sampler.noteOn (pp, q.vel, liveT0 + (q.start - tlStart));
                if (q.end >= tlStart && q.end < te) sampler.noteOff (pp, liveT0 + (q.end - tlStart));""",
        """                const bool held = pressed[size_t (q.pitch / 64)].load() & (1ull << (q.pitch % 64));  // o usuário está tocando essa tecla
                if (q.start >= tlStart && q.start < te && ! held)
                {
                    if (q.forced != Forced::autoMode) { auto l2 = live; l2.forced = q.forced; sampler.setLive (l2); }  // a articulação marcada na nota
                    sampler.noteOn (pp, q.vel, liveT0 + (q.start - tlStart));
                    if (q.forced != Forced::autoMode) sampler.setLive (live);
                }
                if (q.end >= tlStart && q.end < te && ! held) sampler.noteOff (pp, liveT0 + (q.end - tlStart));""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
print("ok")
