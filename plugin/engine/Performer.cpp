#include "Performer.h"

#include <algorithm>
#include <cmath>
#include <tuple>

namespace violino
{
namespace
{
constexpr double kPi = 3.14159265358979323846;
constexpr int kSr = 16000, kHop = 80, kFrame = 1024;
constexpr double kAirTarget = -37.0;  // ar (> 8 kHz) de um violino gravado
constexpr double kFastShare = 0.2;

struct Track
{
    std::vector<float> f0;     // Hz (0 = sem pitch)
    std::vector<bool> voiced;
};

// 48 kHz -> 16 kHz: passa-baixas FIR (sinc janelado, corte 7 kHz) e decimação por 3
std::vector<float> to16k (const std::vector<float>& y)
{
    constexpr int taps = 63, half = taps / 2;
    float h[taps];
    double sum = 0;
    for (int i = 0; i < taps; ++i)
    {
        double n = i - half, fc = 7000.0 / 48000.0;
        double s = n == 0 ? 2 * fc : std::sin (2 * kPi * fc * n) / (kPi * n);
        double w = 0.42 - 0.5 * std::cos (2 * kPi * i / (taps - 1)) + 0.08 * std::cos (4 * kPi * i / (taps - 1));
        sum += h[i] = float (s * w);
    }
    for (auto& v : h) v = float (v / sum);
    std::vector<float> out (y.size() / 3);
    for (size_t o = 0; o < out.size(); ++o)
    {
        long long c = (long long) o * 3;
        double acc = 0;
        for (int k = 0; k < taps; ++k)
        {
            long long i = c + k - half;
            if (i >= 0 && i < (long long) y.size()) acc += h[k] * y[size_t (i)];
        }
        out[o] = float (acc);
    }
    return out;
}

// YIN (de Cheveigné & Kawahara) com interpolação parabólica; 180–1600 Hz como no note_accuracy.py
Track pitchTrack (const std::vector<float>& y48)
{
    auto y = to16k (y48);
    const int tauMin = kSr / 1600, tauMax = kSr / 180, W = kFrame - tauMax;
    Track t;
    std::vector<double> d (size_t (tauMax + 1)), cmnd (size_t (tauMax + 1));
    for (size_t s = 0; s + kFrame <= y.size(); s += kHop)
    {
        const float* x = y.data() + s;
        double energy = 0;
        for (int j = 0; j < kFrame; ++j) energy += double (x[j]) * x[j];
        float f0 = 0;
        bool voiced = false;
        if (std::sqrt (energy / kFrame) > 0.003)
        {
            d[0] = 0;
            for (int tau = 1; tau <= tauMax; ++tau)
            {
                double acc = 0;
                for (int j = 0; j < W; ++j) { double df = x[j] - x[j + tau]; acc += df * df; }
                d[size_t (tau)] = acc;
            }
            double run = 0;
            cmnd[0] = 1;
            for (int tau = 1; tau <= tauMax; ++tau)
            {
                run += d[size_t (tau)];
                cmnd[size_t (tau)] = run > 0 ? d[size_t (tau)] * tau / run : 1;
            }
            int best = -1;
            for (int tau = tauMin; tau < tauMax; ++tau)
                if (cmnd[size_t (tau)] < 0.15)
                {
                    while (tau + 1 < tauMax && cmnd[size_t (tau + 1)] < cmnd[size_t (tau)]) ++tau;
                    best = tau;
                    break;
                }
            if (best < 0)
            {
                best = tauMin;
                for (int tau = tauMin; tau < tauMax; ++tau)
                    if (cmnd[size_t (tau)] < cmnd[size_t (best)]) best = tau;
            }
            if (cmnd[size_t (best)] < 0.25 && best > tauMin && best < tauMax)
            {
                double a = cmnd[size_t (best - 1)], b = cmnd[size_t (best)], c = cmnd[size_t (best + 1)];
                double den = a - 2 * b + c, shift = std::abs (den) > 1e-12 ? 0.5 * (a - c) / den : 0;
                f0 = float (kSr / (best + std::clamp (shift, -1.0, 1.0)));
                voiced = true;
            }
        }
        t.f0.push_back (f0);
        t.voiced.push_back (voiced);
    }
    return t;
}

double accuracy (const Track& tr, const std::vector<VNote>& notes, double shift)
{
    int ok = 0, n = 0;
    std::vector<float> buf;
    for (auto& note : notes)
    {
        if (note.pitch < kMinPitch) continue;
        ++n;
        double dur = note.end - note.start, a = note.start + shift + 0.25 * dur, b = note.start + shift + 0.75 * dur;
        buf.clear();
        for (long long i = std::max (0LL, (long long) std::ceil (a * kSr / kHop)); i < (long long) tr.f0.size() && i * double (kHop) / kSr <= b; ++i)
            if (tr.voiced[size_t (i)]) buf.push_back (tr.f0[size_t (i)]);
        if (buf.empty()) continue;
        std::nth_element (buf.begin(), buf.begin() + long (buf.size() / 2), buf.end());
        double med = buf.size() % 2 ? buf[buf.size() / 2]
                                    : 0.5 * (buf[buf.size() / 2] + *std::max_element (buf.begin(), buf.begin() + long (buf.size() / 2)));
        double cents = 1200 * std::log2 (med / (440.0 * std::pow (2.0, (note.pitch - 69) / 12.0)));
        ok += std::abs (cents) < 50 ? 1 : 0;
    }
    return n ? double (ok) / n : 0;
}
} // namespace

QualityInfo qualityInfo (Quality q)
{
    switch (q)
    {
        case Quality::low: return { 8, 0 };
        case Quality::medium: return { 15, 0 };
        case Quality::high: return { 30, 0 };     // o mesmo da avaliação oficial do VIOLET (sampler_steps: 30)
        case Quality::extreme: return { 30, 8 };
    }
    return { 30, 0 };
}

double noteAccuracy (const std::vector<float>& audio, const std::vector<VNote>& notes, double shift)
{
    return accuracy (pitchTrack (audio), notes, shift);
}

double airLevel (const std::vector<float>& y)
{
    // Welch (Hann 4096, salto 2048): mesma razão de energias que a FFT inteira do violino.py
    constexpr int N = 4096;
    if (y.size() < size_t (N)) return -60;
    double hi = 0, total = 0;
    std::vector<double> re (N), im (N);
    for (size_t s = 0; s + N <= y.size(); s += N / 2)
    {
        for (int i = 0; i < N; ++i)
        {
            re[size_t (i)] = y[s + size_t (i)] * (0.5 - 0.5 * std::cos (2 * kPi * i / N));
            im[size_t (i)] = 0;
        }
        // FFT radix-2 in-place
        for (int i = 1, j = 0; i < N; ++i)
        {
            int bit = N >> 1;
            for (; j & bit; bit >>= 1) j ^= bit;
            j ^= bit;
            if (i < j) std::swap (re[size_t (i)], re[size_t (j)]), std::swap (im[size_t (i)], im[size_t (j)]);
        }
        for (int len = 2; len <= N; len <<= 1)
        {
            double ang = -2 * kPi / len;
            for (int i = 0; i < N; i += len)
                for (int k = 0; k < len / 2; ++k)
                {
                    double wr = std::cos (ang * k), wi = std::sin (ang * k);
                    size_t u = size_t (i + k), v = size_t (i + k + len / 2);
                    double xr = re[v] * wr - im[v] * wi, xi = re[v] * wi + im[v] * wr;
                    re[v] = re[u] - xr, im[v] = im[u] - xi;
                    re[u] += xr, im[u] += xi;
                }
        }
        for (int k = 0; k <= N / 2; ++k)
        {
            double p = re[size_t (k)] * re[size_t (k)] + im[size_t (k)] * im[size_t (k)], f = k * 48000.0 / N;
            total += p;
            if (f > 8000 && f < 16000) hi += p;
        }
    }
    return 10 * std::log10 (hi / (total + 1e-12) + 1e-12);
}

Take Performer::perform (const std::vector<VNote>& notes, Quality q, double fastShare, uint64_t seed,
                         const std::function<bool (float)>& progress, int takesOverride, int stepsOverride,
                         const std::vector<float>& cc25)
{
    auto info = qualityInfo (q);
    if (stepsOverride > 0) info.steps = std::clamp (stepsOverride, 1, 50);
    int takes = takesOverride > 0 ? takesOverride : (info.takes > 0 ? info.takes : (fastShare >= kFastShare ? 4 : 1));
    Take best;
    std::tuple<double, double, double> bestKey { -1, 0, 0 };
    for (int k = 0; k < takes; ++k)
    {
        auto sub = [&] (float f) { return ! progress || progress ((float (k) + f * 0.97f) / float (takes)); };
        auto audio = renderer.render (notes, info.steps, seed + uint64_t (k) * 7919, sub, cc25);
        if (audio.empty())
            return {};  // cancelado
        // notas certas no melhor atraso tocável (-20…+40 ms); também com 1 take, para compensar o atraso
        double acc = -1, lag = 0;
        auto track = pitchTrack (audio);
        for (int i = -2; i <= 4; ++i)
        {
            double s = i * 0.01, a = accuracy (track, notes, s);
            if (a > acc + 1e-9 || (std::abs (a - acc) < 1e-9 && std::abs (s) < std::abs (lag)))
                acc = a, lag = s;
        }
        double air = airLevel (audio);
        std::tuple<double, double, double> key { std::round (acc * 50) / 50, -std::abs (air - kAirTarget), -std::abs (lag) };
        if (key > bestKey)
        {
            bestKey = key;
            best.audio = std::move (audio);
            best.accuracy = acc, best.lag = lag, best.air = air;
        }
    }
    best.takesTried = takes;
    if (best.lag > 0)  // compensa o atraso: o áudio cai no tempo do MIDI
        best.audio.erase (best.audio.begin(), best.audio.begin() + long (std::min (best.audio.size(), size_t (std::lround (best.lag * 48000)))));
    if (progress) progress (1.0f);
    return best;
}
} // namespace violino
