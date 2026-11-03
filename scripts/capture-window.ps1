param([string]$Name = 'cosmos2-window.png')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$session = Get-Content "$root\output\session.json" | ConvertFrom-Json
$process = Get-Process -Id $session.app
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WindowCapture {
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left,Top,Right,Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out Rect r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);
}
'@
$rect = New-Object WindowCapture+Rect
$handle = $process.MainWindowHandle
if ($handle -eq 0) { throw 'A janela do Cosmos2 ainda nao esta disponivel.' }
[WindowCapture]::GetWindowRect($handle, [ref]$rect) | Out-Null
$bitmap = New-Object Drawing.Bitmap ($rect.Right - $rect.Left), ($rect.Bottom - $rect.Top)
$graphics = [Drawing.Graphics]::FromImage($bitmap)
$dc = $graphics.GetHdc()
try { $ok = [WindowCapture]::PrintWindow($handle, $dc, 2) } finally { $graphics.ReleaseHdc($dc) }
if (!$ok) { throw 'O Windows nao conseguiu capturar a janela do Cosmos2.' }
$path = Join-Path "$root\evidence" $Name
$bitmap.Save($path, [Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose(); $bitmap.Dispose()
Write-Output $path
