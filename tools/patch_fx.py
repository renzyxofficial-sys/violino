"""MixFx: EQ on/off, Compressor, Saturation, Chorus, Delay, Stereo (decorrelação) como módulos do usuário."""
import os

os.chdir(r"C:\Users\TheoH\violino\plugin\engine")


def rep(s, old, new, n=1):
    c = s.count(old)
    assert c == n, (c, old[:70])
    return s.replace(old, new)


h = open("MixFx.h", encoding="utf-8").read()
h = rep(h, """    float eqLow = 0, eqMid = 0, eqHigh = 0, eqAir = 0;  // dB
    float outputDb = 0;
};""", """    bool eqOn = true;
    float eqLow = 0, eqMid = 0, eqHigh = 0, eqAir = 0;  // dB
    bool compOn = false;
    float compThresh = -18, compRatio = 3, compAttackMs = 15, compReleaseMs = 150, compMakeup = 3;
    bool satOn = false;
    float satDrive = 0.3f;
    bool chorusOn = false;
    float chorusRate = 0.6f, chorusDepth = 0.3f, chorusMix = 0.25f;
    bool delayOn = false;
    float delayMs = 320, delayFeedback = 0.25f, delayMix = 0.18f;
    bool stereoOn = true;
    float stereoWidth = 0.5f;
    float outputDb = 0;
    bool operator== (const MixSettings&) const = default;
};""")
h = rep(h, """    bool wetOn = false, compOn = false;
    float wet = 0, drive = 0, width = 1, tailGain = 1;
    double compThresh = 0, compRatio = 1, compAtk = 0, compRel = 0, env = 0, envC = 0, gainDb = 0, makeup = 0;
    float outGain = 1;
};""", """    bool wetOn = false, compOn = false;
    float wet = 0, drive = 0, width = 1, tailGain = 1;
    double compThresh = 0, compRatio = 1, compAtk = 0, compRel = 0, env = 0, envC = 0, gainDb = 0, makeup = 0;
    float outGain = 1;

    // módulos do usuário (aba Effects)
    struct Comp
    {
        double thresh = -18, ratio = 3, atk = 0, rel = 0, env = 0, envC = 0, gain = 0, makeup = 0;
        float process (float x);
    } userComp;
    std::vector<float> chorusBuf, delayL, delayR, decoA, decoB;
    size_t chorusPos = 0, delayPos = 0, delayLen = 1;
    double chorusPhase = 0;
    float delayLpL = 0, delayLpR = 0;
    std::array<Biquad, 4> deco;  // all-pass de decorrelação (Stereo)
};""")
open("MixFx.h", "w", encoding="utf-8").write(h)

c = open("MixFx.cpp", encoding="utf-8").read()
c = rep(c, """    for (auto& u : user) u.reserve (8);
    built = false;""", """    for (auto& u : user) u.reserve (8);
    chorusBuf.assign (size_t (0.05 * sr) + 4, 0.f);
    delayL.assign (size_t (1.2 * sr) + 4, 0.f);
    delayR.assign (size_t (1.2 * sr) + 4, 0.f);
    built = false;""")
c = rep(c, """    bool same = s.style == cur.style && s.reverbOn == cur.reverbOn && s.room == cur.room && s.reverbMix == cur.reverbMix
                && s.decay == cur.decay && s.predelayMs == cur.predelayMs && s.eqLow == cur.eqLow && s.eqMid == cur.eqMid
                && s.eqHigh == cur.eqHigh && s.eqAir == cur.eqAir && s.outputDb == cur.outputDb;
    if (same && built)""", """    if (s == cur && built)""")
c = rep(c, """    for (int c = 0; c < 2; ++c)
    {
        add (user[size_t (c)], Biquad::lowShelf, 180, cur.eqLow, 0.7);""", """    // Compressor do usuário (depois da cor do estilo)
    userComp.thresh = cur.compThresh, userComp.ratio = std::max (1.0f, cur.compRatio);
    userComp.atk = std::exp (-1.0 / (std::max (0.5f, cur.compAttackMs) * 0.001 * sr));
    userComp.rel = std::exp (-1.0 / (std::max (5.0f, cur.compReleaseMs) * 0.001 * sr));
    userComp.envC = std::exp (-1.0 / (0.01 * sr));
    userComp.makeup = cur.compMakeup;
    // Stereo: dois pares de all-pass diferentes; L = x + S, R = x - S (a soma mono volta a ser x)
    const double decoF[] = { 320, 1150, 470, 2300 };
    for (size_t i = 0; i < 4; ++i)
    {
        deco[i].set (Biquad::peak, decoF[i], 0, 0.7, sr);  // zera e usa como all-pass de 2ª ordem abaixo
        double w = 2 * kPi * decoF[i] / sr, al = std::sin (w) / (2 * 0.7), a0 = 1 + al;
        deco[i].b0 = (1 - al) / a0, deco[i].b1 = -2 * std::cos (w) / a0, deco[i].b2 = 1, deco[i].b2 = (1 + al) / a0;
        deco[i].a1 = -2 * std::cos (w) / a0, deco[i].a2 = (1 - al) / a0;
    }
    delayLen = std::clamp<size_t> (size_t (cur.delayMs * 0.001 * sr), 1, delayL.size() - 1);
    for (int c = 0; c < 2; ++c)
    {
        if (! cur.eqOn) continue;
        add (user[size_t (c)], Biquad::lowShelf, 180, cur.eqLow, 0.7);""")
c = rep(c, """void MixFx::reset()
{
    reverb.reset();""", """float MixFx::Comp::process (float x)
{
    env = envC * env + (1 - envC) * double (x) * x;
    double db = 10 * std::log10 (env + 1e-18);
    double target = -std::max (db - thresh, 0.0) * (1 - 1 / ratio);
    double c = target < gain ? atk : rel;
    gain = c * gain + (1 - c) * target;
    return x * float (std::pow (10.0, (gain + makeup) / 20));
}

void MixFx::reset()
{
    reverb.reset();
    std::fill (chorusBuf.begin(), chorusBuf.end(), 0.f);
    std::fill (delayL.begin(), delayL.end(), 0.f);
    std::fill (delayR.begin(), delayR.end(), 0.f);
    for (auto& d : deco) d.reset();""")
c = rep(c, """        float l = x, r = x;
        if (wetOn)
        {
            float tl, tr;
            reverb.process (sendLp.process (sendHp.process (x)), tl, tr);
            float m = 0.5f * (tl + tr), s = 0.5f * (tl - tr) * width;
            tl = (m + s) * tailGain, tr = (m - s) * tailGain;
            l = (1 - wet) * x + wet * tl;
            r = (1 - wet) * x + wet * tr;
        }""", """        if (cur.compOn) x = userComp.process (x);
        if (cur.satOn && cur.satDrive > 0)
        {
            const float d = cur.satDrive, k = 1 + 6 * d, ref = 0.5f;
            x = (1 - 0.6f * d) * x + 0.6f * d * std::tanh (k * x / ref) / std::tanh (k) * ref;
        }
        // seco estéreo: Stereo (decorrelação) e Chorus
        float dl = x, dr = x;
        if (cur.stereoOn && cur.stereoWidth > 0)
        {
            float a = deco[1].process (deco[0].process (x)), b = deco[3].process (deco[2].process (x));
            float s = 0.5f * cur.stereoWidth * (a - b);
            dl = x + s, dr = x - s;
        }
        if (cur.chorusOn)
        {
            chorusBuf[chorusPos] = x;
            chorusPhase += cur.chorusRate / sr;
            if (chorusPhase >= 1) chorusPhase -= 1;
            auto tap = [&] (double phase) {
                double d = (0.012 + 0.004 * cur.chorusDepth * (1 + std::sin (2 * kPi * phase))) * sr;
                double rp = double (chorusPos) - d;
                while (rp < 0) rp += double (chorusBuf.size());
                size_t i0 = size_t (rp) % chorusBuf.size(), i1 = (i0 + 1) % chorusBuf.size();
                float fr = float (rp - std::floor (rp));
                return chorusBuf[i0] + fr * (chorusBuf[i1] - chorusBuf[i0]);
            };
            float cl = tap (chorusPhase), cr = tap (chorusPhase + 0.25);
            dl = (1 - cur.chorusMix) * dl + cur.chorusMix * cl;
            dr = (1 - cur.chorusMix) * dr + cur.chorusMix * cr;
            chorusPos = (chorusPos + 1) % chorusBuf.size();
        }
        float l = dl, r = dr;
        if (wetOn)
        {
            float tl, tr;
            reverb.process (sendLp.process (sendHp.process (x)), tl, tr);
            float m = 0.5f * (tl + tr), s = 0.5f * (tl - tr) * width;
            tl = (m + s) * tailGain, tr = (m - s) * tailGain;
            l = (1 - wet) * dl + wet * tl;
            r = (1 - wet) * dr + wet * tr;
        }
        if (cur.delayOn)
        {
            // eco estéreo cruzado (ping-pong) com passa-baixas na realimentação
            size_t rp = (delayPos + delayL.size() - delayLen) % delayL.size();
            float el = delayL[rp], er = delayR[rp];
            delayLpL += 0.35f * (el - delayLpL);
            delayLpR += 0.35f * (er - delayLpR);
            delayL[delayPos] = 0.5f * (l + r) + cur.delayFeedback * delayLpR;
            delayR[delayPos] = cur.delayFeedback * delayLpL;
            delayPos = (delayPos + 1) % delayL.size();
            l += cur.delayMix * el;
            r += cur.delayMix * er;
        }""")
open("MixFx.cpp", "w", encoding="utf-8").write(c)
print("ok")
