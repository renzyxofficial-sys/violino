"""Biblioteca de MIDIs clássicos (Mutopia Project, domínio público / CC): peças para violino solo.
Baixa ~100 peças, no máximo 12 por compositor, e grava library/index.json
(compositor, título, estilo, playstyle sugerido, arquivo, licença)."""
import html
import io
import json
import os
import re
import time
import urllib.request
import zipfile

OUT = r"C:\Users\TheoH\violino\library"
BASE = "https://www.mutopiaproject.org/cgibin/make-table.cgi?Instrument=Violin&startat={}"
STYLE_TO_PLAY = {"Baroque": "Baroque", "Classical": "Classical", "Romantic": "Romantic", "Renaissance": "Baroque",
                 "Modern": "Cinematic", "Traditional": "Lyrical", "Folk": "Lyrical"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Violino-plugin-library/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def cells(block):
    return [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", block, re.S)]


def safe(s):
    return re.sub(r"[^A-Za-z0-9 ._()-]+", "", s).strip()[:70] or "piece"


pieces = []
for start in range(0, 1500, 10):
    page = get(BASE.format(start)).decode("utf-8", "ignore")
    blocks = re.findall(r'<table class="table-bordered result-table">(.*?)</table>', page, re.S)
    if not blocks:
        break
    for b in blocks:
        c = cells(b)
        if len(c) < 12:
            continue
        title, composer, instr, style, lic = c[0], c[1], c[4], c[6], c[9]
        mid = re.search(r'href="([^"]+\.mid)"', b)
        zipm = re.search(r'href="([^"]+-mids\.zip)"', b)
        il = instr.strip().lower()
        # violino solo, ou violino com piano / contínuo / outro violino (o import pega a linha do violino)
        if "violin" not in il or any(w in il for w in ("orchestra", "choir", "voice", "soprano", "quartet", "quintet", "viola")):
            continue
        pieces.append({"title": re.sub(r"^\d+\.\s*", "", title), "composer": composer, "style": style, "license": lic,
                       "mid": mid.group(1) if mid else None, "zip": zipm.group(1) if zipm else None})
    time.sleep(0.4)
print("found", len(pieces))

per, chosen = {}, []
for p in pieces:
    if per.get(p["composer"], 0) >= 12:
        continue
    per[p["composer"]] = per.get(p["composer"], 0) + 1
    chosen.append(p)
    if len(chosen) >= 100:
        break

os.makedirs(OUT, exist_ok=True)
index = []
for p in chosen:
    d = os.path.join(OUT, safe(p["composer"]))
    os.makedirs(d, exist_ok=True)
    try:
        if p["mid"]:
            files = [(safe(p["title"]) + ".mid", get(p["mid"]))]
        elif p["zip"]:
            z = zipfile.ZipFile(io.BytesIO(get(p["zip"])))
            names = sorted(n for n in z.namelist() if n.lower().endswith(".mid"))[:4]  # até 4 movimentos
            files = [(safe(p["title"]) + (f" - {k + 1}" if len(names) > 1 else "") + ".mid", z.read(n)) for k, n in enumerate(names)]
        else:
            continue
    except Exception as e:  # um arquivo que falha não para a biblioteca
        print("skip", p["title"], e)
        continue
    for name, data in files:
        open(os.path.join(d, name), "wb").write(data)
        index.append({"composer": p["composer"], "title": os.path.splitext(name)[0], "style": p["style"] or "Other",
                      "playstyle": STYLE_TO_PLAY.get(p["style"], "Natural"), "license": p["license"],
                      "file": os.path.relpath(os.path.join(d, name), OUT).replace("\\", "/")})
    time.sleep(0.3)
json.dump(index, open(os.path.join(OUT, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("pieces", len(chosen), "files", len(index), "composers", len(per))
