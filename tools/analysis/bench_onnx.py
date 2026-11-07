"""Mede o núcleo do VIOLET em ONNX Runtime (DirectML) com as modulações fixas na GPU (IOBinding).

Uso: deps\\ortenv\\Scripts\\python.exe tools\\analysis\\bench_onnx.py <pasta_onnx> <core.onnx> [nível de otimização]
"""
import os
import sys
import time

import numpy as np
import onnxruntime as ort

d, core_name = sys.argv[1], sys.argv[2]
level = sys.argv[3] if len(sys.argv) > 3 else "basic"
ref = np.load(os.path.join(d, "reference.npz"))
so = ort.SessionOptions()
so.log_severity_level = 3
so.enable_mem_pattern = False
so.graph_optimization_level = {"basic": ort.GraphOptimizationLevel.ORT_ENABLE_BASIC,
                               "ext": ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED,
                               "all": ort.GraphOptimizationLevel.ORT_ENABLE_ALL,
                               "off": ort.GraphOptimizationLevel.ORT_DISABLE_ALL}[level]
DEV = int(os.environ.get("DML_DEVICE", "0"))  # adaptador DXGI; neste PC 0 = RTX, 1 = Intel UHD
prov = [("DmlExecutionProvider", {"device_id": DEV})]
cond = ort.InferenceSession(os.path.join(d, "violet_cond.onnx"), so, providers=prov)
core = ort.InferenceSession(os.path.join(d, core_name), so, providers=prov)
f = np.float16 if "float16" in core.get_inputs()[0].type else np.float32
bm, fm = cond.run(None, dict(midi_roll=ref["midi_roll"], tech_roll=ref["tech_roll"],
                             tech_keep=np.ones((1, 1, 1), np.float32), cc_tokens=ref["cc_tokens"],
                             cc_keep=np.zeros((1, 1, 1), np.float32)))
dev = lambda a: ort.OrtValue.ortvalue_from_numpy(np.ascontiguousarray(a.astype(f)), "dml", DEV)  # noqa: E731
bm_d, fm_d, x_d = dev(bm), dev(fm), dev(ref["noise"])
io = core.io_binding()
io.bind_ortvalue_input("block_mod", bm_d)
io.bind_ortvalue_input("final_mod", fm_d)
io.bind_ortvalue_input("x", x_d)
io.bind_cpu_input("t", np.array([0.5], f))
io.bind_output("v", "dml", DEV)
for _ in range(3):
    core.run_with_iobinding(io)
n = 20
t0 = time.time()
for _ in range(n):
    core.run_with_iobinding(io)
    io.get_outputs()[0].numpy()  # força sincronizar
per = (time.time() - t0) / n
print(f"{core_name} [{level}]: {per * 1000:.1f} ms por chamada -> 30 passos (57 chamadas) = {per * 57:.2f} s")
