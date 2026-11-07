"""Modo Auto: todas as notas em Auto (ignora articulação marcada, keyswitch e Shorts). Auto + Dynamics e Manual: como antes."""
import os
os.chdir(r"C:\Users\TheoH\violino\plugin")


def patch(p, pairs):
    a = open(p, encoding='utf-8').read()
    for o, n in pairs:
        assert a.count(o) == 1, (p, a.count(o), o[:70]); a = a.replace(o, n)
    open(p, 'w', encoding='utf-8').write(a)


patch('source/PluginProcessor.cpp', [
    ("""                            notes[i].forced == Forced::autoMode && choice ("playMode") == 1 ? kShortForced[juce::jlimit (0, 2, choice ("shortsMode"))] : notes[i].forced });""",
     """                            choice ("articMode") == 0 ? Forced::autoMode  // modo Auto: o algoritmo decide tudo (a marcação fica guardada para os outros modos)
                            : notes[i].forced == Forced::autoMode && choice ("playMode") == 1 ? kShortForced[juce::jlimit (0, 2, choice ("shortsMode"))] : notes[i].forced });"""),
    ("""    live.forced = ksPending ? liveForced : paramForced;
    if (shorts && live.forced == Forced::autoMode) live.forced = kShortForced[juce::jlimit (0, 2, choice ("shortsMode"))];""",
     """    live.forced = ksPending ? liveForced : paramForced;
    if (shorts && live.forced == Forced::autoMode) live.forced = kShortForced[juce::jlimit (0, 2, choice ("shortsMode"))];
    const bool allAuto = choice ("articMode") == 0;
    if (allAuto) live.forced = Forced::autoMode;  // modo Auto: o preview também decide sozinho"""),
    ("""                    if (q.forced != Forced::autoMode) { auto l2 = live; l2.forced = q.forced; sampler.setLive (l2); }  // a articulação marcada na nota""",
     """                    if (q.forced != Forced::autoMode && ! allAuto) { auto l2 = live; l2.forced = q.forced; sampler.setLive (l2); }  // a articulação marcada na nota"""),
    ("""                    if (q.forced != Forced::autoMode) sampler.setLive (live);""",
     """                    if (q.forced != Forced::autoMode && ! allAuto) sampler.setLive (live);"""),
])
patch('ui/app.js', [
    ("const an = artAt(c[0], c[2]), forced = c[3] > 0 ? ART_IDS[c[3]] : null, art = forced || (an ? an[3] : 'auto');",
     "const an = artAt(c[0], c[2]), forced = c[3] > 0 && am !== 0 ? ART_IDS[c[3]] : null, art = forced || (an ? an[3] : 'auto');  // modo Auto: tudo automático"),
])
print('ok')
