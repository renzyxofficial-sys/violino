"""Bloco 1 / áudio: preview com nível uniforme (normaliza cada sample), interpolação Hermite (sem o chiado
do aliasing linear), roubo de voz sem corte seco; render: silêncio antes do 1º ataque + fade in; cache limitado."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


p = open("source/PreviewSampler.cpp", encoding="utf-8").read()
p = rep(p, """        auto* src = buf.getReadPointer (0);
        for (size_t i = 0; i < s.data.size(); ++i)
            s.data[i] = int16_t (juce::jlimit (-32767.0f, 32767.0f, src[i] * 32767.0f));""", """        auto* src = buf.getReadPointer (0);
        // nível uniforme: o RMS da janela mais forte (200 ms) vai para um alvo por camada (f 6 dB acima de p),
        // porque as gravações do VSCO variam muito de nota para nota e de articulação para articulação
        const int win = juce::jmax (1, int (fileRate * 0.2));
        double best = 1e-9;
        for (int a = 0; a + win <= buf.getNumSamples(); a += win / 2)
        {
            double e = 0;
            for (int i = a; i < a + win; ++i) e += double (src[i]) * src[i];
            best = std::max (best, std::sqrt (e / win));
        }
        const float norm = juce::jlimit (0.25f, 8.0f, float ((s.layer ? 0.16 : 0.08) / best));
        for (size_t i = 0; i < s.data.size(); ++i)
            s.data[i] = int16_t (juce::jlimit (-32767.0f, 32767.0f, src[i] * norm * 32767.0f));""")
p = rep(p, """    Voice* oldest = &voices[0];
    for (auto& v : voices)
    {
        if (! v.active)
            return v;
        if (v.age > oldest->age)
            oldest = &v;
    }
    return *oldest;""", """    // livre > a que já está soltando (mais velha) > a mais velha; nunca corta seco o que soa forte
    Voice* best = nullptr;
    for (auto& v : voices)
    {
        if (! v.active)
            return v;
        if (best == nullptr || (v.releasing && ! best->releasing) || (v.releasing == best->releasing && v.age > best->age))
            best = &v;
    }
    return *best;""")
# Hermite de 4 pontos (o linear gera aliasing e o "chiado" nas notas agudas)
p = rep(p, """            if (ip + 1 >= dp.size() || jf + 1 >= df.size())""", """            if (ip + 2 >= dp.size() || jf + 2 >= df.size())""")
p = rep(p, """            float sp = (dp[ip] + fr * (dp[ip + 1] - dp[ip])) * (1.0f / 32768.0f);
            float sf = (df[jf] + ff * (df[jf + 1] - df[jf])) * (1.0f / 32768.0f);""", """            auto hermite = [] (const std::vector<int16_t>& d, size_t i, float t) {
                const float xm1 = i > 0 ? d[i - 1] : d[i], x0 = d[i], x1 = d[i + 1], x2 = d[i + 2];
                const float c1 = 0.5f * (x1 - xm1), c2 = xm1 - 2.5f * x0 + 2.0f * x1 - 0.5f * x2, c3 = 0.5f * (x2 - xm1) + 1.5f * (x0 - x1);
                return ((c3 * t + c2) * t + c1) * t + x0;
            };
            float sp = hermite (dp, ip, fr) * (1.0f / 32768.0f);
            float sf = hermite (df, jf, ff) * (1.0f / 32768.0f);""")
open("source/PreviewSampler.cpp", "w", encoding="utf-8").write(p)

# preview da DAW em frase sem render: velocity da curva, mas sem extremos
s = open("source/PluginProcessor.cpp", encoding="utf-8").read()
s = rep(s, "                            vel = juce::jlimit (1, 127, juce::roundToInt ((cc - 20.f) / 0.8f));  // inverso de 20 + 0.8 vel",
        "                            vel = juce::jlimit (45, 120, juce::roundToInt ((cc - 20.f) / 0.8f));  // inverso de 20 + 0.8 vel, sem extremos")
# render: silêncio antes do primeiro ataque + fade in curto (o VIOLET às vezes "respira" antes da nota)
s = rep(s, """        auto f = cacheFile (r.id);
        f.getParentDirectory().createDirectory();
        f.replaceWithData (r.take.audio.data(), r.take.audio.size() * sizeof (float));""", """        for (auto& p : phrases)
            if (p.hash == r.id && ! p.starts.empty())
            {
                const double first = p.starts.front().first - p.origin;  // 1º ataque, em segundos do áudio
                const size_t z = size_t (std::max (0.0, first - 0.06) * 48000), fade = 1920;  // 40 ms
                auto& au = r.take.audio;
                for (size_t i = 0; i < std::min (z, au.size()); ++i) au[i] = 0;
                for (size_t i = 0; i < fade && z + i < au.size(); ++i)
                    au[z + i] *= float (0.5 - 0.5 * std::cos (3.14159265358979 * double (i) / double (fade)));
            }
        auto f = cacheFile (r.id);
        f.getParentDirectory().createDirectory();
        f.replaceWithData (r.take.audio.data(), r.take.audio.size() * sizeof (float));
        // cache limitado: acima de 1,5 GB apaga os renders mais antigos até 1 GB
        {
            juce::Array<juce::File> files = f.getParentDirectory().findChildFiles (juce::File::findFiles, false, "*.f32");
            juce::int64 total = 0;
            for (auto& x : files) total += x.getSize();
            if (total > (juce::int64) 1536 << 20)
            {
                std::sort (files.begin(), files.end(), [] (const juce::File& a, const juce::File& b) { return a.getLastModificationTime() < b.getLastModificationTime(); });
                for (auto& x : files)
                {
                    if (total < (juce::int64) 1024 << 20) break;
                    total -= x.getSize();
                    x.deleteFile();
                }
            }
        }""")
open("source/PluginProcessor.cpp", "w", encoding="utf-8").write(s)
print("ok")
