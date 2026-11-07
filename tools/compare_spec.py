import numpy as np, soundfile as sf, sys
d = sys.argv[1]
t, _ = sf.read(d + "/check_torch.wav"); a, _ = sf.read(d + "/check_violet_core.wav"); b, _ = sf.read(d + "/check_violet_core_fp16.wav")
def spec(y, n=2048, h=512):
    w = np.hanning(n); fr = [np.abs(np.fft.rfft(w * y[i:i+n])) for i in range(0, len(y) - n, h)]
    return 20 * np.log10(np.array(fr) + 1e-5)
def bands(y):
    S = 10 ** (spec(y) / 10); f = np.fft.rfftfreq(2048, 1/48000)
    return [10*np.log10(S[:, (f>=lo)&(f<hi)].sum() + 1e-12) for lo, hi in ((0,500),(500,2000),(2000,8000),(8000,24000))]
st = spec(t)
for name, y in (("fp32", a), ("fp16", b)):
    s = spec(y); m = st > st.max() - 60
    print(name, "dif. espectral média %.2f dB" % np.abs(s - st)[m].mean(), "| bandas (dB vs torch):", np.round(np.array(bands(y)) - np.array(bands(t)), 2))
