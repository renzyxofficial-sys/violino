# Fecha o Standalone do jeito certo (sem deixar WebView2 órfão), limpa órfãos e abre de novo
$p = Get-Process Violino -ErrorAction SilentlyContinue
if ($p) { $p | ForEach-Object { $_.CloseMainWindow() | Out-Null }; Start-Sleep 2; Get-Process Violino -ErrorAction SilentlyContinue | Stop-Process -Force }
Get-CimInstance Win32_Process -Filter "Name='msedgewebview2.exe'" | Where-Object { $_.CommandLine -match 'Violino' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if ($args[0] -ne 'stop') { Start-Process C:\Users\TheoH\violino\plugin\build\Violino_artefacts\Release\Standalone\Violino.exe | Out-Null }
