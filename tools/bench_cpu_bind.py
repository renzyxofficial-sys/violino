import numpy as np, onnxruntime as ort, time, os, sys
d = sys.argv[1]
so = ort.SessionOptions(); so.log_severity_level = 3; so.enable_mem_pattern = False
prov = [("DmlExecutionProvider", {"device_id": 0})]
core = ort.InferenceSession(os.path.join(d, "violet_core_fp16.onnx"), so, providers=prov)
f = np.float16
feeds = {i.name: np.random.randn(*i.shape).astype(f) for i in core.get_inputs()}
io = core.io_binding()
for k, v in feeds.items(): io.bind_cpu_input(k, v)
io.bind_output("v")
for _ in range(3): core.run_with_iobinding(io)
t0 = time.time()
for _ in range(20): core.run_with_iobinding(io); io.copy_outputs_to_cpu()
print("modulações copiadas da CPU a cada chamada: %.1f ms" % ((time.time() - t0) / 20 * 1000))
