// VIOLET em ONNX Runtime (DirectML): notas -> áudio seco a 48 kHz, sem Python.
//
// Mesma conta do src/inference/long_audio.py do VIOLET: janelas de 10 s com 50 % de sobreposição,
// rolos de notas (51 alturas) e de técnica (13 canais) a 10 ms, amostrador Heun de fluxo retificado,
// decodificador DACVAE, crossfade Hann e máscaras de silêncio nas bordas. A rede é dividida em
// violet_cond.onnx (só depende do MIDI: 1x por janela) e violet_core_fp16.onnx (cada passo).
#pragma once

#include "Articulator.h"

#include <atomic>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

namespace violino
{
struct GpuInfo
{
    int dmlDevice = 0;
    std::string name;
    uint64_t totalBytes = 0;
};

class VioletRenderer
{
public:
    static constexpr int kSampleRate = 48000;
    static constexpr int kFrames = 250, kRollFrames = 1000, kPitches = 51, kTechs = 13, kLatent = 128;
    static constexpr int kWindowSamples = 480000, kModDim = 4608, kFinalDim = 1536, kBlocks = 12;

    VioletRenderer();
    ~VioletRenderer();

    // dllDir: onde estão onnxruntime.dll e DirectML.dll; modelDir: os três .onnx
    bool load (const std::wstring& dllDir, const std::wstring& modelDir, std::string& error);
    void unload();
    bool isLoaded() const { return loaded.load(); }
    const GpuInfo& gpu() const { return gpuInfo; }
    uint64_t gpuBytesInUse() const;  // memória de vídeo usada por este processo

    // progress(fração) devolve false para cancelar; nesse caso o resultado vem vazio
    // cc25: CC1 (0..1) a 25 Hz desde o início do render; vazio = sem condicionamento de dinâmica
    std::vector<float> render (const std::vector<VNote>& notes, int steps, uint64_t seed,
                               const std::function<bool (float)>& progress, const std::vector<float>& cc25 = {});

private:
    struct Impl;
    std::unique_ptr<Impl> impl;
    std::atomic<bool> loaded { false };
    GpuInfo gpuInfo;
};

GpuInfo pickGpu();  // adaptador DXGI com mais memória dedicada (o DirectML usa o mesmo índice)
} // namespace violino
