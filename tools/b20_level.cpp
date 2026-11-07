std::vector<float> ViolinoProcessor::levelNotes (const Phrase& p, const std::vector<float>& audio) const
{
    // nivelador lento (como um LA-2A): o VIOLET deixa trechos ligados/longos 10-20 dB abaixo dos ataques curtos
    // (medido nos renders). Envelope de 300 ms aproximado da mediana da frase; silêncio e cauda não sobem.
    const float even = value ("evenOut") / 100.f;
    juce::ignoreUnused (p);
    if (even <= 0.001f || audio.size() < 48000) return audio;
    const size_t hop = 480, win = 14400, nf = audio.size() / hop;  // quadros de 10 ms, janela de 300 ms
    std::vector<double> pre (audio.size() + 1, 0.0);
    for (size_t i = 0; i < audio.size(); ++i) pre[i + 1] = pre[i] + double (audio[i]) * audio[i];
    std::vector<float> env (nf);
    for (size_t f = 0; f < nf; ++f)
    {
        const size_t c = f * hop, a = c > win / 2 ? c - win / 2 : 0, b = std::min (audio.size(), c + win / 2);
        env[f] = float (10 * std::log10 ((pre[b] - pre[a]) / double (std::max<size_t> (1, b - a)) + 1e-12));
    }
    std::vector<float> on;
    for (auto e : env) if (e > -60) on.push_back (e);
    if (on.size() < 10) return audio;
    std::nth_element (on.begin(), on.begin() + long (on.size() * 6 / 10), on.end());
    const float ref = on[on.size() * 6 / 10];  // um pouco acima da mediana: o alvo é o corpo da frase
    std::vector<float> g (nf, 0.f);
    for (size_t f = 0; f < nf; ++f)
        if (env[f] > ref - 35)  // abaixo disso é silêncio/cauda: não sobe ruído
            g[f] = std::clamp ((ref - env[f]) * even, -8.f, 15.f);
    for (int pass = 0; pass < 2; ++pass)  // suaviza ~120 ms nos dois sentidos (sem bombear)
    {
        float y = g.empty() ? 0.f : g[0];
        for (size_t f = 0; f < nf; ++f) y += 0.08f * (g[f] - y), g[f] = y;
        y = g.empty() ? 0.f : g[nf - 1];
        for (size_t f = nf; f-- > 0;) y += 0.08f * (g[f] - y), g[f] = y;
    }
    std::vector<float> out (audio.size());
    for (size_t i = 0; i < audio.size(); ++i)
    {
        const double fp = double (i) / hop;
        const size_t f0 = std::min (nf - 1, size_t (fp)), f1 = std::min (nf - 1, f0 + 1);
        const float db = g[f0] + float (fp - double (f0)) * (g[f1] - g[f0]);
        out[i] = audio[i] * std::pow (10.f, db / 20.f);
    }
    return out;
}

