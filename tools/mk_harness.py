"""Gera uit/test.html: a UI com um backend falso (estado de exemplo) para testar no navegador."""
import os, shutil
os.chdir(r"C:\Users\TheoH\violino")
h = open("plugin/ui/index.html", encoding="utf-8").read()
mock = open("tools/harness_mock.html", encoding="utf-8").read()
h = h.replace("<script>", mock + "\n<script>", 1).replace("</body>", "<script>setTimeout(()=>__push(true),50);</script></body>")
os.makedirs("uit", exist_ok=True)
open("uit/test.html", "w", encoding="utf-8").write(h)
shutil.copy("plugin/ui/violin.webp", "uit/violin.webp")
print("ok")
