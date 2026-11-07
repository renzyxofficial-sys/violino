// Articulação e dinâmica automáticas (porte de auto_articulate.py: mesmas regras e constantes).
// Entrada: notas tocadas (com técnica do usuário opcional). Saída: notas prontas para o VIOLET
// (técnica por nota, motivo em inglês para a UI) + curva de dinâmica.
#pragma once

#include <string>
#include <vector>

namespace violino
{
enum class Tech
{
    automatic = -1,  // "auto": o algoritmo decide
    none = 0,        // canal "sem técnica" do VIOLET (modo gravação real)
    sustain = 1, tremolo, trillMajor, trillMinor, staccato, spiccato, ricochet, pizzicato, harmonic,
    legatoBow, legatoSlur, legatoPortamento  // 10..12 (ids do VIOLET)
};

const char* techName (Tech t);       // "sustain", "legato_slur"...
Tech techFromName (const std::string&);
bool isLegato (Tech t);

// Botões de articulação / keyswitches (forçam uma técnica em todas as notas)
enum class Forced { autoMode, sustain, legato, spiccato, staccato, pizzicato, tremolo, trill, portamento, harmonic };

enum class ArticMode { autoMode, autoDynamics, manual };
enum class PlayMode { legato, polyLegato, longNormal };

struct InNote
{
    double start = 0, end = 0;
    int pitch = 60, vel = 100;
    Tech user = Tech::automatic;     // técnica fixada nota a nota (keyswitch do VIOLET no MIDI, edição na UI)
    Forced forced = Forced::autoMode; // botão/keyswitch de articulação ativo quando a nota foi tocada
};

struct ArtNote
{
    double start = 0, end = 0;
    int pitch = 60, vel = 100;
    Tech tech = Tech::automatic;
    std::string reason;
    bool user = false;
    Forced forced = Forced::autoMode;
    int voice = 0;
    double dur() const { return end - start; }
};

struct ArticSettings
{
    ArticMode mode = ArticMode::autoMode;
    PlayMode play = PlayMode::legato;
    int portaVelocity = 45;   // nota ligada com velocity abaixo disto = portamento
    double legatoGap = 0.010; // notas a até isto (ou sobrepostas) são ligadas
};

struct Articulated
{
    std::vector<ArtNote> notes;          // na ordem do tempo (todas as vozes)
    std::vector<float> dynTimes, dynValues; // CC1 0..127 a cada 20 ms (modo Auto)
};

// Constantes do auto_articulate.py
constexpr int kMinPitch = 55, kMaxPitch = 105;
constexpr double kMinNote = 0.06, kOverlap = 0.03, kFast = 0.25, kShort = 0.15, kTrillNote = 0.13, kCcFrame = 0.02;

Articulated articulate (const std::vector<InNote>& in, const ArticSettings& s);

// Notas do VIOLET: técnica numérica e fim estendido nas ligaduras (legato = notas sobrepostas)
struct VNote
{
    double start, end;
    int pitch, tech;
};
std::vector<VNote> toViolet (const std::vector<ArtNote>& voiceNotes, double gap = 0.010);

std::string summary (const std::vector<ArtNote>&);
} // namespace violino
