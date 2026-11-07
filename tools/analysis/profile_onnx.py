"""Perfil por operação do núcleo do VIOLET no DirectML: onde o tempo vai."""
import collections
import json
import os
import sys

import numpy as np
import onnxruntime as ort

d, core_name = sys.argv[1], sys.argv[2]
ref = np.load(os.path.join(d, "reference.npz"))
so = ort.SessionOptions()
so.log_severity_level = 3
so.enable_mem_pattern = False
so.enable_profiling = True
so.profile_file_prefix = os.path.join(d, "prof")
core = ort.InferenceSession(os.path.join(d, core_name), so,
                            providers=[("DmlExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"])
f = np.float16 if "float16" in core.get_inputs()[0].type else np.float32
feeds = {i.name: np.random.randn(*i.shape).astype(f) for i in core.get_inputs()}
feeds["t"] = np.array([0.5], f)
for _ in range(8):
    core.run(None, feeds)
path = core.end_profiling()
ev = [e for e in json.load(open(path)) if e.get("cat") == "Node"]
by = collections.defaultdict(float)
prov = collections.Counter()
for e in ev:
    a = e.get("args", {})
    by[(a.get("op_name", "?"), a.get("provider", "?"))] += e["dur"]
    prov[a.get("provider", "?")] += 1
tot = sum(by.values())
print("nós por provider:", dict(prov))
for (op, p), us in sorted(by.items(), key=lambda kv: -kv[1])[:15]:
    print(f"{op:28s} {p:24s} {us / 8 / 1000:8.2f} ms/chamada  {100 * us / tot:5.1f}%")
os.remove(path)
