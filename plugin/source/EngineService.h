// Motor de render compartilhado por todas as instâncias do plugin (um modelo na GPU por processo):
// fila de frases numa thread própria, carregar/descarregar o modelo, estado para a UI.
#pragma once

#include "Performer.h"

#include <juce_core/juce_core.h>

#include <deque>
#include <mutex>

struct Paths
{
    static juce::File dataDir();     // %LOCALAPPDATA%\Violino
    static juce::File modelDir();    // dataDir\models (ou a pasta de desenvolvimento)
    static juce::File sampleDir();   // dataDir\samples
    static juce::File pluginDir();   // pasta do binário do plugin (onde ficam as DLLs)
};

// Configurações de todas as instâncias (dataDir/settings.json): carregar ao abrir, escala da UI
struct Settings
{
    static juce::var get (const juce::String& key, const juce::var& fallback);
    static void set (const juce::String& key, const juce::var& value);
};

void appLog (const juce::String& message);  // dataDir/ui.log

class EngineService : private juce::Thread
{
public:
    struct Job
    {
        uint64_t id = 0;
        const void* owner = nullptr;
        std::vector<std::vector<violino::VNote>> voices;  // renderizadas separadas e somadas
        violino::Quality quality = violino::Quality::high;
        double fastShare = 0;
        int takes = 0;
        int steps = 0;  // 0 = o do nível de qualidade
        std::vector<float> cc25;  // dinâmica para o modelo (CC1 0..1, 25 Hz)
    };
    struct Result
    {
        uint64_t id = 0;
        violino::Take take;
        juce::String error;
    };
    struct Status
    {
        bool loaded = false, loading = false;
        juce::String error, gpu;
        uint64_t usedBytes = 0, totalBytes = 0;
        uint64_t current = 0;  // id renderizando agora (0 = nenhum)
        float progress = 0;
        int queued = 0;
    };

    EngineService();
    ~EngineService() override;

    void submit (Job job);
    void cancelOwner (const void* owner);
    bool isQueued (uint64_t id);
    bool popResult (const void* owner, Result& out);
    void requestLoad();
    void requestUnload();
    Status status();

private:
    void run() override;
    bool ensureLoaded();

    violino::VioletRenderer renderer;
    violino::Performer performer { renderer };
    std::mutex lock;
    std::deque<Job> queue;
    std::vector<std::pair<const void*, Result>> results;
    std::atomic<uint64_t> current { 0 }, cancelId { 0 };
    const void* currentOwner = nullptr;  // protegido por lock
    std::atomic<float> progress { 0 };
    std::atomic<bool> wantLoad { false }, wantUnload { false }, loading { false };
    juce::String lastError;
    juce::WaitableEvent wake;
};
