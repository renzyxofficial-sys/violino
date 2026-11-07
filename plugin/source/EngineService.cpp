#include "EngineService.h"

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

juce::File Paths::dataDir()
{
    auto local = juce::SystemStats::getEnvironmentVariable ("LOCALAPPDATA", {});
    auto dir = local.isNotEmpty() ? juce::File (local) : juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory);
    return dir.getChildFile ("Violino");
}

// Conteúdo (modelos e samples): dentro do pacote do plugin (Contents/Resources), senão na pasta de dados,
// senão nas pastas do projeto (desenvolvimento). O pacote é o único lugar que todo DAW sempre enxerga.
static juce::File findContent (const char* sub, const char* marker, const juce::File& devDir)
{
    const juce::File candidates[] = { Paths::pluginDir().getParentDirectory().getChildFile ("Resources").getChildFile (sub),
                                      Paths::dataDir().getChildFile (sub), devDir };
    for (auto& d : candidates)
        if (d.getChildFile (marker).existsAsFile())
            return d;
    return candidates[0];
}

juce::File Paths::modelDir()
{
    return findContent ("models", "violet_core_fp16.onnx", juce::File::getSpecialLocation (juce::File::userHomeDirectory).getChildFile ("violino/onnx"));
}

juce::File Paths::sampleDir()
{
    return findContent ("samples", "samples.json", juce::File::getSpecialLocation (juce::File::userHomeDirectory).getChildFile ("violino/plugin/resources/samples"));
}

static juce::CriticalSection settingsLock;

juce::var Settings::get (const juce::String& key, const juce::var& fallback)
{
    const juce::ScopedLock sl (settingsLock);
    auto v = juce::JSON::parse (Paths::dataDir().getChildFile ("settings.json"));
    return v.hasProperty (key) ? v[juce::Identifier (key)] : fallback;
}

void Settings::set (const juce::String& key, const juce::var& value)
{
    const juce::ScopedLock sl (settingsLock);
    auto file = Paths::dataDir().getChildFile ("settings.json");
    auto v = juce::JSON::parse (file);
    if (! v.isObject()) v = juce::var (new juce::DynamicObject());
    v.getDynamicObject()->setProperty (key, value);
    file.getParentDirectory().createDirectory();
    file.replaceWithText (juce::JSON::toString (v));
}

void appLog (const juce::String& message)
{
    static juce::CriticalSection logLock;
    const juce::ScopedLock sl (logLock);
    auto f = Paths::dataDir().getChildFile ("ui.log");
    if (f.getSize() > (1 << 20)) f.deleteFile();
    f.getParentDirectory().createDirectory();
    f.appendText (juce::Time::getCurrentTime().toString (true, true) + "  " + message + juce::newLine);
}

juce::File Paths::pluginDir()
{
    HMODULE mod = nullptr;
    GetModuleHandleExW (GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                        reinterpret_cast<LPCWSTR> (&Paths::pluginDir), &mod);
    wchar_t path[MAX_PATH] = {};
    GetModuleFileNameW (mod, path, MAX_PATH);
    return juce::File (juce::String (path)).getParentDirectory();
}

EngineService::EngineService() : juce::Thread ("Violino Engine")
{
    startThread (juce::Thread::Priority::normal);
}

EngineService::~EngineService()
{
    signalThreadShouldExit();
    cancelId = ~uint64_t (0);
    wake.signal();
    stopThread (30000);
}

void EngineService::submit (Job job)
{
    {
        std::lock_guard<std::mutex> g (lock);
        for (auto& j : queue)
            if (j.id == job.id)
                return;
        if (current == job.id)
            return;
        queue.push_back (std::move (job));
    }
    wake.signal();
}

void EngineService::cancelOwner (const void* owner)
{
    std::lock_guard<std::mutex> g (lock);
    queue.erase (std::remove_if (queue.begin(), queue.end(), [&] (auto& j) { return j.owner == owner; }), queue.end());
    results.erase (std::remove_if (results.begin(), results.end(), [&] (auto& r) { return r.first == owner; }), results.end());
    if (currentOwner == owner)
        cancelId = current.load();
}

bool EngineService::isQueued (uint64_t id)
{
    std::lock_guard<std::mutex> g (lock);
    if (current == id)
        return true;
    for (auto& j : queue)
        if (j.id == id)
            return true;
    return false;
}

bool EngineService::popResult (const void* owner, Result& out)
{
    std::lock_guard<std::mutex> g (lock);
    for (auto it = results.begin(); it != results.end(); ++it)
        if (it->first == owner)
        {
            out = std::move (it->second);
            results.erase (it);
            return true;
        }
    return false;
}

void EngineService::requestLoad() { wantLoad = true, wake.signal(); }
void EngineService::requestUnload() { wantUnload = true, cancelId = current.load(), wake.signal(); }

EngineService::Status EngineService::status()
{
    Status s;
    s.loaded = renderer.isLoaded();
    s.loading = loading;
    s.gpu = renderer.gpu().name;
    s.totalBytes = renderer.gpu().totalBytes;
    s.usedBytes = s.loaded ? renderer.gpuBytesInUse() : 0;
    s.current = current;
    s.progress = progress;
    std::lock_guard<std::mutex> g (lock);
    s.queued = int (queue.size());
    s.error = lastError;
    return s;
}

bool EngineService::ensureLoaded()
{
    if (renderer.isLoaded())
        return true;
    loading = true;
    std::string err;
    bool ok = renderer.load (Paths::pluginDir().getFullPathName().toWideCharPointer(),
                             Paths::modelDir().getFullPathName().toWideCharPointer(), err);
    loading = false;
    std::lock_guard<std::mutex> g (lock);
    lastError = ok ? juce::String() : juce::String (err);
    return ok;
}

void EngineService::run()
{
    while (! threadShouldExit())
    {
        if (wantUnload.exchange (false))
            renderer.unload();
        if (wantLoad.exchange (false))
            ensureLoaded();
        Job job;
        {
            std::lock_guard<std::mutex> g (lock);
            if (! queue.empty())
            {
                job = std::move (queue.front());
                queue.pop_front();
                current = job.id;
                currentOwner = job.owner;
            }
        }
        if (job.id == 0)
        {
            wake.wait (500);
            continue;
        }
        Result r;
        r.id = job.id;
        progress = 0;
        if (ensureLoaded())
        {
            const float nv = float (std::max<size_t> (1, job.voices.size()));
            for (size_t v = 0; v < job.voices.size() && r.error.isEmpty(); ++v)
            {
                auto take = performer.perform (job.voices[v], job.quality, job.fastShare, 1234 + job.id % 100000 + v * 104729,
                                               [this, id = job.id, v, nv] (float f) { progress = (float (v) + f) / nv; return cancelId != id && ! threadShouldExit(); },
                                               job.takes, job.steps, job.cc25);
                if (take.audio.empty())
                {
                    r.error = "cancelled";
                    break;
                }
                if (v == 0)
                    r.take = std::move (take);
                else
                {
                    // soma a segunda voz (cordas duplas), com um pouco menos de ganho para não estourar
                    r.take.audio.resize (std::max (r.take.audio.size(), take.audio.size()), 0.0f);
                    for (size_t i = 0; i < take.audio.size(); ++i) r.take.audio[i] = 0.8f * (r.take.audio[i] + take.audio[i]);
                    for (size_t i = take.audio.size(); i < r.take.audio.size(); ++i) r.take.audio[i] *= 0.8f;
                    r.take.accuracy = 0.5 * (r.take.accuracy + take.accuracy);
                }
            }
        }
        else
            r.error = lastError;
        {
            std::lock_guard<std::mutex> g (lock);
            if (cancelId != job.id)
                results.push_back ({ job.owner, std::move (r) });
            current = 0;
            currentOwner = nullptr;
            cancelId = 0;
        }
        progress = 0;
    }
    renderer.unload();
}
