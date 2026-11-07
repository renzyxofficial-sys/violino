// Do MIDI articulado ao take final: N candidatos do VIOLET, escolha do melhor e compensação de atraso
// (porte de violino.py: pick_best + note_accuracy.py, com YIN no lugar do pYIN).
#pragma once

#include "VioletRenderer.h"

namespace violino
{
enum class Quality { low, medium, high, extreme };

struct QualityInfo
{
    int steps;
    int takes;  // 0 = 1 take, ou 4 se a frase tem muitas notas rápidas
};
QualityInfo qualityInfo (Quality q);

struct Take
{
    std::vector<float> audio;  // 48 kHz mono, já compensado (lag > 0 cortado do início)
    double accuracy = 0, lag = 0, air = 0;
    int takesTried = 0;
};

// Notas para a contagem de "notas certas": as do VIOLET (fim estendido), pitch >= 55
double noteAccuracy (const std::vector<float>& audio48k, const std::vector<VNote>& notes, double shift);
double airLevel (const std::vector<float>& audio48k);  // energia 8–16 kHz relativa ao total (dB)

class Performer
{
public:
    explicit Performer (VioletRenderer& r) : renderer (r) {}

    // fastShare = fração de notas <= 0,25 s (decide 1 ou 4 takes nos níveis sem take fixo)
    Take perform (const std::vector<VNote>& notes, Quality q, double fastShare, uint64_t seed,
                  const std::function<bool (float)>& progress, int takesOverride = 0, int stepsOverride = 0,
                  const std::vector<float>& cc25 = {});

private:
    VioletRenderer& renderer;
};
} // namespace violino
