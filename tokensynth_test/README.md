# Teste do TokenSynth (comparação com o VIOLET)

Objetivo: instalar o **TokenSynth** (ICASSP 2025, "clonador" de instrumento a partir de MIDI + áudio de referência)
no WSL, gerar os mesmos trechos com timbres de violino, cello e outros, e comparar com o VIOLET de ouvido e com
medidas objetivas. **Não mexer no plugin nem no VIOLET** — é só um teste isolado.

- Repositório: https://github.com/kyungsukim42/tokensynth (código MIT)
- Artigo: https://arxiv.org/abs/2502.08939
- Pesos: https://huggingface.co/KyungsuKim/TokenSynth (baixam sozinhos no 1º uso; **conferir a licença dos pesos** no card)

## O que já sabemos (para não perder tempo)

- Transformer de tokens (~175 M parâmetros) + codec **DAC 44 kHz** + timbre pelo **CLAP** (áudio ou texto).
- Treinado com notas do **NSynth** tocando músicas do **Lakh MIDI** (trechos de **5 s**).
- Entrada por nota: início, fim, altura e **velocity com só 4 níveis**. **Sem** articulação, vibrato, ligadura ou pitch bend.
- O quickstart do README grava em **16 kHz**, mas o codec é 44 kHz: **conferir a taxa real da saída**.
- Precisa do MIDI inteiro antes de gerar (não é tempo real). Trechos longos podem degradar: testar com ~8–10 s.

## Ambiente (WSL, Ubuntu)

O WSL já tem o `~/miniforge3` (usado pelo VIOLET). Criar um ambiente separado para não quebrar o do VIOLET:

```bash
~/miniforge3/bin/conda create -y -n tokensynth python=3.10
~/miniforge3/envs/tokensynth/bin/pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
~/miniforge3/envs/tokensynth/bin/pip install tokensynth pretty_midi soundfile numpy
cd ~ && git clone https://github.com/kyungsukim42/tokensynth.git
```

Se `pip install tokensynth` falhar, instalar a partir do clone: `cd ~/tokensynth && ~/miniforge3/envs/tokensynth/bin/pip install -e .`

Primeiro teste (o exemplo oficial):

```bash
cd ~/tokensynth && ~/miniforge3/envs/tokensynth/bin/python quickstart.py
```

## Material de teste (já está na máquina)

Pastas do Windows vistas do WSL em `/mnt/c/...`:

- **MIDIs** (biblioteca do plugin, Mutopia, domínio público/CC):
  - `/mnt/c/Users/TheoH/violino/library/by J. S. Bach (16851750)/Violin Concerto N 1 - Violin Solo - 1.mid`
  - `/mnt/c/Users/TheoH/violino/library/by J. S. Bach (16851750)/Sonata for Violin and Clavier No.4 - 1.mid`
  - Usar a **linha do violino** (trilha com mais notas acima do Sol 3) e cortar em **~8–10 s** (script abaixo).
- **Referência de violino** (VSCO 2 CE, CC0):
  - `/mnt/c/Users/TheoH/violino/deps/VSCO-2-CE/Strings/Solo Violin/Arco Vib/LLVln_ArcoVib_A4_f.wav` (sustentado)
  - `/mnt/c/Users/TheoH/violino/deps/VSCO-2-CE/Strings/Solo Violin/spic/` (spiccato)
- **Referência de cello / viola / outros**: a pasta local só tem violino. Opções:
  1. Texto no CLAP: `"solo cello, warm, legato"`, `"solo viola"`, `"flute"`.
  2. Baixar samples CC0 do VSCO 2 CE completo: https://github.com/sgossner/VSCO-2-CE (pastas de cello/viola).
- **Render do VIOLET para comparar**: exportar o mesmo trecho pelo plugin (Drag Audio ou Export WAV) e copiar para
  `/mnt/c/Users/TheoH/violino/tokensynth_test/violet/`.

## Script de teste

Salvar como `/mnt/c/Users/TheoH/violino/tokensynth_test/run_test.py` e rodar com o Python do ambiente `tokensynth`.
Ajustar os nomes das funções conforme o quickstart do repositório (a API abaixo é a do README em nov/2026).

```python
import pretty_midi, soundfile as sf, torch, os
from tokensynth import TokenSynth, CLAP, DACDecoder   # conferir nomes no quickstart.py

OUT = "/mnt/c/Users/TheoH/violino/tokensynth_test/out"
os.makedirs(OUT, exist_ok=True)
dev = "cuda" if torch.cuda.is_available() else "cpu"

def violin_line(path, seconds=10.0):
    pm = pretty_midi.PrettyMIDI(path)
    inst = max(pm.instruments, key=lambda i: sum(n.pitch >= 55 for n in i.notes))  # a linha do violino
    t0 = min(n.start for n in inst.notes)
    out = pretty_midi.PrettyMIDI(); new = pretty_midi.Instrument(program=40)
    for n in inst.notes:
        if n.start - t0 < seconds:
            new.notes.append(pretty_midi.Note(n.velocity, n.pitch, n.start - t0, min(n.end - t0, seconds)))
    out.instruments.append(new)
    p = os.path.join(OUT, os.path.basename(path).replace(".mid", "_cut.mid")); out.write(p); return p

synth = TokenSynth.from_pretrained(aug=True, device=dev)
clap, dec = CLAP(device=dev), DACDecoder(device=dev)
lib = "/mnt/c/Users/TheoH/violino/library/by J. S. Bach (16851750)/"
midis = [violin_line(lib + "Violin Concerto N 1 - Violin Solo - 1.mid"), violin_line(lib + "Sonata for Violin and Clavier No.4 - 1.mid")]
refs = {
    "violin_ref": ("audio", "/mnt/c/Users/TheoH/violino/deps/VSCO-2-CE/Strings/Solo Violin/Arco Vib/LLVln_ArcoVib_A4_f.wav"),
    "violin_text": ("text", "solo violin, expressive, legato"),
    "cello_text": ("text", "solo cello, warm, legato"),
    "viola_text": ("text", "solo viola"),
}
for m in midis:
    for name, (kind, val) in refs.items():
        timbre = clap.encode_audio(val) if kind == "audio" else clap.encode_text(val)   # conferir assinatura (wav vs caminho)
        tokens = synth.synthesize(timbre, m, top_p=0.95) if kind == "audio" else synth.synthesize(timbre, m, top_p=0.6, guidance_scale=1.6)
        wav = dec.decode(tokens)
        sr = 44100   # CONFERIR: o quickstart grava em 16000; usar a taxa real do decoder
        sf.write(os.path.join(OUT, f"{os.path.basename(m)[:-4]}_{name}.wav"), wav.squeeze().cpu().numpy(), sr)
print("ok ->", OUT)
```

## Como comparar

1. **De ouvido** (o mais importante): mesmo trecho no VIOLET × TokenSynth (violino) × TokenSynth (cello/viola).
   Notar: realismo do arco, ligaduras, ataques, ruído, afinação, estabilidade em notas longas.
2. **Medidas** (mesmas usadas no VIOLET): ruído (planicidade espectral), brilho e nível a cada 0,5 s.
   O script `C:\Users\TheoH\violino\tools\quality.py` lê o cache do plugin; adaptar a linha `f = ...` para ler um
   `.wav` (com `soundfile.read`) e rodar nos arquivos de `out/` e `violet/`.
3. **Tempo de geração** e **VRAM** (RTX 3070 Ti, 8 GB): anotar segundos por segundo de áudio.

## O que reportar na volta

- Funcionou? Taxa de amostragem real da saída e licença dos pesos.
- Para cada timbre: nota de 1 a 5 (realismo) e comentários.
- Velocidade e VRAM.
- Conclusão: vale virar um modo "outros instrumentos" no plugin (via ONNX, como o VIOLET) ou não.

## Não fazer

- Não alterar `~/VIOLET`, o ambiente dele nem o plugin (`C:\Users\TheoH\violino\plugin`).
- Backup da versão atual do plugin: `C:\Users\TheoH\violino\backups\Violino-v0.22-2026-11-06.zip`.
