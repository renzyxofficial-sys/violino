#include "Articulator.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <set>

namespace violino
{
namespace
{
constexpr double kPi = 3.14159265358979323846;

const char* kNames[] = { "none", "sustain", "tremolo", "trill_major", "trill_minor", "staccato", "spiccato",
                         "ricochet", "pizzicato", "harmonic", "legato_bow", "legato_slur", "legato_portamento" };

std::string fmt (const char* f, double a, double b = 0)
{
    char buf[128];
    std::snprintf (buf, sizeof buf, f, a, b);
    return buf;
}

// Separa em vozes (até 2): acorde -> voz de cima e de baixo; nota seguinte vai para a voz mais
// próxima em altura que já está livre.
std::vector<std::vector<ArtNote>> splitVoices (std::vector<ArtNote> notes, bool mono)
{
    std::sort (notes.begin(), notes.end(), [] (auto& a, auto& b) { return a.start != b.start ? a.start < b.start : a.pitch > b.pitch; });
    std::vector<std::vector<ArtNote>> voices (mono ? 1 : 2);
    double chordStart = -1;
    int inChord = 0;
    for (auto& n : notes)
    {
        if (mono)
        {
            auto& v = voices[0];
            if (! v.empty() && n.start - v.back().start < 0.03)
                continue;  // acorde: mantém a nota mais aguda
            v.push_back (n);
            continue;
        }
        if (chordStart >= 0 && n.start - chordStart < 0.03)
        {
            if (++inChord >= 2)
                continue;  // no máximo cordas duplas
            n.voice = 1;
            voices[1].push_back (n);
            continue;
        }
        chordStart = n.start;
        inChord = 0;
        int best = 0;
        double bestCost = 1e9;
        for (int k = 0; k < 2; ++k)
        {
            double cost = voices[k].empty() ? 50.0 : std::abs (n.pitch - voices[k].back().pitch);
            if (! voices[k].empty() && voices[k].back().end > n.start + kOverlap * 3)
                cost += 1000;  // ainda soando
            if (cost < bestCost)
                bestCost = cost, best = k;
        }
        n.voice = best;
        voices[best].push_back (n);
    }
    for (auto& v : voices)
        for (size_t i = 0; i + 1 < v.size(); ++i)
            if (v[i].end > v[i + 1].start + kOverlap * 3)  // sobreposição longa = nota sustentada sob a outra
                v[i].end = v[i + 1].start + kOverlap;
    if (! mono && voices[1].empty())
        voices.pop_back();
    return voices;
}

// Trilos e trêmolos escritos por extenso viram uma nota só com a técnica.
std::vector<ArtNote> collapseOrnaments (const std::vector<ArtNote>& notes)
{
    std::vector<ArtNote> out;
    size_t i = 0;
    auto close = [&] (size_t j) { return notes[j].start - notes[j - 1].end <= 0.03; };
    auto maxVel = [&] (size_t a, size_t b) { int m = 0; for (size_t k = a; k < b; ++k) m = std::max (m, notes[k].vel); return m; };
    while (i < notes.size())
    {
        const auto& a = notes[i];
        if (! a.user && a.forced == Forced::autoMode && a.dur() <= kTrillNote)
        {
            size_t j = i + 1;
            while (j < notes.size() && notes[j].pitch == a.pitch && notes[j].dur() <= kTrillNote && close (j))
                ++j;
            if (j - i >= 4)
            {
                ArtNote n = a;
                n.end = notes[j - 1].end;
                n.vel = maxVel (i, j);
                n.tech = Tech::tremolo;
                n.reason = fmt ("%.0f fast repetitions", double (j - i));
                out.push_back (n);
                i = j;
                continue;
            }
            j = i + 1;
            std::set<int> pair;
            while (j < notes.size() && notes[j].dur() <= kTrillNote && close (j))
            {
                int step = std::abs (notes[j].pitch - notes[j - 1].pitch);
                std::set<int> p { notes[j].pitch, notes[j - 1].pitch };
                if ((step != 1 && step != 2) || (! pair.empty() && p != pair))
                    break;
                pair = p;
                ++j;
            }
            if (! pair.empty() && j - i >= 4)
            {
                while (j < notes.size() && pair.count (notes[j].pitch) && notes[j].dur() <= kTrillNote && close (j))
                    ++j;
                int low = *pair.begin(), interval = *pair.rbegin() - low;
                ArtNote n = a;
                n.end = notes[j - 1].end;
                n.pitch = low;
                n.vel = maxVel (i, j);
                n.tech = interval == 1 ? Tech::trillMinor : Tech::trillMajor;
                n.reason = fmt ("%.0f notes alternating by %.0f semitone(s)", double (j - i), double (interval));
                out.push_back (n);
                i = j;
                continue;
            }
        }
        out.push_back (a);
        ++i;
    }
    return out;
}

// O que o VIOLET não sabe tocar: fora de G3–A7, notas < 60 ms e notas repetidas no mesmo instante.
std::vector<ArtNote> prepareForViolet (std::vector<ArtNote> notes)
{
    std::vector<ArtNote> out;
    for (auto n : notes)
    {
        while (n.pitch < kMinPitch) n.pitch += 12;
        while (n.pitch > kMaxPitch) n.pitch -= 12;
        n.end = std::max (n.end, n.start + kMinNote);
        if (! out.empty() && std::abs (out.back().start - n.start) < 0.01 && out.back().pitch == n.pitch)
            continue;
        out.push_back (n);
    }
    return out;
}

bool shortTech (Tech t)
{
    return t == Tech::none || t == Tech::staccato || t == Tech::spiccato || t == Tech::pizzicato || t == Tech::tremolo;
}

void classify (std::vector<ArtNote>& notes, const ArticSettings& s)
{
    const double gap = s.legatoGap;
    for (size_t i = 0; i < notes.size(); ++i)
    {
        auto& n = notes[i];
        const ArtNote* nxt = i + 1 < notes.size() ? &notes[i + 1] : nullptr;
        const ArtNote* prev = i > 0 ? &notes[i - 1] : nullptr;
        double ioi = nxt ? nxt->start - n.start : n.dur();
        bool connected = prev && n.start - prev->end <= gap;
        if (n.user || n.tech != Tech::automatic)
            continue;
        if (s.mode == ArticMode::manual)
        {
            // só keyswitches: sem keyswitch, Sustain ou Legato pela conexão
            n.tech = ! connected ? Tech::sustain : (n.pitch == prev->pitch ? Tech::legatoBow : Tech::legatoSlur);
            n.reason = connected ? "manual: connected" : "manual: no keyswitch";
            continue;
        }
        if (connected)
        {
            if (prev->dur() <= kFast || n.dur() <= kFast)
                n.tech = Tech::none, n.reason = "fast and connected";
            else if (n.pitch != prev->pitch && n.vel < s.portaVelocity)
                n.tech = Tech::legatoPortamento, n.reason = fmt ("connected with low velocity (%.0f)", n.vel);
            else if (n.pitch == prev->pitch)
                n.tech = Tech::legatoBow, n.reason = "repeated connected note (bow change)";
            else if (shortTech (prev->tech))
                n.tech = Tech::sustain, n.reason = "slur starts after a short note";
            else
                n.tech = Tech::legatoSlur, n.reason = "connected to previous note";
            continue;
        }
        double articulation = n.dur() / std::max (ioi, 1e-3);
        if (n.dur() <= kShort || (n.dur() <= 0.4 && articulation < 0.6))
            n.tech = Tech::spiccato, n.reason = fmt ("short and detached (%.0f ms of %.0f ms)", n.dur() * 1000, ioi * 1000);
        else if (n.dur() <= kFast || ioi <= kFast)
            n.tech = Tech::none, n.reason = "fast detache";
        else
            n.tech = Tech::sustain, n.reason = "long and separate";
    }
}

// Botão/keyswitch de articulação ativo na nota: a técnica dele, nas notas que o usuário não fixou.
void applyForced (std::vector<ArtNote>& notes)
{
    for (size_t i = 0; i < notes.size(); ++i)
    {
        auto& n = notes[i];
        const Forced f = n.forced;
        if (n.user || f == Forced::autoMode)
            continue;
        const ArtNote* prev = i > 0 ? &notes[i - 1] : nullptr;
        const ArtNote* nxt = i + 1 < notes.size() ? &notes[i + 1] : nullptr;
        bool near = prev && n.start - prev->end < (f == Forced::legato || f == Forced::portamento ? 1.0 : kFast);  // marcado à mão: liga até 1 s
        n.reason = "articulation button";
        switch (f)
        {
            case Forced::sustain: n.tech = Tech::sustain; break;
            case Forced::spiccato: n.tech = Tech::spiccato; break;
            case Forced::staccato: n.tech = Tech::staccato; break;
            case Forced::pizzicato: n.tech = Tech::pizzicato; break;
            case Forced::tremolo: n.tech = Tech::tremolo; break;
            case Forced::harmonic: n.tech = Tech::harmonic; break;
            case Forced::trill:
                n.tech = nxt && nxt->pitch - n.pitch == 1 ? Tech::trillMinor : Tech::trillMajor;
                break;
            case Forced::legato:
            case Forced::portamento:
                if (! near)
                    n.tech = Tech::sustain;
                else if (f == Forced::portamento && n.pitch != prev->pitch)
                    n.tech = Tech::legatoPortamento;
                else
                    n.tech = n.pitch == prev->pitch ? Tech::legatoBow : Tech::legatoSlur;
                if (near)
                    notes[i - 1].end = std::max (notes[i - 1].end, n.start);  // liga de verdade
                break;
            case Forced::autoMode: break;
        }
    }
}

std::vector<std::pair<size_t, size_t>> phrases (const std::vector<ArtNote>& notes)
{
    std::vector<std::pair<size_t, size_t>> out;
    size_t start = 0;
    for (size_t i = 1; i < notes.size(); ++i)
    {
        double gap = notes[i].start - notes[i - 1].end;
        if (gap >= 0.25 || notes[i].start - notes[start].start > 12.0)
        {
            out.push_back ({ start, i });
            start = i;
        }
    }
    out.push_back ({ start, notes.size() });
    return out;
}

// Curva de CC1 (0–127) em quadros de 20 ms: nível pela velocity da arcada + arco de frase,
// contorno melódico, messa di voce; suavizada (sigma 80 ms).
void dynamics (const std::vector<ArtNote>& notes, double gap, std::vector<float>& times, std::vector<float>& values)
{
    times.clear();
    values.clear();
    if (notes.empty())
        return;
    double end = 0;
    for (auto& n : notes) end = std::max (end, n.end);
    size_t nT = size_t (std::ceil ((end + 1.0) / kCcFrame));
    std::vector<double> t (nT), cc (nT);
    for (size_t i = 0; i < nT; ++i) t[i] = i * kCcFrame;
    std::vector<double> perNote (notes.size());
    for (size_t i = 0; i < notes.size(); ++i)
    {
        bool tied = i > 0 && notes[i].start - notes[i - 1].end <= gap;
        perNote[i] = tied ? perNote[i - 1] : 20 + 0.8 * notes[i].vel;
    }
    std::fill (cc.begin(), cc.end(), perNote[0]);
    for (auto [a, b] : phrases (notes))
    {
        double pStart = notes[a].start, pEnd = notes[b - 1].end;
        if (pEnd - pStart <= 0)
            continue;
        size_t apex = a;
        double best = -1e9, meanPitch = 0;
        for (size_t k = a; k < b; ++k)
        {
            double sc = notes[k].pitch + 6 * std::min (notes[k].dur(), 1.5);
            if (sc > best) best = sc, apex = k;
            meanPitch += notes[k].pitch;
        }
        meanPitch /= double (b - a);
        double xApex = std::clamp ((notes[apex].start + notes[apex].dur() / 2 - pStart) / (pEnd - pStart), 0.25, 0.85);
        for (size_t k = a; k < b; ++k)
        {
            const auto& n = notes[k];
            double until = k + 1 < b ? notes[k + 1].start : n.end + 0.3;
            double contour = std::clamp (0.8 * (n.pitch - meanPitch), -10.0, 10.0);
            for (size_t i = 0; i < nT; ++i)
            {
                if (t[i] < n.start || t[i] >= until) continue;
                double x = (t[i] - pStart) / (pEnd - pStart);
                double arc = x <= xApex ? -0.5 + 1.5 * std::sin (kPi / 2 * x / xApex)
                                        : 1.0 - 1.8 * std::pow (std::max (x - xApex, 0.0) / (1 - xApex), 1.3);
                double v = perNote[k] + 14 * arc + contour;
                if (n.dur() >= 0.9)
                    v += 8 * std::sin (kPi * std::clamp ((t[i] - n.start) / n.dur(), 0.0, 1.0));
                cc[i] = v;
            }
        }
        size_t idx = size_t (std::lower_bound (t.begin(), t.end(), pEnd) - t.begin());
        if (idx > 0)
        {
            double hold = cc[idx - 1];
            for (size_t i = idx; i < nT && t[i] < pEnd + 0.3; ++i) cc[i] = hold;
        }
    }
    // suaviza (gaussiana de 25 pontos, bordas repetidas)
    double kern[25], ks = 0;
    for (int k = -12; k <= 12; ++k) ks += kern[k + 12] = std::exp (-0.5 * std::pow (k * kCcFrame / 0.08, 2));
    times.resize (nT);
    values.resize (nT);
    for (size_t i = 0; i < nT; ++i)
    {
        double acc = 0;
        for (int k = -12; k <= 12; ++k)
            acc += kern[k + 12] * cc[size_t (std::clamp<long long> ((long long) i + k, 0, (long long) nT - 1))];
        times[i] = float (t[i]);
        values[i] = float (std::clamp (std::round (acc / ks), 20.0, 124.0));
    }
}
} // namespace

const char* techName (Tech t)
{
    return t == Tech::automatic ? "auto" : kNames[int (t)];
}

Tech techFromName (const std::string& s)
{
    for (int i = 0; i <= 12; ++i)
        if (s == kNames[i]) return Tech (i);
    return Tech::automatic;
}

bool isLegato (Tech t)
{
    return t == Tech::legatoBow || t == Tech::legatoSlur || t == Tech::legatoPortamento;
}

Articulated articulate (const std::vector<InNote>& in, const ArticSettings& s)
{
    std::vector<ArtNote> raw;
    for (auto& i : in)
    {
        ArtNote n;
        n.start = i.start, n.end = std::max (i.end, i.start + 0.005), n.pitch = i.pitch, n.vel = i.vel;
        if (i.user != Tech::automatic)
            n.tech = i.user, n.user = true, n.reason = "keyswitch";
        n.forced = i.forced;
        raw.push_back (n);
    }
    Articulated out;
    for (auto& voice : splitVoices (raw, s.play == PlayMode::legato))
    {
        // trilos/trêmolos escritos por extenso só se juntam onde nenhum botão força a técnica
        auto notes = prepareForViolet (s.mode == ArticMode::manual ? voice : collapseOrnaments (voice));
        applyForced (notes);
        classify (notes, s);
        if (s.play == PlayMode::longNormal)
            for (auto& n : notes)
                if (isLegato (n.tech))
                    n.tech = Tech::sustain, n.reason = "Long Normal: new bow on every note";
        out.notes.insert (out.notes.end(), notes.begin(), notes.end());
    }
    std::sort (out.notes.begin(), out.notes.end(), [] (auto& a, auto& b) { return a.start < b.start; });
    dynamics (out.notes, s.legatoGap, out.dynTimes, out.dynValues);
    return out;
}

std::vector<VNote> toViolet (const std::vector<ArtNote>& notes, double gap)
{
    std::vector<VNote> out;
    for (size_t i = 0; i < notes.size(); ++i)
    {
        const auto& n = notes[i];
        double end = n.end;
        if (i + 1 < notes.size())
        {
            const auto& nx = notes[i + 1];
            if ((isLegato (nx.tech) || nx.tech == Tech::none) && nx.start - n.end <= gap)
                end = std::max (end, nx.start + kOverlap);  // legato do VIOLET = notas sobrepostas
        }
        out.push_back ({ n.start, end, n.pitch, std::max (0, int (n.tech)) });
    }
    return out;
}

std::string summary (const std::vector<ArtNote>& notes)
{
    std::map<std::string, int> c;
    for (auto& n : notes) c[techName (n.tech)]++;
    std::vector<std::pair<int, std::string>> v;
    for (auto& [k, n] : c) v.push_back ({ -n, k });
    std::sort (v.begin(), v.end());
    std::string s;
    for (auto& [n, k] : v) s += (s.empty() ? "" : ", ") + k + " " + std::to_string (-n);
    return s;
}
} // namespace violino
