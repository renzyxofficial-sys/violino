// violino_cli: MIDI -> WAV com o motor nativo (mesmo fluxo do violino.py, sem Python nem WSL).
//   violino_cli entrada.mid saida.wav [--quality low|medium|high|extreme] [--mix dry|lyrical|romantic|baroque|cinematic]
//                                     [--takes N] [--report tecnicas.csv]
#include "Articulator.h"
#include "MixFx.h"
#include "Performer.h"

#include <juce_audio_formats/juce_audio_formats.h>

#include <chrono>
#include <iostream>
#include <map>

using namespace violino;

static std::wstring exeDir()
{
    return juce::File::getSpecialLocation (juce::File::currentExecutableFile).getParentDirectory().getFullPathName().toWideCharPointer();
}

int main (int argc, char* argv[])
{
    if (argc < 3)
    {
        std::cout << "uso: violino_cli entrada.mid saida.wav [--quality high] [--mix dry] [--takes N] [--report x.csv] [--models pasta]\n";
        return 1;
    }
    juce::File in (juce::File::getCurrentWorkingDirectory().getChildFile (argv[1]));
    juce::File out (juce::File::getCurrentWorkingDirectory().getChildFile (argv[2]));
    std::map<std::string, std::string> opt { { "--quality", "high" }, { "--mix", "dry" }, { "--takes", "0" },
                                             { "--models", juce::File::getSpecialLocation (juce::File::userApplicationDataDirectory).getChildFile ("Violino/models").getFullPathName().toStdString() } };
    for (int i = 3; i + 1 < argc; i += 2) opt[argv[i]] = argv[i + 1];

    // MIDI: notas >= 55 tocam; keyswitches (notas do mapa do VIOLET) valem para a nota seguinte
    juce::FileInputStream fs (in);
    juce::MidiFile mf;
    if (! fs.openedOk() || ! mf.readFrom (fs))
    {
        std::cerr << "não consegui ler " << argv[1] << "\n";
        return 1;
    }
    mf.convertTimestampTicksToSeconds();
    const std::map<int, Tech> ks { { 36, Tech::sustain }, { 37, Tech::tremolo }, { 38, Tech::trillMajor }, { 39, Tech::trillMinor },
                                   { 40, Tech::staccato }, { 41, Tech::spiccato }, { 42, Tech::ricochet }, { 43, Tech::pizzicato },
                                   { 44, Tech::harmonic }, { 48, Tech::legatoBow }, { 49, Tech::legatoSlur }, { 50, Tech::legatoPortamento } };
    std::vector<InNote> notes;
    std::vector<std::pair<double, Tech>> switches;
    for (int t = 0; t < mf.getNumTracks(); ++t)
    {
        juce::MidiMessageSequence seq (*mf.getTrack (t));
        seq.updateMatchedPairs();
        for (auto* e : seq)
        {
            if (! e->message.isNoteOn()) continue;
            double s = e->message.getTimeStamp(), en = e->noteOffObject ? e->noteOffObject->message.getTimeStamp() : s + 0.2;
            int p = e->message.getNoteNumber();
            if (p < kMinPitch)
            {
                if (auto it = ks.find (p); it != ks.end()) switches.push_back ({ s, it->second });
                continue;
            }
            notes.push_back ({ s, en, p, e->message.getVelocity(), Tech::automatic });
        }
    }
    std::sort (notes.begin(), notes.end(), [] (auto& a, auto& b) { return a.start < b.start; });
    for (auto [t, tech] : switches)
        for (auto& n : notes)
            if (n.start - t >= -0.02 && n.start - t <= 0.03) { n.user = tech; break; }

    auto t0 = std::chrono::steady_clock::now();
    ArticSettings as;
    auto art = articulate (notes, as);
    auto vnotes = toViolet (art.notes);
    double fast = 0;
    for (auto& n : art.notes) fast += n.dur() <= kFast ? 1 : 0;
    fast /= std::max<size_t> (1, art.notes.size());
    std::cout << "[1/3] " << art.notes.size() << " notas | " << summary (art.notes) << "\n";
    if (opt.count ("--report"))
    {
        juce::File rep (juce::File::getCurrentWorkingDirectory().getChildFile (opt["--report"]));
        juce::String csv = "idx,start_s,pitch,length_ms,technique,reason\n";
        for (size_t i = 0; i < art.notes.size(); ++i)
        {
            auto& n = art.notes[i];
            csv << juce::String (int (i)) << "," << juce::String (n.start, 3) << "," << n.pitch << "," << int (n.dur() * 1000) << ","
                << techName (n.tech) << "," << n.reason << "\n";
        }
        rep.replaceWithText (csv);
    }

    VioletRenderer renderer;
    std::string err;
    std::wstring models = juce::String (opt["--models"]).toWideCharPointer();
    if (! renderer.load (exeDir(), models, err))
    {
        std::cerr << "motor: " << err << "\n";
        return 1;
    }
    auto t1 = std::chrono::steady_clock::now();
    std::cout << "      GPU: " << renderer.gpu().name << " | carga " << std::chrono::duration<double> (t1 - t0).count() << " s\n";
    const std::map<std::string, Quality> qs { { "low", Quality::low }, { "medium", Quality::medium }, { "high", Quality::high }, { "extreme", Quality::extreme } };
    Performer perf (renderer);
    int lastPct = -1;
    auto take = perf.perform (vnotes, qs.at (opt["--quality"]), fast, 1234,
                              [&] (float f) { int p = int (f * 100); if (p / 10 != lastPct / 10) { std::cout << "      " << p << " %\n"; lastPct = p; } return true; },
                              std::stoi (opt["--takes"]));
    auto t2 = std::chrono::steady_clock::now();
    std::cout << "[2/3] " << take.takesTried << " take(s): " << int (take.accuracy * 100) << " % das notas certas, atraso "
              << int (take.lag * 1000) << " ms, ar " << take.air << " dB | " << std::chrono::duration<double> (t2 - t1).count() << " s\n";

    // mixagem (offline, o mesmo processador do plugin)
    const std::map<std::string, MixStyle> ms { { "dry", MixStyle::dry }, { "lyrical", MixStyle::lyrical }, { "romantic", MixStyle::romantic },
                                               { "baroque", MixStyle::baroque }, { "cinematic", MixStyle::cinematic } };
    MixFx fx;
    fx.prepare (48000);
    MixSettings mset;
    mset.style = ms.at (opt["--mix"]);
    fx.set (mset);
    size_t tail = mset.style == MixStyle::dry ? 0 : size_t (48000 * 4);
    std::vector<float> mono (take.audio);
    mono.resize (mono.size() + tail, 0.f);
    juce::AudioBuffer<float> buf (2, int (mono.size()));
    fx.process (mono.data(), buf.getWritePointer (0), buf.getWritePointer (1), int (mono.size()));
    out.deleteFile();
    juce::WavAudioFormat wav;
    std::unique_ptr<juce::OutputStream> os (out.createOutputStream().release());
    if (auto* w = wav.createWriterFor (os.get(), 48000, 2, 24, {}, 0))
    {
        os.release();
        std::unique_ptr<juce::AudioFormatWriter> writer (w);
        writer->writeFromAudioSampleBuffer (buf, 0, buf.getNumSamples());
    }
    std::cout << "[3/3] " << argv[2] << " | " << opt["--mix"] << " | total " << std::chrono::duration<double> (std::chrono::steady_clock::now() - t0).count() << " s\n";
    return 0;
}
