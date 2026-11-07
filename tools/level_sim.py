"""Simula o nivelador (mesmo algoritmo do C++) num render do cache e mostra o envelope antes/depois."""
import glob
import os

import numpy as np

f = [x for x in glob.glob('/mnt/c/Users/TheoH/AppData/Local/Violino/cache/*.f32') if os.path.basename(x).startswith('d23a')][0]
x = np.fromfile(f, dtype=np.float32).astype(np.float64)
hop, win, even = 480, 14400, 0.9
nf = len(x) // hop
pre = np.concatenate([[0], np.cumsum(x * x)])
env = np.empty(nf)
for k in range(nf):
    c = k * hop; a = max(0, c - win // 2); b = min(len(x), c + win // 2)
    env[k] = 10 * np.log10((pre[b] - pre[a]) / max(1, b - a) + 1e-12)
on = np.sort(env[env > -60])
ref = on[len(on) * 6 // 10]
g = np.where(env > ref - 35, np.clip((ref - env) * even, -8, 15), 0.0)
for _ in range(2):
    y = g[0]
    for k in range(nf): y += 0.08 * (g[k] - y); g[k] = y
    y = g[-1]
    for k in range(nf - 1, -1, -1): y += 0.08 * (g[k] - y); g[k] = y
gs = np.interp(np.arange(len(x)) / hop, np.arange(nf), g)
out = x * 10 ** (gs / 20)


def envl(s):
    h = 12000
    return [20 * np.log10(np.sqrt(np.mean(s[i:i + h] ** 2)) + 1e-9) for i in range(0, len(s) - h, h)]


b, a = envl(x), envl(out)
act = [k for k in range(len(b)) if b[k] > -55]
print("before: spread (p10..p90) %.1f dB" % (np.percentile([b[k] for k in act], 90) - np.percentile([b[k] for k in act], 10)))
print("after : spread (p10..p90) %.1f dB" % (np.percentile([a[k] for k in act], 90) - np.percentile([a[k] for k in act], 10)))
print("before mid (60-95):", " ".join(f"{d:.0f}" for d in b[60:95]))
print("after  mid (60-95):", " ".join(f"{d:.0f}" for d in a[60:95]))
