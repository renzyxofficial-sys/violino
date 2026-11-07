# Estado do projeto (2026-11-06, ~14:20)

## Pronto e instalado (VST3 em C:\Program Files\Common Files\VST3\Violino.vst3)
- Modelos e samples DENTRO do pacote (Contents\Resources) — ver memória sandbox-appdata-virtualized.
- v0.5: preview com relógio próprio (bug do spiccato com DAW parado), Stop do render, captura de CC1,
  dinâmica: render segue a curva alvo (Dynamics follow), preview usa a curva; Reverb estilo uJAM com
  Freeze/Ducking/Surprise; EQ Pro-Q, Saturator, Echo, Compressor, Chorus, Stereo; edição de MIDI na
  timeline (selecionar/mover/redimensionar/criar/apagar) + paleta de articulações; aba Score (papel antigo).

## v0.6 (instalado ~14:35)
- Stereo off por padrão; chip de articulação segue o mouse e cai só na nota sob o cursor; Ctrl+roda = zoom
  no MIDI (centrado no mouse); Play Mode = Legato / Shorts (Spiccato, Staccato, Pizzicato); Steps 1..50
  (os botões de qualidade ajustam: 8/15/30/30); rótulo do Zoom livre.

## v0.7 (instalado ~14:41)
- Drag MIDI por frase (♪ MIDI: .mid com as edições e o CC1, 960 ppq, tempo do DAW); transporte interno:
  ⏮ volta ao início, ▶/⏸ toca e pausa do cursor, clique na régua posiciona o cursor.

## v0.7.2 (instalado): Espaço = play/stop; stop volta para onde o play começou; foco do teclado ao abrir/clicar.

## PRÓXIMO (pedido de 2026-11-06 ~15:00, não iniciado — pausado em 95% do limite)
a. Timeline: grade de compassos/tempos pelo BPM + faixas de altura (teclas pretas) para saber onde cria o MIDI.
b. Barra de rolagem horizontal da timeline (quando com zoom) e arrastar a vista com o botão do meio do mouse.
c. Reverb: trocar o donut por algo intuitivo (gráfico do envelope: pre-delay, reflexões iniciais, cauda do
   Decay, com o Size); o aviso OFF fica sobre o Output (mover para perto do título).
d. Aba Effects: botão para desligar TODOS os efeitos de uma vez (bypass global; parâmetro fxBypass).

## Falta (pedido do usuário)
0. Score editável como Cubase/Logic: escrever notas clicando na pauta (ferramenta lápis, figura escolhida,
   arrastar nota na pauta muda altura, apagar). Hoje só exibe. Ver também quadradinhos azuis estranhos na pauta
   com a performance real do usuário (provável glifo).

1. Biblioteca de ~100 MIDIs clássicos (APROVADO baixar do Mutopia Project, CC/domínio público):
   partes de violino; categorias por compositor / gênero / performance (estilo do browser do Addictive
   Drums); ouvir, carregar na timeline do plugin e arrastar para o DAW.
2. Opcional: testar VIOLET com w_cc > 0 (dinâmica nativa da IA) — hoje é pós-render.

## Dicas de trabalho
- Fechar o Standalone com tools\restart_standalone.ps1 (matar à força deixa WebView2 órfão = tela branca).
- Prints: tools\shot_fx.ps1 -Tiles "0 6"; conferir JS com node --check no <script> do index.html.
- Build: plugin\ui\build_ui.py e depois cmake --build plugin\build --config Release.
