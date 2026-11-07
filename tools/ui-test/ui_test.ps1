# Teste de ponta a ponta no Standalone: toca notas clicando no teclado da UI e tira prints.
param([string]$Shot = "$env:TEMP\violino_test.png", [int]$WaitAfter = 20)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class U {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
  public struct RECT { public int L, T, R, B; }
}
"@
$p = Get-Process Violino | Select-Object -First 1
[U]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
Start-Sleep -Milliseconds 600
$r = New-Object U+RECT; [U]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
# conteúdo começa abaixo da barra do Standalone (~30 px); a UI é 1280x940 escalada
$cw = $r.R - $r.L - 2; $top = $r.T + 30; $s = $cw / 1280.0
$wk = 1172.0 / 52 * $s
# teclas brancas: A0 = índice 0; C4 = índice 23. Teclado começa em x = 18 + 2*22 + 2*10 + 14 (rodas) ~ 96 px
$kx0 = $r.L + 1 + (18 + 22 + 10 + 22 + 14) * $s
$ky = $top + (940 - 150 + 16 + 90) * $s
function Click-Key([int]$white, [int]$ms) {
  # medido no print: C4 (branca 23) começa em x ~ 680 da janela, teclas a ~19,7 px, altura útil em y ~ 790
  $x = [int]($r.L + 689 + ($white - 23) * 19.72 * ($cw / 1120.0))
  $y = [int]($r.T + 790 * ($cw / 1120.0))
  [U]::SetCursorPos($x, $y); [U]::mouse_event(2, 0, 0, 0, 0); Start-Sleep -Milliseconds $ms; [U]::mouse_event(4, 0, 0, 0, 0)
}
# C5 D5 E5 F5 G5 E5 C5 (índices de branca: C5 = 30)
foreach ($k in 30, 31, 32, 33, 34, 32, 30) { Click-Key $k 380; Start-Sleep -Milliseconds 40 }
Start-Sleep -Seconds $WaitAfter
$bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$bmp.Save($Shot)
"ok $Shot"
