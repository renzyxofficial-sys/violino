#include "PreviewSampler.h"

#include <cmath>

using namespace violino;

namespace
{
constexpr double kHalfPi = 1.5707963267948966;

int setIndex (const juce::String& art)
{
    if (art == "spiccato") return PreviewSampler::spiccatoSet;
    if (art == "pizzicato") return PreviewSampler::pizzicatoSet;
    if (art == "tremolo") return PreviewSampler::tremoloSet;
    return PreviewSampler::sustainSet;
}

float releaseSec (int set)
{
    switch (set)
    {
        case PreviewSampler::spiccatoSet: return 0.12f;
        case PreviewSampler::pizzicatoSet: return 0.6f;
        case PreviewSampler::tremoloSet: return 0.2f;
        default: return 0.25f;
    }
}
} // namespace

bool PreviewSampler::load (const juce::File& dir, juce::String& error)
{
    const auto listFile = dir.getChildFile ("samples.json");
    juce::String text;
    if (juce::FileInputStream in (listFile); in.openedOk())
        text = in.readEntireStreamAsString();
    juce::var json;
    const auto parsed = juce::JSON::parse (text, json);
    if (! json.isObject())
    {
        // diagnóstico completo: existe? tamanho? leu quanto? onde o JSON quebrou?
        error = "samples.json: exists=" + juce::String (int (listFile.existsAsFile())) + " size=" + juce::String (listFile.getSize())
                + " read=" + juce::String (text.length()) + " parse=" + parsed.getErrorMessage() + " (" + listFile.getFullPathName() + ")";
        return false;
    }
    if (loaded.exchange (false))
        juce::Thread::sleep (100);  // recarregando: deixa a thread de áudio largar as vozes
    allNotesOff();
    for (auto& s : sets) s.clear();
    fileRate = double (json["sampleRate"]);
    int failed = 0;
    juce::FlacAudioFormat flac;
    if (json["samples"].getArray() == nullptr)
    {
        error = "samples.json has no sample list";
        return false;
    }
    for (auto& e : *json["samples"].getArray())
    {
        auto file = dir.getChildFile (e["file"].toString());
        std::unique_ptr<juce::AudioFormatReader> reader (flac.createReaderFor (file.createInputStream().release(), true));
        if (reader == nullptr)
        {
            ++failed;
            continue;
        }
        juce::AudioBuffer<float> buf (1, int (reader->lengthInSamples));
        reader->read (&buf, 0, buf.getNumSamples(), 0, true, false);
        Sample s;
        s.root = int (e["root"]), s.layer = int (e["layer"]), s.rr = int (e["rr"]);
        s.data.resize (size_t (buf.getNumSamples()));
        auto* src = buf.getReadPointer (0);
        // nível uniforme: o RMS da janela mais forte (200 ms) vai para um alvo por camada (f 6 dB acima de p),
        // porque as gravações do VSCO variam muito de nota para nota e de articulação para articulação
        const int win = juce::jmax (1, int (fileRate * 0.2));
        double best = 1e-9;
        for (int a = 0; a + win <= buf.getNumSamples(); a += win / 2)
        {
            double e = 0;
            for (int i = a; i < a + win; ++i) e += double (src[i]) * src[i];
            best = std::max (best, std::sqrt (e / win));
        }
        const float norm = juce::jlimit (0.25f, 2.5f, float ((s.layer ? 0.16 : 0.08) / best));  // no máximo +8 dB: mais que isso sobe o chiado das gravações suaves
        for (size_t i = 0; i < s.data.size(); ++i)
            s.data[i] = int16_t (juce::jlimit (-32767.0f, 32767.0f, src[i] * norm * 32767.0f));
        sets[size_t (setIndex (e["art"].toString()))].push_back (std::move (s));
    }
    count = 0;
    for (auto& v : sets) count += int (v.size());
    if (sets[sustainSet].empty())
    {
        error = "Preview samples could not be read (" + juce::String (failed) + " files failed)";
        return false;
    }
    loaded = true;
    return true;
}

void PreviewSampler::prepare (double sampleRate)
{
    hostRate = sampleRate;
    allNotesOff();
}

const PreviewSampler::Sample* PreviewSampler::pick (int set, int pitch, int layer, bool roundRobin)
{
    const auto& v = sets[size_t (set)].empty() ? sets[sustainSet] : sets[size_t (set)];
    const Sample* best = nullptr;
    int bestCost = 1 << 30;
    int wantRr = roundRobin ? 1 + (rrFlip & 1) : 1;
    for (auto& s : v)
    {
        int cost = std::abs (s.root - pitch) * 8 + (s.layer != layer ? 1000 : 0) + (s.rr != wantRr ? 1 : 0);
        if (cost < bestCost)
            bestCost = cost, best = &s;
    }
    return best;
}

double PreviewSampler::rateFor (int pitch, const Sample* s) const
{
    return std::pow (2.0, (pitch - s->root + bend) / 12.0) * fileRate / hostRate;
}

PreviewSampler::Voice& PreviewSampler::freeVoice()
{
    // livre > a que já está soltando (mais velha) > a mais velha; nunca corta seco o que soa forte
    Voice* best = nullptr;
    for (auto& v : voices)
    {
        if (! v.active)
            return v;
        if (best == nullptr || (v.releasing && ! best->releasing) || (v.releasing == best->releasing && v.age > best->age))
            best = &v;
    }
    return *best;
}

float PreviewSampler::layerX (int velocity) const
{
    return juce::jlimit (0.0f, 1.0f, (live.dynamicsFromCc ? cc1 : velocity) / 127.0f);
}

void PreviewSampler::startVoice (Voice& v, int pitch, int set, double startPos, float fadeSec)
{
    v = Voice {};
    v.active = v.held = true;
    v.pitch = pitch, v.set = set;
    bool rr = set == spiccatoSet || set == pizzicatoSet;
    v.p = pick (set, pitch, 0, rr);
    v.f = pick (set, pitch, 1, rr);
    if (rr) ++rrFlip;
    v.inc = v.incTarget = rateFor (pitch, v.p);
    v.pos = startPos * fileRate;
    v.env = fadeSec > 0 ? 0.0f : 1.0f;
    v.envTarget = 1.0f;
    v.envStep = fadeSec > 0 ? float (1.0 / (fadeSec * hostRate)) : 0.0f;
    v.age = 0;
}

void PreviewSampler::noteOn (int pitch, int velocity, double timeSec)
{
    if (! loaded)
        return;
    lastVelocity = velocity;
    // técnica tocada ao vivo: botão/keyswitch, senão a decisão do modo Auto com o que já se sabe
    Voice* held = nullptr;
    for (auto& v : voices)
        if (v.active && v.held && ! v.releasing && (held == nullptr || std::abs (v.pitch - pitch) < std::abs (held->pitch - pitch)))
            held = &v;
    bool chord = timeSec - lastOnTime < 0.03;
    bool connected = live.play != PlayMode::longNormal && ! chord && (held != nullptr || timeSec - lastOffTime <= 0.01);
    int set = sustainSet;
    bool legato = false, porta = false, trill = false, harmonic = false;
    switch (live.forced)
    {
        case Forced::spiccato:
        case Forced::staccato: set = spiccatoSet; break;
        case Forced::pizzicato: set = pizzicatoSet; break;
        case Forced::tremolo: set = tremoloSet; break;
        case Forced::trill: trill = true; break;
        case Forced::harmonic: harmonic = true; break;
        case Forced::legato: legato = connected; break;
        case Forced::portamento: legato = porta = connected; break;
        case Forced::sustain: break;
        case Forced::autoMode:
            if (connected)
                legato = true, porta = velocity < live.portaVelocity;
            else if (timeSec - lastOnTime < kFast)
                set = spiccatoSet;  // rápida e destacada
            break;
    }
    if (live.play == PlayMode::legato && ! chord)
        for (auto& v : voices)  // monofônico: a nota nova assume
            if (v.active && &v != held && ! v.releasing)
                v.releasing = true, v.envTarget = 0, v.envStep = float (1.0 / (0.04 * hostRate));

    auto& v = freeVoice();
    if (legato && held != nullptr && held->p != nullptr)
    {
        // legato: nota nova entra já sustentada (sem o ataque) em crossfade; portamento desliza
        const float fade = porta ? 0.09f : 0.03f;
        const int fromPitch = held->pitch;
        held->releasing = true, held->held = false;
        held->envTarget = 0, held->envStep = float (1.0 / ((porta ? 0.09 : 0.06) * hostRate));
        if (porta)
        {
            held->incTarget = held->inc * std::pow (2.0, (pitch - fromPitch) / 12.0);
            held->glide = std::pow (held->incTarget / held->inc, 1.0 / (0.09 * hostRate));
        }
        startVoice (v, pitch, set, 0.08, fade);
        if (porta)
        {
            v.inc = v.incTarget * std::pow (2.0, (fromPitch - pitch) / 12.0);
            v.glide = std::pow (v.incTarget / v.inc, 1.0 / (0.09 * hostRate));
        }
    }
    else
    {
        startVoice (v, pitch, set, 0.0, 0.002f);
    }
    v.lpCoef = harmonic ? 0.25f : 1.0f;  // harmônico: sustain filtrado
    if (trill)
    {
        v.trillRate = 7.5;
        v.trillRatio = std::pow (2.0, 2.0 / 12.0);
    }
    v.vel = velocity;
    lastPitch = pitch;
    lastOnTime = timeSec;
}

void PreviewSampler::noteOff (int pitch, double timeSec)
{
    for (auto& v : voices)
        if (v.active && v.held && v.pitch == pitch)
        {
            v.held = false;
            v.releasing = true;
            v.envTarget = 0;
            v.envStep = float (1.0 / (releaseSec (v.set) * hostRate));
        }
    lastOffTime = timeSec;
}

void PreviewSampler::allNotesOff()
{
    for (auto& v : voices) v.active = false;
}

void PreviewSampler::render (float* out, int numSamples)
{
    if (! loaded)
        return;
    const float level = juce::Decibels::decibelsToGain (live.levelDb) * 0.45f;
    for (auto& v : voices)
    {
        if (! v.active || v.p == nullptr)
            continue;
        v.age += numSamples;
        const float x = layerX (v.vel);
        const float gp = float (std::cos (x * kHalfPi)), gf = float (std::sin (x * kHalfPi));
        const float loud = level * (1 - live.intensity + live.intensity * (0.12f + 0.88f * x));
        const auto& dp = v.p->data;
        const auto& df = v.f != nullptr ? v.f->data : v.p->data;
        const double ratioPF = v.f != nullptr ? double (v.f->root == v.p->root ? 1.0 : std::pow (2.0, (v.p->root - v.f->root) / 12.0)) : 1.0;
        for (int i = 0; i < numSamples; ++i)
        {
            size_t ip = size_t (v.pos);
            double posF = v.pos * ratioPF;
            size_t jf = size_t (posF);
            if (ip + 2 >= dp.size() || jf + 2 >= df.size())
            {
                v.active = false;
                break;
            }
            float fr = float (v.pos - double (ip)), ff = float (posF - double (jf));
            auto hermite = [] (const std::vector<int16_t>& d, size_t i, float t) {
                const float xm1 = i > 0 ? d[i - 1] : d[i], x0 = d[i], x1 = d[i + 1], x2 = d[i + 2];
                const float c1 = 0.5f * (x1 - xm1), c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2, c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
                return ((c3 * t + c2) * t + c1) * t + x0;
            };
            float sp = hermite (dp, ip, fr) * (1.0f / 32768.0f);
            float sf = hermite (df, jf, ff) * (1.0f / 32768.0f);
            float s = gp * sp + gf * sf;
            v.lpState += v.lpCoef * (s - v.lpState);
            s = v.lpState;
            if (v.envStep > 0)
            {
                if (v.env < v.envTarget) v.env = std::min (v.envTarget, v.env + v.envStep);
                else if (v.env > v.envTarget) v.env = std::max (v.envTarget, v.env - v.envStep);
            }
            if (v.releasing && v.env <= 0.0f)
            {
                v.active = false;
                break;
            }
            out[i] += s * v.env * loud;
            double step = v.inc;
            if (v.trillRate > 0)
            {
                v.trillPhase += v.trillRate / hostRate;
                if (std::fmod (v.trillPhase, 1.0) >= 0.5) step *= v.trillRatio;
            }
            v.pos += step;
            if (v.glide != 1.0)
            {
                v.inc *= v.glide;
                if ((v.glide > 1 && v.inc >= v.incTarget) || (v.glide < 1 && v.inc <= v.incTarget))
                    v.inc = v.incTarget, v.glide = 1.0;
            }
        }
    }
}
