// Preview em tempo real: violino solo seco (VSCO 2 CE, CC0), para tocar sem esperar a IA.
// Camadas p/f com crossfade pela dinâmica, round robin nas curtas, legato por crossfade e deslize,
// trilo por alternância de altura, harmônico como sustain filtrado. Sem alocação no áudio.
#pragma once

#include "Articulator.h"

#include <juce_audio_formats/juce_audio_formats.h>

#include <array>
#include <atomic>
#include <vector>

class PreviewSampler
{
public:
    enum Set { sustainSet, spiccatoSet, pizzicatoSet, tremoloSet, numSets };

    bool load (const juce::File& dir, juce::String& error);  // samples.json + FLACs (thread de fundo)
    bool isLoaded() const { return loaded; }
    int sampleCount() const { return count; }
    void prepare (double sampleRate);

    struct Live
    {
        violino::PlayMode play = violino::PlayMode::legato;
        violino::Forced forced = violino::Forced::autoMode;
        bool dynamicsFromCc = false;  // Auto + Dynamics / Manual: CC1 manda na dinâmica
        int portaVelocity = 45;
        float intensity = 0.7f;       // quanto a dinâmica muda o volume
        float levelDb = 0;
    };
    void setLive (const Live& l) { live = l; }
    void noteOn (int pitch, int velocity, double timeSec);
    void noteOff (int pitch, double timeSec);
    void setModWheel (int value) { cc1 = value; }
    void setPitchBend (float semitones) { bend = semitones; }
    void allNotesOff();
    void render (float* out, int numSamples);  // soma no buffer mono

private:
    struct Sample
    {
        int root = 60, layer = 0, rr = 1;
        std::vector<int16_t> data;
    };
    struct Voice
    {
        bool active = false, releasing = false, held = false;
        int pitch = 0, set = 0, vel = 100;
        const Sample* p = nullptr;
        const Sample* f = nullptr;
        double pos = 0, inc = 1, incTarget = 1, glide = 1;  // glide: fator por amostra até o alvo
        float env = 0, envStep = 0, envTarget = 1;
        float lpState = 0, lpCoef = 1;        // harmônico: passa-baixas
        double trillPhase = 0, trillRate = 0; // trilo: alterna incTrill / inc
        double trillRatio = 1;
        int age = 0;
    };

    const Sample* pick (int set, int pitch, int layer, bool roundRobin);
    Voice& freeVoice();
    void startVoice (Voice& v, int pitch, int set, double startPos, float fadeSec);
    float layerX (int velocity) const;
    double rateFor (int pitch, const Sample* s) const;

    std::array<std::vector<Sample>, numSets> sets;
    std::array<Voice, 24> voices;
    std::atomic<bool> loaded { false };
    std::atomic<int> count { 0 };
    double hostRate = 48000, fileRate = 44100;
    Live live;
    int cc1 = 90, lastVelocity = 100, counter = 0, rrFlip = 0;
    float bend = 0;
    double lastOnTime = -10, lastOffTime = -10;
    int lastPitch = -1;
};
