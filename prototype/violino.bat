@echo off
rem MIDI de violino -> audio (tecnicas e dinamica automaticas + VIOLET no WSL).
rem Uso: violino entrada.mid saida.wav [--overrides tecnicas.csv] [--mix dry|lyrical|romantic|baroque|cinematic] [--qualidade low|medium|high|extreme] [--candidatos N]
if "%~2"=="" (
  echo Uso: violino entrada.mid saida.wav [--overrides tecnicas.csv] [--mix dry|lyrical|romantic|baroque|cinematic] [--qualidade low|medium|high|extreme] [--candidatos N]
  exit /b 1
)
rem --exec: sem shell no meio, para as barras invertidas dos caminhos chegarem intactas
wsl -d Ubuntu --exec /home/theoh/miniforge3/envs/violet/bin/python /mnt/c/Users/TheoH/violino/prototype/violino.py %*
