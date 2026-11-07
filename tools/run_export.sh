#!/bin/bash
# Exporta o VIOLET para ONNX (chamado do Windows: wsl -d Ubuntu --exec bash /mnt/c/Users/TheoH/violino/tools/run_export.sh)
set -e
cd ~/VIOLET
cp /mnt/c/Users/TheoH/violino/tools/export_onnx.py src/export_onnx.py
export PROJECT_ROOT=~/VIOLET
export REF_MIDI=/mnt/c/Users/TheoH/violino/teste/melody_auto.mid
export OUT_DIR=/mnt/c/Users/TheoH/violino/onnx
CK=~/VIOLET/checkpoints
~/miniforge3/envs/violet/bin/python src/export_onnx.py \
  "model.ema_ckpt_path=$CK/pretrained_checkpoint/ema_snapshots/ema_prof_99515" \
  "encoder.finetuned_ckpt=$CK/dacvae_ft/weights.pth" logger=csv \
  hydra.run.dir=/tmp/violet_export
ls -la "$OUT_DIR"
