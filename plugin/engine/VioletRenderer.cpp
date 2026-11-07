#include "VioletRenderer.h"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dxgi1_4.h>

#include <onnxruntime_cxx_api.h>
#include <dml_provider_factory.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <random>

namespace violino
{
namespace
{
constexpr double kFrameRate = 25.0, kStep = 0.01, kWindowSec = 10.0, kTail = 1.0, kEdge = 0.04;
constexpr int kAttempts = 4, kSeedStride = 1009;
constexpr float kSilenceRms = 1e-2f;

// ---- meia precisão (IEEE 754 binary16), arredondamento para o par mais próximo
uint16_t toHalf (float f)
{
    uint32_t x;
    std::memcpy (&x, &f, 4);
    uint32_t sign = (x >> 16) & 0x8000u;
    int32_t exp = int32_t ((x >> 23) & 0xff) - 127 + 15;
    uint32_t mant = x & 0x7fffffu;
    if (((x >> 23) & 0xff) == 0xff)
        return uint16_t (sign | 0x7c00u | (mant ? 0x200u : 0));
    if (exp >= 31)
        return uint16_t (sign | 0x7c00u);
    if (exp <= 0)
    {
        if (exp < -10)
            return uint16_t (sign);
        mant |= 0x800000u;
        uint32_t shift = uint32_t (14 - exp);
        uint32_t half = mant >> shift, rem = mant & ((1u << shift) - 1), mid = 1u << (shift - 1);
        if (rem > mid || (rem == mid && (half & 1)))
            ++half;
        return uint16_t (sign | half);
    }
    uint32_t half = sign | (uint32_t (exp) << 10) | (mant >> 13);
    uint32_t rem = mant & 0x1fffu;
    if (rem > 0x1000u || (rem == 0x1000u && (half & 1)))
        ++half;
    return uint16_t (half);
}

float fromHalf (uint16_t h)
{
    uint32_t sign = uint32_t (h & 0x8000u) << 16, exp = (h >> 10) & 0x1f, mant = h & 0x3ffu, x;
    if (exp == 0)
    {
        if (mant == 0)
            x = sign;
        else
        {
            exp = 127 - 15 + 1;
            while (! (mant & 0x400u)) mant <<= 1, --exp;
            x = sign | (exp << 23) | ((mant & 0x3ffu) << 13);
        }
    }
    else if (exp == 31)
        x = sign | 0x7f800000u | (mant << 13);
    else
        x = sign | ((exp - 15 + 127) << 23) | (mant << 13);
    float f;
    std::memcpy (&f, &x, 4);
    return f;
}

bool playable (const VNote& n) { return n.pitch >= kMinPitch; }

bool activity (const std::vector<VNote>& notes, double st)
{
    for (auto& n : notes)
        if (playable (n) && n.end > st && n.start < st + kWindowSec)
            return true;
    return false;
}

// início da primeira nota na janela (relativo), ou -1
double firstOnset (const std::vector<VNote>& notes, double st, double len)
{
    double best = -1;
    for (auto& n : notes)
    {
        if (! playable (n) || n.end <= st || n.start >= st + len)
            continue;
        if (n.start <= st)
            return 0.0;
        double rel = n.start - st;
        if (best < 0 || rel < best)
            best = rel;
    }
    return best;
}

void edgeMask (float* y, size_t n, double onsetRel)
{
    size_t edge = std::min<size_t> (size_t (std::lround (kEdge * VioletRenderer::kSampleRate)), n);
    std::fill (y + n - edge, y + n, 0.0f);
    if (onsetRel < 0 || onsetRel >= kEdge)
        std::fill (y, y + edge, 0.0f);
}

float peakRms (const float* y, size_t n)
{
    const size_t frame = 4800, hop = 1200;  // 100 ms / 25 ms
    auto rms = [&] (size_t a, size_t len) { double s = 0; for (size_t i = a; i < a + len; ++i) s += double (y[i]) * y[i]; return float (std::sqrt (s / double (len))); };
    if (n == 0) return 0;
    if (n <= frame) return rms (0, n);
    float peak = 0;
    for (size_t s = 0; s + frame <= n; s += hop)
        peak = std::max (peak, rms (s, frame));
    return peak;
}

std::wstring join (const std::wstring& dir, const wchar_t* name)
{
    return dir + (dir.empty() || dir.back() == L'\\' || dir.back() == L'/' ? L"" : L"\\") + name;
}
} // namespace

GpuInfo pickGpu()
{
    GpuInfo best;
    IDXGIFactory1* factory = nullptr;
    if (FAILED (CreateDXGIFactory1 (__uuidof (IDXGIFactory1), (void**) &factory)))
        return best;
    IDXGIAdapter1* ad = nullptr;
    for (UINT i = 0; factory->EnumAdapters1 (i, &ad) != DXGI_ERROR_NOT_FOUND; ++i)
    {
        DXGI_ADAPTER_DESC1 d;
        ad->GetDesc1 (&d);
        if (! (d.Flags & DXGI_ADAPTER_FLAG_SOFTWARE) && d.DedicatedVideoMemory > best.totalBytes)
        {
            best.dmlDevice = int (i);
            best.totalBytes = d.DedicatedVideoMemory;
            char name[128] = {};
            WideCharToMultiByte (CP_UTF8, 0, d.Description, -1, name, sizeof name - 1, nullptr, nullptr);
            best.name = name;
        }
        ad->Release();
    }
    factory->Release();
    return best;
}

struct VioletRenderer::Impl
{
    std::unique_ptr<Ort::Env> env;
    std::unique_ptr<Ort::Session> cond, core, dec;
    std::unique_ptr<Ort::MemoryInfo> cpu;

    // buffers reaproveitados entre janelas
    std::vector<float> midiRoll, techRoll, ccTokens, block32, final32;
    std::vector<uint16_t> block16, final16, x16, v16;
    std::vector<float> x, vc, vn, xn, latents;

    template <typename T>
    Ort::Value tensor (T* data, size_t count, std::initializer_list<int64_t> shape, ONNXTensorElementDataType type)
    {
        std::vector<int64_t> s (shape);
        return Ort::Value::CreateTensor (*cpu, (void*) data, count * sizeof (T), s.data(), s.size(), type);
    }

    void runCond (bool techPresent, bool ccPresent)
    {
        float techKeep = techPresent ? 1.0f : 0.0f, ccKeep = ccPresent ? 1.0f : 0.0f;  // w_tech = 1; CC1 quando há curva
        const char* inNames[] = { "midi_roll", "tech_roll", "tech_keep", "cc_tokens", "cc_keep" };
        const char* outNames[] = { "block_mod", "final_mod" };
        constexpr auto F = ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT;
        Ort::Value in[] = { tensor (midiRoll.data(), midiRoll.size(), { 1, kPitches, kRollFrames }, F),
                            tensor (techRoll.data(), techRoll.size(), { 1, kTechs, kRollFrames }, F),
                            tensor (&techKeep, 1, { 1, 1, 1 }, F),
                            tensor (ccTokens.data(), ccTokens.size(), { 1, kFrames, 1 }, F),
                            tensor (&ccKeep, 1, { 1, 1, 1 }, F) };
        auto out = cond->Run (Ort::RunOptions { nullptr }, inNames, in, 5, outNames, 2);
        const float* b = out[0].GetTensorData<float>();
        const float* f = out[1].GetTensorData<float>();
        block16.resize (size_t (kBlocks) * kFrames * kModDim);
        final16.resize (size_t (kFrames) * kFinalDim);
        for (size_t i = 0; i < block16.size(); ++i) block16[i] = toHalf (b[i]);
        for (size_t i = 0; i < final16.size(); ++i) final16[i] = toHalf (f[i]);
    }

    void velocity (const std::vector<float>& xin, float sigma, std::vector<float>& vout)
    {
        constexpr auto H = ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT16;
        x16.resize (xin.size());
        for (size_t i = 0; i < xin.size(); ++i) x16[i] = toHalf (xin[i]);
        uint16_t t = toHalf (sigma);
        const char* inNames[] = { "x", "t", "block_mod", "final_mod" };
        const char* outNames[] = { "v" };
        Ort::Value in[] = { tensor (x16.data(), x16.size(), { 1, kLatent, kFrames }, H),
                            tensor (&t, 1, { 1 }, H),
                            tensor (block16.data(), block16.size(), { kBlocks, 1, kFrames, kModDim }, H),
                            tensor (final16.data(), final16.size(), { 1, kFrames, kFinalDim }, H) };
        auto out = core->Run (Ort::RunOptions { nullptr }, inNames, in, 4, outNames, 1);
        const uint16_t* v = out[0].GetTensorData<uint16_t>();
        vout.resize (xin.size());
        for (size_t i = 0; i < vout.size(); ++i) vout[i] = fromHalf (v[i]);
    }

    void decode (std::vector<float>& audio)
    {
        const char* inNames[] = { "latents" };
        const char* outNames[] = { "wav" };
        Ort::Value in[] = { tensor (latents.data(), latents.size(), { 1, kLatent, kFrames }, ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT) };
        auto out = dec->Run (Ort::RunOptions { nullptr }, inNames, in, 1, outNames, 1);
        const float* w = out[0].GetTensorData<float>();
        audio.assign (w, w + kWindowSamples);
    }
};

VioletRenderer::VioletRenderer() : impl (std::make_unique<Impl>()), gpuInfo (pickGpu()) {}
VioletRenderer::~VioletRenderer() { unload(); }

bool VioletRenderer::load (const std::wstring& dllDir, const std::wstring& modelDir, std::string& error)
{
    if (loaded)
        return true;
    // Carrega as DLLs pelo caminho completo antes do primeiro uso (onnxruntime.dll é delay-load):
    // o Windows tem uma onnxruntime.dll antiga no System32, e o DAW não procura na pasta do plugin.
    static bool dllsReady = false;
    if (! dllsReady)
    {
        if (! LoadLibraryExW (join (dllDir, L"DirectML.dll").c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH)
            || ! LoadLibraryExW (join (dllDir, L"onnxruntime.dll").c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH))
        {
            error = "ONNX Runtime or DirectML not found next to the plugin";
            return false;
        }
        Ort::InitApi();
        dllsReady = true;
    }
    try
    {
        gpuInfo = pickGpu();
        impl->env = std::make_unique<Ort::Env> (ORT_LOGGING_LEVEL_ERROR, "violino");
        impl->cpu = std::make_unique<Ort::MemoryInfo> (Ort::MemoryInfo::CreateCpu (OrtArenaAllocator, OrtMemTypeDefault));
        Ort::SessionOptions so;
        so.DisableMemPattern();  // exigido pelo DirectML
        so.SetExecutionMode (ORT_SEQUENTIAL);
        so.SetGraphOptimizationLevel (GraphOptimizationLevel::ORT_ENABLE_ALL);
        Ort::ThrowOnError (OrtSessionOptionsAppendExecutionProvider_DML (so, gpuInfo.dmlDevice));
        impl->cond = std::make_unique<Ort::Session> (*impl->env, join (modelDir, L"violet_cond.onnx").c_str(), so);
        impl->core = std::make_unique<Ort::Session> (*impl->env, join (modelDir, L"violet_core_fp16.onnx").c_str(), so);
        impl->dec = std::make_unique<Ort::Session> (*impl->env, join (modelDir, L"dacvae_decode.onnx").c_str(), so);
    }
    catch (const std::exception& e)
    {
        error = e.what();
        unload();
        return false;
    }
    loaded = true;
    return true;
}

void VioletRenderer::unload()
{
    loaded = false;
    impl->cond.reset();
    impl->core.reset();
    impl->dec.reset();
    impl->cpu.reset();
    impl->env.reset();
    impl->block16 = {};
    impl->final16 = {};
}

uint64_t VioletRenderer::gpuBytesInUse() const
{
    uint64_t used = 0;
    IDXGIFactory1* factory = nullptr;
    if (FAILED (CreateDXGIFactory1 (__uuidof (IDXGIFactory1), (void**) &factory)))
        return 0;
    IDXGIAdapter1* ad = nullptr;
    if (factory->EnumAdapters1 (UINT (gpuInfo.dmlDevice), &ad) == S_OK)
    {
        IDXGIAdapter3* ad3 = nullptr;
        if (SUCCEEDED (ad->QueryInterface (__uuidof (IDXGIAdapter3), (void**) &ad3)))
        {
            DXGI_QUERY_VIDEO_MEMORY_INFO info {};
            if (SUCCEEDED (ad3->QueryVideoMemoryInfo (0, DXGI_MEMORY_SEGMENT_GROUP_LOCAL, &info)))
                used = info.CurrentUsage;
            ad3->Release();
        }
        ad->Release();
    }
    factory->Release();
    return used;
}

std::vector<float> VioletRenderer::render (const std::vector<VNote>& notes, int steps, uint64_t seed,
                                           const std::function<bool (float)>& progress, const std::vector<float>& cc25)
{
    if (! loaded || notes.empty())
        return {};
    auto& m = *impl;

    double lastEnd = 0;
    for (auto& n : notes) lastEnd = std::max (lastEnd, n.end);
    double eff = std::max (lastEnd + kTail, kWindowSec);
    const int winFrames = kFrames, stepFrames = int (kFrames * 0.5);
    int totalFrames = std::max (int (std::ceil (eff * kFrameRate)), winFrames);
    std::vector<int> positions;
    for (int c = 0; c + winFrames <= totalFrames; c += stepFrames) positions.push_back (c);
    if (positions.empty() || positions.back() + winFrames < totalFrames)
        positions.push_back (std::max (0, totalFrames - winFrames));

    std::vector<float> sigmas (size_t (std::max (steps, 1) + 1));  // N passos = N+1 sigmas de 1 a 0
    for (size_t i = 0; i < sigmas.size(); ++i) sigmas[i] = 1.0f - float (i) / float (sigmas.size() - 1);  // linspace(1, 0)
    const int evalsPerWindow = std::max (1, 2 * int (sigmas.size() - 1) - 1);
    int active = 0;
    for (int p : positions) active += activity (notes, p / kFrameRate) ? 1 : 0;
    const double totalEvals = std::max (1, active * evalsPerWindow);
    double done = 0;
    bool cancelled = false;
    auto tick = [&] { done += 1; if (progress && ! progress (float (std::min (done / totalEvals, 1.0)))) cancelled = true; };

    std::vector<std::vector<float>> windows;
    std::vector<size_t> startSamples;
    m.midiRoll.assign (size_t (kPitches) * kRollFrames, 0.f);
    m.techRoll.assign (size_t (kTechs) * kRollFrames, 0.f);
    m.ccTokens.assign (kFrames, 0.f);

    for (size_t w = 0; w < positions.size() && ! cancelled; ++w)
    {
        const double st = positions[w] / kFrameRate, en = st + kWindowSec;
        startSamples.push_back (size_t (std::lround (st * kSampleRate)));
        std::vector<float> audio (kWindowSamples, 0.0f);
        if (! activity (notes, st))
        {
            windows.push_back (std::move (audio));
            continue;
        }
        // rolos de notas e de técnica (build_cropped_binary_midi_roll / build_cropped_tech_roll)
        std::fill (m.midiRoll.begin(), m.midiRoll.end(), 0.f);
        std::fill (m.techRoll.begin(), m.techRoll.end(), 0.f);
        bool techPresent = false;
        for (auto& n : notes)
        {
            if (! playable (n)) continue;
            double on = std::max (n.start, st), off = std::min (n.end, en);
            if (off <= on) continue;
            int a = std::clamp (int (std::floor ((on - st) / kStep)), 0, kRollFrames);
            int b = std::clamp (int (std::ceil ((off - st) / kStep)), 0, kRollFrames);
            if (b <= a) continue;
            if (n.pitch <= kMaxPitch)
                std::fill_n (m.midiRoll.begin() + size_t (n.pitch - kMinPitch) * kRollFrames + a, b - a, 1.f);
            int tid = std::clamp (n.tech, 0, kTechs - 1);
            std::fill_n (m.techRoll.begin() + size_t (tid) * kRollFrames + a, b - a, 1.f);
            techPresent = true;
        }
        if (! cc25.empty())  // a fatia da curva de dinâmica desta janela (mesma taxa dos quadros: 25 Hz)
            for (int f = 0; f < kFrames; ++f)
                m.ccTokens[size_t (f)] = cc25[size_t (std::min (positions[w] + f, int (cc25.size()) - 1))];
        m.runCond (techPresent, ! cc25.empty());

        const double onsetRel = firstOnset (notes, st, kWindowSec);
        std::vector<float> best;
        float bestScore = -1;
        for (int attempt = 0; attempt < kAttempts && ! cancelled; ++attempt)
        {
            std::mt19937_64 rng (seed + uint64_t (w) * kSeedStride + uint64_t (attempt));
            std::normal_distribution<float> gauss;
            m.x.resize (size_t (kLatent) * kFrames);
            for (auto& v : m.x) v = sigmas[0] * gauss (rng);
            // Heun (ReflowEulerSampler com use_heun)
            for (size_t i = 0; i + 1 < sigmas.size() && ! cancelled; ++i)
            {
                float s = sigmas[i], sn = sigmas[i + 1], h = sn - s;
                m.velocity (m.x, s, m.vc);
                tick();
                m.xn.resize (m.x.size());
                for (size_t k = 0; k < m.x.size(); ++k) m.xn[k] = m.x[k] + h * m.vc[k];
                if (sn != 0.0f)
                {
                    m.velocity (m.xn, sn, m.vn);
                    tick();
                    for (size_t k = 0; k < m.x.size(); ++k) m.xn[k] = m.x[k] + 0.5f * h * (m.vc[k] + m.vn[k]);
                }
                std::swap (m.x, m.xn);
            }
            if (cancelled) break;
            m.latents = m.x;
            std::vector<float> take;
            m.decode (take);
            // diagnóstico de janela quase muda (render_window_diagnostics): tenta outra semente
            size_t edge = size_t (std::lround (kEdge * kSampleRate));
            size_t a = (onsetRel < 0 || onsetRel >= kEdge) ? edge : 0;
            float score = take.size() > a + edge ? peakRms (take.data() + a, take.size() - a - edge) : peakRms (take.data(), take.size());
            if (score > bestScore)
                bestScore = score, best = take;
            if (score >= kSilenceRms)
            {
                best = std::move (take);
                break;
            }
            done -= evalsPerWindow;  // nova tentativa: a barra não avança duas vezes
        }
        if (cancelled) break;
        edgeMask (best.data(), best.size(), onsetRel);
        windows.push_back (std::move (best));
    }
    if (cancelled)
        return {};

    // crossfade Hann (get_blending_weights) e máscara final
    const size_t N = kWindowSamples;
    size_t total = std::max (size_t (std::lround (eff * kSampleRate)), startSamples.back() + N);
    std::vector<double> sum (total, 0.0), wsum (total, 0.0);
    std::vector<float> hann (N);
    for (size_t i = 0; i < N; ++i) hann[i] = float (0.5 - 0.5 * std::cos (2.0 * 3.14159265358979323846 * double (i) / double (N - 1)));
    for (size_t w = 0; w < windows.size(); ++w)
    {
        for (size_t i = 0; i < N; ++i)
        {
            double wt = windows.size() == 1 ? 1.0 : hann[i];
            if (windows.size() > 1 && w == 0 && i < std::min (N, startSamples[1] - startSamples[0])) wt = 1.0;
            if (windows.size() > 1 && w + 1 == windows.size() && i >= std::min (N, startSamples[w - 1] + N - startSamples[w])) wt = 1.0;
            size_t k = startSamples[w] + i;
            if (k >= total) break;
            sum[k] += windows[w][i] * wt;
            wsum[k] += wt;
        }
    }
    std::vector<float> out (total);
    for (size_t i = 0; i < total; ++i) out[i] = float (sum[i] / std::max (wsum[i], 1e-8));
    double effLen = double (total) / kSampleRate;
    edgeMask (out.data(), out.size(), firstOnset (notes, 0.0, std::max (effLen, eff)));
    return out;
}
} // namespace violino
