# Abre a aba Effects no Standalone e tira um print de cada mÃ³dulo pedido (Ã­ndices 0..6 da fileira)
param([string]$Dir, [string]$Tiles = "0 5 2 6")
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class UF { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r); [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y); [DllImport("user32.dll")] public static extern void mouse_event(int f, int x, int y, int d, int e);
public struct RECT { public int L, T, R, B; } }
"@
$p = Get-Process Violino | Select-Object -First 1
[UF]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 400
$r = New-Object UF+RECT; [UF]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
$s = ($r.R - $r.L - 2) / 1280.0
function Click([double]$x, [double]$y) {
  [UF]::SetCursorPos([int]($r.L + 1 + $x * $s), [int]($r.T + 30 + $y * $s)); [UF]::mouse_event(2,0,0,0,0); Start-Sleep -Milliseconds 60; [UF]::mouse_event(4,0,0,0,0); Start-Sleep -Milliseconds 500
}
Click 711 31   # aba Effects
foreach ($i in ($Tiles -split "[ ,;]+" | ForEach-Object { [int]$_ })) {
  Click (280 + $i * 110.6 + 40) 200
  [UF]::SetCursorPos($r.L + 5, $r.B - 5); Start-Sleep -Milliseconds 600
  $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
  [System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
  $c = $bmp.Clone([System.Drawing.Rectangle]::new([int](270 * $s), [int](30 + 110 * $s), [int](790 * $s), [int](600 * $s)), $bmp.PixelFormat)
  $c.Save("$Dir\fx_" + $i + "_" + (Get-Date -Format "HHmmss") + ".png")
}
"ok"

