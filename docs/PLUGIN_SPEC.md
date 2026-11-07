# Plugin de violino solo com IA — especificação (v0.5, 2026-11-06)

> **Idioma do plugin: 100 % inglês.** Este documento é em português, mas todo texto que o
> usuário vê (botões, abas, mensagens, motivos das decisões, nomes de técnicas, relatórios)
> é em inglês. Os nomes entre aspas abaixo são os rótulos finais.

Plugin VST3 (Windows primeiro; AU/macOS depois) que toca o MIDI do DAW como um violinista.
Mesmo fluxo e "vibe" do Vienna Performer: **você toca e ouve na hora um violino solo seco
(samples), o plugin captura a frase, a IA (VIOLET) interpreta e renderiza, e o render passa a
tocar no lugar do preview**, sincronizado com o playhead do DAW. Por enquanto só **violino**,
mas com a base pronta para outros instrumentos e plugins (§11).

---

## 1. Fluxo (igual ao Performer)
1. **Preview em tempo real** — toda nota soa na hora pelo sampler de **violino SOLO**
   (VSCO 2 CE, CC0). Seco, sem latência, leve. Sem IR (os samples já são um violino real).
2. **Capture** — grava notas, velocity, CC1/CC11, pitch bend, keyswitches e CC64 com o tempo
   do DAW (PPQ + segundos). A captura **segue o playhead**: tocar de novo um trecho substitui
   a captura daquele trecho. **Frase** = notas sem pausa ≥ 2 s.
3. **Interpretação** — cada frase passa pelo modo de execução (§3) e pelo articulador (§4).
   Tudo aparece na aba Performance e é editável.
4. **Render** — *Autorender* manda a frase para a fila assim que é capturada; sem ele, botão
   *Render*. O motor nativo (§8) faz N candidatos, escolhe o de mais notas certas e compensa o
   atraso. **Render sempre seco.**
5. **Reprodução** — trecho renderizado toca a IA alinhada ao playhead; trecho sem render ou
   editado depois toca o preview, marcado como desatualizado. Cache por frase (hash de notas +
   técnicas + dinâmica + parâmetros): só re-renderiza o que mudou.

## 2. Modos de execução (seletor na aba Instrument, automatizável)
| Modo | Preview (tempo real) | Render da IA |
|---|---|---|
| **Legato** (padrão) | monofônico; nota encostada/sobreposta não reataca: crossfade + deslize curto; nota separada reataca | uma linha, com legato e portamento |
| **Poly Legato** | polifônico com legato **por voz** (até 2 vozes: cordas duplas reais) | separa as vozes, renderiza cada uma e soma |
| **Long Normal** | polifônico, toda nota com arcada nova | sem legato; acordes renderizados por voz |

## 3. Modos de articulação
| Modo | Técnicas | Dinâmica |
|---|---|---|
| **Auto** (padrão) | o algoritmo decide (§4); keyswitch tocado prevalece | **pela velocity** (velocity baixa = dinâmica baixa) + arco de frase |
| **Auto + Dynamics** | o algoritmo decide (§4) | **você controla pelo CC1** (mod wheel; CC11 se não houver CC1); velocity só decide ataque e transição |
| **Manual** | só keyswitches (sem keyswitch: Sustain ou Legato pela conexão) | CC1 |

### Botões de articulação (forçar uma técnica)
Uma fileira de botões grandes, um por técnica — **Auto · Sustain · Legato · Spiccato ·
Staccato · Pizzicato · Tremolo · Trill · Portamento · Harmonic** — com LED, cor e a tecla do
keyswitch embaixo. Clicar num botão **força aquela técnica em todas as notas** (por exemplo, só
Pizzicato, só Spiccato, só Legato), tanto no preview quanto no render; **Auto** devolve a
decisão ao algoritmo. É o mesmo controle dos keyswitches (tocar D1 = clicar em Sustain) e é
automatizável pelo DAW, então dá para trocar de técnica ao longo da música por automação.
Prioridade: edição nota a nota > botão/keyswitch ativo > algoritmo.

## 3b. Mix Styles (mixagens embutidas)
Testado e descartado: reescrever a performance do MIDI por estilo (rubato, agógica) soava quase
igual de um estilo para outro. No lugar, **4 mixagens prontas** além de **Dry** (padrão, para
usar o reverb do DAW). Calibradas pelos guias de mixagem de cordas (ModWheel, MusicProductionWiki,
Stock Music Musician, Audiorecording.me, tailout) e pela prática de gravação barroca (igreja,
perspectiva distante). Implementação de referência: `mixer.py`.

| Mix Style | Sala (RT60) | Pré-delay | EQ no violino | Envio do reverb | Compressão / cor | Estéreo |
|---|---|---|---|---|---|---|
| **Dry** | — | — | — | — | — | mono centro |
| **Lyrical** | Chamber ~1,4 s, 26 % | 36 ms (na frente) | antes: HP 100 · −1,5 @300 · +2 @1,2 k · bus: +4 @3,2 k · shelf +5,5 @6,5 k | HP 220 / LP 11 k | 2:1 leve | 1,1 |
| **Romantic** | Concert Hall ~2,6 s, 36 % | 22 ms | antes: HP 75 · corpo +1,5 @250 · −0,5 @3,4 k · bus: +3,5 @2,4 k · shelf +5 @6,5 k | HP 170 / LP 10 k | sem compressão · fita | 1,35 |
| **Baroque** | Igreja ~3 s, 38 % | 6 ms (distante) | antes: HP 150 · caixa −3 @320 · bus: +3 @4,5 k · shelf +2,5 @7,5 k (sutil) | HP 160 / LP 8 k | nenhuma | 0,6 (estreito) |
| **Cinematic** | Scoring Stage ~3,2 s, 42 % | 35 ms (solista à frente) | antes: HP 90 · corpo +1 @250 · −1 @3,8 k (estreito) · bus: +3,5 @2,8 k · shelf +6,5 @6 k (tipo Pultec) | HP 200 / LP 11 k | bus 2,5:1, ataque 20 ms · fita | 1,8 (bem aberto) |

Medido contra o Dry no mesmo take: centróide 1309 → Lyrical 1505 · Romantic 1383 · Baroque 1497 ·
Cinematic 1499 Hz; ar (> 8 kHz) +2,8 / +3,0 / +1,4 / +4,8 dB; largura 0,23 / 0,40 / 0,26 / 0,60.
O brilho vai no **bus, depois da sala** (como o shelf de ar no bus de cordas): antes do reverb a
cauda, quase toda médios, diluía o brilho.

Mapa do violino usado: 200–350 Hz corpo · 300–500 Hz madeira/caixa · ~1 kHz nasal ·
2,5–4 kHz aspereza · 8–12 kHz ar. Para violino real os guias pedem EQ sutil; o que mais separa
os estilos é o espaço (sala, pré-delay, filtro do envio, largura).

- Knobs do módulo: **Mix Style**, **Amount** (molhado), **Decay** (escala do RT60), **Tone**.

## 3c. Render Quality
Medido na RTX 3070 Ti (`bench_violet.py`): 15 passos soam como 30 (0,6 dB de diferença no
espectro) e 60 como 30 (0,2 dB, inaudível); já **trocar a semente muda até 6 dB** (um take pode
sair 7 dB mais escuro). Por isso a qualidade máxima vem de **gerar mais takes e escolher**, não de
mais passos.

| Nível | Passos | Takes | Escolha | 10 s de frase (motor carregado) |
|---|---|---|---|---|
| **Low** | 8 | 1 (4 se ≥ 20 % de notas rápidas) | notas certas no tempo | ~0,8 s |
| **Medium** | 15 | idem | idem | ~1,3 s |
| **High** (padrão) | 30 | idem | idem | ~2,6 s |
| **Extreme Quality** | 30 | 8 | notas certas (faixas de 2 %) → brilho mais perto de um violino gravado (> 8 kHz ≈ −37 dB) → menor atraso | ~20 s |

Escolhido de ouvido pelo usuário: "o Extreme soa muito bem".

Teste com a melodia de 26 s pelo comando completo: High 30 s; Extreme 152 s (8 takes com "ar" de
−39,0 a −34,7 dB e 2 deles com 97 % de notas certas — a escolha descartou os piores). Os dois
tempos incluem ~13 s de carga do modelo e da CLI, que somem no motor persistente.
**Tempo real ao vivo não é possível com o VIOLET** (janelas de 10 s, não causal): ao vivo quem
toca é o preview; com Autorender a frase fica pronta ~1 s depois de capturada, e no playback o
motor renderiza à frente do cursor (~1,3 s por janela, uma a cada 5 s de música).
- O Mix Style vale para o preview e para o render (é efeito de saída, não muda a IA).

## 4. Detecção automática (mesmas regras no preview e no render)
| O que você toca | O que ele toca |
|---|---|
| nota curta e destacada (≤ 150 ms, ou ≤ 400 ms e < 60 % do espaço até a próxima) | **Spiccato** |
| alternância rápida entre duas notas a 1–2 semitons (≥ 4 notas ≤ 130 ms) | **Trilo** (de tom ou semitom, pelo intervalo) |
| mesma nota repetida muito rápido (≥ 4 notas ≤ 130 ms) | **Trêmolo** |
| nota ligada (encostada/sobreposta) | **Legato** |
| nota ligada tocada com **velocity baixa (< 45)** | **Portamento** |
| nota repetida ligada | Legato com troca de arco |
| notas rápidas ligadas ou em detaché (≤ 250 ms) | Natural (o modo que acerta 95–100 % das notas rápidas) |
| nota longa separada | **Sustain** |
| velocity da arcada (modo Auto) | **dinâmica** (35 → ~60 · 80 → ~85 · 115 → ~116); notas ligadas herdam o nível da arcada, então a velocity baixa do portamento não derruba o som |

Testado (`teste/regras/regras.mid`): portamento, spiccato, trilo e dinâmica pela velocity
detectados como acima, 100 % das notas certas no render.

**Sincronia preview ↔ performance:** o mesmo articulador (C++, com testes de equivalência
contra o `auto_articulate.py`) roda nos dois lados.
- *Reprodução de frase capturada:* o preview toca **exatamente** as técnicas que a IA vai
  renderizar (as mesmas que aparecem na faixa Articulation).
- *Tocando ao vivo:* a decisão é feita na hora com a informação disponível (ainda sem saber a
  duração da nota): ligada → legato; ligada com velocity baixa → portamento; notas rápidas e
  soltas → spiccato; alternância rápida → trilo a partir da 3ª nota. Quando a frase termina,
  a faixa Articulation mostra a decisão final (a mesma do render).

## 5. Keyswitches (simples: só teclas brancas, uma técnica por tecla; C1 = MIDI 36)
| Tecla | Técnica | Cor do chip |
|---|---|---|
| **C1** | **Auto** (volta ao automático) | ouro |
| D1 | Sustain | âmbar |
| E1 | Legato | mel |
| F1 | Spiccato | laranja |
| G1 | Staccato | cobre |
| A1 | Pizzicato | verde-oliva |
| B1 | Tremolo | vinho |
| C2 | Trill (tom; semitom quando a nota seguinte estiver a 1 semitom) | rosa-verniz |
| D2 | Portamento | mogno |
| E2 | Harmonic | creme |

Latch: vale da próxima nota em diante até outro keyswitch ou C1. Os chips ficam em linha na aba
Instrument (nome + tecla, como "Regular C1 · Pizzicato D1 · Tremolo E1" do Performer) e as teclas
aparecem coloridas no teclado virtual. Clicar no chip seleciona a técnica. Mapeamento pode ser
transposto (oitava) em Settings.

## 6. Preview em tempo real (sampler)
- **VSCO 2 Community Edition — Solo Violin** (CC0), **só o básico** para o plugin ficar leve
  e sobrar RAM/VRAM para o modelo: `Arco Vib` (sustain), `spic` (curtas) e `Pizz`; o `Trem`
  só se couber no orçamento. Por articulação: 1 amostra a cada 3 semitons, 2 camadas de
  dinâmica (p e f), 1 round robin (2 nas curtas), cauda cortada em ~2 s, FLAC 16 bits.
  **Meta: ≤ 60 MB** no disco e ~20 MB de RAM (só o início de cada amostra fica na memória).
- Sampler próprio: mapeamento por nota e camada de dinâmica, crossfade de camadas por CC1,
  round robin quando houver, release natural. Técnicas sem sample próprio são montadas:
  legato = crossfade + deslize de pitch (25 ms; portamento 90 ms), staccato = spiccato mais
  longo, trilo = alternância das duas notas no ritmo do trilo, harmônico = sustain filtrado.

## 7. Interface — fluxo do Performer, visual no estilo Apple, 2 temas

### Regras do Liquid Glass seguidas (WWDC25 "Meet Liquid Glass" e "Build an AppKit app with the new design")
1. **Vidro só na camada de controles**, que flutua sobre o conteúdo: barra de ferramentas
   (grupos em cápsula), barra de articulações, sidebar (placa flutuante), inspetor e barra de
   transporte. **O conteúdo não é vidro**: timeline/piano roll, listas de ajustes e teclado.
2. **Sem vidro sobre vidro**: dentro do vidro, botões usam preenchimentos translúcidos.
3. **Cor só no que é principal**: o botão Render (azul) e as articulações; Capture fica
   vermelho quando ativo; o resto é neutro com ícones monocromáticos.
4. **Cantos concêntricos** (janela 26 px → placas 20 px → linhas 8 px) e **cápsulas** nos
   controles grandes; segmentado com a opção ativa "levantada".
5. Títulos que não são botões (nome do plugin, status) ficam sem vidro.
6. Ajustes e efeitos em **listas agrupadas** (estilo Ajustes do Sistema) com sliders e
   switches, no lugar de knobs.
Decisão do usuário (2026-11-06), depois de testar "Maple/Ebony" (madeira e verniz) e um escuro
monocromático: **estilo Apple** (linguagem do macOS/iOS: superfícies lisas, cantos arredondados,
separadores finos, sombras quase invisíveis, controles segmentados, títulos em caixa normal,
cores de sistema). Inspirado, sem logotipos nem SF Pro (licença restrita): fonte **Inter**.

| Elemento | **Light** | **Dark** |
|---|---|---|
| Fundo | `#F5F5F7` | `#1C1C1E` |
| Painéis | branco `#FFFFFF`, sombra 0,5 px | `#2C2C2E` |
| Trilho de segmentado / opção ativa | `#EDEDF0` / branco com sombra | `#3A3A3D` / `#636366` |
| Destaque, seleção, notas | azul `#007AFF` | azul `#0A84FF` |
| Texto / secundário | `#1D1D1F` / `#6E6E73` | `#F5F5F7` / `#98989D` |
| Estados | Rendered verde `#34C759` · Rendering laranja `#FF9500` · Capturing vermelho `#FF3B30` | `#30D158` · `#FF9F0A` · `#FF453A` |
| Medidores | verde → amarelo → vermelho | idem (variantes escuras) |

A tela de Performance acompanha o tema (clara no Light, escura no Dark). **Switch ☀/☾** no topo
(verde de sistema quando no Dark; salvo por instância, padrão em Settings).

### Uma cor por articulação (paleta de sistema)
Auto cinza · Sustain azul · Legato ciano · Spiccato laranja · Staccato amarelo · Pizzicato verde ·
Tremolo roxo · Trill rosa · Portamento vermelho · Harmonic índigo — variantes claras/escuras da
paleta de sistema. Texto preto sobre a cor (≥ 4,5:1), branco só no índigo. As mesmas cores nos
botões (fundo cheio quando ativo; ponto colorido quando não), na faixa Articulation e nas teclas
de keyswitch do teclado.

### Teclado (rodapé, sempre visível)
Teclado A0–C8 com **pitch bend e mod wheel** à esquerda (como os teclados de sampler). A
tessitura do violino (G3–A7) fica acesa e o resto apagado; as teclas de keyswitch (C1–E2) têm a
cor da sua articulação; as notas tocadas acendem em tempo real.

### Topo
Logo + nome + versão · instrumento (ícone + "Violino Solo") · faixa do DAW · preset ◀ ▶ +
salvar · desfazer/refazer · ☀/☾ · Compact View · Settings · Help · status do motor
(● Pronto / ● Renderizando 2 / ● Modelo descarregado / ● Erro).

### Abas
1. **Performance** — régua do DAW, FIT, Zoom, visão geral; piano roll das notas capturadas;
   selos **CAPTURING** (segue o playhead) · **QUEUED** · **RENDERING** (progresso) ·
   **RENDERED ✓** · **OUTDATED**; faixas **Dynamics** (editável) e **Articulation** (chips por
   nota, editáveis: seleção → técnica ou Auto). Botões: Capture · Autorender · Render · Clear ·
   Export WAV. Rodapé: "3 frases capturadas · 2 renderizadas · a captura segue o playhead".
2. **Instrument** — "Play Mode" (Legato / Poly Legato / Long Normal), "Articulation Mode"
   (Auto / Auto + Dynamics / Manual), **fileira de botões de articulação** (§3), knobs:
   "Dynamics Intensity", "Level", "Legato Gap", "Portamento Velocity" (45), "Humanize",
   "Takes" (1–8 / Auto).
3. **Effects** — módulos lado a lado com power:
   - **EQ** (Low / Mid / High / Air)
   - **Width**
   - **Mix Style** (§3b) — **Dry por padrão** · Lyrical · Romantic · Baroque · Cinematic.
   - **Reverb** — **desligado por padrão**; 5 salas: **Room · Chamber · Concert Hall ·
     Scoring Stage · Cathedral** (FDN próprio de 8 linhas: reflexões iniciais estéreo, difusor,
     decaimento separado grave/agudo; RT60 medido a ±10 % do alvo). Knobs: Mix, Decay,
     Pre-delay, Tone, Send HP/LP. Os Mix Styles usam este mesmo reverb.
   - **Output** (ganho, medidor L/R, limitador)
4. **Project Control Room** (janela) — todas as instâncias: faixa, instrumento, frases,
   status; "renderizar tudo" / "parar"; uso de VRAM; **UNLOAD MODEL**.
5. **Settings** — motor (GPU escolhida, VRAM, precisão FP16/FP32, descarregar após X min
   parado), cache (pasta, tamanho, limpar), oitava dos keyswitches, tema padrão, idioma.

### Painel lateral (sempre visível)
Output (dB) + medidor · "**Render tocando**" / "**Preview tocando**" · status do motor e fila ·
VRAM usada · botão **UNLOAD MODEL** (libera a GPU; o modelo recarrega sozinho no próximo
render) · instâncias no projeto (abre o Control Room).

### Compact View
Instrumento, modo, Capture/Autorender, status, medidor.

## 8. Motor de render nativo (sem WSL, sem Python para o usuário)
- **VIOLET exportado para ONNX** (DiT ~555 MB + decodificador DACVAE ~411 MB; FP16 ≈ metade)
  e executado pelo **ONNX Runtime** num processo auxiliar **"Violino Engine" (C++)**:
  - **DirectML** (qualquer GPU DX12: NVIDIA, AMD, Intel) e **CUDA** quando houver NVIDIA.
  - Um único processo serve todas as instâncias do projeto (pipe local); se cair, não derruba
    o DAW. Nunca roda na thread de áudio.
  - Sampler de fluxo retificado (30 passos de Euler, CFG), janelas de 10 s com crossfade,
    escolha de candidato (detector de pitch YIN em C++) e compensação de atraso.
  - **Unload model** libera a VRAM na hora; descarregar automático após X min parado (Settings).
- Etapas: (1) exportar e validar o ONNX contra o PyTorch (diferença numérica + escuta);
  (2) motor C++; (3) instalador com os modelos. Se algum operador não exportar, plano B:
  runtime embutido (Python + PyTorch nativo do Windows, sem WSL, só NVIDIA).

## 9. Otimização
- Preview: samples com início pré-carregado na RAM e o resto lido do disco (streaming),
  limite de vozes, processamento em blocos, SIMD (juce::dsp), sem alocação na thread de áudio.
- Comunicação plugin ↔ motor por fila sem lock; renders gravados em cache no disco e lidos
  em streaming; só a frase editada é re-renderizada.
- GPU: FP16, janelas em lote, modelo carregado uma vez por sessão, unload manual/automático.
- UI: desenho vetorial com cache de camadas, 30 fps só quando algo muda.

## 10. Checagem contra o Vienna Performer
| Performer | Aqui |
|---|---|
| Instrument + chips de articulação com keyswitch | ✓ (layout simples, teclas brancas) |
| Sound: Mixer, Close/Room, Output, medidor | ✓ Effects + Output; Reverb off por padrão |
| Performances: régua, FIT, Zoom, notas, Dynamics, Articulation | ✓ |
| Capturing / Rendered, captura segue o playhead | ✓ (+ Queued, Rendering, Outdated) |
| Autorender / Capture | ✓ (+ Render manual, Clear, Export) |
| Status: Ready, créditos | ✓ status do motor/GPU (local, sem créditos) + Unload model |
| Project Control Room | ✓ |
| Compact View, Settings, Help | ✓ |
| Preview simples enquanto não renderiza | ✓ violino solo (VSCO 2 CE) |
| Frase por pausa ≥ 2 s, re-render só do que mudou | ✓ |

## 11. Base para outros instrumentos e plugins
O código é dividido em **núcleo** (captura, timeline, motor, UI, efeitos, cache) e **pacote de
instrumento** (modelo de IA, samples de preview, regras do articulador, mapa de keyswitches,
ícone e cores). Um plugin novo (cello, flauta, naipe de cordas...) é um pacote novo sobre o
mesmo núcleo.

## 12. Licenças
JUCE (GPLv3 para projeto open source) · VSCO 2 CE (CC0) · VIOLET (MIT; atenção: parte do
treino usou renders de uma sample library comercial) · ONNX Runtime (MIT).

## 12b. Textos em inglês (rótulos finais)
Abas: "Performance" · "Instrument" · "Effects" · "Control Room" · "Settings".
Botões: "Capture" · "Autorender" · "Render" · "Clear" · "Export WAV" · "Unload Model" ·
"Compact View" · "Help". Estados: "Capturing" · "Queued" · "Rendering" · "Rendered" ·
"Outdated" · "Ready" · "Model unloaded" · "Engine offline". Painel: "Render playing" /
"Preview playing". Motivos das decisões (já em inglês no articulador): "short and detached",
"connected with low velocity", "notes alternating by 2 semitones", "long and separate"...
Relatório de técnicas: colunas `idx, start_s, note, length_ms, technique, reason, dynamics`.

## 13. Ordem de construção
1. Exportar VIOLET para ONNX e validar contra o PyTorch (Windows nativo).
2. Motor "Violino Engine" (C++/ONNX Runtime) + unload + articulador em C++ com testes contra o
   Python.
3. Plugin mínimo: sampler de preview (3 modos) + captura + envio + reprodução do render.
4. Aba Performance; abas Instrument e Effects (com os 5 reverbs); temas; Compact View; Control
   Room; presets.
5. Testes em DAW (Cubase, Reaper, FL Studio, Ableton): sincronia, salvar/abrir, várias
   instâncias, mudança de tempo, 44,1/48/96 kHz.
