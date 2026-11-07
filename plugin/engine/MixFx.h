// Efeitos de saída em tempo real (mono -> estéreo). Duas partes:
//  - Mix Styles (porte de mixer.py): EQ, compressor, fita, sala FDN, largura e EQ de bus calibrados.
//  - Módulos do usuário (aba Effects): EQ paramétrico de 5 bandas, Compressor, Saturation (8 curvas),
//    Chorus, Stereo, Delay (Stereo/Ping Pong/Mid-Side; Digital/Tape/Analog) e Reverb (9 modos, 3 cores).
// Sem alocação no processamento: prepare() reserva tudo; set() pode rodar na thread de áudio.
#pragma once

#include <array>
#include <atomic>
#include <cstdint>
#include <vector>

namespace violino
{
enum class MixStyle { dry, lyrical, romantic, baroque, cinematic };
enum class Room { room, chamber, concertHall, scoringStage, cathedral };

struct Biquad
{
    double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0, z1 = 0, z2 = 0;
    enum Kind { peak, highpass, lowpass, highShelf, lowShelf, allpass };
    void set (Kind k, double f, double gainDb, double q, double sr);
    float process (float x)
    {
        double y = b0 * x + z1;
        z1 = b1 * x - a1 * y + z2;
        z2 = b2 * x - a2 * y;
        return float (y);
    }
    void reset() { z1 = z2 = 0; }
};

// Reverb: FDN de 8 linhas (Householder), reflexões iniciais, difusor de entrada, difusão tardia por
// linha, absorção em 3 faixas (grave / médio / agudo) e modulação das linhas.
struct ReverbParams
{
    double decay = 2.4, bassMult = 1.6, bassFreq = 300, highFreq = 4000, highShelfDb = -4;
    double size = 1.0, earlyDiff = 0.7, lateDiff = 0.0, attack = 0.5, modRate = 0, modDepth = 0;
    double predelay = 0.022, erLen = 0.06, erGain = 0.35;
};

class FdnReverb
{
public:
    void prepare (double sampleRate);
    void configure (const ReverbParams& p);  // sem alocar
    void process (float in, float& outL, float& outR);
    void reset();

private:
    static constexpr int kLines = 8;
    double sr = 48000;
    std::vector<float> pre;
    size_t preLen = 1, prePos = 0;
    std::array<std::vector<float>, 4> ap;
    std::array<size_t, 4> apLen {}, apPos {};
    float apG = 0.7f;
    std::array<std::vector<float>, kLines> line, lap;  // linha e all-pass tardio de cada linha
    std::array<size_t, kLines> lapLen {}, lapPos {};
    std::array<double, kLines> delay {}, gLow {}, gMid {}, gHigh {}, lowState {}, highState {};
    size_t writePos = 0, bufLen = 1;
    double cLow = 0, cHigh = 0, lateG = 0, modDepthSmp = 0, modInc = 0, modPhase = 0;
    std::array<float, kLines> signL {}, signR {};
    std::vector<float> erBuf;
    size_t erPos = 0;
    std::array<size_t, 12> erTap {};
    std::array<float, 12> erGain {};
};

struct EqBand
{
    bool on = true;
    int type = 2;  // 0 Low Cut, 1 Low Shelf, 2 Bell, 3 High Shelf, 4 High Cut
    float freq = 1000, gain = 0, q = 0.71f;
    bool operator== (const EqBand&) const = default;
};

struct MixSettings
{
    MixStyle style = MixStyle::dry;
    bool eqOn = true;
    std::array<EqBand, 5> eq {};
    bool compOn = false;
    float compThresh = -18, compRatio = 3, compAttackMs = 15, compReleaseMs = 150, compMakeup = 3;
    bool satOn = false;
    int satType = 0;
    float satDriveDb = 6, satOutputDb = 0, satMix = 1;
    bool chorusOn = false;
    float chorusRate = 0.6f, chorusDepth = 0.3f, chorusMix = 0.25f;
    bool stereoOn = true;
    float stereoWidth = 0.5f;
    bool delayOn = false;
    int delayMode = 1, delayChar = 0;  // modo: 0 Stereo, 1 Ping Pong, 2 Mid/Side; caráter: 0 Digital, 1 Tape, 2 Analog
    float delayLeftMs = 375, delayRightMs = 250, delayFeedback = 0.4f, delayHp = 50, delayLp = 5000, delayMod = 0.2f, delayMix = 0.14f;
    bool reverbOn = false;
    int revColor = 0;  // 0 1970s, 1 1980s, 2 Now
    float reverbMix = 0.3f, predelayMs = 20, revDecay = 4, revHighFreq = 6000, revHighShelf = -6, revBassFreq = 300, revBassMult = 1.5f;
    float revSize = 1, revAttack = 0.5f, revEarly = 1, revLate = 1, revModRate = 2.5f, revModDepth = 0.38f, revHighCut = 8000, revLowCut = 10;
    bool revFreeze = false;
    float revDucking = 0;
    float outputDb = 0;
    bool operator== (const MixSettings&) const = default;
};

float saturate (int type, float x);  // as 8 curvas (a UI desenha as mesmas)

class MixFx
{
public:
    void prepare (double sampleRate);
    void set (const MixSettings& s);
    void process (const float* mono, float* left, float* right, int n);
    void reset();
    float gainReductionDb() const { return grDb.load(); }

private:
    void rebuild();
    double sr = 48000;
    MixSettings cur;
    bool built = false;

    // Mix Style
    FdnReverb styleVerb, userVerb;
    std::vector<Biquad> pre;
    std::array<std::vector<Biquad>, 2> bus;
    Biquad sendHp, sendLp;
    std::array<Biquad, 2> userSendHp, userSendLp;
    bool styleOn = false, styleComp = false;
    float wet = 0, drive = 0, width = 1, styleTail = 1, userTail = 1;
    double compThresh = 0, compRatio = 1, compAtk = 0, compRel = 0, env = 0, envC = 0, gainDb = 0, makeup = 0;

    // módulos do usuário
    std::array<std::array<Biquad, 2>, 5> eq, eq2;  // por banda (L, R); cortes usam duas seções (24 dB/oit)
    std::array<bool, 5> eqActive {}, eqDouble {};
    struct Comp
    {
        double thresh = -18, ratio = 3, atk = 0, rel = 0, env = 0, envC = 0, gain = 0, makeup = 0;
        float process (float x);
    } userComp;
    std::atomic<float> grDb { 0 };
    std::array<Biquad, 4> deco;
    std::vector<float> chorusBuf, dlyL, dlyR;
    size_t chorusPos = 0, dlyPos = 0;
    double chorusPhase = 0, dlyPhase = 0, dlyLenL = 1, dlyLenR = 1;
    std::array<Biquad, 2> dlyHp, dlyLp;
    float dlyLpState[2] = { 0, 0 };
    double duckEnv = 0;
    float outGain = 1;
};
} // namespace violino
