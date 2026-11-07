"""Confere o VIOLET em ONNX (DirectML no Windows) contra a janela de referência do PyTorch.

Uso: deps\\ortenv\\Scripts\\python.exe tools\\build\\validate_onnx.py <pasta_onnx> [violet_core.onnx|violet_core_fp16.onnx]
Roda o condicionamento uma vez, repete o amostrador Heun do VIOLET com UMA chamada do núcleo por
avaliação (técnica ligada, CC desligado = w_tech 1, w_cc 0), decodifica e compara latentes e áudio;
mede o tempo de cada etapa.
"""
import os
import sys
import time

import numpy as np
import onnxruntime as ort
import soundfile as sf

d = sys.argv[1]
core_name = sys.argv[2] if len(sys.argv) > 2 else "violet_core.onnx"
ref = np.load(os.path.join(d, "reference.npz"))
so = ort.SessionOptions()
so.log_severity_level = 3
DEV = int(os.environ.get("DML_DEVICE", "0"))  # adaptador DXGI; neste PC 0 = RTX, 1 = Intel UHD
prov = [("DmlExecutionProvider", {"device_id": DEV}), "CPUExecutionProvider"]

t0 = time.time()
cond = ort.InferenceSession(os.path.join(d, "violet_cond.onnx"), so, providers=prov)
core = ort.InferenceSession(os.path.join(d, core_name), so, providers=prov)
dec = ort.InferenceSession(os.path.join(d, "dacvae_decode.onnx"), so, providers=prov)
print(f"{core_name} | carga: {time.time() - t0:.1f} s")
f = np.float16 if "float16" in core.get_inputs()[0].type else np.float32


def run_cond():
    return cond.run(None, dict(midi_roll=ref["midi_roll"], tech_roll=ref["tech_roll"],
                               tech_keep=np.ones((1, 1, 1), np.float32), cc_tokens=ref["cc_tokens"],
                               cc_keep=np.zeros((1, 1, 1), np.float32)))


def sample(noise, sigmas, block_mod, final_mod):
    bm, fm = block_mod.astype(f), final_mod.astype(f)

    def v(x, s):
        return core.run(None, dict(x=x.astype(f), t=np.array([s], f), block_mod=bm,
                                   final_mod=fm))[0].astype(np.float32)

    x = sigmas[0] * noise
    for i in range(len(sigmas) - 1):
        s, sn = float(sigmas[i]), float(sigmas[i + 1])
        vc = v(x, s)
        xn = x + (sn - s) * vc
        if sn != 0:
            xn = x + 0.5 * (sn - s) * (vc + v(xn, sn))
        x = xn
    return x


bm, fm = run_cond()  # aquece
sample(ref["noise"], ref["sigmas"][:2], bm, fm)
dec.run(None, {"latents": ref["latents"]})
t0 = time.time()
bm, fm = run_cond()
t_cond = time.time() - t0
t0 = time.time()
lat = sample(ref["noise"], ref["sigmas"], bm, fm)
t_dit = time.time() - t0
t0 = time.time()
wav = dec.run(None, {"latents": lat.astype(np.float32)})[0]
t_dec = time.time() - t0

lr, wr = ref["latents"], ref["wav"]
print(f"cond: {t_cond:.2f} s | DiT 30 passos: {t_dit:.2f} s | decode: {t_dec:.2f} s "
      f"| total por janela de 10 s: {t_cond + t_dit + t_dec:.2f} s")
print(f"latentes: rel {np.linalg.norm(lat - lr) / np.linalg.norm(lr):.4g}")
n = min(wav.shape[-1], wr.shape[-1])
a, b = wav.reshape(-1)[:n], wr.reshape(-1)[:n]
err = np.linalg.norm(a - b) / np.linalg.norm(b)
print(f"áudio: SNR {-20 * np.log10(err + 1e-12):.1f} dB | pico onnx {np.abs(a).max():.3f} / torch {np.abs(b).max():.3f}")
sf.write(os.path.join(d, f"check_{os.path.splitext(core_name)[0]}.wav"), a, 48000)
