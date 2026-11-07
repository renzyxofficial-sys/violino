# Violino — estado e backlog
# v0.17 (2026-11-06 noite): backlog principal concluído. Falta: sugestões finais / testes do usuário.
 (atualizado 2026-11-06 ~20:30)

Instalado: VST3 em C:\Program Files\Common Files\VST3\Violino.vst3 (modelos e samples em Contents\Resources).
Build: python plugin\ui\build_ui.py; cmake --build plugin\build --config Release --target Violino_Standalone Violino_VST3;
copiar o binário Contents\x86_64-win\Violino.vst3 (Ableton fechado). Conferir JS: node --check no <script> do index.html.
Standalone: tools\restart_standalone.ps1 (nunca matar à força: WebView2 órfão = tela branca).
Memória: sandbox virtualiza %LOCALAPPDATA% (Ableton não enxerga) -> conteúdo vai no pacote do VST3.
Notas antigas: RETOMAR_old.md.

## Feito até v0.8.2
EQ Pro-Q, Saturator, Echo, Reverb (estilo uJAM), Compressor, Chorus, Stereo, FX ON/OFF global; dinâmica
(CC1, Dynamics follow); edição de MIDI na timeline + paleta; Score (só exibe); Drag Audio/MIDI por frase;
transporte interno (⏮ ▶/■, régua, stop volta ao início do play); grade + scrollbar + botão do meio;
Play Mode Legato/Shorts; Steps 1..50; Espaço só no Standalone.

## Bloco 1 instalado (v0.9): itens [x] abaixo. Chiado: Hermite + normalização + roubo de voz suave (confirmar com o usuário).

## Bloco 2 instalado (v0.10): ferramentas da seleção, split de take (✂ no cursor), fade por trecho (alça branca),
   lápis na Dynamics, portamento manual liga até 1 s, trilo sempre junta.

## Bloco 3 instalado (v0.11, 2026-11-06): regiões estilo Logic (cabeçalho: seleciona/move; bordas: corta/estende,
   Alt = estica; cmd takeResize), barra do take fixa e centralizada, barra vertical de mover (Sel/Take/All, texto),
   zoom/scroll suaves (por tempo), faixa de velocity + Alt/roda (cmd noteVel), fade estilo FL com curvatura
   (fadeTension, p[8]), dynamics por clique-e-arraste contínuo, transporte centrado, reverb estilo ChromaVerb
   (MAIN/DETAILS, nós do Damping EQ), cores do tema claro, "Sound Presets". Teste no navegador: tools/mk_harness.py -> uit/test.html.

## Bloco 4 instalado (v0.12): Play/Pause/Stop (cmds pause/stop), undo/redo no C++ (EditSnap; Ctrl+Z, botões do topo),
   Ctrl+C/V/X/A/D, Delete apaga notas ou o take selecionado, seleção por caixa, menu do botão direito (notas/take/roll),
   grade Auto/Snap/Free (edit.js), régua em compassos (arrastar = zoom/rolagem), visão geral no lugar da barra de rolagem,
   renomear take (duplo clique no cabeçalho; CapNote.take), BPM do Standalone (cmd bpm, Settings standaloneBpm),
   barra de controle estilo Ableton na largura toda, Drag All com WAV pronto em segundo plano, reverb animado (canvas rvfx).

## Bloco 5 instalado (v0.13): Play interno toca o preview das notas sem render (antes: sem render = Play mudo),
   Pause/Stop soltam as notas; metrônomo só no Standalone (cmd metro, Settings metronome); desfazer só registra
   mudança real (sameSnap) e a captura vira um passo próprio; Alt durante o arraste = sem grade; Ctrl+arrastar = velocity.

## Bloco 6 instalado (v0.14): Standalone: Play roda livre (não para no fim nem sem render) e grava na posição da
   timeline (t0 = timelinePos); Play/Espaço de novo = pausa; Cycle (cmd cycle {on,a,b}, faixa amarela na régua, desligado por padrão).

## v0.18: modo Auto força tudo em Auto (render e preview); CC1 da dinâmica entra no VIOLET (param modelDyn, padrão on;
   não entra no hash -> renders antigos continuam, ↻ para ouvir com CC1); modo foco (botão Compact view: esconde painéis, G.l/G.w).

## v0.19: (modo Auto com tudo em Tech::none soou PIOR -> revertido em v0.19.1: Auto = articulador decide, ignorando marcações); modelDyn agora
   desligado por padrão (avaliação oficial: sampler_w_tech 1, sampler_w_cc 0; long_audio usa default_cc1_value 100);
   modo foco animado (L.geoK); Alt+roda fora das notas = zoom vertical (L.vzoom, Shift+roda rola), notas com altura variável.

## v0.20: Even out (levelNotes): cada nota medida enquanto soa e aproximada da mediana (+9/-6 dB, 70%), antes do
   shapeDynamics; corrige sustain/legato mais baixos que ataques curtos. Sem re-render (pós-processo).

## v0.21: Even out virou nivelador contínuo (envelope 300 ms -> p60 da frase, 90%, -8..+15 dB, sem subir silêncio):
   no render real de 32,8 s o spread caiu de 20,8 dB para 5,1 dB (tools/level_sim.py).

## v0.22: análise (tools/quality.py): ruído sobe nos trechos baixos/longos; emendas OK (oficial também faz crossfade
   Hann 50%). Oficial usa sampler_steps 30 -> Low 8 · Med 15 · High 30 (padrão) · Extreme 30 + 8 takes; steps 4..50.
   Even out limitado a +10 dB. Próximos: A/B de steps, escolha do melhor por janela.

## BACKLOG — pedido grande do usuário (2026-11-06 noite). Fazer TUDO, preservando o que existe.
### Áudio / preview / render
- [x] Drag All Audio (manter os individuais)
- [x] Chiado quando o preview toca junto com o Ableton
- [x] Preview com volume inconsistente (muito baixo/alto) — referência da melodia
- [x] Render sempre mono: o VIOLET gera mono por natureza; a largura vem do reverb/Mix presets e do módulo Stereo (off por padrão, a pedido)
- [x] Renderizar cada trecho individualmente
- [x] Remover todas as renderizações / remover render de um trecho para refazer
- [x] Limitar o tamanho do cache de áudio (pasta cache .f32)
- [x] Som antes da 1ª nota: silenciar antes do ataque + fade in discreto
- [x] Tocar prévia da nota ao mover/adicionar nota no piano roll
### MIDI / edição
- [x] Export MIDI com dynamics / sem dynamics (duas opções)
- [x] Nome de cada nota no piano roll
- [x] Excluir um take MIDI inteiro (por frase)
- [x] Ferramenta Split + edição de trechos estilo piano roll/playlist
- [x] Fade in por trecho ajustável (como Logic/Ableton/FL)
- [x] Edição de velocity
- [x] Quantize + humanize, transpose, split de notas, Scale Correct (ref.: Ableton Pitch & Time: Fit to Scale,
      Invert, Add Interval, Stretch x2 /2, Grid, Set Length, Humanize %, Reverse, Legato)
- [x] Dynamics: lápis / pontos e curvas
### Articulações / interpretação
- [x] Sobreposição visual das articulações; 1 articulação por nota
- [x] Trill detectado = só Trill na nota
- [x] Articulações manuais (Portamento) não funcionam — checar relação com velocity
- [x] Controles de vibrato e playstyle (v0.15: VIOLET não tem vibrato/estilo nativo — só notas, técnica e CC1;
      Playstyle = macro de legato/portamento/dinâmica antes do render; vibrato = linha de atraso modulada só SOMA, notas > 0,35 s)
- [x] Play do Standalone cortava a nota segurada (só staccato) — corrigido v0.15
- [x] VIOLET tem posição de microfone? NÃO (verificado no código: entradas = notas, técnica, CC1; 'classes' existe na DiT
      mas o modelo foi treinado com classes=None). O som é sempre o close do dataset; ambiente = Mix presets / reverb.
### Score / navegação
- [x] Score editável (v0.17: seleção/lápis/borracha, figuras + ponto, ♯ ♭, arrastar altura e tempo, quadradinho azul do lápis)
- [x] Lista de páginas acessível (v0.16: botões de página no rodapé da Score)
### Interface / animações
- [x] Sobreposições na área de export MIDI e nas articulações
- [x] Presets de sonoridade (Mix Styles) na página principal
- [x] Corrigir a linha vermelha (passa por cima do transporte)
- [x] Escala padrão 125%
- [x] Fundo gradiente estilo Apple nos dois temas (ref.: C:\Users\TheoH\Downloads\dark-gradient-background-with-copy-space_53876-99548.avif)
- [x] Liquid Glass fiel à Apple nos botões (v0.16: 1ª rodada só CSS — brilho, borda de luz, hover/clique, chaves com mola, menus animados)
- [x] Animações fluidas (troca de aba, menus, chaves com mola, notas com transição)
- [x] Nota tocando: brilho + leve bounce
- [x] Nota inteira na cor da articulação (hoje só um traço no início)
### Pesquisa
- [x] Instrument X (Dreamtonics): pré-render, editor interno, import MIDI/MusicXML, Retakes, unison até 16. Trazido: Import MIDI
- [ ] No fim: sugerir melhorias
### Ainda de antes
- [x] Reverb: trocar o donut por gráfico de envelope; OFF sobre o Output
- [x] Biblioteca (v0.17): 60 peças / 137 MIDIs / 31 compositores (tools/get_mutopia.py -> library/, copiada para Contents/Resources/library), painel ♫ Library com filtro por estilo e Playstyle sugerido
