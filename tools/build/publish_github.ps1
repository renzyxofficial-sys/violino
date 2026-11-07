# Publica o repositório no GitHub (público) com o e-mail privado do GitHub no commit.
$ErrorActionPreference = 'Stop'
$gh = 'C:\Program Files\GitHub CLI\gh.exe'
Set-Location 'C:\Users\TheoH\violino'

$login = & $gh api user --jq .login
$id = & $gh api user --jq .id
$noreply = "$id+$login@users.noreply.github.com"
git config user.name $login
git config user.email $noreply
# reescreve o autor do único commit (ainda não enviado) e refaz a tag nele
git commit --amend --reset-author --no-edit | Out-Null
git tag -f -a v0.22-alpha -m 'Alpha 0.22: backup point before next improvements' | Out-Null
Write-Host "Autor do commit: $(git log -1 --format='%an <%ae>')"

& $gh repo create violino --public --source . --remote origin --push `
    --description 'AI solo violin for your DAW: VST3/Standalone running the VIOLET neural model locally (ONNX Runtime + DirectML)'
git push origin v0.22-alpha
& $gh repo edit "$login/violino" --add-topic vst3 --add-topic juce --add-topic violin --add-topic music-ai --add-topic diffusion
Write-Host "Pronto: https://github.com/$login/violino"
