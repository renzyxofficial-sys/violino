// O plugin: você toca e ouve o preview na hora; a frase é capturada com o tempo do DAW, a IA
// renderiza, e no playback o render toca no lugar do preview, alinhado ao playhead.
#pragma once

#include <thread>
#include "EngineService.h"
#include "MixFx.h"
#include "PreviewSampler.h"

#include <juce_audio_processors/juce_audio_processors.h>
#include <juce_audio_utils/juce_audio_utils.h>

#include <map>
#include <set>
#include <thread>

class ViolinoProcessor : public juce::AudioProcessor, private juce::Timer
{
public:
    ViolinoProcessor();
    ~ViolinoProcessor() override;

    void prepareToPlay (double sampleRate, int blockSize) override;
    void releaseResources() override {}
    bool isBusesLayoutSupported (const BusesLayout&) const override;
    void processBlock (juce::AudioBuffer<float>&, juce::MidiBuffer&) override;

    juce::AudioProcessorEditor* createEditor() override;
    bool hasEditor() const override { return true; }
    const juce::String getName() const override { return JucePlugin_Name; }
    bool acceptsMidi() const override { return true; }
    bool producesMidi() const override { return false; }
    double getTailLengthSeconds() const override { return 4.0; }
    int getNumPrograms() override { return 1; }
    int getCurrentProgram() override { return 0; }
    void setCurrentProgram (int) override {}
    const juce::String getProgramName (int) override { return {}; }
    void changeProgramName (int, const juce::String&) override {}
    void getStateInformation (juce::MemoryBlock&) override;
    void setStateInformation (const void*, int) override;

    // ---- interface (thread de mensagens)
    juce::var buildUiState();
    void handleUiCommand (const juce::var& cmd);
    void handleUiCommandImpl (const juce::var& cmd);
    bool exportWav (const juce::File& file, juce::String& error);
    std::function<void()> onExportRequested;
    std::function<void()> onImportRequested;  // Import MIDI: o editor abre o seletor de arquivo
    bool importMidi (const juce::File& file, juce::String& error);
    std::function<void (const juce::File&)> onDragRequested;  // arrastar a frase para o DAW
    std::function<void()> onScaleChanged;

    juce::AudioProcessorValueTreeState params;
    juce::var uiPrefs { new juce::DynamicObject() };  // tema, aba (salvos com o projeto)

private:
    // eventos do áudio para a thread de mensagens (fila sem lock)
    struct Event
    {
        enum Type : uint8_t { noteOn, noteOff, forced, transportStart, transportStop, cc } type;
        uint8_t a = 0, b = 0;
        bool matched = false, capturable = false;
        double time = 0;
    };
    struct CapNote
    {
        double start, end;
        int pitch, vel;
        violino::Forced forced;
        int pass;
        bool open;
        juce::String take;  // nome do take (o usuário renomeia; vai junto com as notas)
    };
    struct Phrase
    {
        double start = 0, end = 0, origin = 0;
        std::vector<size_t> idx;
        std::vector<std::pair<double, int>> starts;  // (início, altura) das notas tocadas
        std::vector<std::pair<double, float>> target; // dinâmica pedida (CC 0..127) a cada 20 ms, tempo absoluto
        uint64_t hash = 0, content = 0;  // content: só notas/técnicas (antes a qualidade entrava no hash)
        violino::Articulated art;   // tempos relativos à origem
        std::vector<std::vector<violino::VNote>> voices;  // 1 (Legato) ou 2 (cordas duplas)
        double fastShare = 0;
        bool open = false;
    };
    struct Rendered
    {
        std::vector<float> audio;  // 48 kHz
        double accuracy = 0;
        juce::Array<juce::var> peaks;  // forma de onda para a UI: pico a cada 50 ms (0..100)
    };
    struct Clip
    {
        double origin = 0, first = 0, last = 0;
        uint64_t dynKey = 0;
        std::vector<float> audio;                 // na taxa do host (já com a dinâmica aplicada)
        std::vector<std::pair<double, int>> notes; // (início, altura), para silenciar o preview
    };
    using ClipSet = std::vector<std::shared_ptr<const Clip>>;
    using DynSet = std::vector<std::shared_ptr<const std::vector<std::pair<double, float>>>>;
    struct CcPoint
    {
        double time;
        int value, pass;
    };
    std::vector<float> shapeDynamics (const Phrase& p, const std::vector<float>& audio48) const;
    uint64_t dynKey (const Phrase& p) const;

    void timerCallback() override;
    void pushEvent (const Event& e);
    void drainEvents();
    void rebuildPhrases();
    void rebuildClips();
    void submit (const Phrase& p);
    bool matchesClip (const ClipSet& clips, double t, int pitch) const;
    violino::ArticSettings articSettings() const;
    violino::MixSettings mixSettings() const;
    int choice (const char* id) const;
    float value (const char* id) const;
    bool flag (const char* id) const;
    void setParam (const char* id, float plainValue);
    juce::File cacheFile (uint64_t hash) const;

    juce::SharedResourcePointer<EngineService> engine;
    PreviewSampler sampler;
    violino::MixFx fx;
    juce::MidiMessageCollector uiMidi;
    juce::AudioBuffer<float> mono;
    double sampleRate = 48000;

    // áudio -> mensagens
    juce::AbstractFifo fifo { 4096 };
    std::array<Event, 4096> events;
    std::atomic<double> playheadSec { 0 };
    std::atomic<bool> playing { false }, hostTransport { false };
    std::atomic<int> modWheel { 0 }, pitchWheel { 8192 };
    std::atomic<float> meterL { 0 }, meterR { 0 };
    std::atomic<bool> renderAudible { false };
    std::array<std::atomic<uint64_t>, 2> pressed {};
    std::atomic<int> auditionIndex { -1 };
    std::atomic<double> auditionPos { 0 };
    std::atomic<double> hostBpm { 120 };
    std::atomic<bool> timelinePlay { false };  // Play interno (sem o DAW)
    std::atomic<double> timelinePos { 0 };
    double playStart = 0;  // onde o play começou (o clique na régua): parar volta para cá

    // estado do áudio
    bool wasPlaying = false;
    double lastBlockTime = 0, internalClock = 0;
    std::array<bool, 128> mutedNote {};
    violino::Forced liveForced = violino::Forced::autoMode;
    bool ksPending = false;
    violino::Forced lastParamForced = violino::Forced::autoMode;
    double liveClock = 0;
    std::set<uint64_t> stopped;  // frases paradas pelo usuário (Stop): o Autorender não reenvia
    std::atomic<std::shared_ptr<const ClipSet>> clips;
    std::vector<std::shared_ptr<const ClipSet>> retired;  // libera fora da thread de áudio
    std::atomic<std::shared_ptr<const DynSet>> dynCurves;
    std::vector<std::shared_ptr<const DynSet>> retiredDyn;
    std::vector<CcPoint> ccCurve;  // CC1 capturado (Auto + Dynamics)
    std::vector<double> splits;    // pontos de split de take (o usuário corta uma frase em duas)
    std::map<long long, double> fades;  // fade in por frase (chave: início da frase em ms)
    std::map<long long, double> fadeTension;  // curvatura do fade (-1..1, 0,5 = quadrática)
    std::vector<std::pair<double, float>> dynDrawn;  // dinâmica desenhada com o lápis (tempo, CC)
    void applyFade (const Phrase& p, std::vector<float>& audio48) const;
    void applyVibrato (const Phrase& p, std::vector<float>& audio48) const;  // vibrato extra nas notas longas
    std::vector<float> levelNotes (const Phrase& p, const std::vector<float>& audio48) const;  // nota a nota perto da mediana
    double styleVibrato() const;    // quanto o Playstyle soma ao vibrato (%)
    float styleIntensity() const;   // quanto o Playstyle escala a dinâmica
    double ccPassTime = -1;
    uint64_t dynSettings = 0;

    // estado da captura (thread de mensagens)
    std::vector<CapNote> notes;
    std::map<int, size_t> openNote;
    std::vector<Phrase> phrases;
    std::map<uint64_t, Rendered> cache;
    std::map<uint64_t, std::shared_ptr<const Clip>> clipCache;
    std::map<uint64_t, std::pair<double, double>> renderedRegions;  // hash -> (início, fim), para "Outdated"
    int pass = 0;
    bool passActive = false, passHasNotes = false, dirty = false;
    double passStart = 0;
    juce::String lastError;
    uint64_t settingsHash = 0;
    std::atomic<int> sampleState { 0 };  // 0 parado, 1 carregando, 2 pronto, 3 erro
    juce::String sampleError;
    juce::CriticalSection sampleLock;
    int auditionPhrase = -1;
    void startSampleLoad();
    void loadSamplesNow();
    static juce::Array<juce::var> peaksOf (const std::vector<float>& audio);
    bool writeWav (const juce::File& file, int phrase, juce::String& error);  // phrase -1 = tudo
    bool buildMix (int phrase, std::vector<float>& monoOut, juce::String& error) const;  // thread de mensagens
    static bool renderMixFile (std::vector<float> monoOut, const violino::MixSettings& ms, const juce::File& file, juce::String& error);
    uint64_t mixSignature() const;
    juce::File allMixFile (uint64_t sig) const;
    std::thread allThread;
    std::atomic<bool> allBusy { false };
    std::atomic<uint64_t> allReadySig { 0 };
    uint64_t allPendingSig = 0;
    double allPendingSince = 0;
    // desfazer / refazer (edições da timeline)
    struct EditSnap
    {
        std::vector<CapNote> notes;
        std::vector<double> splits;
        std::map<long long, double> fades, fadeTension;
        std::vector<std::pair<double, float>> dynDrawn;
    };
    std::vector<EditSnap> undoStack, redoStack;
    EditSnap snapshot() const { return { notes, splits, fades, fadeTension, dynDrawn }; }
    void restore (EditSnap s);
    std::vector<uint64_t> legacyHashes (const Phrase& p) const;  // nomes antigos (com qualidade/steps) do mesmo render
    static bool sameSnap (const EditSnap& a, const EditSnap& b);
    void pushUndo (EditSnap s);
    double lastCaptureEdit = 0;
    // Play interno: notas sem render tocam no preview; metrônomo do Standalone
    struct PNote { double start, end; int pitch, vel; violino::Forced forced; };
    std::atomic<std::shared_ptr<const std::vector<PNote>>> previewNotes;
    std::vector<std::shared_ptr<const std::vector<PNote>>> retiredPreview;
    bool wasTimeline = false;
    std::atomic<bool> metroOn { false };
    std::atomic<bool> cycleOn { false };          // Cycle: o Play interno volta de cycleB para cycleA
    std::atomic<double> cycleA { 0 }, cycleB { 0 };
    long long metroBeat = 0;
    int metroLeft = 0, metroT = 0;
    bool metroAccent = false;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (ViolinoProcessor)
};
