cd ~/VIOLET
ls; ls checkpoints
grep -niE "huggingface|hf\.co|zenodo|dataset|checkpoint|download|CSV-TD|license" README* 2>/dev/null | head -30
git remote -v 2>/dev/null | head -2
