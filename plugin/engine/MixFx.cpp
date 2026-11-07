#include "MixFx.h"

#include <algorithm>
#include <cmath>
#include <random>

namespace violino
{
namespace
{
constexpr double kPi = 3.14159265358979323846;
constexpr int kBase[] = { 1531, 1777, 2053, 2311, 2591, 2833, 3121, 3413 };
constexpr int kLateAp[] = { 113, 131, 149, 167, 181, 199, 223, 241 };

struct Band { Biquad::Kind k; double f, g, q; };
struct Style
{
    ReverbParams verb;
    double wet, sendHp, sendLp;
    std::vector<Band> eq, busEq;
    bool comp;
    double thresh, ratio, attack, release, drive, width;
};

// Salas do mixer.py (RT60 grave/agudo -> decaimento + shelf agudo) e os números do MIX_STYLES
ReverbParams room (double rtLow, double rtHigh, double predelay, double size, double erLen, double erGain, double rtScale)
{
    ReverbParams p;
    p.decay = rtLow * rtScale, p.bassMult = 1.0, p.bassFreq = 500, p.highFreq = 4000;
    p.highShelfDb = 20 * std::log10 (rtHigh / rtLow);
    p.size = size, p.earlyDiff = 0.7, p.lateDiff = 0, p.attack = 0.5, p.predelay = predelay, p.erLen = erLen, p.erGain = erGain;
    return p;
}

const Style& style (MixStyle s)
{
    using K = Biquad::Kind;
    static const Style lyrical { room (1.4, 0.9, 0.036, 0.7, 0.04, 0.45, 1.0), 0.26, 220, 11000,
                                 { { K::highpass, 100, 0, 0.7 }, { K::peak, 300, -1.5, 1.0 }, { K::peak, 1200, 2.0, 1.2 } },
                                 { { K::peak, 3200, 4.0, 1.0 }, { K::highShelf, 6500, 5.5, 0.7 } }, true, -22, 2.0, 0.03, 0.2, 0.0, 1.1 };
    static const Style romantic { room (2.4, 1.5, 0.022, 1.0, 0.06, 0.35, 1.1), 0.36, 170, 10000,
                                  { { K::highpass, 75, 0, 0.7 }, { K::peak, 250, 1.5, 0.8 }, { K::peak, 3400, -0.5, 1.2 } },
                                  { { K::peak, 2400, 3.5, 0.9 }, { K::highShelf, 6500, 5.0, 0.7 } }, false, 0, 1, 0, 0, 0.25, 1.35 };
    static const Style baroque { room (5.0, 2.8, 0.006, 1.6, 0.12, 0.25, 0.62), 0.38, 160, 8000,
                                 { { K::highpass, 150, 0, 0.7 }, { K::peak, 320, -3.0, 0.9 } },
                                 { { K::peak, 4500, 3.0, 0.9 }, { K::highShelf, 7500, 2.5, 0.7 } }, false, 0, 1, 0, 0, 0.0, 0.6 };
    static const Style cinematic { room (2.0, 1.6, 0.035, 1.15, 0.07, 0.5, 1.6), 0.42, 200, 11000,
                                   { { K::highpass, 90, 0, 0.7 }, { K::peak, 250, 1.0, 0.8 }, { K::peak, 3800, -1.0, 2.5 } },
                                   { { K::peak, 2800, 3.5, 0.9 }, { K::highShelf, 6000, 6.5, 0.7 } }, true, -22, 2.5, 0.02, 0.12, 0.2, 1.8 };
    switch (s)
    {
        case MixStyle::lyrical: return lyrical;
        case MixStyle::romantic: return romantic;
        case MixStyle::baroque: return baroque;
        default: return cinematic;
    }
}

// mede o ganho que leva a cauda ao nível do seco (o mixer.py normaliza pelo RMS)
double calibrate (FdnReverb& verb, const ReverbParams& p, double sr, double hp, double lp)
{
    verb.configure (p);
    verb.reset();
    Biquad h, l;
    h.set (Biquad::highpass, hp, 0, 0.7071, sr);
    l.set (Biquad::lowpass, lp, 0, 0.7071, sr);
    std::mt19937 nr (11);
    std::normal_distribution<float> g (0.f, 0.1f);
    double eIn = 0, eOut = 0;
    const int n = int (sr * (1.0 + std::min (p.decay, 4.0)));
    for (int i = 0; i < n; ++i)
    {
        float x = g (nr), a, b;
        eIn += double (x) * x;
        verb.process (l.process (h.process (x)), a, b);
        if (i > n / 2) eOut += 0.5 * (double (a) * a + double (b) * b);
    }
    verb.reset();
    return std::sqrt ((eIn / n) / std::max (eOut / (n - n / 2), 1e-12));
}

double styleCalib[4] = { 1, 1, 1, 1 }, userCalibRef = 1;
} // namespace

// ------------------------------------------------------------------ curvas de saturação (iguais às da UI)
float saturate (int type, float u)
{
    switch (type)
    {
        case 0: return std::tanh (u);                                                       // Analog Clip
        case 1: return float (std::sin (std::clamp (double (u), -kPi / 2, kPi / 2)));     // Soft Sine
        case 2: return u > 0 ? u / (1 + u) : u / (1 - 0.6f * u);                          // Bass Shaper (assimétrico)
        case 3: return float (2 / kPi * std::atan (u));                                    // Medium Curve
        case 4: { float c = std::clamp (u, -1.0f, 1.0f); return 1.5f * c - 0.5f * c * c * c; }  // Hard Curve
        case 5: return std::sin (u);                                                         // Sinoid Fold
        case 6: return std::clamp (u, -1.0f, 1.0f);                                         // Digital Clip
        default: { const float k = 2.5f; return (1 + k) * u / (1 + k * std::abs (u)); }    // Waveshaper
    }
}

void Biquad::set (Kind k, double f, double gainDb, double q, double sr)
{
    f = std::clamp (f, 10.0, sr * 0.45);
    q = std::max (q, 0.05);
    double A = std::pow (10.0, gainDb / 40), w = 2 * kPi * f / sr, cw = std::cos (w), sw = std::sin (w), al = sw / (2 * q);
    double B0, B1, B2, A0, A1, A2;
    switch (k)
    {
        case peak: B0 = 1 + al * A, B1 = -2 * cw, B2 = 1 - al * A, A0 = 1 + al / A, A1 = -2 * cw, A2 = 1 - al / A; break;
        case highpass: B0 = (1 + cw) / 2, B1 = -(1 + cw), B2 = (1 + cw) / 2, A0 = 1 + al, A1 = -2 * cw, A2 = 1 - al; break;
        case lowpass: B0 = (1 - cw) / 2, B1 = 1 - cw, B2 = (1 - cw) / 2, A0 = 1 + al, A1 = -2 * cw, A2 = 1 - al; break;
        case allpass: B0 = 1 - al, B1 = -2 * cw, B2 = 1 + al, A0 = 1 + al, A1 = -2 * cw, A2 = 1 - al; break;
        case highShelf:
        {
            double s = 2 * std::sqrt (A) * al;
            B0 = A * ((A + 1) + (A - 1) * cw + s), B1 = -2 * A * ((A - 1) + (A + 1) * cw), B2 = A * ((A + 1) + (A - 1) * cw - s);
            A0 = (A + 1) - (A - 1) * cw + s, A1 = 2 * ((A - 1) - (A + 1) * cw), A2 = (A + 1) - (A - 1) * cw - s;
            break;
        }
        default:
        {
            double s = 2 * std::sqrt (A) * al;
            B0 = A * ((A + 1) - (A - 1) * cw + s), B1 = 2 * A * ((A - 1) - (A + 1) * cw), B2 = A * ((A + 1) - (A - 1) * cw - s);
            A0 = (A + 1) + (A - 1) * cw + s, A1 = -2 * ((A - 1) + (A + 1) * cw), A2 = (A + 1) + (A - 1) * cw - s;
        }
    }
    b0 = B0 / A0, b1 = B1 / A0, b2 = B2 / A0, a1 = A1 / A0, a2 = A2 / A0;
}

// ------------------------------------------------------------------ FDN
void FdnReverb::prepare (double sampleRate)
{
    sr = sampleRate;
    const double k = sr / 48000.0;
    pre.assign (size_t (0.25 * sr) + 2, 0.f);
    const int apD[] = { 142, 107, 379, 277 };
    for (int i = 0; i < 4; ++i)
    {
        apLen[size_t (i)] = std::max<size_t> (1, size_t (apD[i] * k));
        ap[size_t (i)].assign (apLen[size_t (i)], 0.f);
    }
    bufLen = size_t (kBase[7] * 2.0 * k) + 64;  // tamanho máximo (Size 100 % da catedral) + modulação
    for (int i = 0; i < kLines; ++i)
    {
        line[size_t (i)].assign (bufLen, 0.f);
        lapLen[size_t (i)] = std::max<size_t> (1, size_t (kLateAp[i] * k));
        lap[size_t (i)].assign (lapLen[size_t (i)], 0.f);
    }
    erBuf.assign (size_t (0.13 * sr) + 2, 0.f);
    std::mt19937 rng (7);
    std::uniform_int_distribution<int> coin (0, 1);
    for (int i = 0; i < kLines; ++i)
    {
        signL[size_t (i)] = coin (rng) ? 1.f : -1.f;
        signR[size_t (i)] = coin (rng) ? 1.f : -1.f;
    }
    configure (ReverbParams {});
    reset();
}

void FdnReverb::configure (const ReverbParams& p)
{
    const double k = sr / 48000.0;
    preLen = std::clamp<size_t> (size_t (p.predelay * sr), 1, pre.size() - 1);
    apG = float (std::clamp (p.earlyDiff, 0.0, 1.0) * 0.75);
    lateG = std::clamp (p.lateDiff, 0.0, 1.0) * 0.6;
    const double decay = std::max (p.decay, 0.1), rtLow = decay * std::max (p.bassMult, 0.1);
    const double rtHigh = decay * std::max (std::pow (10.0, p.highShelfDb / 20.0), 0.02);
    cLow = 1 - std::exp (-2 * kPi * std::clamp (p.bassFreq, 20.0, 5000.0) / sr);
    cHigh = 1 - std::exp (-2 * kPi * std::clamp (p.highFreq, 200.0, sr * 0.45) / sr);
    modDepthSmp = std::clamp (p.modDepth, 0.0, 1.0) * 12.0 * k;
    modInc = std::max (p.modRate, 0.0) / sr;
    for (int i = 0; i < kLines; ++i)
    {
        double d = std::clamp (kBase[i] * std::clamp (p.size, 0.2, 2.0) * k, 200.0, double (bufLen) - modDepthSmp - 4);
        delay[size_t (i)] = d;
        gLow[size_t (i)] = std::pow (10.0, -3.0 * d / (rtLow * sr));
        gMid[size_t (i)] = std::pow (10.0, -3.0 * d / (decay * sr));
        gHigh[size_t (i)] = std::pow (10.0, -3.0 * d / (rtHigh * sr));
    }
    std::mt19937 rng (7);
    std::uniform_real_distribution<double> u (0.004, std::max (p.erLen, 0.01)), amp (0.6, 1.0);
    std::array<double, 12> times;
    for (auto& t : times) t = u (rng);
    std::sort (times.begin(), times.end());
    const double erLevel = p.erGain * (1.6 - 1.2 * std::clamp (p.attack, 0.0, 1.0));  // Attack curto = reflexões fortes
    for (int i = 0; i < 12; ++i)
    {
        erTap[size_t (i)] = std::min (erBuf.size() - 1, size_t (times[size_t (i)] * sr));
        erGain[size_t (i)] = float (erLevel * (1 - times[size_t (i)] / (std::max (p.erLen, 0.01) * 1.4)) * amp (rng));
    }
}

void FdnReverb::reset()
{
    std::fill (pre.begin(), pre.end(), 0.f);
    for (auto& a : ap) std::fill (a.begin(), a.end(), 0.f);
    for (auto& l : line) std::fill (l.begin(), l.end(), 0.f);
    for (auto& l : lap) std::fill (l.begin(), l.end(), 0.f);
    std::fill (erBuf.begin(), erBuf.end(), 0.f);
    lowState.fill (0), highState.fill (0);
}

void FdnReverb::process (float in, float& outL, float& outR)
{
    pre[prePos] = in;
    float x = pre[(prePos + pre.size() - preLen) % pre.size()];
    prePos = (prePos + 1) % pre.size();
    erBuf[erPos] = x;
    float el = 0, er = 0;
    for (size_t k = 0; k < 12; ++k)
    {
        float v = erGain[k] * erBuf[(erPos + erBuf.size() - erTap[k]) % erBuf.size()];
        if (k % 2) er += v, el += 0.35f * v;
        else el += v, er += 0.35f * v;
    }
    erPos = (erPos + 1) % erBuf.size();
    float d = x;
    for (size_t i = 0; i < 4; ++i)
    {
        auto& b = ap[i];
        float delayed = b[apPos[i]];
        float y = -apG * d + delayed;
        b[apPos[i]] = d + apG * y;
        apPos[i] = (apPos[i] + 1) % apLen[i];
        d = y;
    }
    modPhase += modInc;
    if (modPhase >= 1) modPhase -= 1;
    std::array<double, kLines> f;
    double sum = 0;
    for (size_t i = 0; i < kLines; ++i)
    {
        // leitura fracionária (modulação de cada linha com fase própria)
        double m = modDepthSmp > 0 ? modDepthSmp * (0.5 + 0.5 * std::sin (2 * kPi * (modPhase + 0.125 * double (i)))) : 0;
        double rp = double (writePos) - delay[i] - m;
        while (rp < 0) rp += double (bufLen);
        size_t i0 = size_t (rp) % bufLen, i1 = (i0 + 1) % bufLen;
        double fr = rp - std::floor (rp), tap = line[i][i0] + fr * (line[i][i1] - line[i][i0]);
        // absorção em 3 faixas: grave (< BassFreq), médio, agudo (> HighFreq)
        lowState[i] += cLow * (tap - lowState[i]);
        double y = gLow[i] * lowState[i] + gMid[i] * (tap - lowState[i]);
        highState[i] += cHigh * (y - highState[i]);
        y = highState[i] + (gHigh[i] / std::max (gMid[i], 1e-9)) * (y - highState[i]);
        if (lateG > 0)  // difusão tardia
        {
            auto& b = lap[i];
            double dl = b[lapPos[i]], o = -lateG * y + dl;
            b[lapPos[i]] = float (y + lateG * o);
            lapPos[i] = (lapPos[i] + 1) % lapLen[i];
            y = o;
        }
        f[i] = y;
        sum += y;
    }
    double l = 0, r = 0, hh = 2.0 / kLines * sum;
    for (size_t i = 0; i < kLines; ++i)
    {
        line[i][writePos] = float (f[i] - hh + d * (i % 2 ? 0.5 : -0.5));
        l += signL[i] * f[i];
        r += signR[i] * f[i];
    }
    writePos = (writePos + 1) % bufLen;
    const double norm = 1.0 / std::sqrt (double (kLines));
    outL = float (l * norm) + el;
    outR = float (r * norm) + er;
}

// ------------------------------------------------------------------ cadeia
void MixFx::prepare (double sampleRate)
{
    sr = sampleRate;
    styleVerb.prepare (sr);
    userVerb.prepare (sr);
    for (int s = 0; s < 4; ++s)
    {
        const auto& st = style (MixStyle (s + 1));
        styleCalib[s] = calibrate (styleVerb, st.verb, sr, st.sendHp, st.sendLp);
    }
    ReverbParams ref;
    ref.decay = 2.4, ref.size = 1.0, ref.earlyDiff = 1, ref.lateDiff = 0.6;
    userCalibRef = calibrate (userVerb, ref, sr, 180, 9000);
    pre.reserve (8);
    for (auto& b : bus) b.reserve (8);
    chorusBuf.assign (size_t (0.05 * sr) + 4, 0.f);
    dlyL.assign (size_t (2.5 * sr) + 8, 0.f);
    dlyR.assign (size_t (2.5 * sr) + 8, 0.f);
    built = false;
    rebuild();
    reset();
}

void MixFx::set (const MixSettings& s)
{
    if (s == cur && built)
        return;
    const bool reset1 = s.style != cur.style, reset2 = s.reverbOn != cur.reverbOn;
    cur = s;
    rebuild();
    if (reset1) styleVerb.reset();
    if (reset2) userVerb.reset();
}

void MixFx::rebuild()
{
    pre.clear();
    for (auto& b : bus) b.clear();
    auto add = [&] (std::vector<Biquad>& v, Biquad::Kind k, double f, double g, double q) { Biquad b; b.set (k, f, g, q, sr); v.push_back (b); };
    styleOn = cur.style != MixStyle::dry;
    styleComp = false, drive = 0, width = 1, wet = 0;
    if (styleOn)
    {
        const auto& st = style (cur.style);
        for (auto& b : st.eq) add (pre, b.k, b.f, b.g, b.q);
        for (int c = 0; c < 2; ++c)
            for (auto& b : st.busEq) add (bus[size_t (c)], b.k, b.f, b.g, b.q);
        wet = float (st.wet), drive = float (st.drive), width = float (st.width), styleComp = st.comp;
        compThresh = st.thresh, compRatio = st.ratio;
        compAtk = std::exp (-1.0 / (std::max (st.attack, 1e-3) * sr));
        compRel = std::exp (-1.0 / (std::max (st.release, 1e-3) * sr));
        makeup = -st.thresh * (1 - 1 / st.ratio) * 0.35;
        sendHp.set (Biquad::highpass, st.sendHp, 0, 0.7071, sr);
        sendLp.set (Biquad::lowpass, st.sendLp, 0, 0.7071, sr);
        styleVerb.configure (st.verb);
        styleTail = float (styleCalib[int (cur.style) - 1]);
    }
    envC = std::exp (-1.0 / (0.01 * sr));

    // Reverb do usuário (Color: 1970s escuro e muito modulado; 1980s; Now limpo e aberto)
    {
        // Color muda o som: 1970s escuro, modulação funda, grave pesado; 1980s brilho digital e difusão
        // densa; Now banda cheia com ar, modulação sutil, grave enxuto
        const int col = std::clamp (cur.revColor, 0, 2);
        const double colorMod[] = { 1.6, 1.0, 0.4 }, colorCut[] = { 7000, 11000, 20000 }, colorShelf[] = { -3, 0, 2 };
        const double colorBass[] = { 1.15, 1.0, 0.85 }, colorEarly[] = { 0.8, 1.15, 1.0 }, colorLate[] = { 0.85, 1.0, 1.15 };
        ReverbParams p;
        p.decay = cur.revDecay, p.bassMult = cur.revBassMult * colorBass[col], p.bassFreq = cur.revBassFreq;
        p.highFreq = cur.revHighFreq, p.highShelfDb = std::min (0.0, cur.revHighShelf + colorShelf[col]);
        p.size = 0.35 + 1.45 * cur.revSize, p.attack = cur.revAttack;
        p.earlyDiff = std::min (1.0, cur.revEarly * colorEarly[col]), p.lateDiff = std::min (1.0, cur.revLate * colorLate[col]);
        p.modRate = cur.revModRate, p.modDepth = std::min (1.0, cur.revModDepth * colorMod[col]);
        if (cur.revFreeze)  // Freeze: cauda infinita, sem entrada nova
            p.decay = 600, p.bassMult = 1, p.highShelfDb = 0;
        p.predelay = cur.predelayMs / 1000.0, p.erLen = 0.02 + 0.08 * cur.revSize, p.erGain = 0.4;
        userVerb.configure (p);
        const double cut = std::min<double> (cur.revHighCut, colorCut[col]);
        for (auto& b : userSendHp) b.set (Biquad::highpass, cur.revLowCut, 0, 0.7071, sr);
        for (auto& b : userSendLp) b.set (Biquad::lowpass, cut, 0, 0.7071, sr);
        userTail = float (userCalibRef * std::sqrt (2.4 / std::max (0.2f, cur.revDecay)));
    }

    // EQ paramétrico
    for (size_t i = 0; i < 5; ++i)
    {
        const auto& b = cur.eq[i];
        const bool cut = b.type == 0 || b.type == 4;
        eqActive[i] = cur.eqOn && b.on && (cut || std::abs (b.gain) > 0.01f);
        eqDouble[i] = cut;
        const Biquad::Kind kinds[] = { Biquad::highpass, Biquad::lowShelf, Biquad::peak, Biquad::highShelf, Biquad::lowpass };
        for (int c = 0; c < 2; ++c)
        {
            eq[i][size_t (c)].set (kinds[std::clamp (b.type, 0, 4)], b.freq, b.gain, b.q, sr);
            eq2[i][size_t (c)].set (kinds[std::clamp (b.type, 0, 4)], b.freq, b.gain, b.q, sr);
        }
    }
    userComp.thresh = cur.compThresh, userComp.ratio = std::max (1.0f, cur.compRatio);
    userComp.atk = std::exp (-1.0 / (std::max (0.5f, cur.compAttackMs) * 0.001 * sr));
    userComp.rel = std::exp (-1.0 / (std::max (5.0f, cur.compReleaseMs) * 0.001 * sr));
    userComp.envC = std::exp (-1.0 / (0.01 * sr));
    userComp.makeup = cur.compMakeup;
    const double decoF[] = { 320, 1150, 470, 2300 };
    for (size_t i = 0; i < 4; ++i) deco[i].set (Biquad::allpass, decoF[i], 0, 0.7, sr);
    // Delay: filtros da realimentação (o caráter escurece mais)
    const double charLp[] = { 20000, 6000, 3500 };
    for (auto& b : dlyHp) b.set (Biquad::highpass, cur.delayHp, 0, 0.7071, sr);
    for (auto& b : dlyLp) b.set (Biquad::lowpass, std::min<double> (cur.delayLp, charLp[std::clamp (cur.delayChar, 0, 2)]), 0, 0.7071, sr);
    dlyLenL = std::clamp (cur.delayLeftMs * 0.001 * sr, 1.0, double (dlyL.size()) - 400);
    dlyLenR = std::clamp (cur.delayRightMs * 0.001 * sr, 1.0, double (dlyR.size()) - 400);
    outGain = float (std::pow (10.0, cur.outputDb / 20.0));
    built = true;
}

float MixFx::Comp::process (float x)
{
    env = envC * env + (1 - envC) * double (x) * x;
    double db = 10 * std::log10 (env + 1e-18);
    double target = -std::max (db - thresh, 0.0) * (1 - 1 / ratio);
    double c = target < gain ? atk : rel;
    gain = c * gain + (1 - c) * target;
    return x * float (std::pow (10.0, (gain + makeup) / 20));
}

void MixFx::reset()
{
    styleVerb.reset();
    userVerb.reset();
    env = 0, gainDb = 0;
    sendHp.reset(), sendLp.reset();
    std::fill (chorusBuf.begin(), chorusBuf.end(), 0.f);
    std::fill (dlyL.begin(), dlyL.end(), 0.f);
    std::fill (dlyR.begin(), dlyR.end(), 0.f);
    for (auto& d : deco) d.reset();
}

void MixFx::process (const float* mono, float* left, float* right, int n)
{
    const float satDrive = std::pow (10.0f, cur.satDriveDb / 20.0f), satOut = std::pow (10.0f, cur.satOutputDb / 20.0f);
    float grMax = 0;
    auto readFrac = [] (const std::vector<float>& b, size_t w, double d) {
        double rp = double (w) - d;
        while (rp < 0) rp += double (b.size());
        size_t i0 = size_t (rp) % b.size(), i1 = (i0 + 1) % b.size();
        float fr = float (rp - std::floor (rp));
        return b[i0] + fr * (b[i1] - b[i0]);
    };
    for (int i = 0; i < n; ++i)
    {
        float x = mono[i];
        // ---- Mix Style: cor antes da sala
        for (auto& b : pre) x = b.process (x);
        if (styleComp)
        {
            env = envC * env + (1 - envC) * double (x) * x;
            double db = 10 * std::log10 (env + 1e-18);
            double target = -std::max (db - compThresh, 0.0) * (1 - 1 / compRatio);
            double c = target < gainDb ? compAtk : compRel;
            gainDb = c * gainDb + (1 - c) * target;
            x *= float (std::pow (10.0, (gainDb + makeup) / 20));
        }
        if (drive > 0)
        {
            const float k = 1 + 4 * drive, ref = 0.5f;
            x = (1 - drive) * x + drive * std::tanh (k * x / ref) / std::tanh (k) * ref;
        }
        // ---- módulos do usuário (mono)
        if (cur.compOn)
        {
            x = userComp.process (x);
            grMax = std::min (grMax, float (userComp.gain));
        }
        if (cur.satOn)
        {
            float y = saturate (cur.satType, x * satDrive) * satOut;
            x = (1 - cur.satMix) * x + cur.satMix * y;
        }
        // ---- estéreo: Stereo (decorrelação; a soma mono volta a ser x) e Chorus
        float l = x, r = x;
        if (cur.stereoOn && cur.stereoWidth > 0)
        {
            float a = deco[1].process (deco[0].process (x)), b = deco[3].process (deco[2].process (x));
            float s = 0.5f * cur.stereoWidth * (a - b);
            l = x + s, r = x - s;
        }
        if (cur.chorusOn)
        {
            chorusBuf[chorusPos] = x;
            chorusPhase += cur.chorusRate / sr;
            if (chorusPhase >= 1) chorusPhase -= 1;
            auto tap = [&] (double ph) { return readFrac (chorusBuf, chorusPos, (0.012 + 0.004 * cur.chorusDepth * (1 + std::sin (2 * kPi * ph))) * sr); };
            float cl = tap (chorusPhase), cr = tap (chorusPhase + 0.25);
            l = (1 - cur.chorusMix) * l + cur.chorusMix * cl;
            r = (1 - cur.chorusMix) * r + cur.chorusMix * cr;
            chorusPos = (chorusPos + 1) % chorusBuf.size();
        }
        // ---- Delay
        if (cur.delayOn)
        {
            // modulação: Tape = wow + flutter; Analog = leve; Digital = só o que o usuário pedir
            dlyPhase += 1.0 / sr;
            const double charMod[] = { 0.5, 3.0, 1.0 };
            double mod = cur.delayMod * charMod[std::clamp (cur.delayChar, 0, 2)] * 0.001 * sr
                         * (0.7 * std::sin (2 * kPi * 0.8 * dlyPhase) + 0.3 * std::sin (2 * kPi * 4.3 * dlyPhase));
            float eL = readFrac (dlyL, dlyPos, dlyLenL + std::abs (mod) + 2), eR = readFrac (dlyR, dlyPos, dlyLenR + std::abs (mod) + 2);
            auto loop = [&] (float v, int c) {
                v = dlyLp[size_t (c)].process (dlyHp[size_t (c)].process (v));
                if (cur.delayChar == 1) v = std::tanh (1.4f * v) / 1.4f;       // fita satura
                else if (cur.delayChar == 2) v = std::tanh (1.15f * v) / 1.15f;
                return v * cur.delayFeedback;
            };
            const float mid = 0.5f * (l + r), side = 0.5f * (l - r);
            float outL, outR;
            if (cur.delayMode == 1)  // Ping Pong: entra à esquerda, cruza a cada repetição
            {
                dlyL[dlyPos] = mid + loop (eR, 1);
                dlyR[dlyPos] = loop (eL, 0);
                outL = eL, outR = eR;
            }
            else if (cur.delayMode == 2)  // Mid/Side: tempo L no centro, tempo R nas laterais
            {
                dlyL[dlyPos] = mid + loop (eL, 0);
                dlyR[dlyPos] = side + loop (eR, 1);
                outL = eL + eR, outR = eL - eR;
            }
            else  // Stereo: dois ecos independentes
            {
                dlyL[dlyPos] = l + loop (eL, 0);
                dlyR[dlyPos] = r + loop (eR, 1);
                outL = eL, outR = eR;
            }
            dlyPos = (dlyPos + 1) % dlyL.size();
            l = (1 - 0.5f * cur.delayMix) * l + cur.delayMix * outL;
            r = (1 - 0.5f * cur.delayMix) * r + cur.delayMix * outR;
        }
        // ---- salas: a do Mix Style e o Reverb do usuário
        const float send = 0.5f * (l + r);
        if (styleOn)
        {
            float tl, tr;
            styleVerb.process (sendLp.process (sendHp.process (send)), tl, tr);
            float m = 0.5f * (tl + tr), s = 0.5f * (tl - tr) * width;
            tl = (m + s) * styleTail, tr = (m - s) * styleTail;
            l = (1 - wet) * l + wet * tl;
            r = (1 - wet) * r + wet * tr;
        }
        if (cur.reverbOn)
        {
            float tl, tr;
            userVerb.process (cur.revFreeze ? 0.0f : userSendLp[0].process (userSendHp[0].process (send)), tl, tr);
            // Ducking: o molhado abaixa enquanto o violino toca e volta nas pausas
            duckEnv = std::max (double (std::abs (send)), duckEnv * 0.9996);
            const float duck = 1.0f - cur.revDucking * float (std::min (1.0, duckEnv * 6.0));
            const float w = cur.reverbMix * duck * (cur.revFreeze ? 1.0f : userTail) * (cur.revFreeze ? userTail : 1.0f);
            l = (1 - cur.reverbMix) * l + w * tl;
            r = (1 - cur.reverbMix) * r + w * tr;
        }
        for (auto& b : bus[0]) l = b.process (l);
        for (auto& b : bus[1]) r = b.process (r);
        // ---- EQ paramétrico (no fim, como um Pro-Q no master)
        for (size_t k = 0; k < 5; ++k)
        {
            if (! eqActive[k]) continue;
            l = eq[k][0].process (l), r = eq[k][1].process (r);
            if (eqDouble[k]) l = eq2[k][0].process (l), r = eq2[k][1].process (r);
        }
        l *= outGain, r *= outGain;
        auto soft = [] (float v) { const float t = 0.89f; return std::abs (v) <= t ? v : std::copysign (t + (1 - t) * std::tanh ((std::abs (v) - t) / (1 - t)), v); };
        left[i] = soft (l);
        right[i] = soft (r);
    }
    grDb = grMax;
}
} // namespace violino
