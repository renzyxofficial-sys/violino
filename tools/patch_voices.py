"""Poly Legato / Long Normal: uma render do VIOLET por voz, somadas (o modelo toca uma linha por vez)."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\source")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


s = open("PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, """        // uma linha por voz para o VIOLET (Poly Legato / Long Normal renderizam as vozes juntas)
        p.vnotes.clear();
        for (int v = 0; v < 2; ++v)
        {
            std::vector<ArtNote> voice;
            for (auto& a : p.art.notes) if (a.voice == v) voice.push_back (a);
            auto vn = toViolet (voice, as.play == PlayMode::longNormal ? -1.0 : as.legatoGap);
            p.vnotes.insert (p.vnotes.end(), vn.begin(), vn.end());
        }
        std::sort (p.vnotes.begin(), p.vnotes.end(), [] (auto& a, auto& b) { return a.start < b.start; });""",
"""        // uma linha por voz: o VIOLET toca uma nota por vez, então cordas duplas viram duas renders somadas
        p.voices.clear();
        for (int v = 0; v < 2; ++v)
        {
            std::vector<ArtNote> voice;
            for (auto& a : p.art.notes) if (a.voice == v) voice.push_back (a);
            if (! voice.empty())
                p.voices.push_back (toViolet (voice, as.play == PlayMode::longNormal ? -1.0 : as.legatoGap));
        }""")
s = rep(s, """        for (auto& v : p.vnotes)
            h = fnv (fnv (fnv (fnv (h, std::llround (v.start * 1000)), std::llround (v.end * 1000)), v.pitch), v.tech);""",
"""        for (auto& voice : p.voices)
        {
            h = fnv (h, 7777);
            for (auto& v : voice)
                h = fnv (fnv (fnv (fnv (h, std::llround (v.start * 1000)), std::llround (v.end * 1000)), v.pitch), v.tech);
        }""")
s = rep(s, "    if (p.vnotes.empty() || cache.count (p.hash) || engine->isQueued (p.hash))",
        "    if (p.voices.empty() || cache.count (p.hash) || engine->isQueued (p.hash))")
s = rep(s, "    job.id = p.hash, job.owner = this, job.notes = p.vnotes;", "    job.id = p.hash, job.owner = this, job.voices = p.voices;")
open("PluginProcessor.cpp", "w", encoding="utf-8").write(s)

h = open("PluginProcessor.h", encoding="utf-8").read()
h = rep(h, "        std::vector<violino::VNote> vnotes;", "        std::vector<std::vector<violino::VNote>> voices;  // 1 (Legato) ou 2 (cordas duplas)")
open("PluginProcessor.h", "w", encoding="utf-8").write(h)

eh = open("EngineService.h", encoding="utf-8").read()
eh = rep(eh, "        std::vector<violino::VNote> notes;", "        std::vector<std::vector<violino::VNote>> voices;  // renderizadas separadas e somadas")
open("EngineService.h", "w", encoding="utf-8").write(eh)

ec = open("EngineService.cpp", encoding="utf-8").read()
ec = rep(ec, """            r.take = performer.perform (job.notes, job.quality, job.fastShare, 1234 + job.id % 100000,
                                        [this, id = job.id] (float f) { progress = f; return cancelId != id && ! threadShouldExit(); },
                                        job.takes);
            if (r.take.audio.empty())
                r.error = "cancelled";""", """            const float nv = float (std::max<size_t> (1, job.voices.size()));
            for (size_t v = 0; v < job.voices.size() && r.error.isEmpty(); ++v)
            {
                auto take = performer.perform (job.voices[v], job.quality, job.fastShare, 1234 + job.id % 100000 + v * 104729,
                                               [this, id = job.id, v, nv] (float f) { progress = (float (v) + f) / nv; return cancelId != id && ! threadShouldExit(); },
                                               job.takes);
                if (take.audio.empty())
                {
                    r.error = "cancelled";
                    break;
                }
                if (v == 0)
                    r.take = std::move (take);
                else
                {
                    // soma a segunda voz (cordas duplas), com um pouco menos de ganho para não estourar
                    r.take.audio.resize (std::max (r.take.audio.size(), take.audio.size()), 0.0f);
                    for (size_t i = 0; i < take.audio.size(); ++i) r.take.audio[i] = 0.8f * (r.take.audio[i] + take.audio[i]);
                    for (size_t i = take.audio.size(); i < r.take.audio.size(); ++i) r.take.audio[i] *= 0.8f;
                    r.take.accuracy = 0.5 * (r.take.accuracy + take.accuracy);
                }
            }""")
open("EngineService.cpp", "w", encoding="utf-8").write(ec)
print("ok")
